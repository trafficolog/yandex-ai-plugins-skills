from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = ROOT / "scripts/eval_benchmark/scenarios.py"


class EvalBenchmarkScenarioTests(unittest.TestCase):
    def scenarios(self):
        self.assertTrue(SCENARIOS_PATH.is_file(), "eval benchmark scenarios module must exist")
        from scripts.eval_benchmark import scenarios

        return scenarios

    def make_repo(self, scenario_items: list[dict[str, object]]) -> tuple[tempfile.TemporaryDirectory, Path]:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        plugin = root / "plugins/yandex-seo"
        (plugin / "evals").mkdir(parents=True)
        (plugin / "evals/scenarios.json").write_text(
            json.dumps({"version": 2, "scenarios": scenario_items}, ensure_ascii=False),
            encoding="utf-8",
        )
        return tmp, root

    def base_scenario(self) -> dict[str, object]:
        return {
            "prompt": "audit",
            "skill": "yandex-seo-audit",
            "write": False,
            "expect": {
                "must_route_to": "yandex-seo-audit",
                "outcome": "comply",
                "must_mention_tokens": ["OBSERVED", "DERIVED"],
                "must_convey": ["Separate evidence classes"],
                "must_not_claim": ["hypothesis is observed"],
            },
        }

    def test_loads_v2_with_plugin_source_hash_and_stable_id(self):
        scenarios = self.scenarios()
        scenario = self.base_scenario()
        tmp, root = self.make_repo([scenario])
        self.addCleanup(tmp.cleanup)
        source = root / "plugins/yandex-seo/evals/scenarios.json"

        records = scenarios.load_scenarios(root, ["yandex-seo"])

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["plugin"], "yandex-seo")
        self.assertEqual(record["source_path"], "plugins/yandex-seo/evals/scenarios.json")
        self.assertEqual(record["source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(record["scenario"], scenario)
        self.assertEqual(record["scenario_id"], scenarios.scenario_id("yandex-seo", scenario))

    def test_scenario_order_does_not_change_each_derived_id(self):
        scenarios = self.scenarios()
        first = self.base_scenario()
        second = self.base_scenario()
        second["prompt"] = "second"
        first_ids = {
            item["scenario"]["prompt"]: item["scenario_id"]
            for item in self._load([first, second])
        }
        second_ids = {
            item["scenario"]["prompt"]: item["scenario_id"]
            for item in self._load([second, first])
        }
        self.assertEqual(first_ids, second_ids)

    def _load(self, items: list[dict[str, object]]) -> list[dict[str, object]]:
        scenarios = self.scenarios()
        tmp, root = self.make_repo(items)
        self.addCleanup(tmp.cleanup)
        return scenarios.load_scenarios(root, ["yandex-seo"])

    def test_array_order_inside_scenario_is_semantically_significant(self):
        scenarios = self.scenarios()
        left = self.base_scenario()
        right = json.loads(json.dumps(left))
        right["expect"]["must_convey"] = list(reversed(right["expect"]["must_convey"] + ["Second rule"]))
        left["expect"]["must_convey"].append("Second rule")
        self.assertNotEqual(
            scenarios.scenario_id("yandex-seo", left),
            scenarios.scenario_id("yandex-seo", right),
        )

    def test_duplicate_derived_scenario_ids_are_rejected(self):
        scenario = self.base_scenario()
        with self.assertRaisesRegex(ValueError, "duplicate scenario_id"):
            self._load([scenario, json.loads(json.dumps(scenario))])

    def test_memory_fixture_must_be_safe_existing_repository_relative_path(self):
        scenarios = self.scenarios()
        scenario = self.base_scenario()
        scenario["memory_fixture"] = "evals/fixtures/memory/stale-baseline"
        tmp, root = self.make_repo([scenario])
        self.addCleanup(tmp.cleanup)
        fixture = root / "evals/fixtures/memory/stale-baseline"
        fixture.mkdir(parents=True)
        records = scenarios.load_scenarios(root, ["yandex-seo"])
        self.assertEqual(records[0]["memory_fixture"], "evals/fixtures/memory/stale-baseline")

        for bad in (
            "/tmp/memory",
            "../memory",
            "evals/fixtures/backend-equivalence/x",
            "evals/fixtures/memory/../escape",
            "evals/fixtures/memory/missing",
        ):
            with self.subTest(bad=bad):
                broken = self.base_scenario()
                broken["memory_fixture"] = bad
                tmp2, root2 = self.make_repo([broken])
                self.addCleanup(tmp2.cleanup)
                with self.assertRaises(ValueError):
                    scenarios.load_scenarios(root2, ["yandex-seo"])

    def test_non_v2_source_is_rejected_not_repaired(self):
        scenarios = self.scenarios()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        path = root / "plugins/yandex-seo/evals"
        path.mkdir(parents=True)
        (path / "scenarios.json").write_text(
            json.dumps({"version": 1, "scenarios": [self.base_scenario()]}),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "version 2"):
            scenarios.load_scenarios(root, ["yandex-seo"])


if __name__ == "__main__":
    unittest.main()
