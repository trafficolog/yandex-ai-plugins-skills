from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import uuid
from typing import Any

from .contracts import (
    FUTURE_SKEW,
    canonical_json_bytes,
    find_secret_like_paths,
    format_rfc3339,
    parse_rfc3339,
    sha256_hex,
    validate_execution_receipt,
)
from .storage import append_durable_line, locked_text_file


DECISION_SCHEMA = "yandex-ai-decision/v1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_RECEIPT_FIELDS = (
    "execution_id",
    "preview_id",
    "plugin",
    "operation",
    "target",
    "cardinality",
    "execution",
    "verification",
    "rollback",
)


def _record_hash(record: dict[str, object]) -> str:
    body = {key: value for key, value in record.items() if key != "record_hash"}
    return sha256_hex(canonical_json_bytes(body))


def safe_execution_projection(
    receipt: dict[str, object],
    *,
    recorded_at: str,
    previous_record_hash: str | None,
    record_id: str,
) -> dict[str, object]:
    errors = validate_execution_receipt(receipt)
    if errors:
        raise ValueError("invalid execution receipt: " + "; ".join(errors))
    parse_rfc3339(recorded_at)
    if not isinstance(record_id, str) or not record_id:
        raise ValueError("record_id must be a non-empty string")
    if previous_record_hash is not None and not _HEX64.fullmatch(previous_record_hash):
        raise ValueError("previous_record_hash must be null or lowercase SHA-256")

    projected: dict[str, object] = {
        "schema": DECISION_SCHEMA,
        "record_id": record_id,
        "recorded_at": recorded_at,
        "kind": "EXECUTION",
    }
    for key in _SAFE_RECEIPT_FIELDS:
        projected[key] = deepcopy(receipt[key])
    projected["receipt_sha256"] = sha256_hex(canonical_json_bytes(receipt))
    projected["previous_record_hash"] = previous_record_hash
    for secret_path in find_secret_like_paths(projected):
        raise ValueError(f"secret-like field is not allowed in decision projection at {secret_path}")
    projected["record_hash"] = _record_hash(projected)
    return projected


def _validate_record(
    record: object,
    *,
    index: int,
    expected_previous: str | None,
    at: datetime,
    seen_record_ids: set[str],
    seen_execution_ids: set[str],
    seen_receipt_hashes: set[str],
) -> list[str]:
    errors: list[str] = []
    where = f"decisions[{index}]"
    if not isinstance(record, dict):
        return [f"{where} must be a JSON object"]
    if record.get("schema") != DECISION_SCHEMA:
        errors.append(f"{where}.schema must equal {DECISION_SCHEMA}")
    if record.get("kind") != "EXECUTION":
        errors.append(f"{where}.kind must equal EXECUTION")
    if "result" in record:
        errors.append(f"{where} must not persist raw execution result")

    for key, seen, label in (
        ("record_id", seen_record_ids, "record_id"),
        ("execution_id", seen_execution_ids, "execution_id"),
        ("receipt_sha256", seen_receipt_hashes, "receipt_sha256"),
    ):
        value = record.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"{where}.{key} must be a non-empty string")
        elif value in seen:
            errors.append(f"duplicate {label}: {value}")
        else:
            seen.add(value)

    for key in ("preview_id", "plugin", "operation"):
        value = record.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f"{where}.{key} must be a non-empty string")
    for key in ("target", "cardinality", "execution", "verification", "rollback"):
        if not isinstance(record.get(key), dict):
            errors.append(f"{where}.{key} must be an object")

    recorded_at = record.get("recorded_at")
    if not isinstance(recorded_at, str):
        errors.append(f"{where}.recorded_at must be RFC3339")
    else:
        try:
            parsed = parse_rfc3339(recorded_at)
        except ValueError as exc:
            errors.append(f"{where}.recorded_at: {exc}")
        else:
            if parsed > at.astimezone(timezone.utc) + FUTURE_SKEW:
                errors.append(f"{where}.recorded_at is materially in the future")

    receipt_hash = record.get("receipt_sha256")
    if isinstance(receipt_hash, str) and not _HEX64.fullmatch(receipt_hash):
        errors.append(f"{where}.receipt_sha256 must be lowercase SHA-256")
    previous = record.get("previous_record_hash")
    if previous != expected_previous:
        errors.append(f"{where}.previous_record_hash does not match prior record_hash")
    record_hash = record.get("record_hash")
    if not isinstance(record_hash, str) or not _HEX64.fullmatch(record_hash):
        errors.append(f"{where}.record_hash must be lowercase SHA-256")
    else:
        try:
            expected_hash = _record_hash(record)
        except ValueError as exc:
            errors.append(f"{where} cannot be canonicalized: {exc}")
        else:
            if record_hash != expected_hash:
                errors.append(f"{where}.record_hash does not match canonical record")

    for secret_path in find_secret_like_paths({key: value for key, value in record.items() if key not in {"receipt_sha256", "record_hash", "previous_record_hash"}}):
        errors.append(f"secret-like field is not allowed in decision at {secret_path}")
    return errors


def _validate_lines(lines: list[str], *, at: datetime) -> tuple[list[dict[str, object]], list[str]]:
    records: list[dict[str, object]] = []
    errors: list[str] = []
    previous_hash: str | None = None
    seen_record_ids: set[str] = set()
    seen_execution_ids: set[str] = set()
    seen_receipt_hashes: set[str] = set()

    for index, line in enumerate(lines):
        if not line:
            errors.append(f"decisions[{index}] is a blank JSONL line")
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"decisions[{index}] invalid JSON: {exc.msg}")
            continue
        if isinstance(record, dict):
            records.append(record)
        record_errors = _validate_record(
            record,
            index=index,
            expected_previous=previous_hash,
            at=at,
            seen_record_ids=seen_record_ids,
            seen_execution_ids=seen_execution_ids,
            seen_receipt_hashes=seen_receipt_hashes,
        )
        errors.extend(record_errors)
        if isinstance(record, dict) and isinstance(record.get("record_hash"), str):
            previous_hash = record["record_hash"]
        else:
            previous_hash = None
    return records, errors


def validate_decision_chain(path: Path, *, at: datetime) -> tuple[list[dict[str, object]], list[str]]:
    path = Path(path)
    if not path.is_file():
        return [], [f"missing decisions file: {path}"]
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [], [f"cannot read decisions file: {exc}"]
    lines = text.splitlines()
    return _validate_lines(lines, at=at)


def record_execution(
    memory_root: Path,
    receipt: dict[str, object],
    *,
    now: datetime,
) -> dict[str, object]:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("recording time must be timezone-aware")
    receipt_errors = validate_execution_receipt(receipt)
    if receipt_errors:
        raise ValueError("invalid execution receipt: " + "; ".join(receipt_errors))
    path = Path(memory_root) / "decisions.jsonl"
    source_hash = sha256_hex(canonical_json_bytes(receipt))

    with locked_text_file(path) as (handle, _lock_capability):
        handle.seek(0)
        text = handle.read()
        records, errors = _validate_lines(text.splitlines(), at=now)
        if errors:
            raise ValueError("existing decision trail is invalid: " + "; ".join(errors))
        if any(record.get("execution_id") == receipt.get("execution_id") for record in records):
            raise ValueError(f"duplicate execution_id: {receipt.get('execution_id')}")
        if any(record.get("receipt_sha256") == source_hash for record in records):
            raise ValueError(f"duplicate receipt_sha256: {source_hash}")
        previous_hash = records[-1].get("record_hash") if records else None
        if previous_hash is not None and not isinstance(previous_hash, str):
            raise ValueError("existing decision tail has invalid record_hash")
        record = safe_execution_projection(
            receipt,
            recorded_at=format_rfc3339(now),
            previous_record_hash=previous_hash,
            record_id=f"decision-{uuid.uuid4().hex}",
        )
        line = canonical_json_bytes(record).decode("utf-8")
        append_durable_line(handle, line)
        return record
