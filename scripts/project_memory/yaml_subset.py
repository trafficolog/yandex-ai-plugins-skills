from __future__ import annotations

import json
import math
import re


_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_NUMBER_RE = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$")


class YamlSubsetError(ValueError):
    pass


def _scalar(text: str, *, line: int) -> object:
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
            raise YamlSubsetError(f"line {line}: invalid JSON string") from exc
        if not isinstance(value, str):
            raise YamlSubsetError(f"line {line}: quoted scalar must be a string")
        return value
    if _NUMBER_RE.fullmatch(text):
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise YamlSubsetError(f"line {line}: invalid number") from exc
        if isinstance(value, float) and not math.isfinite(value):
            raise YamlSubsetError(f"line {line}: non-finite numbers are not supported")
        return value
    raise YamlSubsetError(f"line {line}: unsupported scalar syntax")


def _parse_key(text: str, *, line: int) -> str:
    if not _KEY_RE.fullmatch(text):
        raise YamlSubsetError(f"line {line}: unsupported mapping key")
    return text


def _split_mapping_entry(content: str, *, line: int) -> tuple[str, str]:
    if ":" not in content:
        raise YamlSubsetError(f"line {line}: expected mapping entry")
    key_text, value_text = content.split(":", 1)
    key = _parse_key(key_text, line=line)
    if value_text and not value_text.startswith(" "):
        raise YamlSubsetError(f"line {line}: mapping values require one separating space")
    return key, value_text[1:] if value_text else ""


def _prepare(text: str) -> list[tuple[int, str, int]]:
    if "\t" in text:
        raise YamlSubsetError("tabs are not supported")
    lines: list[tuple[int, str, int]] = []
    for line_number, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent % 2:
            raise YamlSubsetError(f"line {line_number}: indentation must use 2-space steps")
        content = raw[indent:].rstrip(" ")
        if content:
            lines.append((indent, content, line_number))
    if not lines:
        raise YamlSubsetError("document is empty")
    if lines[0][0] != 0:
        raise YamlSubsetError(f"line {lines[0][2]}: root indentation must be zero")
    return lines


def loads(text: str) -> object:
    lines = _prepare(text)

    def parse_block(index: int, indent: int) -> tuple[object, int]:
        if index >= len(lines):
            raise YamlSubsetError("unexpected end of document")
        actual_indent, content, line_number = lines[index]
        if actual_indent != indent:
            raise YamlSubsetError(
                f"line {line_number}: expected indentation {indent}, got {actual_indent}"
            )
        if content == "-" or content.startswith("- "):
            return parse_sequence(index, indent)
        return parse_mapping(index, indent)

    def parse_mapping(index: int, indent: int) -> tuple[dict[str, object], int]:
        result: dict[str, object] = {}
        while index < len(lines):
            actual_indent, content, line_number = lines[index]
            if actual_indent < indent:
                break
            if actual_indent > indent:
                raise YamlSubsetError(f"line {line_number}: unexpected indentation")
            if content == "-" or content.startswith("- "):
                raise YamlSubsetError(f"line {line_number}: mixed sequence and mapping")
            key, rest = _split_mapping_entry(content, line=line_number)
            if key in result:
                raise YamlSubsetError(f"line {line_number}: duplicate mapping key {key!r}")
            index += 1
            if rest:
                result[key] = _scalar(rest, line=line_number)
            else:
                if index >= len(lines) or lines[index][0] <= indent:
                    raise YamlSubsetError(f"line {line_number}: missing nested value")
                if lines[index][0] != indent + 2:
                    raise YamlSubsetError(
                        f"line {lines[index][2]}: nested value must indent by exactly 2 spaces"
                    )
                value, index = parse_block(index, indent + 2)
                result[key] = value
        return result, index

    def parse_mapping_item(
        index: int, sequence_indent: int, first_content: str, first_line: int
    ) -> tuple[dict[str, object], int]:
        mapping_indent = sequence_indent + 2
        result: dict[str, object] = {}

        def consume_entry(current_index: int, content: str, line_number: int) -> int:
            key, rest = _split_mapping_entry(content, line=line_number)
            if key in result:
                raise YamlSubsetError(f"line {line_number}: duplicate mapping key {key!r}")
            current_index += 1
            if rest:
                result[key] = _scalar(rest, line=line_number)
                return current_index
            if current_index >= len(lines) or lines[current_index][0] <= mapping_indent:
                raise YamlSubsetError(f"line {line_number}: missing nested value")
            if lines[current_index][0] != mapping_indent + 2:
                raise YamlSubsetError(
                    f"line {lines[current_index][2]}: nested value must indent by exactly 2 spaces"
                )
            value, current_index = parse_block(current_index, mapping_indent + 2)
            result[key] = value
            return current_index

        index = consume_entry(index, first_content, first_line)
        while index < len(lines):
            actual_indent, content, line_number = lines[index]
            if actual_indent <= sequence_indent:
                break
            if actual_indent != mapping_indent:
                raise YamlSubsetError(
                    f"line {line_number}: unexpected indentation in sequence mapping"
                )
            if content == "-" or content.startswith("- "):
                raise YamlSubsetError(
                    f"line {line_number}: sequence item cannot replace mapping entry"
                )
            index = consume_entry(index, content, line_number)
        return result, index

    def parse_sequence(index: int, indent: int) -> tuple[list[object], int]:
        result: list[object] = []
        while index < len(lines):
            actual_indent, content, line_number = lines[index]
            if actual_indent < indent:
                break
            if actual_indent > indent:
                raise YamlSubsetError(f"line {line_number}: unexpected indentation")
            if content != "-" and not content.startswith("- "):
                raise YamlSubsetError(f"line {line_number}: mixed mapping and sequence")
            rest = content[1:]
            if rest.startswith(" "):
                rest = rest[1:]
            index += 1
            if not rest:
                if index >= len(lines) or lines[index][0] <= indent:
                    raise YamlSubsetError(f"line {line_number}: missing sequence item")
                if lines[index][0] != indent + 2:
                    raise YamlSubsetError(
                        f"line {lines[index][2]}: sequence child must indent by exactly 2 spaces"
                    )
                value, index = parse_block(index, indent + 2)
                result.append(value)
            elif ":" in rest:
                value, index = parse_mapping_item(index - 1, indent, rest, line_number)
                result.append(value)
            else:
                result.append(_scalar(rest, line=line_number))
        return result, index

    value, end = parse_block(0, 0)
    if end != len(lines):
        raise YamlSubsetError(f"line {lines[end][2]}: trailing content")
    return value


def _scalar_text(value: object) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise YamlSubsetError("non-finite numbers are not supported")
        return json.dumps(value, ensure_ascii=False, allow_nan=False)
    if value == []:
        return "[]"
    if value == {}:
        return "{}"
    raise YamlSubsetError(f"unsupported value type: {type(value).__name__}")


def _is_inline(value: object) -> bool:
    return (
        isinstance(value, (str, int, float, bool))
        or value is None
        or value == []
        or value == {}
    )


def _validate_value(value: object) -> None:
    if _is_inline(value):
        _scalar_text(value)
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
                raise YamlSubsetError(f"unsupported mapping key {key!r}")
            _validate_value(child)
        return
    if isinstance(value, list):
        for child in value:
            _validate_value(child)
        return
    raise YamlSubsetError(f"unsupported value type: {type(value).__name__}")


def dumps(value: object) -> str:
    _validate_value(value)
    lines: list[str] = []

    def emit(current: object, indent: int) -> None:
        prefix = " " * indent
        if isinstance(current, dict):
            if not current:
                lines.append(prefix + "{}")
                return
            for key, child in current.items():
                if _is_inline(child):
                    lines.append(f"{prefix}{key}: {_scalar_text(child)}")
                else:
                    lines.append(f"{prefix}{key}:")
                    emit(child, indent + 2)
            return
        if isinstance(current, list):
            if not current:
                lines.append(prefix + "[]")
                return
            for child in current:
                if _is_inline(child):
                    lines.append(f"{prefix}- {_scalar_text(child)}")
                elif isinstance(child, dict) and child:
                    items = list(child.items())
                    first_key, first_value = items[0]
                    if _is_inline(first_value):
                        lines.append(f"{prefix}- {first_key}: {_scalar_text(first_value)}")
                    else:
                        lines.append(f"{prefix}- {first_key}:")
                        emit(first_value, indent + 4)
                    for key, item_value in items[1:]:
                        item_prefix = " " * (indent + 2)
                        if _is_inline(item_value):
                            lines.append(f"{item_prefix}{key}: {_scalar_text(item_value)}")
                        else:
                            lines.append(f"{item_prefix}{key}:")
                            emit(item_value, indent + 4)
                else:
                    lines.append(prefix + "-")
                    emit(child, indent + 2)
            return
        lines.append(prefix + _scalar_text(current))

    emit(value, 0)
    return "\n".join(lines) + "\n"
