#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

try:
    from .eval_benchmark.artifacts import (
        build_result_document,
        publish_benchmark_artifacts,
        render_comparison_html,
    )
    from .eval_benchmark.backend_trace import (
        compare_backend_traces,
        load_fixture,
        run_bundled_direct_fixture,
    )
    from .eval_benchmark.protocol import REQUEST_SCHEMA, canonical_json_bytes, invoke_adapter
    from .eval_benchmark.runner import run_benchmark
    from .eval_benchmark.scenarios import load_scenarios
    from .eval_benchmark.snapshots import materialize_snapshot
except ImportError:
    from eval_benchmark.artifacts import (
        build_result_document,
        publish_benchmark_artifacts,
        render_comparison_html,
    )
    from eval_benchmark.backend_trace import (
        compare_backend_traces,
        load_fixture,
        run_bundled_direct_fixture,
    )
    from eval_benchmark.protocol import REQUEST_SCHEMA, canonical_json_bytes, invoke_adapter
    from eval_benchmark.runner import run_benchmark
    from eval_benchmark.scenarios import load_scenarios
    from eval_benchmark.snapshots import materialize_snapshot


ROOT = Path(__file__).resolve().parents[1]
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


def load_adapter_argv(path: Path) -> list[str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid adapter argv JSON: {path}") from exc
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
        raise ValueError("adapter argv config must be a non-empty JSON array of non-empty strings")
    return value


def _plugins(value: str | None) -> list[str] | None:
    if value is None or value == "all":
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise ValueError("--plugins must name at least one plugin or 'all'")
    return items


def _emit_error(message: str) -> int:
    sys.stderr.write(f"ERROR: {message}\n")
    return 2


def _read_json_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label} JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _backend_equivalence(connected_config: Path, fixture_path: Path) -> dict[str, object]:
    fixture = load_fixture(fixture_path)
    connected_argv = load_adapter_argv(connected_config)
    invocation_id = "backend-" + hashlib.sha256(canonical_json_bytes(fixture)).hexdigest()[:24]
    response = invoke_adapter(
        connected_argv,
        {
            "schema": REQUEST_SCHEMA,
            "invocation_id": invocation_id,
            "kind": "backend-equivalence",
            "payload": {"fixture": fixture},
        },
    )
    output = response.get("output")
    if not isinstance(output, dict) or not isinstance(output.get("trace"), dict):
        raise ValueError("connected backend adapter must return output.trace")
    bundled = run_bundled_direct_fixture(ROOT, fixture)
    return compare_backend_traces(output["trace"], bundled)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Provider-neutral executable eval benchmark")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Validate and enumerate eval-v2 fixtures without model execution")
    check.add_argument("--plugins", default="all")

    run = sub.add_parser("run", help="Run eval-v2 fixtures through subject and independent judge adapters")
    run.add_argument("--subject-adapter", type=Path, required=True)
    run.add_argument("--judge-adapter", type=Path, required=True)
    run.add_argument("--plugins", default="all")
    run.add_argument("--evaluated-at")
    run.add_argument("--repository-sha", required=True)
    run.add_argument("--output-root", type=Path, default=Path("artifacts/evals"))
    run.add_argument("--allow-self-judge", action="store_true")

    compare = sub.add_parser("compare", help="Render self-contained HTML from a normative benchmark result")
    compare.add_argument("--results", type=Path, required=True)
    compare.add_argument("--output", type=Path)

    backend = sub.add_parser("backend-equivalence", help="Compare connected and bundled safety-gate traces")
    backend.add_argument("--connected-adapter", type=Path, required=True)
    backend.add_argument("--fixture", type=Path, required=True)

    snapshot = sub.add_parser("publish-snapshot", help="Materialize a verified reviewable snapshot without committing it")
    snapshot.add_argument("--artifact-dir", type=Path, required=True)
    snapshot.add_argument("--repository-root", type=Path, default=ROOT)

    args = parser.parse_args(argv)
    try:
        if args.command == "backend-equivalence":
            result = _backend_equivalence(args.connected_adapter, args.fixture)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0 if result.get("state") == "PASS" else 1

        if args.command == "compare":
            result = _read_json_object(args.results, "benchmark results")
            rendered = render_comparison_html(result)
            if args.output is None:
                sys.stdout.write(rendered + "\n")
            else:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(rendered + "\n", encoding="utf-8", newline="\n")
                print(json.dumps({"output": str(args.output)}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0

        if args.command == "publish-snapshot":
            destination = materialize_snapshot(args.artifact_dir, args.repository_root)
            print(json.dumps({"snapshot_dir": str(destination), "snapshot_id": destination.name}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0

        plugin_names = _plugins(args.plugins)
        if args.command == "check":
            scenarios = load_scenarios(ROOT, plugin_names)
            print(json.dumps({"status": "OK", "scenario_count": len(scenarios)}, sort_keys=True))
            return 0

        repository_sha = args.repository_sha
        if not isinstance(repository_sha, str) or _SHA40.fullmatch(repository_sha) is None:
            raise ValueError("repository SHA must be exactly 40 lowercase hex characters")
        evaluated_at = args.evaluated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        subject_argv = load_adapter_argv(args.subject_adapter)
        judge_argv = load_adapter_argv(args.judge_adapter)
        scenarios = load_scenarios(ROOT, plugin_names)
        run_result = run_benchmark(
            scenarios,
            subject_argv=subject_argv,
            judge_argv=judge_argv,
            evaluated_at=evaluated_at,
            repository_sha=repository_sha,
            allow_self_judge=args.allow_self_judge,
        )
        result = build_result_document(run_result)
        destination = publish_benchmark_artifacts(args.output_root, result)
        print(json.dumps({
            "artifact_dir": str(destination),
            "benchmark_id": result["benchmark_id"],
            "completeness": result["completeness"],
            "comparative_complete": result["comparative_complete"],
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except (ValueError, RuntimeError, TimeoutError, OSError) as exc:
        return _emit_error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
