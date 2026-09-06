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
    scenario = payload.get("scenario") or {}
    expect = scenario.get("expect") or {}
    tokens = expect.get("must_mention_tokens") or []
    convey = expect.get("must_convey") or []
    text = " ".join([*tokens, *convey]).strip() or "deterministic fake subject output"
    response = {
        "schema": RESPONSE_SCHEMA,
        "invocation_id": request.get("invocation_id"),
        "adapter_id": "fake-subject-adapter",
        "adapter_version": "1",
        "runtime": {"name": "repository-fake", "version": "1"},
        "model": {"name": "fake-subject", "version": "1"},
        "output": {
            "text": text,
            "route": expect.get("must_route_to", scenario.get("skill", "unknown")),
            "outcome": expect.get("outcome", "comply"),
        },
    }
    print(json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
