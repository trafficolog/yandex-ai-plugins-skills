import importlib
import importlib.util
import unittest


class SafetyKernelTests(unittest.TestCase):
    def _module(self):
        spec = importlib.util.find_spec("scripts._safety")
        self.assertIsNotNone(spec, "Metrika must provide a local scripts._safety module")
        return importlib.import_module("scripts._safety")

    def test_exact_contract(self):
        safety = self._module()
        self.assertEqual(safety.APPROVAL_SCHEMA, "yandex-ai-approval/v2")
        self.assertEqual(safety.EXECUTION_SCHEMA, "yandex-ai-execution/v1")
        self.assertEqual(safety.BULK_THRESHOLD, 20)
        self.assertEqual(
            safety.known_cardinality(1, artifact_rows=37),
            {
                "scale": "KNOWN",
                "items": 1,
                "threshold": 20,
                "bulk": False,
                "artifact_rows": 37,
            },
        )
        self.assertEqual(
            safety.unknown_cardinality(),
            {"scale": "UNKNOWN", "items": None, "threshold": 20, "bulk": True},
        )

    def test_bulk_ack_and_principal_binding(self):
        safety = self._module()
        with self.assertRaisesRegex(ValueError, "ack-bulk"):
            safety.require_bulk_ack(safety.unknown_cardinality(), False)
        safety.require_bulk_ack(safety.unknown_cardinality(), True)
        first = safety.principal_binding(
            "token-a", domain=b"yandex-metrika-auth-principal/v2"
        )
        changed = safety.principal_binding(
            "token-b", domain=b"yandex-metrika-auth-principal/v2"
        )
        self.assertNotEqual(first, changed)
        self.assertNotIn("token-a", first)


if __name__ == "__main__":
    unittest.main()
