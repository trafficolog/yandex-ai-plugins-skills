import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_PLUGIN_VERSIONS = {
    "yandex-direct-suite": "2.2.0",
    "yandex-metrika": "2.2.0",
    "yandex-webmaster": "2.2.0",
    "yandex-wordstat": "1.2.0",
    "yandex-search": "1.1.0",
    "yandex-seo": "1.2.0",
    "yandex-marketing": "1.1.0",
}

RELEASED_PLUGINS = {
    "yandex-direct": "2.2.0",
    "yandex-metrika": "2.2.0",
    "yandex-search": "1.1.0",
    "yandex-webmaster": "2.2.0",
    "yandex-wordstat": "1.2.0",
}


class Repository150ReleaseSurfaceTests(unittest.TestCase):
    def test_declared_release_is_practitioner_workflow_1_5_0_set(self):
        release = json.loads((ROOT / ".github/releases/release.json").read_text(encoding="utf-8"))
        self.assertEqual(release["schema_version"], 1)
        self.assertEqual(
            release["repository"],
            {
                "version": "1.5.0",
                "tag": "1.5.0",
                "title": "Repository 1.5.0",
                "notes_file": ".github/releases/1.5.0.md",
            },
        )
        self.assertEqual(
            {row["plugin"]: row["version"] for row in release["plugins"]},
            RELEASED_PLUGINS,
        )

    def test_release_notes_name_practitioner_provenance_and_scope(self):
        notes = (ROOT / ".github/releases/1.5.0.md").read_text(encoding="utf-8")
        for token in (
            "Practitioner-informed",
            "f6a75133b3ad07e43991433c1d0a77f69c749f7b",
            "Yandex Direct",
            "Yandex Metrika",
            "Yandex Search",
            "Yandex Webmaster",
            "Yandex Wordstat",
            "smart snippets",
            "exact-preview",
        ):
            self.assertIn(token, notes)
        self.assertIn("does not guarantee", notes.lower())

    def test_marketplaces_and_manifests_match_1_5_0_release_matrix(self):
        agents = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        for marketplace in (agents, claude):
            self.assertEqual({row["name"]: row["version"] for row in marketplace["plugins"]}, EXPECTED_PLUGIN_VERSIONS)

        expected_dirs = {
            "yandex-direct": "2.2.0",
            "yandex-metrika": "2.2.0",
            "yandex-webmaster": "2.2.0",
            "yandex-wordstat": "1.2.0",
            "yandex-search": "1.1.0",
            "yandex-seo": "1.2.0",
            "yandex-marketing": "1.1.0",
        }
        for plugin, version in expected_dirs.items():
            for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
                manifest = json.loads((ROOT / "plugins" / plugin / relative).read_text(encoding="utf-8"))
                self.assertEqual(manifest["version"], version, f"{plugin}/{relative}")

    def test_bilingual_changelogs_stage_new_release(self):
        for relative in ("CHANGELOG.md", "CHANGELOG.en.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("## [1.5.0] — 2026-09-14", text)
        for plugin, version in RELEASED_PLUGINS.items():
            for relative in ("CHANGELOG.md", "CHANGELOG.en.md"):
                text = (ROOT / "plugins" / plugin / relative).read_text(encoding="utf-8")
                self.assertIn(f"## [{version}] — 2026-09-14", text, f"{plugin}/{relative}")

    def test_root_readmes_stage_repository_1_5_0(self):
        for relative in ("README.md", "README.en.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("release-1.5.0", text)
            self.assertIn("`1.5.0`", text)


if __name__ == "__main__":
    unittest.main()
