from __future__ import annotations

import argparse
import json
import os
from typing import Any
from urllib.parse import urlencode

try:
    from . import _safety
    from ._approval import preview_id, require_approval
    from ._http import oauth_headers, redact_headers, request_json
except ImportError:  # CLI execution from scripts directory
    import _safety
    from _approval import preview_id, require_approval
    from _http import oauth_headers, redact_headers, request_json

MANAGEMENT_BASE = "https://api-metrika.yandex.net/management/v1"
READ_METHODS = {"GET", "HEAD", "OPTIONS"}
AUTH_PRINCIPAL_DOMAIN = b"yandex-metrika-auth-principal/v2"


def build_management_url(path: str, query: dict[str, Any] | None = None) -> str:
    clean = path.strip("/")
    url = f"{MANAGEMENT_BASE}/{clean}"
    if query:
        url += "?" + urlencode(query, doseq=True)
    return url


def is_consequential(method: str) -> bool:
    return method.upper() not in READ_METHODS


def approval_envelope(
    *,
    method: str,
    path: str,
    token: str,
    query: dict[str, Any] | None = None,
    body: Any | None = None,
) -> dict[str, Any]:
    normalized_method = method.upper()
    normalized_path = path.strip("/")
    cardinality = _safety.unknown_cardinality()
    safety = {
        "verification": "RESPONSE_ONLY",
        "rollback": "NOT_AVAILABLE",
        "risk_flags": [],
    }
    return {
        "schema": _safety.APPROVAL_SCHEMA,
        "plugin": "yandex-metrika",
        "operation": f"management.{normalized_method.lower()}.{normalized_path}",
        "request": {
            "method": normalized_method,
            "environment": "production",
            "api_version": "management/v1",
            "url": build_management_url(path, query),
            "path": normalized_path,
            "query": dict(query or {}),
            "body": body,
        },
        "target": {
            "path": normalized_path,
            "auth_principal_binding": _safety.principal_binding(
                token, domain=AUTH_PRINCIPAL_DOMAIN
            ),
        },
        "artifacts": [],
        "cardinality": cardinality,
        "safety": safety,
    }


def prepare_request(
    *,
    method: str,
    path: str,
    token: str,
    query: dict[str, Any] | None = None,
    body: Any | None = None,
) -> dict[str, Any]:
    headers = oauth_headers(token)
    envelope = approval_envelope(
        method=method,
        path=path,
        token=token,
        query=query,
        body=body,
    )
    result = {
        "method": method.upper(),
        "url": build_management_url(path, query),
        "headers": redact_headers(headers),
        "body": body,
        "consequential": is_consequential(method),
    }
    if result["consequential"]:
        result.update(
            {
                "approval_schema": envelope["schema"],
                "preview_id": preview_id(envelope),
                "cardinality": envelope["cardinality"],
                "safety": envelope["safety"],
            }
        )
    return result


def execute_request(
    *,
    method: str,
    path: str,
    token: str,
    query: dict[str, Any] | None = None,
    body: Any | None = None,
    approve: str | None = None,
    ack_bulk: bool = False,
) -> Any:
    envelope = approval_envelope(
        method=method,
        path=path,
        token=token,
        query=query,
        body=body,
    )
    approved_preview: str | None = None
    consequential = is_consequential(method)
    if consequential:
        approved_preview = require_approval(envelope, approve)
        _safety.require_bulk_ack(envelope["cardinality"], ack_bulk)
    url = build_management_url(path, query)
    _, payload = request_json(method, url, token, body=body)
    if not consequential:
        return payload
    return _safety.execution_receipt(
        preview_id=approved_preview or "",
        plugin="yandex-metrika",
        operation=envelope["operation"],
        target=envelope["target"],
        cardinality=envelope["cardinality"],
        result=payload,
        verification_capability="RESPONSE_ONLY",
        verification_state="UNVERIFIED",
        rollback_capability="NOT_AVAILABLE",
    )


def run_request(
    *,
    method: str,
    path: str,
    token: str,
    query: dict[str, Any] | None = None,
    body: Any | None = None,
    execute: bool = False,
    approve: str | None = None,
    ack_bulk: bool = False,
) -> Any:
    preview = prepare_request(
        method=method, path=path, token=token, query=query, body=body
    )
    if preview["consequential"] and not execute:
        return {"dry_run": True, **preview}
    return execute_request(
        method=method,
        path=path,
        token=token,
        query=query,
        body=body,
        approve=approve,
        ack_bulk=ack_bulk,
    )


def _json_arg(value: str | None) -> Any | None:
    if value is None:
        return None
    return json.loads(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Yandex Metrika Management API helper")
    parser.add_argument("path")
    parser.add_argument("--method", default="GET")
    parser.add_argument("--query", help="JSON object with query parameters")
    parser.add_argument("--body", help="JSON request body")
    parser.add_argument("--execute", action="store_true", help="Execute consequential writes")
    parser.add_argument("--approve", help="Full preview_id for the exact consequential preview")
    parser.add_argument(
        "--ack-bulk",
        action="store_true",
        help="Acknowledge bulk or unknown operation scale after reviewing the exact preview",
    )
    args = parser.parse_args(argv)

    token = os.environ.get("YANDEX_METRIKA_TOKEN", "")
    query = _json_arg(args.query)
    body = _json_arg(args.body)
    payload = run_request(
        method=args.method,
        path=args.path,
        token=token,
        query=query,
        body=body,
        execute=args.execute,
        approve=args.approve,
        ack_bulk=args.ack_bulk,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
