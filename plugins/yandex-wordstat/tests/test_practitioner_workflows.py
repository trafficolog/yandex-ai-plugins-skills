from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def skill(name: str) -> str:
    return (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8").lower()


class TestPractitionerWorkflows(unittest.TestCase):
    def test_research_establishes_business_and_region_before_target_demand(self):
        text = skill("yandex-wordstat-research")
        self.assertIn("what the business", text)
        self.assertIn("region", text)
        self.assertIn("target demand", text)

    def test_high_priority_or_ambiguous_intent_is_verified_with_search(self):
        text = skill("yandex-wordstat-research") + skill("yandex-wordstat-semantics")
        self.assertIn("intent", text)
        self.assertIn("yandex-search", text)
        self.assertIn("ambiguous", text)
        self.assertIn("adjacent", text)

    def test_router_exposes_missed_demand_workflow(self):
        text = skill("yandex-wordstat")
        self.assertIn("missed demand", text)
        self.assertIn("direct", text)
        self.assertIn("search", text)

    def test_associations_remain_candidates_not_target_demand(self):
        text = skill("yandex-wordstat-semantics")
        self.assertIn("associations", text)
        self.assertIn("nois", text)
        self.assertIn("candidate", text)


if __name__ == "__main__":
    unittest.main()
