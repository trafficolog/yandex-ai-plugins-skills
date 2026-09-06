from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

from project_memory.baselines import build_baseline, create_baseline, scan_baselines
from project_memory.contracts import (
    PROJECT_SCHEMA,
    format_rfc3339,
    parse_rfc3339,
    validate_project,
)
from project_memory.decisions import record_execution, validate_decision_chain
from project_memory.storage import atomic_write_text
from project_memory.yaml_subset import YamlSubsetError, dumps as yaml_dumps, loads as yaml_loads


class ProjectMemoryError(ValueError):
    pass


def _memory_root(root: Path) -> Path:
    return root / ".yandex-ai"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_project(root: Path) -> tuple[Path, dict[str, object]]:
    memory = _memory_root(root)
    project_path = memory / "project.yaml"
    if not project_path.is_file():
        raise ProjectMemoryError(f"missing managed project file: {project_path}")
    try:
        parsed = yaml_loads(project_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, YamlSubsetError) as exc:
        raise ProjectMemoryError(f"cannot read project.yaml: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ProjectMemoryError("project.yaml root must be a mapping")
    return project_path, parsed


def _validate_scaffold(root: Path, *, at: datetime) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    memory = _memory_root(root)
    required_files = ("project.yaml", "decisions.jsonl", "hypotheses.md")
    for name in required_files:
        if not (memory / name).is_file():
            errors.append(f"missing managed file: .yandex-ai/{name}")
    if not (memory / "baselines").is_dir():
        errors.append("missing managed directory: .yandex-ai/baselines")
    if errors:
        return errors, warnings
    try:
        _, doc = _load_project(root)
    except ProjectMemoryError as exc:
        errors.append(str(exc))
        return errors, warnings
    errors.extend(validate_project(doc, at=at))
    _, decision_errors = validate_decision_chain(memory / "decisions.jsonl", at=at)
    errors.extend(decision_errors)
    _, baseline_errors, baseline_warnings = scan_baselines(memory, at=at)
    errors.extend(baseline_errors)
    warnings.extend(baseline_warnings)
    return errors, warnings


def _init(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    memory = _memory_root(root)
    if memory.exists():
        raise ProjectMemoryError(f"managed path already exists: {memory}")

    project_id = args.project_id or root.name
    name = args.name or project_id
    created_at = format_rfc3339(_now())
    doc = {
        "schema": PROJECT_SCHEMA,
        "project": {"id": project_id, "name": name, "created_at": created_at},
        "facts": [],
    }
    validation = validate_project(doc, at=_now())
    if validation:
        raise ProjectMemoryError("invalid initial project: " + "; ".join(validation))

    temp_path: Path | None = Path(tempfile.mkdtemp(prefix=".yandex-ai.tmp-", dir=root))
    try:
        (temp_path / "baselines").mkdir()
        (temp_path / "project.yaml").write_text(yaml_dumps(doc), encoding="utf-8")
        (temp_path / "decisions.jsonl").write_text("", encoding="utf-8")
        (temp_path / "hypotheses.md").write_text("# Project hypotheses\n\n", encoding="utf-8")
        if memory.exists():
            raise ProjectMemoryError(f"managed path appeared during initialization: {memory}")
        os.rename(temp_path, memory)
        temp_path = None
    finally:
        if temp_path is not None and temp_path.exists():
            shutil.rmtree(temp_path, ignore_errors=True)
    print(f"initialized {memory}")
    return 0


def _check(args: argparse.Namespace) -> int:
    try:
        at = parse_rfc3339(args.at) if args.at else _now()
    except ValueError as exc:
        raise ProjectMemoryError(str(exc)) from exc
    errors, warnings = _validate_scaffold(Path(args.root).resolve(), at=at)
    payload = {"ok": not errors, "errors": errors, "warnings": warnings}
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        if not errors:
            print("project memory check passed")
    return 0 if not errors else 1


def _parse_json_value(raw: str) -> object:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProjectMemoryError(f"--value must be strict JSON: {exc.msg}") from exc


def _write_valid_project(project_path: Path, doc: dict[str, object], *, at: datetime) -> None:
    errors = validate_project(doc, at=at)
    if errors:
        raise ProjectMemoryError("project mutation rejected: " + "; ".join(errors))
    atomic_write_text(project_path, yaml_dumps(doc))


def _add_fact(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    project_path, doc = _load_project(root)
    now = _now()
    before = validate_project(doc, at=now)
    if before:
        raise ProjectMemoryError("existing project is invalid: " + "; ".join(before))
    facts = doc.get("facts")
    if not isinstance(facts, list):
        raise ProjectMemoryError("facts must be a list")
    if any(isinstance(f, dict) and f.get("status") == "ACTIVE" and f.get("key") == args.key for f in facts):
        raise ProjectMemoryError(f"an ACTIVE fact already exists for key {args.key!r}; use supersede-fact")
    fact_id = args.fact_id or f"fact-{uuid.uuid4().hex}"
    if any(isinstance(f, dict) and f.get("fact_id") == fact_id for f in facts):
        raise ProjectMemoryError(f"duplicate fact_id: {fact_id}")
    try:
        stated = parse_rfc3339(args.stated_at)
    except ValueError as exc:
        raise ProjectMemoryError(str(exc)) from exc
    fact = {
        "fact_id": fact_id,
        "key": args.key,
        "value": _parse_json_value(args.value),
        "stated_at": format_rfc3339(stated),
        "provenance": "USER_STATED",
        "status": "ACTIVE",
    }
    facts.append(fact)
    _write_valid_project(project_path, doc, at=now)
    print(fact_id)
    return 0


def _supersede_fact(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    project_path, doc = _load_project(root)
    now = _now()
    before = validate_project(doc, at=now)
    if before:
        raise ProjectMemoryError("existing project is invalid: " + "; ".join(before))
    facts = doc.get("facts")
    if not isinstance(facts, list):
        raise ProjectMemoryError("facts must be a list")
    old = next(
        (
            fact
            for fact in facts
            if isinstance(fact, dict)
            and fact.get("fact_id") == args.fact_id
            and fact.get("status") == "ACTIVE"
        ),
        None,
    )
    if old is None:
        raise ProjectMemoryError(f"ACTIVE fact not found: {args.fact_id}")
    if old.get("key") != args.key:
        raise ProjectMemoryError("supersede-fact must keep the original fact key")
    try:
        stated = parse_rfc3339(args.stated_at)
    except ValueError as exc:
        raise ProjectMemoryError(str(exc)) from exc
    replacement_value = _parse_json_value(args.value)
    old["status"] = "SUPERSEDED"
    new_id = f"fact-{uuid.uuid4().hex}"
    facts.append(
        {
            "fact_id": new_id,
            "key": args.key,
            "value": replacement_value,
            "stated_at": format_rfc3339(stated),
            "provenance": "USER_STATED",
            "status": "ACTIVE",
            "supersedes": args.fact_id,
        }
    )
    _write_valid_project(project_path, doc, at=now)
    print(new_id)
    return 0


def _read_receipt(source: str) -> dict[str, object]:
    try:
        text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
        value = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectMemoryError(f"cannot read execution receipt JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ProjectMemoryError("execution receipt must be a JSON object")
    return value


def _record_execution(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    memory = _memory_root(root)
    if not memory.is_dir():
        raise ProjectMemoryError(f"project memory is not initialized: {memory}")
    source = _read_receipt(args.receipt)
    try:
        record = record_execution(memory, source, now=_now())
    except ValueError as exc:
        raise ProjectMemoryError(str(exc)) from exc
    print(record["record_id"])
    return 0


def _read_json_file(path: str, *, label: str) -> object:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectMemoryError(f"cannot read {label} JSON: {exc}") from exc


def _add_baseline(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    memory = _memory_root(root)
    if not memory.is_dir():
        raise ProjectMemoryError(f"project memory is not initialized: {memory}")
    try:
        captured = parse_rfc3339(args.captured_at)
        fresh_until = parse_rfc3339(args.fresh_until)
    except ValueError as exc:
        raise ProjectMemoryError(str(exc)) from exc
    data = _read_json_file(args.input, label="baseline input")
    record = build_baseline(
        baseline_id=args.baseline_id,
        kind=args.kind,
        captured_at=captured,
        fresh_until=fresh_until,
        source=args.source,
        provenance=args.provenance,
        data=data,
        artifact_ref=args.artifact_ref,
        artifact_sha256=args.artifact_sha256,
    )
    try:
        path = create_baseline(memory, record, at=_now())
    except (ValueError, FileExistsError) as exc:
        raise ProjectMemoryError(str(exc)) from exc
    print(path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ya-project")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--root", default=".")
    init_parser.add_argument("--project-id")
    init_parser.add_argument("--name")
    init_parser.set_defaults(handler=_init)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--root", default=".")
    check_parser.add_argument("--at")
    check_parser.add_argument("--json", action="store_true", dest="json_output")
    check_parser.set_defaults(handler=_check)

    add_parser = subparsers.add_parser("add-fact")
    add_parser.add_argument("--root", default=".")
    add_parser.add_argument("--fact-id")
    add_parser.add_argument("--key", required=True)
    add_parser.add_argument("--value", required=True)
    add_parser.add_argument("--stated-at", required=True)
    add_parser.set_defaults(handler=_add_fact)

    supersede_parser = subparsers.add_parser("supersede-fact")
    supersede_parser.add_argument("--root", default=".")
    supersede_parser.add_argument("--fact-id", required=True)
    supersede_parser.add_argument("--key", required=True)
    supersede_parser.add_argument("--value", required=True)
    supersede_parser.add_argument("--stated-at", required=True)
    supersede_parser.set_defaults(handler=_supersede_fact)

    record_parser = subparsers.add_parser("record-execution")
    record_parser.add_argument("receipt")
    record_parser.add_argument("--root", default=".")
    record_parser.set_defaults(handler=_record_execution)

    baseline_parser = subparsers.add_parser("add-baseline")
    baseline_parser.add_argument("--root", default=".")
    baseline_parser.add_argument("--baseline-id")
    baseline_parser.add_argument("--kind", required=True)
    baseline_parser.add_argument("--captured-at", required=True)
    baseline_parser.add_argument("--fresh-until", required=True)
    baseline_parser.add_argument("--source", required=True)
    baseline_parser.add_argument("--provenance", choices=("OBSERVED", "DERIVED"), default="OBSERVED")
    baseline_parser.add_argument("--input", required=True)
    baseline_parser.add_argument("--artifact-ref")
    baseline_parser.add_argument("--artifact-sha256")
    baseline_parser.set_defaults(handler=_add_baseline)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (ProjectMemoryError, YamlSubsetError, OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
