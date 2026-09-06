from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]

P3_PATHS = {
    "scripts/ya_eval.py",
    "scripts/eval_benchmark/__init__.py",
    "scripts/eval_benchmark/protocol.py",
    "scripts/eval_benchmark/scenarios.py",
    "scripts/eval_benchmark/runner.py",
    "scripts/eval_benchmark/judge.py",
    "scripts/eval_benchmark/mechanical.py",
    "scripts/eval_benchmark/backend_trace.py",
    "scripts/eval_benchmark/memory.py",
    "scripts/eval_benchmark/artifacts.py",
    "scripts/eval_benchmark/snapshots.py",
    "evals/adapters/fake_subject.py",
    "evals/adapters/fake_judge.py",
    "evals/adapters/fake_connected_backend.py",
    "evals/fixtures/backend-equivalence/direct-consequential.json",
}

P3_CONTRACT_IDS = {
    "repository.eval-adapter-protocol",
    "repository.eval-independent-judge",
    "repository.eval-backend-equivalence",
    "repository.eval-memory-adversarial",
    "repository.eval-immutable-artifacts",
    "repository.eval-completeness-classification",
}

EXPECTED_TEST_REFS = {
    "repository.eval-adapter-protocol": {
        "tests/test_eval_benchmark_protocol.py::EvalBenchmarkProtocolTests::test_valid_roundtrip_and_model_identity",
        "tests/test_eval_benchmark_protocol.py::EvalBenchmarkProtocolTests::test_timeout_fails_closed",
    },
    "repository.eval-independent-judge": {
        "tests/test_eval_benchmark_judge.py::EvalBenchmarkJudgeTests::test_self_judge_is_rejected_by_default",
        "tests/test_eval_benchmark_judge.py::EvalBenchmarkJudgeTests::test_conveyed_claim_pass_requires_literal_evidence_when_cited",
    },
    "repository.eval-backend-equivalence": {
        "tests/test_eval_benchmark_backend_trace.py::EvalBenchmarkBackendTraceTests::test_bundled_direct_fixture_blocks_before_transport_then_simulates_exact_execution",
        "tests/test_eval_benchmark_backend_trace.py::EvalBenchmarkBackendTraceTests::test_native_preview_may_differ_when_binding_and_gate_are_equivalent",
    },
    "repository.eval-memory-adversarial": {
        "tests/test_eval_benchmark_memory.py::EvalBenchmarkMemoryTests::test_stale_baseline_is_validated_and_preserved_as_stale",
        "tests/test_eval_benchmark_memory.py::EvalBenchmarkMemoryTests::test_historical_execution_decision_is_context_not_new_approval",
    },
    "repository.eval-immutable-artifacts": {
        "tests/test_eval_benchmark_artifacts.py::EvalBenchmarkArtifactTests::test_publish_is_immutable_exact_replay_and_manifest_hashes_every_managed_file",
        "tests/test_eval_benchmark_snapshots.py::EvalBenchmarkSnapshotTests::test_tampered_source_manifest_hash_fails_before_snapshot_creation",
    },
    "repository.eval-completeness-classification": {
        "tests/test_eval_benchmark_completeness.py::EvalBenchmarkCompletenessTests::test_complete_real_evidence_is_classified_comparative_complete",
        "tests/test_eval_benchmark_completeness.py::EvalBenchmarkCompletenessTests::test_fake_subject_or_judge_can_never_be_comparative_complete",
    },
}


class P3EvalBenchmarkRepositoryContractTests(unittest.TestCase):
    def test_p3_runtime_surface_is_complete_and_stdlib_only(self):
        for relative in sorted(P3_PATHS):
            self.assertTrue((ROOT / relative).is_file(), relative)

        allowed_internal = {"scripts", "eval_benchmark"}
        python_paths = [
            "scripts/ya_eval.py",
            *sorted(
                path.relative_to(ROOT).as_posix()
                for path in (ROOT / "scripts/eval_benchmark").glob("*.py")
            ),
        ]
        for relative in python_paths:
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative)
            for node in ast.walk(tree):
                roots: list[str] = []
                if isinstance(node, ast.Import):
                    roots.extend(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    roots.append(node.module.split(".", 1)[0])
                for root in roots:
                    self.assertTrue(
                        root in sys.stdlib_module_names or root in allowed_internal,
                        f"P3 core must remain stdlib-only; {relative} imports {root!r}",
                    )

    def test_repository_validator_registers_p3_surface(self):
        from scripts import validate_repo

        self.assertEqual(set(validate_repo.P3_EVAL_REQUIRED_PATHS), P3_PATHS)
        self.assertEqual(set(validate_repo.P3_EVAL_CONTRACT_IDS), P3_CONTRACT_IDS)
        errors = validate_repo._validate_p3_eval_repository_surface(
            ROOT,
            declared_contract_ids=P3_CONTRACT_IDS,
        )
        self.assertEqual(errors, [])

    def test_contract_matrix_traces_six_p3_domains(self):
        matrix = json.loads((ROOT / "docs/CONTRACT_MATRIX.json").read_text(encoding="utf-8"))
        rows = {
            row["id"]: row
            for row in matrix["contracts"]
            if isinstance(row, dict) and row.get("id") in P3_CONTRACT_IDS
        }
        self.assertEqual(set(rows), P3_CONTRACT_IDS)
        for contract_id, expected_refs in EXPECTED_TEST_REFS.items():
            row = rows[contract_id]
            self.assertEqual(row["plugin"], "repository")
            self.assertEqual(row["status"], "infrastructure")
            self.assertTrue(expected_refs.issubset(set(row["test_refs"])), contract_id)
            self.assertTrue(row["helpers"], contract_id)

    def test_ru_en_docs_distinguish_infrastructure_from_comparative_evidence(self):
        pairs = [
            ("README.md", "README.en.md"),
            ("docs/ARCHITECTURE.md", "docs/ARCHITECTURE.en.md"),
            ("docs/GETTING_STARTED.md", "docs/GETTING_STARTED.en.md"),
            ("SECURITY.md", "SECURITY.en.md"),
            ("docs/ROADMAP.md", "docs/ROADMAP.en.md"),
        ]
        for ru_path, en_path in pairs:
            with self.subTest(pair=(ru_path, en_path)):
                ru = (ROOT / ru_path).read_text(encoding="utf-8")
                en = (ROOT / en_path).read_text(encoding="utf-8")
                for marker in ("INFRASTRUCTURE_READY", "COMPARATIVE_COMPLETE"):
                    self.assertIn(marker, ru)
                    self.assertIn(marker, en)

        readme_ru = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_en = (ROOT / "README.en.md").read_text(encoding="utf-8")
        getting_ru = (ROOT / "docs/GETTING_STARTED.md").read_text(encoding="utf-8")
        getting_en = (ROOT / "docs/GETTING_STARTED.en.md").read_text(encoding="utf-8")
        for text in (readme_ru, readme_en, getting_ru, getting_en):
            self.assertIn("python scripts/ya_eval.py check", text)
            self.assertIn("provider-neutral", text.lower())

        security_ru = (ROOT / "SECURITY.md").read_text(encoding="utf-8").lower()
        security_en = (ROOT / "SECURITY.en.md").read_text(encoding="utf-8").lower()
        for text in (security_ru, security_en):
            self.assertIn("adapter", text)
            self.assertIn("untrusted", text)
            self.assertIn("snapshot", text)
            self.assertIn("authoriz", text)
            self.assertIn("download", text)

        roadmap_ru = (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8")
        roadmap_en = (ROOT / "docs/ROADMAP.en.md").read_text(encoding="utf-8")
        self.assertIn("P3", roadmap_ru)
        self.assertIn("P3", roadmap_en)
        self.assertIn("INFRASTRUCTURE_READY", roadmap_ru)
        self.assertIn("INFRASTRUCTURE_READY", roadmap_en)
        for text in (roadmap_ru.lower(), roadmap_en.lower()):
            self.assertTrue(
                "no live" in text or "не выполнялся" in text or "не проводился" in text,
                "Roadmap must state that no accepted live multi-model benchmark exists",
            )


if __name__ == "__main__":
    unittest.main()
