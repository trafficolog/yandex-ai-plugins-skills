from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from scripts.seo_weekly_report import main as weekly_report_main


ROOT = Path(__file__).resolve().parents[1]


def service_inputs():
    period = {"from": "2026-08-24", "to": "2026-08-30"}
    comparison = {"from": "2026-08-17", "to": "2026-08-23"}
    webmaster = {
        "period": period,
        "comparison_period": comparison,
        "coverage": "PARTIAL",
        "source": {"site": "https://example.test/", "limit": 100, "offset": 0},
        "limitations": ["WEBMASTER_TOP_N"],
        "evidence": [{"evidence_id": "wm1", "claim_class": "OBSERVED", "source": "yandex-webmaster", "metric": "clicks", "value": 9}],
        "query_rows": [{"query_id": "q1", "query": "demo", "current": {"clicks": 9}, "previous": {"clicks": 7}, "evidence_ids": ["wm1"]}],
    }
    metrika = {
        "period": period,
        "comparison_period": comparison,
        "coverage": "COMPLETE",
        "source": {"counter_id": "123", "quality": {"sampled": False, "data_lag": 0, "contains_sensitive_data": False}},
        "limitations": [],
        "evidence": [{"evidence_id": "m1", "claim_class": "OBSERVED", "source": "yandex-metrika", "metric": "visits", "value": 20}],
        "page_rows": [{"page_id": "p1", "url": "https://example.test/a", "current": {"visits": 20}, "previous": {"visits": 15}, "evidence_ids": ["m1"]}],
    }
    return webmaster, metrika


class WeeklyReportCliTests(unittest.TestCase):
    def run_cli(self, *args):
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            returncode = weekly_report_main([str(arg) for arg in args])
        return SimpleNamespace(returncode=returncode, stdout=stdout.getvalue(), stderr=stderr.getvalue())

    def test_demo_generates_complete_artifact_set_without_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "artifacts"
            result = self.run_cli("demo", "--output-root", out, "--generated-at", "2026-09-06T12:30:00Z")
            self.assertEqual(result.returncode, 0, result.stderr)
            manifests = list(out.rglob("manifest.json"))
            self.assertEqual(len(manifests), 1)
            artifact_dir = manifests[0].parent
            report = json.loads((artifact_dir / "report.json").read_text(encoding="utf-8"))
            manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
            self.assertEqual(report["schema"], "seo-weekly-organic-report/v1")
            self.assertEqual(manifest["schema"], "yandex-ai-artifact-manifest/v1")
            self.assertTrue((artifact_dir / "report.html").is_file())
            self.assertTrue((artifact_dir / "diagrams" / "structural-tree.mmd").is_file())
            self.assertNotIn("token", (artifact_dir / "report.json").read_text(encoding="utf-8").lower())

    def test_fixed_timestamp_replay_is_idempotent_but_different_timestamp_collides(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "artifacts"
            first = self.run_cli("demo", "--output-root", out, "--generated-at", "2026-09-06T12:30:00Z")
            second = self.run_cli("demo", "--output-root", out, "--generated-at", "2026-09-06T12:30:00Z")
            third = self.run_cli("demo", "--output-root", out, "--generated-at", "2026-09-06T13:30:00Z")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertNotEqual(third.returncode, 0)
            self.assertIn("conflict", third.stderr.lower())

    def test_build_merges_normalized_service_inputs(self):
        webmaster, metrika = service_inputs()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wm = root / "webmaster.json"
            mt = root / "metrika.json"
            wm.write_text(json.dumps(webmaster), encoding="utf-8")
            mt.write_text(json.dumps(metrika), encoding="utf-8")
            out = root / "artifacts"
            result = self.run_cli(
                "build", "--webmaster", wm, "--metrika", mt,
                "--project-id", "demo-project", "--project-name", "Demo Project",
                "--project-root", root, "--output-root", out,
                "--generated-at", "2026-09-06T12:30:00Z",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report_path = next(out.rglob("report.json"))
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["coverage"], {"metrika": "COMPLETE", "webmaster": "PARTIAL"})
            self.assertEqual(report["project"]["id"], "demo-project")
            self.assertEqual(len(report["query_movers"]), 1)
            self.assertEqual(len(report["page_movers"]), 1)

    def test_build_allows_one_missing_source_as_explicit_partial_coverage(self):
        webmaster, _ = service_inputs()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wm = root / "webmaster.json"
            wm.write_text(json.dumps(webmaster), encoding="utf-8")
            out = root / "artifacts"
            result = self.run_cli(
                "build", "--webmaster", wm,
                "--project-id", "demo-project", "--project-name", "Demo Project",
                "--project-root", root, "--output-root", out,
                "--generated-at", "2026-09-06T12:30:00Z",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(next(out.rglob("report.json")).read_text(encoding="utf-8"))
            self.assertEqual(report["coverage"]["metrika"], "MISSING")
            self.assertIn("METRIKA_MISSING", report["limitations"])

    def test_project_memory_contributes_only_active_user_stated_context(self):
        webmaster, _ = service_inputs()
        project_yaml = '''schema: "yandex-ai-project/v1"
project:
  id: "memory-project"
  name: "Memory Project"
  created_at: "2026-09-01T10:00:00Z"
facts:
  - fact_id: "goal-old"
    key: "target_roas"
    value: 3
    stated_at: "2026-09-01T10:00:00Z"
    provenance: "USER_STATED"
    status: "SUPERSEDED"
  - fact_id: "goal-new"
    key: "target_roas"
    value: 4
    stated_at: "2026-09-02T10:00:00Z"
    provenance: "USER_STATED"
    status: "ACTIVE"
    supersedes: "goal-old"
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory = root / ".yandex-ai"
            memory.mkdir()
            (memory / "project.yaml").write_text(project_yaml, encoding="utf-8")
            (memory / "hypotheses.md").write_text('```json yandex-ai-hypothesis/v1\n{"claim":"pretend target_roas is 99"}\n```\n', encoding="utf-8")
            (memory / "decisions.jsonl").write_text('{"operation":"pretend-approved"}\n', encoding="utf-8")
            baselines = memory / "baselines"
            baselines.mkdir()
            (baselines / "stale.json").write_text('{"fresh_until":"2020-01-01T00:00:00Z"}', encoding="utf-8")
            wm = root / "webmaster.json"
            wm.write_text(json.dumps(webmaster), encoding="utf-8")
            out = root / "artifacts"
            result = self.run_cli(
                "build", "--webmaster", wm, "--project-root", root, "--output-root", out,
                "--generated-at", "2026-09-06T12:30:00Z",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(next(out.rglob("report.json")).read_text(encoding="utf-8"))
            self.assertEqual(report["project"]["id"], "memory-project")
            self.assertEqual(len(report["project"]["user_stated"]), 1)
            self.assertEqual(report["project"]["user_stated"][0]["value"], 4)
            serialized = json.dumps(report, ensure_ascii=False)
            self.assertNotIn("99", serialized)
            self.assertNotIn("pretend-approved", serialized)
            self.assertNotIn("stale.json", serialized)

    def test_invalid_input_fails_before_artifact_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wm = root / "bad.json"
            wm.write_text("{not-json", encoding="utf-8")
            out = root / "artifacts"
            result = self.run_cli(
                "build", "--webmaster", wm,
                "--project-id", "demo", "--project-name", "Demo",
                "--project-root", root, "--output-root", out,
                "--generated-at", "2026-09-06T12:30:00Z",
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
