import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {
    "yandex-wordstat",
    "yandex-wordstat-research",
    "yandex-wordstat-semantics",
    "yandex-wordstat-topic-map",
    "yandex-wordstat-frequency",
    "yandex-wordstat-dynamics",
    "yandex-wordstat-regions",
    "yandex-wordstat-trends",
    "yandex-wordstat-operators",
    "yandex-wordstat-api",
}


class TestPluginLayout(unittest.TestCase):
    def test_codex_manifest_contract(self):
        data = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "yandex-wordstat")
        self.assertEqual(data["version"], "1.2.0")
        self.assertEqual(data["skills"], "./skills/")

    def test_exact_skill_set_exists(self):
        actual = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual(actual, EXPECTED_SKILLS)

    def test_every_skill_is_discoverable(self):
        for skill in sorted(EXPECTED_SKILLS):
            text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), skill)
            self.assertIn("description: Use when", text, skill)

    def test_env_example_has_cloud_credentials(self):
        text = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("YANDEX_WORDSTAT_API_KEY=", text)
        self.assertIn("YANDEX_WORDSTAT_IAM_TOKEN=", text)
        self.assertIn("YANDEX_WORDSTAT_FOLDER_ID=", text)

    def test_evals_have_scenarios(self):
        data = json.loads((ROOT / "evals/scenarios.json").read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 2)
        self.assertGreaterEqual(len(data["scenarios"]), 13)
        for scenario in data["scenarios"]:
            expect = scenario["expect"]
            self.assertIn(expect["outcome"], {"comply", "comply_with_limitations", "refuse"})
            self.assertIn("must_mention_tokens", expect)
            self.assertIn("must_convey", expect)
            self.assertIn("must_not_claim", expect)

    def test_package_docs_exist(self):
        for path in ["README.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md"]:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_production_workflow_contracts(self):
        router = (ROOT / "skills/yandex-wordstat/SKILL.md").read_text(encoding="utf-8")
        semantics = (ROOT / "skills/yandex-wordstat-semantics/SKILL.md").read_text(encoding="utf-8")
        topic_map = (ROOT / "skills/yandex-wordstat-topic-map/SKILL.md").read_text(encoding="utf-8")
        dynamics = (ROOT / "skills/yandex-wordstat-dynamics/SKILL.md").read_text(encoding="utf-8")
        trends = (ROOT / "skills/yandex-wordstat-trends/SKILL.md").read_text(encoding="utf-8")
        api = (ROOT / "skills/yandex-wordstat-api/SKILL.md").read_text(encoding="utf-8")
        research = (ROOT / "skills/yandex-wordstat-research/SKILL.md").read_text(encoding="utf-8")
        for name in sorted(EXPECTED_SKILLS - {"yandex-wordstat"}):
            self.assertIn(name, router)
        self.assertIn("total demand", semantics.lower())
        self.assertIn("provenance", semantics.lower())
        self.assertIn("WORDSTAT_ASSOCIATIONS_CAPPED", semantics)
        self.assertIn("wordstat-topic-map/v1", topic_map)
        self.assertIn("candidate", topic_map.lower())
        self.assertIn("NFKC", topic_map)
        self.assertIn("yandex-search-clustering", topic_map)
        self.assertIn("yandex-seo-topical-architecture", topic_map)
        self.assertIn("PERIOD_MONTHLY", dynamics)
        self.assertIn("PERIOD_WEEKLY", dynamics)
        self.assertIn("fromDate", dynamics)
        self.assertIn("toDate", dynamics)
        for label in ["LOW_VOLUME_NOISE", "STABLE", "GROWING", "EXPLOSIVE", "SEASONAL"]:
            self.assertIn(label, trends)
        for text in [api, research]:
            self.assertIn("90", text)
            self.assertIn("100", text)
            self.assertIn("cost preview", text.lower())

    def test_current_reference_set_exists(self):
        expected = {
            "api-2026.md", "auth.md", "operators.md", "semantics.md", "topic-map.md", "dynamics.md",
            "regions.md", "trends.md", "quota-pricing.md", "safety.md", "sources.md",
        }
        actual = {p.name for p in (ROOT / "references").glob("*.md")}
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
