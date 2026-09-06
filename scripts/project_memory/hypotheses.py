from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from .contracts import FUTURE_SKEW, find_secret_like_paths, parse_rfc3339


HYPOTHESIS_SCHEMA = "yandex-ai-hypothesis/v1"
MANAGED_FENCE = f"```json {HYPOTHESIS_SCHEMA}"
_ALLOWED_PROVENANCE = {"HYPOTHESIS", "DERIVED"}
_ALLOWED_STATUS = {"OPEN", "VALIDATED", "REJECTED", "CLOSED"}


def extract_hypothesis_records(markdown: str) -> list[dict[str, object]]:
    if not isinstance(markdown, str):
        raise ValueError("hypotheses markdown must be text")

    records: list[dict[str, object]] = []
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        if lines[index].strip() != MANAGED_FENCE:
            index += 1
            continue

        start_line = index + 1
        index += 1
        payload_lines: list[str] = []
        while index < len(lines) and lines[index].strip() != "```":
            payload_lines.append(lines[index])
            index += 1
        if index >= len(lines):
            raise ValueError(f"unterminated managed hypothesis fence starting at line {start_line}")

        payload = "\n".join(payload_lines).strip()
        if not payload:
            raise ValueError(f"empty managed hypothesis fence starting at line {start_line}")
        try:
            record = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"malformed managed hypothesis JSON at line {start_line}: {exc.msg}"
            ) from exc
        if not isinstance(record, dict):
            raise ValueError(f"managed hypothesis record at line {start_line} must be a JSON object")
        records.append(record)
        index += 1

    return records


def _require_nonempty_string(
    record: dict[str, Any], key: str, errors: list[str]
) -> str | None:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        errors.append(f"{key} must be a non-empty string")
        return None
    return value


def validate_hypothesis(record: object, *, at: datetime) -> list[str]:
    errors: list[str] = []
    if at.tzinfo is None or at.utcoffset() is None:
        return ["validation time must be timezone-aware"]
    if not isinstance(record, dict):
        return ["hypothesis record must be a mapping"]

    if record.get("schema") != HYPOTHESIS_SCHEMA:
        errors.append(f"schema must equal {HYPOTHESIS_SCHEMA!r}")
    _require_nonempty_string(record, "hypothesis_id", errors)
    _require_nonempty_string(record, "statement", errors)
    _require_nonempty_string(record, "validation_condition", errors)

    provenance = record.get("provenance")
    if provenance not in _ALLOWED_PROVENANCE:
        errors.append("provenance must be HYPOTHESIS or DERIVED")

    status = record.get("status")
    if status not in _ALLOWED_STATUS:
        errors.append("status must be OPEN, VALIDATED, REJECTED, or CLOSED")

    evidence_refs = record.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        errors.append("evidence_refs must be a list")
    elif any(not isinstance(item, str) or not item for item in evidence_refs):
        errors.append("evidence_refs must contain only non-empty strings")

    created_at = record.get("created_at")
    if not isinstance(created_at, str):
        errors.append("created_at must be an RFC3339 string")
    else:
        try:
            parsed = parse_rfc3339(created_at)
        except ValueError as exc:
            errors.append(f"created_at: {exc}")
        else:
            if parsed > at.astimezone(timezone.utc) + FUTURE_SKEW:
                errors.append("created_at is materially in the future")

    for secret_path in find_secret_like_paths(record):
        errors.append(f"secret-like field is not allowed at {secret_path}")

    return errors
