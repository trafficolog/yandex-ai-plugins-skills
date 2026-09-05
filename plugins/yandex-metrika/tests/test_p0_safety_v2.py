from pathlib import Path
import inspect
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import ym_api, ym_import, ym_logs


class _JSONResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"uploading":{"id":1}}'


class MetrikaP0SafetyV2Tests(unittest.TestCase):
    def _csv(self, directory: str, rows: int = 1) -> Path:
        path = Path(directory) / "data.csv"
        body = "ClientId,Target,DateTime\n" + "".join(
            f"{index},lead,1710000000\n" for index in range(1, rows + 1)
        )
        path.write_text(body, encoding="utf-8")
        return path

    def test_management_preview_binds_token_and_unknown_scale(self):
        kwargs = {
            "method": "POST",
            "path": "counter/123/goals",
            "body": {"goal": {"name": "Lead"}},
        }
        first = ym_api.prepare_request(token="token-a", **kwargs)
        changed = ym_api.prepare_request(token="token-b", **kwargs)
        self.assertEqual(first.get("approval_schema"), "yandex-ai-approval/v2")
        self.assertEqual(
            first.get("cardinality"),
            {"scale": "UNKNOWN", "items": None, "threshold": 20, "bulk": True},
        )
        self.assertNotEqual(first["preview_id"], changed["preview_id"])
        self.assertNotIn("token-a", str(first))

    def test_management_run_surface_exposes_bulk_ack(self):
        self.assertIn("ack_bulk", inspect.signature(ym_api.run_request).parameters)

    def test_management_exact_write_returns_receipt(self):
        body = {"goal": {"name": "Lead"}}
        preview = ym_api.prepare_request(
            method="POST", path="counter/123/goals", token="secret", body=body
        )
        with patch(
            "scripts.ym_api.request_json", return_value=({}, {"goal": {"id": 7}})
        ) as request_json:
            receipt = ym_api.run_request(
                method="POST",
                path="counter/123/goals",
                token="secret",
                body=body,
                execute=True,
                approve=preview["preview_id"],
                ack_bulk=True,
            )
        request_json.assert_called_once()
        self.assertEqual(receipt.get("schema"), "yandex-ai-execution/v1")
        self.assertEqual(receipt.get("preview_id"), preview["preview_id"])
        self.assertEqual(
            receipt.get("verification"),
            {"capability": "RESPONSE_ONLY", "state": "UNVERIFIED"},
        )
        self.assertEqual(receipt.get("rollback", {}).get("capability"), "NOT_AVAILABLE")

    def test_logs_preview_binds_token_and_known_single_scale(self):
        first = ym_logs.prepare_logs_request(
            123, "clean", token="token-a", request_id=7
        )
        changed = ym_logs.prepare_logs_request(
            123, "clean", token="token-b", request_id=7
        )
        self.assertEqual(first.get("approval_schema"), "yandex-ai-approval/v2")
        self.assertEqual(
            first.get("cardinality"),
            {"scale": "KNOWN", "items": 1, "threshold": 20, "bulk": False},
        )
        self.assertNotEqual(first["preview_id"], changed["preview_id"])
        self.assertNotIn("token-a", str(first))

    def test_logs_exact_write_returns_receipt_without_bulk_ack(self):
        preview = ym_logs.prepare_logs_request(
            123, "clean", token="secret", request_id=7
        )
        with patch(
            "scripts.ym_logs.request_json", return_value=({}, {"success": True})
        ) as request_json:
            receipt = ym_logs.run_json_action(
                123,
                "clean",
                token="secret",
                request_id=7,
                execute=True,
                approve=preview["preview_id"],
            )
        request_json.assert_called_once()
        self.assertEqual(receipt.get("schema"), "yandex-ai-execution/v1")
        self.assertEqual(receipt.get("preview_id"), preview["preview_id"])

    def test_import_preview_binds_token_and_artifact_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp, rows=1)
            first = ym_import.prepare_import(
                "offline-conversions", 123, path, "token-a"
            )
            changed = ym_import.prepare_import(
                "offline-conversions", 123, path, "token-b"
            )
        self.assertEqual(first.get("approval_schema"), "yandex-ai-approval/v2")
        self.assertEqual(first.get("cardinality", {}).get("scale"), "KNOWN")
        self.assertEqual(first.get("cardinality", {}).get("items"), 1)
        self.assertEqual(first.get("cardinality", {}).get("artifact_rows"), 1)
        self.assertFalse(first.get("cardinality", {}).get("bulk", True))
        self.assertNotEqual(first["preview_id"], changed["preview_id"])
        self.assertNotIn("token-a", str(first))

    def test_import_rows_do_not_change_api_operation_cardinality(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp, rows=21)
            preview = ym_import.prepare_import(
                "offline-conversions", 123, path, "secret"
            )
        self.assertEqual(preview.get("cardinality", {}).get("items"), 1)
        self.assertEqual(preview.get("cardinality", {}).get("artifact_rows"), 21)
        self.assertFalse(preview.get("cardinality", {}).get("bulk", True))

    def test_import_exact_write_returns_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp, rows=1)
            preview = ym_import.prepare_import(
                "offline-conversions", 123, path, "secret"
            )
            opener = Mock(return_value=_JSONResponse())
            receipt = ym_import.run_import(
                "offline-conversions",
                123,
                path,
                "secret",
                execute=True,
                approve=preview["preview_id"],
                opener=opener,
            )
        opener.assert_called_once()
        self.assertEqual(receipt.get("schema"), "yandex-ai-execution/v1")
        self.assertEqual(receipt.get("preview_id"), preview["preview_id"])


if __name__ == "__main__":
    unittest.main()
