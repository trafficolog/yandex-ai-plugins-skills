from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "scripts" / "project_memory" / "baselines.py"
CLI = ROOT / "scripts" / "ya_project.py"


class ProjectMemoryBaselineTests(unittest.TestCase):
    def load_module(self):
        self.assertTrue(BASELINES.exists(), "project memory baselines module must exist")
        from scripts.project_memory import baselines
        return baselines

    def test_build_validate_filename_and_freshness_boundary(self):
        baselines = self.load_module()
        captured = datetime(2026, 9, 6, 7, 30, tzinfo=timezone.utc)
        fresh_until = datetime(2026, 9, 7, 7, 30, tzinfo=timezone.utc)
        record = baselines.build_baseline(
            baseline_id="baseline-1",
            kind="organic-summary",
            captured_at=captured,
            fresh_until=fresh_until,
            source="yandex-webmaster",
            provenance="OBSERVED",
            data={"clicks": 10},
        )
        self.assertEqual(baselines.validate_baseline(record, at=captured), [])
        self.assertEqual(
            baselines.baseline_filename("organic-summary", captured),
            "2026-09-06T073000Z--organic-summary.json",
        )
        self.assertEqual(baselines.freshness_state(record, at=fresh_until), "FRESH")
        self.assertEqual(
            baselines.freshness_state(
                record, at=datetime(2026, 9, 7, 7, 30, 1, tzinfo=timezone.utc)
            ),
            "STALE",
        )

    def test_invalid_time_order_future_capture_secret_key_and_artifact_pair_are_rejected(self):
        baselines = self.load_module()
        at = datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)
        record = baselines.build_baseline(
            baseline_id="baseline-1",
            kind="organic-summary",
            captured_at=datetime(2026, 9, 6, 7, 30, tzinfo=timezone.utc),
            fresh_until=datetime(2026, 9, 7, 7, 30, tzinfo=timezone.utc),
            source="yandex-webmaster",
            provenance="OBSERVED",
            data={"clicks": 10},
        )
        invalid_order = dict(record)
        invalid_order["fresh_until"] = "2026-09-06T07:00:00Z"
        self.assertTrue(any("fresh_until" in e for e in baselines.validate_baseline(invalid_order, at=at)))

        future = dict(record)
        future["captured_at"] = "2026-09-06T08:06:00Z"
        self.assertTrue(any("future" in e.lower() for e in baselines.validate_baseline(future, at=at)))

        secret = dict(record)
        secret["data"] = {"oauth_token": "nope"}
        self.assertTrue(any("secret-like" in e for e in baselines.validate_baseline(secret, at=at)))

        artifact = dict(record)
        artifact["artifact_ref"] = "artifacts/report.json"
        self.assertTrue(any("artifact_sha256" in e for e in baselines.validate_baseline(artifact, at=at)))

    def test_immutable_creation_refuses_same_destination_and_duplicate_id(self):
        baselines = self.load_module()
        captured = datetime(2026, 9, 6, 7, 30, tzinfo=timezone.utc)
        record = baselines.build_baseline(
            baseline_id="baseline-1",
            kind="organic-summary",
            captured_at=captured,
            fresh_until=datetime(2026, 9, 7, 7, 30, tzinfo=timezone.utc),
            source="yandex-webmaster",
            provenance="OBSERVED",
            data={"clicks": 10},
        )
        with tempfile.TemporaryDirectory() as tmp:
            memory = Path(tmp)
            (memory / "baselines").mkdir()
            first = baselines.create_baseline(memory, record)
            before = first.read_bytes()
            with self.assertRaises(FileExistsError):
                baselines.create_baseline(memory, record)
            self.assertEqual(first.read_bytes(), before)

            other = baselines.build_baseline(
                baseline_id="baseline-1",
                kind="paid-summary",
                captured_at=captured,
                fresh_until=datetime(2026, 9, 7, 7, 30, tzinfo=timezone.utc),
                source="yandex-direct",
                provenance="OBSERVED",
                data={"clicks": 5},
            )
            with self.assertRaises(ValueError):
                baselines.create_baseline(memory, other)

    def test_cli_add_baseline_and_check_reports_stale_as_warning_not_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init = subprocess.run(
                [sys.executable, str(CLI), "init", "--root", str(root), "--project-id", "demo", "--name", "Demo"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            data_path = root / "baseline-data.json"
            data_path.write_text(json.dumps({"clicks": 10}), encoding="utf-8")
            added = subprocess.run(
                [
                    sys.executable, str(CLI), "add-baseline",
                    "--root", str(root),
                    "--baseline-id", "baseline-1",
                    "--kind", "organic-summary",
                    "--captured-at", "2026-09-06T07:30:00Z",
                    "--fresh-until", "2026-09-06T08:00:00Z",
                    "--source", "yandex-webmaster",
                    "--input", str(data_path),
                ],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(added.returncode, 0, added.stderr)
            snapshot = root / ".yandex-ai" / "baselines" / "organic-summary" / "2026-09-06T073000Z--organic-summary.json"
            self.assertTrue(snapshot.is_file())

            checked = subprocess.run(
                [sys.executable, str(CLI), "check", "--root", str(root), "--at", "2026-09-07T08:00:01Z", "--json"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            payload = json.loads(checked.stdout)
            self.assertTrue(payload["ok"])
            self.assertTrue(any("STALE" in warning for warning in payload["warnings"]))


if __name__ == "__main__":
    unittest.main()
