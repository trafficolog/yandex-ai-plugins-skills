---
name: yandex-wordstat-semantics
description: Use when the user needs seed expansion, a semantic core candidate set, related queries, or structured Wordstat keyword data.
---

# Wordstat semantics

Use GetTop per seed. Treat `results` as nested/popular phrases and `associations` as a distinct similar-query relation. Associations are usually **noisier** expansion **candidates**, not automatically target demand. Normalize counts but preserve relation types and full **provenance**: every merged phrase keeps all seeds that produced it.

Preserve GetTop coverage metadata. Cloud associations are capped at 20; when `coverage.associations_truncated` is true, propagate an explicit limitation such as `WORDSTAT_ASSOCIATIONS_CAPPED` and do not describe the returned association set as exhaustive semantic coverage.

Before marking a candidate commercially relevant, keep the business object/region in context and classify intent. Treat accessory/component, DIY/repair, informational, navigational and other **adjacent** demand separately from target demand when that distinction matters.

For high-priority or **ambiguous** candidates, route intent validation to Yandex Search when available. For large sets, validate representative/high-value clusters instead of searching every phrase independently.

Never sum overlapping row counts or association counts and label them **total demand**, market size, or unique searches. Keep Yandex `totalCount` per individual seed/expression instead.

Wordstat co-occurrence is candidate generation, not final SEO clustering. Use `yandex-wordstat-topic-map` when those candidates need a structured demand/topic map. Do not claim SERP overlap without a real search-results source; route final overlap clustering to `yandex-search-clustering` and final page architecture to `yandex-seo-topical-architecture`.

For large collections, store JSON/file output with filters, backend, timestamp, relation types, source seeds, intent classification and coverage limitations.

References: `references/semantics.md`, `references/topic-map.md`, `references/api-2026.md`.
