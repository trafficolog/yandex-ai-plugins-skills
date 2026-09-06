import math
import unittest

from scripts.seo_weekly_model import canonical_json_bytes, normalize_report_input, semantic_report_id


GENERATED_AT = "2026-09-06T12:30:00Z"


def valid_payload():
    return {
        "project": {"id": "demo-site", "name": "Demo Site"},
        "period": {"from": "2026-08-24", "to": "2026-08-30"},
        "comparison_period": {"from": "2026-08-17", "to": "2026-08-23"},
        "webmaster": {
            "coverage": "PARTIAL",
            "source": {
                "site": "https://example.test/",
                "limit": 500,
                "offset": 0,
                "filters": {"device": "ALL"},
            },
            "limitations": ["WEBMASTER_TOP_N"],
            "evidence": [
                {
                    "evidence_id": "wm-q1",
                    "claim_class": "OBSERVED",
                    "source": "yandex-webmaster",
                    "metric": "clicks",
                    "value": 12,
                }
            ],
            "query_rows": [
                {
                    "query_id": "q1",
                    "query": "example query",
                    "current": {"impressions": 120, "clicks": 12, "ctr": 0.1, "position": 5.0},
                    "previous": {"impressions": 100, "clicks": 8, "ctr": 0.08, "position": 7.0},
                    "evidence_ids": ["wm-q1"],
                }
            ],
        },
        "metrika": {
            "coverage": "COMPLETE",
            "source": {
                "counter_id": "12345",
                "quality": {
                    "sampled": True,
                    "sample_share": 0.8,
                    "sample_size": 800,
                    "sample_space": 1000,
                    "data_lag": 0,
                    "contains_sensitive_data": False,
                    "total_rows_rounded": False,
                },
            },
            "limitations": ["METRIKA_SAMPLED"],
            "evidence": [
                {
                    "evidence_id": "m-p1",
                    "claim_class": "OBSERVED",
                    "source": "yandex-metrika",
                    "metric": "visits",
                    "value": 100,
                }
            ],
            "page_rows": [
                {
                    "page_id": "p1",
                    "url": "https://example.test/page",
                    "current": {"visits": 100, "users": 80},
                    "previous": {"visits": 80, "users": 70},
                    "evidence_ids": ["m-p1"],
                }
            ],
        },
        "delegated_previews": [
            {
                "preview_id": "preview-1",
                "owner": "cms",
                "operation": "review-title",
                "status": "PREVIEW",
            }
        ],
    }


class WeeklyOrganicModelTests(unittest.TestCase):
    def test_normalizes_versioned_report_and_preserves_source_quality(self):
        report = normalize_report_input(valid_payload(), generated_at=GENERATED_AT)
        self.assertEqual(report["schema"], "seo-weekly-organic-report/v1")
        self.assertEqual(report["generated_at"], GENERATED_AT)
        self.assertEqual(report["coverage"], {"metrika": "COMPLETE", "webmaster": "PARTIAL"})
        self.assertEqual(report["sources"]["webmaster"]["limit"], 500)
        self.assertEqual(report["sources"]["webmaster"]["filters"], {"device": "ALL"})
        self.assertTrue(report["sources"]["metrika"]["quality"]["sampled"])
        self.assertEqual(report["sources"]["metrika"]["quality"]["sample_share"], 0.8)
        self.assertIn("WEBMASTER_TOP_N", report["limitations"])
        self.assertIn("METRIKA_SAMPLED", report["limitations"])
        self.assertEqual(report["delegated_previews"][0]["status"], "PREVIEW")

    def test_builds_deterministic_movers_and_evidence_backed_findings(self):
        report = normalize_report_input(valid_payload(), generated_at=GENERATED_AT)
        query = report["query_movers"][0]
        self.assertEqual(query["query_id"], "q1")
        self.assertEqual(query["metrics"]["clicks"]["delta"], 4)
        self.assertAlmostEqual(query["metrics"]["position"]["delta"], -2.0)
        page = report["page_movers"][0]
        self.assertEqual(page["metrics"]["visits"]["delta"], 20)
        self.assertEqual({item["claim_class"] for item in report["findings"]}, {"DERIVED"})
        known = {item["evidence_id"] for item in report["evidence"]}
        for finding in report["findings"]:
            self.assertTrue(finding["evidence_ids"])
            self.assertTrue(set(finding["evidence_ids"]).issubset(known))

    def test_report_id_ignores_generated_at_but_tracks_semantics(self):
        first = normalize_report_input(valid_payload(), generated_at="2026-09-06T12:30:00Z")
        second = normalize_report_input(valid_payload(), generated_at="2026-09-06T13:30:00Z")
        self.assertEqual(first["report_id"], second["report_id"])
        changed = valid_payload()
        changed["webmaster"]["query_rows"][0]["current"]["clicks"] = 13
        third = normalize_report_input(changed, generated_at="2026-09-06T12:30:00Z")
        self.assertNotEqual(first["report_id"], third["report_id"])
        without_id = dict(first)
        without_id.pop("report_id")
        self.assertEqual(first["report_id"], semantic_report_id(without_id))

    def test_canonical_json_is_stable_and_rejects_non_finite_numbers(self):
        self.assertEqual(canonical_json_bytes({"b": 1, "a": "я"}), b'{"a":"\xd1\x8f","b":1}')
        payload = valid_payload()
        payload["metrika"]["page_rows"][0]["current"]["visits"] = math.nan
        with self.assertRaises(ValueError):
            normalize_report_input(payload, generated_at=GENERATED_AT)

    def test_rejects_invalid_periods_duplicate_evidence_and_claim_classes(self):
        payload = valid_payload()
        payload["comparison_period"] = {"from": "2026-08-29", "to": "2026-09-02"}
        with self.assertRaises(ValueError):
            normalize_report_input(payload, generated_at=GENERATED_AT)

        payload = valid_payload()
        payload["metrika"]["evidence"][0]["evidence_id"] = "wm-q1"
        with self.assertRaises(ValueError):
            normalize_report_input(payload, generated_at=GENERATED_AT)

        payload = valid_payload()
        payload["webmaster"]["evidence"][0]["claim_class"] = "FACT"
        with self.assertRaises(ValueError):
            normalize_report_input(payload, generated_at=GENERATED_AT)

    def test_missing_source_is_partial_not_global_failure(self):
        payload = valid_payload()
        payload.pop("metrika")
        report = normalize_report_input(payload, generated_at=GENERATED_AT)
        self.assertEqual(report["coverage"]["metrika"], "MISSING")
        self.assertEqual(report["page_movers"], [])
        self.assertIn("METRIKA_MISSING", report["limitations"])

    def test_rejects_secret_like_managed_fields(self):
        payload = valid_payload()
        payload["webmaster"]["source"]["oauth_token"] = "do-not-store"
        with self.assertRaises(ValueError):
            normalize_report_input(payload, generated_at=GENERATED_AT)


if __name__ == "__main__":
    unittest.main()
