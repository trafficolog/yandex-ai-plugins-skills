from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts._approval import preview_id
from scripts.ym_logs import (
    download_part,
    logs_approval_envelope,
    logs_endpoint,
    prepare_logs_request,
    run_json_action,
    validate_period,
)


class _Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b"a\tb\n1\t2\n"

    def getcode(self):
        return 200


class TestMetrikaLogs(unittest.TestCase):
    def test_endpoint_lifecycle(self):
        self.assertTrue(logs_endpoint(123, "evaluate").endswith("/counter/123/logrequests/evaluate"))
        self.assertTrue(logs_endpoint(123, "create").endswith("/counter/123/logrequests"))
        self.assertTrue(logs_endpoint(123, "status", request_id=7).endswith("/counter/123/logrequest/7"))
        self.assertTrue(logs_endpoint(123, "download", request_id=7, part_number=2).endswith("/counter/123/logrequest/7/part/2/download"))
        self.assertTrue(logs_endpoint(123, "clean", request_id=7).endswith("/counter/123/logrequest/7/clean"))

    def test_period_must_not_exceed_one_year(self):
        validate_period("2026-01-01", "2027-01-01", today=date(2030, 1, 1))
        with self.assertRaises(ValueError):
            validate_period("2026-01-01", "2027-01-02", today=date(2030, 1, 1))
        with self.assertRaises(ValueError):
            validate_period("2026-02-01", "2026-01-31", today=date(2030, 1, 1))

    def test_current_or_future_date2_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_period("2026-08-01", "2026-09-01", today=date(2026, 9, 1))
        with self.assertRaises(ValueError):
            validate_period("2026-08-01", "2026-09-02", today=date(2026, 9, 1))

    def test_clean_preview_redacts_token_and_emits_preview_id(self):
        preview = prepare_logs_request(123, "clean", token="secret", request_id=7)
        self.assertEqual(preview["headers"]["Authorization"], "OAuth ***")
        self.assertTrue(preview["consequential"])
        envelope = logs_approval_envelope(123, "clean", token="secret", request_id=7)
        self.assertEqual(preview["preview_id"], preview_id(envelope))

    def test_create_execute_without_approval_is_blocked_before_transport(self):
        query = {"date1": "2026-08-01", "date2": "2026-08-02"}
        with patch("scripts.ym_logs.request_json") as request_json:
            with self.assertRaises(ValueError):
                run_json_action(
                    123,
                    "create",
                    token="secret",
                    query=query,
                    execute=True,
                )
        request_json.assert_not_called()

    def test_clean_execute_without_approval_is_blocked_before_transport(self):
        with patch("scripts.ym_logs.request_json") as request_json:
            with self.assertRaises(ValueError):
                run_json_action(
                    123,
                    "clean",
                    token="secret",
                    request_id=7,
                    execute=True,
                )
        request_json.assert_not_called()

    def test_wrong_approval_is_blocked_before_transport(self):
        with patch("scripts.ym_logs.request_json") as request_json:
            with self.assertRaises(ValueError):
                run_json_action(
                    123,
                    "clean",
                    token="secret",
                    request_id=7,
                    execute=True,
                    approve="0" * 64,
                )
        request_json.assert_not_called()

    def test_exact_create_approval_executes_once(self):
        query = {"date1": "2026-08-01", "date2": "2026-08-02"}
        approve = preview_id(logs_approval_envelope(123, "create", token="secret", query=query))
        with patch("scripts.ym_logs.request_json", return_value=({}, {"log_request": {"request_id": 9}})) as request_json:
            result = run_json_action(
                123,
                "create",
                token="secret",
                query=query,
                execute=True,
                approve=approve,
            )
        request_json.assert_called_once()
        self.assertEqual(result["result"], {"log_request": {"request_id": 9}})
        self.assertEqual(result["schema"], "yandex-ai-execution/v1")

    def test_exact_clean_approval_executes_once(self):
        approve = preview_id(logs_approval_envelope(123, "clean", token="secret", request_id=7))
        with patch("scripts.ym_logs.request_json", return_value=({}, {"success": True})) as request_json:
            result = run_json_action(
                123,
                "clean",
                token="secret",
                request_id=7,
                execute=True,
                approve=approve,
            )
        request_json.assert_called_once()
        self.assertEqual(result["result"], {"success": True})
        self.assertEqual(result["schema"], "yandex-ai-execution/v1")

    def test_counter_change_invalidates_approval(self):
        approve = preview_id(logs_approval_envelope(123, "clean", token="secret", request_id=7))
        with patch("scripts.ym_logs.request_json") as request_json:
            with self.assertRaises(ValueError):
                run_json_action(
                    124,
                    "clean",
                    token="secret",
                    request_id=7,
                    execute=True,
                    approve=approve,
                )
        request_json.assert_not_called()

    def test_action_change_invalidates_approval(self):
        approve = preview_id(logs_approval_envelope(123, "clean", token="secret", request_id=7))
        query = {"date1": "2026-08-01", "date2": "2026-08-02"}
        with patch("scripts.ym_logs.request_json") as request_json:
            with self.assertRaises(ValueError):
                run_json_action(
                    123,
                    "create",
                    token="secret",
                    query=query,
                    execute=True,
                    approve=approve,
                )
        request_json.assert_not_called()

    def test_request_id_change_invalidates_approval(self):
        approve = preview_id(logs_approval_envelope(123, "clean", token="secret", request_id=7))
        with patch("scripts.ym_logs.request_json") as request_json:
            with self.assertRaises(ValueError):
                run_json_action(
                    123,
                    "clean",
                    token="secret",
                    request_id=8,
                    execute=True,
                    approve=approve,
                )
        request_json.assert_not_called()

    def test_query_change_invalidates_approval(self):
        approved_query = {"date1": "2026-08-01", "date2": "2026-08-02", "source": "hits"}
        changed_query = {"date1": "2026-08-01", "date2": "2026-08-02", "source": "visits"}
        approve = preview_id(logs_approval_envelope(123, "create", token="secret", query=approved_query))
        with patch("scripts.ym_logs.request_json") as request_json:
            with self.assertRaises(ValueError):
                run_json_action(
                    123,
                    "create",
                    token="secret",
                    query=changed_query,
                    execute=True,
                    approve=approve,
                )
        request_json.assert_not_called()

    def test_evaluate_and_status_execute_without_approval(self):
        with patch("scripts.ym_logs.request_json", return_value=({}, {"ok": True})) as request_json:
            evaluate = run_json_action(
                123,
                "evaluate",
                token="secret",
                query={"date1": "2026-08-01", "date2": "2026-08-02"},
            )
            status = run_json_action(123, "status", token="secret", request_id=7)
        self.assertEqual(request_json.call_count, 2)
        self.assertEqual(evaluate, {"ok": True})
        self.assertEqual(status, {"ok": True})

    def test_download_part_writes_file(self):
        seen = {}

        def opener(request, timeout=30):
            seen["authorization"] = request.headers.get("Authorization")
            return _Response()

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "part.tsv"
            result = download_part(123, 7, 2, "secret", out, opener=opener)
            self.assertEqual(result, out)
            self.assertEqual(out.read_bytes(), b"a\tb\n1\t2\n")
            self.assertEqual(seen["authorization"], "OAuth secret")


if __name__ == "__main__":
    unittest.main()
