# Changelog — Yandex Search

[Русский](CHANGELOG.md) · [**English**](CHANGELOG.en.md)

> `DOCS 1.0.0` added bilingual docs; plugin SemVer is unchanged.

## [1.1.0] — 2026-09-14

- Added an optional bounded smart-snippet/info-context mode for synchronous semantic research: `SEARCH_TYPE_RU` plus `metadata.fields["x-genesis-info-context"]="on"`.
- The JSON smart-snippet response is normalized separately from ordinary XML SERP and preserves `rank`, `url`, `domain`, `title`, `snippet`, and `extract`.
- Ordinary sync/deferred SERP remains the default for rankings, batch collection, snapshots, and clustering; the new mode does not change the existing 250-result ordinary SERP depth contract.
- The conservative small smart-snippet result set is documented as a practitioner/repository guardrail, not as a general official Search API limit.

## [1.0.2] — 2026-09-02

- Added the strict 250-result complete-window contract.
- Added snapshot depth metadata and the rank ceiling guard.
- Preserved 1.0.1 absolute-rank and conservative tracking-URL identity semantics.

## [1.0.1] — 2026-09-02

- Corrected absolute ranks across pages, `fix_typo_mode` validation and adversarial bridge-risk evals.

## [1.0.0] — 2026-09-01

- Initial Yandex Search plugin.
