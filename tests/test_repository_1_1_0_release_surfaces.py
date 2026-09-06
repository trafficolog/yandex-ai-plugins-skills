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
    "yandex-direct": ("2.1.0", "yandex-direct-v2.1.0", ".github/releases/yandex-direct-2.1.0.md"),
    "yandex-metrika": ("2.1.0", "yandex-metrika-v2.1.0", ".github/releases/yandex-metrika-2.1.0.md"),
    "yandex-webmaster": ("2.1.0", "yandex-webmaster-v2.1.0", ".github/releases/yandex-webmaster-2.1.0.md"),
}


class Repository110ReleaseSurfaceTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_root_readmes_stage_repository_1_1_0(self):
        for filename in ("README.md", "README.en.md"):
            text = self.read(filename)
            with self.subTest(filename=filename):
                self.assertIn("release-1.1.0", text)
                self.assertIn("1.1.0", text)
                for plugin, version in EXPECTED_PLUGINS.items():
                    rows = [line for line in text.splitlines() if f"plugins/{plugin}/" in line]
                    self.assertTrue(rows, plugin)
                    self.assertTrue(any(f"| {version} |" in line for line in rows), (plugin, rows))

    def test_bilingual_changelogs_stage_repository_1_1_0(self):
        marker = "## [1.1.0] — 2026-09-05"
        for filename in ("CHANGELOG.md", "CHANGELOG.en.md"):
            with self.subTest(filename=filename):
                self.assertIn(marker, self.read(filename))

    def test_declared_release_set_is_exact(self):
        data = json.loads(self.read(".github/releases/release.json"))
        self.assertEqual(
            data["repository"],
            {
                "version": "1.1.0",
                "tag": "1.1.0",
                "title": "Repository 1.1.0",
                "notes_file": ".github/releases/1.1.0.md",
            },
        )
        self.assertTrue((ROOT / ".github/releases/1.1.0.md").is_file())
        actual = {
            item["plugin"]: (item["version"], item["tag"], item["notes_file"])
            for item in data["plugins"]
        }
        self.assertEqual(actual, RELEASED_PLUGINS)
        for _, (_, _, notes_file) in RELEASED_PLUGINS.items():
            self.assertTrue((ROOT / notes_file).is_file(), notes_file)

    def test_plugin_manifests_and_both_marketplaces_match_target_versions(self):
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

    def test_plugin_changelogs_stage_only_released_plugin_versions(self):
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
