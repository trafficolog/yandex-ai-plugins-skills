import inspect
import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from scripts import yw_api, yw_feeds, yw_indexing, yw_recrawl, yw_sitemaps


class WebmasterP0SafetyV2Tests(unittest.TestCase):
    def test_single_operation_descriptors_are_known_scale(self):
        descriptors = [
            yw_recrawl.submit_request(1, "h", "https://example.com/a", host_url="https://example.com"),
            yw_sitemaps.add_request(1, "h", "https://example.com/sitemap.xml"),
            yw_sitemaps.delete_request(1, "h", "s1"),
            yw_sitemaps.priority_recrawl_request(1, "h", "s1"),
            yw_feeds.start_request(
                1,
                "h",
                host_url="https://example.com",
                feed_url="https://example.com/feed.yml",
                feed_type="YML",
            ),
            yw_indexing.archive_start_request(1, "h"),
        ]
        for descriptor in descriptors:
            with self.subTest(descriptor=descriptor):
                preview = yw_api.prepare_request(
                    token="secret",
                    method=descriptor["method"],
                    path=descriptor["path"],
                    version=descriptor.get("version", "v4"),
                    params=descriptor.get("params"),
                    body=descriptor.get("body"),
                )
                self.assertEqual(preview.get("approval_schema"), "yandex-ai-approval/v2")
                self.assertEqual(preview.get("cardinality", {}).get("scale"), "KNOWN")
                self.assertEqual(preview.get("cardinality", {}).get("items"), 1)
                self.assertFalse(preview.get("cardinality", {}).get("bulk", True))

    def test_feed_batch_add_and_remove_bind_exact_item_count(self):
        add = yw_feeds.batch_add_request(
            1,
            "h",
            host_url="https://example.com",
            feeds=[{"url": f"https://example.com/{i}.yml", "type": "YML"} for i in range(21)],
        )
        remove = yw_feeds.delete_request(
            1,
            "h",
            host_url="https://example.com",
            urls=[f"https://example.com/{i}.yml" for i in range(21)],
        )
        for descriptor in (add, remove):
            with self.subTest(path=descriptor["path"]):
                preview = yw_api.prepare_request(
                    token="secret",
                    method=descriptor["method"],
                    path=descriptor["path"],
                    version=descriptor.get("version", "v4"),
                    params=descriptor.get("params"),
                    body=descriptor.get("body"),
                )
                self.assertEqual(preview.get("cardinality", {}).get("items"), 21)
                self.assertTrue(preview.get("cardinality", {}).get("bulk"))

    def test_unrecognized_generic_write_is_unknown_scale(self):
        preview = yw_api.prepare_request(
            method="POST",
            path="user/1/hosts/h/opaque-mutation",
            token="secret",
            body={"value": 1},
        )
        self.assertEqual(
            preview.get("cardinality"),
            {"scale": "UNKNOWN", "items": None, "threshold": 20, "bulk": True},
        )

    def test_oauth_principal_change_invalidates_preview_without_embedded_credentials(self):
        kwargs = {
            "method": "POST",
            "path": "user/1/hosts/h/recrawl/queue",
            "body": {"url": "https://example.com/a"},
        }
        first = yw_api.prepare_request(token="oauth-a", **kwargs)
        changed = yw_api.prepare_request(token="oauth-b", **kwargs)
        self.assertNotEqual(first["preview_id"], changed["preview_id"])
        self.assertNotIn("oauth-a", str(first))
        transport = Mock()
        with self.assertRaises(ValueError):
            yw_api.run_request(
                token="oauth-b",
                execute=True,
                approve=first["preview_id"],
                transport=transport,
                **kwargs,
            )
        transport.assert_not_called()

    def test_bulk_write_needs_ack_before_transport(self):
        descriptor = yw_feeds.batch_add_request(
            1,
            "h",
            host_url="https://example.com",
            feeds=[{"url": f"https://example.com/{i}.yml", "type": "YML"} for i in range(21)],
        )
        preview = yw_api.prepare_request(token="secret", **descriptor)
        transport = Mock(return_value={"ok": True})
        with self.assertRaisesRegex(ValueError, "ack-bulk"):
            yw_api.run_request(
                token="secret",
                execute=True,
                approve=preview["preview_id"],
                transport=transport,
                **descriptor,
            )
        transport.assert_not_called()

    def test_bulk_write_with_ack_returns_receipt(self):
        descriptor = yw_feeds.batch_add_request(
            1,
            "h",
            host_url="https://example.com",
            feeds=[{"url": f"https://example.com/{i}.yml", "type": "YML"} for i in range(21)],
        )
        preview = yw_api.prepare_request(token="secret", **descriptor)
        transport = Mock(return_value={"ok": True})
        receipt = yw_api.run_request(
            token="secret",
            execute=True,
            approve=preview["preview_id"],
            ack_bulk=True,
            transport=transport,
            **descriptor,
        )
        transport.assert_called_once()
        self.assertEqual(receipt.get("schema"), "yandex-ai-execution/v1")
        self.assertEqual(receipt.get("preview_id"), preview["preview_id"])
        self.assertEqual(receipt.get("result"), {"ok": True})
        self.assertEqual(
            receipt.get("verification"),
            {"capability": "RESPONSE_ONLY", "state": "UNVERIFIED"},
        )
        self.assertEqual(receipt.get("rollback", {}).get("capability"), "NOT_AVAILABLE")

    def test_run_surface_and_cli_expose_bulk_ack(self):
        self.assertIn("ack_bulk", inspect.signature(yw_api.run_request).parameters)
        captured = {}

        def fake_run_request(**kwargs):
            captured.update(kwargs)
            return {"ok": True}

        argv = [
            "yw_api.py",
            "user/1/hosts/h/opaque-mutation",
            "--method",
            "POST",
            "--body",
            '{"value":1}',
            "--execute",
            "--approve",
            "a" * 64,
            "--ack-bulk",
        ]
        with patch.object(yw_api, "run_request", side_effect=fake_run_request):
            with patch.dict(os.environ, {"YANDEX_WEBMASTER_TOKEN": "secret"}, clear=False):
                with patch.object(sys, "argv", argv):
                    with redirect_stdout(io.StringIO()):
                        try:
                            rc = yw_api.main()
                        except SystemExit as exc:
                            self.fail(f"--ack-bulk must be accepted by the CLI: {exc}")
        self.assertEqual(rc, 0)
        self.assertTrue(captured["ack_bulk"])


if __name__ == "__main__":
    unittest.main()
