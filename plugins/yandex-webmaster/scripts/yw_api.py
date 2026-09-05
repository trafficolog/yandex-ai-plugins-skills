from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from typing import Any, Callable
from urllib.parse import urlencode, urlsplit, urlunsplit

try:
    from . import _safety
    from ._approval import preview_id, require_approval
    from ._http import auth_headers, redact_headers, request_json
except ImportError:
    import _safety
    from _approval import preview_id, require_approval
    from _http import auth_headers, redact_headers, request_json

API_ROOT = "https://api.webmaster.yandex.net"
ALLOWED_VERSIONS = {"v4", "v4.1"}
READ_METHODS = {"GET", "HEAD", "OPTIONS"}
BASIC_AUTH_BINDING_DOMAIN = b"yandex-webmaster-basic-auth/v1\0"
AUTH_PRINCIPAL_DOMAIN = b"yandex-webmaster-auth-principal/v2"


def api_url(path: str, *, params: dict[str, Any] | None = None, version: str = "v4") -> str:
    if version not in ALLOWED_VERSIONS:
        raise ValueError(f"Unsupported Yandex Webmaster API version: {version}")
    clean = path.strip("/")
    url = f"{API_ROOT}/{version}/{clean}"
    if params:
        url += "?" + urlencode(params, doseq=True)
    return url


def is_consequential(method: str) -> bool:
    return method.upper() not in READ_METHODS


def webmaster_cardinality(path: str, body: Any | None) -> dict[str, object]:
    normalized = path.strip("/")
    if (
        normalized.endswith("/feeds/batch/add")
        and isinstance(body, dict)
        and isinstance(body.get("feeds"), list)
    ):
        return _safety.known_cardinality(len(body["feeds"]))
    if (
        normalized.endswith("/feeds/batch/remove")
        and isinstance(body, dict)
        and isinstance(body.get("urls"), list)
    ):
        return _safety.known_cardinality(len(body["urls"]))
    if normalized.endswith("/recrawl/queue"):
        return _safety.known_cardinality(1)
    if normalized.endswith("/user-added-sitemaps"):
        return _safety.known_cardinality(1)
    if "/user-added-sitemaps/" in normalized:
        return _safety.known_cardinality(1)
    if normalized.endswith("/recrawl"):
        return _safety.known_cardinality(1)
    if normalized.endswith("/feeds/add/start"):
        return _safety.known_cardinality(1)
    if normalized.endswith("/indexing/archive"):
        return _safety.known_cardinality(1)
    return _safety.unknown_cardinality()


def redact_url_credentials(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if not parsed.scheme or not parsed.hostname or (parsed.username is None and parsed.password is None):
        return value
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    netloc = f"***:***@{host}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _approval_url_credentials(value: str, *, token: str | None) -> str:
    """Bind URL credentials with an OAuth-keyed HMAC without exposing a password verifier."""
    try:
        parsed = urlsplit(value)
    except ValueError:
        return value
    if not parsed.scheme or not parsed.hostname or (parsed.username is None and parsed.password is None):
        return value
    if not token:
        raise ValueError("OAuth token is required to safely bind embedded URL credentials")
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    username = parsed.username or ""
    password = parsed.password or ""
    credential_binding = hmac.new(
        token.encode("utf-8"),
        BASIC_AUTH_BINDING_DOMAIN + f"{username}\0{password}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    netloc = f"credential-hmac-sha256:{credential_binding}@{host}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _redact_preview_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_url_credentials(value)
    if isinstance(value, list):
        return [_redact_preview_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_preview_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _redact_preview_value(item) for key, item in value.items()}
    return value


def _approval_value(value: Any, *, token: str | None) -> Any:
    if isinstance(value, str):
        return _approval_url_credentials(value, token=token)
    if isinstance(value, list):
        return [_approval_value(item, token=token) for item in value]
    if isinstance(value, tuple):
        return [_approval_value(item, token=token) for item in value]
    if isinstance(value, dict):
        return {key: _approval_value(item, token=token) for key, item in value.items()}
    return value


def approval_envelope(
    *,
    method: str,
    path: str,
    token: str,
    params: dict[str, Any] | None = None,
    body: Any | None = None,
    version: str = "v4",
) -> dict[str, Any]:
    normalized_method = method.upper()
    normalized_path = path.strip("/")
    safe_params = _approval_value(params or {}, token=token)
    safe_body = _approval_value(body, token=token)
    cardinality = webmaster_cardinality(normalized_path, body)
    safety = {
        "verification": "RESPONSE_ONLY",
        "rollback": "NOT_AVAILABLE",
        "risk_flags": [],
    }
    return {
        "schema": _safety.APPROVAL_SCHEMA,
        "plugin": "yandex-webmaster",
        "operation": f"api.{normalized_method.lower()}.{normalized_path}",
        "request": {
            "method": normalized_method,
            "environment": "production",
            "api_version": version,
            "url": api_url(path, params=safe_params or None, version=version),
            "path": normalized_path,
            "query": safe_params,
            "body": safe_body,
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
    params: dict[str, Any] | None = None,
    body: Any | None = None,
    version: str = "v4",
) -> dict[str, Any]:
    envelope = approval_envelope(
        method=method,
        path=path,
        token=token,
        params=params,
        body=body,
        version=version,
    )
    safe_preview_params = _redact_preview_value(params or {})
    result = {
        "method": method.upper(),
        "url": api_url(path, params=safe_preview_params or None, version=version),
        "headers": redact_headers(auth_headers(token)),
        "body": _redact_preview_value(body),
        "consequential": is_consequential(method),
        "version": version,
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


def run_request(
    *,
    method: str,
    path: str,
    token: str,
    params: dict[str, Any] | None = None,
    body: Any | None = None,
    version: str = "v4",
    execute: bool = False,
    approve: str | None = None,
    ack_bulk: bool = False,
    transport: Callable[..., Any] | None = None,
) -> Any:
    preview = prepare_request(
        method=method,
        path=path,
        token=token,
        params=params,
        body=body,
        version=version,
    )
    consequential = is_consequential(method)
    if consequential and not execute:
        return {"dry_run": True, **preview}

    envelope = approval_envelope(
        method=method,
        path=path,
        token=token,
        params=params,
        body=body,
        version=version,
    )
    approved_preview: str | None = None
    if consequential:
        approved_preview = require_approval(envelope, approve)
        _safety.require_bulk_ack(envelope["cardinality"], ack_bulk)

    url = api_url(path, params=params, version=version)
    if transport is not None:
        payload = transport(method=method.upper(), url=url, token=token, body=body)
    else:
        _, payload = request_json(method, url, token, body=body)

    if not consequential:
        return payload
    return _safety.execution_receipt(
        preview_id=approved_preview or "",
        plugin="yandex-webmaster",
        operation=envelope["operation"],
        target=envelope["target"],
        cardinality=envelope["cardinality"],
        result=payload,
        verification_capability="RESPONSE_ONLY",
        verification_state="UNVERIFIED",
        rollback_capability="NOT_AVAILABLE",
    )


def _json_arg(value: str | None) -> Any | None:
    return None if value is None else json.loads(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Yandex Webmaster API helper")
    parser.add_argument("path")
    parser.add_argument("--method", default="GET")
    parser.add_argument("--version", choices=sorted(ALLOWED_VERSIONS), default="v4")
    parser.add_argument("--params", help="JSON object with query parameters")
    parser.add_argument("--body", help="JSON request body")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approve", help="Exact preview_id for the consequential operation")
    parser.add_argument(
        "--ack-bulk",
        action="store_true",
        help="Acknowledge bulk or unknown operation scale after reviewing the exact preview",
    )
    args = parser.parse_args(argv)
    token = os.environ.get("YANDEX_WEBMASTER_TOKEN", "")
    payload = run_request(
        method=args.method,
        path=args.path,
        token=token,
        params=_json_arg(args.params),
        body=_json_arg(args.body),
        version=args.version,
        execute=args.execute,
        approve=args.approve,
        ack_bulk=args.ack_bulk,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
