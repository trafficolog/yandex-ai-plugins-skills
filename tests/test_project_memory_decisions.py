from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ROOT / "scripts" / "project_memory" / "decisions.py"
CLI = ROOT / "scripts" / "ya_project.py"


def receipt(execution_id="exec-1", preview_id="preview-1"):
    return {
        "schema": "yandex-ai-execution/v1",
        "execution_id": execution_id,
        "preview_id": preview_id,
        "plugin": "yandex-direct",
        "operation": "campaigns.add",
        "target": {"environment": "prod", "client_login": "demo-login"},
        "cardinality": {"scale": "KNOWN", "items": 1, "threshold": 20, "bulk": False},
        "execution": {"state": "EXECUTED"},
        "verification": {"capability": "RESPONSE_ONLY", "state": "UNVERIFIED"},
        "rollback": {"capability": "NOT_AVAILABLE", "snapshot_available": False},
        "result": {"access_token": "must-not-persist", "campaign_id": 123},
    }


class ProjectMemoryDecisionTests(unittest.TestCase):
    def load_module(self):
        self.assertTrue(DECISIONS.exists(), "project memory decisions module must exist")
        from scripts.project_memory import decisions
        return decisions

    def test_receipt_projection_excludes_result_and_hashes_complete_receipt(self):
        decisions = self.load_module()
        source = receipt()
        self.assertEqual(decisions.validate_execution_receipt(source), [])
        projected = decisions.safe_execution_projection(
            source,
            recorded_at="2026-09-06T08:00:00Z",
            previous_record_hash=None,
            record_id="record-1",
        )
        self.assertNotIn("result", projected)
        self.assertNotIn("must-not-persist", json.dumps(projected, sort_keys=True))
        self.assertEqual(projected["schema"], "yandex-ai-decision/v1")
        self.assertEqual(projected["kind"], "EXECUTION")
        first_hash = projected["receipt_sha256"]

        changed = deepcopy(source)
        changed["result"]["campaign_id"] = 456
        changed_projection = decisions.safe_execution_projection(
            changed,
            recorded_at="2026-09-06T08:00:00Z",
            previous_record_hash=None,
            record_id="record-2",
        )
        self.assertNotEqual(first_hash, changed_projection["receipt_sha256"])

    def test_receipt_schema_and_required_safety_fields_are_fail_closed(self):
        decisions = self.load_module()
        bad_schema = receipt()
        bad_schema["schema"] = "yandex-ai-execution/v2"
        self.assertTrue(any("yandex-ai-execution/v1" in e for e in decisions.validate_execution_receipt(bad_schema)))

        for field in ("execution_id", "preview_id", "plugin", "operation", "target", "cardinality", "execution", "verification", "rollback", "result"):
            with self.subTest(field=field):
                bad = receipt()
                bad.pop(field)
                self.assertTrue(decisions.validate_execution_receipt(bad))

        bad_state = receipt()
        bad_state["execution"]["state"] = "PLANNED"
        self.assertTrue(any("EXECUTED" in e for e in decisions.validate_execution_receipt(bad_state)))

    def test_chain_links_and_detects_tampering(self):
        decisions = self.load_module()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decisions.jsonl"
            path.write_text("", encoding="utf-8")
            now = datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)
            first = decisions.record_execution(path.parent, receipt(), now=now)
            second = decisions.record_execution(path.parent, receipt("exec-2", "preview-2"), now=now)
            self.assertIsNone(first["previous_record_hash"])
            self.assertEqual(second["previous_record_hash"], first["record_hash"])
            records, errors = decisions.validate_decision_chain(path, at=now)
            self.assertEqual(errors, [])
            self.assertEqual(len(records), 2)

            lines = path.read_text(encoding="utf-8").splitlines()
            tampered = json.loads(lines[0])
            tampered["operation"] = "campaigns.delete"
            lines[0] = json.dumps(tampered, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            _, errors = decisions.validate_decision_chain(path, at=now)
            self.assertTrue(any("record_hash" in e or "previous_record_hash" in e for e in errors))

    def test_duplicate_execution_or_receipt_is_rejected_without_append(self):
        decisions = self.load_module()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decisions.jsonl"
            path.write_text("", encoding="utf-8")
            now = datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)
            decisions.record_execution(path.parent, receipt(), now=now)
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                decisions.record_execution(path.parent, receipt(), now=now)
            self.assertEqual(path.read_bytes(), before)

            duplicate_id_different_receipt = receipt()
            duplicate_id_different_receipt["result"]["campaign_id"] = 999
            with self.assertRaises(ValueError):
                decisions.record_execution(path.parent, duplicate_id_different_receipt, now=now)
            self.assertEqual(path.read_bytes(), before)

    def test_malformed_jsonl_and_future_recorded_at_fail_validation(self):
        decisions = self.load_module()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decisions.jsonl"
            path.write_text("not-json\n", encoding="utf-8")
            _, errors = decisions.validate_decision_chain(
                path, at=datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)
            )
            self.assertTrue(any("JSON" in e for e in errors))

            path.write_text("", encoding="utf-8")
            decisions.record_execution(
                path.parent,
                receipt(),
                now=datetime(2026, 9, 6, 8, 10, tzinfo=timezone.utc),
            )
            _, errors = decisions.validate_decision_chain(
                path, at=datetime(2026, 9, 6, 8, 0, tzinfo=timezone.utc)
            )
            self.assertTrue(any("future" in e.lower() for e in errors))

    def test_cli_record_execution_accepts_file_and_check_verifies_chain(self):
        self.assertTrue(CLI.exists())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init = subprocess.run(
                [sys.executable, str(CLI), "init", "--root", str(root), "--project-id", "demo", "--name", "Demo"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            receipt_path = root / "receipt.json"
            receipt_path.write_text(json.dumps(receipt()), encoding="utf-8")
            recorded = subprocess.run(
                [sys.executable, str(CLI), "record-execution", str(receipt_path), "--root", str(root)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(recorded.returncode, 0, recorded.stderr)
            line = json.loads((root / ".yandex-ai" / "decisions.jsonl").read_text(encoding="utf-8"))
            self.assertNotIn("result", line)
            checked = subprocess.run(
                [sys.executable, str(CLI), "check", "--root", str(root), "--at", "2099-01-01T00:00:00Z", "--json"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertTrue(json.loads(checked.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
