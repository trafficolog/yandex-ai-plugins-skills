from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


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

    def test_repository_1_3_0_notes_preserve_then_current_plugin_matrix(self):
        notes = (ROOT / ".github/releases/1.3.0.md").read_text(encoding="utf-8")
        for token in (
            "Direct `2.1.0`",
            "Metrika `2.1.0`",
            "Webmaster `2.1.0`",
            "Wordstat `1.1.2`",
            "Search `1.0.2`",
            "SEO `1.2.0`",
            "Marketing `1.1.0`",
        ):
            self.assertIn(token, notes)


if __name__ == "__main__":
    unittest.main()
