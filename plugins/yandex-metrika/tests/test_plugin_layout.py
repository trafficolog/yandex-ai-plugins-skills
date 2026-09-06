import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {
    "yandex-metrika",
    "yandex-metrika-audit",
    "yandex-metrika-reporting",
    "yandex-metrika-conversions",
    "yandex-metrika-ecommerce",
    "yandex-metrika-attribution",
    "yandex-metrika-goals",
    "yandex-metrika-logs",
    "yandex-metrika-imports",
    "yandex-metrika-api",
}


class TestPluginLayout(unittest.TestCase):
    def test_codex_manifest_contract(self):
        data = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "yandex-metrika")
        self.assertEqual(data["version"], "2.1.0")
        self.assertEqual(data["skills"], "./skills/")

    def test_exact_skill_set_exists(self):
        actual = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual(actual, EXPECTED_SKILLS)

    def test_env_example_uses_metrika_token(self):
        text = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("YANDEX_METRIKA_TOKEN=", text)

    def test_evals_have_scenarios(self):
        data = json.loads((ROOT / "evals/scenarios.json").read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 2)
        self.assertGreaterEqual(len(data["scenarios"]), 10)
        for scenario in data["scenarios"]:
            expect = scenario["expect"]
            self.assertIn(expect["outcome"], {"comply", "comply_with_limitations", "refuse"})
            self.assertIn("must_mention_tokens", expect)
            self.assertIn("must_convey", expect)
            self.assertIn("must_not_claim", expect)

    def test_package_docs_exist(self):
        for path in ["README.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md"]:
            self.assertTrue((ROOT / path).is_file(), path)


if __name__ == "__main__":
    unittest.main()
