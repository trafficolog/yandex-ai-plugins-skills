from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Repository140ReleaseSurfaceTests(unittest.TestCase):
    def test_repository_1_4_0_release_notes_remain_historical(self):
        notes = (ROOT / ".github/releases/1.4.0.md").read_text(encoding="utf-8")
        for token in (
            "P3 Benchmark Infrastructure",
            "INFRASTRUCTURE_READY",
            "COMPARATIVE_COMPLETE",
            "model eval runner",
            "independent judge",
            "backend-equivalence",
            "Project Memory",
            "immutable",
        ):
            self.assertIn(token, notes)
        self.assertIn("not", notes.lower())
        self.assertIn("live multi-model", notes.lower())

    def test_bilingual_changelogs_preserve_repository_1_4_0(self):
        for relative in ("CHANGELOG.md", "CHANGELOG.en.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("## [1.4.0] — 2026-09-06", text)
            self.assertIn("P3 Benchmark Infrastructure", text)
            self.assertIn("INFRASTRUCTURE_READY", text)

    def test_repository_1_4_0_notes_preserve_then_current_plugin_matrix(self):
        notes = (ROOT / ".github/releases/1.4.0.md").read_text(encoding="utf-8")
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

    def test_current_readmes_still_explain_p3_evidence_boundary(self):
        for relative in ("README.md", "README.en.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("P3", text)
            self.assertIn("INFRASTRUCTURE_READY", text)
            self.assertIn("COMPARATIVE_COMPLETE", text)


if __name__ == "__main__":
    unittest.main()
