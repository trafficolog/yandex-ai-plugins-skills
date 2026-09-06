from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from typing import Any


PROJECT_SCHEMA = "yandex-ai-project/v1"
FUTURE_SKEW = timedelta(minutes=5)
_SECRET_TERMS = (
    "authorization",
    "credentials",
    "password",
    "apikey",
    "secret",
    "token",
)


def parse_rfc3339(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp must be a non-empty RFC3339 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"invalid RFC3339 timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("RFC3339 timestamp must include timezone information")
    return parsed.astimezone(timezone.utc)


def format_rfc3339(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_compatible(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_json_compatible(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _json_compatible(item) for key, item in value.items())
    return False


def normalize_field_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _is_secret_like_key(name: str) -> bool:
    normalized = normalize_field_name(name)
    return any(term in normalized for term in _SECRET_TERMS)


def find_secret_like_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            if isinstance(key, str) and _is_secret_like_key(key):
                found.append(child_path)
            found.extend(find_secret_like_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_secret_like_paths(child, f"{path}[{index}]"))
    return found


def _require_string(mapping: dict[str, Any], key: str, where: str, errors: list[str]) -> str | None:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        errors.append(f"{where}.{key} must be a non-empty string")
        return None
    return value


def _check_event_time(raw: Any, *, where: str, at: datetime, errors: list[str]) -> datetime | None:
    if not isinstance(raw, str):
        errors.append(f"{where} must be an RFC3339 string")
        return None
    try:
        parsed = parse_rfc3339(raw)
    except ValueError as exc:
        errors.append(f"{where}: {exc}")
        return None
    if parsed > at.astimezone(timezone.utc) + FUTURE_SKEW:
        errors.append(f"{where} is materially in the future")
    return parsed


def validate_project(doc: object, *, at: datetime) -> list[str]:
    errors: list[str] = []
    if at.tzinfo is None or at.utcoffset() is None:
        return ["validation time must be timezone-aware"]
    if not isinstance(doc, dict):
        return ["project document must be a mapping"]
    if doc.get("schema") != PROJECT_SCHEMA:
        errors.append(f"schema must equal {PROJECT_SCHEMA!r}")

    project = doc.get("project")
    if not isinstance(project, dict):
        errors.append("project must be a mapping")
    else:
        _require_string(project, "id", "project", errors)
        _require_string(project, "name", "project", errors)
        _check_event_time(project.get("created_at"), where="project.created_at", at=at, errors=errors)

    facts = doc.get("facts")
    if not isinstance(facts, list):
        errors.append("facts must be a list")
        facts = []

    ids: set[str] = set()
    facts_by_id: dict[str, dict[str, Any]] = {}
    active_by_key: dict[str, list[str]] = {}
    stated_times: dict[str, datetime] = {}
    superseded_ids: set[str] = set()
    superseders: dict[str, list[str]] = {}

    for index, fact in enumerate(facts):
        where = f"facts[{index}]"
        if not isinstance(fact, dict):
            errors.append(f"{where} must be a mapping")
            continue
        fact_id = _require_string(fact, "fact_id", where, errors)
        key = _require_string(fact, "key", where, errors)
        if fact_id:
            if fact_id in ids:
                errors.append(f"duplicate fact_id: {fact_id}")
            else:
                ids.add(fact_id)
                facts_by_id[fact_id] = fact
        if "value" not in fact:
            errors.append(f"{where}.value is required")
        elif not _json_compatible(fact["value"]):
            errors.append(f"{where}.value must be JSON-compatible")

        stated = _check_event_time(fact.get("stated_at"), where=f"{where}.stated_at", at=at, errors=errors)
        if fact_id and stated is not None:
            stated_times[fact_id] = stated

        if fact.get("provenance") != "USER_STATED":
            errors.append(f"{where}.provenance must equal USER_STATED")
        status = fact.get("status")
        if status not in {"ACTIVE", "SUPERSEDED"}:
            errors.append(f"{where}.status must be ACTIVE or SUPERSEDED")
        if status == "ACTIVE" and key:
            active_by_key.setdefault(key, []).append(fact_id or where)
        if status == "SUPERSEDED" and fact_id:
            superseded_ids.add(fact_id)

        supersedes = fact.get("supersedes")
        if supersedes is not None:
            if not isinstance(supersedes, str) or not supersedes:
                errors.append(f"{where}.supersedes must be a non-empty fact_id")
            elif fact_id:
                superseders.setdefault(supersedes, []).append(fact_id)

    for key, fact_ids in active_by_key.items():
        if len(fact_ids) > 1:
            errors.append(f"multiple ACTIVE facts for key {key!r}: {', '.join(fact_ids)}")

    for old_id, replacement_ids in superseders.items():
        old = facts_by_id.get(old_id)
        if old is None:
            errors.append(f"supersedes references unknown fact_id {old_id!r}")
            continue
        if old.get("status") != "SUPERSEDED":
            errors.append(f"supersedes target {old_id!r} must have status SUPERSEDED")
        if len(replacement_ids) > 1:
            errors.append(f"SUPERSEDED fact {old_id!r} has multiple replacements")
        for replacement_id in replacement_ids:
            replacement = facts_by_id.get(replacement_id)
            if replacement is None:
                continue
            if replacement.get("status") != "ACTIVE":
                errors.append(f"replacement fact {replacement_id!r} must be ACTIVE")
            if replacement.get("key") != old.get("key"):
                errors.append(f"replacement fact {replacement_id!r} must keep the same key as {old_id!r}")
            old_time = stated_times.get(old_id)
            new_time = stated_times.get(replacement_id)
            if old_time is not None and new_time is not None and new_time < old_time:
                errors.append(f"replacement fact {replacement_id!r} cannot predate {old_id!r}")

    for old_id in sorted(superseded_ids):
        if old_id not in superseders:
            errors.append(f"SUPERSEDED fact {old_id!r} must be referenced by one replacement")

    for secret_path in find_secret_like_paths(doc):
        errors.append(f"secret-like field is not allowed at {secret_path}")

    return errors
