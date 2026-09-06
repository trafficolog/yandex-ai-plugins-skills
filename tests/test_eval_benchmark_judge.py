from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
JUDGE_PATH = ROOT / "scripts/eval_benchmark/judge.py"
MECHANICAL_PATH = ROOT / "scripts/eval_benchmark/mechanical.py"


class EvalBenchmarkJudgeTests(unittest.TestCase):
    def modules(self):
        self.assertTrue(MECHANICAL_PATH.is_file(), "mechanical eval module must exist")
        self.assertTrue(JUDGE_PATH.is_file(), "semantic judge module must exist")
        from scripts.eval_benchmark import judge, mechanical

        return judge, mechanical

    def expectations(self) -> dict[str, object]:
        return {
            "must_route_to": "router",
            "outcome": "comply_with_limitations",
            "must_mention_tokens": ["OBSERVED"],
            "must_convey": ["State the source limitation"],
            "must_not_claim": ["full evidence is available"],
        }

    def subject(self, *, model: str = "subject-model") -> dict[str, object]:
        return {
            "schema": "yandex-ai-eval-adapter-response/v1",
            "invocation_id": "subject-1",
            "adapter_id": "subject-adapter",
            "adapter_version": "1",
            "runtime": {"name": "runtime", "version": "1"},
            "model": {"name": model, "version": "2026-09"},
            "output": {
                "text": "OBSERVED: Metrika is unavailable, so performance evidence is limited.",
                "route": "router",
                "outcome": "comply_with_limitations",
            },
        }

    def judge_response(self, *, model: str = "judge-model") -> dict[str, object]:
        return {
            "schema": "yandex-ai-eval-adapter-response/v1",
            "invocation_id": "judge-1",
            "adapter_id": "judge-adapter",
            "adapter_version": "1",
            "runtime": {"name": "runtime", "version": "1"},
            "model": {"name": model, "version": "2026-09"},
            "output": {
                "observed_outcome": "comply_with_limitations",
                "route": {"state": "PASS", "actual": "router", "rationale": "correct route"},
                "must_convey": [
                    {
                        "expectation": "State the source limitation",
                        "state": "PASS",
                        "evidence": ["performance evidence is limited"],
                        "rationale": "limitation is explicit",
                    }
                ],
                "must_not_claim": [
                    {
                        "expectation": "full evidence is available",
                        "state": "PASS",
                        "evidence": [],
                        "rationale": "forbidden claim is absent",
                    }
                ],
                "rationale": "subject preserves the limitation",
            },
        }

    def write_judge_adapter(self, *, model: str) -> list[str]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "judge_adapter.py"
        response = self.judge_response(model=model)
        path.write_text(
            textwrap.dedent(
                f"""
                import json, sys
                request = json.loads(sys.stdin.readline())
                response = {json.dumps(response)!r}
                response = json.loads(response)
                response["invocation_id"] = request["invocation_id"]
                print(json.dumps(response))
                """
            ),
            encoding="utf-8",
        )
        return [sys.executable, str(path)]

    def test_exact_tokens_are_case_sensitive_mechanical_evidence(self):
        _, mechanical = self.modules()
        result = mechanical.evaluate_exact_tokens("OBSERVED observed", ["OBSERVED", "Observed"])
        self.assertEqual(
            result,
            [
                {"token": "OBSERVED", "present": True, "state": "PASS"},
                {"token": "Observed", "present": False, "state": "FAIL"},
            ],
        )

    def test_self_judge_is_rejected_by_default(self):
        judge, _ = self.modules()
        scenario = {"expect": self.expectations()}
        with self.assertRaisesRegex(ValueError, "independent"):
            judge.evaluate_semantics(
                self.subject(),
                scenario,
                judge_argv=self.write_judge_adapter(model="subject-model"),
            )

    def test_explicit_self_judge_is_marked_and_not_hidden(self):
        judge, _ = self.modules()
        result = judge.evaluate_semantics(
            self.subject(),
            {"expect": self.expectations()},
            judge_argv=self.write_judge_adapter(model="subject-model"),
            allow_self_judge=True,
        )
        self.assertEqual(result["judge_mode"], "SELF_JUDGED")

    def test_conveyed_claim_pass_requires_literal_evidence_when_cited(self):
        judge, _ = self.modules()
        response = self.judge_response()
        response["output"]["must_convey"][0]["evidence"] = ["not present in subject output"]
        normalized = judge.validate_judge_response(
            self.subject()["output"]["text"], self.expectations(), response
        )
        self.assertEqual(normalized["must_convey"][0]["state"], "UNDETERMINED")

    def test_absence_pass_needs_no_excerpt_but_failure_needs_literal_evidence(self):
        judge, _ = self.modules()
        valid_absence = judge.validate_judge_response(
            self.subject()["output"]["text"], self.expectations(), self.judge_response()
        )
        self.assertEqual(valid_absence["must_not_claim"][0]["state"], "PASS")

        response = self.judge_response()
        response["output"]["must_not_claim"][0].update(
            {"state": "FAIL", "evidence": ["invented forbidden quote"]}
        )
        normalized = judge.validate_judge_response(
            self.subject()["output"]["text"], self.expectations(), response
        )
        self.assertEqual(normalized["must_not_claim"][0]["state"], "UNDETERMINED")

    def test_invalid_semantic_state_is_rejected(self):
        judge, _ = self.modules()
        response = self.judge_response()
        response["output"]["must_convey"][0]["state"] = "MAYBE"
        with self.assertRaisesRegex(ValueError, "PASS.*FAIL.*UNDETERMINED"):
            judge.validate_judge_response(
                self.subject()["output"]["text"], self.expectations(), response
            )

    def test_hidden_reasoning_fields_are_rejected(self):
        judge, _ = self.modules()
        response = self.judge_response()
        response["output"]["chain_of_thought"] = "private reasoning"
        with self.assertRaisesRegex(ValueError, "hidden reasoning"):
            judge.validate_judge_response(
                self.subject()["output"]["text"], self.expectations(), response
            )

    def test_scenario_state_is_fail_then_undetermined_then_pass(self):
        judge, _ = self.modules()
        semantic_pass = {
            "route": {"state": "PASS"},
            "outcome": {"state": "PASS"},
            "must_convey": [{"state": "PASS"}],
            "must_not_claim": [{"state": "PASS"}],
        }
        self.assertEqual(
            judge.scenario_state([{"state": "FAIL"}], semantic_pass), "FAIL"
        )
        uncertain = json.loads(json.dumps(semantic_pass))
        uncertain["must_convey"][0]["state"] = "UNDETERMINED"
        self.assertEqual(
            judge.scenario_state([{"state": "PASS"}], uncertain), "UNDETERMINED"
        )
        failed = json.loads(json.dumps(semantic_pass))
        failed["must_not_claim"][0]["state"] = "FAIL"
        self.assertEqual(judge.scenario_state([{"state": "PASS"}], failed), "FAIL")
        self.assertEqual(
            judge.scenario_state([{"state": "PASS"}], semantic_pass), "PASS"
        )


if __name__ == "__main__":
    unittest.main()
