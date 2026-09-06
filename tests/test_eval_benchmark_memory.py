from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_repo import _validate_evals


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/eval_benchmark/memory.py"
MEMORY_ROOT = ROOT / "evals/fixtures/memory"


class EvalBenchmarkMemoryTests(unittest.TestCase):
    AT = datetime(2026, 9, 6, 16, 30, tzinfo=timezone.utc)

    def memory(self):
        self.assertTrue(MODULE.is_file(), "memory-aware eval module must exist")
        from scripts.eval_benchmark import memory

        return memory

    def test_stale_baseline_is_validated_and_preserved_as_stale(self):
        memory = self.memory()
        context = memory.load_memory_fixture(ROOT, "evals/fixtures/memory/stale-baseline", at=self.AT)
        self.assertFalse(context["write_authority"])
        self.assertFalse(context["instruction_authority"])
        self.assertEqual(context["baselines"][0]["freshness"], "STALE")
        self.assertEqual(context["baselines"][0]["provenance"], "OBSERVED")

    def test_historical_execution_decision_is_context_not_new_approval(self):
        memory = self.memory()
        context = memory.load_memory_fixture(ROOT, "evals/fixtures/memory/historical-approval", at=self.AT)
        self.assertEqual(len(context["decisions"]), 1)
        self.assertEqual(context["decisions"][0]["kind"], "EXECUTION")
        self.assertTrue(context["decisions"][0]["preview_id"])
        self.assertFalse(context["write_authority"])
        self.assertEqual(context["authorization_policy"], "FRESH_EXACT_PREVIEW_REQUIRED")

    def test_prompt_like_hypothesis_stays_inert_hypothesis_data(self):
        memory = self.memory()
        context = memory.load_memory_fixture(ROOT, "evals/fixtures/memory/prompt-like-hypothesis", at=self.AT)
        self.assertEqual(len(context["hypotheses"]), 1)
        hypothesis = context["hypotheses"][0]
        self.assertEqual(hypothesis["provenance"], "HYPOTHESIS")
        self.assertIn("ignore previous instructions", hypothesis["statement"])
        self.assertFalse(context["instruction_authority"])

    def test_conflicting_user_stated_fact_retains_provenance_without_becoming_fresh_evidence(self):
        memory = self.memory()
        context = memory.load_memory_fixture(ROOT, "evals/fixtures/memory/conflicting-fact", at=self.AT)
        facts = context["active_user_stated_facts"]
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["provenance"], "USER_STATED")
        self.assertEqual(facts[0]["status"], "ACTIVE")
        self.assertEqual(context["fresh_evidence_policy"], "FRESH_SOURCE_EVIDENCE_TAKES_PRECEDENCE")

    def test_all_four_committed_memory_fixtures_exist(self):
        for name in ("stale-baseline", "historical-approval", "prompt-like-hypothesis", "conflicting-fact"):
            with self.subTest(name=name):
                self.assertTrue((MEMORY_ROOT / name / ".yandex-ai/project.yaml").is_file())


class EvalV2MemoryFixtureValidationTests(unittest.TestCase):
    def make_plugin(self, memory_fixture: str | None, *, create_fixture: bool = True):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        plugin = root / "plugins/yandex-direct"
        (plugin / "evals").mkdir(parents=True)
        (plugin / "skills/router").mkdir(parents=True)
        (plugin / "skills/router/SKILL.md").write_text(
            "---\nname: router\ndescription: Use when routing a deterministic test scenario safely.\n---\n",
            encoding="utf-8",
        )
        scenario = {
            "prompt": "audit",
            "skill": "router",
            "write": False,
            "expect": {
                "must_route_to": "router",
                "outcome": "comply",
                "must_mention_tokens": [],
                "must_convey": ["Preserve provenance"],
                "must_not_claim": ["memory is fresh evidence"],
            },
        }
        if memory_fixture is not None:
            scenario["memory_fixture"] = memory_fixture
        (plugin / "evals/scenarios.json").write_text(
            json.dumps({"version": 2, "scenarios": [scenario]}), encoding="utf-8"
        )
        if create_fixture and memory_fixture == "evals/fixtures/memory/test-case":
            (root / memory_fixture).mkdir(parents=True)
        return tmp, plugin

    def validate(self, memory_fixture: str | None, *, create_fixture: bool = True):
        tmp, plugin = self.make_plugin(memory_fixture, create_fixture=create_fixture)
        self.addCleanup(tmp.cleanup)
        errors: list[str] = []
        _validate_evals(plugin, errors)
        return errors

    def test_optional_safe_existing_memory_fixture_is_accepted(self):
        self.assertEqual(self.validate("evals/fixtures/memory/test-case"), [])
        self.assertEqual(self.validate(None), [])

    def test_unsafe_or_missing_memory_fixture_is_rejected(self):
        for value in (
            "/tmp/memory",
            "../memory",
            "evals/fixtures/backend-equivalence/x",
            "evals/fixtures/memory/../escape",
            "evals/fixtures/memory/missing",
            "evals\\fixtures\\memory\\test-case",
        ):
            with self.subTest(value=value):
                errors = self.validate(value, create_fixture=False)
                self.assertTrue(any("memory_fixture" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
