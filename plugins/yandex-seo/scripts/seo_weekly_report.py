from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

try:
    from .seo_weekly_artifacts import artifact_directory, build_manifest, publish_artifact_set
    from .seo_weekly_graphs import export_graphs
    from .seo_weekly_html import render_html
    from .seo_weekly_memory import load_project_context
    from .seo_weekly_model import canonical_json_bytes, normalize_report_input
except ImportError:
    from seo_weekly_artifacts import artifact_directory, build_manifest, publish_artifact_set
    from seo_weekly_graphs import export_graphs
    from seo_weekly_html import render_html
    from seo_weekly_memory import load_project_context
    from seo_weekly_model import canonical_json_bytes, normalize_report_input


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
DEMO_FIXTURE = PLUGIN_ROOT / "fixtures" / "weekly-organic-demo.json"


def _now_rfc3339() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path, field: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read valid JSON from {field}: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{field} must contain a JSON object")
    return value


def _service_envelope(path: Path, service: str) -> tuple[dict[str, str], dict[str, str], dict[str, Any]]:
    raw = _load_json(path, service)
    period = raw.pop("period", None)
    comparison = raw.pop("comparison_period", None)
    if not isinstance(period, dict) or not isinstance(comparison, dict):
        raise ValueError(f"{service} input requires period and comparison_period objects")
    return period, comparison, raw


def _merge_periods(values: list[tuple[dict[str, str], dict[str, str]]]) -> tuple[dict[str, str], dict[str, str]]:
    if not values:
        raise ValueError("build requires at least one service input")
    period, comparison = values[0]
    for other_period, other_comparison in values[1:]:
        if other_period != period or other_comparison != comparison:
            raise ValueError("service inputs must use identical period and comparison_period")
    return period, comparison


def _project_context(args: argparse.Namespace) -> dict[str, Any]:
    memory = load_project_context(Path(args.project_root))
    explicit_id = args.project_id
    explicit_name = args.project_name
    if (explicit_id is None) != (explicit_name is None):
        raise ValueError("--project-id and --project-name must be supplied together")
    if explicit_id is not None:
        project: dict[str, Any] = {"id": explicit_id, "name": explicit_name}
        if memory and memory.get("user_stated"):
            project["user_stated"] = memory["user_stated"]
        return project
    if memory is None:
        raise ValueError("build requires project memory or explicit --project-id/--project-name")
    return memory


def _publish(payload: dict[str, Any], *, output_root: Path, generated_at: str) -> dict[str, Any]:
    report = normalize_report_input(payload, generated_at=generated_at)
    report_bytes = canonical_json_bytes(report)
    files: dict[str, bytes] = {
        "report.json": report_bytes,
        "report.html": render_html(report).encode("utf-8"),
    }
    for path, text in export_graphs(report).items():
        files[path] = text.encode("utf-8")
    manifest = build_manifest(files, report_bytes=report_bytes, created_at=generated_at)
    destination = artifact_directory(
        Path(output_root),
        report["project"]["id"],
        report["period"]["to"],
        report["report_id"],
    )
    publish_artifact_set(destination, files, manifest)
    return {
        "report_id": report["report_id"],
        "artifact_set_id": manifest["artifact_set_id"],
        "path": str(destination),
        "coverage": report["coverage"],
        "limitations": report["limitations"],
    }


def _run_demo(args: argparse.Namespace) -> dict[str, Any]:
    payload = _load_json(DEMO_FIXTURE, "demo fixture")
    return _publish(
        payload,
        output_root=Path(args.output_root),
        generated_at=args.generated_at or _now_rfc3339(),
    )


def _run_build(args: argparse.Namespace) -> dict[str, Any]:
    periods: list[tuple[dict[str, str], dict[str, str]]] = []
    payload: dict[str, Any] = {"project": _project_context(args)}
    if args.webmaster is not None:
        period, comparison, service = _service_envelope(Path(args.webmaster), "webmaster")
        periods.append((period, comparison))
        payload["webmaster"] = service
    if args.metrika is not None:
        period, comparison, service = _service_envelope(Path(args.metrika), "metrika")
        periods.append((period, comparison))
        payload["metrika"] = service
    period, comparison = _merge_periods(periods)
    payload["period"] = period
    payload["comparison_period"] = comparison
    if args.structures is not None:
        structures = _load_json(Path(args.structures), "structures")
        if "structural_tree" not in structures and isinstance(structures.get("structures"), dict):
            structures = structures["structures"]
        payload["structures"] = structures
    return _publish(
        payload,
        output_root=Path(args.output_root),
        generated_at=args.generated_at or _now_rfc3339(),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build portable P2 Weekly Organic Report artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="build the bundled sanitized demo without credentials/network")
    demo.add_argument("--output-root", default="artifacts")
    demo.add_argument("--generated-at")

    build = subparsers.add_parser("build", help="build from normalized read-only Webmaster/Metrika evidence files")
    build.add_argument("--webmaster")
    build.add_argument("--metrika")
    build.add_argument("--structures")
    build.add_argument("--project-root", default=".")
    build.add_argument("--project-id")
    build.add_argument("--project-name")
    build.add_argument("--output-root", default="artifacts")
    build.add_argument("--generated-at")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = _run_demo(args) if args.command == "demo" else _run_build(args)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
