from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
import math
from typing import Any


SCHEMA = "seo-weekly-organic-report/v1"
CLAIM_CLASSES = {"OBSERVED", "DERIVED", "HYPOTHESIS", "METHODOLOGY"}
COVERAGE_STATES = {"COMPLETE", "PARTIAL", "MISSING"}
SECRET_KEYS = {
    "authorization", "password", "passwd", "secret", "api_key", "apikey",
    "credential", "credentials", "access_token", "refresh_token", "oauth_token",
}


def canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"value is not canonical JSON: {exc}") from exc


def _validate_finite(value: Any, path: str = "root") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} contains a non-finite number")
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_finite(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_finite(item, f"{path}[{index}]")


def _validate_secret_keys(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for raw_key, item in value.items():
            key = str(raw_key).lower().replace("-", "_")
            if (
                key in SECRET_KEYS
                or key.endswith("_password")
                or key.endswith("_secret")
                or key.endswith("_token")
                or key.endswith("_api_key")
            ):
                raise ValueError(f"secret-like managed field is forbidden: {path}.{raw_key}")
            _validate_secret_keys(item, f"{path}.{raw_key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_secret_keys(item, f"{path}[{index}]")


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _validate_generated_at(value: str) -> str:
    text = _require_string(value, "generated_at")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("generated_at must be RFC3339/ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("generated_at must include a timezone")
    return text


def _validate_period(value: Any, field: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    start_text = _require_string(value.get("from"), f"{field}.from")
    end_text = _require_string(value.get("to"), f"{field}.to")
    try:
        start = date.fromisoformat(start_text)
        end = date.fromisoformat(end_text)
    except ValueError as exc:
        raise ValueError(f"{field} dates must use YYYY-MM-DD") from exc
    if start > end:
        raise ValueError(f"{field}.from must be <= {field}.to")
    return {"from": start.isoformat(), "to": end.isoformat()}


def _validate_project(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("project must be an object")
    result: dict[str, Any] = {
        "id": _require_string(value.get("id"), "project.id"),
        "name": _require_string(value.get("name"), "project.name"),
    }
    if "user_stated" in value:
        if not isinstance(value["user_stated"], list):
            raise ValueError("project.user_stated must be a list")
        result["user_stated"] = deepcopy(value["user_stated"])
    return result


def _validate_coverage(value: Any, field: str) -> str:
    if value not in COVERAGE_STATES:
        raise ValueError(f"{field} must be one of {sorted(COVERAGE_STATES)}")
    return str(value)


def _validate_limitations(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    result: list[str] = []
    for item in value:
        text = _require_string(item, f"{field}[]")
        if text not in result:
            result.append(text)
    return result


def _normalize_source(payload: dict[str, Any], name: str) -> tuple[str, dict[str, Any], list[str], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    raw = payload.get(name)
    if raw is None:
        return "MISSING", {}, [f"{name.upper()}_MISSING"], [], [], []
    if not isinstance(raw, dict):
        raise ValueError(f"{name} must be an object")
    coverage = _validate_coverage(raw.get("coverage"), f"{name}.coverage")
    source = raw.get("source", {})
    if not isinstance(source, dict):
        raise ValueError(f"{name}.source must be an object")
    limitations = _validate_limitations(raw.get("limitations", []), f"{name}.limitations")
    if coverage == "PARTIAL" and not limitations:
        limitations.append(f"{name.upper()}_PARTIAL")
    if coverage == "MISSING":
        if f"{name.upper()}_MISSING" not in limitations:
            limitations.append(f"{name.upper()}_MISSING")
        source = {}
    evidence = raw.get("evidence", [])
    if not isinstance(evidence, list):
        raise ValueError(f"{name}.evidence must be a list")
    query_rows = raw.get("query_rows", [])
    page_rows = raw.get("page_rows", [])
    if not isinstance(query_rows, list) or not isinstance(page_rows, list):
        raise ValueError(f"{name} query_rows/page_rows must be lists")
    return coverage, deepcopy(source), limitations, deepcopy(evidence), deepcopy(query_rows), deepcopy(page_rows)


def _normalize_evidence(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], set[str]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in items:
        if not isinstance(raw, dict):
            raise ValueError("each evidence record must be an object")
        evidence_id = _require_string(raw.get("evidence_id"), "evidence.evidence_id")
        if evidence_id in seen:
            raise ValueError(f"duplicate evidence_id: {evidence_id}")
        claim_class = raw.get("claim_class")
        if claim_class not in CLAIM_CLASSES:
            raise ValueError(f"evidence.claim_class must be one of {sorted(CLAIM_CLASSES)}")
        source = _require_string(raw.get("source"), "evidence.source")
        item = deepcopy(raw)
        item["evidence_id"] = evidence_id
        item["claim_class"] = claim_class
        item["source"] = source
        if claim_class == "METHODOLOGY" and (item.get("metric") is not None or item.get("value") is not None):
            raise ValueError("METHODOLOGY evidence cannot carry metric/value")
        normalized.append(item)
        seen.add(evidence_id)
    normalized.sort(key=lambda item: item["evidence_id"])
    return normalized, seen


def _metric_delta(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, dict[str, float | int]]:
    metrics: dict[str, dict[str, float | int]] = {}
    for key in sorted(set(current) & set(previous)):
        now = current[key]
        before = previous[key]
        if isinstance(now, bool) or isinstance(before, bool):
            continue
        if not isinstance(now, (int, float)) or not isinstance(before, (int, float)):
            continue
        metrics[key] = {"current": now, "previous": before, "delta": now - before}
    return metrics


def _normalize_movers(rows: list[dict[str, Any]], *, kind: str, evidence_ids: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    id_field = "query_id" if kind == "query" else "page_id"
    label_field = "query" if kind == "query" else "url"
    movers: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in rows:
        if not isinstance(raw, dict):
            raise ValueError(f"each {kind} row must be an object")
        item_id = _require_string(raw.get(id_field), f"{kind}.{id_field}")
        if item_id in seen:
            raise ValueError(f"duplicate {id_field}: {item_id}")
        seen.add(item_id)
        label = _require_string(raw.get(label_field), f"{kind}.{label_field}")
        current = raw.get("current")
        previous = raw.get("previous")
        if not isinstance(current, dict) or not isinstance(previous, dict):
            raise ValueError(f"{kind}.current and previous must be objects")
        refs = raw.get("evidence_ids", [])
        if not isinstance(refs, list):
            raise ValueError(f"{kind}.evidence_ids must be a list")
        normalized_refs = [_require_string(ref, f"{kind}.evidence_ids[]") for ref in refs]
        unknown = set(normalized_refs) - evidence_ids
        if unknown:
            raise ValueError(f"{kind} row references unknown evidence IDs: {sorted(unknown)}")
        metrics = _metric_delta(current, previous)
        mover = {
            id_field: item_id,
            label_field: label,
            "metrics": metrics,
            "evidence_ids": normalized_refs,
        }
        movers.append(mover)
        if metrics and normalized_refs:
            findings.append({
                "finding_id": f"{kind}:{item_id}",
                "kind": f"{kind.upper()}_CHANGE",
                "claim_class": "DERIVED",
                "subject_id": item_id,
                "subject": label,
                "metrics": deepcopy(metrics),
                "evidence_ids": normalized_refs,
            })
    movers.sort(key=lambda item: item[id_field])
    findings.sort(key=lambda item: item["finding_id"])
    return movers, findings


def semantic_report_id(report_without_id: dict[str, Any]) -> str:
    if not isinstance(report_without_id, dict):
        raise ValueError("report must be an object")
    semantic = deepcopy(report_without_id)
    semantic.pop("report_id", None)
    semantic.pop("generated_at", None)
    digest = hashlib.sha256(canonical_json_bytes(semantic)).hexdigest()
    return digest[:24]


def normalize_report_input(payload: dict[str, Any], *, generated_at: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    _validate_finite(payload)
    _validate_secret_keys(payload)
    generated = _validate_generated_at(generated_at)
    project = _validate_project(payload.get("project"))
    period = _validate_period(payload.get("period"), "period")
    comparison = _validate_period(payload.get("comparison_period"), "comparison_period")
    if date.fromisoformat(comparison["to"]) >= date.fromisoformat(period["from"]):
        raise ValueError("comparison_period must end before period starts")

    wm_coverage, wm_source, wm_limits, wm_evidence, wm_queries, wm_pages = _normalize_source(payload, "webmaster")
    m_coverage, m_source, m_limits, m_evidence, m_queries, m_pages = _normalize_source(payload, "metrika")

    evidence, known_evidence = _normalize_evidence(wm_evidence + m_evidence)
    query_movers, query_findings = _normalize_movers(wm_queries + m_queries, kind="query", evidence_ids=known_evidence)
    page_movers, page_findings = _normalize_movers(wm_pages + m_pages, kind="page", evidence_ids=known_evidence)

    limitations: list[str] = []
    for item in wm_limits + m_limits:
        if item not in limitations:
            limitations.append(item)

    delegated = payload.get("delegated_previews", [])
    if not isinstance(delegated, list):
        raise ValueError("delegated_previews must be a list")
    normalized_delegated: list[dict[str, Any]] = []
    for raw in delegated:
        if not isinstance(raw, dict):
            raise ValueError("each delegated preview must be an object")
        item = deepcopy(raw)
        item["preview_id"] = _require_string(item.get("preview_id"), "delegated_preview.preview_id")
        item["owner"] = _require_string(item.get("owner"), "delegated_preview.owner")
        item["operation"] = _require_string(item.get("operation"), "delegated_preview.operation")
        if item.get("status") != "PREVIEW":
            raise ValueError("delegated preview status must be PREVIEW")
        normalized_delegated.append(item)
    normalized_delegated.sort(key=lambda item: item["preview_id"])

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at": generated,
        "project": project,
        "period": period,
        "comparison_period": comparison,
        "coverage": {"metrika": m_coverage, "webmaster": wm_coverage},
        "sources": {"metrika": m_source, "webmaster": wm_source},
        "summary": {
            "query_movers": len(query_movers),
            "page_movers": len(page_movers),
            "findings": len(query_findings) + len(page_findings),
            "limitations": len(limitations),
        },
        "query_movers": query_movers,
        "page_movers": page_movers,
        "findings": query_findings + page_findings,
        "limitations": limitations,
        "evidence": evidence,
        "delegated_previews": normalized_delegated,
    }
    if "structures" in payload:
        structures = payload["structures"]
        if not isinstance(structures, dict):
            raise ValueError("structures must be an object")
        report["structures"] = deepcopy(structures)
    _validate_finite(report)
    report["report_id"] = semantic_report_id(report)
    canonical_json_bytes(report)
    return report
