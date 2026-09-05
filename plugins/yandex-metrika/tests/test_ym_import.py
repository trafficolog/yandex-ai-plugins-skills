from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from scripts._approval import preview_id
from scripts.ym_import import (
    IMPORT_PATHS,
    build_multipart_file,
    execute_import,
    guard_expense_source,
    import_approval_envelope,
    inspect_csv,
    prepare_import,
    run_import,
    sha256_file,
)


class _JSONResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"uploading":{"id":1}}'


class TestMetrikaImport(unittest.TestCase):
    def _csv(self, directory: str, content: str = "ClientId,Target,DateTime\n1,lead,1710000000\n") -> Path:
        path = Path(directory) / "data.csv"
        path.write_text(content, encoding="utf-8")
        return path

    def test_import_paths(self):
        self.assertEqual(IMPORT_PATHS["offline-conversions"], "offline_conversions/upload")
        self.assertEqual(IMPORT_PATHS["calls"], "offline_conversions/upload_calls")
        self.assertEqual(IMPORT_PATHS["expenses"], "expense/upload")

    def test_inspect_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp)
            info = inspect_csv(path)
            self.assertEqual(info["rows"], 1)
            self.assertEqual(info["columns"], ["ClientId", "Target", "DateTime"])
            self.assertEqual(info["encoding"], "utf-8")
            self.assertGreater(info["size_bytes"], 0)

    def test_sha256_file_is_content_sensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp, "A,B\n1,x\n")
            first = sha256_file(path)
            path.write_text("A,B\n2,y\n", encoding="utf-8")
            second = sha256_file(path)
            self.assertNotEqual(first, second)

    def test_non_utf8_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_bytes(b"name\n\xff\n")
            with self.assertRaises(ValueError):
                inspect_csv(path)

    def test_direct_expense_source_aliases_are_rejected(self):
        aliases = [
            "Yandex Direct",
            "Яндекс Директ",
            "direct",
            "Директ",
            "yandex-direct",
            "yandexdirect",
            "ЯндексДирект",
            "direct_yandex",
            "ya.direct",
            "Yandex Direct RU",
            "direct_ads",
            "Яндекс Директ агентство",
        ]
        for source in aliases:
            with self.subTest(source=source):
                with self.assertRaises(ValueError):
                    guard_expense_source(source)

    def test_arbitrary_concatenated_direct_word_is_not_proven_source(self):
        guard_expense_source("MyDirect")

    def test_direct_like_utm_expense_csv_requires_explicit_override(self):
        content = "Date,UTMSource,UTMMedium,Expenses\n2026-08-01,yandex,cpc,100\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp, content)
            with self.assertRaisesRegex(ValueError, "DIRECT_DUPLICATION_RISK"):
                prepare_import("expenses", 123, path, "secret", source="agency")

            preview = prepare_import(
                "expenses",
                123,
                path,
                "secret",
                source="agency",
                allow_direct_risk=True,
            )
            self.assertIn("DIRECT_DUPLICATION_RISK", preview["warnings"])
            self.assertIn("DIRECT_DUPLICATION_RISK", preview["safety"]["risk_flags"])

    def test_direct_traffic_source_detail_without_utm_requires_explicit_override(self):
        content = "Date,TrafficSource,TrafficSourceDetail,Expenses\n2026-08-01,ad,yandex_direct_star,100\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp, content)
            with self.assertRaisesRegex(ValueError, "DIRECT_DUPLICATION_RISK"):
                prepare_import("expenses", 123, path, "secret", source="agency")

            preview = prepare_import(
                "expenses",
                123,
                path,
                "secret",
                source="agency",
                allow_direct_risk=True,
            )
            self.assertIn("DIRECT_DUPLICATION_RISK", preview["warnings"])

    def test_unverifiable_expense_source_requires_explicit_override(self):
        content = "Date,TrafficSource,Expenses\n2026-08-01,ad,100\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp, content)
            with self.assertRaisesRegex(ValueError, "DIRECT_SOURCE_UNVERIFIED"):
                prepare_import("expenses", 123, path, "secret", source="MyDirect")

            preview = prepare_import(
                "expenses",
                123,
                path,
                "secret",
                source="MyDirect",
                allow_direct_risk=True,
            )
            self.assertIn("DIRECT_SOURCE_UNVERIFIED", preview["warnings"])

    def test_non_direct_traffic_source_detail_is_allowed_without_utm(self):
        content = "Date,TrafficSource,TrafficSourceDetail,Expenses\n2026-08-01,ad,google_adwords,100\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp, content)
            preview = prepare_import("expenses", 123, path, "secret", source="agency")
            self.assertEqual(preview.get("warnings"), [])

    def test_non_direct_expense_csv_is_not_flagged(self):
        content = "Date,UTMSource,UTMMedium,Expenses\n2026-08-01,newsletter,email,100\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp, content)
            preview = prepare_import("expenses", 123, path, "secret", source="agency")
            self.assertEqual(preview.get("warnings"), [])

    def test_preview_redacts_token_keeps_metadata_and_emits_content_bound_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp)
            preview = prepare_import("offline-conversions", 123, path, "secret", comment="batch")
            self.assertEqual(preview["headers"]["Authorization"], "OAuth ***")
            self.assertEqual(preview["file"]["rows"], 1)
            self.assertEqual(preview["file"]["sha256"], sha256_file(path))
            self.assertNotIn("1,lead", str(preview))
            self.assertIn("comment=batch", preview["url"])
            envelope = import_approval_envelope(
                "offline-conversions",
                123,
                path,
                token="secret",
                comment="batch",
            )
            self.assertEqual(preview["preview_id"], preview_id(envelope))

    def test_same_name_and_size_different_bytes_change_approval_id(self):
        with tempfile.TemporaryDirectory() as left_tmp, tempfile.TemporaryDirectory() as right_tmp:
            left = self._csv(left_tmp, "A,B\n1,x\n")
            right = self._csv(right_tmp, "A,B\n2,y\n")
            self.assertEqual(left.name, right.name)
            self.assertEqual(left.stat().st_size, right.stat().st_size)
            left_id = preview_id(import_approval_envelope("offline-conversions", 123, left, token="secret"))
            right_id = preview_id(import_approval_envelope("offline-conversions", 123, right, token="secret"))
            self.assertNotEqual(left_id, right_id)

    def test_execute_without_approval_is_blocked_before_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp)
            opener = Mock(return_value=_JSONResponse())
            with self.assertRaises(ValueError):
                execute_import("offline-conversions", 123, path, "secret", opener=opener)
            opener.assert_not_called()

    def test_wrong_approval_is_blocked_before_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp)
            opener = Mock(return_value=_JSONResponse())
            with self.assertRaises(ValueError):
                execute_import(
                    "offline-conversions",
                    123,
                    path,
                    "secret",
                    approve="0" * 64,
                    opener=opener,
                )
            opener.assert_not_called()

    def test_file_mutation_after_preview_invalidates_approval_before_upload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp, "A,B\n1,x\n")
            approve = preview_id(import_approval_envelope("offline-conversions", 123, path, token="secret"))
            path.write_text("A,B\n2,y\n", encoding="utf-8")
            opener = Mock(return_value=_JSONResponse())
            with self.assertRaises(ValueError):
                execute_import(
                    "offline-conversions",
                    123,
                    path,
                    "secret",
                    approve=approve,
                    opener=opener,
                )
            opener.assert_not_called()

    def test_exact_approval_uploads_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp)
            approve = preview_id(import_approval_envelope("offline-conversions", 123, path, token="secret"))
            opener = Mock(return_value=_JSONResponse())
            result = execute_import(
                "offline-conversions",
                123,
                path,
                "secret",
                approve=approve,
                opener=opener,
            )
            opener.assert_called_once()
            self.assertEqual(result["result"], {"uploading": {"id": 1}})
            self.assertEqual(result["schema"], "yandex-ai-execution/v1")

    def test_run_import_preview_then_exact_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp)
            preview = run_import("offline-conversions", 123, path, "secret")
            self.assertTrue(preview["dry_run"])
            opener = Mock(return_value=_JSONResponse())
            result = run_import(
                "offline-conversions",
                123,
                path,
                "secret",
                execute=True,
                approve=preview["preview_id"],
                opener=opener,
            )
            opener.assert_called_once()
            self.assertEqual(result["result"], {"uploading": {"id": 1}})
            self.assertEqual(result["preview_id"], preview["preview_id"])

    def test_multipart_builder_contains_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._csv(tmp)
            content_type, body = build_multipart_file(path, boundary="TESTBOUNDARY")
            self.assertEqual(content_type, "multipart/form-data; boundary=TESTBOUNDARY")
            self.assertIn(b'filename="data.csv"', body)
            self.assertIn(b"ClientId,Target,DateTime", body)


if __name__ == "__main__":
    unittest.main()
