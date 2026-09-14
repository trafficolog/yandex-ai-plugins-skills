---
name: yandex-search-research
description: Use when running a multi-query Yandex SERP research workflow for competitors, intent, rankings, clustering, or evidence-backed answers.
---
# SERP research

Define objective, queries, region/search type and top-K before choosing the transport mode.

For competitor/ranking/clustering work, run `yandex-search-batch` cost preview first and collect compatible `GROUP_MODE_FLAT` snapshots. If demand weighting is required, join later with Wordstat instead of calling unweighted SERP presence demand or market share.

For a small set of RU queries where the research question requires judging page meaning or citing source content, use `yandex-search-web` with optional smart snippets/info context after the candidate set is known. Do not pay the smart-snippet premium for every query when ordinary SERP evidence is sufficient.

Keep a practical evidence chain: objective → query/region → collected SERP evidence → observed pattern → interpretation/uncertainty → next action. Search-result presence alone does not establish demand; route demand magnitude to Wordstat.
