# Yandex Search

[**Русский**](README.md) · [English](README.en.md)

Версия `1.1.0`. SEO-first service plugin для classic web SERP retrieval, snapshots, rankings, competitor presence, URL-overlap clustering, sync/deferred Search API v2 workflows и bounded semantic research через smart snippets / info context.

> `DOCS 1.0.0` меняет только документацию.

## Smart snippets / info context 1.1.0

Для небольшого интерактивного исследования смысла страниц sync request может включить `metadata.fields["x-genesis-info-context"]="on"` при `search_type=SEARCH_TYPE_RU`. Такой ответ приходит как JSON и нормализуется отдельно от обычного XML SERP в `rank`, `url`, `domain`, `title`, `snippet`, `extract`.

Режим опциональный: обычный sync/deferred SERP остаётся default для позиций, массового сбора, snapshots и clustering. Консервативный практический guard ограничивает smart-snippet research небольшим числом документов; это repository/practitioner guardrail, а не заявленный общий официальный лимит Search API.

## Capability matrix

| Capability | Read | Write | MCP/App | Bundled API | File fallback |
|---|---:|---:|---:|---:|---:|
| Interactive web SERP retrieval | yes | no | optional | yes | yes |
| Bounded smart snippets / info context | yes | no | optional | yes | yes |
| Deferred / batch search | yes | no | optional | yes | yes |
| SERP snapshot normalization | yes | no | optional | yes | yes |
| Absolute rank / snapshot comparison | yes | no | optional | yes | yes |
| Competitor presence analysis | yes | no | optional | yes | yes |
| URL-overlap clustering / bridge-risk analysis | yes | no | optional | yes | yes |
| Raw Search API request construction | preview | no | optional | yes | yes |

## 250-result depth contract

`requested_per_page = groups_on_page * docs_in_group`; `window_start = page * requested_per_page`; `window_end = window_start + requested_per_page`.

Window с `end == 250` допустим. `start >= 250` или `end > 250` отклоняется — helper не полагается на undocumented partial truncation. Snapshot сохраняет `max_supported_results`, `window_start`, `window_end`, `reaches_result_ceiling`; rank >250 невозможен.

SERP presence не называется market share. URL identity остаётся conservative: tracking params могут отделяться, functional params сохраняют различие страниц.

```bash
python -m unittest discover -s tests -v
```
