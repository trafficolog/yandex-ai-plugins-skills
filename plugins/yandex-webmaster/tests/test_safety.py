import importlib
import importlib.util
import unittest


class SafetyKernelTests(unittest.TestCase):
    def _module(self):
        spec = importlib.util.find_spec("scripts._safety")
        self.assertIsNotNone(spec, "Webmaster must provide a local scripts._safety module")
        return importlib.import_module("scripts._safety")

    def test_exact_contract(self):
        safety = self._module()
        self.assertEqual(safety.APPROVAL_SCHEMA, "yandex-ai-approval/v2")
        self.assertEqual(safety.EXECUTION_SCHEMA, "yandex-ai-execution/v1")
        self.assertEqual(safety.BULK_THRESHOLD, 20)
        self.assertEqual(
            safety.known_cardinality(21),
            {"scale": "KNOWN", "items": 21, "threshold": 20, "bulk": True},
        )
        self.assertEqual(
            safety.unknown_cardinality(),
            {"scale": "UNKNOWN", "items": None, "threshold": 20, "bulk": True},
        )

    def test_bulk_ack_and_principal_binding(self):
        safety = self._module()
        with self.assertRaisesRegex(ValueError, "ack-bulk"):
            safety.require_bulk_ack(safety.known_cardinality(21), False)
        safety.require_bulk_ack(safety.known_cardinality(21), True)
        first = safety.principal_binding(
            "oauth-a", domain=b"yandex-webmaster-auth-principal/v2"
        )
        changed = safety.principal_binding(
            "oauth-b", domain=b"yandex-webmaster-auth-principal/v2"
        )
        self.assertNotEqual(first, changed)
        self.assertNotIn("oauth-a", first)


if __name__ == "__main__":
    unittest.main()
