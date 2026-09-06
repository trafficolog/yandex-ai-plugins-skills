from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from .protocol import canonical_json_bytes


TRACE_SCHEMA = "yandex-ai-backend-trace/v1"
_REQUIRED_CASES = ("no_approval", "wrong_approval", "exact_approval")


def load_fixture(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid backend-equivalence fixture: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError("backend-equivalence fixture must be an object")
    return value


def normalize_backend_trace(trace: object) -> dict[str, object]:
    if not isinstance(trace, dict):
        raise ValueError("backend trace must be an object")
    if trace.get("schema") != TRACE_SCHEMA:
        raise ValueError(f"backend trace schema must equal {TRACE_SCHEMA}")
    if trace.get("backend_kind") not in {"CONNECTED", "BUNDLED"}:
        raise ValueError("backend_kind must be CONNECTED or BUNDLED")
    for key in ("logical_request_id", "plugin", "operation", "native_preview_id"):
        if not isinstance(trace.get(key), str) or not trace[key]:
            raise ValueError(f"backend trace {key} must be a non-empty string")
    binding = trace.get("normalized_approval_binding")
    if not isinstance(binding, dict):
        raise ValueError("normalized_approval_binding must be an object")
    for key in ("plugin", "operation", "request", "target", "cardinality", "safety"):
        if key not in binding:
            raise ValueError(f"normalized_approval_binding.{key} is required")
    canonical_json_bytes(binding)
    later = trace.get("later_turn_approval")
    if not isinstance(later, dict) or later.get("required") is not True:
        raise ValueError("later_turn_approval.required must be true")
    if not isinstance(later.get("proof"), str) or not later["proof"]:
        raise ValueError("later_turn_approval.proof must be a non-empty string")
    cases = trace.get("cases")
    if not isinstance(cases, dict):
        raise ValueError("backend trace cases must be an object")
    for case_name in _REQUIRED_CASES:
        case = cases.get(case_name)
        if not isinstance(case, dict):
            raise ValueError(f"backend trace case {case_name} is required")
        expected_approval = {
            "no_approval": "MISSING",
            "wrong_approval": "WRONG",
            "exact_approval": "EXACT",
        }[case_name]
        if case.get("approval") != expected_approval:
            raise ValueError(f"{case_name}.approval must equal {expected_approval}")
        if not isinstance(case.get("ack_bulk"), bool):
            raise ValueError(f"{case_name}.ack_bulk must be boolean")
        if not isinstance(case.get("transport_attempted"), bool):
            raise ValueError(f"{case_name}.transport_attempted must be boolean")
        if case.get("state") not in {"BLOCKED", "EXECUTED"}:
            raise ValueError(f"{case_name}.state must be BLOCKED or EXECUTED")
        if case.get("state") == "EXECUTED":
            if not isinstance(case.get("execution_receipt_id"), str) or not case["execution_receipt_id"]:
                raise ValueError(f"{case_name}.execution_receipt_id is required for EXECUTED")
    canonical_json_bytes(trace)
    return json.loads(canonical_json_bytes(trace).decode("utf-8"))


def approval_binding_sha256(trace: dict[str, object]) -> str:
    normalized = normalize_backend_trace(trace)
    return hashlib.sha256(canonical_json_bytes(normalized["normalized_approval_binding"])).hexdigest()


def compare_backend_traces(
    connected: dict[str, object], bundled: dict[str, object]
) -> dict[str, object]:
    left = normalize_backend_trace(connected)
    right = normalize_backend_trace(bundled)
    if left["backend_kind"] != "CONNECTED" or right["backend_kind"] != "BUNDLED":
        raise ValueError("compare_backend_traces requires CONNECTED then BUNDLED traces")
    differences: list[str] = []
    if left["logical_request_id"] != right["logical_request_id"]:
        differences.append("logical_request_id differs")
    if left["plugin"] != right["plugin"]:
        differences.append("plugin differs")
    if left["operation"] != right["operation"]:
        differences.append("operation differs")
    if left["normalized_approval_binding"] != right["normalized_approval_binding"]:
        differences.append("normalized_approval_binding differs")
    if left["later_turn_approval"] != right["later_turn_approval"]:
        differences.append("later_turn_approval differs")
    left_cases = left["cases"]
    right_cases = right["cases"]
    assert isinstance(left_cases, dict) and isinstance(right_cases, dict)
    for case_name in _REQUIRED_CASES:
        left_case = left_cases[case_name]
        right_case = right_cases[case_name]
        assert isinstance(left_case, dict) and isinstance(right_case, dict)
        for field in ("approval", "ack_bulk", "transport_attempted", "state"):
            if left_case.get(field) != right_case.get(field):
                differences.append(f"{case_name}.{field} differs")
    return {
        "state": "PASS" if not differences else "FAIL",
        "connected_binding_sha256": approval_binding_sha256(left),
        "bundled_binding_sha256": approval_binding_sha256(right),
        "differences": differences,
        "connected_native_preview_id": left["native_preview_id"],
        "bundled_native_preview_id": right["native_preview_id"],
    }


def _direct_module(repository_root: Path):
    scripts_path = repository_root / "plugins/yandex-direct/scripts"
    path_text = str(scripts_path)
    inserted = path_text not in sys.path
    if inserted:
        sys.path.insert(0, path_text)
    try:
        import yd_api  # type: ignore
    except ImportError as exc:
        raise ValueError("unable to load bundled Direct helper") from exc
    return yd_api, inserted, path_text


def run_bundled_direct_fixture(
    repository_root: Path, fixture: dict[str, object]
) -> dict[str, object]:
    if fixture.get("schema") != "yandex-ai-backend-equivalence-fixture/v1":
        raise ValueError("unsupported backend-equivalence fixture schema")
    request = fixture.get("request")
    target = fixture.get("target")
    if not isinstance(request, dict) or not isinstance(target, dict):
        raise ValueError("fixture request and target must be objects")
    service = request.get("service")
    method = request.get("method")
    params = request.get("params")
    environment = request.get("environment")
    if not isinstance(service, str) or not isinstance(method, str) or not isinstance(params, dict):
        raise ValueError("fixture request service/method/params are invalid")
    if environment not in {"production", "sandbox"}:
        raise ValueError("fixture request environment is invalid")
    client_login = target.get("client_login")
    principal_id = target.get("principal_id")
    if client_login is not None and not isinstance(client_login, str):
        raise ValueError("fixture target client_login must be string or null")
    if not isinstance(principal_id, str) or not principal_id:
        raise ValueError("fixture target principal_id is required")

    yd_api, inserted, path_text = _direct_module(repository_root)
    original_request_json = yd_api._http.request_json
    calls = 0

    def fake_request_json(*args: Any, **kwargs: Any):
        nonlocal calls
        calls += 1
        return ({"result": {"UpdateResults": [{"Id": 123}]}}, {"request_id": "benchmark-fixture"})

    try:
        client = yd_api.YandexDirectClient(
            "benchmark-fixture-token",
            client_login=client_login,
            environment=environment,
        )
        envelope = client.approval_envelope(service, method, params)
        native_preview = yd_api.preview_id(envelope)
        cases: dict[str, dict[str, object]] = {}
        for case_name, approval in (
            ("no_approval", None),
            ("wrong_approval", "0" * 64),
            ("exact_approval", native_preview),
        ):
            before = calls
            yd_api._http.request_json = fake_request_json
            try:
                result = client.request(
                    service,
                    method,
                    params,
                    approve=approval,
                    ack_bulk=bool(fixture.get("ack_bulk", False)),
                )
            except ValueError:
                cases[case_name] = {
                    "approval": {"no_approval": "MISSING", "wrong_approval": "WRONG", "exact_approval": "EXACT"}[case_name],
                    "ack_bulk": bool(fixture.get("ack_bulk", False)),
                    "transport_attempted": calls > before,
                    "state": "BLOCKED",
                }
            else:
                receipt_id = result.get("execution_id") if isinstance(result, dict) else None
                cases[case_name] = {
                    "approval": {"no_approval": "MISSING", "wrong_approval": "WRONG", "exact_approval": "EXACT"}[case_name],
                    "ack_bulk": bool(fixture.get("ack_bulk", False)),
                    "transport_attempted": calls > before,
                    "state": "EXECUTED",
                    "execution_receipt_id": str(receipt_id or "simulated-receipt"),
                }
        binding = {
            "plugin": "yandex-direct",
            "operation": envelope["operation"],
            "request": {
                "environment": environment,
                "service": service,
                "method": method,
                "params": params,
            },
            "target": {"client_login": client_login, "principal_id": principal_id},
            "cardinality": envelope["cardinality"],
            "safety": envelope["safety"],
        }
        trace = {
            "schema": TRACE_SCHEMA,
            "backend_kind": "BUNDLED",
            "logical_request_id": fixture.get("logical_request_id"),
            "plugin": "yandex-direct",
            "operation": envelope["operation"],
            "native_preview_id": native_preview,
            "normalized_approval_binding": binding,
            "later_turn_approval": {"required": True, "proof": "HOST_RESPONSIBILITY"},
            "cases": cases,
        }
        return normalize_backend_trace(trace)
    finally:
        yd_api._http.request_json = original_request_json
        if inserted and sys.path and sys.path[0] == path_text:
            sys.path.pop(0)
