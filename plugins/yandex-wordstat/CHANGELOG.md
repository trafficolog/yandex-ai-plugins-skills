# Журнал изменений — Yandex Wordstat

[**Русский**](CHANGELOG.md) · [English](CHANGELOG.en.md)

## [1.2.0] — 2026-09-14

- Demand research теперь фиксирует регион и фактический бизнес-offer до semantic expansion; `results` и более шумные `associations` получают разные роли.
- Добавлена practitioner intent-классификация `TARGET` / `ADJACENT` / `INFORMATIONAL` / `NAVIGATIONAL` / `AMBIGUOUS`; high-value и ambiguous clusters маршрутизируются в Search evidence verification.
- Search validation применяется выборочно к важным/неоднозначным кластерам, а не механически к каждой строке большого semantic set.
- Добавлен missed-demand workflow относительно текущей Direct semantics; overlap/no-sum contract сохраняется, поэтому phrase counts не превращаются в выдуманный total market demand.
- Candidate-only boundary Phase 7 сохранён: Wordstat не доказывает final SERP clusters или page boundaries.

## [1.1.2] — 2026-09-03

- `wordstat-topic-map/v1` теперь нормализует query text через Unicode NFKC + casefold + whitespace folding, совпадая с conservative cross-service query joining в SEO.
- Unicode compatibility variants больше не создают отдельные query keys; provenance, aliases и отдельные demand observations сохраняются без invented summation.
- Candidate-only ownership не меняется: Wordstat по-прежнему не утверждает финальные SERP clusters, page boundaries или internal links.

## [1.1.1] — 2026-09-03

- Усилен provenance contract `wordstat-topic-map/v1`: duplicate `seeds[].seed` identifiers отклоняются до нормализации phrase records.
- Candidate topic relations теперь требуют разные `from_topic_id` и `to_topic_id`; self-relations недопустимы.
- Candidate-only ownership не меняется: Wordstat по-прежнему не утверждает финальные page boundaries или internal links.

## [1.1.0] — 2026-09-02

- Добавлен `yandex-wordstat-topic-map` и deterministic helper `wordstat-topic-map/v1` для candidate demand/topic mapping.
- Equivalent query text дедуплицируется без суммирования overlapping demand; сохраняются все source seeds, Wordstat relation types и отдельные demand observations.
- Candidate topics остаются `CANDIDATE`, candidate relations — `HYPOTHESIS`; Wordstat не утверждает финальные page boundaries.
- `WORDSTAT_ASSOCIATIONS_CAPPED` propagates в topic-map limitations.
- Final SERP clustering явно делегирован `yandex-search-clustering`, а page architecture — `yandex-seo-topical-architecture`.

## [1.0.2] — 2026-09-02

- Добавлен verified 20-association cap и explicit coverage metadata.
- Weekly/monthly operator handling уточнён как repository compatibility guard, `PERIOD_DAILY` сохранён.
- Semantics guidance распространяет `WORDSTAT_ASSOCIATIONS_CAPPED` и no-sum demand invariant.

## [1.0.1] — 2026-09-02

- Добавлен daily Dynamics, secret-safe requests, adversarial no-sum eval и capability matrix.

## [1.0.0] — 2026-09-01

- Первый Yandex Wordstat marketplace plugin.
