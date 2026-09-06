from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/eval_benchmark/artifacts.py"


def sample_run() -> dict[str, object]:
    return {
        "evaluated_at": "2026-09-06T17:00:00Z",
        "repository_sha": "a" * 40,
        "scenarios": [
            {
                "plugin": "yandex-direct",
                "scenario_id": "b" * 64,
                "source_path": "plugins/yandex-direct/evals/scenarios.json",
                "source_sha256": "c" * 64,
                "state": "PASS",
                "subject": {
                    "schema": "yandex-ai-eval-adapter-response/v1",
                    "invocation_id": "subject-demo",
                    "adapter_id": "fake-subject",
                    "adapter_version": "1",
                    "runtime": {"name": "python", "version": "3.13"},
                    "model": {"name": "fake-model-a", "version": "1"},
                    "output": {
                        "text": "<unsafe> preview_id is required",
                        "route": "yandex-direct-api",
                        "outcome": "comply",
                    },
                },
                "mechanical": [{"token": "preview_id", "state": "PASS"}],
                "semantic": {
                    "judge_identity": ["python", "3.13", "fake-judge", "1"],
                    "subject_identity": ["python", "3.13", "fake-model-a", "1"],
                    "judge_mode": "INDEPENDENT",
                    "route": {"expected": "yandex-direct-api", "actual": "yandex-direct-api", "state": "PASS", "rationale": ""},
                    "outcome": {"expected": "comply", "actual": "comply", "state": "PASS"},
                    "must_convey": [{"expectation": "Require preview", "state": "PASS", "evidence": ["preview_id is required"], "rationale": "literal evidence"}],
                    "must_not_claim": [{"expectation": "already executed", "state": "PASS", "evidence": [], "rationale": "absent"}],
                    "rationale": "bounded verdict",
                },
            }
        ],
        "aggregate": {"passed": 1, "failed": 0, "undetermined": 0, "total": 1},
        "subject_identities": [
            {
                "adapter_id": "fake-subject",
                "adapter_version": "1",
                "runtime": {"name": "python", "version": "3.13"},
                "model": {"name": "fake-model-a", "version": "1"},
                "fake": True,
            }
        ],
        "completeness": "INFRASTRUCTURE_READY",
        "comparative_complete": False,
    }


class EvalBenchmarkArtifactTests(unittest.TestCase):
    def artifacts(self):
        self.assertTrue(MODULE.is_file(), "benchmark artifacts module must exist")
        from scripts.eval_benchmark import artifacts

        return artifacts

    def test_result_schema_id_and_security_are_deterministic(self):
        artifacts = self.artifacts()
        first = artifacts.build_result_document(sample_run(), backend_equivalence={"state": "PASS"}, memory_results={"passed": 4, "total": 4})
        second = artifacts.build_result_document(sample_run(), backend_equivalence={"state": "PASS"}, memory_results={"passed": 4, "total": 4})
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "yandex-ai-benchmark-result/v1")
        self.assertRegex(first["benchmark_id"], r"^[0-9a-f]{64}$")
        poisoned = sample_run()
        poisoned["scenarios"][0]["subject"]["chain_of_thought"] = "private"  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "hidden|reasoning"):
            artifacts.build_result_document(poisoned)

    def test_html_is_self_contained_and_escapes_model_output(self):
        artifacts = self.artifacts()
        result = artifacts.build_result_document(sample_run())
        html = artifacts.render_comparison_html(result)
        self.assertIn("Content-Security-Policy", html)
        self.assertNotIn("<script", html.lower())
        self.assertNotIn("src=", html.lower())
        self.assertNotIn("http://", html.lower())
        self.assertNotIn("https://", html.lower())
        self.assertNotIn("<unsafe>", html)
        self.assertIn("&lt;unsafe&gt;", html)
        self.assertIn("INFRASTRUCTURE_READY", html)

    def test_publish_is_immutable_exact_replay_and_manifest_hashes_every_managed_file(self):
        artifacts = self.artifacts()
        result = artifacts.build_result_document(sample_run())
        with tempfile.TemporaryDirectory() as tmp:
            destination = artifacts.publish_benchmark_artifacts(Path(tmp), result)
            self.assertEqual(destination.name, result["benchmark_id"])
            manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema"], "yandex-ai-benchmark-manifest/v1")
            self.assertEqual(manifest["primary_artifact"], "results.json")
            paths = {item["path"] for item in manifest["files"]}
            self.assertIn("results.json", paths)
            self.assertIn("comparison.html", paths)
            self.assertTrue(any(path.startswith("runs/subject-") for path in paths))
            self.assertTrue(any(path.startswith("runs/judge-") for path in paths))
            self.assertNotIn("manifest.json", paths)
            for item in manifest["files"]:
                payload = (destination / item["path"]).read_bytes()
                self.assertEqual(item["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(artifacts.publish_benchmark_artifacts(Path(tmp), result), destination)
            original = (destination / "results.json").read_bytes()
            (destination / "results.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conflict|unexpected|hash|exact"):
                artifacts.publish_benchmark_artifacts(Path(tmp), result)
            self.assertEqual((destination / "results.json").read_text(encoding="utf-8"), "{}\n")
            self.assertNotEqual(original, (destination / "results.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
