from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
