---
name: yandex-search-batch
description: Use when planning or executing many Yandex web queries with quota, cost, sync versus deferred mode, and resumable operation handling.
---
# Batch search

1. Validate and dedupe queries.
2. Produce a **cost preview** for sync and deferred modes using dated prices.
3. Recommend sync for small interactive work and `/v2/web/searchAsync` for larger batches when appropriate.
4. Treat smart snippets/info context as an interactive sync-only capability, not a batch default. For large rank/domain/coverage jobs, prefer ordinary/deferred results unless source extracts are explicitly worth the extra cost.
5. Never auto-spend based only on available quota.
6. Deferred flow is submit → persist operation IDs → status → collect; do not poll forever. Results have a documented 12-hour retention window.

If the task needs page extracts rather than scalable SERP collection, route the relevant small subset to `yandex-search-web` after the batch has identified which results actually need deeper reading.
