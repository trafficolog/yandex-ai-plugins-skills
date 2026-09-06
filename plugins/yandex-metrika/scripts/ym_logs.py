from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from . import _safety
    from ._approval import preview_id, require_approval
    from ._http import oauth_headers, redact_headers, request_json
except ImportError:
    import _safety
    from _approval import preview_id, require_approval
    from _http import oauth_headers, redact_headers, request_json

BASE = "https://api-metrika.yandex.net/management/v1"
CONSEQUENTIAL_ACTIONS = {"create", "clean"}
AUTH_PRINCIPAL_DOMAIN = b"yandex-metrika-auth-principal/v2"


def _anniversary(day: date) -> date:
    try:
        return day.replace(year=day.year + 1)
    except ValueError:  # Feb 29 -> Feb 28 next year
        return day.replace(year=day.year + 1, day=28)


def validate_period(date1: str, date2: str, *, today: date | None = None) -> tuple[date, date]:
    start = date.fromisoformat(date1)
    end = date.fromisoformat(date2)
    if end < start:
        raise ValueError("Logs date2 must be on or after date1")
    today = today or date.today()
    if end >= today:
        raise ValueError("Logs date2 must be earlier than the current day")
    if end > _anniversary(start):
        raise ValueError("A Yandex Metrika Logs request cannot exceed one year")
    return start, end


def logs_endpoint(
    counter_id: int,
    action: str,
    *,
    request_id: int | None = None,
    part_number: int | None = None,
) -> str:
    prefix = f"{BASE}/counter/{int(counter_id)}"
    if action == "evaluate":
        return f"{prefix}/logrequests/evaluate"
    if action == "create":
        return f"{prefix}/logrequests"
    if request_id is None:
        raise ValueError(f"request_id is required for Logs action '{action}'")
    if action == "status":
        return f"{prefix}/logrequest/{int(request_id)}"
    if action == "clean":
        return f"{prefix}/logrequest/{int(request_id)}/clean"
    if action == "download":
        if part_number is None:
            raise ValueError("part_number is required for Logs download")
        return f"{prefix}/logrequest/{int(request_id)}/part/{int(part_number)}/download"
    raise ValueError(f"Unknown Logs action: {action}")


def _query_url(url: str, query: dict[str, Any] | None) -> str:
    if not query:
        return url
    normalized = {k: v for k, v in query.items() if v is not None}
    return url + "?" + urlencode(normalized)


def logs_approval_envelope(
    counter_id: int,
    action: str,
    *,
    token: str,
    request_id: int | None = None,
    part_number: int | None = None,
    query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    method = "POST" if action in CONSEQUENTIAL_ACTIONS else "GET"
    url = _query_url(
        logs_endpoint(counter_id, action, request_id=request_id, part_number=part_number),
        query,
    )
    cardinality = _safety.known_cardinality(1)
    safety = {
        "verification": "RESPONSE_ONLY",
        "rollback": "NOT_AVAILABLE",
        "risk_flags": [],
    }
    return {
        "schema": _safety.APPROVAL_SCHEMA,
        "plugin": "yandex-metrika",
        "operation": f"logs.{action}",
        "request": {
            "method": method,
            "environment": "production",
            "api_version": "management/v1",
            "url": url,
            "path": url.split("/management/v1/", 1)[-1].split("?", 1)[0],
            "query": dict(query or {}),
            "body": None,
        },
        "target": {
            "counter_id": int(counter_id),
            "action": action,
            "request_id": request_id,
            "part_number": part_number,
            "auth_principal_binding": _safety.principal_binding(
                token, domain=AUTH_PRINCIPAL_DOMAIN
            ),
        },
        "artifacts": [],
        "cardinality": cardinality,
        "safety": safety,
    }


def prepare_logs_request(
    counter_id: int,
    action: str,
    *,
    token: str,
    request_id: int | None = None,
    part_number: int | None = None,
    query: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if action in {"evaluate", "create"} and query:
        if query.get("date1") and query.get("date2"):
            validate_period(str(query["date1"]), str(query["date2"]))
    envelope = logs_approval_envelope(
        counter_id,
        action,
        token=token,
        request_id=request_id,
        part_number=part_number,
        query=query,
    )
    result = {
        "method": envelope["request"]["method"],
        "url": envelope["request"]["url"],
        "headers": redact_headers(oauth_headers(token, content_type="")),
        "consequential": action in CONSEQUENTIAL_ACTIONS,
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


def execute_json_action(
    counter_id: int,
    action: str,
    *,
    token: str,
    request_id: int | None = None,
    query: dict[str, Any] | None = None,
    approve: str | None = None,
) -> Any:
    envelope = logs_approval_envelope(
        counter_id,
        action,
        token=token,
        request_id=request_id,
        query=query,
    )
    approved_preview: str | None = None
    consequential = action in CONSEQUENTIAL_ACTIONS
    if consequential:
        approved_preview = require_approval(envelope, approve)
    _, payload = request_json(
        envelope["request"]["method"], envelope["request"]["url"], token
    )
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


def run_json_action(
    counter_id: int,
    action: str,
    *,
    token: str,
    request_id: int | None = None,
    query: dict[str, Any] | None = None,
    execute: bool = False,
    approve: str | None = None,
) -> Any:
    preview = prepare_logs_request(
        counter_id,
        action,
        token=token,
        request_id=request_id,
        query=query,
    )
    if preview["consequential"] and not execute:
        return {"dry_run": True, **preview}
    return execute_json_action(
        counter_id,
        action,
        token=token,
        request_id=request_id,
        query=query,
        approve=approve,
    )


def download_part(
    counter_id: int,
    request_id: int,
    part_number: int,
    token: str,
    output: Path,
    *,
    timeout: int = 60,
    opener: Callable[..., Any] = urlopen,
) -> Path:
    url = logs_endpoint(counter_id, "download", request_id=request_id, part_number=part_number)
    request = Request(url, headers=oauth_headers(token, content_type=""), method="GET")
    with opener(request, timeout=timeout) as response:
        data = response.read()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Yandex Metrika Logs API helper")
    parser.add_argument("action", choices=["evaluate", "create", "status", "download", "clean"])
    parser.add_argument("counter", type=int)
    parser.add_argument("--request-id", type=int)
    parser.add_argument("--part-number", type=int)
    parser.add_argument("--date1")
    parser.add_argument("--date2")
    parser.add_argument("--fields")
    parser.add_argument("--source", choices=["hits", "visits"])
    parser.add_argument("--attribution")
    parser.add_argument("--output")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approve", help="Full preview_id for the exact consequential preview")
    args = parser.parse_args(argv)

    token = os.environ.get("YANDEX_METRIKA_TOKEN", "")
    query = None
    if args.action in {"evaluate", "create"}:
        if not all([args.date1, args.date2, args.fields, args.source]):
            parser.error("evaluate/create require --date1 --date2 --fields --source")
        validate_period(args.date1, args.date2)
        query = {
            "date1": args.date1,
            "date2": args.date2,
            "fields": args.fields,
            "source": args.source,
            "attribution": args.attribution if args.action == "create" else None,
        }

    if args.action == "download":
        if args.request_id is None or args.part_number is None or not args.output:
            parser.error("download requires --request-id --part-number --output")
        path = download_part(args.counter, args.request_id, args.part_number, token, Path(args.output))
        print(json.dumps({"output": str(path)}, ensure_ascii=False))
        return 0

    payload = run_json_action(
        args.counter,
        args.action,
        token=token,
        request_id=args.request_id,
        query=query,
        execute=args.execute,
        approve=args.approve,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
