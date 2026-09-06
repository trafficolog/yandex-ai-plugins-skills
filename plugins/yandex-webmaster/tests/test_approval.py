import unittest


class ApprovalContractTests(unittest.TestCase):
    def test_preview_id_is_key_order_independent(self):
        from scripts._approval import preview_id

        left = {"schema": "yandex-ai-approval/v2", "body": {"b": 2, "a": 1}}
        right = {"body": {"a": 1, "b": 2}, "schema": "yandex-ai-approval/v2"}
        self.assertEqual(preview_id(left), preview_id(right))

    def test_require_approval_rejects_without_leaking_expected_digest(self):
        from scripts._approval import preview_id, require_approval

        envelope = {"schema": "yandex-ai-approval/v2", "plugin": "yandex-webmaster"}
        expected = preview_id(envelope)
        with self.assertRaises(ValueError) as raised:
            require_approval(envelope, None)
        self.assertNotIn(expected, str(raised.exception))
        self.assertIn("fresh preview", str(raised.exception))

    def test_require_approval_rejects_wrong_digest_without_leaking_expected_digest(self):
        from scripts._approval import preview_id, require_approval

        envelope = {"schema": "yandex-ai-approval/v2", "plugin": "yandex-webmaster"}
        expected = preview_id(envelope)
        with self.assertRaises(ValueError) as raised:
            require_approval(envelope, "0" * 64)
        self.assertNotIn(expected, str(raised.exception))

    def test_require_approval_accepts_exact_digest(self):
        from scripts._approval import preview_id, require_approval

        envelope = {"schema": "yandex-ai-approval/v2", "plugin": "yandex-webmaster"}
        digest = preview_id(envelope)
        self.assertEqual(require_approval(envelope, digest), digest)


if __name__ == "__main__":
    unittest.main()
