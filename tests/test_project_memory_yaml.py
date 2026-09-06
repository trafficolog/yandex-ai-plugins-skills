import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "project_memory" / "yaml_subset.py"


class RestrictedYamlTests(unittest.TestCase):
    def load_module(self):
        self.assertTrue(MODULE_PATH.exists(), "restricted YAML codec must exist")
        spec = importlib.util.spec_from_file_location("project_memory_yaml_under_test", MODULE_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(module)
        return module

    def test_round_trip_project_shape(self):
        module = self.load_module()
        value = {
            "schema": "yandex-ai-project/v1",
            "project": {
                "id": "demo",
                "name": "Demo",
                "created_at": "2026-09-06T07:30:00Z",
            },
            "facts": [
                {
                    "fact_id": "f1",
                    "key": "target_roas",
                    "value": 4.5,
                    "stated_at": "2026-09-06T07:30:00Z",
                    "provenance": "USER_STATED",
                    "status": "ACTIVE",
                }
            ],
        }
        rendered = module.dumps(value)
        self.assertEqual(module.loads(rendered), value)
        self.assertIn('schema: "yandex-ai-project/v1"', rendered)
        self.assertIn('  id: "demo"', rendered)

    def test_scalars_follow_strict_json_compatible_rules(self):
        module = self.load_module()
        value = {
            "text": "null true 01 stay strings",
            "truth": True,
            "falsehood": False,
            "nothing": None,
            "integer": -12,
            "fraction": 4.5,
            "items": ["x", 1, 2.5, False, None],
        }
        self.assertEqual(module.loads(module.dumps(value)), value)

    def test_duplicate_mapping_keys_are_rejected(self):
        module = self.load_module()
        with self.assertRaises(module.YamlSubsetError):
            module.loads('schema: "a"\nschema: "b"\n')

    def test_unsafe_yaml_features_are_rejected(self):
        module = self.load_module()
        cases = (
            'a: &x 1\nb: *x\n',
            'a: !python/object 1\n',
            'a: |\n  x\n',
            'a: >\n  x\n',
            '<<: {}\n',
            'a:\t1\n',
            'a: yes\n',
            'a: 01\n',
            'a: 2026-09-06\n',
        )
        for text in cases:
            with self.subTest(text=text), self.assertRaises(module.YamlSubsetError):
                module.loads(text)

    def test_non_two_space_indentation_is_rejected(self):
        module = self.load_module()
        with self.assertRaises(module.YamlSubsetError):
            module.loads('root:\n   child: "x"\n')


if __name__ == "__main__":
    unittest.main()
