import ast
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs" / "CONTRACT_MATRIX.json"
VALIDATOR = ROOT / "scripts" / "validate_repo.py"


class ProjectMemoryRepositoryContractTests(unittest.TestCase):
    def test_project_memory_runtime_surface_is_complete_and_stdlib_only(self):
        required = [
            "scripts/ya_project.py",
            "scripts/project_memory/__init__.py",
            "scripts/project_memory/yaml_subset.py",
            "scripts/project_memory/contracts.py",
            "scripts/project_memory/storage.py",
            "scripts/project_memory/decisions.py",
            "scripts/project_memory/baselines.py",
            "scripts/project_memory/hypotheses.py",
        ]
        for relative in required:
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file(), relative)

        allowed_internal = {"project_memory", "scripts"}
        for relative in required:
            path = ROOT / relative
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                module = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name.split(".", 1)[0]
                        self.assertTrue(
                            module in sys.stdlib_module_names or module in allowed_internal,
                            f"third-party import {module!r} in {relative}",
                        )
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    module = node.module.split(".", 1)[0]
                    self.assertTrue(
                        module in sys.stdlib_module_names or module in allowed_internal,
                        f"third-party import {module!r} in {relative}",
                    )

    def test_repository_validator_registers_project_memory_surface(self):
        source = VALIDATOR.read_text(encoding="utf-8")
        self.assertIn("PROJECT_MEMORY_REQUIRED_PATHS", source)
        self.assertIn("_validate_project_memory_repository_surface", source)
        self.assertIn("repository.project-memory-contract", source)
        self.assertNotIn('root / ".yandex-ai"', source)

    def test_contract_matrix_traces_four_project_memory_domains(self):
        matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
        rows = {row["id"]: row for row in matrix["contracts"]}
        expected = {
            "repository.project-memory-contract": {
                "scripts/ya_project.py",
                "scripts/project_memory/contracts.py",
            },
            "repository.project-memory-decisions": {
                "scripts/project_memory/decisions.py",
            },
            "repository.project-memory-baselines": {
                "scripts/project_memory/baselines.py",
            },
            "repository.project-memory-hypotheses": {
                "scripts/project_memory/hypotheses.py",
            },
        }
        for contract_id, helpers in expected.items():
            with self.subTest(contract=contract_id):
                self.assertIn(contract_id, rows)
                row = rows[contract_id]
                self.assertEqual(row["plugin"], "repository")
                self.assertEqual(row["status"], "infrastructure")
                self.assertEqual(row["skills"], [])
                self.assertTrue(helpers.issubset(set(row["helpers"])))
                self.assertTrue(row["test_refs"])
                self.assertTrue(row["references"])
                self.assertEqual(row["freshness_controlled_references"], [])

    def test_ru_en_docs_define_authorization_freshness_and_data_boundaries(self):
        pairs = [
            (ROOT / "docs" / "ARCHITECTURE.md", ROOT / "docs" / "ARCHITECTURE.en.md"),
            (ROOT / "docs" / "GETTING_STARTED.md", ROOT / "docs" / "GETTING_STARTED.en.md"),
            (ROOT / "SECURITY.md", ROOT / "SECURITY.en.md"),
        ]
        required_tokens = (
            "yandex-ai-project/v1",
            "yandex-ai-decision/v1",
            "yandex-ai-baseline/v1",
            "yandex-ai-hypothesis/v1",
            "USER_STATED",
            "HYPOTHESIS",
            "DERIVED",
            "record-execution",
            "add-baseline",
            "result",
            "STALE",
            "preview_id",
            "--ack-bulk",
        )
        for ru_path, en_path in pairs:
            for path in (ru_path, en_path):
                text = path.read_text(encoding="utf-8")
                for token in required_tokens:
                    with self.subTest(path=path.name, token=token):
                        self.assertIn(token, text)

        ru_security = (ROOT / "SECURITY.md").read_text(encoding="utf-8").lower()
        en_security = (ROOT / "SECURITY.en.md").read_text(encoding="utf-8").lower()
        self.assertIn("память проекта не является разрешением на запись", ru_security)
        self.assertIn("project memory is not write permission", en_security)
        self.assertIn("не является полной dlp", ru_security)
        self.assertIn("not a complete dlp", en_security)


if __name__ == "__main__":
    unittest.main()
