from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from .protocol import canonical_json_bytes


EVAL_VERSION = 2
MEMORY_FIXTURE_PREFIX = ("evals", "fixtures", "memory")


def scenario_id(plugin_name: str, scenario: dict[str, object]) -> str:
    if not isinstance(plugin_name, str) or not plugin_name:
        raise ValueError("plugin_name must be a non-empty string")
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be an object")
    preimage = plugin_name.encode("utf-8") + b"\n" + canonical_json_bytes(scenario)
    return hashlib.sha256(preimage).hexdigest()


def _validate_memory_fixture(repository_root: Path, value: object) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise ValueError("memory_fixture must be a safe repository-relative POSIX path")
    if value.startswith("/") or "//" in value:
        raise ValueError("memory_fixture must be a safe repository-relative POSIX path")
    pure = PurePosixPath(value)
    parts = pure.parts
    if len(parts) <= len(MEMORY_FIXTURE_PREFIX) or tuple(parts[:3]) != MEMORY_FIXTURE_PREFIX:
        raise ValueError("memory_fixture must stay under evals/fixtures/memory/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("memory_fixture cannot contain traversal segments")
    root = repository_root.resolve()
    memory_root = (root / "evals/fixtures/memory").resolve()
    target = (root / Path(*parts)).resolve()
    try:
        target.relative_to(memory_root)
    except ValueError as exc:
        raise ValueError("memory_fixture escapes evals/fixtures/memory/") from exc
    if not target.is_dir():
        raise ValueError(f"memory_fixture does not exist: {value}")
    return value


def _validate_scenario_shape(scenario: object, *, where: str) -> dict[str, Any]:
    if not isinstance(scenario, dict):
        raise ValueError(f"{where} must be an object")
    for key in ("prompt", "skill"):
        if not isinstance(scenario.get(key), str) or not str(scenario[key]).strip():
            raise ValueError(f"{where}.{key} must be a non-empty string")
    write = scenario.get("write")
    if write is not False and write not in {"preview-first", "approval-required"}:
        raise ValueError(f"{where}.write has invalid eval-v2 value")
    expect = scenario.get("expect")
    if not isinstance(expect, dict):
        raise ValueError(f"{where}.expect must be an object")
    route = expect.get("must_route_to")
    if not isinstance(route, str) or route != scenario.get("skill"):
        raise ValueError(f"{where}.expect.must_route_to must match skill")
    if expect.get("outcome") not in {"comply", "comply_with_limitations", "refuse"}:
        raise ValueError(f"{where}.expect.outcome has invalid eval-v2 value")
    for field in ("must_mention_tokens", "must_convey", "must_not_claim"):
        values = expect.get(field)
        if not isinstance(values, list) or any(not isinstance(item, str) or not item.strip() for item in values):
            raise ValueError(f"{where}.expect.{field} must be a list of non-empty strings")
    canonical_json_bytes(scenario)
    return scenario


def load_scenarios(
    repository_root: Path,
    plugin_names: list[str] | None = None,
) -> list[dict[str, object]]:
    root = repository_root.resolve()
    plugins_root = root / "plugins"
    if plugin_names is None:
        names = sorted(
            path.name
            for path in plugins_root.iterdir()
            if path.is_dir() and (path / "evals/scenarios.json").is_file()
        )
    else:
        if any(not isinstance(name, str) or not name or "/" in name or "\\" in name or name in {".", ".."} for name in plugin_names):
            raise ValueError("plugin names must be immediate-child directory names")
        names = sorted(set(plugin_names))

    records: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for plugin_name in names:
        source = plugins_root / plugin_name / "evals/scenarios.json"
        if not source.is_file():
            raise ValueError(f"missing eval-v2 source for plugin {plugin_name}: {source}")
        source_bytes = source.read_bytes()
        try:
            data = json.loads(source_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid eval-v2 JSON for plugin {plugin_name}") from exc
        if not isinstance(data, dict) or data.get("version") != EVAL_VERSION:
            raise ValueError(f"eval source for {plugin_name} must use version 2")
        scenario_values = data.get("scenarios")
        if not isinstance(scenario_values, list) or not scenario_values:
            raise ValueError(f"eval source for {plugin_name} must contain scenarios")
        source_sha256 = hashlib.sha256(source_bytes).hexdigest()
        for index, raw_scenario in enumerate(scenario_values):
            scenario = _validate_scenario_shape(raw_scenario, where=f"{plugin_name}.scenarios[{index}]")
            derived_id = scenario_id(plugin_name, scenario)
            if derived_id in seen_ids:
                raise ValueError(f"duplicate scenario_id: {derived_id}")
            seen_ids.add(derived_id)
            record: dict[str, object] = {
                "plugin": plugin_name,
                "source_path": source.relative_to(root).as_posix(),
                "source_sha256": source_sha256,
                "scenario_id": derived_id,
                "scenario": scenario,
            }
            if "memory_fixture" in scenario:
                record["memory_fixture"] = _validate_memory_fixture(root, scenario["memory_fixture"])
            records.append(record)
    return sorted(records, key=lambda item: (str(item["plugin"]), str(item["scenario_id"])))
