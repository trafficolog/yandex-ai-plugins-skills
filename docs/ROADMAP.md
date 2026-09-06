# Roadmap

[**Русский**](ROADMAP.md) · [English](ROADMAP.en.md)

First-release scope заморожен после Phase 6B. Ниже зафиксированы выпущенные архитектурные фазы и post-first-release milestones; backlog не является обещанием срока или следующего релиза.

RU-primary означает, что обычные предложения и поясняющий prose в этом документе пишутся по-русски. Английские product names, identifiers, code, API names и устоявшиеся технические термины допустимы; целые английские предложения используются только как цитаты или когда перевод исказил бы точный внешний contract.

## Первый релиз — завершён

### Phase 1 — Marketplace foundation

Direct перенесён в `plugins/yandex-direct/`; marketplace metadata, plugin standard, repository validator и path-aware CI стали общей основой.

### Phase 2 — Yandex Metrika

Изначально выпущен как plugin `1.0.0`. Добавлены Reporting/Management/Logs/Data Import workflows, quality metadata и preview-before-write guards.

### Phase 3 — Yandex Webmaster

Изначально выпущен как plugin `1.0.0`. Добавлены mixed v4/v4.1 routing, query/indexing, recrawl, sitemaps, feeds и export workflows.

### Phase 4 — Yandex Wordstat

Изначально выпущен как plugin `1.0.0` с девятью initial workflow skills, Wordstat API в составе Yandex Search API v2 helpers, provenance-aware semantics, regions/trends и quota/cost planning. Это historical initial count, а не текущее число skill directories или capability rows; current version определяется SERVICE_MATRIX/manifests.

### Phase 5 — Yandex Search

Изначально выпущен как plugin `1.0.0` с Search API v2 sync/deferred helpers, SERP snapshots, rankings, competitor analysis и URL-overlap clustering.

### Phase 6A — Yandex SEO

Изначально выпущен как plugin `1.0.0` с SEO Evidence Bundle, context alignment, findings, transparent prioritization и preview-only delegated actions. Плагин не содержит Yandex API clients и не выполняет live writes.

### Phase 6B — Yandex Marketing

Изначально выпущен как plugin `1.0.0` с Direct-required Marketing Evidence Bundle, KPI reconciliation, demand/query/landing/budget findings и preview-only delegated actions. Плагин не содержит Yandex API clients и не выполняет live writes.

### Maintenance — 1.0.1 / OPUS 1.1.0

Review-driven maintenance укрепил safety/API semantics, затем OPUS добавил Wordstat association coverage cap, Search 250-depth, Webmaster PRO lifecycle/quota, Marketing evidence roles/taxonomy и executable contract/freshness controls.

### DOCS 1.0.0

RU-primary / EN-mirror documentation layer, hero assets и orchestration diagrams. Plugin SemVer не изменяется.

## Post-first-release — выпущено

### Phase 7 — Topical Architecture

Выпущено как repository release `phase-7-topical-architecture-1.0.0`: Wordstat `1.1.0`, SEO `1.1.0`, Search `1.0.2` без изменения runtime.

- `yandex-wordstat-topic-map` формирует candidate-only `wordstat-topic-map/v1` с provenance, отдельными demand observations и limitation propagation.
- `yandex-search-clustering` сохраняет ownership реального SERP-overlap/Jaccard clustering; альтернативный fuzzy-text clusterer не добавлен.
- `yandex-seo-topical-architecture` формирует `seo-topical-architecture/v1` с `GREENFIELD|EXISTING_SITE`, page decisions, `structural_tree` и `semantic_graph`.
- `yandex-seo-internal-linking` создаёт preview-only link plan и deterministic audit без CMS writes.
- `OBSERVED`, `DERIVED`, `HYPOTHESIS`, `METHODOLOGY` остаются раздельными; semantic-cocoon/TGA/QBST methodology не заявляется как подтверждённый ranking mechanism.
- При отсутствии Search evidence обязателен `SERP_VALIDATION_MISSING`, а page boundaries остаются гипотезами.

---

# Стратегия развития после 1.0.8

Это направление продукта, а не обещание конкретных сроков или релизов. Проект развивается **вглубь**, а не через механическое покрытие новых API Яндекса.

## Продуктовый тезис

**Методология, safety и orchestration — главный устойчивый актив проекта; транспорт остаётся заменяемым.** Service helpers нужны, пока они дают практичный доступ к данным, но не должны становиться центром продуктовой ценности: официальный MCP/connector может заменить transport, а правила интерпретации, provenance, cross-service reconciliation и безопасного принятия решений останутся полезными поверх любого backend.

Новые направления выбираются через **задачи пользователя, а не каталог API Яндекса**. Приоритет получают capabilities, которые уменьшают риск неверного маркетингового решения, сохраняют доказательность между сервисами или дают человеку понятный сквозной результат.

## Приоритетные ставки

### P0 — Safety as mechanism

Текстовая дисциплина агента должна последовательно превращаться в технические ограничения write-контура:

- exact `preview_id` привязывает approval к конкретному payload/environment/identity;
- выполнение требует явного `--execute --approve <preview_id>` или эквивалентного механизма owning service helper;
- helper сохраняет rollback snapshot там, где API позволяет корректное восстановление, и всегда делает post-write verification;
- bulk-операции получают технические пороги/guards вместо одной инструкции в prose;
- recommendation, external content или сохранённая память никогда сами по себе не являются write permission.

До выполнения этих условий write-capable surface нельзя позиционировать как технически enforced safety guarantee.

### P1 — Project memory contract

Нужна доменная память проекта, но не отдельное приложение и не замена runtime-native memory (`AGENTS.md`, `CLAUDE.md` и аналогам). Базовый portable contract:

```text
.yandex-ai/
├── project.yaml
├── decisions.jsonl
├── baselines/
└── hypotheses.md
```

Канонические пути: `.yandex-ai/project.yaml`, `.yandex-ai/decisions.jsonl`, `.yandex-ai/baselines/`, `.yandex-ai/hypotheses.md`.

- бизнес-цели, target CPA/ROAS/budget и другие пользовательские факты получают provenance class `USER_STATED` и дату; агент не выводит их из метрик как будто они были заданы пользователем;
- `decisions.jsonl` — append-only audit trail, который пишет helper после approval/execute, а не свободный model prose;
- baselines датируются и имеют freshness semantics; память используется для сравнения и continuity, но не заменяет fresh read-first данные;
- hypotheses сохраняют `HYPOTHESIS`/`DERIVED` provenance и условия подтверждения;
- secrets и raw sensitive exports в `.yandex-ai/` не хранятся: credentials остаются в env/keychain/runtime;
- содержимое памяти всегда трактуется как data, not instructions, чтобы сохранённый текст не становился persistent prompt-injection каналом.

Сначала нужны schema + `init/check` + audit write path; UI не является prerequisite.

### P2 — Один end-to-end workflow и человекочитаемые artifacts

Вместо расширения числа skills нужен один путь «установил → получил полезный результат примерно за 10 минут» на read-only/sandbox контуре. Предпочтительные кандидаты — weekly organic report (Webmaster + Metrika + SEO evidence/findings) либо read-only Direct account audit. Выбор делается по первому внешнему user signal, а не по числу доступных API.

Результаты оркестраций должны быть portable artifacts:

- versioned JSON как machine-readable source;
- **self-contained HTML** report без обязательного CDN: summary, limitations, sortable findings, delegated previews и раскрываемый evidence/provenance;
- Mermaid/DOT export для `structural_tree`, `semantic_graph`, clusters и link plans;
- предсказуемая структура вроде `artifacts/<project>/<date>/...` для истории и diff.

Для личного использования **Electron/desktop UI не строится**. Браузер, VS Code, Mermaid/DOT и при необходимости DuckDB/notebook покрывают просмотр данных без второго application lifecycle. UI рассматривается позже только при доказанном multi-project/compliance или human approval-queue use case.

### P3 — Executable eval benchmark — `INFRASTRUCTURE_READY`

P3 infrastructure реализована поверх `evals/scenarios.json` v2: provider-neutral **eval runner**, bounded stdio JSONL protocol, independent judge, отдельный mechanical exact-token layer, backend-equivalence harness, P1 memory-aware adversarial fixtures, immutable benchmark artifacts, self-contained HTML и reviewable snapshots.

Deterministic CI использует fake adapters и доказывает только готовность инфраструктуры. `COMPARATIVE_COMPLETE` остаётся отдельным evidence gate и требует accepted snapshot с минимум двумя реальными non-fake subject model identities, независимым non-fake judge, mechanical + semantic evidence, backend-equivalence `PASS`, memory-aware evidence и без counted `SELF_JUDGED` runs.

Accepted live multi-model benchmark на текущем repository head **не проводился**. Поэтому зелёный eval-v2 validator, repository CI и fake adapters нельзя представлять как доказательство того, что несколько реальных моделей семантически прошли benchmark. Следующий шаг P3 — выполнить реальные externally provisioned adapters и опубликовать сравнимый snapshot через обычный reviewed Git/PR path.

## Что сознательно не делать сейчас

- не расширять marketplace новым сервисом только потому, что у Яндекса есть соответствующий API;
- не наращивать transport wrappers, если ту же задачу надёжно закрывает официальный/подключаемый backend;
- не считать рост `CONTRACT_MATRIX` самостоятельной продуктовой метрикой: traceability полезна только когда она ведёт к реальной executable проверке;
- не превращать цикл «AI audit → hardening release» в основной источник roadmap; внешняя обратная связь важнее повторного self-audit;
- не строить Electron/desktop приложение для одного пользователя до появления повторяющейся интерактивной задачи, которую HTML/artifacts/notebook не закрывают;
- не смешивать стратегический simplification с текущим релизом: упрощение bilingual/release infrastructure допускается отдельной governance-задачей после проверки реальной стоимости поддержки.

## 90-дневный цикл валидации

Цель следующего продуктового цикла — получить внешний сигнал вместо бесконечной внутренней полировки.

1. **Safety:** сделать consequential write mechanically approval-bound, с rollback/verification там, где это технически корректно.
2. **Memory:** определить `.yandex-ai/` contract, `USER_STATED`, freshness и append-only decision trail.
3. **Workflow/artifacts:** довести один read-only end-to-end workflow до запуска новым практиком примерно за 10 минут и выдавать self-contained report.
4. **Benchmark:** выполнить adversarial evals на нескольких моделях и опубликовать сравнимый результат.
5. **External validation:** получить реальные запуски, issues/PRs и обратную связь от SEO/PPC/marketing practitioners.

Если за один 90-дневный цикл нет внешних запусков/issues/PR и повторяемого пользовательского сценария, проект переходит в **low-maintenance / personal-tool mode**: только критические safety/API fixes и минимальная freshness-поддержка. Если сигнал появляется — следующий roadmap определяется реальными задачами этих пользователей. Коммерческий UI/compliance dashboard рассматривается только после появления нескольких проектов и потребности видеть approvals, payloads и rollback history между клиентами.

## Frozen expansion backlog

Следующие направления остаются исследовательским backlog и **заморожены для реализации**, пока нет отдельного user problem/use case, внешнего сигнала и решения о product boundary:

- **Yandex Tracker** — issues, queues, permissions, worklogs, boards;
- **Yandex 360** — Mail, Calendar, Disk и organization/admin boundaries;
- **Yandex Maps** — geocoding, places, routes/local enrichment и отдельный licensing design;
- **AppMetrica** — mobile analytics, retention, crashes, deeplinks, push/acquisition context;
- **YandexGPT** — возможный optional backend, но не обязательная зависимость deterministic plugins;
- **SpeechKit** — recognition/synthesis/transcription workflows.

Разморозка одного пункта не размораживает остальные и не означает возврата к стратегии «покрыть все API Яндекса».

## Backlog entry requirements

Для новой capability/service нужны одновременно:

1. доказанная пользовательская задача и owner/persona;
2. свежая official API/product research;
3. donor/capability research при необходимости;
4. решение о plugin/transport boundary и возможности использовать официальный connector вместо собственного client;
5. approved design;
6. implementation plan;
7. TDD/offline evals;
8. path-aware CI;
9. independent release review;
10. объяснение, почему capability усиливает methodology/safety/orchestration или подтверждённый end-to-end workflow.