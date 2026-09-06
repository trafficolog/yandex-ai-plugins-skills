#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import sys
from typing import Any

try:
    from . import validate_repo_core as _core
except ImportError:
    import validate_repo_core as _core

# Preserve the established validator API, including private helpers used by
# repository regression tests, while layering repository-owned P1 validation.
for _name in dir(_core):
    if not _name.startswith("__") and _name not in {"validate_repository", "main"}:
        globals()[_name] = getattr(_core, _name)

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
    matrix_path = root.resolve() / "docs/CONTRACT_MATRIX.json"
    try:
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return errors
    errors.extend(
        _validate_project_memory_repository_surface(
            root.resolve(),
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
