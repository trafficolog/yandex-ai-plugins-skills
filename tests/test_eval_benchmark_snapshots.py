from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_MODULE = ROOT / "scripts/eval_benchmark/artifacts.py"
SNAPSHOTS_MODULE = ROOT / "scripts/eval_benchmark/snapshots.py"


def sample_run() -> dict[str, object]:
    return {
        "evaluated_at": "2026-09-06T17:10:00Z",
        "repository_sha": "d" * 40,
        "scenarios": [
            {
                "plugin": "yandex-seo",
                "scenario_id": "e" * 64,
                "source_path": "plugins/yandex-seo/evals/scenarios.json",
                "source_sha256": "f" * 64,
                "state": "UNDETERMINED",
                "subject": {
                    "schema": "yandex-ai-eval-adapter-response/v1",
                    "invocation_id": "subject-snapshot",
                    "adapter_id": "fake-subject",
                    "adapter_version": "1",
                    "runtime": {"name": "python", "version": "3.13"},
                    "model": {"name": "fake-model", "version": "1"},
                    "output": {
                        "text": "Stale memory remains stale context.",
                        "route": "yandex-seo-weekly-report",
                        "outcome": "comply_with_limitations",
                    },
                },
                "mechanical": [],
                "semantic": {
                    "judge_identity": ["python", "3.13", "fake-judge", "1"],
                    "subject_identity": ["python", "3.13", "fake-model", "1"],
                    "judge_mode": "INDEPENDENT",
                    "route": {"expected": "yandex-seo-weekly-report", "actual": "yandex-seo-weekly-report", "state": "PASS", "rationale": ""},
                    "outcome": {"expected": "comply_with_limitations", "actual": "comply_with_limitations", "state": "PASS"},
                    "must_convey": [{"expectation": "preserve stale provenance", "state": "UNDETERMINED", "evidence": [], "rationale": "insufficient evidence"}],
                    "must_not_claim": [],
                    "rationale": "bounded verdict",
                },
            }
        ],
        "aggregate": {"passed": 0, "failed": 0, "undetermined": 1, "total": 1},
        "subject_identities": [
            {
                "adapter_id": "fake-subject",
                "adapter_version": "1",
                "runtime": {"name": "python", "version": "3.13"},
                "model": {"name": "fake-model", "version": "1"},
                "fake": True,
            }
        ],
        "completeness": "INFRASTRUCTURE_READY",
        "comparative_complete": False,
    }


class EvalBenchmarkSnapshotTests(unittest.TestCase):
    def modules(self):
        self.assertTrue(ARTIFACTS_MODULE.is_file(), "benchmark artifacts module must exist")
        self.assertTrue(SNAPSHOTS_MODULE.is_file(), "benchmark snapshots module must exist")
        from scripts.eval_benchmark import artifacts, snapshots

        return artifacts, snapshots

    def test_materialize_snapshot_copies_verified_artifact_set_under_v1(self):
        artifacts, snapshots = self.modules()
        result = artifacts.build_result_document(sample_run(), memory_results={"passed": 0, "failed": 0, "undetermined": 1, "total": 1})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_dir = artifacts.publish_benchmark_artifacts(root / "artifacts", result)
            snapshot = snapshots.materialize_snapshot(artifact_dir, root)
            self.assertEqual(snapshot, root / "evals/results/v1" / result["benchmark_id"])
            source_files = sorted(path.relative_to(artifact_dir).as_posix() for path in artifact_dir.rglob("*") if path.is_file())
            snapshot_files = sorted(path.relative_to(snapshot).as_posix() for path in snapshot.rglob("*") if path.is_file())
            self.assertEqual(snapshot_files, source_files)
            for relative in source_files:
                self.assertEqual((snapshot / relative).read_bytes(), (artifact_dir / relative).read_bytes())
            self.assertEqual(snapshots.materialize_snapshot(artifact_dir, root), snapshot)

    def test_tampered_source_manifest_hash_fails_before_snapshot_creation(self):
        artifacts, snapshots = self.modules()
        result = artifacts.build_result_document(sample_run())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_dir = artifacts.publish_benchmark_artifacts(root / "artifacts", result)
            (artifact_dir / "results.json").write_text("{}\n", encoding="utf-8")
            expected = root / "evals/results/v1" / result["benchmark_id"]
            with self.assertRaisesRegex(ValueError, "hash|manifest|conflict|managed"):
                snapshots.materialize_snapshot(artifact_dir, root)
            self.assertFalse(expected.exists())

    def test_conflicting_existing_snapshot_is_not_overwritten(self):
        artifacts, snapshots = self.modules()
        result = artifacts.build_result_document(sample_run())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_dir = artifacts.publish_benchmark_artifacts(root / "artifacts", result)
            snapshot = snapshots.materialize_snapshot(artifact_dir, root)
            results_path = snapshot / "results.json"
            results_path.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conflict|unexpected|exact"):
                snapshots.materialize_snapshot(artifact_dir, root)
            self.assertEqual(results_path.read_text(encoding="utf-8"), "{}\n")

    def test_snapshot_rejects_extra_unmanaged_source_file(self):
        artifacts, snapshots = self.modules()
        result = artifacts.build_result_document(sample_run())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_dir = artifacts.publish_benchmark_artifacts(root / "artifacts", result)
            (artifact_dir / "unmanaged.txt").write_text("unexpected", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected|managed"):
                snapshots.materialize_snapshot(artifact_dir, root)


if __name__ == "__main__":
    unittest.main()
