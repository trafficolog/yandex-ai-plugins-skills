from __future__ import annotations

import json
import math
import os
import subprocess
from typing import Any


REQUEST_SCHEMA = "yandex-ai-eval-adapter-request/v1"
RESPONSE_SCHEMA = "yandex-ai-eval-adapter-response/v1"


def _is_json_compatible(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json_compatible(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_compatible(item) for key, item in value.items())
    return False


def canonical_json_bytes(value: object) -> bytes:
    if not _is_json_compatible(value):
        raise ValueError("value must be finite JSON-compatible data")
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _require_nonempty_string(mapping: dict[str, Any], key: str, where: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{where}.{key} must be a non-empty string")
    return value


def _validate_request(request: object) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ValueError("adapter request must be a JSON object")
    if request.get("schema") != REQUEST_SCHEMA:
        raise ValueError(f"adapter request schema must equal {REQUEST_SCHEMA}")
    _require_nonempty_string(request, "invocation_id", "request")
    _require_nonempty_string(request, "kind", "request")
    if not isinstance(request.get("payload"), dict):
        raise ValueError("request.payload must be an object")
    if not _is_json_compatible(request):
        raise ValueError("adapter request must be finite JSON-compatible data")
    return request


def _validate_response(response: object, *, invocation_id: str) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise ValueError("adapter response must be a JSON object")
    if response.get("schema") != RESPONSE_SCHEMA:
        raise ValueError(f"adapter response schema must equal {RESPONSE_SCHEMA}")
    actual_id = _require_nonempty_string(response, "invocation_id", "response")
    if actual_id != invocation_id:
        raise ValueError("response.invocation_id must match request invocation_id exactly")
    _require_nonempty_string(response, "adapter_id", "response")
    _require_nonempty_string(response, "adapter_version", "response")
    for section in ("runtime", "model"):
        value = response.get(section)
        if not isinstance(value, dict):
            raise ValueError(f"response.{section} must be an object")
        _require_nonempty_string(value, "name", f"response.{section}")
        _require_nonempty_string(value, "version", f"response.{section}")
    if not isinstance(response.get("output"), dict):
        raise ValueError("response.output must be an object")
    if not _is_json_compatible(response):
        raise ValueError("adapter response must be finite JSON-compatible data")
    return response


def model_identity(metadata: dict[str, object]) -> tuple[str, str, str, str]:
    response = _validate_response(metadata, invocation_id=str(metadata.get("invocation_id", "")))
    runtime = response["runtime"]
    model = response["model"]
    assert isinstance(runtime, dict) and isinstance(model, dict)
    return (
        str(runtime["name"]),
        str(runtime["version"]),
        str(model["name"]),
        str(model["version"]),
    )


def invoke_adapter(
    argv: list[str],
    request: dict[str, object],
    *,
    timeout_seconds: float = 60.0,
    max_stdout_bytes: int = 1_000_000,
    max_stderr_bytes: int = 200_000,
    env: dict[str, str] | None = None,
) -> dict[str, object]:
    if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item for item in argv):
        raise ValueError("adapter argv must be a non-empty list of non-empty strings")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if max_stdout_bytes <= 0 or max_stderr_bytes <= 0:
        raise ValueError("adapter output byte limits must be positive")

    validated_request = _validate_request(request)
    invocation_id = str(validated_request["invocation_id"])
    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    process = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        env=process_env,
    )
    try:
        stdout, stderr = process.communicate(
            input=canonical_json_bytes(validated_request) + b"\n",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.communicate()
        raise TimeoutError(f"adapter timeout after {timeout_seconds} seconds") from exc

    if len(stdout) > max_stdout_bytes:
        raise ValueError(f"adapter stdout exceeds {max_stdout_bytes} bytes")
    if len(stderr) > max_stderr_bytes:
        raise ValueError(f"adapter stderr exceeds {max_stderr_bytes} bytes")
    if process.returncode != 0:
        raise RuntimeError(f"adapter exit code {process.returncode}")

    try:
        stdout_text = stdout.decode("utf-8", errors="strict")
        stderr.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("adapter output must be valid UTF-8") from exc

    lines = stdout_text.splitlines()
    if len(lines) != 1 or not lines[0].strip():
        raise ValueError("adapter stdout must contain exactly one JSON response line")
    try:
        response = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise ValueError("adapter stdout must contain one valid JSON response") from exc
    return _validate_response(response, invocation_id=invocation_id)
