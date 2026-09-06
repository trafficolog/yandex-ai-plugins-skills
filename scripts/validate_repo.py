#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any

try:
    from . import validate_repo_core as _core
except ImportError:
    import validate_repo_core as _core

# Preserve the established validator API, including private helpers used by
# repository regression tests, while layering repository-owned P1/P3 validation.
for _name in dir(_core):
    if not _name.startswith("__") and _name not in {"validate_repository", "main"}:
        globals()[_name] = getattr(_core, _name)

_CORE_VALIDATE_EVALS = _core._validate_evals
_MEMORY_FIXTURE_PREFIX = ("evals", "fixtures", "memory")

PROJECT_MEMORY_REQUIRED_PATHS = (
    "scripts/ya_project.py",
    "scripts/project_memory/__init__.py",
    "scripts/project_memory/yaml_subset.py",
    "scripts/project_memory/contracts.py",
    "scripts/project_memory/storage.py",
    "scripts/project_memory/decisions.py",
    "scripts/project_memory/baselines.py",
    "scripts/project_memory/hypotheses.py",
)
PROJECT_MEMORY_CONTRACT_IDS = {
    "repository.project-memory-contract",
    "repository.project-memory-decisions",
    "repository.project-memory-baselines",
    "repository.project-memory-hypotheses",
}
_PROJECT_MEMORY_INTERNAL_IMPORTS = {"project_memory", "scripts"}


def _project_memory_contract_ids(matrix: Any) -> set[str]:
    if not isinstance(matrix, dict):
        return set()
    contracts = matrix.get("contracts")
    if not isinstance(contracts, list):
        return set()
    return {
        row.get("id")
        for row in contracts
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }


def _validate_project_memory_repository_surface(
    root: Path,
    *,
    declared_contract_ids: set[str],
) -> list[str]:
    """Validate committed P1 runtime only when the repository declares P1."""
    if "repository.project-memory-contract" not in declared_contract_ids:
        return []

    errors: list[str] = []
    missing_contracts = PROJECT_MEMORY_CONTRACT_IDS - declared_contract_ids
    for contract_id in sorted(missing_contracts):
        errors.append(f"project memory contract row missing: {contract_id}")

    for relative in PROJECT_MEMORY_REQUIRED_PATHS:
        path = root / relative
        if not path.is_file():
            errors.append(f"project memory runtime path missing: {relative}")
            continue
        if path.suffix != ".py":
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            errors.append(f"project memory Python source is invalid: {relative}: {exc}")
            continue
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.append(node.module.split(".", 1)[0])
            for module in modules:
                if module not in sys.stdlib_module_names and module not in _PROJECT_MEMORY_INTERNAL_IMPORTS:
                    errors.append(
                        f"project memory runtime requires third-party import {module!r}: {relative}"
                    )
    return errors


def _validate_eval_memory_fixture_paths(plugin_path: Path, errors: list[str]) -> None:
    path = plugin_path / "evals/scenarios.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return
    if not isinstance(data, dict) or not isinstance(data.get("scenarios"), list):
        return

    repository_root = plugin_path.parents[1].resolve()
    fixture_root = (repository_root / "evals/fixtures/memory").resolve()
    for index, scenario in enumerate(data["scenarios"]):
        if not isinstance(scenario, dict) or "memory_fixture" not in scenario:
            continue
        value = scenario.get("memory_fixture")
        prefix = f"eval scenario #{index} memory_fixture"
        if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
            errors.append(f"{prefix} must be a safe repository-relative POSIX path: {path}")
            continue
        if value.startswith("/") or "//" in value:
            errors.append(f"{prefix} must be a safe repository-relative POSIX path: {path}")
            continue
        pure = PurePosixPath(value)
        parts = pure.parts
        if len(parts) <= len(_MEMORY_FIXTURE_PREFIX) or tuple(parts[:3]) != _MEMORY_FIXTURE_PREFIX:
            errors.append(f"{prefix} must stay under evals/fixtures/memory/: {path}")
            continue
        if any(part in {"", ".", ".."} for part in parts):
            errors.append(f"{prefix} cannot contain traversal segments: {path}")
            continue
        target = (repository_root / Path(*parts)).resolve()
        try:
            target.relative_to(fixture_root)
        except ValueError:
            errors.append(f"{prefix} escapes evals/fixtures/memory/: {path}")
            continue
        if not target.is_dir():
            errors.append(f"{prefix} does not exist: {value}: {path}")


def _validate_evals(plugin_path: Path, errors: list[str]) -> None:
    """Preserve eval-v2 validation and add the optional P3 memory fixture boundary."""
    _CORE_VALIDATE_EVALS(plugin_path, errors)
    _validate_eval_memory_fixture_paths(plugin_path, errors)


def validate_repository(
    root: Path,
    *,
    today=None,
    changed_paths: set[str] | None = None,
    strict_reference_freshness: bool = False,
) -> list[str]:
    errors = _core.validate_repository(
        root,
        today=today,
        changed_paths=changed_paths,
        strict_reference_freshness=strict_reference_freshness,
    )
    resolved_root = root.resolve()
    plugins_root = resolved_root / "plugins"
    if plugins_root.is_dir():
        for plugin_path in sorted(path for path in plugins_root.iterdir() if path.is_dir()):
            if (plugin_path / "evals/scenarios.json").is_file():
                _validate_eval_memory_fixture_paths(plugin_path, errors)

    matrix_path = resolved_root / "docs/CONTRACT_MATRIX.json"
    try:
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return errors
    errors.extend(
        _validate_project_memory_repository_surface(
            resolved_root,
            declared_contract_ids=_project_memory_contract_ids(matrix),
        )
    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate repository contracts")
    parser.add_argument("--changed-files-file", type=Path)
    parser.add_argument("--strict-reference-freshness", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    errors = validate_repository(
        root,
        changed_paths=_core._read_changed_paths(args.changed_files_file),
        strict_reference_freshness=args.strict_reference_freshness,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
