import importlib
import importlib.util
import unittest


class SafetyKernelTests(unittest.TestCase):
    def _module(self):
        spec = importlib.util.find_spec("scripts._safety")
        self.assertIsNotNone(spec, "Direct must provide a local scripts._safety module")
        return importlib.import_module("scripts._safety")

    def test_exact_contract(self):
        safety = self._module()
        self.assertEqual(safety.APPROVAL_SCHEMA, "yandex-ai-approval/v2")
        self.assertEqual(safety.EXECUTION_SCHEMA, "yandex-ai-execution/v1")
        self.assertEqual(safety.BULK_THRESHOLD, 20)
        self.assertEqual(
            safety.known_cardinality(3),
            {"scale": "KNOWN", "items": 3, "threshold": 20, "bulk": False},
        )
        self.assertEqual(
            safety.unknown_cardinality(),
            {"scale": "UNKNOWN", "items": None, "threshold": 20, "bulk": True},
        )

    def test_bulk_ack_gate(self):
        safety = self._module()
        safety.require_bulk_ack(safety.known_cardinality(20), False)
        with self.assertRaisesRegex(ValueError, "ack-bulk"):
            safety.require_bulk_ack(safety.known_cardinality(21), False)
        with self.assertRaisesRegex(ValueError, "ack-bulk"):
            safety.require_bulk_ack(safety.unknown_cardinality(), False)
        safety.require_bulk_ack(safety.known_cardinality(21), True)

    def test_principal_binding_is_stable_and_token_sensitive(self):
        safety = self._module()
        first = safety.principal_binding(
            "secret-a", domain=b"yandex-direct-auth-principal/v2"
        )
        same = safety.principal_binding(
            "secret-a", domain=b"yandex-direct-auth-principal/v2"
        )
        changed = safety.principal_binding(
            "secret-b", domain=b"yandex-direct-auth-principal/v2"
        )
        self.assertEqual(first, same)
        self.assertNotEqual(first, changed)
        self.assertNotIn("secret-a", first)


if __name__ == "__main__":
    unittest.main()
