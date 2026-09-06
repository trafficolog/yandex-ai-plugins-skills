from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryOnlyScopeTests(unittest.TestCase):
    def test_repository_1_0_7_release_remains_historical(self):
        notes = (ROOT / ".github/releases/1.0.7.md").read_text(encoding="utf-8")
        self.assertIn("Repository 1.0.7", notes)
        self.assertIn("repository-only", notes.lower())
        self.assertIn("no plugin tags", notes.lower())
        self.assertIn("Yandex Direct 2.0.1", notes)
        self.assertIn("Yandex Metrika 2.0.0", notes)
        self.assertIn("Yandex Webmaster 2.0.0", notes)

    def test_bilingual_changelogs_preserve_repository_1_0_7(self):
        marker = "## [1.0.7] — 2026-09-05"
        for filename in ("CHANGELOG.md", "CHANGELOG.en.md"):
            self.assertIn(marker, (ROOT / filename).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
