import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.seo_weekly_artifacts import artifact_directory, build_manifest, publish_artifact_set


class WeeklyArtifactTests(unittest.TestCase):
    def test_artifact_directory_is_predictable_and_path_safe(self):
        root = Path("/tmp/artifacts")
        got = artifact_directory(root, "demo-site", "2026-08-30", "abc123")
        self.assertEqual(got, root / "demo-site" / "2026-08-30" / "weekly-organic-abc123")
        for unsafe in ["", ".", "..", "../escape", "/absolute", "a/b", "a\\b", "bad\x00slug"]:
            with self.assertRaises(ValueError, msg=unsafe):
                artifact_directory(root, unsafe, "2026-08-30", "abc123")
        for unsafe_report in ["../x", "/x", "a/b", ""]:
            with self.assertRaises(ValueError):
                artifact_directory(root, "demo-site", "2026-08-30", unsafe_report)

    def test_manifest_hashes_managed_files_and_excludes_itself(self):
        report_bytes = b'{"schema":"seo-weekly-organic-report/v1"}'
        files = {
            "report.json": report_bytes,
            "report.html": b"<html></html>",
            "diagrams/tree.mmd": b"flowchart TD\n",
        }
        manifest = build_manifest(files, report_bytes=report_bytes, created_at="2026-09-06T12:30:00Z")
        self.assertEqual(manifest["schema"], "yandex-ai-artifact-manifest/v1")
        self.assertEqual(manifest["artifact_set_id"], hashlib.sha256(report_bytes).hexdigest())
        self.assertEqual(manifest["primary_artifact"], "report.json")
        self.assertEqual([item["path"] for item in manifest["files"]], sorted(files))
        self.assertNotIn("manifest.json", {item["path"] for item in manifest["files"]})
        by_path = {item["path"]: item for item in manifest["files"]}
        self.assertEqual(by_path["report.json"]["role"], "PRIMARY_JSON")
        self.assertEqual(by_path["report.json"]["schema"], "seo-weekly-organic-report/v1")
        self.assertEqual(by_path["report.html"]["media_type"], "text/html; charset=utf-8")
        self.assertEqual(by_path["diagrams/tree.mmd"]["role"], "MERMAID")
        self.assertEqual(by_path["report.html"]["sha256"], hashlib.sha256(files["report.html"]).hexdigest())

    def test_manifest_rejects_unsafe_relative_paths(self):
        for unsafe in ["/abs", "../escape", "a/../b", "a\\b", "", "manifest.json"]:
            with self.assertRaises(ValueError, msg=unsafe):
                build_manifest({unsafe: b"x", "report.json": b"{}"}, report_bytes=b"{}", created_at="2026-09-06T12:30:00Z")

    def test_publish_is_atomic_and_exact_replay_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "artifact-set"
            report_bytes = b'{"schema":"seo-weekly-organic-report/v1","report_id":"r1"}'
            files = {"report.json": report_bytes, "report.html": b"<html>ok</html>"}
            manifest = build_manifest(files, report_bytes=report_bytes, created_at="2026-09-06T12:30:00Z")
            first = publish_artifact_set(destination, files, manifest)
            self.assertEqual(first, destination)
            self.assertEqual((destination / "report.json").read_bytes(), report_bytes)
            stored_manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(stored_manifest, manifest)
            second = publish_artifact_set(destination, files, manifest)
            self.assertEqual(second, destination)

    def test_conflicting_existing_snapshot_fails_without_rewrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "artifact-set"
            report_bytes = b'{"schema":"seo-weekly-organic-report/v1","report_id":"r1"}'
            files = {"report.json": report_bytes, "report.html": b"<html>ok</html>"}
            manifest = build_manifest(files, report_bytes=report_bytes, created_at="2026-09-06T12:30:00Z")
            publish_artifact_set(destination, files, manifest)
            (destination / "report.html").write_bytes(b"conflict")
            with self.assertRaises(ValueError):
                publish_artifact_set(destination, files, manifest)
            self.assertEqual((destination / "report.html").read_bytes(), b"conflict")

    def test_extra_file_breaks_exact_snapshot_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "artifact-set"
            report_bytes = b"{}"
            files = {"report.json": report_bytes}
            manifest = build_manifest(files, report_bytes=report_bytes, created_at="2026-09-06T12:30:00Z")
            publish_artifact_set(destination, files, manifest)
            (destination / "extra.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                publish_artifact_set(destination, files, manifest)


if __name__ == "__main__":
    unittest.main()
