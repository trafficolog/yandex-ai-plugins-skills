from __future__ import annotations

from datetime import datetime
import hashlib
import re
from typing import Any

from .judge import evaluate_semantics, scenario_state
from .mechanical import evaluate_exact_tokens
from .protocol import REQUEST_SCHEMA, canonical_json_bytes, invoke_adapter


_SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _validate_timestamp(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("evaluated_at must be an RFC3339 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("evaluated_at must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("evaluated_at must include timezone")
    return value


def _identity_projection(response: dict[str, object]) -> dict[str, object]:
    runtime = response.get("runtime")
    model = response.get("model")
    assert isinstance(runtime, dict) and isinstance(model, dict)
    adapter_id = str(response.get("adapter_id", ""))
    return {
        "adapter_id": adapter_id,
        "adapter_version": str(response.get("adapter_version", "")),
        "runtime": {"name": runtime.get("name"), "version": runtime.get("version")},
        "model": {"name": model.get("name"), "version": model.get("version")},
        "fake": adapter_id.startswith("fake-"),
    }


def run_scenario(
    scenario_record: dict[str, object],
    *,
    subject_argv: list[str],
    judge_argv: list[str],
    allow_self_judge: bool = False,
    adapter_env: dict[str, str] | None = None,
) -> dict[str, object]:
    if not isinstance(scenario_record, dict):
        raise ValueError("scenario_record must be an object")
    scenario = scenario_record.get("scenario")
    scenario_id = scenario_record.get("scenario_id")
    if not isinstance(scenario, dict) or not isinstance(scenario_id, str) or not scenario_id:
        raise ValueError("scenario_record must contain scenario and scenario_id")
    expect = scenario.get("expect")
    if not isinstance(expect, dict):
        raise ValueError("scenario.expect must be an object")
    invocation_id = "subject-" + hashlib.sha256(
        canonical_json_bytes({"scenario_id": scenario_id, "scenario": scenario})
    ).hexdigest()[:24]
    request = {
        "schema": REQUEST_SCHEMA,
        "invocation_id": invocation_id,
        "kind": "subject",
        "payload": {
            "plugin": scenario_record.get("plugin"),
            "scenario_id": scenario_id,
            "scenario": scenario,
        },
    }
    subject = invoke_adapter(subject_argv, request, env=adapter_env)
    output = subject.get("output")
    if not isinstance(output, dict) or not isinstance(output.get("text"), str):
        raise ValueError("subject adapter output must contain final text")
    tokens = expect.get("must_mention_tokens")
    if not isinstance(tokens, list):
        raise ValueError("scenario exact-token expectations must be a list")
    mechanical = evaluate_exact_tokens(str(output["text"]), tokens)
    semantic = evaluate_semantics(
        subject,
        scenario,
        judge_argv=judge_argv,
        allow_self_judge=allow_self_judge,
        adapter_env=adapter_env,
    )
    return {
        "plugin": scenario_record.get("plugin"),
        "scenario_id": scenario_id,
        "source_path": scenario_record.get("source_path"),
        "source_sha256": scenario_record.get("source_sha256"),
        "state": scenario_state(mechanical, semantic),
        "subject": subject,
        "mechanical": mechanical,
        "semantic": semantic,
    }


def run_benchmark(
    scenarios: list[dict[str, object]],
    *,
    subject_argv: list[str],
    judge_argv: list[str],
    evaluated_at: str,
    repository_sha: str,
    allow_self_judge: bool = False,
) -> dict[str, object]:
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("benchmark requires at least one scenario")
    _validate_timestamp(evaluated_at)
    if not isinstance(repository_sha, str) or _SHA40.fullmatch(repository_sha) is None:
        raise ValueError("repository SHA must be exactly 40 lowercase hex characters")
    results = [
        run_scenario(
            record,
            subject_argv=subject_argv,
            judge_argv=judge_argv,
            allow_self_judge=allow_self_judge,
        )
        for record in sorted(scenarios, key=lambda item: str(item.get("scenario_id", "")))
    ]
    aggregate = {
        "passed": sum(item["state"] == "PASS" for item in results),
        "failed": sum(item["state"] == "FAIL" for item in results),
        "undetermined": sum(item["state"] == "UNDETERMINED" for item in results),
        "total": len(results),
    }
    identities: dict[tuple[str, str, str, str, str], dict[str, object]] = {}
    self_judged = False
    for item in results:
        subject = item["subject"]
        semantic = item["semantic"]
        assert isinstance(subject, dict) and isinstance(semantic, dict)
        projection = _identity_projection(subject)
        runtime = projection["runtime"]
        model = projection["model"]
        assert isinstance(runtime, dict) and isinstance(model, dict)
        key = (
            str(projection["adapter_id"]),
            str(runtime.get("name")),
            str(runtime.get("version")),
            str(model.get("name")),
            str(model.get("version")),
        )
        identities[key] = projection
        self_judged = self_judged or semantic.get("judge_mode") == "SELF_JUDGED"
    identity_values = [identities[key] for key in sorted(identities)]
    has_fake_subject = any(bool(item.get("fake")) for item in identity_values)
    return {
        "evaluated_at": evaluated_at,
        "repository_sha": repository_sha,
        "scenarios": results,
        "aggregate": aggregate,
        "subject_identities": identity_values,
        "completeness": "INFRASTRUCTURE_READY",
        "comparative_complete": False if (has_fake_subject or self_judged or len(identity_values) < 2) else False,
    }
