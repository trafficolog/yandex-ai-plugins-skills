# Changelog — Yandex Wordstat

[Русский](CHANGELOG.md) · [**English**](CHANGELOG.en.md)

## [1.2.0] — 2026-09-14

- Demand research now establishes region and the actual business offer before semantic expansion; `results` and noisier `associations` have distinct roles.
- Added practitioner intent classes `TARGET` / `ADJACENT` / `INFORMATIONAL` / `NAVIGATIONAL` / `AMBIGUOUS`; high-value and ambiguous clusters route to Search evidence verification.
- Search validation is applied selectively to important/ambiguous clusters instead of mechanically to every row in a large semantic set.
- Added a missed-demand workflow relative to current Direct semantics; overlap/no-sum rules remain, so phrase counts are not turned into invented total market demand.
- The Phase 7 candidate-only boundary remains: Wordstat does not prove final SERP clusters or page boundaries.

## [1.1.2] — 2026-09-03

- `wordstat-topic-map/v1` now normalizes query text with Unicode NFKC + casefold + whitespace folding, matching conservative cross-service SEO query joining.
- Unicode compatibility variants no longer create separate query keys; provenance, aliases, and separate demand observations remain preserved without invented summation.
- Candidate-only ownership is unchanged: Wordstat still does not claim final SERP clusters, page boundaries, or internal links.

## [1.1.1] — 2026-09-03

- Hardened `wordstat-topic-map/v1` provenance: duplicate `seeds[].seed` identifiers are rejected before phrase normalization.
- Candidate topic relations now require distinct `from_topic_id` and `to_topic_id`; self-relations are invalid.
- Candidate-only ownership is unchanged: Wordstat still does not claim final page boundaries or internal links.

## [1.1.0] — 2026-09-02

- Added `yandex-wordstat-topic-map` and the deterministic `wordstat-topic-map/v1` helper for candidate demand/topic mapping.
- Equivalent query text is deduplicated without summing overlapping demand; all source seeds, Wordstat relation types, and separate demand observations are preserved.
- Candidate topics remain `CANDIDATE` and candidate relations remain `HYPOTHESIS`; Wordstat does not claim final page boundaries.
- `WORDSTAT_ASSOCIATIONS_CAPPED` propagates into topic-map limitations.
- Final SERP clustering is explicitly delegated to `yandex-search-clustering`, while page architecture belongs to `yandex-seo-topical-architecture`.

## [1.0.2] — 2026-09-02

- Added the verified 20-association cap and explicit coverage metadata.
- Clarified weekly/monthly operator handling as repository compatibility policy while preserving `PERIOD_DAILY`.
- Propagated `WORDSTAT_ASSOCIATIONS_CAPPED` and the no-sum demand invariant.

## [1.0.1] — 2026-09-02

- Added daily Dynamics, secret-safe requests, adversarial no-sum evals and the capability matrix.

## [1.0.0] — 2026-09-01

- Initial Yandex Wordstat marketplace plugin.
