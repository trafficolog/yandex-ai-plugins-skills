# Yandex Wordstat

[**Русский**](README.md) · [English](README.en.md)

Версия `1.2.0`. Workflow-first service plugin для demand research через Wordstat API в составе Yandex Search API v2: GetTop, GetDynamics, GetRegionsDistribution, GetRegionsTree, evidence-first candidate topic maps и practitioner-informed intent/missed-demand analysis.

> Phase 7 `1.1.0` добавил `yandex-wordstat-topic-map` и `wordstat-topic-map/v1`; patch `1.1.1` усиливает provenance: duplicate seed identifiers и candidate self-relations отклоняются, ownership финального SERP clustering и page architecture не меняется.

## Practitioner workflow 1.2.0

Перед расширением семантики явно зафиксируйте регион и то, что бизнес действительно продаёт/предлагает. `results` используются как основной источник расширения вокруг seed, а более шумные `associations` — как candidate discovery, не как готовый спрос.

Кандидаты классифицируются как `TARGET`, `ADJACENT`, `INFORMATIONAL`, `NAVIGATIONAL` или `AMBIGUOUS`. Для high-value и неоднозначных кластеров проверяйте intent через Yandex Search evidence; нет необходимости делать дорогую Search-проверку каждой строки большого массива. Отдельный missed-demand workflow сравнивает релевантный Wordstat demand с уже покрытой семантикой Direct, не суммируя перекрывающиеся phrase counts в фиктивный market size.

## Capability matrix

| Capability | Read | Write | MCP/App | Bundled API | File fallback |
|---|---:|---:|---:|---:|---:|
| Top requests / associations | yes | no | optional | yes | yes |
| Frequency / operator research | yes | no | optional | yes | yes |
| Dynamics, including daily | yes | no | optional | yes | yes |
| Regional distribution / region tree | yes | no | optional | yes | yes |
| Trend classification | yes | no | optional | yes | yes |
| Candidate demand/topic map | yes | no | optional | yes | yes |
| Intent / missed-demand research | yes | no | optional | yes | yes |
| Quota / cost planning | yes | no | optional | yes | yes |

## Topic Map: граница ответственности

`yandex-wordstat-topic-map` формирует `wordstat-topic-map/v1`: нормализованные query evidence, все source seeds/relations, отдельные demand observations, candidate topics и candidate relations.

Pipeline:

```text
Wordstat: yandex-wordstat-topic-map
  ↓ candidate-only wordstat-topic-map/v1
Search: yandex-search-clustering
  ↓ real SERP-overlap validation
SEO: yandex-seo-topical-architecture
  ↓ page decisions / structural_tree / semantic_graph
SEO: yandex-seo-internal-linking
  ↓ preview-only link plan / audit
```

Ключевой контракт: **Wordstat не доказывает финальные page boundaries**. Associations/co-occurrence используются только для candidate discovery. Финальный SERP clustering принадлежит `yandex-search-clustering`, а архитектура страниц — `yandex-seo-topical-architecture`.

## Interpretation contract

- `results` (nested/popular) и `associations` (similar relation) не смешиваются;
- phrase/association counts перекрываются и **не суммируются** в total market demand;
- seed/operator provenance сохраняется рядом с числами; `seeds[].seed` уникален внутри одного topic-map bundle, duplicate identifiers отклоняются;
- candidate relations должны связывать разные topic IDs; self-relations недопустимы;
- GetTop associations имеют cap `20`; ровно 20 → `associations_truncated=true` и limitation `WORDSTAT_ASSOCIATIONS_CAPPED` downstream;
- weekly/monthly operator restriction — repository compatibility policy, не заявленный официальный запрет Яндекса;
- `PERIOD_DAILY` остаётся supported path для non-`+` operators;
- topic-map confidence `LOW|MEDIUM|HIGH` — quality class, не вероятность;
- candidate relations остаются `HYPOTHESIS`, пока downstream evidence не подтверждает более сильный claim.

Большие semantic collections сохраняются в files/artifacts.

```bash
python -m unittest discover -s tests -v
```
