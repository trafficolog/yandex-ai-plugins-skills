import copy
import unittest

from scripts.seo_weekly_graphs import export_graphs


def graph_report():
    return {
        "schema": "seo-weekly-organic-report/v1",
        "structures": {
            "structural_tree": {
                "nodes": [
                    {"page_id": "detail", "title": "Detail\nPage", "url": "/detail", "canonical_parent_id": "home"},
                    {"page_id": "home", "title": "Home \"Root\"", "url": "/", "canonical_parent_id": None},
                ],
                "edges": [{"parent_page_id": "home", "child_page_id": "detail"}],
            },
            "semantic_graph": {
                "nodes": [{"page_id": "detail"}, {"page_id": "home"}],
                "edges": [{"from_page_id": "home", "to_page_id": "detail", "relation": "SUPPORT"}],
            },
            "clusters": [
                {"cluster_id": "c2", "queries": ["second"]},
                {"cluster_id": "c1", "label": "Cluster [one]", "queries": ["a", "b"]},
            ],
            "link_plan": [
                {"from_page_id": "home", "to_page_id": "detail", "relation": "SUPPORT", "anchor_concept": "read \"more\""}
            ],
        },
    }


class WeeklyGraphTests(unittest.TestCase):
    def test_exports_only_present_source_structures(self):
        files = export_graphs(graph_report())
        self.assertEqual(
            set(files),
            {
                "diagrams/structural-tree.mmd",
                "diagrams/structural-tree.dot",
                "diagrams/semantic-graph.mmd",
                "diagrams/semantic-graph.dot",
                "diagrams/clusters.mmd",
                "diagrams/internal-links.dot",
            },
        )
        for path, text in files.items():
            self.assertIsInstance(text, str, path)
            self.assertTrue(text.endswith("\n"), path)

    def test_absent_structures_emit_no_placeholder_graphs(self):
        self.assertEqual(export_graphs({"schema": "seo-weekly-organic-report/v1"}), {})
        self.assertEqual(export_graphs({"schema": "seo-weekly-organic-report/v1", "structures": {}}), {})

    def test_exports_escape_hostile_labels(self):
        files = export_graphs(graph_report())
        structural_mmd = files["diagrams/structural-tree.mmd"]
        structural_dot = files["diagrams/structural-tree.dot"]
        self.assertNotIn('Home "Root"', structural_dot)
        self.assertIn('Home \\"Root\\"', structural_dot)
        self.assertNotIn("Detail\nPage", structural_dot)
        self.assertIn("Detail\\nPage", structural_dot)
        self.assertNotIn("Detail\nPage", structural_mmd)
        self.assertIn("Detail\\nPage", structural_mmd)
        self.assertIn("Cluster \\[one\\]", files["diagrams/clusters.mmd"])
        self.assertIn('read \\"more\\"', files["diagrams/internal-links.dot"])

    def test_output_order_is_stable_for_semantically_identified_items(self):
        first = export_graphs(graph_report())
        shuffled = graph_report()
        shuffled["structures"]["structural_tree"]["nodes"].reverse()
        shuffled["structures"]["semantic_graph"]["nodes"].reverse()
        shuffled["structures"]["clusters"].reverse()
        second = export_graphs(shuffled)
        self.assertEqual(first, second)

    def test_rejects_unknown_page_references(self):
        bad = graph_report()
        bad["structures"]["semantic_graph"]["edges"][0]["to_page_id"] = "missing"
        with self.assertRaises(ValueError):
            export_graphs(bad)


if __name__ == "__main__":
    unittest.main()
