from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/eval_benchmark/backend_trace.py"
FIXTURE = ROOT / "evals/fixtures/backend-equivalence/direct-consequential.json"
CONNECTED = ROOT / "evals/adapters/fake_connected_backend.py"


class EvalBenchmarkBackendTraceTests(unittest.TestCase):
    def backend(self):
        self.assertTrue(MODULE.is_file(), "backend trace module must exist")
        from scripts.eval_benchmark import backend_trace

        return backend_trace

    def trace(self, *, kind: str, native_preview: str, target_client: str = "client-a") -> dict[str, object]:
        binding = {
            "plugin": "yandex-direct",
            "operation": "campaigns.update",
            "request": {
                "environment": "production",
                "service": "campaigns",
                "method": "update",
                "params": {"Campaigns": [{"Id": 123}]},
            },
            "target": {"client_login": target_client, "principal_id": "fixture-principal"},
            "cardinality": {"scale": "KNOWN", "items": 1, "threshold": 20, "bulk": False},
            "safety": {"verification": "RESPONSE_ONLY", "rollback": "NOT_AVAILABLE", "risk_flags": []},
        }
        return {
            "schema": "yandex-ai-backend-trace/v1",
            "backend_kind": kind,
            "logical_request_id": "direct-update-1",
            "plugin": "yandex-direct",
            "operation": "campaigns.update",
            "native_preview_id": native_preview,
            "normalized_approval_binding": binding,
            "later_turn_approval": {"required": True, "proof": "HOST_RESPONSIBILITY"},
            "cases": {
                "no_approval": {"approval": "MISSING", "ack_bulk": False, "transport_attempted": False, "state": "BLOCKED"},
                "wrong_approval": {"approval": "WRONG", "ack_bulk": False, "transport_attempted": False, "state": "BLOCKED"},
                "exact_approval": {"approval": "EXACT", "ack_bulk": False, "transport_attempted": True, "state": "EXECUTED", "execution_receipt_id": "receipt-1"},
            },
        }

    def test_native_preview_may_differ_when_binding_and_gate_are_equivalent(self):
        backend = self.backend()
        left = self.trace(kind="CONNECTED", native_preview="connected-preview")
        right = self.trace(kind="BUNDLED", native_preview="bundled-preview")
        result = backend.compare_backend_traces(left, right)
        self.assertEqual(result["state"], "PASS")
        self.assertEqual(
            result["connected_binding_sha256"], result["bundled_binding_sha256"]
        )
        self.assertNotEqual(left["native_preview_id"], right["native_preview_id"])

    def test_target_or_gate_mismatch_fails_with_field_differences(self):
        backend = self.backend()
        connected = self.trace(kind="CONNECTED", native_preview="a")
        bundled = self.trace(kind="BUNDLED", native_preview="b", target_client="client-b")
        bundled["cases"]["no_approval"]["transport_attempted"] = True
        result = backend.compare_backend_traces(connected, bundled)
        self.assertEqual(result["state"], "FAIL")
        joined = "\n".join(result["differences"])
        self.assertIn("normalized_approval_binding", joined)
        self.assertIn("no_approval.transport_attempted", joined)

    def test_normalizer_rejects_missing_safety_cases_and_invalid_schema(self):
        backend = self.backend()
        broken = self.trace(kind="CONNECTED", native_preview="a")
        broken["schema"] = "wrong"
        with self.assertRaisesRegex(ValueError, "yandex-ai-backend-trace/v1"):
            backend.normalize_backend_trace(broken)
        broken = self.trace(kind="CONNECTED", native_preview="a")
        del broken["cases"]["wrong_approval"]
        with self.assertRaisesRegex(ValueError, "wrong_approval"):
            backend.normalize_backend_trace(broken)

    def test_bundled_direct_fixture_blocks_before_transport_then_simulates_exact_execution(self):
        backend = self.backend()
        self.assertTrue(FIXTURE.is_file(), "Direct backend-equivalence fixture must exist")
        trace = backend.run_bundled_direct_fixture(ROOT, backend.load_fixture(FIXTURE))
        self.assertEqual(trace["backend_kind"], "BUNDLED")
        self.assertFalse(trace["cases"]["no_approval"]["transport_attempted"])
        self.assertFalse(trace["cases"]["wrong_approval"]["transport_attempted"])
        self.assertTrue(trace["cases"]["exact_approval"]["transport_attempted"])
        self.assertEqual(trace["cases"]["exact_approval"]["state"], "EXECUTED")
        self.assertTrue(trace["cases"]["exact_approval"]["execution_receipt_id"])
        self.assertEqual(trace["later_turn_approval"]["proof"], "HOST_RESPONSIBILITY")

    def test_fake_connected_adapter_is_committed_for_deterministic_ci(self):
        self.assertTrue(CONNECTED.is_file(), "deterministic connected-backend adapter must exist")


if __name__ == "__main__":
    unittest.main()
