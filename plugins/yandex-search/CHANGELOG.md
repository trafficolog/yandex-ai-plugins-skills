# Журнал изменений — Yandex Search

[**Русский**](CHANGELOG.md) · [English](CHANGELOG.en.md)

> `DOCS 1.0.0` добавил bilingual docs; SemVer плагина не изменён.

## [1.1.0] — 2026-09-14

- Добавлен опциональный bounded smart-snippet/info-context mode для синхронного semantic research: `SEARCH_TYPE_RU` + `metadata.fields["x-genesis-info-context"]="on"`.
- JSON smart-snippet response нормализуется отдельно от обычного XML SERP и сохраняет `rank`, `url`, `domain`, `title`, `snippet`, `extract`.
- Обычный sync/deferred SERP остаётся default для rankings, batch collection, snapshots и clustering; новый режим не меняет существующий 250-result ordinary SERP depth contract.
- Консервативный небольшой smart-snippet result set документирован как practitioner/repository guardrail, а не как общий официальный Search API limit.

## [1.0.2] — 2026-09-02

- Добавлен strict 250-result complete-window contract.
- Snapshot получил depth metadata и rank ceiling guard.
- Сохранены absolute-rank и conservative tracking-URL identity semantics 1.0.1.

## [1.0.1] — 2026-09-02

- Исправлены absolute ranks across pages, `fix_typo_mode` validation и adversarial bridge-risk evals.

## [1.0.0] — 2026-09-01

- Первый Yandex Search plugin.
