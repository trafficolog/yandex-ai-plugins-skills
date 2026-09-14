from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def skill(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8").lower()


class TestPractitionerWorkflows(unittest.TestCase):
    def test_business_goals_are_distinct_from_micro_events(self):
        text = skill("yandex-metrika-conversions")
        self.assertIn("business outcome", text)
        self.assertIn("micro", text)
        self.assertIn("zero", text)
        self.assertIn("denominator", text)

    def test_reporting_requires_comparable_measurement_basis(self):
        text = skill("yandex-metrika-reporting")
        self.assertIn("same goal", text)
        self.assertIn("same attribution", text)
        self.assertIn("incomplete access", text)

    def test_ecommerce_pnl_requires_compatible_spend_and_revenue(self):
        text = skill("yandex-metrika-ecommerce")
        self.assertIn("pnl", text)
        self.assertIn("compatible spend", text)
        self.assertIn("revenue", text)
        self.assertIn("clicks", text)
        self.assertIn("visits", text)

    def test_modern_attribution_contract_is_preserved(self):
        text = skill("yandex-metrika-attribution")
        self.assertIn("automatic", text)
        self.assertIn("do not silently use legacy `lastsign`", text)


if __name__ == "__main__":
    unittest.main()
