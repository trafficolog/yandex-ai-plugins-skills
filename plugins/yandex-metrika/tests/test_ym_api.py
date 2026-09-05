import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from scripts._approval import preview_id
from scripts._http import oauth_headers, redact_headers
from scripts import ym_api
from scripts.ym_api import (
    approval_envelope,
    build_management_url,
    is_consequential,
    prepare_request,
    run_request,
)


class TestMetrikaApi(unittest.TestCase):
    def test_oauth_header_and_redaction(self):
        self.assertEqual(oauth_headers("secret")["Authorization"], "OAuth secret")
        self.assertEqual(
            redact_headers({"Authorization": "OAuth secret", "Accept": "application/json"}),
            {"Authorization": "OAuth ***", "Accept": "application/json"},
        )

    def test_management_url_encodes_query(self):
        self.assertEqual(
            build_management_url("counters", {"per_page": 10, "search_string": "мой сайт"}),
            "https://api-metrika.yandex.net/management/v1/counters?per_page=10&search_string=%D0%BC%D0%BE%D0%B9+%D1%81%D0%B0%D0%B9%D1%82",
        )

    def test_write_methods_are_consequential(self):
        self.assertFalse(is_consequential("GET"))
        for method in ["POST", "PUT", "PATCH", "DELETE"]:
            self.assertTrue(is_consequential(method), method)

    def test_prepare_write_request_redacts_token_and_emits_preview_id(self):
        body = {"goal": {"name": "Lead"}}
        preview = prepare_request(
            method="POST",
            path="counter/123/goals",
            token="secret",
            body=body,
        )
        self.assertEqual(preview["headers"]["Authorization"], "OAuth ***")
        self.assertEqual(preview["method"], "POST")
        self.assertEqual(preview["body"], body)
        envelope = approval_envelope(
            method="POST",
            path="counter/123/goals",
            token="secret",
            query=None,
            body=body,
        )
        self.assertEqual(preview["preview_id"], preview_id(envelope))

    def test_execute_without_approval_is_blocked_before_transport(self):
        with patch("scripts.ym_api.request_json") as request_json:
            with self.assertRaises(ValueError):
                run_request(
                    method="POST",
                    path="counter/123/goals",
                    token="secret",
                    body={"goal": {"name": "Lead"}},
                    execute=True,
                )
        request_json.assert_not_called()

    def test_wrong_approval_is_blocked_before_transport(self):
        with patch("scripts.ym_api.request_json") as request_json:
            with self.assertRaises(ValueError):
                run_request(
                    method="POST",
                    path="counter/123/goals",
                    token="secret",
                    body={"goal": {"name": "Lead"}},
                    execute=True,
                    approve="0" * 64,
                    ack_bulk=True,
                )
        request_json.assert_not_called()

    def test_exact_approval_executes_once(self):
        body = {"goal": {"name": "Lead"}}
        envelope = approval_envelope(
            method="POST",
            path="counter/123/goals",
            token="secret",
            query=None,
            body=body,
        )
        approve = preview_id(envelope)
        with patch("scripts.ym_api.request_json", return_value=({}, {"goal": {"id": 7}})) as request_json:
            result = run_request(
                method="POST",
                path="counter/123/goals",
                token="secret",
                body=body,
                execute=True,
                approve=approve,
                ack_bulk=True,
            )
        request_json.assert_called_once()
        self.assertEqual(result["result"], {"goal": {"id": 7}})
        self.assertEqual(result["schema"], "yandex-ai-execution/v1")

    def test_path_change_invalidates_approval(self):
        body = {"goal": {"name": "Lead"}}
        approve = preview_id(approval_envelope(
            method="POST", path="counter/123/goals", token="secret", query=None, body=body
        ))
        with patch("scripts.ym_api.request_json") as request_json:
            with self.assertRaises(ValueError):
                run_request(
                    method="POST",
                    path="counter/124/goals",
                    token="secret",
                    body=body,
                    execute=True,
                    approve=approve,
                )
        request_json.assert_not_called()

    def test_query_change_invalidates_approval(self):
        body = {"goal": {"name": "Lead"}}
        approve = preview_id(approval_envelope(
            method="POST",
            path="counter/123/goals",
            token="secret",
            query={"lang": "ru"},
            body=body,
        ))
        with patch("scripts.ym_api.request_json") as request_json:
            with self.assertRaises(ValueError):
                run_request(
                    method="POST",
                    path="counter/123/goals",
                    token="secret",
                    query={"lang": "en"},
                    body=body,
                    execute=True,
                    approve=approve,
                )
        request_json.assert_not_called()

    def test_body_change_invalidates_approval(self):
        approve = preview_id(approval_envelope(
            method="POST",
            path="counter/123/goals",
            token="secret",
            query=None,
            body={"goal": {"name": "Lead"}},
        ))
        with patch("scripts.ym_api.request_json") as request_json:
            with self.assertRaises(ValueError):
                run_request(
                    method="POST",
                    path="counter/123/goals",
                    token="secret",
                    body={"goal": {"name": "Sale"}},
                    execute=True,
                    approve=approve,
                )
        request_json.assert_not_called()

    def test_read_executes_without_approval(self):
        with patch("scripts.ym_api.request_json", return_value=({}, {"counters": []})) as request_json:
            result = run_request(
                method="GET",
                path="counters",
                token="secret",
                execute=False,
            )
        request_json.assert_called_once()
        self.assertEqual(result, {"counters": []})

    def test_cli_execute_forwards_approval(self):
        captured = {}

        def fake_run_request(**kwargs):
            captured.update(kwargs)
            return {"ok": True}

        with patch.object(ym_api, "run_request", side_effect=fake_run_request):
            with patch.dict("os.environ", {"YANDEX_METRIKA_TOKEN": "secret"}):
                with redirect_stdout(io.StringIO()):
                    rc = ym_api.main([
                        "counter/123/goals",
                        "--method", "POST",
                        "--body", '{"goal":{"name":"Lead"}}',
                        "--execute",
                        "--approve", "a" * 64,
                    ])
        self.assertEqual(rc, 0)
        self.assertTrue(captured["execute"])
        self.assertEqual(captured["approve"], "a" * 64)
        self.assertFalse(captured["ack_bulk"])


if __name__ == "__main__":
    unittest.main()
