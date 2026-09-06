from __future__ import annotations

import json
import math
from pathlib import Path
import re
from typing import Any


PROJECT_SCHEMA = "yandex-ai-project/v1"
_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_NUMBER_RE = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$")


class ProjectMemoryError(ValueError):
    pass


def _scalar(text: str, line: int) -> object:
    if text == "true":
        return True
    if text == "false":
        return False
    if text == "null":
        return None
    if text == "[]":
        return []
    if text == "{}":
        return {}
    if text.startswith('"'):
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProjectMemoryError(f"line {line}: invalid JSON string") from exc
        if not isinstance(value, str):
            raise ProjectMemoryError(f"line {line}: quoted scalar must be a string")
        return value
    if _NUMBER_RE.fullmatch(text):
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProjectMemoryError(f"line {line}: invalid number") from exc
        if isinstance(value, float) and not math.isfinite(value):
            raise ProjectMemoryError(f"line {line}: non-finite number")
        return value
    raise ProjectMemoryError(f"line {line}: unsupported scalar syntax")


def _split_entry(content: str, line: int) -> tuple[str, str]:
    if ":" not in content:
        raise ProjectMemoryError(f"line {line}: expected mapping entry")
    key, rest = content.split(":", 1)
    if not _KEY_RE.fullmatch(key):
        raise ProjectMemoryError(f"line {line}: unsupported mapping key")
    if rest and not rest.startswith(" "):
        raise ProjectMemoryError(f"line {line}: mapping values require one separating space")
    return key, rest[1:] if rest else ""


def _loads_yaml_subset(text: str) -> object:
    if "\t" in text:
        raise ProjectMemoryError("tabs are not supported")
    lines: list[tuple[int, str, int]] = []
    for number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise ProjectMemoryError(f"line {number}: indentation must use 2-space steps")
        lines.append((indent, raw[indent:].rstrip(" "), number))
    if not lines or lines[0][0] != 0:
        raise ProjectMemoryError("project YAML must have a zero-indented root")

    def parse_block(index: int, indent: int) -> tuple[object, int]:
        if index >= len(lines) or lines[index][0] != indent:
            raise ProjectMemoryError("invalid nested block")
        content = lines[index][1]
        return parse_sequence(index, indent) if content == "-" or content.startswith("- ") else parse_mapping(index, indent)

    def parse_mapping(index: int, indent: int) -> tuple[dict[str, object], int]:
        result: dict[str, object] = {}
        while index < len(lines):
            actual, content, number = lines[index]
            if actual < indent:
                break
            if actual > indent:
                raise ProjectMemoryError(f"line {number}: unexpected indentation")
            if content == "-" or content.startswith("- "):
                raise ProjectMemoryError(f"line {number}: mixed sequence and mapping")
            key, rest = _split_entry(content, number)
            if key in result:
                raise ProjectMemoryError(f"line {number}: duplicate key {key}")
            index += 1
            if rest:
                result[key] = _scalar(rest, number)
            else:
                if index >= len(lines) or lines[index][0] != indent + 2:
                    raise ProjectMemoryError(f"line {number}: missing nested value")
                result[key], index = parse_block(index, indent + 2)
        return result, index

    def parse_mapping_item(index: int, sequence_indent: int, first_content: str, first_line: int) -> tuple[dict[str, object], int]:
        mapping_indent = sequence_indent + 2
        result: dict[str, object] = {}

        def consume(current: int, content: str, number: int) -> int:
            key, rest = _split_entry(content, number)
            if key in result:
                raise ProjectMemoryError(f"line {number}: duplicate key {key}")
            current += 1
            if rest:
                result[key] = _scalar(rest, number)
                return current
            if current >= len(lines) or lines[current][0] != mapping_indent + 2:
                raise ProjectMemoryError(f"line {number}: missing nested value")
            result[key], current = parse_block(current, mapping_indent + 2)
            return current

        index = consume(index, first_content, first_line)
        while index < len(lines):
            actual, content, number = lines[index]
            if actual <= sequence_indent:
                break
            if actual != mapping_indent or content == "-" or content.startswith("- "):
                raise ProjectMemoryError(f"line {number}: invalid sequence mapping indentation")
            index = consume(index, content, number)
        return result, index

    def parse_sequence(index: int, indent: int) -> tuple[list[object], int]:
        result: list[object] = []
        while index < len(lines):
            actual, content, number = lines[index]
            if actual < indent:
                break
            if actual > indent:
                raise ProjectMemoryError(f"line {number}: unexpected indentation")
            if content != "-" and not content.startswith("- "):
                raise ProjectMemoryError(f"line {number}: mixed mapping and sequence")
            rest = content[1:]
            if rest.startswith(" "):
                rest = rest[1:]
            index += 1
            if not rest:
                if index >= len(lines) or lines[index][0] != indent + 2:
                    raise ProjectMemoryError(f"line {number}: missing sequence item")
                value, index = parse_block(index, indent + 2)
                result.append(value)
            elif ":" in rest:
                value, index = parse_mapping_item(index - 1, indent, rest, number)
                result.append(value)
            else:
                result.append(_scalar(rest, number))
        return result, index

    value, end = parse_block(0, 0)
    if end != len(lines):
        raise ProjectMemoryError(f"line {lines[end][2]}: trailing content")
    return value


def load_project_context(project_root: Path) -> dict[str, Any] | None:
    path = Path(project_root) / ".yandex-ai" / "project.yaml"
    if not path.exists():
        return None
    try:
        doc = _loads_yaml_subset(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise ProjectMemoryError(f"cannot read {path}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != PROJECT_SCHEMA:
        raise ProjectMemoryError(f"project memory must use schema {PROJECT_SCHEMA}")
    project = doc.get("project")
    facts = doc.get("facts")
    if not isinstance(project, dict) or not isinstance(facts, list):
        raise ProjectMemoryError("project memory requires project mapping and facts list")
    project_id = project.get("id")
    name = project.get("name")
    if not isinstance(project_id, str) or not project_id or not isinstance(name, str) or not name:
        raise ProjectMemoryError("project memory requires non-empty project.id and project.name")

    active: list[dict[str, Any]] = []
    active_keys: set[str] = set()
    fact_ids: set[str] = set()
    for raw in facts:
        if not isinstance(raw, dict):
            raise ProjectMemoryError("each project fact must be a mapping")
        fact_id = raw.get("fact_id")
        key = raw.get("key")
        provenance = raw.get("provenance")
        status = raw.get("status")
        if not isinstance(fact_id, str) or not fact_id or fact_id in fact_ids:
            raise ProjectMemoryError("facts require unique non-empty fact_id")
        fact_ids.add(fact_id)
        if not isinstance(key, str) or not key:
            raise ProjectMemoryError("facts require non-empty key")
        if provenance != "USER_STATED":
            raise ProjectMemoryError("project facts must use USER_STATED provenance")
        if status not in {"ACTIVE", "SUPERSEDED"}:
            raise ProjectMemoryError("project fact status must be ACTIVE or SUPERSEDED")
        if "value" not in raw:
            raise ProjectMemoryError("project fact value is required")
        if status == "ACTIVE":
            if key in active_keys:
                raise ProjectMemoryError(f"multiple ACTIVE facts for key {key}")
            active_keys.add(key)
            item = {
                "fact_id": fact_id,
                "key": key,
                "value": raw["value"],
                "stated_at": raw.get("stated_at"),
                "provenance": "USER_STATED",
            }
            active.append(item)
    active.sort(key=lambda item: (item["key"], item["fact_id"]))
    return {"id": project_id, "name": name, "user_stated": active}
