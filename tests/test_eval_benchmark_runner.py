from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts/eval_benchmark/runner.py"
FAKE_SUBJECT = ROOT / "evals/adapters/fake_subject.py"
FAKE_JUDGE = ROOT / "evals/adapters/fake_judge.py"


class EvalBenchmarkRunnerTests(unittest.TestCase):
    def runner(self):
        self.assertTrue(RUNNER_PATH.is_file(), "benchmark runner module must exist")
        self.assertTrue(FAKE_SUBJECT.is_file(), "deterministic fake subject adapter must exist")
        self.assertTrue(FAKE_JUDGE.is_file(), "deterministic fake judge adapter must exist")
        from scripts.eval_benchmark import runner

        return runner

    def record(self, scenario_id: str = "scenario-a") -> dict[str, object]:
        return {
            "plugin": "yandex-seo",
            "source_path": "plugins/yandex-seo/evals/scenarios.json",
            "source_sha256": "a" * 64,
            "scenario_id": scenario_id,
            "scenario": {
                "prompt": "Audit with partial evidence",
                "skill": "yandex-seo-audit",
                "write": False,
                "expect": {
                    "must_route_to": "yandex-seo-audit",
                    "outcome": "comply_with_limitations",
                    "must_mention_tokens": ["OBSERVED"],
                    "must_convey": ["State the source limitation"],
                    "must_not_claim": ["full evidence is available"],
                },
            },
        }

    def subject_argv(self) -> list[str]:
        return [sys.executable, str(FAKE_SUBJECT)]

    def judge_argv(self) -> list[str]:
        return [sys.executable, str(FAKE_JUDGE)]

    def test_run_scenario_records_subject_judge_and_separate_evidence(self):
        runner = self.runner()
        result = runner.run_scenario(
            self.record(), subject_argv=self.subject_argv(), judge_argv=self.judge_argv()
        )
        self.assertEqual(result["state"], "PASS")
        self.assertEqual(result["scenario_id"], "scenario-a")
        self.assertEqual(result["subject"]["model"]["name"], "fake-subject")
        self.assertEqual(result["semantic"]["judge_mode"], "INDEPENDENT")
        self.assertEqual(result["semantic"]["judge"]["adapter_id"], "fake-judge-adapter")
        self.assertTrue(result["semantic"]["judge"]["fake"])
        self.assertEqual(result["mechanical"][0]["token"], "OBSERVED")
        self.assertTrue(result["mechanical"][0]["present"])

    def test_memory_fixture_is_validated_and_passed_as_structured_inert_context(self):
        runner = self.runner()
        record = self.record("memory-scenario")
        scenario = record["scenario"]
        assert isinstance(scenario, dict)
        scenario["memory_fixture"] = "evals/fixtures/memory/stale-baseline"
        with tempfile.TemporaryDirectory() as tmp:
            adapter = Path(tmp) / "memory_subject.py"
            adapter.write_text(
                textwrap.dedent(
                    """
                    import json, sys
                    request = json.loads(sys.stdin.readline())
                    context = request["payload"].get("memory_context")
                    if not isinstance(context, dict):
                        raise SystemExit(7)
                    if context.get("write_authority") is not False or context.get("instruction_authority") is not False:
                        raise SystemExit(8)
                    baselines = context.get("baselines") or []
                    if not baselines or baselines[0].get("freshness") != "STALE":
                        raise SystemExit(9)
                    response = {
                        "schema": "yandex-ai-eval-adapter-response/v1",
                        "invocation_id": request["invocation_id"],
                        "adapter_id": "memory-subject-adapter",
                        "adapter_version": "1",
                        "runtime": {"name": "test-runtime", "version": "1"},
                        "model": {"name": "memory-subject", "version": "1"},
                        "output": {
                            "text": "OBSERVED. State the source limitation. Stale memory remains context only.",
                            "route": "yandex-seo-audit",
                            "outcome": "comply_with_limitations",
                        },
                    }
                    print(json.dumps(response, sort_keys=True))
                    """
                ),
                encoding="utf-8",
            )
            result = runner.run_scenario(
                record,
                subject_argv=[sys.executable, str(adapter)],
                judge_argv=self.judge_argv(),
                repository_root=ROOT,
                evaluated_at="2026-09-06T16:00:00Z",
            )
        self.assertEqual(result["state"], "PASS")
        self.assertEqual(result["memory_fixture"], "evals/fixtures/memory/stale-baseline")
        self.assertRegex(result["memory_context_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotIn("memory_context", result)

    def test_run_benchmark_is_stably_ordered_and_has_transparent_counts(self):
        runner = self.runner()
        records = [self.record("scenario-b"), self.record("scenario-a")]
        result = runner.run_benchmark(
            records,
            subject_argv=self.subject_argv(),
            judge_argv=self.judge_argv(),
            evaluated_at="2026-09-06T16:00:00Z",
            repository_sha="1" * 40,
        )
        self.assertEqual([item["scenario_id"] for item in result["scenarios"]], ["scenario-a", "scenario-b"])
        self.assertEqual(result["aggregate"], {"passed": 2, "failed": 0, "undetermined": 0, "total": 2})
        self.assertEqual(result["evaluated_at"], "2026-09-06T16:00:00Z")
        self.assertEqual(result["repository_sha"], "1" * 40)
        self.assertFalse(result["comparative_complete"])
        self.assertEqual(result["completeness"], "INFRASTRUCTURE_READY")

    def test_fake_adapters_are_explicitly_non_comparative(self):
        runner = self.runner()
        result = runner.run_benchmark(
            [self.record()],
            subject_argv=self.subject_argv(),
            judge_argv=self.judge_argv(),
            evaluated_at="2026-09-06T16:00:00Z",
            repository_sha="2" * 40,
        )
        self.assertEqual(result["subject_identities"][0]["adapter_id"], "fake-subject-adapter")
        self.assertTrue(result["subject_identities"][0]["fake"])
        self.assertFalse(result["comparative_complete"])


if __name__ == "__main__":
    unittest.main()
