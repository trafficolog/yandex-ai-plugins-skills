from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Repository108ReleaseSurfaceTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_bilingual_changelogs_preserve_repository_1_0_8(self):
        marker = "## [1.0.8] — 2026-09-05"
        for filename in ("CHANGELOG.md", "CHANGELOG.en.md"):
            with self.subTest(filename=filename):
                self.assertIn(marker, self.read(filename))

    def test_repository_1_0_8_release_notes_remain_historical(self):
        notes = self.read(".github/releases/1.0.8.md")
        self.assertIn("Repository 1.0.8", notes)
        self.assertIn("repository-only", notes.lower())
        self.assertIn("no plugin tags", notes.lower())
        self.assertIn("Direct 2.0.1", notes)
        self.assertIn("Metrika 2.0.0", notes)
        self.assertIn("Webmaster 2.0.0", notes)


if __name__ == "__main__":
    unittest.main()
