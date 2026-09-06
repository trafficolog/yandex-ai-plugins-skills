from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PLUGINS = {
    "yandex-direct": "2.1.0",
    "yandex-metrika": "2.1.0",
    "yandex-webmaster": "2.1.0",
    "yandex-wordstat": "1.1.2",
    "yandex-search": "1.0.2",
    "yandex-seo": "1.1.2",
    "yandex-marketing": "1.1.0",
}
RELEASED_PLUGINS = {
    "yandex-direct": ("2.1.0", ".github/releases/yandex-direct-2.1.0.md", "Yandex Direct 2.1.0"),
    "yandex-metrika": ("2.1.0", ".github/releases/yandex-metrika-2.1.0.md", "Yandex Metrika 2.1.0"),
    "yandex-webmaster": ("2.1.0", ".github/releases/yandex-webmaster-2.1.0.md", "Yandex Webmaster 2.1.0"),
}


class Repository110ReleaseSurfaceTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_repository_1_1_0_remains_historical(self):
        marker = "## [1.1.0] — 2026-09-05"
        for filename in ("CHANGELOG.md", "CHANGELOG.en.md"):
            with self.subTest(filename=filename):
                self.assertIn(marker, self.read(filename))
        self.assertTrue((ROOT / ".github/releases/1.1.0.md").is_file())

    def test_bilingual_changelogs_preserve_repository_1_1_0(self):
        marker = "## [1.1.0] — 2026-09-05"
        for filename in ("CHANGELOG.md", "CHANGELOG.en.md"):
            with self.subTest(filename=filename):
                self.assertIn(marker, self.read(filename))

    def test_historical_release_notes_preserve_plugin_release_set(self):
        repository_notes = self.read(".github/releases/1.1.0.md")
        self.assertIn("1.1.0", repository_notes)
        for plugin, (version, notes_file, display_name) in RELEASED_PLUGINS.items():
            with self.subTest(plugin=plugin):
                self.assertTrue((ROOT / notes_file).is_file(), notes_file)
                self.assertIn(version, self.read(notes_file))
                self.assertIn(display_name, repository_notes)

    def test_plugin_manifests_and_both_marketplaces_preserve_1_1_0_plugin_versions(self):
        for plugin, expected in EXPECTED_PLUGINS.items():
            for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
                data = json.loads(self.read(f"plugins/{plugin}/{relative}"))
                self.assertEqual(data["version"], expected, f"{plugin}/{relative}")

        expected_by_marketplace_name = {
            "yandex-direct-suite": "2.1.0",
            "yandex-metrika": "2.1.0",
            "yandex-webmaster": "2.1.0",
            "yandex-wordstat": "1.1.2",
            "yandex-search": "1.0.2",
            "yandex-seo": "1.1.2",
            "yandex-marketing": "1.1.0",
        }
        for relative in (".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
            data = json.loads(self.read(relative))
            actual = {item["name"]: item["version"] for item in data["plugins"]}
            self.assertEqual(actual, expected_by_marketplace_name, relative)

    def test_plugin_changelogs_preserve_only_released_plugin_versions(self):
        for plugin in RELEASED_PLUGINS:
            for filename in ("CHANGELOG.md", "CHANGELOG.en.md"):
                self.assertIn(
                    "## [2.1.0] — 2026-09-05",
                    self.read(f"plugins/{plugin}/{filename}"),
                )
        for plugin in ("yandex-wordstat", "yandex-search", "yandex-seo", "yandex-marketing"):
            for filename in ("CHANGELOG.md", "CHANGELOG.en.md"):
                self.assertNotIn(
                    "## [2.1.0] — 2026-09-05",
                    self.read(f"plugins/{plugin}/{filename}"),
                )


if __name__ == "__main__":
    unittest.main()
