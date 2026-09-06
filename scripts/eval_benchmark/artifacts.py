from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Any

from .protocol import canonical_json_bytes


RESULT_SCHEMA = "yandex-ai-benchmark-result/v1"
MANIFEST_SCHEMA = "yandex-ai-benchmark-manifest/v1"
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HIDDEN_OR_PRIVATE_KEYS = {
    "chainofthought",
    "hiddenreasoning",
    "scratchpad",
    "privatereasoning",
    "reasoningtrace",
    "credentials",
    "password",
    "rawenvironment",
    "environmentvariables",
    "adapterargv",
    "commandline",
}


def _normalized_key(value: str) -> str:
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def _reject_private_fields(value: object, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and _normalized_key(key) in _HIDDEN_OR_PRIVATE_KEYS:
                raise ValueError(f"hidden reasoning or private execution field is not allowed at {path}.{key}")
            _reject_private_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_private_fields(child, f"{path}[{index}]")


def _validate_timestamp(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("evaluated_at must be a non-empty RFC3339 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError("evaluated_at must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("evaluated_at must include timezone")
    return value


def _require_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _validate_result_shape(result: object) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("benchmark result must be an object")
    if result.get("schema") != RESULT_SCHEMA:
        raise ValueError(f"benchmark result schema must equal {RESULT_SCHEMA}")
    benchmark_id = result.get("benchmark_id")
    if not isinstance(benchmark_id, str) or _HEX64.fullmatch(benchmark_id) is None:
        raise ValueError("benchmark_id must be lowercase SHA-256")
    repository_sha = result.get("repository_sha")
    if not isinstance(repository_sha, str) or _HEX40.fullmatch(repository_sha) is None:
        raise ValueError("repository_sha must be exactly 40 lowercase hex characters")
    _validate_timestamp(result.get("evaluated_at"))
    if result.get("completeness") not in {"INFRASTRUCTURE_READY", "COMPARATIVE_COMPLETE"}:
        raise ValueError("benchmark completeness has unsupported value")
    if not isinstance(result.get("comparative_complete"), bool):
        raise ValueError("comparative_complete must be boolean")
    scenarios = result.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("benchmark result must contain scenarios")
    _require_mapping(result.get("aggregate"), "aggregate")
    _reject_private_fields(result)

    body = {key: value for key, value in result.items() if key != "benchmark_id"}
    expected = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    if benchmark_id != expected:
        raise ValueError("benchmark_id does not match canonical benchmark result")
    return result


def build_result_document(
    run_result: dict[str, object],
    *,
    backend_equivalence: dict[str, object] | None = None,
    memory_results: dict[str, object] | None = None,
) -> dict[str, object]:
    if not isinstance(run_result, dict):
        raise ValueError("run_result must be an object")
    _reject_private_fields(run_result)
    evaluated_at = _validate_timestamp(run_result.get("evaluated_at"))
    repository_sha = run_result.get("repository_sha")
    if not isinstance(repository_sha, str) or _HEX40.fullmatch(repository_sha) is None:
        raise ValueError("repository_sha must be exactly 40 lowercase hex characters")
    scenarios = run_result.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("run_result.scenarios must be a non-empty list")
    aggregate = _require_mapping(run_result.get("aggregate"), "run_result.aggregate")
    identities = run_result.get("subject_identities")
    if not isinstance(identities, list):
        raise ValueError("run_result.subject_identities must be a list")
    completeness = run_result.get("completeness")
    if completeness not in {"INFRASTRUCTURE_READY", "COMPARATIVE_COMPLETE"}:
        raise ValueError("run_result.completeness has unsupported value")
    comparative_complete = run_result.get("comparative_complete")
    if not isinstance(comparative_complete, bool):
        raise ValueError("run_result.comparative_complete must be boolean")

    body: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "evaluated_at": evaluated_at,
        "repository_sha": repository_sha,
        "completeness": completeness,
        "comparative_complete": comparative_complete,
        "aggregate": deepcopy(aggregate),
        "subject_identities": deepcopy(identities),
        "scenarios": deepcopy(scenarios),
    }
    if backend_equivalence is not None:
        if not isinstance(backend_equivalence, dict):
            raise ValueError("backend_equivalence must be an object")
        body["backend_equivalence"] = deepcopy(backend_equivalence)
    if memory_results is not None:
        if not isinstance(memory_results, dict):
            raise ValueError("memory_results must be an object")
        body["memory_results"] = deepcopy(memory_results)
    _reject_private_fields(body)
    benchmark_id = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    result = dict(body)
    result["benchmark_id"] = benchmark_id
    _validate_result_shape(result)
    return result


def _state_counts(result: dict[str, Any]) -> tuple[int, int, int, int]:
    aggregate = _require_mapping(result.get("aggregate"), "aggregate")
    values: list[int] = []
    for key in ("passed", "failed", "undetermined", "total"):
        value = aggregate.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"aggregate.{key} must be a non-negative integer")
        values.append(value)
    return values[0], values[1], values[2], values[3]


def render_comparison_html(result: dict[str, object]) -> str:
    data = _validate_result_shape(result)
    passed, failed, undetermined, total = _state_counts(data)
    esc = lambda value: html.escape(str(value), quote=True)
    scenario_rows: list[str] = []
    detail_blocks: list[str] = []
    scenarios = data["scenarios"]
    assert isinstance(scenarios, list)
    for item in scenarios:
        if not isinstance(item, dict):
            raise ValueError("scenario result items must be objects")
        plugin = item.get("plugin", "")
        scenario_id = item.get("scenario_id", "")
        state = item.get("state", "")
        if not isinstance(scenario_id, str) or _HEX64.fullmatch(scenario_id) is None:
            raise ValueError("scenario_id must be lowercase SHA-256")
        subject = _require_mapping(item.get("subject"), "scenario.subject")
        output = _require_mapping(subject.get("output"), "scenario.subject.output")
        text = output.get("text")
        if not isinstance(text, str):
            raise ValueError("scenario subject output text must be a string")
        semantic = _require_mapping(item.get("semantic"), "scenario.semantic")
        mechanical = item.get("mechanical")
        if not isinstance(mechanical, list):
            raise ValueError("scenario.mechanical must be a list")
        scenario_rows.append(
            "<tr><td>" + esc(plugin) + "</td><td><code>" + esc(scenario_id[:16]) +
            "</code></td><td>" + esc(state) + "</td><td>" + esc(output.get("route", "")) + "</td></tr>"
        )
        detail_blocks.append(
            "<section class=\"scenario\"><h3>" + esc(plugin) + " · " + esc(scenario_id[:16]) +
            "</h3><p><strong>State:</strong> " + esc(state) +
            "</p><h4>Final subject output</h4><pre>" + esc(text) +
            "</pre><h4>Mechanical evidence</h4><pre>" + esc(json.dumps(mechanical, ensure_ascii=False, sort_keys=True)) +
            "</pre><h4>Semantic evidence</h4><pre>" + esc(json.dumps(semantic, ensure_ascii=False, sort_keys=True)) +
            "</pre></section>"
        )

    csp = "default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; media-src 'none'; frame-src 'none'; connect-src 'none'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
    document = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content=""" + esc(csp) + """>
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Yandex AI benchmark comparison</title>
<style>body{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;line-height:1.45}code,pre{font-family:ui-monospace,monospace}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f5f5;padding:1rem;border-radius:.5rem}table{border-collapse:collapse;width:100%}th,td{border:1px solid #bbb;padding:.5rem;text-align:left}.scenario{border-top:1px solid #ccc;margin-top:2rem;padding-top:1rem}.status{font-weight:700}</style>
</head><body><main><h1>Executable eval benchmark</h1>
<p><strong>Benchmark:</strong> <code>""" + esc(data["benchmark_id"]) + """</code></p>
<p><strong>Repository:</strong> <code>""" + esc(data["repository_sha"]) + """</code></p>
<p><strong>Evaluated:</strong> """ + esc(data["evaluated_at"]) + """</p>
<p class="status"><strong>Completeness:</strong> """ + esc(data["completeness"]) + """</p>
<h2>Aggregate</h2><p>PASS """ + str(passed) + """ · FAIL """ + str(failed) + """ · UNDETERMINED """ + str(undetermined) + """ · TOTAL """ + str(total) + """</p>
<h2>Scenarios</h2><table><thead><tr><th>Plugin</th><th>Scenario</th><th>State</th><th>Route</th></tr></thead><tbody>""" + "".join(scenario_rows) + """</tbody></table>
""" + "".join(detail_blocks) + """
</main></body></html>"""
    return document


def _validate_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("managed artifact path must be a non-empty POSIX relative path")
    if value == "manifest.json" or value.startswith("/") or value.endswith("/") or "//" in value:
        raise ValueError("managed artifact path must be normalized and exclude manifest.json")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("managed artifact path cannot contain traversal segments")
    pure = PurePosixPath(value)
    if pure.is_absolute() or str(pure) != value:
        raise ValueError("managed artifact path must be normalized POSIX relative path")
    return value


def _role_and_media_type(path: str) -> tuple[str, str]:
    if path == "results.json":
        return "PRIMARY_JSON", "application/json"
    if path == "comparison.html":
        return "COMPARISON_HTML", "text/html; charset=utf-8"
    if path.startswith("runs/subject-") and path.endswith(".json"):
        return "SUBJECT_RUN", "application/json"
    if path.startswith("runs/judge-") and path.endswith(".json"):
        return "JUDGE_RUN", "application/json"
    raise ValueError(f"unsupported benchmark artifact path: {path}")


def _managed_files(result: dict[str, object]) -> dict[str, bytes]:
    data = _validate_result_shape(result)
    files: dict[str, bytes] = {
        "results.json": canonical_json_bytes(data) + b"\n",
        "comparison.html": (render_comparison_html(data) + "\n").encode("utf-8"),
    }
    scenarios = data["scenarios"]
    assert isinstance(scenarios, list)
    seen: set[str] = set()
    for item in scenarios:
        assert isinstance(item, dict)
        scenario_id = str(item.get("scenario_id", ""))
        if _HEX64.fullmatch(scenario_id) is None:
            raise ValueError("scenario_id must be lowercase SHA-256")
        if scenario_id in seen:
            raise ValueError(f"duplicate scenario_id in benchmark result: {scenario_id}")
        seen.add(scenario_id)
        suffix = scenario_id[:24]
        subject = _require_mapping(item.get("subject"), "scenario.subject")
        semantic = _require_mapping(item.get("semantic"), "scenario.semantic")
        _reject_private_fields(subject)
        _reject_private_fields(semantic)
        files[f"runs/subject-{suffix}.json"] = canonical_json_bytes(subject) + b"\n"
        files[f"runs/judge-{suffix}.json"] = canonical_json_bytes(semantic) + b"\n"
    return files


def _build_manifest(result: dict[str, object], files: dict[str, bytes]) -> dict[str, object]:
    data = _validate_result_shape(result)
    items: list[dict[str, object]] = []
    for raw_path in sorted(files):
        path = _validate_relative_path(raw_path)
        content = files[raw_path]
        role, media_type = _role_and_media_type(path)
        items.append({
            "path": path,
            "role": role,
            "media_type": media_type,
            "sha256": hashlib.sha256(content).hexdigest(),
        })
    return {
        "schema": MANIFEST_SCHEMA,
        "artifact_set_id": data["benchmark_id"],
        "created_at": data["evaluated_at"],
        "repository_sha": data["repository_sha"],
        "primary_artifact": "results.json",
        "files": items,
    }


def _expected_bytes(result: dict[str, object]) -> dict[str, bytes]:
    files = _managed_files(result)
    manifest = _build_manifest(result, files)
    expected = dict(files)
    expected["manifest.json"] = canonical_json_bytes(manifest) + b"\n"
    return expected


def _verify_exact_directory(destination: Path, expected: dict[str, bytes]) -> None:
    if not destination.is_dir():
        raise ValueError("artifact destination exists and is not a directory")
    actual_paths = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    }
    if actual_paths != set(expected):
        raise ValueError("existing artifact set has unexpected or missing files; exact replay required")
    for relative, content in expected.items():
        if (destination / PurePosixPath(relative)).read_bytes() != content:
            raise ValueError(f"existing artifact set conflicts at {relative}; exact replay required")


def publish_benchmark_artifacts(output_root: Path, result: dict[str, object]) -> Path:
    data = _validate_result_shape(result)
    benchmark_id = str(data["benchmark_id"])
    destination = Path(output_root) / benchmark_id
    expected = _expected_bytes(data)
    parent = destination.parent
    parent.mkdir(parents=True, exist_ok=True)
    lock_path = parent / f".{benchmark_id}.lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("benchmark artifact destination is locked by another writer") from exc
    temp_path: Path | None = None
    try:
        with os.fdopen(lock_fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
            handle.flush()
            os.fsync(handle.fileno())
        if destination.exists():
            _verify_exact_directory(destination, expected)
            return destination
        temp_path = Path(tempfile.mkdtemp(prefix=f".{benchmark_id}.", dir=str(parent)))
        for relative, content in expected.items():
            target = temp_path / PurePosixPath(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        if destination.exists():
            raise ValueError("benchmark artifact destination appeared during publication")
        os.rename(temp_path, destination)
        temp_path = None
        return destination
    finally:
        if temp_path is not None and temp_path.exists():
            shutil.rmtree(temp_path)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def verify_benchmark_artifact_directory(source: Path) -> tuple[dict[str, object], dict[str, bytes]]:
    source = Path(source)
    if not source.is_dir():
        raise ValueError("benchmark artifact source must be a directory")
    manifest_path = source / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("benchmark artifact manifest is missing or invalid") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("benchmark artifact manifest has unsupported schema")
    if manifest.get("primary_artifact") != "results.json":
        raise ValueError("benchmark artifact manifest primary_artifact must be results.json")
    items = manifest.get("files")
    if not isinstance(items, list) or not items:
        raise ValueError("benchmark artifact manifest files must be non-empty")

    expected_paths = {"manifest.json"}
    files: dict[str, bytes] = {}
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"benchmark manifest files[{index}] must be an object")
        path = _validate_relative_path(item.get("path"))
        if path in seen:
            raise ValueError(f"duplicate managed artifact path: {path}")
        seen.add(path)
        role, media_type = _role_and_media_type(path)
        if item.get("role") != role or item.get("media_type") != media_type:
            raise ValueError(f"benchmark manifest metadata mismatch for {path}")
        sha = item.get("sha256")
        if not isinstance(sha, str) or _HEX64.fullmatch(sha) is None:
            raise ValueError(f"benchmark manifest hash is invalid for {path}")
        target = source / PurePosixPath(path)
        if not target.is_file():
            raise ValueError(f"managed benchmark artifact missing: {path}")
        content = target.read_bytes()
        if hashlib.sha256(content).hexdigest() != sha:
            raise ValueError(f"managed benchmark artifact hash mismatch: {path}")
        files[path] = content
        expected_paths.add(path)

    actual_paths = {
        path.relative_to(source).as_posix()
        for path in source.rglob("*")
        if path.is_file()
    }
    if actual_paths != expected_paths:
        raise ValueError("benchmark artifact source contains unexpected or missing managed files")

    try:
        result = json.loads(files["results.json"].decode("utf-8"))
    except (KeyError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("results.json is missing or invalid") from exc
    data = _validate_result_shape(result)
    if manifest.get("artifact_set_id") != data["benchmark_id"]:
        raise ValueError("benchmark manifest artifact_set_id does not match results.json")
    if manifest.get("created_at") != data["evaluated_at"]:
        raise ValueError("benchmark manifest created_at does not match results.json")
    if manifest.get("repository_sha") != data["repository_sha"]:
        raise ValueError("benchmark manifest repository_sha does not match results.json")
    expected_manifest = _build_manifest(data, _managed_files(data))
    if manifest != expected_manifest:
        raise ValueError("benchmark artifact manifest does not exactly match normative result")
    return data, {**files, "manifest.json": manifest_path.read_bytes()}
