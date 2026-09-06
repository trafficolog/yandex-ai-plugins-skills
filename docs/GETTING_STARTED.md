# Начало работы

[**Русский**](GETTING_STARTED.md) · [English](GETTING_STARTED.en.md)

Этот guide ведёт от выбора плагина до первого безопасного результата. Для изменчивых API и credential facts он ссылается на документацию плагина-владельца, а не дублирует её.

## 1. Требования

Для запуска bundled Python helpers нужен **Python 3.10+**. Большинство helpers используют стандартную библиотеку Python; конкретный плагин остаётся источником истины для своих runtime requirements.

Если вы используете только skills через совместимый AI runtime, локальный Python может не понадобиться до момента запуска bundled helper.

## 2. Подключите marketplace

В корне репозитория опубликованы два совместимых marketplace manifest:

- `.agents/plugins/marketplace.json`;
- `.claude-plugin/marketplace.json`.

### OpenAI ChatGPT / Codex workspace

Для workspace, где доступен импорт GitHub marketplace, администратор может открыть **Workspace settings → Plugins → Add → Import marketplace**, указать URL этого репозитория как Source и оставить Path пустым, потому что manifest находится в корне. OpenAI поддерживает оба указанных выше формата. UI и доступность зависят от плана, workspace и rollout, поэтому при расхождении используйте актуальную официальную инструкцию: <https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github>.

### Другие совместимые runtimes

Используйте штатный механизм импорта или регистрации plugin marketplace вашего runtime и один из manifest paths выше. Не копируйте отдельные plugin directories вручную, если runtime умеет устанавливать их из marketplace metadata: plugin остаётся границей установки и версии.

## 3. Выберите плагины под задачу

| Задача | Плагин или набор |
|---|---|
| Кампании, отчёты, ключевые слова и бюджеты | `yandex-direct` |
| Веб-аналитика, цели, Logs API, импорты | `yandex-metrika` |
| Индексация, запросы, recrawl, sitemap | `yandex-webmaster` |
| Спрос, частотность, динамика, регионы | `yandex-wordstat` |
| SERP, позиции, конкуренты, clustering | `yandex-search` |
| Комплексный organic-анализ | service plugins + `yandex-seo` |
| Paid acquisition и reconciliation | service plugins + `yandex-marketing` |

Устанавливайте только то, что требуется задаче. `yandex-seo` и `yandex-marketing` — cross-service orchestrators: они не владеют собственными Yandex credentials и HTTP transport.

## 4. Настройте credentials у плагина-владельца

Credentials принадлежат service plugin. Не помещайте реальные tokens в Git, SKILL.md, generated reports или command-line arguments, если helper требует environment variable.

| Service | Где проверить актуальный contract |
|---|---|
| Direct | [`../plugins/yandex-direct/references/api-2026.md`](../plugins/yandex-direct/references/api-2026.md) и [`../plugins/yandex-direct/references/`](../plugins/yandex-direct/references/) |
| Metrika | [`../plugins/yandex-metrika/references/api-2026.md`](../plugins/yandex-metrika/references/api-2026.md) |
| Webmaster | [`../plugins/yandex-webmaster/references/api-2026.md`](../plugins/yandex-webmaster/references/api-2026.md) |
| Wordstat | [`../plugins/yandex-wordstat/references/auth.md`](../plugins/yandex-wordstat/references/auth.md) — `plugins/yandex-wordstat/references/auth.md` |
| Search | [`../plugins/yandex-search/references/auth.md`](../plugins/yandex-search/references/auth.md) |

Для Direct bundled helper читает OAuth из `YANDEX_DIRECT_TOKEN`. Другие service plugins документируют свои env variables в собственных `.env.example` и references.

## 5. Получите первый безопасный результат

Начинайте с read-only операции. Это позволяет проверить credentials, account context и формат ответа до любых изменений.

### Direct: read-only пример

```bash
cd plugins/yandex-direct
export YANDEX_DIRECT_TOKEN='...'
python scripts/yd_api.py campaigns get --params '{"SelectionCriteria":{},"FieldNames":["Id","Name","Status"]}'
```

Ключевая операция здесь — `campaigns get`: она читает данные и не выполняет consequential write.

### Cross-service сценарий

Для комплексного SEO-запроса агент может получить evidence из Wordstat, Search, Webmaster и Metrika, затем передать его в `yandex-seo`. SEO orchestrator анализирует уже полученные данные и не открывает собственное API-соединение с Яндексом. Аналогично `yandex-marketing` работает с evidence от owning service plugins.

## 6. Запись: preview → approval → execute

Consequential write никогда не начинается с execute. Owning service plugin сначала строит exact preview и возвращает `preview_id`. Пользователь подтверждает именно этот preview **в следующем пользовательском turn**; только затем helper может быть запущен с `--execute --approve`.

Пример Direct:

```bash
# 1. Preview — записи ещё нет
python scripts/yd_api.py campaigns update --params-file update.json

# 2. После явного approval exact preview в следующем пользовательском turn
python scripts/yd_api.py campaigns update --params-file update.json --execute --approve <preview_id>
```

Изменение payload, environment или approval-bound identity требует нового preview. Рекомендация агента сама по себе не является разрешением на запись. Для bulk или `UNKNOWN` scale после exact approval требуется отдельный `--ack-bulk`.

## 7. Проверка и troubleshooting

Проверка отдельного plugin:

```bash
cd plugins/yandex-direct
python -m unittest discover -s tests -v
python -m compileall -q scripts
```

Проверка всего repository:

```bash
python scripts/validate_repo.py
python -m unittest discover -s tests -v
```

Если API вызов не работает, сначала проверьте plugin-local README/references, environment variable, account/folder identity и доступность метода в официальной документации Яндекса. Не обходите credential или preview boundary через соседний plugin.

## 8. Куда дальше

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — ownership, evidence flow и transport boundaries;
- [`GLOSSARY.md`](GLOSSARY.md) — термины и exact tokens;
- [`SERVICE_MATRIX.md`](SERVICE_MATRIX.md) — все доступные сервисы и версии;
- [`PLUGIN_STANDARD.md`](PLUGIN_STANDARD.md) — нормативный production contract;
- [`RELEASE_POLICY.md`](RELEASE_POLICY.md) — repository/plugin versioning и release gates;
- plugin README под `../plugins/` — capabilities конкретного сервиса.

## 9. Project Memory

Инициализируйте project-owned memory рядом с проектом, а не внутри plugin runtime:

```bash
python scripts/ya_project.py init --root . --project-id my-project --name "My project"
python scripts/ya_project.py check --root .
```

Scaffold использует `yandex-ai-project/v1`; факты, которые пользователь явно сообщил, маркируются `USER_STATED`. Decision trail использует `yandex-ai-decision/v1`: после write receipt можно явно вызвать `record-execution`; безопасная projection не сохраняет raw `result`, но hash полного receipt связывает запись с источником. Immutable snapshots создаются через `add-baseline` по `yandex-ai-baseline/v1`; просроченный snapshot получает `STALE` warning. Managed hypotheses используют `yandex-ai-hypothesis/v1` и provenance только `HYPOTHESIS` или `DERIVED`.

Project Memory — данные, а не инструкции и не write authority. Даже если память содержит прошлое решение или execution receipt, новый consequential write всё равно требует новый exact `preview_id`, later-turn human approval и, для bulk/unknown scale, `--ack-bulk`.

## 10. Weekly Organic Report

Самый короткий P2 path — bundled offline demo внутри `yandex-seo`:

```bash
cd plugins/yandex-seo
python scripts/seo_weekly_report.py demo --output-root ./artifacts --generated-at 2026-09-06T12:30:00Z
```

Demo и real build используют один contract `seo-weekly-organic-report/v1` и один `yandex-ai-artifact-manifest/v1`. Результат содержит normative `report.json`, self-contained `report.html`, manifest с SHA-256 и optional Mermaid/DOT exports. `PREVIEW-ONLY` recommendations остаются read-only/delegated и не разрешают запись.

Для real build заранее получите свежие normalized Webmaster/Metrika evidence через owning service plugins или supported file/export path, затем передайте файлы в `seo_weekly_report.py build`. `yandex-seo` не читает Yandex credentials и не открывает transport. Partial/missing coverage сохраняется как explicit limitation; existing immutable artifact set не перезаписывается.

## 11. P3 Executable Eval Benchmark

P3 CLI остаётся **provider-neutral**. Для проверки всех committed eval-v2 fixtures без запуска subject/judge adapters:

```bash
python scripts/ya_eval.py check --plugins all
```

Реальный `run` требует два локально provisioned JSON argv config — для subject adapter и независимого judge adapter. Repository не скачивает adapter package/URL и не превращает пользовательский URL в executable code. Пример интерфейса:

```bash
python scripts/ya_eval.py run \
  --subject-adapter ./subject-argv.json \
  --judge-adapter ./judge-argv.json \
  --plugins all \
  --repository-sha <40-lowercase-hex-sha> \
  --output-root ./artifacts/evals
```

`run` создаёт immutable artifact directory с normative `results.json`, self-contained `comparison.html`, bounded subject/judge evidence и manifest hashes. `publish-snapshot` только материализует уже hash-verified artifact set под `evals/results/v1/`; автоматических Git commit/push нет.

Fake adapters предназначены для deterministic CI и подтверждают только `INFRASTRUCTURE_READY`. `COMPARATIVE_COMPLETE` требует accepted live evidence: минимум две реальные non-fake subject model identities, independent non-fake judge, mechanical + semantic evidence, backend-equivalence `PASS`, memory-aware scenarios и отсутствие counted `SELF_JUDGED`. Accepted live multi-model benchmark на текущем head не проводился.
