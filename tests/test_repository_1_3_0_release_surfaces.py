import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PLUGIN_VERSIONS = {
    "yandex-direct-suite": "2.1.0",
    "yandex-metrika": "2.1.0",
    "yandex-webmaster": "2.1.0",
    "yandex-wordstat": "1.1.2",
    "yandex-search": "1.0.2",
    "yandex-seo": "1.2.0",
    "yandex-marketing": "1.1.0",
}


class Repository130HistoricalReleaseTests(unittest.TestCase):
    def test_repository_1_3_0_release_notes_remain_historical(self):
        repository_notes = (ROOT / ".github/releases/1.3.0.md").read_text(encoding="utf-8")
        seo_notes = (ROOT / ".github/releases/yandex-seo-v1.2.0.md").read_text(encoding="utf-8")
        for text in (repository_notes, seo_notes):
            for token in (
                "Weekly Organic Report",
                "seo-weekly-organic-report/v1",
                "yandex-ai-artifact-manifest/v1",
                "self-contained",
                "PREVIEW-ONLY",
            ):
                self.assertIn(token, text)
        self.assertIn("yandex-seo-v1.2.0", repository_notes)

    def test_bilingual_changelogs_preserve_repository_1_3_0(self):
        for relative in ("CHANGELOG.md", "CHANGELOG.en.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("## [1.3.0] — 2026-09-06", text)
            self.assertIn("Weekly Organic Report", text)

    def test_seo_1_2_0_release_surfaces_remain_historical(self):
        for relative in ("plugins/yandex-seo/README.md", "plugins/yandex-seo/README.en.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("1.2.0", text)
            self.assertIn("Weekly Organic Report", text)
        for relative in ("plugins/yandex-seo/CHANGELOG.md", "plugins/yandex-seo/CHANGELOG.en.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("## [1.2.0]", text)
            self.assertIn("Weekly Organic Report", text)

    def test_plugin_versions_after_1_3_0_remain_the_same_until_explicit_plugin_release(self):
        agents = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual({row["name"]: row["version"] for row in agents["plugins"]}, EXPECTED_PLUGIN_VERSIONS)
        self.assertEqual({row["name"]: row["version"] for row in claude["plugins"]}, EXPECTED_PLUGIN_VERSIONS)


if __name__ == "__main__":
    unittest.main()
