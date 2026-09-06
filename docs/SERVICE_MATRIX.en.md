# Service Matrix

[Русский](SERVICE_MATRIX.md) · [**English**](SERVICE_MATRIX.en.md)

Status reflects what this repository actually ships, not upstream product availability. Production plugins use independent SemVer.

> **Repository 1.1.0 release state:** Direct, Metrika, and Webmaster advance to `2.1.0` with mechanically enforced `yandex-ai-approval/v2`, authenticated-principal/cardinality binding, a bulk/unknown pre-transport gate, and `yandex-ai-execution/v1` receipts. Wordstat, Search, SEO, and Marketing remain on their current versions.

| Service plugin | Tier | Status | Version | Primary scope | Execution sources to evaluate |
|---|---:|---|---|---|---|
| Yandex Direct | 1 | **available** | 2.1.0 | campaigns, audit, reports, optimization, keywords, budget; approval v2; bulk/unknown `--ack-bulk`; execution receipts | bundled API helper; future MCP/app adapter |
| Yandex Metrika | 1 | **available** | 2.1.0 | reporting, conversions, ecommerce, attribution, goals, Logs API, imports; approval v2; Management unknown-scale guard; single-operation Logs/import receipts | bundled API helpers; optional MCP/app backend |
| Yandex Webmaster | 1 | **available** | 2.1.0 | indexing, diagnostics, queries, sitemaps, recrawl, links, feeds, exports; approval v2; descriptor/batch cardinality; execution receipts | bundled API helpers; optional MCP/app backend |
| Yandex Wordstat | 1 | **available** | 1.1.2 | demand, frequency, semantics, dynamics, regions, trends; candidate topic maps; 20-association cap; unambiguous seed/topic relation provenance | bundled Wordstat API within Yandex Search API v2 helpers; optional MCP/app backend |
| Yandex Search | 1 | **available** | 1.0.2 | web SERP, batch, rankings, competitors, URL-overlap clustering; 250-result depth | bundled Search API v2 helpers; optional MCP/app backend |
| Yandex SEO | X | **available** | 1.1.2 | cross-service demand, visibility, performance, gaps, cannibalization, topical architecture, internal-link planning, prioritization; hardened structural/link artifact validation | pure-data orchestration over Wordstat + Search + Webmaster + Metrika |
| Yandex Marketing | X | **available** | 1.1.0 | paid performance, KPI reconciliation, evidence roles, demand/query intelligence, landing/budget opportunities | pure-data orchestration over Direct + Metrika + Wordstat with optional Search context |
| Yandex Tracker | 2 | backlog | — | issues, queues, permissions, worklogs, boards | official API first |
| Yandex 360 | 2 | backlog | — | mail, calendar, disk, organization | official APIs first |
| Yandex Maps | 2 | backlog | — | geocoding, places, routes | product/licensing boundary required |
| AppMetrica | 3 | backlog | — | mobile analytics, cohorts, crashes, deeplinks, push | official API first |
| YandexGPT | 3 | backlog | — | generation, embeddings, summarization | optional Yandex Cloud backend |
| SpeechKit | 3 | backlog | — | speech recognition and synthesis | Yandex Cloud |

## Cross-service workflows

- `yandex-seo`: **available 1.1.2** — Wordstat + Search + Webmaster + Metrika; Topical Architecture and Internal Linking; no own transport, delegated previews only.
- `yandex-marketing`: **available 1.1.0** — Direct + Metrika + Wordstat, Search optional; `canonical` / `reconciliation_only` / `enrichment` roles are explicit.
- `yandex-ecommerce`, `yandex-mobile-growth`, `yandex-growth`: backlog ideas only.

Cross-service `.agents` entries use `authentication: ON_USE`; SEO/Marketing still own no Yandex credentials or HTTP transport. Canonical explanation: [`ARCHITECTURE.en.md`](ARCHITECTURE.en.md).

## Phase 7 — Topical Architecture & Semantic Cocoons

Phase 7 splits the semantic-cocoon workflow across the existing service boundaries:

```text
Wordstat: yandex-wordstat-topic-map
    ↓  wordstat-topic-map/v1 (candidate-only)
Search: yandex-search-clustering
    ↓  real SERP overlap / Jaccard / bridge_risk
SEO: yandex-seo-topical-architecture
    ↓  seo-topical-architecture/v1
SEO: yandex-seo-internal-linking
    ↓  preview-only link plan / audit
```

Ownership contract:

- **Wordstat** collects demand evidence and candidate topics; Wordstat associations/co-occurrence do not prove final page boundaries. Patch `1.1.1` also rejects duplicate seed identifiers and candidate self-relations.
- **Search** remains the sole owner of SERP-overlap clustering. Phase 7 does not add a competing fuzzy-text clusterer in Wordstat or SEO and does not change Search `1.0.2`.
- **SEO Topical Architecture** consumes Search-owned clusters plus optional Webmaster/Metrika/site-inventory evidence and validates page decisions, `structural_tree`, and `semantic_graph`. Patch `1.1.1` whitelist-normalizes structural nodes and prevents execution-state leakage.
- **Internal Linking** produces/audits preview artifacts only; it performs no CMS writes. Candidate-link `evidence` is list-typed.
- `OBSERVED`, `DERIVED`, `HYPOTHESIS`, and `METHODOLOGY` remain distinct. Methodology from semantic-cocoon/TGA/QBST material is not promoted to a ranking fact without independent authoritative evidence.

Both `GREENFIELD` and `EXISTING_SITE` modes are supported. When Search evidence is missing, the architecture must disclose `SERP_VALIDATION_MISSING` and page boundaries remain hypotheses.

## Repository controls

High-risk contracts map to concrete skills/helpers/tests in [`CONTRACT_MATRIX.json`](CONTRACT_MATRIX.json). The matrix is a traceability index, not semantic proof. On PR/push, the 90-day age gate blocks only a changed freshness-controlled reference; the weekly scheduled strict check evaluates the complete controlled set and synchronizes a freshness issue.

Shared runtime promotion requires not only repetition and a stable interface but also a safe installability/distribution contract for independently installed plugins; hidden repo-root dependencies are forbidden.

See [`ROADMAP.en.md`](ROADMAP.en.md) · [Русский](ROADMAP.md).
