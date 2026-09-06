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


class Repository130ReleaseSurfaceTests(unittest.TestCase):
    def test_declared_release_is_repository_1_3_0_plus_seo_1_2_0(self):
        release = json.loads((ROOT / ".github/releases/release.json").read_text(encoding="utf-8"))
        self.assertEqual(release["schema_version"], 1)
        self.assertEqual(
            release["repository"],
            {
                "version": "1.3.0",
                "tag": "1.3.0",
                "title": "Repository 1.3.0",
                "notes_file": ".github/releases/1.3.0.md",
            },
        )
        self.assertEqual(
            release["plugins"],
            [
                {
                    "plugin": "yandex-seo",
                    "version": "1.2.0",
                    "tag": "yandex-seo-v1.2.0",
                    "title": "Yandex SEO 1.2.0",
                    "notes_file": ".github/releases/yandex-seo-v1.2.0.md",
                }
            ],
        )

    def test_release_notes_describe_weekly_report_and_immutable_artifacts(self):
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

    def test_seo_version_converges_across_manifests_and_marketplaces(self):
        for relative in (
            "plugins/yandex-seo/.codex-plugin/plugin.json",
            "plugins/yandex-seo/.claude-plugin/plugin.json",
        ):
            manifest = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], "1.2.0")

        agents = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual({row["name"]: row["version"] for row in agents["plugins"]}, EXPECTED_PLUGIN_VERSIONS)
        self.assertEqual({row["name"]: row["version"] for row in claude["plugins"]}, EXPECTED_PLUGIN_VERSIONS)

    def test_bilingual_current_release_surfaces_stage_repository_and_seo_versions(self):
        for relative in ("README.md", "README.en.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("release-1.3.0", text)
            self.assertIn("`1.3.0`", text)
            self.assertIn("yandex-seo", text)
            self.assertIn("1.2.0", text)
        for relative in ("CHANGELOG.md", "CHANGELOG.en.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("## [1.3.0]", text)
            self.assertIn("Weekly Organic Report", text)
        for relative in ("plugins/yandex-seo/README.md", "plugins/yandex-seo/README.en.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("1.2.0", text)
            self.assertIn("Weekly Organic Report", text)
        for relative in ("plugins/yandex-seo/CHANGELOG.md", "plugins/yandex-seo/CHANGELOG.en.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("## [1.2.0]", text)
            self.assertIn("Weekly Organic Report", text)

    def test_unrelated_plugin_versions_remain_unchanged(self):
        expected_dirs = {
            "yandex-direct": "2.1.0",
            "yandex-metrika": "2.1.0",
            "yandex-webmaster": "2.1.0",
            "yandex-wordstat": "1.1.2",
            "yandex-search": "1.0.2",
            "yandex-marketing": "1.1.0",
        }
        for plugin, version in expected_dirs.items():
            for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
                manifest = json.loads((ROOT / "plugins" / plugin / relative).read_text(encoding="utf-8"))
                self.assertEqual(manifest["version"], version)


if __name__ == "__main__":
    unittest.main()
