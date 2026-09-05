from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

APPROVAL_SCHEMA = "yandex-ai-approval/v2"
EXECUTION_SCHEMA = "yandex-ai-execution/v1"
BULK_THRESHOLD = 20


def principal_binding(token: str, *, domain: bytes) -> str:
    return hmac.new(token.encode("utf-8"), domain, hashlib.sha256).hexdigest()


def known_cardinality(
    items: int, *, artifact_rows: int | None = None
) -> dict[str, object]:
    if items < 0:
        raise ValueError("cardinality items must be non-negative")
    result: dict[str, object] = {
        "scale": "KNOWN",
        "items": items,
        "threshold": BULK_THRESHOLD,
        "bulk": items > BULK_THRESHOLD,
    }
    if artifact_rows is not None:
        result["artifact_rows"] = artifact_rows
    return result


def unknown_cardinality(*, artifact_rows: int | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "scale": "UNKNOWN",
        "items": None,
        "threshold": BULK_THRESHOLD,
        "bulk": True,
    }
    if artifact_rows is not None:
        result["artifact_rows"] = artifact_rows
    return result


def require_bulk_ack(cardinality: dict[str, object], ack_bulk: bool) -> None:
    if cardinality.get("bulk") is True and not ack_bulk:
        raise ValueError(
            "bulk or unknown-scale execution requires --ack-bulk after reviewing the exact preview"
        )


def execution_receipt(
    *,
    preview_id: str,
    plugin: str,
    operation: str,
    target: dict[str, object],
    cardinality: dict[str, object],
    result: Any,
    verification_capability: str,
    verification_state: str,
    rollback_capability: str,
) -> dict[str, object]:
    return {
        "schema": EXECUTION_SCHEMA,
        "execution_id": secrets.token_hex(16),
        "preview_id": preview_id,
        "plugin": plugin,
        "operation": operation,
        "target": target,
        "cardinality": cardinality,
        "execution": {"state": "EXECUTED"},
        "verification": {
            "capability": verification_capability,
            "state": verification_state,
        },
        "rollback": {
            "capability": rollback_capability,
            "snapshot_available": False,
        },
        "result": result,
    }
