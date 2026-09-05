import io
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from scripts import yd_api
from scripts._approval import preview_id
from scripts.yd_api import YandexDirectClient


class TestYandexDirectClient(unittest.TestCase):
    def test_uses_v501_endpoint(self):
        client = YandexDirectClient("token")
        self.assertEqual(
            client.endpoint("campaigns"),
            "https://api.direct.yandex.com/json/v501/campaigns",
        )

    def test_client_login_header_is_optional(self):
        without_login = YandexDirectClient("token").headers()
        with_login = YandexDirectClient("token", client_login="agency-client").headers()
        self.assertNotIn("Client-Login", without_login)
        self.assertEqual(with_login["Client-Login"], "agency-client")

    def test_dry_run_redacts_token_and_emits_preview_id(self):
        client = YandexDirectClient("secret-token", client_login="client")
        preview = client.request("campaigns", "update", {"Campaigns": [{"Id": 123}]}, dry_run=True)
        self.assertTrue(preview["dry_run"])
        self.assertEqual(preview["headers"]["Authorization"], "Bearer ***REDACTED***")
        self.assertEqual(preview["body"]["method"], "update")
        self.assertEqual(preview["approval_schema"], "yandex-ai-approval/v2")
        self.assertEqual(preview["cardinality"]["items"], 1)
        self.assertEqual(preview["safety"]["verification"], "RESPONSE_ONLY")
        self.assertEqual(preview["safety"]["rollback"], "NOT_AVAILABLE")
        self.assertEqual(preview["preview_id"], preview_id(client.approval_envelope("campaigns", "update", {"Campaigns": [{"Id": 123}]})))
        self.assertNotIn("secret-token", str(client.approval_envelope("campaigns", "update", {})))

    def test_v2_envelope_binds_target_principal_and_scale(self):
        client = YandexDirectClient("secret-token", client_login="client-a")
        envelope = client.approval_envelope(
            "campaigns", "update", {"Campaigns": [{"Id": 1}, {"Id": 2}]}
        )
        self.assertEqual(envelope["schema"], "yandex-ai-approval/v2")
        self.assertEqual(envelope["target"]["client_login"], "client-a")
        self.assertIn("auth_principal_binding", envelope["target"])
        self.assertEqual(envelope["cardinality"]["items"], 2)
        self.assertFalse(envelope["cardinality"]["bulk"])
        self.assertNotIn("secret-token", str(envelope))

    def test_v1_digest_cannot_authorize_v2_execution(self):
        client = YandexDirectClient("token", client_login="client")
        params = {"Campaigns": [{"Id": 123}]}
        legacy = {
            "schema": "yandex-ai-approval/v1",
            "plugin": "yandex-direct",
            "operation": "campaigns.update",
            "method": "POST",
            "target": {
                "environment": "production",
                "client_login": "client",
                "auth_principal_hmac_sha256": yd_api.auth_principal_binding("token"),
            },
            "url": client.endpoint("campaigns"),
            "body": client.body("update", params),
            "artifacts": [],
        }
        with patch("scripts.yd_api._http.request_json", return_value=({}, {})) as request_json:
            with self.assertRaises(ValueError):
                client.request("campaigns", "update", params, approve=preview_id(legacy))
        request_json.assert_not_called()

    def test_write_execute_requires_approval_before_transport(self):
        client = YandexDirectClient("token", client_login="client")
        with patch("scripts.yd_api._http.request_json") as request_json:
            with self.assertRaises(ValueError):
                client.request("campaigns", "update", {"Campaigns": [{"Id": 123}]})
        request_json.assert_not_called()

    def test_wrong_approval_does_not_call_transport(self):
        client = YandexDirectClient("token", client_login="client")
        with patch("scripts.yd_api._http.request_json") as request_json:
            with self.assertRaises(ValueError):
                client.request(
                    "campaigns",
                    "update",
                    {"Campaigns": [{"Id": 123}]},
                    approve="0" * 64,
                )
        request_json.assert_not_called()

    def test_exact_approval_calls_transport_once(self):
        client = YandexDirectClient("token", client_login="client")
        params = {"Campaigns": [{"Id": 123}]}
        approve = preview_id(client.approval_envelope("campaigns", "update", params))
        api_payload = {"result": {"UpdateResults": []}}
        with patch("scripts.yd_api._http.request_json", return_value=(api_payload, {})) as request_json:
            result = client.request("campaigns", "update", params, approve=approve)
        request_json.assert_called_once()
        self.assertEqual(result["result"], api_payload)

    def test_bulk_write_needs_ack_before_transport(self):
        client = YandexDirectClient("token", client_login="client")
        params = {"Campaigns": [{"Id": i} for i in range(21)]}
        approve = preview_id(client.approval_envelope("campaigns", "update", params))
        with patch("scripts.yd_api._http.request_json", return_value=({}, {})) as request_json:
            with self.assertRaisesRegex(ValueError, "ack-bulk"):
                client.request("campaigns", "update", params, approve=approve)
        request_json.assert_not_called()

    def test_unknown_scale_needs_ack_before_transport(self):
        client = YandexDirectClient("token")
        params = {"OpaqueMutation": {"Id": 1}}
        approve = preview_id(client.approval_envelope("strategies", "update", params))
        with patch("scripts.yd_api._http.request_json", return_value=({}, {})) as request_json:
            with self.assertRaisesRegex(ValueError, "ack-bulk"):
                client.request("strategies", "update", params, approve=approve)
        request_json.assert_not_called()

    def test_write_returns_execution_receipt(self):
        client = YandexDirectClient("token", client_login="client")
        params = {"Campaigns": [{"Id": 123}]}
        approve = preview_id(client.approval_envelope("campaigns", "update", params))
        api_payload = {"result": {"UpdateResults": [{"Id": 123}]}}
        with patch("scripts.yd_api._http.request_json", return_value=(api_payload, {})):
            receipt = client.request("campaigns", "update", params, approve=approve)
        self.assertEqual(receipt.get("schema"), "yandex-ai-execution/v1")
        self.assertEqual(receipt.get("preview_id"), approve)
        self.assertEqual(receipt.get("execution"), {"state": "EXECUTED"})
        self.assertEqual(
            receipt.get("verification"),
            {"capability": "RESPONSE_ONLY", "state": "UNVERIFIED"},
        )
        self.assertEqual(receipt.get("rollback", {}).get("capability"), "NOT_AVAILABLE")

    def test_client_login_change_invalidates_approval(self):
        params = {"Campaigns": [{"Id": 123}]}
        source = YandexDirectClient("token", client_login="client-a")
        approve = preview_id(source.approval_envelope("campaigns", "update", params))
        target = YandexDirectClient("token", client_login="client-b")
        with patch("scripts.yd_api._http.request_json") as request_json:
            with self.assertRaises(ValueError):
                target.request("campaigns", "update", params, approve=approve)
        request_json.assert_not_called()

    def test_token_change_invalidates_approval_without_client_login(self):
        params = {"Campaigns": [{"Id": 123}]}
        source = YandexDirectClient("token-account-a")
        approve = preview_id(source.approval_envelope("campaigns", "update", params))
        target = YandexDirectClient("token-account-b")
        with patch("scripts.yd_api._http.request_json") as request_json:
            with self.assertRaises(ValueError):
                target.request("campaigns", "update", params, approve=approve)
        request_json.assert_not_called()

    def test_auth_principal_binding_is_stable_but_token_sensitive(self):
        params = {"Campaigns": [{"Id": 123}]}
        first = YandexDirectClient("secret-token-a").approval_envelope("campaigns", "update", params)
        same = YandexDirectClient("secret-token-a").approval_envelope("campaigns", "update", params)
        changed = YandexDirectClient("secret-token-b").approval_envelope("campaigns", "update", params)
        self.assertEqual(first, same)
        self.assertNotEqual(first, changed)
        self.assertNotIn("secret-token-a", str(first))
        self.assertNotIn("secret-token-b", str(changed))

    def test_service_change_invalidates_approval(self):
        client = YandexDirectClient("token", client_login="client")
        params = {"Campaigns": [{"Id": 123}]}
        approve = preview_id(client.approval_envelope("campaigns", "update", params))
        with patch("scripts.yd_api._http.request_json") as request_json:
            with self.assertRaises(ValueError):
                client.request("adgroups", "update", params, approve=approve)
        request_json.assert_not_called()

    def test_body_change_invalidates_approval(self):
        client = YandexDirectClient("token", client_login="client")
        approved_params = {"Campaigns": [{"Id": 123}]}
        changed_params = {"Campaigns": [{"Id": 124}]}
        approve = preview_id(client.approval_envelope("campaigns", "update", approved_params))
        with patch("scripts.yd_api._http.request_json") as request_json:
            with self.assertRaises(ValueError):
                client.request("campaigns", "update", changed_params, approve=approve)
        request_json.assert_not_called()

    def test_known_read_method_executes_without_approval(self):
        client = YandexDirectClient("token")
        with patch("scripts.yd_api._http.request_json", return_value=({"result": {}}, {})) as request_json:
            client.request("campaigns", "get", {})
        request_json.assert_called_once()

    def _run_cli_and_capture_dry_run(self, method: str) -> bool:
        captured = {}

        def fake_request(
            self,
            service,
            request_method,
            params,
            *,
            dry_run=False,
            approve=None,
            ack_bulk=False,
        ):
            captured["service"] = service
            captured["method"] = request_method
            captured["dry_run"] = dry_run
            captured["approve"] = approve
            captured["ack_bulk"] = ack_bulk
            return {"dry_run": dry_run}

        with patch.dict(os.environ, {"YANDEX_DIRECT_TOKEN": "token"}, clear=False):
            with patch.object(yd_api.YandexDirectClient, "request", new=fake_request):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    rc = yd_api.main(["bids", method, "--params", "{}"])
        self.assertEqual(rc, 0)
        return captured["dry_run"]

    def test_set_defaults_to_preview_without_execute(self):
        self.assertTrue(self._run_cli_and_capture_dry_run("set"))

    def test_unknown_method_defaults_to_preview_without_execute(self):
        self.assertTrue(self._run_cli_and_capture_dry_run("frobnicate"))

    def test_method_classification_is_case_insensitive(self):
        self.assertFalse(self._run_cli_and_capture_dry_run("GET"))
        self.assertTrue(self._run_cli_and_capture_dry_run("Set"))

    def test_cli_execute_passes_approval_to_client(self):
        captured = {}

        def fake_request(
            self,
            service,
            request_method,
            params,
            *,
            dry_run=False,
            approve=None,
            ack_bulk=False,
        ):
            captured["dry_run"] = dry_run
            captured["approve"] = approve
            captured["ack_bulk"] = ack_bulk
            return {"ok": True}

        with patch.dict(os.environ, {"YANDEX_DIRECT_TOKEN": "token"}, clear=False):
            with patch.object(yd_api.YandexDirectClient, "request", new=fake_request):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    rc = yd_api.main([
                        "campaigns",
                        "update",
                        "--params",
                        "{}",
                        "--execute",
                        "--approve",
                        "a" * 64,
                    ])
        self.assertEqual(rc, 0)
        self.assertFalse(captured["dry_run"])
        self.assertEqual(captured["approve"], "a" * 64)
        self.assertFalse(captured["ack_bulk"])

    def test_cli_ack_bulk_is_forwarded(self):
        captured = {}

        def fake_request(
            self,
            service,
            request_method,
            params,
            *,
            dry_run=False,
            approve=None,
            ack_bulk=False,
        ):
            captured["ack_bulk"] = ack_bulk
            return {"ok": True}

        with patch.dict(os.environ, {"YANDEX_DIRECT_TOKEN": "token"}, clear=False):
            with patch.object(yd_api.YandexDirectClient, "request", new=fake_request):
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    try:
                        rc = yd_api.main([
                            "campaigns",
                            "update",
                            "--params",
                            "{}",
                            "--execute",
                            "--approve",
                            "a" * 64,
                            "--ack-bulk",
                        ])
                    except SystemExit as exc:
                        self.fail(f"--ack-bulk must be accepted by the CLI: {exc}")
        self.assertEqual(rc, 0)
        self.assertTrue(captured["ack_bulk"])


if __name__ == "__main__":
    unittest.main()
