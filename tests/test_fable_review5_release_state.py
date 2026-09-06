import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "yandex-direct": ("yandex-direct-suite", "2.1.0"),
    "yandex-metrika": ("yandex-metrika", "2.1.0"),
    "yandex-webmaster": ("yandex-webmaster", "2.1.0"),
}


class FableReview5ReleaseStateTests(unittest.TestCase):
    def test_target_plugin_manifests_match_current_release_matrix(self):
        for plugin, (_, version) in EXPECTED.items():
            with self.subTest(plugin=plugin):
                base = ROOT / "plugins" / plugin
                for relative in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
                    data = json.loads((base / relative).read_text(encoding="utf-8"))
                    self.assertEqual(data["version"], version)

    def test_marketplaces_match_current_release_matrix(self):
        agents = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        agent_versions = {item["name"]: item["version"] for item in agents["plugins"]}
        claude_versions = {item["name"]: item["version"] for item in claude["plugins"]}
        for _, (marketplace_name, version) in EXPECTED.items():
            self.assertEqual(agent_versions[marketplace_name], version)
            self.assertEqual(claude_versions[marketplace_name], version)

    def test_root_readmes_preserve_published_immutable_fable_generation_history(self):
        stale_fragments = (
            "Tags/releases для `2.0.0` создаются отдельно",
            "tags/releases for `2.0.0` are created separately",
            "staged breaking safety generation",
            "staged major generation",
        )
        for filename in ("README.md", "README.en.md"):
            text = (ROOT / filename).read_text(encoding="utf-8")
            self.assertIn("immutable", text.lower())
            for fragment in stale_fragments:
                self.assertNotIn(fragment, text)

    def test_service_matrix_matches_current_release_versions(self):
        labels = {
            "yandex-direct": "Yandex Direct",
            "yandex-metrika": "Yandex Metrika",
            "yandex-webmaster": "Yandex Webmaster",
        }
        for filename in ("SERVICE_MATRIX.md", "SERVICE_MATRIX.en.md"):
            text = (ROOT / "docs" / filename).read_text(encoding="utf-8")
            for plugin, (_, version) in EXPECTED.items():
                service = labels[plugin]
                matching = [line for line in text.splitlines() if line.startswith(f"| {service} |")]
                self.assertEqual(len(matching), 1, service)
                self.assertIn(f"| {version} |", matching[0])

    def test_verification_examples_compile_complete_script_tree(self):
        for filename in ("README.md", "README.en.md"):
            text = (ROOT / filename).read_text(encoding="utf-8")
            self.assertIn("python -m compileall -q scripts", text)
            self.assertNotIn("python -m py_compile scripts/marketing_prioritize.py", text)


if __name__ == "__main__":
    unittest.main()
