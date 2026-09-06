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


class Repository140ReleaseSurfaceTests(unittest.TestCase):
    def test_declared_release_is_repository_only_1_4_0(self):
        release = json.loads((ROOT / ".github/releases/release.json").read_text(encoding="utf-8"))
        self.assertEqual(release["schema_version"], 1)
        self.assertEqual(
            release["repository"],
            {
                "version": "1.4.0",
                "tag": "1.4.0",
                "title": "Repository 1.4.0",
                "notes_file": ".github/releases/1.4.0.md",
            },
        )
        self.assertEqual(release["plugins"], [])

    def test_release_notes_describe_p3_benchmark_infrastructure_truthfully(self):
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

    def test_bilingual_current_release_surfaces_stage_repository_1_4_0(self):
        for relative in ("README.md", "README.en.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("release-1.4.0", text)
            self.assertIn("`1.4.0`", text)
            self.assertIn("P3", text)
            self.assertIn("INFRASTRUCTURE_READY", text)
            self.assertIn("COMPARATIVE_COMPLETE", text)
        for relative in ("CHANGELOG.md", "CHANGELOG.en.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("## [1.4.0] — 2026-09-06", text)
            self.assertIn("P3 Benchmark Infrastructure", text)
            self.assertIn("INFRASTRUCTURE_READY", text)

    def test_all_plugin_versions_remain_unchanged(self):
        agents = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual({row["name"]: row["version"] for row in agents["plugins"]}, EXPECTED_PLUGIN_VERSIONS)
        self.assertEqual({row["name"]: row["version"] for row in claude["plugins"]}, EXPECTED_PLUGIN_VERSIONS)

        expected_dirs = {
            "yandex-direct": "2.1.0",
            "yandex-metrika": "2.1.0",
            "yandex-webmaster": "2.1.0",
            "yandex-wordstat": "1.1.2",
            "yandex-search": "1.0.2",
            "yandex-seo": "1.2.0",
            "yandex-marketing": "1.1.0",
        }
        for plugin, version in expected_dirs.items():
            for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
                manifest = json.loads((ROOT / "plugins" / plugin / relative).read_text(encoding="utf-8"))
                self.assertEqual(manifest["version"], version)


if __name__ == "__main__":
    unittest.main()
