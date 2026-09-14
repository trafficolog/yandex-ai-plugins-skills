from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def skill(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8").lower()


class TestPractitionerWorkflows(unittest.TestCase):
    def test_reporting_requires_business_goal_and_comparable_basis(self):
        text = skill("yandex-direct-reporting")
        self.assertIn("business conversion goal", text)
        self.assertIn("conversion delay", text)
        self.assertIn("aggregate raw", text)
        self.assertIn("zero denominator", text)

    def test_optimization_uses_observation_to_effect_loop(self):
        text = skill("yandex-direct-optimize")
        for token in ["observation", "hypothesis", "verification", "effect metric"]:
            self.assertIn(token, text)
        self.assertIn("success criterion", text)
        self.assertIn("stop", text)

    def test_keywords_treat_rare_demand_as_data_sufficiency_problem(self):
        text = skill("yandex-direct-keywords")
        self.assertIn("rarely_served", text)
        self.assertIn("data sufficiency", text)
        self.assertIn("consolidat", text)

    def test_practical_contract_does_not_weaken_preview_approval(self):
        for name in ["yandex-direct-optimize", "yandex-direct-keywords", "yandex-direct-budget"]:
            text = skill(name)
            self.assertIn("approval-contract: exact-preview", text)
            self.assertIn("approval-turn-policy: later-turn-only", text)


if __name__ == "__main__":
    unittest.main()
