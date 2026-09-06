from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import uuid
from typing import Any

from .contracts import (
    FUTURE_SKEW,
    canonical_json_bytes,
    find_secret_like_paths,
    format_rfc3339,
    is_json_compatible,
    parse_rfc3339,
)


BASELINE_SCHEMA = "yandex-ai-baseline/v1"
_KIND_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _validate_kind(kind: str) -> str:
    if not isinstance(kind, str) or not _KIND_RE.fullmatch(kind):
        raise ValueError("baseline kind must match lowercase kebab-case")
    return kind


def baseline_filename(kind: str, captured_at: datetime) -> str:
    kind = _validate_kind(kind)
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("captured_at must be timezone-aware")
    stamp = captured_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    return f"{stamp}--{kind}.json"


def build_baseline(
    *,
    baseline_id: str | None,
    kind: str,
    captured_at: datetime,
    fresh_until: datetime,
    source: str,
    provenance: str,
    data: object,
    artifact_ref: str | None = None,
    artifact_sha256: str | None = None,
) -> dict[str, object]:
    _validate_kind(kind)
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("captured_at must be timezone-aware")
    if fresh_until.tzinfo is None or fresh_until.utcoffset() is None:
        raise ValueError("fresh_until must be timezone-aware")
    record: dict[str, object] = {
        "schema": BASELINE_SCHEMA,
        "baseline_id": baseline_id or f"baseline-{uuid.uuid4().hex}",
        "kind": kind,
        "captured_at": format_rfc3339(captured_at),
        "fresh_until": format_rfc3339(fresh_until),
        "source": source,
        "provenance": provenance,
        "data": data,
    }
    if artifact_ref is not None:
        record["artifact_ref"] = artifact_ref
    if artifact_sha256 is not None:
        record["artifact_sha256"] = artifact_sha256
    return record


def validate_baseline(record: object, *, at: datetime) -> list[str]:
    errors: list[str] = []
    if at.tzinfo is None or at.utcoffset() is None:
        return ["baseline validation time must be timezone-aware"]
    if not isinstance(record, dict):
        return ["baseline must be a JSON object"]
    if record.get("schema") != BASELINE_SCHEMA:
        errors.append(f"baseline.schema must equal {BASELINE_SCHEMA}")
    for key in ("baseline_id", "kind", "source"):
        value = record.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"baseline.{key} must be a non-empty string")
    kind = record.get("kind")
    if isinstance(kind, str):
        try:
            _validate_kind(kind)
        except ValueError as exc:
            errors.append(str(exc))
    if record.get("provenance") not in {"OBSERVED", "DERIVED"}:
        errors.append("baseline.provenance must be OBSERVED or DERIVED")
    if "data" not in record:
        errors.append("baseline.data is required")
    elif not is_json_compatible(record["data"]):
        errors.append("baseline.data must be finite JSON-compatible data")

    captured: datetime | None = None
    fresh: datetime | None = None
    try:
        captured_raw = record.get("captured_at")
        if not isinstance(captured_raw, str):
            raise ValueError("captured_at must be RFC3339")
        captured = parse_rfc3339(captured_raw)
        if captured > at.astimezone(timezone.utc) + FUTURE_SKEW:
            errors.append("baseline.captured_at is materially in the future")
    except ValueError as exc:
        errors.append(f"baseline.captured_at: {exc}")
    try:
        fresh_raw = record.get("fresh_until")
        if not isinstance(fresh_raw, str):
            raise ValueError("fresh_until must be RFC3339")
        fresh = parse_rfc3339(fresh_raw)
    except ValueError as exc:
        errors.append(f"baseline.fresh_until: {exc}")
    if captured is not None and fresh is not None and fresh < captured:
        errors.append("baseline.fresh_until must be greater than or equal to captured_at")

    artifact_ref = record.get("artifact_ref")
    artifact_sha256 = record.get("artifact_sha256")
    if (artifact_ref is None) != (artifact_sha256 is None):
        errors.append("baseline artifact_ref and artifact_sha256 must be provided together")
    if artifact_ref is not None and (not isinstance(artifact_ref, str) or not artifact_ref):
        errors.append("baseline.artifact_ref must be a non-empty string")
    if artifact_sha256 is not None and (
        not isinstance(artifact_sha256, str) or not _HEX64.fullmatch(artifact_sha256)
    ):
        errors.append("baseline.artifact_sha256 must be lowercase SHA-256")

    for secret_path in find_secret_like_paths(record):
        errors.append(f"secret-like field is not allowed in baseline at {secret_path}")
    return errors


def freshness_state(record: dict[str, object], *, at: datetime) -> str:
    raw = record.get("fresh_until")
    if not isinstance(raw, str):
        raise ValueError("baseline fresh_until is missing")
    fresh_until = parse_rfc3339(raw)
    return "FRESH" if at.astimezone(timezone.utc) <= fresh_until else "STALE"


def _baseline_path(memory_root: Path, record: dict[str, object]) -> Path:
    kind = record.get("kind")
    captured_raw = record.get("captured_at")
    if not isinstance(kind, str) or not isinstance(captured_raw, str):
        raise ValueError("baseline kind/captured_at required for path")
    captured = parse_rfc3339(captured_raw)
    return Path(memory_root) / "baselines" / kind / baseline_filename(kind, captured)


def _existing_baseline_ids(memory_root: Path) -> set[str]:
    ids: set[str] = set()
    base = Path(memory_root) / "baselines"
    if not base.is_dir():
        return ids
    for path in sorted(base.rglob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and isinstance(value.get("baseline_id"), str):
            ids.add(value["baseline_id"])
    return ids


def create_baseline(memory_root: Path, record: dict[str, object], *, at: datetime | None = None) -> Path:
    now = at or datetime.now(timezone.utc)
    errors = validate_baseline(record, at=now)
    if errors:
        raise ValueError("invalid baseline: " + "; ".join(errors))
    path = _baseline_path(Path(memory_root), record)
    if path.exists():
        raise FileExistsError(path)
    baseline_id = record.get("baseline_id")
    if baseline_id in _existing_baseline_ids(Path(memory_root)):
        raise ValueError(f"duplicate baseline_id: {baseline_id}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = canonical_json_bytes(record).decode("utf-8") + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    return path


def scan_baselines(
    memory_root: Path, *, at: datetime
) -> tuple[list[dict[str, object]], list[str], list[str]]:
    records: list[dict[str, object]] = []
    errors: list[str] = []
    warnings: list[str] = []
    ids: set[str] = set()
    base = Path(memory_root) / "baselines"
    if not base.is_dir():
        return records, [f"missing baselines directory: {base}"], warnings
    for path in sorted(base.rglob("*.json")):
        rel = path.relative_to(Path(memory_root))
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{rel}: invalid baseline JSON: {exc}")
            continue
        baseline_errors = validate_baseline(value, at=at)
        errors.extend(f"{rel}: {error}" for error in baseline_errors)
        if not isinstance(value, dict):
            continue
        records.append(value)
        baseline_id = value.get("baseline_id")
        if isinstance(baseline_id, str):
            if baseline_id in ids:
                errors.append(f"duplicate baseline_id: {baseline_id}")
            ids.add(baseline_id)
        try:
            expected = _baseline_path(Path(memory_root), value)
        except ValueError as exc:
            errors.append(f"{rel}: cannot derive canonical baseline path: {exc}")
        else:
            if path != expected:
                errors.append(f"{rel}: baseline path is not canonical; expected {expected.relative_to(Path(memory_root))}")
        if not baseline_errors:
            state = freshness_state(value, at=at)
            if state == "STALE":
                warnings.append(f"STALE baseline {rel}")
    return records, errors, warnings
