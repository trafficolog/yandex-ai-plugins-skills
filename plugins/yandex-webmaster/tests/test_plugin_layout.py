import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {
    "yandex-webmaster",
    "yandex-webmaster-audit",
    "yandex-webmaster-site-management",
    "yandex-webmaster-search-queries",
    "yandex-webmaster-indexing",
    "yandex-webmaster-recrawl",
    "yandex-webmaster-sitemaps",
    "yandex-webmaster-links",
    "yandex-webmaster-feeds",
    "yandex-webmaster-exports",
    "yandex-webmaster-api",
}


class TestPluginLayout(unittest.TestCase):
    def test_codex_manifest_contract(self):
        data = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "yandex-webmaster")
        self.assertEqual(data["version"], "2.1.0")
        self.assertEqual(data["skills"], "./skills/")

    def test_exact_skill_set_exists(self):
        actual = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual(actual, EXPECTED_SKILLS)

    def test_every_skill_is_discoverable(self):
        for skill in sorted(EXPECTED_SKILLS):
            text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), skill)
            self.assertIn("description: Use when", text, skill)

    def test_env_example_uses_webmaster_token(self):
        text = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("YANDEX_WEBMASTER_TOKEN=", text)

    def test_evals_have_scenarios(self):
        data = json.loads((ROOT / "evals/scenarios.json").read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 2)
        self.assertGreaterEqual(len(data["scenarios"]), 9)
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
        router = (ROOT / "skills/yandex-webmaster/SKILL.md").read_text(encoding="utf-8")
        recrawl = (ROOT / "skills/yandex-webmaster-recrawl/SKILL.md").read_text(encoding="utf-8")
        sitemaps = (ROOT / "skills/yandex-webmaster-sitemaps/SKILL.md").read_text(encoding="utf-8")
        exports = (ROOT / "skills/yandex-webmaster-exports/SKILL.md").read_text(encoding="utf-8")
        sites = (ROOT / "skills/yandex-webmaster-site-management/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("yandex-webmaster-recrawl", router)
        self.assertIn("read → analyze → preview → explicit approval → write → verify", router)
        self.assertIn("quota", recrawl.lower())
        self.assertIn("URL_ALREADY_ADDED", recrawl)
        self.assertIn("v4.1", sitemaps)
        self.assertIn("10", sitemaps)
        self.assertIn("pro/limits", exports)
        self.assertIn("download", exports.lower())
        self.assertIn("autonomously poll", exports.lower())
        self.assertIn("24 hours", exports.lower())
        self.assertIn("exact target", sites.lower())

    def test_current_reference_set_exists(self):
        expected = {
            "api-2026.md", "audit-framework.md", "endpoint-map.md", "indexing.md",
            "queries.md", "recrawl.md", "sitemaps.md", "feeds.md", "exports.md",
            "safety.md", "sources.md",
        }
        actual = {p.name for p in (ROOT / "references").glob("*.md")}
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
