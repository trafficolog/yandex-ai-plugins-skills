from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIRS = [
    "yandex-direct",
    "yandex-metrika",
    "yandex-webmaster",
    "yandex-wordstat",
    "yandex-search",
    "yandex-seo",
    "yandex-marketing",
]
KEY_DOCS = [
    "SERVICE_MATRIX",
    "ROADMAP",
    "PLUGIN_STANDARD",
    "REVIEW_FIRST_RELEASE",
    "GETTING_STARTED",
    "ARCHITECTURE",
    "GLOSSARY",
    "RELEASE_POLICY",
]


def release_markers(text: str) -> list[str]:
    return re.findall(r"^##\s+\[([^\]]+)\]", text, flags=re.MULTILINE)


class BilingualDocumentationTests(unittest.TestCase):
    def test_root_readme_and_changelog_have_ru_en_pairs(self):
        for path in ["README.md", "README.en.md", "CHANGELOG.md", "CHANGELOG.en.md"]:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_all_plugins_have_ru_en_readme_and_changelog_pairs(self):
        for plugin in PLUGIN_DIRS:
            base = ROOT / "plugins" / plugin
            for path in ["README.md", "README.en.md", "CHANGELOG.md", "CHANGELOG.en.md"]:
                self.assertTrue((base / path).is_file(), f"{plugin}/{path}")

    def test_key_repository_docs_have_english_mirrors(self):
        for name in KEY_DOCS:
            self.assertTrue((ROOT / "docs" / f"{name}.md").is_file(), name)
            self.assertTrue((ROOT / "docs" / f"{name}.en.md").is_file(), f"{name}.en")

    def test_root_language_switches_are_reciprocal(self):
        ru = (ROOT / "README.md").read_text(encoding="utf-8")
        en = (ROOT / "README.en.md").read_text(encoding="utf-8")
        self.assertIn("README.en.md", ru)
        self.assertIn("README.md", en)
        ru_change = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        en_change = (ROOT / "CHANGELOG.en.md").read_text(encoding="utf-8")
        self.assertIn("CHANGELOG.en.md", ru_change)
        self.assertIn("CHANGELOG.md", en_change)

    def test_plugin_language_switches_are_reciprocal(self):
        for plugin in PLUGIN_DIRS:
            base = ROOT / "plugins" / plugin
            ru = (base / "README.md").read_text(encoding="utf-8")
            en = (base / "README.en.md").read_text(encoding="utf-8")
            self.assertIn("README.en.md", ru, plugin)
            self.assertIn("README.md", en, plugin)
            ru_change = (base / "CHANGELOG.md").read_text(encoding="utf-8")
            en_change = (base / "CHANGELOG.en.md").read_text(encoding="utf-8")
            self.assertIn("CHANGELOG.en.md", ru_change, plugin)
            self.assertIn("CHANGELOG.md", en_change, plugin)

    def test_changelog_release_markers_match_between_languages(self):
        pairs = [(ROOT / "CHANGELOG.md", ROOT / "CHANGELOG.en.md")]
        pairs.extend(
            (
                ROOT / "plugins" / plugin / "CHANGELOG.md",
                ROOT / "plugins" / plugin / "CHANGELOG.en.md",
            )
            for plugin in PLUGIN_DIRS
        )
        for ru_path, en_path in pairs:
            with self.subTest(path=str(ru_path.relative_to(ROOT))):
                self.assertEqual(
                    release_markers(ru_path.read_text(encoding="utf-8")),
                    release_markers(en_path.read_text(encoding="utf-8")),
                )

    def test_root_readmes_use_language_specific_hero_assets(self):
        ru = (ROOT / "README.md").read_text(encoding="utf-8")
        en = (ROOT / "README.en.md").read_text(encoding="utf-8")
        self.assertIn("docs/assets/readme/root-hero-ru.svg", ru)
        self.assertIn("docs/assets/readme/root-hero-en.svg", en)
        self.assertTrue((ROOT / "docs/assets/readme/root-hero-ru.svg").is_file())
        self.assertTrue((ROOT / "docs/assets/readme/root-hero-en.svg").is_file())

    def test_primary_root_docs_are_russian(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("Русский", readme)
        self.assertIn("репозитор", readme.lower())
        self.assertIn("Измен", changelog)

    def test_seo_readmes_explain_orchestration_with_mermaid(self):
        for filename in ["README.md", "README.en.md"]:
            content = (ROOT / "plugins/yandex-seo" / filename).read_text(encoding="utf-8")
            self.assertIn("```mermaid", content)
            for token in ["Wordstat", "Search", "Webmaster", "Metrika", "SEO Evidence Bundle"]:
                self.assertIn(token, content)
            self.assertIn("delegated", content.lower())

    def test_marketing_readmes_explain_reconciliation_orchestration_with_mermaid(self):
        for filename in ["README.md", "README.en.md"]:
            content = (ROOT / "plugins/yandex-marketing" / filename).read_text(encoding="utf-8")
            self.assertIn("```mermaid", content)
            for token in ["Direct", "Metrika", "Wordstat", "Search", "Marketing Evidence Bundle"]:
                self.assertIn(token, content)
            for role in ["canonical", "reconciliation_only", "enrichment"]:
                self.assertIn(role, content)

    def test_current_plugin_semver_matrix(self):
        expected = {
            "yandex-direct": "2.1.0",
            "yandex-metrika": "2.1.0",
            "yandex-webmaster": "2.1.0",
            "yandex-wordstat": "1.1.2",
            "yandex-search": "1.0.2",
            "yandex-seo": "1.1.2",
            "yandex-marketing": "1.1.0",
        }
        import json
        for plugin, version in expected.items():
            manifest = json.loads(
                (ROOT / "plugins" / plugin / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["version"], version, plugin)


if __name__ == "__main__":
    unittest.main()
