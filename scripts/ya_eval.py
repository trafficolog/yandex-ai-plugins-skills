#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

try:
    from .eval_benchmark.runner import run_benchmark
    from .eval_benchmark.scenarios import load_scenarios
except ImportError:
    from eval_benchmark.runner import run_benchmark
    from eval_benchmark.scenarios import load_scenarios


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

    args = parser.parse_args(argv)
    try:
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
        result = run_benchmark(
            scenarios,
            subject_argv=subject_argv,
            judge_argv=judge_argv,
            evaluated_at=evaluated_at,
            repository_sha=repository_sha,
            allow_self_judge=args.allow_self_judge,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    except (ValueError, RuntimeError, TimeoutError, OSError) as exc:
        return _emit_error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
