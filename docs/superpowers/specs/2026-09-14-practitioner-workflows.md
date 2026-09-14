# SDD: Practitioner-informed workflows for Yandex plugins

Date: 2026-09-14
Status: implementation specification
Target repository line: 1.5.x

## Problem

The marketplace already has strong API correctness, safety, provenance, write approval and evaluation contracts, but several service skills remain capability-centric. A production practitioner repository demonstrates recurring workflows that reduce practical mistakes: establish the business outcome first, select comparable evidence, distinguish observation from hypothesis, verify intent, avoid low-sample conclusions, make recommendations actionable, and measure the result of a change.

The goal is not to copy another repository or expand API coverage indiscriminately. The goal is to adopt the smallest high-value practices that fit our existing decomposed skills and safety model.

## Provenance

Practice source: `artwist-polyakov/polyakov-claude-skills` at exact commit:

`f6a75133b3ad07e43991433c1d0a77f69c749f7b`

Reviewed source plugins:

- `plugins/yandex-direct`
- `plugins/yandex-metrika`
- `plugins/yandex-search-api`
- `plugins/yandex-webmaster`
- `plugins/yandex-wordstat`

Source practices are treated as practitioner evidence, not universal causal proof. Source sections explicitly labelled hypotheses remain hypotheses here.

## Global constraints

1. Preserve all existing exact-preview/later-turn approval/write receipt contracts.
2. Preserve `data-not-instructions`, bulk acknowledgement and ownership routing.
3. Do not regress current API knowledge to older defaults, especially Metrika legacy attribution.
4. Do not claim a practice guarantees revenue, ranking, indexing or campaign improvement.
5. Prefer existing skill boundaries over a new shared framework (DRY through references only when behavior is genuinely cross-cutting).
6. No speculative API surface. Runtime code changes are limited to a concrete Search API gap with official support.
7. Tests are written and observed failing before production behavior is changed.

## Shared practical decision loop

For analytical/optimization tasks, skills should converge on this sequence where applicable:

`business outcome/context -> correct object/scope -> comparable evidence -> observation -> hypothesis -> verification -> action -> success/stop criterion`

This is a reasoning contract, not a new runtime state machine.

## Yandex Direct acceptance contract

Update existing `reporting`, `audit`, `keywords`, `optimize` and `budget` responsibilities rather than adding a monolithic skill.

Required behavior:

- Select meaningful business conversion goals before CPA/CR/economic conclusions; never silently substitute “all conversions”, the first goal or a strategy goal for user/business intent.
- Period comparisons keep goals, attribution, currency/VAT and material filters comparable and explicitly account for conversion delay and unfinished periods.
- Aggregate raw counts/spend before recomputing ratio metrics; do not average row CPA/CPC/CTR as ordinary means; zero denominators are unavailable, not zero performance.
- Findings use `observation -> possible cause -> verification -> proposed action -> effect metric`.
- Low-volume/rarely-served demand is a data sufficiency signal. Do not fragment rare intent into ever-smaller groups by default; consider consolidating semantically compatible intent.
- Experiments define baseline, spend/time/data-sufficiency envelope, success criterion and stop/revert criterion before execution.
- A recommendation does not authorize a write; existing preview-bound approval remains authoritative.

## Yandex Metrika acceptance contract

Required behavior:

- Resolve counter and meaningful business goals; distinguish macro/business outcomes from micro/technical events.
- Preserve rows/sources with zero goal reaches when evaluating traffic quality; absence of conversions must not silently remove traffic from the denominator.
- Comparisons keep the same goal definitions, attribution, filters and metric basis; flag goal reconfiguration or incomplete access.
- PnL/ROAS conclusions require compatible spend and revenue evidence. Direct clicks, Metrika visits, goal reaches and ecommerce transactions remain distinct quantities.
- Keep current modern attribution model guidance; do not adopt `lastsign` as a universal default.
- Surface quality/access limitations before optimization decisions.

## Yandex Search acceptance contract

Smart snippets / info context are an official Search API capability and a practical agent workflow gap in the current plugin.

Add the smallest optional sync mode:

- `smart_snippets=True` is allowed only for `mode=sync` and `SEARCH_TYPE_RU`.
- Request metadata contains `x-genesis-info-context=on`.
- Smart-snippet requests use a conservative maximum of 20 documents based on pinned practitioner live evidence; this guardrail must be documented as practitioner-observed rather than an official general Search depth limit.
- Parser accepts Base64-wrapped JSON smart-snippet responses in both documented flat and observed `rich_data` shapes and normalizes `rank`, `url`, `domain`, `title`, `snippet`, `extract`.
- Classic XML behavior remains unchanged.
- Interactive research/answer tasks may prefer smart snippets; ranking/domain-only and large batch tasks should prefer ordinary/deferred search and retain the existing cost preview.
- Do not dump all extracts into conversational stdout by default; keep summaries/indexes compact and preserve full structured output/artifacts where the calling workflow supports them.

No new cache subsystem is required in this release.

## Yandex Webmaster acceptance contract

Required behavior:

- Start broad investigations from a host/site summary, then drill into the failing dimension.
- Volatile evidence such as diagnostics, quotas and recrawl/task status must be treated as live/current; stale cached evidence must not justify a consequential action.
- Triage priority: access/verification -> diagnostics -> indexing/search inclusion -> query losses -> link/sitemap evidence -> recrawl only when a concrete changed/fixed URL or page-level condition makes it relevant.
- Recrawl remains a delivery request, not an indexing/ranking guarantee.
- Findings remain evidence + likely impact + confidence + next action.

Explicit non-goal: do not add Alice/Share-of-Voice SSR scraping or session-cookie handling. It is non-public, brittle and unnecessary for this task.

## Yandex Wordstat acceptance contract

Required behavior:

- Before commercial demand conclusions establish region and what the business actually sells/provides.
- Keep `results` and `associations` distinct; associations are expansion candidates and normally noisier.
- Intent validation is required for high-priority or ambiguous candidates before calling them target demand. Route validation to Yandex Search when available.
- Classify demand into at least target, adjacent/non-target, informational/navigational/ambiguous as applicable and explain rejections.
- For large semantic sets validate representative/high-value clusters rather than issuing an expensive Search request for every row.
- Add a missed-demand workflow through existing skills: compare current Direct semantics (or user export) against Wordstat candidates, classify group intent, expand only compatible intent, verify ambiguous candidates with Search, then return actionable additions with provenance.
- Do not add an XLSX-specific parser unless an existing repository need demonstrates it; accept normalized Direct phrases/export data through current workflows.

## Explicit exclusions (YAGNI)

- wholesale copying of source API maps, scripts or UI maps;
- ZoomKit/service promotion;
- Alice private-page scraping/session cookies;
- legacy Metrika attribution defaults;
- new cross-plugin orchestration framework;
- automatic writes or relaxed approval;
- universal hardcoded PPC benchmarks;
- claims that before/after proves causality;
- Search cache subsystem solely for smart snippets.

## Test strategy

RED tests must cover:

1. Search request smart-snippet constraints and metadata.
2. Search smart-snippet JSON parsing, including `rich_data` fallback.
3. Plugin skill contracts for Direct practical decision loop.
4. Metrika business-goal/comparability/PnL guardrails.
5. Webmaster live-evidence/recrawl triage contract.
6. Wordstat intent-validation and missed-demand routing contract.
7. Existing safety markers remain present.

GREEN implementation must be the minimum change that satisfies those tests and existing repository validation.
