---
name: yandex-search-api
description: Use when building or inspecting low-level Yandex Search API v2 web-search requests and responses, including smart snippets/info context.
---
# Search API

Current classic Web Search endpoints: `/v2/web/search` and `/v2/web/searchAsync`. REST fields are CamelCase. Auth may use API-Key or IAM token; redact credentials from previews. Current service-account role is `search-api.webSearch.user`, API-key scope `yc.search-api.execute`.

## Smart snippets / info context

The shipped helper supports optional smart snippets on synchronous RU search. `build_search_request(..., smart_snippets=True)` requires `mode="sync"` and `SEARCH_TYPE_RU`, and sends `metadata.fields["x-genesis-info-context"] = "on"`.

With info context enabled, `rawData` may contain JSON rather than the classic XML/HTML body. `scripts/ys_parse.py` detects that payload and normalizes both the documented flat document shape and the practitioner-observed `rich_data` nesting to `rank`, `url`, `domain`, `title`, `snippet`, and `extract`.

The helper conservatively limits smart-snippet requests to 20 documents based on pinned practitioner live evidence from `artwist-polyakov/polyakov-claude-skills@f6a75133b3ad07e43991433c1d0a77f69c749f7b`. This 20-document guardrail is not presented as the general documented Search API depth limit.

Use smart snippets when source text materially helps an interactive answer/research task. For large position/domain batches, ordinary/deferred search is normally cheaper and more appropriate.

Image and generative Search APIs remain outside this plugin's shipped scope.

## Classic result depth

The documented result-depth ceiling is 250 results per query. The bundled request helper validates the **entire** configured result window: `requested_per_page = groupsOnPage * docsInGroup`, `window_start = page * requested_per_page`, `window_end = window_start + requested_per_page` (exclusive). `window_end == 250` is valid; `window_start >= 250` or `window_end > 250` is rejected. Do not assume the service will provide a safe partial final page beyond the documented ceiling.
