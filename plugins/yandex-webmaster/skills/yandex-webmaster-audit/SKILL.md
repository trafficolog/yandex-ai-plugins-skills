---
name: yandex-webmaster-audit
description: Use when auditing SEO health, diagnostics, indexing, queries, sitemaps or links in Yandex Webmaster.
---

# Yandex Webmaster audit

Read `../../references/audit-framework.md`, `../../references/indexing.md`, `../../references/queries.md` and `../../references/safety.md`.

Use evidence-first `PASS / ISSUE / REVIEW / N/A`. Resolve verification/data availability first and capture a current **host summary** before drilling down. Then triage diagnostics → indexing/search inclusion → query losses → broken/internal/external links → sitemap evidence. Preserve Yandex severity/state and exact periods/filters.

Treat diagnostics, quotas and operational status as live/volatile evidence when they affect the next action. Historical/exported evidence is useful for trend analysis but must not be presented as current state without refresh.

For each finding provide evidence, likely impact, confidence and a next action. When proposing a fix, separate the observation from the likely cause and state how the cause can be verified. Do not convert a recommendation into recrawl/sitemap/feed writes without a separate preview and approval.

Recrawl belongs at the end of triage: propose it only when a concrete URL was changed/fixed or page-level evidence indicates a fresh fetch is relevant. Recrawl is not a substitute for diagnosing exclusion, canonicalization, content quality or query-demand issues.
