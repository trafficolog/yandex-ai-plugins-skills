import base64
import json
import unittest

from scripts.ys_parse import parse_search_response
from scripts.ys_request import build_search_request


class TestPractitionerSmartSnippets(unittest.TestCase):
    def test_sync_ru_request_enables_info_context_metadata(self):
        request = build_search_request(
            "налог усн 2026",
            folder_id="folder",
            api_key="key",
            smart_snippets=True,
            search_type="SEARCH_TYPE_RU",
            groups_on_page=20,
        )
        self.assertEqual(
            request["body"]["metadata"]["fields"]["x-genesis-info-context"],
            "on",
        )

    def test_smart_snippets_reject_async_mode(self):
        with self.assertRaisesRegex(ValueError, "smart snippets.*sync"):
            build_search_request(
                "x", folder_id="f", api_key="k", mode="async", smart_snippets=True
            )

    def test_smart_snippets_reject_non_ru_search_type(self):
        with self.assertRaisesRegex(ValueError, "SEARCH_TYPE_RU"):
            build_search_request(
                "x",
                folder_id="f",
                api_key="k",
                search_type="SEARCH_TYPE_COM",
                smart_snippets=True,
            )

    def test_smart_snippets_use_conservative_twenty_document_guardrail(self):
        with self.assertRaisesRegex(ValueError, "20"):
            build_search_request(
                "x",
                folder_id="f",
                api_key="k",
                groups_on_page=21,
                docs_in_group=1,
                smart_snippets=True,
            )

    def test_json_info_context_normalizes_live_rich_data_shape(self):
        raw = json.dumps(
            {
                "docs": [
                    {
                        "FullUrl": "https://example.com/page",
                        "rich_data": {
                            "Num": 3,
                            "DocumentTitle": "Example title",
                            "Description": "Short description",
                            "ForcedShortUrl": "example.com",
                        },
                        "info_context": "Long relevant extract for the agent.",
                    }
                ]
            },
            ensure_ascii=False,
        )
        payload = {"rawData": base64.b64encode(raw.encode()).decode()}
        result = parse_search_response(payload, "FORMAT_XML")
        self.assertEqual(result["format"], "json")
        self.assertEqual(result["results"][0]["rank"], 3)
        self.assertEqual(result["results"][0]["title"], "Example title")
        self.assertEqual(result["results"][0]["domain"], "example.com")
        self.assertEqual(result["results"][0]["extract"], "Long relevant extract for the agent.")

    def test_json_info_context_accepts_documented_flat_shape(self):
        raw = json.dumps(
            {
                "docs": [
                    {
                        "Num": 1,
                        "DocumentTitle": "Flat title",
                        "FullUrl": "https://flat.example/a",
                        "Description": "Flat description",
                        "info_context": "Flat extract",
                    }
                ]
            }
        )
        payload = {"rawData": base64.b64encode(raw.encode()).decode()}
        row = parse_search_response(payload, "FORMAT_XML")["results"][0]
        self.assertEqual(row["rank"], 1)
        self.assertEqual(row["domain"], "flat.example")
        self.assertEqual(row["extract"], "Flat extract")


if __name__ == "__main__":
    unittest.main()
