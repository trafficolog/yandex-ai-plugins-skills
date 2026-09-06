from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = ROOT / "scripts/ya_eval.py"


class YaEvalCliTests(unittest.TestCase):
    def cli(self):
        self.assertTrue(CLI_PATH.is_file(), "repository eval CLI must exist")
        from scripts import ya_eval

        return ya_eval

    def test_adapter_argv_config_requires_json_string_array_not_shell_string(self):
        cli = self.cli()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "adapter.json"
            path.write_text(json.dumps(["python", "adapter.py"]), encoding="utf-8")
            self.assertEqual(cli.load_adapter_argv(path), ["python", "adapter.py"])
            path.write_text(json.dumps("python adapter.py"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "array"):
                cli.load_adapter_argv(path)
            path.write_text(json.dumps([]), encoding="utf-8")
            with self.assertRaises(ValueError):
                cli.load_adapter_argv(path)

    def test_check_validates_real_fixtures_without_adapter_execution(self):
        cli = self.cli()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = cli.main(["check", "--plugins", "yandex-seo"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertGreater(payload["scenario_count"], 0)
        self.assertEqual(payload["status"], "OK")

    def test_run_rejects_invalid_repository_sha_before_adapter_execution(self):
        cli = self.cli()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject = root / "subject.json"
            judge = root / "judge.json"
            subject.write_text(json.dumps(["definitely-missing-subject-command"]), encoding="utf-8")
            judge.write_text(json.dumps(["definitely-missing-judge-command"]), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = cli.main([
                    "run",
                    "--subject-adapter", str(subject),
                    "--judge-adapter", str(judge),
                    "--repository-sha", "not-a-sha",
                    "--evaluated-at", "2026-09-06T16:00:00Z",
                    "--plugins", "yandex-seo",
                ])
            self.assertEqual(code, 2)
            self.assertIn("repository SHA", stderr.getvalue())

    def test_run_publishes_immutable_artifact_directory(self):
        cli = self.cli()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subject_cfg = root / "subject.json"
            judge_cfg = root / "judge.json"
            subject_cfg.write_text(json.dumps([sys.executable, str(ROOT / "evals/adapters/fake_subject.py")]), encoding="utf-8")
            judge_cfg.write_text(json.dumps([sys.executable, str(ROOT / "evals/adapters/fake_judge.py")]), encoding="utf-8")
            output_root = root / "artifacts"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = cli.main([
                    "run",
                    "--subject-adapter", str(subject_cfg),
                    "--judge-adapter", str(judge_cfg),
                    "--repository-sha", "a" * 40,
                    "--evaluated-at", "2026-09-06T17:20:00Z",
                    "--plugins", "yandex-search",
                    "--output-root", str(output_root),
                ])
            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            artifact_dir = Path(payload["artifact_dir"])
            self.assertTrue((artifact_dir / "manifest.json").is_file())
            self.assertTrue((artifact_dir / "results.json").is_file())
            result = json.loads((artifact_dir / "results.json").read_text(encoding="utf-8"))
            self.assertEqual(result["schema"], "yandex-ai-benchmark-result/v1")
            self.assertEqual(payload["benchmark_id"], result["benchmark_id"])
            self.assertEqual(result["completeness"], "INFRASTRUCTURE_READY")
            self.assertFalse(result["comparative_complete"])

    def _published_artifact(self, root: Path) -> Path:
        from scripts.eval_benchmark import artifacts

        run = {
            "evaluated_at": "2026-09-06T17:30:00Z",
            "repository_sha": "b" * 40,
            "scenarios": [{
                "plugin": "yandex-search",
                "scenario_id": "c" * 64,
                "source_path": "plugins/yandex-search/evals/scenarios.json",
                "source_sha256": "d" * 64,
                "state": "PASS",
                "subject": {
                    "schema": "yandex-ai-eval-adapter-response/v1",
                    "invocation_id": "subject-cli",
                    "adapter_id": "fake-subject-adapter",
                    "adapter_version": "1",
                    "runtime": {"name": "repository-fake", "version": "1"},
                    "model": {"name": "fake-subject", "version": "1"},
                    "output": {"text": "safe output", "route": "yandex-search", "outcome": "comply"},
                },
                "mechanical": [],
                "semantic": {
                    "judge_identity": ["repository-fake", "1", "fake-judge", "1"],
                    "subject_identity": ["repository-fake", "1", "fake-subject", "1"],
                    "judge_mode": "INDEPENDENT",
                    "route": {"expected": "yandex-search", "actual": "yandex-search", "state": "PASS", "rationale": ""},
                    "outcome": {"expected": "comply", "actual": "comply", "state": "PASS"},
                    "must_convey": [],
                    "must_not_claim": [],
                    "rationale": "bounded",
                },
            }],
            "aggregate": {"passed": 1, "failed": 0, "undetermined": 0, "total": 1},
            "subject_identities": [{
                "adapter_id": "fake-subject-adapter",
                "adapter_version": "1",
                "runtime": {"name": "repository-fake", "version": "1"},
                "model": {"name": "fake-subject", "version": "1"},
                "fake": True,
            }],
            "completeness": "INFRASTRUCTURE_READY",
            "comparative_complete": False,
        }
        result = artifacts.build_result_document(run)
        return artifacts.publish_benchmark_artifacts(root / "artifacts", result)

    def test_compare_renders_self_contained_html_from_normative_results(self):
        cli = self.cli()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_dir = self._published_artifact(root)
            output = root / "comparison-copy.html"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = cli.main(["compare", "--results", str(artifact_dir / "results.json"), "--output", str(output)])
            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["output"], str(output))
            text = output.read_text(encoding="utf-8")
            self.assertIn("Content-Security-Policy", text)
            self.assertNotIn("https://", text)

    def test_publish_snapshot_materializes_only_and_does_not_commit(self):
        cli = self.cli()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_dir = self._published_artifact(root)
            repository_root = root / "repo"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = cli.main([
                    "publish-snapshot",
                    "--artifact-dir", str(artifact_dir),
                    "--repository-root", str(repository_root),
                ])
            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            snapshot = Path(payload["snapshot_dir"])
            self.assertTrue((snapshot / "manifest.json").is_file())
            self.assertEqual(snapshot.parent, repository_root / "evals/results/v1")
            self.assertFalse((repository_root / ".git").exists())


if __name__ == "__main__":
    unittest.main()
