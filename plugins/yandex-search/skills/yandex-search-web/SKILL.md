---
name: yandex-search-web
description: Use when retrieving one or a few classic Yandex web SERPs interactively, including source extracts for agent research.
---
# Web search

Resolve the user objective, query, search type and region before fetching.

For rank/domain/SERP-shape work, use ordinary structured XML and prefer `GROUP_MODE_FLAT` for SEO analysis. Preserve query/search configuration in the result snapshot.

For an interactive RU research/answer task where the agent needs enough page text to judge or answer without separately opening every result, prefer optional **smart snippets / info context**: sync mode, `SEARCH_TYPE_RU`, and the Search API metadata flag implemented by `scripts/ys_request.py`. The helper uses a conservative 20-document ceiling for this mode based on pinned practitioner live evidence; this is a plugin guardrail, not the general Search API depth limit.

Smart snippets are materially more expensive than ordinary/deferred result collection. Do not enable them for rank-only/domain-only collection merely because the feature exists.

For 1–5 interactive requests, sync is normally appropriate. Use `yandex-search-batch` for larger workloads, especially position/coverage jobs where full extracts are unnecessary.

When smart snippets are returned, keep the conversational output compact: summarize/select relevant extracts and preserve the structured results rather than dumping every long `extract` into the chat.
