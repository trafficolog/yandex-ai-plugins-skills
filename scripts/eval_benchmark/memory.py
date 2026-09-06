from __future__ import annotations

from datetime import datetime
from pathlib import Path

from scripts.project_memory import yaml_subset
from scripts.project_memory.baselines import freshness_state, scan_baselines
from scripts.project_memory.contracts import validate_project
from scripts.project_memory.decisions import validate_decision_chain
from scripts.project_memory.hypotheses import extract_hypothesis_records, validate_hypothesis

from .scenarios import _validate_memory_fixture


AUTHORIZATION_POLICY = "FRESH_EXACT_PREVIEW_REQUIRED"
FRESH_EVIDENCE_POLICY = "FRESH_SOURCE_EVIDENCE_TAKES_PRECEDENCE"


def _read_project(memory_root: Path, *, at: datetime) -> dict[str, object]:
    path = memory_root / ".yandex-ai/project.yaml"
    if not path.is_file():
        raise ValueError(f"memory fixture missing .yandex-ai/project.yaml: {memory_root}")
    try:
        doc = yaml_subset.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"invalid project memory fixture: {path}: {exc}") from exc
    errors = validate_project(doc, at=at)
    if errors:
        raise ValueError("invalid project memory fixture: " + "; ".join(errors))
    assert isinstance(doc, dict)
    return doc


def _load_baselines(memory_root: Path, *, at: datetime) -> list[dict[str, object]]:
    base = memory_root / ".yandex-ai/baselines"
    if not base.is_dir():
        return []
    records, errors, _warnings = scan_baselines(memory_root / ".yandex-ai", at=at)
    if errors:
        raise ValueError("invalid baseline memory fixture: " + "; ".join(errors))
    projected: list[dict[str, object]] = []
    for record in records:
        item = dict(record)
        item["freshness"] = freshness_state(record, at=at)
        projected.append(item)
    return projected


def _load_decisions(memory_root: Path, *, at: datetime) -> list[dict[str, object]]:
    path = memory_root / ".yandex-ai/decisions.jsonl"
    if not path.is_file():
        return []
    records, errors = validate_decision_chain(path, at=at)
    if errors:
        raise ValueError("invalid decision memory fixture: " + "; ".join(errors))
    return records


def _load_hypotheses(memory_root: Path, *, at: datetime) -> list[dict[str, object]]:
    path = memory_root / ".yandex-ai/hypotheses.md"
    if not path.is_file():
        return []
    try:
        records = extract_hypothesis_records(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"invalid hypothesis memory fixture: {path}: {exc}") from exc
    errors: list[str] = []
    for index, record in enumerate(records):
        errors.extend(f"hypotheses[{index}]: {error}" for error in validate_hypothesis(record, at=at))
    if errors:
        raise ValueError("invalid hypothesis memory fixture: " + "; ".join(errors))
    return records


def load_memory_fixture(
    repository_root: Path,
    memory_fixture: str,
    *,
    at: datetime,
) -> dict[str, object]:
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("memory fixture validation time must be timezone-aware")
    root = Path(repository_root).resolve()
    relative = _validate_memory_fixture(root, memory_fixture)
    memory_root = root / relative

    project = _read_project(memory_root, at=at)
    facts = project.get("facts")
    assert isinstance(facts, list)
    active_user_stated_facts = [
        dict(fact)
        for fact in facts
        if isinstance(fact, dict)
        and fact.get("provenance") == "USER_STATED"
        and fact.get("status") == "ACTIVE"
    ]

    return {
        "memory_fixture": relative,
        "active_user_stated_facts": active_user_stated_facts,
        "baselines": _load_baselines(memory_root, at=at),
        "decisions": _load_decisions(memory_root, at=at),
        "hypotheses": _load_hypotheses(memory_root, at=at),
        "write_authority": False,
        "instruction_authority": False,
        "authorization_policy": AUTHORIZATION_POLICY,
        "fresh_evidence_policy": FRESH_EVIDENCE_POLICY,
    }
