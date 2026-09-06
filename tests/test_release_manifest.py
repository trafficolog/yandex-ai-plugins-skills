import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/release_manifest.py"
MANIFEST = ROOT / ".github/releases/release.json"


class ReleaseManifestTests(unittest.TestCase):
    def load_module(self):
        self.assertTrue(SCRIPT.exists(), "scripts/release_manifest.py must exist")
        spec = importlib.util.spec_from_file_location("release_manifest_under_test", SCRIPT)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(module)
        return module

    def make_fixture(
        self,
        *,
        repository_version="1.0.6",
        repository_tag="1.0.6",
        repository_title=None,
        notes_file=".github/releases/1.0.6.md",
        create_notes=True,
        surface_version=None,
        plugin=None,
        plugin_version=None,
        plugin_tag=None,
        plugin_title=None,
        actual_plugin_version=None,
        duplicate_plugin=False,
    ):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        releases = root / ".github/releases"
        releases.mkdir(parents=True)

        if create_notes and notes_file.startswith(".github/releases/"):
            notes_path = root / notes_file
            notes_path.parent.mkdir(parents=True, exist_ok=True)
            notes_path.write_text("release notes\n", encoding="utf-8")

        declared_surface_version = surface_version or repository_version
        (root / "README.md").write_text(f"release-{declared_surface_version}\n", encoding="utf-8")
        (root / "README.en.md").write_text(f"release-{declared_surface_version}\n", encoding="utf-8")
        (root / "CHANGELOG.md").write_text(f"## [{declared_surface_version}] — 2026-09-05\n", encoding="utf-8")
        (root / "CHANGELOG.en.md").write_text(f"## [{declared_surface_version}] — 2026-09-05\n", encoding="utf-8")

        plugins = []
        if plugin is not None:
            declared_version = plugin_version or "1.0.0"
            actual_version = actual_plugin_version or declared_version
            plugin_dir = root / "plugins" / plugin
            (plugin_dir / ".codex-plugin").mkdir(parents=True)
            (plugin_dir / ".claude-plugin").mkdir(parents=True)
            manifest = {"name": plugin, "version": actual_version, "skills": "./skills/"}
            (plugin_dir / ".codex-plugin/plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
            (plugin_dir / ".claude-plugin/plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
            entry = {
                "plugin": plugin,
                "version": declared_version,
                "tag": plugin_tag or f"{plugin}-v{declared_version}",
                "title": plugin_title or f"{plugin} {declared_version}",
                "notes_file": f".github/releases/{plugin}-v{declared_version}.md",
            }
            (releases / f"{plugin}-v{declared_version}.md").write_text("plugin notes\n", encoding="utf-8")
            plugins.append(entry)
            if duplicate_plugin:
                plugins.append(dict(entry))

        data = {
            "schema_version": 1,
            "repository": {
                "version": repository_version,
                "tag": repository_tag,
                "title": repository_title or f"Repository {repository_version}",
                "notes_file": notes_file,
            },
            "plugins": plugins,
        }
        (releases / "release.json").write_text(json.dumps(data), encoding="utf-8")
        return root

    def validate(self, root):
        module = self.load_module()
        return module.validate_release_manifest(root)

    def items(self, root):
        module = self.load_module()
        return module.release_items(root)

    def test_current_declared_manifest_is_valid(self):
        self.assertTrue(MANIFEST.exists(), ".github/releases/release.json must exist")
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        repository = data["repository"]
        self.assertTrue((ROOT / repository["notes_file"]).exists(), f"{repository['notes_file']} must exist")
        for plugin in data["plugins"]:
            self.assertTrue((ROOT / plugin["notes_file"]).exists(), f"{plugin['notes_file']} must exist")
        self.assertEqual(self.validate(ROOT), [])
        expected = [("repository", "repository", repository["version"], repository["tag"])]
        expected.extend(
            ("plugin", plugin["plugin"], plugin["version"], plugin["tag"])
            for plugin in data["plugins"]
        )
        self.assertEqual(
            [(item.kind, item.name, item.version, item.tag) for item in self.items(ROOT)],
            expected,
        )

    def test_repository_tag_must_equal_version(self):
        root = self.make_fixture(repository_version="1.0.6", repository_tag="repository-1.0.6")
        self.assertTrue(any("repository tag must equal version" in error for error in self.validate(root)))

    def test_repository_version_must_be_strict_semver(self):
        root = self.make_fixture(repository_version="release-1", repository_tag="release-1")
        self.assertTrue(any("strict SemVer" in error for error in self.validate(root)))

    def test_notes_path_must_be_confined_to_release_directory(self):
        root = self.make_fixture(notes_file="../notes.md")
        self.assertTrue(any(".github/releases" in error for error in self.validate(root)))

    def test_notes_file_must_exist(self):
        root = self.make_fixture(notes_file=".github/releases/missing.md", create_notes=False)
        self.assertTrue(any("notes file does not exist" in error for error in self.validate(root)))

    def test_declared_plugin_must_match_both_manifest_versions(self):
        root = self.make_fixture(
            plugin="yandex-wordstat",
            plugin_version="1.2.0",
            actual_plugin_version="1.1.2",
        )
        errors = self.validate(root)
        self.assertTrue(any("yandex-wordstat" in error and "1.1.2" in error and "1.2.0" in error for error in errors))

    def test_plugin_tag_must_be_canonical(self):
        root = self.make_fixture(
            plugin="yandex-wordstat",
            plugin_version="1.1.2",
            plugin_tag="wordstat-1.1.2",
        )
        self.assertTrue(any("yandex-wordstat-v1.1.2" in error for error in self.validate(root)))

    def test_plugins_and_tags_must_be_unique(self):
        root = self.make_fixture(
            plugin="yandex-wordstat",
            plugin_version="1.1.2",
            duplicate_plugin=True,
        )
        errors = self.validate(root)
        self.assertTrue(any("duplicate plugin" in error for error in errors))
        self.assertTrue(any("duplicate release tag" in error for error in errors))

    def test_tsv_emitted_scalars_reject_tabs_and_line_breaks(self):
        repository_root = self.make_fixture(repository_title="Repository 1.0.6\ninjected")
        repository_errors = self.validate(repository_root)
        self.assertTrue(any("TSV control character" in error for error in repository_errors), repository_errors)

        plugin_root = self.make_fixture(
            plugin="yandex-wordstat",
            plugin_version="1.1.2",
            plugin_title="Yandex Wordstat\t1.1.2",
        )
        plugin_errors = self.validate(plugin_root)
        self.assertTrue(any("TSV control character" in error for error in plugin_errors), plugin_errors)

    def test_repository_release_surfaces_must_match_declared_version(self):
        root = self.make_fixture(repository_version="1.0.6", surface_version="1.0.5")
        errors = self.validate(root)
        for filename in ("README.md", "README.en.md", "CHANGELOG.md", "CHANGELOG.en.md"):
            with self.subTest(filename=filename):
                self.assertTrue(
                    any(filename in error and "1.0.6" in error for error in errors),
                    errors,
                )


if __name__ == "__main__":
    unittest.main()
