# Журнал изменений — Yandex SEO

[**Русский**](CHANGELOG.md) · [English](CHANGELOG.en.md)

## [1.2.0] — 2026-09-06

### Weekly Organic Report

- Добавлен `yandex-seo-weekly-report` и нормативный `seo-weekly-organic-report/v1` для нормализованных Webmaster/Metrika evidence, exact current/comparison periods, explicit coverage/provenance/limitations и delegated findings.
- Добавлен `yandex-ai-artifact-manifest/v1`: managed relative paths, roles/media types, SHA-256 и immutable snapshot semantics с exact idempotent replay без overwrite конфликтующего artifact set.
- `report.html` self-contained: restrictive CSP, escaped source/user text, без CDN, remote fonts, analytics и network fetch; `report.json` остаётся source of truth.
- Mermaid/DOT exports deterministic и создаются только при наличии реальных source structures.
- Добавлены `demo`/`build` CLI modes и sanitized offline fixture; demo не требует credentials или сети.
- Optional P1 context ограничен project identity + active `USER_STATED` facts; decisions/hypotheses/stale baselines не становятся fresh evidence.
- Все delegated recommendations имеют `PREVIEW-ONLY`; SEO остаётся transport-free/read-only и не расширяет P0 approval/write authority.

## [1.1.2] — 2026-09-03

- Empirical boundary-changing decisions (`CREATE|MERGE|SPLIT|REDIRECT|SECTION_ONLY|BRIDGE|NO_PAGE`) теперь требуют Search-owned provenance; `MERGE`/`REDIRECT` дополнительно требуют evidence существующего URL/страницы.
- `coverage.search=PARTIAL` теперь явно добавляет `SERP_VALIDATION_PARTIAL`; Search cluster ingress валидируется и автоматически переносит bridge/source limitations downstream.
- `METHODOLOGY` стал first-class qualitative kind в SEO Evidence Bundle, но не может маскироваться под quantitative metric evidence.
- Topical Architecture различает неоценённые `link_plan`/`audits` (`null`) и реально выполненные пустые результаты через explicit attachment helpers.
- Internal-link audit считает orphan по отсутствию inbound links, сохраняет и флагирует duplicate links, а rootless `BRIDGE` без inbound link отмечает как orphan/broken bridge. Explicit `ROOT` и legacy parentless node без `page_role` остаются exempt; explicit non-root roles проверяются на orphan. Self-links публикуются как `SELF_LINK` и не участвуют в valid/inbound reachability counts.
- Transport-free, preview-only и Search-owned clustering boundaries не меняются.

## [1.1.1] — 2026-09-03

- `structural_tree.nodes` теперь нормализуются через explicit field whitelist; caller `decision/status/write/execution_id` не попадают в transport-free structural artifact.
- Candidate-link `evidence` в `yandex-seo-internal-linking` теперь обязан быть list; scalar/object payload отклоняется до preview serialization.
- Topical Architecture ownership, Search-owned SERP clustering и preview-only/no-CMS-write boundary не меняются.

## [1.1.0] — 2026-09-02

- Добавлен `yandex-seo-topical-architecture` и schema `seo-topical-architecture/v1` для `GREENFIELD` / `EXISTING_SITE` architecture workflows.
- `structural_tree` и `semantic_graph` разделены: canonical structural parent остаётся единственным, semantic relations могут быть множественными.
- Добавлены page decisions `PRESERVE|CREATE|EXPAND|MERGE|SPLIT|REDIRECT|SECTION_ONLY|BRIDGE|NO_PAGE|MANUAL_REVIEW`.
- Evidence classes `OBSERVED|DERIVED|HYPOTHESIS|METHODOLOGY` и confidence `LOW|MEDIUM|HIGH` валидируются явно; methodology не повышается до ranking fact.
- При отсутствии Search evidence добавляется `SERP_VALIDATION_MISSING`; Search остаётся владельцем SERP-overlap clustering.
- Добавлен `yandex-seo-internal-linking`: preview-only link plans и deterministic audit (`ORPHAN_PAGE`, `STRUCTURAL_PARENT_LINK_MISSING`, `MISSING_JUSTIFIED_LINK`, `UNKNOWN_LINK_ENDPOINT`).
- SEO остаётся transport-free/read-only и не выполняет CMS writes.

## [1.0.1] — 2026-09-02

- Required Evidence Bundle context (`site`, `analysis_period`, `search_region_id`).
- Добавлены explicit period/geography/Search-config/device alignment states.
- Missing Webmaster impressions не считаются measured zero; quality/coverage limitations propagируются.
- Delegated previews остаются non-writing orchestration.

## [1.0.0]

- Первый cross-service SEO Evidence Bundle, findings и delegated-action workflows.
