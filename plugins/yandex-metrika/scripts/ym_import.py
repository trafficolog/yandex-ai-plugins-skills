from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from . import _safety
    from ._approval import preview_id, require_approval
    from ._http import oauth_headers, redact_headers
except ImportError:
    import _safety
    from _approval import preview_id, require_approval
    from _http import oauth_headers, redact_headers

BASE = "https://api-metrika.yandex.net/management/v1/counter"
IMPORT_PATHS = {
    "offline-conversions": "offline_conversions/upload",
    "calls": "offline_conversions/upload_calls",
    "expenses": "expense/upload",
}
DIRECT_SOURCE_ALIASES = {
    "direct",
    "директ",
    "yandexdirect",
    "яндексдирект",
    "directyandex",
    "yadirect",
}
DIRECT_SOURCE_TOKENS = {"direct", "директ"}
DIRECT_UTM_SOURCES = {"yandex", "яндекс", "yandexdirect", "яндексдирект", "ya"}
DIRECT_UTM_MEDIA = {"cpc", "ppc", "paidsearch", "context", "контекст"}
DIRECT_TRAFFIC_SOURCE_DETAILS = {"yandexdirectstar"}
AUTH_PRINCIPAL_DOMAIN = b"yandex-metrika-auth-principal/v2"


def _read_file_bytes(path: Path) -> bytes:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_bytes()


def _decode_csv_bytes(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded") from exc


def _inspect_csv_bytes(path: Path, data: bytes) -> dict[str, Any]:
    text = _decode_csv_bytes(data)
    rows = list(csv.reader(text.splitlines()))
    if not rows or not rows[0]:
        raise ValueError("CSV must contain a header row")
    return {
        "rows": max(0, len(rows) - 1),
        "columns": rows[0],
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "encoding": "utf-8",
        "name": Path(path).name,
    }


def inspect_csv(path: Path) -> dict[str, Any]:
    path = Path(path)
    return _inspect_csv_bytes(path, _read_file_bytes(path))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compact_label(value: str) -> str:
    return re.sub(r"[^0-9a-zа-яё]+", "", value.strip().casefold())


def _label_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^0-9a-zа-яё]+", value.strip().casefold())
        if token
    }


def guard_expense_source(source: str | None) -> None:
    if source is None:
        return
    compact = _compact_label(source)
    tokens = _label_tokens(source)
    if compact in DIRECT_SOURCE_ALIASES or tokens & DIRECT_SOURCE_TOKENS:
        raise ValueError(
            "Do not import Yandex Direct expenses into Metrika: Direct cost data is transferred automatically and manual upload can duplicate expenses"
        )


def _classify_expense_bytes(data: bytes) -> str:
    text = _decode_csv_bytes(data)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return "UNVERIFIED"

    normalized_names = {_compact_label(name): name for name in reader.fieldnames if name}
    utm_source_key = normalized_names.get("utmsource")
    utm_medium_key = normalized_names.get("utmmedium")
    traffic_source_key = normalized_names.get("trafficsource")
    traffic_detail_key = normalized_names.get("trafficsourcedetail")

    saw_row = False
    saw_unverified = False
    for row in reader:
        saw_row = True
        utm_source = _compact_label(str(row.get(utm_source_key) or "")) if utm_source_key else ""
        utm_medium = _compact_label(str(row.get(utm_medium_key) or "")) if utm_medium_key else ""
        traffic_source = (
            _compact_label(str(row.get(traffic_source_key) or "")) if traffic_source_key else ""
        )
        traffic_detail = (
            _compact_label(str(row.get(traffic_detail_key) or "")) if traffic_detail_key else ""
        )

        if traffic_detail in DIRECT_TRAFFIC_SOURCE_DETAILS:
            return "DIRECT"
        if utm_source in {"yandexdirect", "яндексдирект"}:
            return "DIRECT"
        if utm_source in DIRECT_UTM_SOURCES and utm_medium in DIRECT_UTM_MEDIA:
            return "DIRECT"

        if traffic_detail:
            continue
        if utm_source:
            if utm_source in DIRECT_UTM_SOURCES and not utm_medium:
                saw_unverified = True
            continue
        if traffic_source:
            if traffic_source == "ad":
                saw_unverified = True
            continue
        saw_unverified = True

    if not saw_row or saw_unverified:
        return "UNVERIFIED"
    return "NON_DIRECT"


def classify_expense_source(path: Path) -> str:
    """Classify expense provenance as DIRECT, NON_DIRECT, or UNVERIFIED."""
    return _classify_expense_bytes(_read_file_bytes(Path(path)))


def detect_direct_expense_risk(path: Path) -> bool:
    """Detect proven Direct expense rows without claiming every ad row is Direct."""
    return classify_expense_source(path) == "DIRECT"


def import_url(kind: str, counter_id: int, query: dict[str, Any] | None = None) -> str:
    try:
        suffix = IMPORT_PATHS[kind]
    except KeyError as exc:
        raise ValueError(f"Unknown import kind: {kind}") from exc
    url = f"{BASE}/{int(counter_id)}/{suffix}"
    if query:
        clean = {k: v for k, v in query.items() if v is not None}
        if clean:
            url += "?" + urlencode(clean)
    return url


def _normalized_import_query(
    kind: str,
    source: str | None,
    query: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(query)
    if kind == "expenses" and source is not None and "provider" not in normalized:
        normalized["provider"] = source
    return normalized


def _expense_warnings(
    kind: str,
    source: str | None,
    allow_direct_risk: bool,
    file_bytes: bytes,
) -> list[str]:
    if kind != "expenses":
        return []

    guard_expense_source(source)
    provenance = _classify_expense_bytes(file_bytes)
    warning: str | None = None
    if provenance == "DIRECT":
        warning = "DIRECT_DUPLICATION_RISK"
        message = (
            f"{warning}: CSV contains Yandex Direct expense provenance. "
            "Metrika receives Yandex Direct costs automatically; inspect the file and "
            "use --allow-direct-risk only after confirming these rows are intentionally uploaded."
        )
    elif provenance == "UNVERIFIED":
        warning = "DIRECT_SOURCE_UNVERIFIED"
        message = (
            f"{warning}: CSV does not contain enough source evidence to rule out Yandex Direct expenses. "
            "Add UTMSource/UTMMedium or TrafficSourceDetail, or use --allow-direct-risk only after "
            "confirming the expense provenance."
        )
    else:
        message = ""

    if warning and not allow_direct_risk:
        raise ValueError(message)
    return [warning] if warning else []


def import_approval_envelope(
    kind: str,
    counter_id: int,
    file_path: Path,
    *,
    token: str,
    source: str | None = None,
    allow_direct_risk: bool = False,
    _file_bytes: bytes | None = None,
    **query: Any,
) -> dict[str, Any]:
    file_path = Path(file_path)
    file_bytes = _read_file_bytes(file_path) if _file_bytes is None else _file_bytes
    file_info = _inspect_csv_bytes(file_path, file_bytes)
    normalized_query = _normalized_import_query(kind, source, query)
    warnings = _expense_warnings(kind, source, allow_direct_risk, file_bytes)
    cardinality = _safety.known_cardinality(1, artifact_rows=file_info["rows"])
    safety = {
        "verification": "RESPONSE_ONLY",
        "rollback": "NOT_AVAILABLE",
        "risk_flags": warnings,
    }
    url = import_url(kind, counter_id, normalized_query)
    return {
        "schema": _safety.APPROVAL_SCHEMA,
        "plugin": "yandex-metrika",
        "operation": f"import.{kind}",
        "request": {
            "method": "POST",
            "environment": "production",
            "api_version": "management/v1",
            "url": url,
            "path": f"counter/{int(counter_id)}/{IMPORT_PATHS[kind]}",
            "query": {k: v for k, v in normalized_query.items() if v is not None},
            "body": None,
        },
        "target": {
            "counter_id": int(counter_id),
            "kind": kind,
            "source": source,
            "allow_direct_risk": bool(allow_direct_risk),
            "auth_principal_binding": _safety.principal_binding(
                token, domain=AUTH_PRINCIPAL_DOMAIN
            ),
        },
        "artifacts": [
            {
                "name": file_info["name"],
                "size_bytes": file_info["size_bytes"],
                "sha256": file_info["sha256"],
            }
        ],
        "cardinality": cardinality,
        "safety": safety,
    }


def build_multipart_file(
    path: Path,
    *,
    boundary: str | None = None,
    file_bytes: bytes | None = None,
) -> tuple[str, bytes]:
    path = Path(path)
    data = _read_file_bytes(path) if file_bytes is None else file_bytes
    boundary = boundary or f"----YandexMetrika{secrets.token_hex(12)}"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode("utf-8"),
            b"Content-Type: text/csv\r\n\r\n",
            data,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return f"multipart/form-data; boundary={boundary}", body


def _prepare_import_snapshot(
    kind: str,
    counter_id: int,
    file_path: Path,
    token: str,
    *,
    source: str | None = None,
    allow_direct_risk: bool = False,
    **query: Any,
) -> tuple[dict[str, Any], bytes]:
    file_path = Path(file_path)
    file_bytes = _read_file_bytes(file_path)
    warnings = _expense_warnings(kind, source, allow_direct_risk, file_bytes)
    file_info = _inspect_csv_bytes(file_path, file_bytes)
    normalized_query = _normalized_import_query(kind, source, query)
    envelope = import_approval_envelope(
        kind,
        counter_id,
        file_path,
        token=token,
        source=source,
        allow_direct_risk=allow_direct_risk,
        _file_bytes=file_bytes,
        **query,
    )
    preview = {
        "method": "POST",
        "url": import_url(kind, counter_id, normalized_query),
        "headers": redact_headers(oauth_headers(token, content_type="multipart/form-data")),
        "file": file_info,
        "kind": kind,
        "counter_id": int(counter_id),
        "consequential": True,
        "warnings": warnings,
        "approval_schema": envelope["schema"],
        "preview_id": preview_id(envelope),
        "cardinality": envelope["cardinality"],
        "safety": envelope["safety"],
    }
    return preview, file_bytes


def prepare_import(
    kind: str,
    counter_id: int,
    file_path: Path,
    token: str,
    *,
    source: str | None = None,
    allow_direct_risk: bool = False,
    **query: Any,
) -> dict[str, Any]:
    preview, _ = _prepare_import_snapshot(
        kind,
        counter_id,
        file_path,
        token,
        source=source,
        allow_direct_risk=allow_direct_risk,
        **query,
    )
    return preview


def execute_import(
    kind: str,
    counter_id: int,
    file_path: Path,
    token: str,
    *,
    source: str | None = None,
    allow_direct_risk: bool = False,
    approve: str | None = None,
    timeout: int = 120,
    opener: Callable[..., Any] = urlopen,
    **query: Any,
) -> Any:
    preview, file_bytes = _prepare_import_snapshot(
        kind,
        counter_id,
        file_path,
        token,
        source=source,
        allow_direct_risk=allow_direct_risk,
        **query,
    )
    envelope = import_approval_envelope(
        kind,
        counter_id,
        file_path,
        token=token,
        source=source,
        allow_direct_risk=allow_direct_risk,
        _file_bytes=file_bytes,
        **query,
    )
    approved_preview = require_approval(envelope, approve)
    content_type, body = build_multipart_file(Path(file_path), file_bytes=file_bytes)
    headers = oauth_headers(token, content_type=content_type)
    request = Request(preview["url"], data=body, headers=headers, method="POST")
    with opener(request, timeout=timeout) as response:
        raw = response.read()
    payload = None if not raw else json.loads(raw.decode("utf-8"))
    return _safety.execution_receipt(
        preview_id=approved_preview,
        plugin="yandex-metrika",
        operation=envelope["operation"],
        target=envelope["target"],
        cardinality=envelope["cardinality"],
        result=payload,
        verification_capability="RESPONSE_ONLY",
        verification_state="UNVERIFIED",
        rollback_capability="NOT_AVAILABLE",
    )


def run_import(
    kind: str,
    counter_id: int,
    file_path: Path,
    token: str,
    *,
    source: str | None = None,
    allow_direct_risk: bool = False,
    execute: bool = False,
    approve: str | None = None,
    timeout: int = 120,
    opener: Callable[..., Any] = urlopen,
    **query: Any,
) -> Any:
    if not execute:
        return {
            "dry_run": True,
            **prepare_import(
                kind,
                counter_id,
                file_path,
                token,
                source=source,
                allow_direct_risk=allow_direct_risk,
                **query,
            ),
        }
    return execute_import(
        kind,
        counter_id,
        file_path,
        token,
        source=source,
        allow_direct_risk=allow_direct_risk,
        approve=approve,
        timeout=timeout,
        opener=opener,
        **query,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Yandex Metrika data import helper")
    parser.add_argument("kind", choices=sorted(IMPORT_PATHS))
    parser.add_argument("counter", type=int)
    parser.add_argument("file")
    parser.add_argument("--comment")
    parser.add_argument("--source", help="Provider/source label. Direct/Yandex Direct aliases are rejected for expenses.")
    parser.add_argument(
        "--allow-direct-risk",
        action="store_true",
        help="Allow an expense CSV with Direct or unverified source provenance after explicitly reviewing duplication risk.",
    )
    parser.add_argument("--new-goal-name", help="Calls import new_goal_name")
    parser.add_argument("--type", dest="offline_type", choices=["BASIC", "CALLS", "CHATS"])
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approve", help="Full preview_id for the exact consequential preview")
    args = parser.parse_args(argv)

    token = os.environ.get("YANDEX_METRIKA_TOKEN", "")
    query: dict[str, Any] = {"comment": args.comment}
    if args.kind == "calls":
        query["new_goal_name"] = args.new_goal_name
    if args.kind == "offline-conversions":
        query["type"] = args.offline_type
    payload = run_import(
        args.kind,
        args.counter,
        Path(args.file),
        token,
        source=args.source,
        allow_direct_risk=args.allow_direct_risk,
        execute=args.execute,
        approve=args.approve,
        **query,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
