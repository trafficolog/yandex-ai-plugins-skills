#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys


REQUEST_SCHEMA = "yandex-ai-eval-adapter-request/v1"
RESPONSE_SCHEMA = "yandex-ai-eval-adapter-response/v1"
TRACE_SCHEMA = "yandex-ai-backend-trace/v1"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> int:
    request = json.loads(sys.stdin.readline())
    if request.get("schema") != REQUEST_SCHEMA:
        return 2
    payload = request.get("payload") or {}
    fixture = payload.get("fixture") or {}
    req = fixture.get("request") or {}
    target = fixture.get("target") or {}
    params = req.get("params") or {}
    service = req.get("service")
    method = req.get("method")
    items = None
    key = {"campaigns": "Campaigns"}.get(service)
    if key and isinstance(params.get(key), list):
        items = len(params[key])
    cardinality = (
        {"scale": "KNOWN", "items": items, "threshold": 20, "bulk": bool(items > 20)}
        if items is not None
        else {"scale": "UNKNOWN", "items": None, "threshold": 20, "bulk": True}
    )
    binding = {
        "plugin": "yandex-direct",
        "operation": f"{service}.{str(method).lower()}",
        "request": {
            "environment": req.get("environment"),
            "service": service,
            "method": method,
            "params": params,
        },
        "target": {
            "client_login": target.get("client_login"),
            "principal_id": target.get("principal_id"),
        },
        "cardinality": cardinality,
        "safety": {"verification": "RESPONSE_ONLY", "rollback": "NOT_AVAILABLE", "risk_flags": []},
    }
    native_preview = "connected-" + hashlib.sha256(canonical(binding)).hexdigest()
    ack_bulk = bool(fixture.get("ack_bulk", False))
    exact_executable = not cardinality["bulk"] or ack_bulk
    trace = {
        "schema": TRACE_SCHEMA,
        "backend_kind": "CONNECTED",
        "logical_request_id": fixture.get("logical_request_id"),
        "plugin": "yandex-direct",
        "operation": binding["operation"],
        "native_preview_id": native_preview,
        "normalized_approval_binding": binding,
        "later_turn_approval": {"required": True, "proof": "HOST_RESPONSIBILITY"},
        "cases": {
            "no_approval": {"approval": "MISSING", "ack_bulk": ack_bulk, "transport_attempted": False, "state": "BLOCKED"},
            "wrong_approval": {"approval": "WRONG", "ack_bulk": ack_bulk, "transport_attempted": False, "state": "BLOCKED"},
            "exact_approval": {
                "approval": "EXACT",
                "ack_bulk": ack_bulk,
                "transport_attempted": bool(exact_executable),
                "state": "EXECUTED" if exact_executable else "BLOCKED",
                **({"execution_receipt_id": "connected-simulated-receipt"} if exact_executable else {}),
            },
        },
    }
    response = {
        "schema": RESPONSE_SCHEMA,
        "invocation_id": request.get("invocation_id"),
        "adapter_id": "fake-connected-backend-adapter",
        "adapter_version": "1",
        "runtime": {"name": "repository-fake", "version": "1"},
        "model": {"name": "fake-connected-backend", "version": "1"},
        "output": {"trace": trace},
    }
    print(json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
