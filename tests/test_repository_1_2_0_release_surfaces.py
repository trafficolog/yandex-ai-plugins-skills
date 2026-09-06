import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Repository120ReleaseSurfaceTests(unittest.TestCase):
    def test_declared_release_is_repository_only_1_2_0(self):
        release = json.loads((ROOT / ".github/releases/release.json").read_text(encoding="utf-8"))
        self.assertEqual(release["schema_version"], 1)
        self.assertEqual(
            release["repository"],
            {
                "version": "1.2.0",
                "tag": "1.2.0",
                "title": "Repository 1.2.0",
                "notes_file": ".github/releases/1.2.0.md",
            },
        )
        self.assertEqual(release["plugins"], [])

    def test_repository_readmes_and_changelogs_stage_1_2_0(self):
        for path in (ROOT / "README.md", ROOT / "README.en.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("release-1.2.0", text)
            self.assertIn("`1.2.0`", text)
        for path in (ROOT / "CHANGELOG.md", ROOT / "CHANGELOG.en.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("## [1.2.0]", text)
            self.assertIn("Project Memory", text)

    def test_repository_release_notes_describe_p1_without_plugin_release(self):
        notes = ROOT / ".github/releases/1.2.0.md"
        self.assertTrue(notes.is_file())
        text = notes.read_text(encoding="utf-8")
        for token in (
            "Project Memory",
            "yandex-ai-project/v1",
            "yandex-ai-decision/v1",
            "yandex-ai-baseline/v1",
            "yandex-ai-hypothesis/v1",
            "record-execution",
            "add-baseline",
            "plugins: []",
        ):
            self.assertIn(token, text)

    def test_plugin_versions_remain_unchanged(self):
        expected = {
            "yandex-direct": "2.1.0",
            "yandex-metrika": "2.1.0",
            "yandex-webmaster": "2.1.0",
            "yandex-wordstat": "1.1.2",
            "yandex-search": "1.0.2",
            "yandex-seo": "1.1.2",
            "yandex-marketing": "1.1.0",
        }
        agents = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual({row["name"]: row["version"] for row in agents["plugins"]}, expected)
        self.assertEqual({row["name"]: row["version"] for row in claude["plugins"]}, expected)
        for plugin, version in expected.items():
            for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
                manifest = json.loads((ROOT / "plugins" / plugin / relative).read_text(encoding="utf-8"))
                self.assertEqual(manifest["version"], version)


if __name__ == "__main__":
    unittest.main()
