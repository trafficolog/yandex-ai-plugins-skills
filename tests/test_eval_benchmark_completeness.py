from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/eval_benchmark/artifacts.py"


def semantic(subject_model: str, *, self_judged: bool = False, fake_judge: bool = False) -> dict[str, object]:
    judge_model = subject_model if self_judged else "independent-judge"
    judge_runtime = "repository-fake" if fake_judge else "provider-runtime"
    return {
        "judge_identity": [judge_runtime, "1", judge_model, "2026-09"],
        "subject_identity": ["provider-runtime", "1", subject_model, "2026-09"],
        "judge_mode": "SELF_JUDGED" if self_judged else "INDEPENDENT",
        "judge": {
            "adapter_id": "fake-judge-adapter" if fake_judge else "real-judge-adapter",
            "adapter_version": "1",
            "runtime": {"name": judge_runtime, "version": "1"},
            "model": {"name": judge_model, "version": "2026-09"},
            "fake": fake_judge,
        },
        "route": {"expected": "router", "actual": "router", "state": "PASS", "rationale": "structured route"},
        "outcome": {"expected": "comply", "actual": "comply", "state": "PASS"},
        "must_convey": [{"expectation": "preserve provenance", "state": "PASS", "evidence": ["preserve provenance"], "rationale": "literal"}],
        "must_not_claim": [{"expectation": "write already authorized", "state": "PASS", "evidence": [], "rationale": "absent"}],
        "rationale": "bounded semantic verdict",
    }


def scenario(index: int, model: str, *, self_judged: bool = False, fake_judge: bool = False) -> dict[str, object]:
    return {
        "plugin": "yandex-direct" if index == 1 else "yandex-seo",
        "scenario_id": ("a" if index == 1 else "b") * 64,
        "source_path": f"plugins/{'yandex-direct' if index == 1 else 'yandex-seo'}/evals/scenarios.json",
        "source_sha256": ("c" if index == 1 else "d") * 64,
        "memory_fixture": "evals/fixtures/memory/stale-baseline" if index == 2 else None,
        "memory_context_sha256": "e" * 64 if index == 2 else None,
        "state": "PASS",
        "subject": {
            "schema": "yandex-ai-eval-adapter-response/v1",
            "invocation_id": f"subject-{index}",
            "adapter_id": f"real-subject-adapter-{index}",
            "adapter_version": "1",
            "runtime": {"name": "provider-runtime", "version": "1"},
            "model": {"name": model, "version": "2026-09"},
            "output": {"text": "TOKEN preserve provenance", "route": "router", "outcome": "comply"},
        },
        "mechanical": [{"token": "TOKEN", "present": True, "state": "PASS"}],
        "semantic": semantic(model, self_judged=self_judged, fake_judge=fake_judge),
    }


def complete_run() -> dict[str, object]:
    return {
        "evaluated_at": "2026-09-06T18:00:00Z",
        "repository_sha": "f" * 40,
        "scenarios": [scenario(1, "subject-model-a"), scenario(2, "subject-model-b")],
        "aggregate": {"passed": 2, "failed": 0, "undetermined": 0, "total": 2},
        "subject_identities": [
            {
                "adapter_id": "real-subject-adapter-1",
                "adapter_version": "1",
                "runtime": {"name": "provider-runtime", "version": "1"},
                "model": {"name": "subject-model-a", "version": "2026-09"},
                "fake": False,
            },
            {
                "adapter_id": "real-subject-adapter-2",
                "adapter_version": "1",
                "runtime": {"name": "provider-runtime", "version": "1"},
                "model": {"name": "subject-model-b", "version": "2026-09"},
                "fake": False,
            },
        ],
        "completeness": "INFRASTRUCTURE_READY",
        "comparative_complete": False,
    }


class EvalBenchmarkCompletenessTests(unittest.TestCase):
    def artifacts(self):
        self.assertTrue(MODULE.is_file())
        from scripts.eval_benchmark import artifacts

        return artifacts

    def test_complete_real_evidence_is_classified_comparative_complete(self):
        artifacts = self.artifacts()
        result = artifacts.build_result_document(
            complete_run(),
            backend_equivalence={"state": "PASS", "differences": []},
            memory_results={"passed": 1, "failed": 0, "undetermined": 0, "total": 1},
        )
        self.assertEqual(result["completeness"], "COMPARATIVE_COMPLETE")
        self.assertTrue(result["comparative_complete"])

    def test_fake_subject_or_judge_can_never_be_comparative_complete(self):
        artifacts = self.artifacts()
        fake_subject = complete_run()
        fake_subject["subject_identities"][0]["fake"] = True  # type: ignore[index]
        fake_subject["completeness"] = "COMPARATIVE_COMPLETE"
        fake_subject["comparative_complete"] = True
        result = artifacts.build_result_document(
            fake_subject,
            backend_equivalence={"state": "PASS"},
            memory_results={"passed": 1, "failed": 0, "undetermined": 0, "total": 1},
        )
        self.assertEqual(result["completeness"], "INFRASTRUCTURE_READY")
        self.assertFalse(result["comparative_complete"])

        fake_judge = complete_run()
        fake_judge["scenarios"][0]["semantic"] = semantic("subject-model-a", fake_judge=True)  # type: ignore[index]
        result = artifacts.build_result_document(
            fake_judge,
            backend_equivalence={"state": "PASS"},
            memory_results={"passed": 1, "failed": 0, "undetermined": 0, "total": 1},
        )
        self.assertFalse(result["comparative_complete"])

    def test_self_judge_missing_backend_or_missing_memory_blocks_completion(self):
        artifacts = self.artifacts()
        self_judged = complete_run()
        self_judged["scenarios"][0]["semantic"] = semantic("subject-model-a", self_judged=True)  # type: ignore[index]
        cases = [
            (self_judged, {"state": "PASS"}, {"passed": 1, "failed": 0, "undetermined": 0, "total": 1}),
            (complete_run(), {"state": "FAIL"}, {"passed": 1, "failed": 0, "undetermined": 0, "total": 1}),
            (complete_run(), {"state": "PASS"}, None),
        ]
        for run, backend, memory in cases:
            with self.subTest(backend=backend, memory=memory is not None):
                result = artifacts.build_result_document(run, backend_equivalence=backend, memory_results=memory)
                self.assertEqual(result["completeness"], "INFRASTRUCTURE_READY")
                self.assertFalse(result["comparative_complete"])

    def test_mechanical_and_semantic_evidence_are_both_required(self):
        artifacts = self.artifacts()
        no_mechanical = complete_run()
        for item in no_mechanical["scenarios"]:  # type: ignore[index]
            item["mechanical"] = []
        result = artifacts.build_result_document(
            no_mechanical,
            backend_equivalence={"state": "PASS"},
            memory_results={"passed": 1, "failed": 0, "undetermined": 0, "total": 1},
        )
        self.assertFalse(result["comparative_complete"])

        no_semantic_evidence = complete_run()
        for item in no_semantic_evidence["scenarios"]:  # type: ignore[index]
            item["semantic"]["must_convey"] = []
            item["semantic"]["must_not_claim"] = []
        result = artifacts.build_result_document(
            no_semantic_evidence,
            backend_equivalence={"state": "PASS"},
            memory_results={"passed": 1, "failed": 0, "undetermined": 0, "total": 1},
        )
        self.assertFalse(result["comparative_complete"])


if __name__ == "__main__":
    unittest.main()
