import ast
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
P2_SCRIPTS = (
    "seo_weekly_model.py",
    "seo_weekly_artifacts.py",
    "seo_weekly_html.py",
    "seo_weekly_graphs.py",
    "seo_weekly_memory.py",
    "seo_weekly_report.py",
)
REQUIRED_CONTRACT_IDS = {
    "seo.weekly-report-provenance",
    "seo.weekly-report-self-contained-html",
    "seo.weekly-report-immutable-artifacts",
    "seo.weekly-report-graph-exports",
}


class P2WeeklyOrganicReportContractTests(unittest.TestCase):
    def test_contract_matrix_traces_all_p2_high_risk_surfaces(self):
        matrix = json.loads((ROOT / "docs/CONTRACT_MATRIX.json").read_text(encoding="utf-8"))
        by_id = {item["id"]: item for item in matrix["contracts"]}
        self.assertTrue(REQUIRED_CONTRACT_IDS.issubset(by_id))
        for contract_id in REQUIRED_CONTRACT_IDS:
            row = by_id[contract_id]
            self.assertEqual(row["plugin"], "yandex-seo")
            self.assertIn("plugins/yandex-seo/skills/yandex-seo-weekly-report/SKILL.md", row["skills"])
            self.assertTrue(row["helpers"])
            self.assertTrue(row["test_refs"])

    def test_bilingual_docs_expose_quick_path_and_artifact_contracts(self):
        pairs = (
            ("README.md", "README.en.md"),
            ("docs/ARCHITECTURE.md", "docs/ARCHITECTURE.en.md"),
            ("docs/GETTING_STARTED.md", "docs/GETTING_STARTED.en.md"),
            ("SECURITY.md", "SECURITY.en.md"),
            ("plugins/yandex-seo/README.md", "plugins/yandex-seo/README.en.md"),
        )
        for left, right in pairs:
            for relative in (left, right):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("seo-weekly-organic-report/v1", text, relative)
                self.assertIn("yandex-ai-artifact-manifest/v1", text, relative)
                self.assertIn("seo_weekly_report.py demo", text, relative)
                self.assertIn("self-contained", text.lower(), relative)
                self.assertIn("PREVIEW-ONLY", text, relative)

    def test_p2_runtime_has_no_transport_or_credential_environment_access(self):
        scripts_root = ROOT / "plugins/yandex-seo/scripts"
        forbidden_roots = {"http", "socket", "ssl", "requests", "httpx", "aiohttp", "urllib", "urllib3", "pycurl", "subprocess", "importlib"}
        for name in P2_SCRIPTS:
            path = scripts_root / name
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    imported.add(node.module.split(".", 1)[0])
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                    self.assertFalse(node.value.id == "os" and node.attr == "environ", name)
            self.assertFalse(imported & forbidden_roots, f"{name}: {sorted(imported & forbidden_roots)}")
            for service_module in ("ym_api", "ym_report", "yw_api", "yw_queries"):
                self.assertNotIn(service_module, source, name)

    def test_repository_keeps_existing_cross_service_transport_guard(self):
        validator = (ROOT / "scripts/validate_repo_core.py").read_text(encoding="utf-8")
        self.assertIn('CROSS_SERVICE_PLUGINS = {"yandex-seo", "yandex-marketing"}', validator)
        self.assertIn("_validate_cross_service_transport", validator)
        self.assertIn('"subprocess"', validator)


if __name__ == "__main__":
    unittest.main()
