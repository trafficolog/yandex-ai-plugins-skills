from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ("yandex-direct", "yandex-metrika", "yandex-webmaster")
SENTINEL = "P0_SENTINEL_SECRET_6c90b2"


def run_plugin_python(plugin: str, source: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT / "plugins" / plugin,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


class P0ExecutableSafetyContractTests(unittest.TestCase):
    def test_local_safety_kernels_converge(self):
        source = r'''
import json
from scripts import _safety
print(json.dumps({
    "approval_schema": _safety.APPROVAL_SCHEMA,
    "execution_schema": _safety.EXECUTION_SCHEMA,
    "threshold": _safety.BULK_THRESHOLD,
    "known20": _safety.known_cardinality(20),
    "known21": _safety.known_cardinality(21),
    "unknown": _safety.unknown_cardinality(),
}))
'''
        expected = {
            "approval_schema": "yandex-ai-approval/v2",
            "execution_schema": "yandex-ai-execution/v1",
            "threshold": 20,
            "known20": {"scale": "KNOWN", "items": 20, "threshold": 20, "bulk": False},
            "known21": {"scale": "KNOWN", "items": 21, "threshold": 20, "bulk": True},
            "unknown": {"scale": "UNKNOWN", "items": None, "threshold": 20, "bulk": True},
        }
        for plugin in PLUGINS:
            with self.subTest(plugin=plugin):
                self.assertEqual(run_plugin_python(plugin, source), expected)

    def test_write_plugins_block_bulk_or_unknown_before_transport(self):
        sources = {
            "yandex-direct": r'''
import json
from unittest.mock import patch
from scripts._approval import preview_id
from scripts.yd_api import YandexDirectClient
client = YandexDirectClient("secret", client_login="client")
params = {"Campaigns": [{"Id": i} for i in range(21)]}
approve = preview_id(client.approval_envelope("campaigns", "update", params))
with patch("scripts.yd_api._http.request_json") as transport:
    try:
        client.request("campaigns", "update", params, approve=approve)
        blocked = False
    except ValueError as exc:
        blocked = "ack-bulk" in str(exc)
    print(json.dumps({"blocked": blocked, "transport_called": transport.called}))
''',
            "yandex-metrika": r'''
import json
from unittest.mock import patch
from scripts import ym_api
preview = ym_api.prepare_request(method="POST", path="counter/1/goals", token="secret", body={"goal":{"name":"Lead"}})
with patch("scripts.ym_api.request_json") as transport:
    try:
        ym_api.run_request(method="POST", path="counter/1/goals", token="secret", body={"goal":{"name":"Lead"}}, execute=True, approve=preview["preview_id"])
        blocked = False
    except ValueError as exc:
        blocked = "ack-bulk" in str(exc)
    print(json.dumps({"blocked": blocked, "transport_called": transport.called}))
''',
            "yandex-webmaster": r'''
import json
from unittest.mock import Mock
from scripts import yw_api, yw_feeds
descriptor = yw_feeds.batch_add_request(1, "h", host_url="https://example.com", feeds=[{"url": f"https://example.com/{i}.yml", "type": "YML"} for i in range(21)])
preview = yw_api.prepare_request(token="secret", **descriptor)
transport = Mock(return_value={"ok": True})
try:
    yw_api.run_request(token="secret", execute=True, approve=preview["preview_id"], transport=transport, **descriptor)
    blocked = False
except ValueError as exc:
    blocked = "ack-bulk" in str(exc)
print(json.dumps({"blocked": blocked, "transport_called": transport.called}))
''',
        }
        for plugin, source in sources.items():
            with self.subTest(plugin=plugin):
                self.assertEqual(
                    run_plugin_python(plugin, source),
                    {"blocked": True, "transport_called": False},
                )

    def test_previews_and_receipts_do_not_leak_secret(self):
        sources = {
            "yandex-direct": rf'''
import json
from scripts import _safety
from scripts.yd_api import YandexDirectClient, AUTH_PRINCIPAL_DOMAIN
secret = {SENTINEL!r}
client = YandexDirectClient(secret, client_login="client")
preview = client.request("campaigns", "update", {{"Campaigns":[{{"Id":1}}]}}, dry_run=True)
receipt = _safety.execution_receipt(preview_id=preview["preview_id"], plugin="yandex-direct", operation="campaigns.update", target={{"auth_principal_binding": _safety.principal_binding(secret, domain=AUTH_PRINCIPAL_DOMAIN)}}, cardinality=preview["cardinality"], result={{"ok": True}}, verification_capability="RESPONSE_ONLY", verification_state="UNVERIFIED", rollback_capability="NOT_AVAILABLE")
print(json.dumps({{"preview": preview, "receipt": receipt}}))
''',
            "yandex-metrika": rf'''
import json
from scripts import _safety, ym_api
secret = {SENTINEL!r}
preview = ym_api.prepare_request(method="POST", path="counter/1/goals", token=secret, body={{"goal":{{"name":"Lead"}}}})
receipt = _safety.execution_receipt(preview_id=preview["preview_id"], plugin="yandex-metrika", operation="management.post.counter/1/goals", target={{"auth_principal_binding": _safety.principal_binding(secret, domain=ym_api.AUTH_PRINCIPAL_DOMAIN)}}, cardinality=preview["cardinality"], result={{"ok": True}}, verification_capability="RESPONSE_ONLY", verification_state="UNVERIFIED", rollback_capability="NOT_AVAILABLE")
print(json.dumps({{"preview": preview, "receipt": receipt}}))
''',
            "yandex-webmaster": rf'''
import json
from scripts import _safety, yw_api
secret = {SENTINEL!r}
preview = yw_api.prepare_request(method="POST", path="user/1/hosts/h/recrawl/queue", token=secret, body={{"url":"https://example.com/a"}})
receipt = _safety.execution_receipt(preview_id=preview["preview_id"], plugin="yandex-webmaster", operation="api.post.user/1/hosts/h/recrawl/queue", target={{"auth_principal_binding": _safety.principal_binding(secret, domain=yw_api.AUTH_PRINCIPAL_DOMAIN)}}, cardinality=preview["cardinality"], result={{"ok": True}}, verification_capability="RESPONSE_ONLY", verification_state="UNVERIFIED", rollback_capability="NOT_AVAILABLE")
print(json.dumps({{"preview": preview, "receipt": receipt}}))
''',
        }
        for plugin, source in sources.items():
            with self.subTest(plugin=plugin):
                payload = run_plugin_python(plugin, source)
                serialized = json.dumps(payload, ensure_ascii=False)
                self.assertNotIn(SENTINEL, serialized)
                self.assertEqual(payload["preview"]["approval_schema"], "yandex-ai-approval/v2")
                self.assertEqual(payload["receipt"]["schema"], "yandex-ai-execution/v1")

    def test_contract_matrix_declares_p0_safety_convergence(self):
        matrix = json.loads((ROOT / "docs/CONTRACT_MATRIX.json").read_text(encoding="utf-8"))
        entries = {entry["id"]: entry for entry in matrix["contracts"]}
        self.assertIn("repository.p0-safety-convergence", entries)
        entry = entries["repository.p0-safety-convergence"]
        self.assertEqual(entry["plugin"], "repository")
        self.assertEqual(entry["status"], "infrastructure")
        self.assertEqual(
            entry["test_refs"],
            [
                "tests/test_p0_executable_safety_contract.py::P0ExecutableSafetyContractTests::test_local_safety_kernels_converge",
                "tests/test_p0_executable_safety_contract.py::P0ExecutableSafetyContractTests::test_write_plugins_block_bulk_or_unknown_before_transport",
                "tests/test_p0_executable_safety_contract.py::P0ExecutableSafetyContractTests::test_previews_and_receipts_do_not_leak_secret",
            ],
        )


if __name__ == "__main__":
    unittest.main()
