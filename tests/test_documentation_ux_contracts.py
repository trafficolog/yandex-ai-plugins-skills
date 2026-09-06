from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PLUGINS = {
    "yandex-direct": ("yandex-direct-suite", "2.1.0"),
    "yandex-metrika": ("yandex-metrika", "2.1.0"),
    "yandex-webmaster": ("yandex-webmaster", "2.1.0"),
    "yandex-wordstat": ("yandex-wordstat", "1.1.2"),
    "yandex-search": ("yandex-search", "1.0.2"),
    "yandex-seo": ("yandex-seo", "1.1.2"),
    "yandex-marketing": ("yandex-marketing", "1.1.0"),
}
NEW_DOC_PAIRS = (
    "GETTING_STARTED",
    "ARCHITECTURE",
    "GLOSSARY",
    "RELEASE_POLICY",
)


class DocumentationUXGovernanceContractTests(unittest.TestCase):
    def _read(self, relative: str) -> str:
        path = ROOT / relative
        self.assertTrue(path.is_file(), relative)
        return path.read_text(encoding="utf-8")

    def test_new_bilingual_user_and_governance_docs_exist(self):
        for name in NEW_DOC_PAIRS:
            with self.subTest(name=name):
                self.assertTrue((ROOT / "docs" / f"{name}.md").is_file())
                self.assertTrue((ROOT / "docs" / f"{name}.en.md").is_file())
        self.assertTrue((ROOT / "CONTRIBUTING.md").is_file())

    def test_root_readmes_are_navigation_hubs_for_human_docs(self):
        required_links = (
            "docs/GETTING_STARTED",
            "docs/ARCHITECTURE",
            "docs/RELEASE_POLICY",
            "docs/SERVICE_MATRIX",
            "plugins/yandex-direct/",
            "plugins/yandex-seo/",
            "plugins/yandex-marketing/",
        )
        for filename in ("README.md", "README.en.md"):
            text = self._read(filename)
            with self.subTest(filename=filename):
                for token in required_links:
                    self.assertIn(token, text)

    def test_root_readmes_stage_current_repository_1_2_0(self):
        for filename in ("README.md", "README.en.md"):
            text = self._read(filename)
            with self.subTest(filename=filename):
                self.assertIn("release-1.2.0", text)
                self.assertIn("`1.2.0`", text)
                for plugin, (_, version) in EXPECTED_PLUGINS.items():
                    row = [line for line in text.splitlines() if f"plugins/{plugin}/" in line]
                    self.assertTrue(row, plugin)
                    self.assertTrue(any(f"| {version} |" in line for line in row), (plugin, row))

    def test_getting_started_has_minimum_safe_onboarding_contract(self):
        for filename in ("docs/GETTING_STARTED.md", "docs/GETTING_STARTED.en.md"):
            text = self._read(filename)
            with self.subTest(filename=filename):
                for token in (
                    "Python 3.10+",
                    ".agents/plugins/marketplace.json",
                    ".claude-plugin/marketplace.json",
                    "plugins/yandex-direct/references/",
                    "plugins/yandex-wordstat/references/auth.md",
                    "YANDEX_DIRECT_TOKEN",
                    "campaigns get",
                    "preview_id",
                    "--execute --approve",
                ):
                    self.assertIn(token, text)

    def test_release_policy_defines_one_repository_semver_and_human_gate(self):
        required = (
            "repository SemVer",
            "plugin SemVer",
            "AI audit",
            "CI",
            "independent review",
            "human",
            "OPUS",
            "PHASE",
            "DOCS",
            "FABLE",
        )
        for filename in ("docs/RELEASE_POLICY.md", "docs/RELEASE_POLICY.en.md"):
            text = self._read(filename)
            with self.subTest(filename=filename):
                for token in required:
                    self.assertIn(token, text)

    def test_wordstat_readmes_use_unambiguous_search_api_wording(self):
        ru = self._read("plugins/yandex-wordstat/README.md")
        en = self._read("plugins/yandex-wordstat/README.en.md")
        self.assertIn("Wordstat API в составе Yandex Search API v2", ru)
        self.assertIn("Wordstat API within Yandex Search API v2", en)

    def test_executable_write_safety_v2_is_documented_truthfully(self):
        required_tokens = (
            "yandex-ai-approval/v2",
            "--ack-bulk",
            "yandex-ai-execution/v1",
            "RESPONSE_ONLY",
            "NOT_AVAILABLE",
        )
        for filename in ("docs/PLUGIN_STANDARD.md", "docs/PLUGIN_STANDARD.en.md"):
            text = self._read(filename)
            with self.subTest(filename=filename):
                for token in required_tokens:
                    self.assertIn(token, text)

        ru = self._read("docs/PLUGIN_STANDARD.md").lower()
        en = self._read("docs/PLUGIN_STANDARD.en.md").lower()
        self.assertIn("standalone cli", ru)
        self.assertIn("standalone cli", en)
        self.assertIn("не может доказать", ru)
        self.assertIn("cannot prove", en)
        self.assertIn("позднем разговорном ходе", ru)
        self.assertIn("later conversational turn", en)

    def test_current_plugin_and_marketplace_versions_match_release_matrix(self):
        expected_by_marketplace_name = {
            marketplace_name: version
            for _, (marketplace_name, version) in EXPECTED_PLUGINS.items()
        }
        for plugin, (_, version) in EXPECTED_PLUGINS.items():
            base = ROOT / "plugins" / plugin
            for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
                data = json.loads((base / relative).read_text(encoding="utf-8"))
                self.assertEqual(data["version"], version, f"{plugin}/{relative}")

        agents = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        for marketplace in (agents, claude):
            actual = {item["name"]: item["version"] for item in marketplace["plugins"]}
            for name, version in expected_by_marketplace_name.items():
                self.assertEqual(actual[name], version, name)


if __name__ == "__main__":
    unittest.main()
