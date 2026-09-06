import hashlib
import unittest
from unittest.mock import Mock

from scripts import _http, yw_api, yw_export, yw_feeds, yw_indexing, yw_recrawl, yw_sitemaps
from scripts._approval import preview_id


class TestWebmasterApi(unittest.TestCase):
    def test_oauth_header_and_redaction(self):
        headers = _http.auth_headers("secret")
        self.assertEqual(headers["Authorization"], "OAuth secret")
        self.assertEqual(_http.redact_headers(headers)["Authorization"], "OAuth ***")

    def test_v4_url_encodes_query(self):
        url = yw_api.api_url("user/123/hosts", params={"offset": 10, "tag": ["a", "b"]})
        self.assertTrue(url.startswith("https://api.webmaster.yandex.net/v4/user/123/hosts?"))
        self.assertIn("offset=10", url)
        self.assertIn("tag=a", url)
        self.assertIn("tag=b", url)

    def test_v41_url_is_explicit(self):
        url = yw_api.api_url("user/1/hosts/h/sitemaps/recrawl", version="v4.1")
        self.assertEqual(url, "https://api.webmaster.yandex.net/v4.1/user/1/hosts/h/sitemaps/recrawl")

    def test_prepare_write_request_redacts_token_and_emits_preview_id(self):
        body = {"host_url": "https://example.com"}
        preview = yw_api.prepare_request(
            method="POST",
            path="user/1/hosts",
            token="secret",
            body=body,
        )
        self.assertTrue(preview["consequential"])
        self.assertEqual(preview["headers"]["Authorization"], "OAuth ***")
        self.assertEqual(preview["body"]["host_url"], "https://example.com")
        self.assertEqual(preview["approval_schema"], "yandex-ai-approval/v2")
        envelope = yw_api.approval_envelope(
            method="POST",
            path="user/1/hosts",
            token="secret",
            body=body,
        )
        self.assertEqual(preview["preview_id"], preview_id(envelope))

    def test_prepare_request_redacts_basic_auth_embedded_in_urls_and_digest_data(self):
        preview = yw_api.prepare_request(
            method="POST",
            path="user/1/hosts/h/feeds/add/start",
            token="secret",
            body={"url": "https://feeduser:feedpass@example.com/feed.yml"},
        )
        envelope = yw_api.approval_envelope(
            method="POST",
            path="user/1/hosts/h/feeds/add/start",
            token="secret",
            body={"url": "https://feeduser:feedpass@example.com/feed.yml"},
        )
        self.assertNotIn("feedpass", str(preview))
        self.assertNotIn("feeduser", str(preview))
        self.assertNotIn("feedpass", str(envelope))
        self.assertNotIn("feeduser", str(envelope))
        self.assertEqual(preview["body"]["url"], "https://***:***@example.com/feed.yml")

    def test_basic_auth_binding_is_keyed_and_not_plain_credential_hash(self):
        kwargs = {
            "method": "POST",
            "path": "user/1/hosts/h/feeds/add/start",
            "body": {"url": "https://feeduser:feedpass@example.com/feed.yml"},
        }
        envelope = yw_api.approval_envelope(token="oauth-secret-a", **kwargs)
        plain_fingerprint = hashlib.sha256(b"feeduser\0feedpass").hexdigest()
        self.assertNotIn(plain_fingerprint, str(envelope))
        self.assertNotIn("feeduser", str(envelope))
        self.assertNotIn("feedpass", str(envelope))
        changed_key = yw_api.approval_envelope(token="oauth-secret-b", **kwargs)
        self.assertNotEqual(preview_id(envelope), preview_id(changed_key))

    def test_basic_auth_preview_id_changes_with_oauth_binding_key(self):
        kwargs = {
            "method": "POST",
            "path": "user/1/hosts/h/feeds/add/start",
            "body": {"url": "https://feeduser:feedpass@example.com/feed.yml"},
        }
        first = yw_api.prepare_request(token="oauth-secret-a", **kwargs)
        same = yw_api.prepare_request(token="oauth-secret-a", **kwargs)
        changed = yw_api.prepare_request(token="oauth-secret-b", **kwargs)
        self.assertEqual(first["preview_id"], same["preview_id"])
        self.assertNotEqual(first["preview_id"], changed["preview_id"])

    def test_preview_does_not_execute_transport(self):
        calls = []
        result = yw_api.run_request(
            method="POST",
            path="user/1/hosts",
            token="secret",
            body={"host_url": "https://example.com"},
            execute=False,
            transport=lambda **kwargs: calls.append(kwargs),
        )
        self.assertEqual(calls, [])
        self.assertTrue(result["dry_run"])
        self.assertIn("preview_id", result)

    def test_execute_without_approval_is_blocked_before_transport(self):
        transport = Mock()
        with self.assertRaises(ValueError):
            yw_api.run_request(
                method="POST",
                path="user/1/hosts",
                token="secret",
                body={"host_url": "https://example.com"},
                execute=True,
                transport=transport,
            )
        transport.assert_not_called()

    def test_wrong_approval_is_blocked_before_transport(self):
        transport = Mock()
        with self.assertRaises(ValueError):
            yw_api.run_request(
                method="DELETE",
                path="user/1/hosts/h/user-added-sitemaps/7",
                token="secret",
                execute=True,
                approve="0" * 64,
                transport=transport,
            )
        transport.assert_not_called()

    def test_exact_approval_executes_transport_once(self):
        body = {"host_url": "https://example.com"}
        approve = preview_id(yw_api.approval_envelope(
            method="POST",
            path="user/1/hosts",
            token="secret",
            body=body,
        ))
        transport = Mock(return_value={"host_id": "h"})
        result = yw_api.run_request(
            method="POST",
            path="user/1/hosts",
            token="secret",
            body=body,
            execute=True,
            approve=approve,
            ack_bulk=True,
            transport=transport,
        )
        transport.assert_called_once()
        self.assertEqual(result["result"], {"host_id": "h"})
        self.assertEqual(result["schema"], "yandex-ai-execution/v1")

    def _assert_mutation_invalidates(self, approved_kwargs, changed_kwargs):
        approve = preview_id(yw_api.approval_envelope(token="secret", **approved_kwargs))
        transport = Mock()
        with self.assertRaises(ValueError):
            yw_api.run_request(
                token="secret",
                execute=True,
                approve=approve,
                transport=transport,
                **changed_kwargs,
            )
        transport.assert_not_called()

    def test_api_version_change_invalidates_approval(self):
        base = {"method": "POST", "path": "user/1/hosts/h/sitemaps/7/recrawl", "version": "v4.1", "body": None}
        changed = {**base, "version": "v4"}
        self._assert_mutation_invalidates(base, changed)

    def test_path_change_invalidates_approval(self):
        base = {"method": "POST", "path": "user/1/hosts/h/recrawl/queue", "body": {"url": "https://example.com/a"}}
        changed = {**base, "path": "user/1/hosts/h2/recrawl/queue"}
        self._assert_mutation_invalidates(base, changed)

    def test_query_change_invalidates_approval(self):
        base = {"method": "POST", "path": "user/1/hosts/h/sitemaps/7/recrawl", "version": "v4.1", "params": {"parent_id": "1"}, "body": None}
        changed = {**base, "params": {"parent_id": "2"}}
        self._assert_mutation_invalidates(base, changed)

    def test_body_change_invalidates_approval(self):
        base = {"method": "POST", "path": "user/1/hosts/h/recrawl/queue", "body": {"url": "https://example.com/a"}}
        changed = {**base, "body": {"url": "https://example.com/b"}}
        self._assert_mutation_invalidates(base, changed)

    def test_read_executes_without_approval(self):
        transport = Mock(return_value={"hosts": []})
        result = yw_api.run_request(
            method="GET",
            path="user/1/hosts",
            token="secret",
            execute=False,
            transport=transport,
        )
        transport.assert_called_once()
        self.assertEqual(result, {"hosts": []})

    def test_specialized_write_descriptors_are_all_bound_at_transport_boundary(self):
        descriptors = [
            yw_recrawl.submit_request(1, "h", "https://example.com/a", host_url="https://example.com"),
            yw_sitemaps.add_request(1, "h", "https://example.com/sitemap.xml"),
            yw_sitemaps.delete_request(1, "h", "s1"),
            yw_sitemaps.priority_recrawl_request(1, "h", "s1", parent_id="p1"),
            yw_feeds.start_request(
                1,
                "h",
                host_url="https://example.com",
                feed_url="https://example.com/feed.yml",
                feed_type="YML",
            ),
            yw_feeds.batch_add_request(
                1,
                "h",
                host_url="https://example.com",
                feeds=[{"url": "https://example.com/a.yml", "type": "YML"}],
            ),
            yw_feeds.delete_request(
                1,
                "h",
                host_url="https://example.com",
                urls=["https://example.com/a.yml"],
            ),
            yw_export.start_request(
                1,
                "h",
                dates=["2026-08-01"],
                paths=["/catalog"],
                region_ids=[213],
            ),
            yw_indexing.archive_start_request(1, "h"),
        ]
        for descriptor in descriptors:
            with self.subTest(descriptor=descriptor):
                kwargs = {
                    "method": descriptor["method"],
                    "path": descriptor["path"],
                    "version": descriptor.get("version", "v4"),
                    "params": descriptor.get("params"),
                    "body": descriptor.get("body"),
                }
                preview = yw_api.prepare_request(token="secret", **kwargs)
                self.assertTrue(preview["consequential"])
                transport = Mock(return_value={"ok": True})
                with self.assertRaises(ValueError):
                    yw_api.run_request(token="secret", execute=True, transport=transport, **kwargs)
                transport.assert_not_called()
                result = yw_api.run_request(
                    token="secret",
                    execute=True,
                    approve=preview["preview_id"],
                    ack_bulk=bool(preview["cardinality"]["bulk"]),
                    transport=transport,
                    **kwargs,
                )
                transport.assert_called_once()
                self.assertEqual(result["result"], {"ok": True})
                self.assertEqual(result["schema"], "yandex-ai-execution/v1")

    def test_api_version_is_restricted(self):
        with self.assertRaises(ValueError):
            yw_api.api_url("user", version="v999")


if __name__ == "__main__":
    unittest.main()
