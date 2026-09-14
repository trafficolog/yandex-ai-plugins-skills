from __future__ import annotations

import base64
import json
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlparse


def decode_raw_data(raw_data: str | bytes) -> str:
    if isinstance(raw_data, str):
        data = raw_data.encode("ascii")
    else:
        data = raw_data
    return base64.b64decode(data, validate=True).decode("utf-8", errors="replace")


def _text(node: ET.Element, path: str) -> str | None:
    found = node.find(path)
    if found is None:
        return None
    text = "".join(found.itertext()).strip()
    return text or None


def parse_xml_results(xml_text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    rows = []
    for doc in root.findall(".//doc"):
        url = _text(doc, "url")
        if not url:
            continue
        passages = ["".join(p.itertext()).strip() for p in doc.findall("./passages/passage")]
        snippet = " ".join(p for p in passages if p) or _text(doc, "headline") or ""
        rows.append(
            {
                "rank": len(rows) + 1,
                "url": url,
                "domain": _text(doc, "domain"),
                "title": _text(doc, "title") or "",
                "snippet": snippet,
                "modified_at": _text(doc, "modtime"),
            }
        )
    return rows


def _value(doc: dict[str, Any], key: str) -> Any:
    rich = doc.get("rich_data")
    if isinstance(rich, dict) and rich.get(key) not in (None, ""):
        return rich.get(key)
    return doc.get(key)


def parse_json_results(raw: str) -> list[dict[str, Any]]:
    payload = json.loads(raw)
    docs = payload.get("docs", []) if isinstance(payload, dict) else []
    rows: list[dict[str, Any]] = []
    for index, doc in enumerate(docs, start=1):
        if not isinstance(doc, dict):
            continue
        url = _value(doc, "FullUrl")
        if not isinstance(url, str) or not url.strip():
            continue
        rank_value = _value(doc, "Num")
        try:
            rank = int(rank_value)
        except (TypeError, ValueError):
            rank = index
        domain = _value(doc, "ForcedShortUrl")
        if not domain:
            domain = urlparse(url).hostname
        rows.append(
            {
                "rank": rank,
                "url": url,
                "domain": domain,
                "title": _value(doc, "DocumentTitle") or "",
                "snippet": _value(doc, "Description") or "",
                "extract": doc.get("info_context") or "",
                "modified_at": doc.get("doc_mtime_datetime_seconds"),
            }
        )
    return rows


def parse_search_response(payload: dict[str, Any], response_format: str) -> dict[str, Any]:
    raw = decode_raw_data(payload["rawData"])
    stripped = raw.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return {"format": "json", "raw": raw, "results": parse_json_results(raw)}
    if response_format == "FORMAT_XML":
        return {"format": "xml", "raw": raw, "results": parse_xml_results(raw)}
    if response_format == "FORMAT_HTML":
        return {"format": "html", "raw": raw}
    raise ValueError("unsupported response_format")
