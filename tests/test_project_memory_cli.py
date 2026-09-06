import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.project_memory import yaml_subset


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "ya_project.py"


class ProjectMemoryCliTests(unittest.TestCase):
    def run_cli(self, *args, input_text=None):
        self.assertTrue(CLI.exists(), "ya-project CLI must exist")
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_init_creates_canonical_scaffold_and_check_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_cli(
                "init", "--root", str(root), "--project-id", "demo", "--name", "Demo"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            memory = root / ".yandex-ai"
            self.assertTrue((memory / "project.yaml").is_file())
            self.assertEqual((memory / "decisions.jsonl").read_text(encoding="utf-8"), "")
            self.assertTrue((memory / "baselines").is_dir())
            self.assertTrue((memory / "hypotheses.md").is_file())

            doc = yaml_subset.loads((memory / "project.yaml").read_text(encoding="utf-8"))
            self.assertEqual(doc["schema"], "yandex-ai-project/v1")
            self.assertEqual(doc["project"]["id"], "demo")
            self.assertEqual(doc["facts"], [])

            checked = self.run_cli(
                "check", "--root", str(root), "--at", "2099-01-01T00:00:00Z", "--json"
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            payload = json.loads(checked.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["errors"], [])

    def test_init_collision_fails_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self.run_cli(
                "init", "--root", str(root), "--project-id", "demo", "--name", "Demo"
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            project = root / ".yandex-ai" / "project.yaml"
            before = project.read_bytes()
            second = self.run_cli(
                "init", "--root", str(root), "--project-id", "other", "--name", "Other"
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(project.read_bytes(), before)

    def test_add_and_supersede_fact_preserve_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(
                self.run_cli("init", "--root", str(root), "--project-id", "demo", "--name", "Demo").returncode,
                0,
            )
            added = self.run_cli(
                "add-fact",
                "--root", str(root),
                "--fact-id", "f1",
                "--key", "target_roas",
                "--value", "4.0",
                "--stated-at", "2026-09-06T07:00:00Z",
            )
            self.assertEqual(added.returncode, 0, added.stderr)

            project = root / ".yandex-ai" / "project.yaml"
            before_invalid = project.read_bytes()
            invalid = self.run_cli(
                "supersede-fact",
                "--root", str(root),
                "--fact-id", "f1",
                "--key", "budget",
                "--value", "100",
                "--stated-at", "2026-09-06T07:10:00Z",
            )
            self.assertNotEqual(invalid.returncode, 0)
            self.assertEqual(project.read_bytes(), before_invalid)

            replaced = self.run_cli(
                "supersede-fact",
                "--root", str(root),
                "--fact-id", "f1",
                "--key", "target_roas",
                "--value", "4.5",
                "--stated-at", "2026-09-06T07:10:00Z",
            )
            self.assertEqual(replaced.returncode, 0, replaced.stderr)
            doc = yaml_subset.loads(project.read_text(encoding="utf-8"))
            old = next(f for f in doc["facts"] if f["fact_id"] == "f1")
            active = next(f for f in doc["facts"] if f["status"] == "ACTIVE")
            self.assertEqual(old["status"], "SUPERSEDED")
            self.assertEqual(active["key"], "target_roas")
            self.assertEqual(active["value"], 4.5)
            self.assertEqual(active["supersedes"], "f1")
            self.assertNotEqual(active["fact_id"], "f1")

    def test_add_fact_refuses_second_active_value_for_same_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(
                self.run_cli("init", "--root", str(root), "--project-id", "demo", "--name", "Demo").returncode,
                0,
            )
            self.assertEqual(
                self.run_cli(
                    "add-fact", "--root", str(root), "--fact-id", "f1", "--key", "budget",
                    "--value", "100", "--stated-at", "2026-09-06T07:00:00Z"
                ).returncode,
                0,
            )
            second = self.run_cli(
                "add-fact", "--root", str(root), "--fact-id", "f2", "--key", "budget",
                "--value", "200", "--stated-at", "2026-09-06T07:05:00Z"
            )
            self.assertNotEqual(second.returncode, 0)

    def test_check_rejects_secret_like_project_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(
                self.run_cli("init", "--root", str(root), "--project-id", "demo", "--name", "Demo").returncode,
                0,
            )
            project = root / ".yandex-ai" / "project.yaml"
            doc = yaml_subset.loads(project.read_text(encoding="utf-8"))
            doc["facts"] = [{
                "fact_id": "f1",
                "key": "context",
                "value": {"api_key": "do-not-store"},
                "stated_at": "2026-09-06T07:00:00Z",
                "provenance": "USER_STATED",
                "status": "ACTIVE",
            }]
            project.write_text(yaml_subset.dumps(doc), encoding="utf-8")
            result = self.run_cli(
                "check", "--root", str(root), "--at", "2026-09-06T08:00:00Z", "--json"
            )
            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertTrue(any("secret-like" in e for e in payload["errors"]))


if __name__ == "__main__":
    unittest.main()
