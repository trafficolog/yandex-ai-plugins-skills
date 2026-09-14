from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def skill(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8").lower()


class TestPractitionerWorkflows(unittest.TestCase):
    def test_audit_starts_with_summary_then_triage(self):
        text = skill("yandex-webmaster-audit")
        self.assertIn("host summary", text)
        for token in ["diagnostics", "indexing", "query", "links", "sitemap"]:
            self.assertIn(token, text)

    def test_volatile_operational_evidence_must_be_live(self):
        text = skill("yandex-webmaster") + skill("yandex-webmaster-recrawl")
        self.assertIn("volatile", text)
        self.assertIn("live", text)
        self.assertIn("quota", text)
        self.assertIn("task status", text)

    def test_recrawl_requires_concrete_page_level_reason(self):
        text = skill("yandex-webmaster-recrawl")
        self.assertIn("concrete", text)
        self.assertIn("changed", text)
        self.assertIn("not an indexing/ranking guarantee", text)

    def test_preview_bound_write_contract_remains(self):
        text = skill("yandex-webmaster-recrawl")
        self.assertIn("approval-contract: exact-preview", text)
        self.assertIn("approval-turn-policy: later-turn-only", text)


if __name__ == "__main__":
    unittest.main()
