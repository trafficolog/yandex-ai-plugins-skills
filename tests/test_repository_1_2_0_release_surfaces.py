from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Repository120HistoricalReleaseTests(unittest.TestCase):
    def test_bilingual_changelogs_preserve_repository_1_2_0(self):
        for path in (ROOT / "CHANGELOG.md", ROOT / "CHANGELOG.en.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("## [1.2.0]", text)
            self.assertIn("Project Memory", text)

    def test_repository_1_2_0_release_notes_remain_historical(self):
        notes = ROOT / ".github/releases/1.2.0.md"
        self.assertTrue(notes.is_file())
        text = notes.read_text(encoding="utf-8")
        for token in (
            "Repository 1.2.0",
            "Project Memory",
            "yandex-ai-project/v1",
            "yandex-ai-decision/v1",
            "yandex-ai-baseline/v1",
            "yandex-ai-hypothesis/v1",
            "record-execution",
            "add-baseline",
            "plugins: []",
            "SEO `1.1.2`",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
