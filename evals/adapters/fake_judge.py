#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


REQUEST_SCHEMA = "yandex-ai-eval-adapter-request/v1"
RESPONSE_SCHEMA = "yandex-ai-eval-adapter-response/v1"


def main() -> int:
    request = json.loads(sys.stdin.readline())
    if request.get("schema") != REQUEST_SCHEMA:
        return 2
    payload = request.get("payload") or {}
    expect = payload.get("expect") or {}
    subject = payload.get("subject") or {}
    text = subject.get("text", "")
    must_convey = []
    for item in expect.get("must_convey") or []:
        evidence = [item] if isinstance(item, str) and item in text else []
        must_convey.append({
            "expectation": item,
            "state": "PASS" if evidence else "UNDETERMINED",
            "evidence": evidence,
            "rationale": "deterministic fake semantic check",
        })
    must_not_claim = []
    for item in expect.get("must_not_claim") or []:
        present = isinstance(item, str) and item in text
        must_not_claim.append({
            "expectation": item,
            "state": "FAIL" if present else "PASS",
            "evidence": [item] if present else [],
            "rationale": "deterministic fake forbidden-claim check",
        })
    actual_route = subject.get("route", "")
    expected_route = expect.get("must_route_to", "")
    response = {
        "schema": RESPONSE_SCHEMA,
        "invocation_id": request.get("invocation_id"),
        "adapter_id": "fake-judge-adapter",
        "adapter_version": "1",
        "runtime": {"name": "repository-fake", "version": "1"},
        "model": {"name": "fake-judge", "version": "1"},
        "output": {
            "observed_outcome": subject.get("outcome", "comply"),
            "route": {
                "state": "PASS" if actual_route == expected_route else "FAIL",
                "actual": actual_route,
                "rationale": "deterministic fake route check",
            },
            "must_convey": must_convey,
            "must_not_claim": must_not_claim,
            "rationale": "deterministic fake judge; not real semantic benchmark evidence",
        },
    }
    print(json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
