import unittest

from scripts.seo_weekly_html import render_html


def report_fixture():
    return {
        "schema": "seo-weekly-organic-report/v1",
        "report_id": "r1",
        "generated_at": "2026-09-06T12:30:00Z",
        "project": {"id": "demo", "name": "Demo <script>alert(1)</script>"},
        "period": {"from": "2026-08-24", "to": "2026-08-30"},
        "comparison_period": {"from": "2026-08-17", "to": "2026-08-23"},
        "coverage": {"webmaster": "PARTIAL", "metrika": "COMPLETE"},
        "sources": {"webmaster": {"site": "https://example.test/"}, "metrika": {"counter_id": "123"}},
        "summary": {"query_movers": 1, "page_movers": 1, "findings": 1, "limitations": 1},
        "query_movers": [
            {"query_id": "q1", "query": "<b>query & x</b>", "metrics": {"clicks": {"current": 12, "previous": 8, "delta": 4}}, "evidence_ids": ["e1"]}
        ],
        "page_movers": [
            {"page_id": "p1", "url": "https://example.test/page?x=<bad>", "metrics": {"visits": {"current": 100, "previous": 80, "delta": 20}}, "evidence_ids": ["e1"]}
        ],
        "findings": [
            {"finding_id": "query:q1", "kind": "QUERY_CHANGE", "claim_class": "DERIVED", "subject_id": "q1", "subject": "danger \"quoted\" <img src=x onerror=1>", "metrics": {"clicks": {"current": 12, "previous": 8, "delta": 4}}, "evidence_ids": ["e1"]}
        ],
        "limitations": ["WEBMASTER_TOP_N <script>bad()</script>"],
        "evidence": [
            {"evidence_id": "e1", "claim_class": "OBSERVED", "source": "yandex-webmaster", "metric": "clicks", "value": 12, "note": "javascript:alert(1)"}
        ],
        "delegated_previews": [
            {"preview_id": "dp1", "owner": "cms", "operation": "change <title>", "status": "PREVIEW"}
        ],
    }


class WeeklyHtmlTests(unittest.TestCase):
    def test_renderer_escapes_source_text(self):
        html = render_html(report_fixture())
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn("<img src=x onerror=1>", html)
        self.assertIn("Demo &lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("&lt;b&gt;query &amp; x&lt;/b&gt;", html)
        self.assertIn("&lt;img src=x onerror=1&gt;", html)

    def test_report_is_self_contained_and_blocks_network_surfaces(self):
        html = render_html(report_fixture()).lower()
        for forbidden in [
            '<script src=', '<link ', '<iframe', '<object', '<embed',
            'src="http://', "src='http://", 'src="https://', "src='https://",
            'href="http://', "href='http://", 'href="https://', "href='https://",
            'fetch(', 'xmlhttprequest', 'websocket(', 'sendbeacon',
        ]:
            self.assertNotIn(forbidden, html, forbidden)
        self.assertIn("content-security-policy", html)
        self.assertIn("default-src &#x27;none&#x27;", html)
        self.assertIn("frame-ancestors &#x27;none&#x27;", html)

    def test_required_sections_and_preview_only_boundary_are_visible(self):
        html = render_html(report_fixture())
        for text in ["Summary", "Coverage", "Limitations", "Findings", "Query movers", "Page movers", "Evidence / provenance"]:
            self.assertIn(text, html)
        self.assertIn("PREVIEW-ONLY", html)
        self.assertIn("<details", html)
        self.assertIn("data-sort", html)
        self.assertIn("id=\"finding-filter\"", html)
        limitation_index = html.index("Limitations")
        first_details = html.index("<details")
        self.assertLess(limitation_index, first_details)

    def test_renderer_does_not_invent_findings(self):
        report = report_fixture()
        report["findings"] = []
        html = render_html(report)
        self.assertNotIn("QUERY_CHANGE", html)
        self.assertIn("No findings", html)


if __name__ == "__main__":
    unittest.main()
