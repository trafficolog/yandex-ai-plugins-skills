# Журнал изменений

[**Русский**](CHANGELOG.md) · [English](CHANGELOG.en.md)

Все значимые изменения уровня репозитория фиксируются здесь. Плагины используют независимый SemVer и имеют собственные changelog-файлы.

## [1.2.0] — 2026-09-06

P1 Project Memory — repository-only release с project-owned domain memory, которая сохраняет контекст между отдельными запусками, но не становится памятью AI runtime и не расширяет write authority.

### Изменено

- Добавлен zero-third-party-dependency CLI `scripts/ya_project.py` и канонический `.yandex-ai/` scaffold: `project.yaml`, `decisions.jsonl`, `baselines/`, `hypotheses.md`.
- `yandex-ai-project/v1` хранит project identity и `USER_STATED` facts; supersession сохраняет историю и не допускает две active values одного logical key.
- `record-execution` проецирует P0 `yandex-ai-execution/v1` в chained `yandex-ai-decision/v1`: raw `result` не сохраняется, а `receipt_sha256` считается по полному исходному receipt.
- `add-baseline` создаёт immutable `yandex-ai-baseline/v1` snapshots; exact `fresh_until` остаётся `FRESH`, после границы snapshot становится `STALE` warning без автоматической mutation.
- `yandex-ai-hypothesis/v1` управляет только explicit fenced JSON records с provenance `HYPOTHESIS` / `DERIVED`; unmanaged Markdown и prompt-like строки остаются инертными данными.
- Restricted YAML parser, atomic project writes, decision hash-chain, duplicate guards, future timestamp guards и secret-like key heuristic реализованы без сторонних Python packages.
- Repository validator и `CONTRACT_MATRIX.json` получили четыре P1 infrastructure contracts; ARCHITECTURE, GETTING_STARTED и SECURITY синхронизированы в RU/EN.
- Project Memory не является разрешением на запись: новый consequential write всё равно требует новый exact `preview_id`, later-turn human approval и отдельный `--ack-bulk` для bulk/unknown scale. Secret heuristic не заявляется как полная DLP.
- Release intent repository-only: `.github/releases/release.json` содержит `plugins: []`; plugin releases/tags не создаются и не retarget.

### Версии плагинов не изменены

Direct `2.1.0`, Metrika `2.1.0`, Webmaster `2.1.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.1.0] — 2026-09-05

P0 executable write-safety release: repository contract и три write-capable service plugins переходят на единый approval/scale/receipt baseline без заявления неподтверждённого read-back или rollback.

### Изменено

- Direct, Metrika и Webmaster используют `yandex-ai-approval/v2`, связывающий exact target/request, authenticated-principal identity, cardinality и declared safety capability; секреты не попадают в preview.
- Repository safety threshold `20` закреплён как внутренняя policy, не Yandex API limit. Bulk `>20` и `UNKNOWN` scale требуют отдельный `--ack-bulk` после exact `preview_id` approval и блокируются до transport без него.
- Successful consequential execution возвращает `yandex-ai-execution/v1`; текущая verification capability честно объявлена `RESPONSE_ONLY` / `UNVERIFIED`, rollback — `NOT_AVAILABLE`.
- Metrika сохраняет exact-file SHA-256, `artifact_rows` и expense `risk_flags`; Logs/import остаются single API operations (`KNOWN`, `items=1`) независимо от row count файла.
- Webmaster сохраняет credential-safe binding embedded URL Basic Auth через OAuth-keyed/domain-separated HMAC и exact cardinality для feed batches.
- Repository convergence tests и `CONTRACT_MATRIX.json` проверяют поведенческое совпадение трёх локальных safety kernels без root shared runtime dependency.
- Standalone CLI механически доказывает exact preview binding, но не может доказать, что человек подтвердил preview в отдельном later conversational turn; human provenance остаётся обязательной host/operator policy.

### Plugin releases

Direct `2.1.0`, Metrika `2.1.0`, Webmaster `2.1.0`.

### Остальные версии не изменены

Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.10] — 2026-09-05

Repository-only supply-chain hardening release, закрывающий issue #43. Production runtime и SemVer плагинов не меняются.

### Изменено

- Все внешние GitHub Actions в трёх active workflows закреплены на полные immutable 40-hex commit SHA вместо mutable major tags.
- Actions одновременно переведены на Node 24 generation: `actions/checkout` v5, `actions/setup-python` v6 и `actions/github-script` v8.
- Добавлен `.github/dependabot.yml` для еженедельных `github-actions` update PR, чтобы обновления pinned SHA проходили через reviewable changes.
- Добавлен fail-closed regression contract, запрещающий mutable/non-SHA external `uses:` refs и требующий Dependabot GitHub Actions update contract.
- Exact-head PR CI подтвердил отсутствие прежнего Node 20 action-runtime deprecation warning.
- Release intent остаётся repository-only: `.github/releases/release.json` содержит `plugins: []`, поэтому новые plugin tags не публикуются.

### Версии плагинов не изменены

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.9] — 2026-09-05

Repository-only release, фиксирующий depth-first продуктовую стратегию после Fable 5.1 review. Production runtime и SemVer плагинов не меняются.

### Изменено

- ROADMAP меняет основной вектор с catalog-style расширения новых Yandex API на methodology/safety/orchestration и user-problem-driven развитие; transport считается заменяемым слоем.
- P0 закрепляет mechanically enforced write safety: exact `preview_id`/approval binding, rollback там, где он технически корректен, post-write verification и bulk guards.
- P1 вводит planned `.yandex-ai/` domain-memory contract: `project.yaml`, append-only `decisions.jsonl`, freshness-aware baselines, hypotheses, `USER_STATED`, no secrets и memory-as-data semantics.
- P2 ставит один примерно 10-minute read-only end-to-end workflow и portable artifacts (versioned JSON, self-contained HTML, Mermaid/DOT, predictable artifact folders) выше desktop UI; Electron явно не нужен на personal stage.
- P3 развивает eval fixtures в executable multi-model benchmark с semantic judge, backend equivalence и memory-aware adversarial scenarios.
- Tracker, Yandex 360, Maps, AppMetrica, YandexGPT и SpeechKit переведены в Frozen expansion backlog до отдельного external user signal/use case.
- Добавлен 90-day external-validation loop; при отсутствии реальных runs/issues/PR проект переходит в low-maintenance/personal-tool mode.
- Release intent остаётся repository-only: `.github/releases/release.json` содержит `plugins: []`, поэтому новые plugin tags не публикуются.

### Версии плагинов не изменены

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.8] — 2026-09-05

Repository-only release для закрытия остаточных Fable Round 2 governance/documentation gaps. Production runtime и SemVer плагинов не меняются.

### Изменено

- Production-facing plugin docs больше не используют `docs/superpowers/` как нормативный источник; historical implementation context остаётся доступным, но canonical contracts находятся в production docs/tests.
- Текущее именование Wordstat унифицировано, русский текст закреплён как primary prose, а RU/EN pairs проверяются механически.
- `PLUGIN_STANDARD` получил `REQ-SKILL-CONTENT`: progressive disclosure, body semantics и validator-enforced bounds теперь связаны одним явным repository requirement.
- Длинная семантика cross-service `authentication: ON_USE` / deferred-auth централизована в `ARCHITECTURE`; SEO/Marketing сохраняют только краткую ссылку и transport ownership boundary.
- ROADMAP отделяет initial shipped versions от текущих и явно оставляет model semantic eval runner/backend equivalence в backlog, не выдавая structural eval validation за semantic model proof.
- Добавлены community governance templates/Code of Conduct и bilingual dated Fable Round 2 closure artifact.
- Release intent остаётся repository-only: `.github/releases/release.json` содержит `plugins: []`, поэтому новые plugin tags не публикуются.

### Версии плагинов не изменены

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.7] — 2026-09-05

Repository-only release для hardening governance и contract traceability. Production runtime и SemVer плагинов не меняются.

### Изменено

- `CONTRACT_MATRIX.json` переведён на schema v2: file-only test links заменены exact Python selectors `test_file.py::test_function` / `test_file.py::TestClass::test_method`.
- Contract validator разрешает selectors через `ast.parse` без import/execute тестовых модулей, fail-closed обрабатывает invalid Python/non-UTF8 и отклоняет statically skipped tests.
- `PLUGIN_STANDARD` RU/EN получил 17 стабильных `REQ-ID` с явным enforcement ownership и сохранением границы между mechanical validation и semantic review/policy.
- Добавлены bilingual repository-owned review artifacts с exact evidence по PR #56 и явно зафиксированным exact-head Codex code-review quota limitation; отсутствие review не представляется как clean review.
- Добавлены `SECURITY.md` / `SECURITY.en.md` для secret exposure, approval bypass, prompt-injection/data-as-instructions, transport ownership, immutable release history и supply-chain concerns без выдуманных контактов или response SLA.
- `docs/superpowers/` явно классифицирован как historical implementation context, а не canonical production authority; root README RU/EN получил навигацию к dated review index.

### Версии плагинов не изменены

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.6] — 2026-09-05

Repository-only release для консолидации release infrastructure. Production runtime и SemVer плагинов не меняются.

### Изменено

- Release intent вынесен в declarative `.github/releases/release.json`; один `publish-current-release.yml` теперь обслуживает будущие repository и явно объявленные plugin releases без нового workflow на каждый release.
- Generic manifest validator проверяет schema, strict repository SemVer, notes paths, существование plugin directories, Codex/Claude manifest versions, canonical plugin tags и uniqueness release set.
- Hardened publisher сохраняет successful exact-main CI gate, stale-main no-op, common-target draft recovery, fail-closed remote tag probes, detached-target validation, immutable verification и safe rollback window.
- Все 12 historical OPUS/FABLE/PHASE/DOCS/release-specific publisher workflows удалены из active default-branch workflow set после завершённых immutable releases; их точный source остаётся доступен через Git history/tags.
- Workflow-specific publisher tests заменены generic manifest/publisher/migration contracts с сохранением reusable safety assertions.
- Release policy фиксирует правило: каждый новый release set получает новый repository SemVer/tag; `plugins: []` означает repository-only release и не создаёт plugin tags.

### Версии плагинов не изменены

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.5] — 2026-09-04

Documentation UX/governance release уровня репозитория. Production runtime и SemVer плагинов не меняются.

### Изменено

- Root README RU/EN переработаны в human-first landing: назначение marketplace, plugin selection, безопасный quick start, практический workflow, понятные границы проекта и навигация по документации теперь находятся до низкоуровневых implementation details.
- Добавлены обязательные bilingual `GETTING_STARTED`, `ARCHITECTURE`, `GLOSSARY` и `RELEASE_POLICY`; repository validator проверяет их как key-doc pairs с reciprocal links, heading-level и SemVer parity.
- Добавлен `CONTRIBUTING.md` как короткий entrypoint к production plugin standard, TDD/CI и release rules.
- `PLUGIN_STANDARD` и independent review guide теперь явно фиксируют human release gate: green CI необходим, но сам по себе не разрешает merge/release; publisher запускается только после принятого изменения в `main` и успешного exact-SHA CI.
- Wordstat README RU/EN использует однозначное название «Wordstat API в составе Yandex Search API v2» / “Wordstat API within Yandex Search API v2”, не меняя API behavior или plugin version `1.1.2`.
- Historical repository/plugin codenames и tags остаются immutable history; текущая repository line использует одну SemVer `1.0.5`.

### Release

- Добавлен repository-only publisher `1.0.5` по существующему hardened exact-main pattern: successful `CI` push exact SHA, stale-main guard, immutable/draft recovery, fail-closed rollback и повторная validator/test verification на release target.
- Publisher не создаёт plugin tags и проверяет, что manifest matrix остаётся Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

### Версии плагинов не изменены

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.4] — 2026-09-04

FABLE 5.1 audit-3 maintenance release уровня репозитория. Версии production-плагинов не меняются.

### Исправлено

- Cross-service transport boundary для SEO/Marketing теперь AST-проверяется по всему Python tree, блокирует transport/dynamic import roots и реальные Yandex endpoint forms, а unreadable/non-UTF8 source обрабатывается fail-closed.
- Generic `SKILL.md` contract проверяет `name == directory`, marketplace-wide uniqueness, bounded description/size и exact-preview/untrusted-data markers для `approval-required` writes.
- Версии plugin manifests теперь сверяются с canonical RU/EN README, changelog, root version surfaces и `SERVICE_MATRIX`; исправлен ранее скрытый README drift SEO и Wordstat с `1.1.1` на уже опубликованный `1.1.2` без нового plugin release.
- Bilingual validation распознаёт `PHASE 7`/`FABLE` release markers и проверяет heading-level structure и SemVer-set parity; устранены найденные реальные drift в root README и `PLUGIN_STANDARD`.
- Validator больше не загрязняет namespace невалидными marketplace paths, обнаруживает orphan plugin directories, распознаёт `~/.agents/`, `$HOME/`, `${HOME}/` и принимает BOM/CRLF/terminal-delimiter frontmatter.
- Добавлен repository-only immutable publisher `1.0.4`, gated на successful `CI` push exact SHA ветки `main`; plugin tags не создаются.

### Версии плагинов не изменены

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.3] — 2026-09-04

FABLE 5.1 review-5 maintenance release после опубликованной immutable `2.0.0` safety generation.

### Исправлено

- Yandex Direct `2.0.1`: Reports CLI больше не принимает OAuth через argv; token читается только из `YANDEX_DIRECT_TOKEN`.
- Direct Reports HTTP errors ограничены 4096 bytes, invalid UTF-8 декодируется с replacement semantics, `URLError` становится secret-free operational failure; opener/sleep injectable для deterministic tests.
- Reports `201/202 + retryIn` polling и один retry первого HTTP `500` сохранены как отдельный read-only async contract.
- `CONTRACT_MATRIX.json` получил explicit Direct contracts для Reports async transport, KPI provenance и creation≠activation; `references/sources.md` включён в freshness control с canonical `Verified:` marker.
- Исправлены false-positive SEO internal-linking tests: unknown endpoint и forced exact-match теперь проверяются с otherwise-valid candidate metadata и точными failure messages. Production SEO code не менялся; SEO остаётся `1.1.2`.
- Repository secret scanner теперь проверяет committed `.env` / `.env.*` files и сохраняет безопасные placeholder semantics `.env.example`.
- RU/EN root docs синхронизированы с уже опубликованной immutable FABLE `2.0.0` generation и Direct `2.0.1`; verification examples используют `python -m compileall -q scripts`.
- Safety docs разделяют executable helper guarantees и agent/operator policy: generic rollback snapshots и bulk `>20` enforcement отложены до отдельного safety design.

### Release matrix

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [OPUS 1.1.3] — 2026-09-03

Hardening Phase 7 contracts по новому Opus 5 audit.

### Исправлено

- Yandex SEO `1.1.2`: empirical boundary-changing decisions требуют Search-owned provenance; empirical `MERGE`/`REDIRECT` дополнительно требуют evidence существующей страницы/URL.
- `coverage.search=PARTIAL` теперь раскрывается как `SERP_VALIDATION_PARTIAL`; Search cluster ingress валидируется, bridge/source limitations автоматически propagируются downstream.
- `METHODOLOGY` стал first-class qualitative Evidence Bundle kind, но не может маскироваться под quantitative metric evidence.
- Неоценённые `link_plan`/`audits` теперь различаются от evaluated-empty результатов (`null` vs explicit attached `[]`).
- Internal-link audit считает orphan по отсутствию inbound links, сохраняет/флагирует duplicate links и считает rootless `BRIDGE` без inbound link orphan/broken bridge. Explicit `ROOT` и legacy parentless node без `page_role` остаются exempt; explicit non-root roles проверяются на orphan. Self-links публикуются как `SELF_LINK` и исключаются из valid/inbound reachability counts.
- Yandex Wordstat `1.1.2`: topic-map query normalization использует Unicode NFKC + casefold + whitespace folding без invented demand summation.
- Legacy OPUS 1.1.0 publisher переведён на canonical repository guard `trafficolog/yandex-ai-plugins-skills`; repository-level regression не допускает возврата старого имени.

### Published plugin matrix

Direct `1.0.1`, Metrika `1.0.3`, Webmaster `1.0.3`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [OPUS 1.1.2] — 2026-09-03

Residual hardening по оставшимся замечаниям финального Opus 5 audit.

### Исправлено

- Yandex Metrika `1.0.3` закрывает Direct expense provenance gap для CSV без `UTMSource` / `UTMMedium`: официальный `TrafficSourceDetail=yandex_direct_star` блокируется как `DIRECT_DUPLICATION_RISK`.
- Недостаточная expense provenance теперь fail-closed как `DIRECT_SOURCE_UNVERIFIED`; generic `TrafficSource=ad` без source detail требует explicit review/`--allow-direct-risk` вместо silent pass.
- Explicit non-Direct source detail остаётся разрешённым; arbitrary provider label вроде `MyDirect` не объявляется Direct только по substring.
- Shared-code rule усилен installability/distribution gate: duplication + stable interface недостаточны для root runtime package, пока независимо устанавливаемый plugin не может гарантированно получить shared dependency.
- N3/N5/N6/N8 повторно сверены с текущим contract/docs состоянием и не переоткрываются: traceability ≠ semantic proof, cross-service `ON_USE` соответствует marketplace schema, Webmaster `state`/`download_url` подтверждены, Marketing spec уже normatively reconciled.

### Published plugin matrix

Direct `1.0.1`, Metrika `1.0.3`, Webmaster `1.0.3`, Wordstat `1.1.1`, Search `1.0.2`, SEO `1.1.1`, Marketing `1.1.0`.

## [1.0.2] — 2026-09-03

Maintenance release уровня репозитория для hardening release-инфраструктуры после Phase 7.

### Исправлено

- Legacy publisher `OPUS 1.1.1` теперь распознаёт полностью опубликованный исторический release set на одном ancestor SHA и завершает последующие `main` runs как verified no-op.
- Partial OPUS release set восстанавливается на уже опубликованном общем SHA, а не переносится на текущий `main`.
- Inconsistent/multi-SHA historical release state остаётся hard failure; исторические теги не retarget/mutate.
- Добавлен regression contract `tests/test_opus_publisher_idempotency.py` для immutable/no-op/partial-recovery semantics.
- Добавлен repository release publisher `1.0.2`, gated на успешный `CI` push точного SHA ветки `main`.

### Версии плагинов не изменены

Direct `1.0.1`, Metrika `1.0.2`, Webmaster `1.0.3`, Wordstat `1.1.1`, Search `1.0.2`, SEO `1.1.1`, Marketing `1.1.0`.

## [PHASE 7 1.0.1] — 2026-09-03

Post-release hardening patch для Topical Architecture / Semantic Cocoons baseline.

### Исправлено

- Yandex Wordstat `1.1.1` отклоняет duplicate `seeds[].seed`, сохраняя `source_seed` однозначным provenance key.
- Yandex Wordstat `1.1.1` отклоняет candidate topic self-relations (`from_topic_id == to_topic_id`).
- Yandex SEO `1.1.1` нормализует `structural_tree.nodes` через explicit field whitelist и не переносит caller execution/recommendation state (`decision`, `status`, `write`, `execution_id`).
- Yandex SEO `1.1.1` требует list-typed candidate-link `evidence`; scalar/object payload отклоняется до preview serialization.
- Service ownership, Search `1.0.2`, transport-free SEO boundary и preview-only internal-link semantics не меняются.

### Published plugin matrix

Direct `1.0.1`, Metrika `1.0.2`, Webmaster `1.0.3`, Wordstat `1.1.1`, Search `1.0.2`, SEO `1.1.1`, Marketing `1.1.0`.

## [PHASE 7 1.0.0] — 2026-09-02

Evidence-first Topical Architecture / Semantic Cocoons release.

### Architecture

- Yandex Wordstat `1.1.0` получил `yandex-wordstat-topic-map` и `wordstat-topic-map/v1`: candidate-only topic maps, provenance-preserving query deduplication, отдельные demand observations и explicit limitation propagation.
- Yandex Search остаётся `1.0.2` и единственным владельцем real SERP-overlap/Jaccard clustering; Phase 7 не добавляет competing fuzzy-text clusterer и не меняет Search runtime.
- Yandex SEO `1.1.0` получил `yandex-seo-topical-architecture` и `seo-topical-architecture/v1` для `GREENFIELD|EXISTING_SITE`, page decisions, независимых `structural_tree` и `semantic_graph`.
- Yandex SEO `1.1.0` получил `yandex-seo-internal-linking`: preview-only link planning и deterministic audit без CMS writes.

### Evidence and safety contracts

- `OBSERVED`, `DERIVED`, `HYPOTHESIS`, `METHODOLOGY` остаются раздельными; semantic-cocoon/TGA/QBST methodology не заявляется как подтверждённый ranking mechanism.
- Без Search evidence обязателен `SERP_VALIDATION_MISSING`, а page boundaries остаются hypotheses.
- Wordstat associations/co-occurrence не объявляются финальными page boundaries и не агрегируются в fictitious total demand.
- SEO остаётся transport-free: никаких новых Yandex HTTP clients, credentials или live mutations.
- `CONTRACT_MATRIX.json` закрепляет `wordstat.topic-map-candidate-boundary`, `seo.topical-architecture-structural-tree`, `seo.topical-architecture-evidence-classes`, `seo.internal-linking-preview-only`.

### Published plugin matrix

Direct `1.0.1`, Metrika `1.0.2`, Webmaster `1.0.3`, Wordstat `1.1.0`, Search `1.0.2`, SEO `1.1.0`, Marketing `1.1.0`.

## [OPUS 1.1.1] — 2026-09-02

Follow-up fix-release по финальному Opus 5 review.

### Repository controls

- 90-day freshness gate больше не является time-bomb для несвязанных PR: age hard-fail применяется к изменённому freshness-controlled reference, а scheduled strict workflow проверяет весь набор и синхронизирует отдельный GitHub issue.
- `CONTRACT_MATRIX.json` расширен контрактами Metrika Direct-expense duplication guard, Webmaster indexing archive lifecycle, SEO unknown Webmaster impressions и Marketing quality metadata shape.
- `PLUGIN_STANDARD` прямо определяет contract matrix как traceability index, а не semantic proof, и фиксирует, что eval fixtures пока структурно валидируются, но не исполняются против модели.
- Cross-service `authentication: ON_USE` документирован как schema-compatible deferred-auth metadata без собственной credential/transport surface.
- Marketing taxonomy согласована с фактической девяткой executable finding types и explicit deferred set через normative spec amendment.

### Plugin releases

- Yandex Metrika `1.0.2`: source-label guard для Direct expenses распознаёт tokenized labels и сохраняет независимый CSV UTM risk layer.
- Yandex Webmaster `1.0.3`: официально перепроверено поле indexing archive `state` (`IN_PROGRESS` / `DONE` / `FAILED`) и закреплено regression/traceability contract.
- Direct `1.0.1`, Wordstat `1.0.2`, Search `1.0.2`, SEO `1.0.1`, Marketing `1.1.0` не менялись.

## [DOCS 1.0.0] — 2026-09-02

### Изменено

- Русский язык стал основным для root README/CHANGELOG и ключевой repository-документации; английские версии публикуются как `.en.md` mirrors.
- Все семь production-плагинов получили двуязычные README/CHANGELOG пары без изменения их SemVer.
- Добавлены два локальных SVG hero-banner для RU/EN root README в `docs/assets/readme/`.
- В README `yandex-seo` и `yandex-marketing` добавлены Mermaid-схемы orchestration, явно показывающие evidence flow, no-transport boundary и delegated previews.
- Repository validator теперь проверяет наличие языковых пар, reciprocal language links и равенство release markers в RU/EN changelog.
- `docs/PLUGIN_STANDARD.md` закрепляет bilingual documentation как production contract.

### Версии плагинов не изменены

Direct `1.0.1`, Metrika `1.0.1`, Webmaster `1.0.2`, Wordstat `1.0.2`, Search `1.0.2`, SEO `1.0.1`, Marketing `1.1.0`.

## [OPUS 1.1.0] — 2026-09-02

Contract-hardening milestone: Wordstat association coverage cap, Search 250-result depth, Webmaster PRO lifecycle/quota semantics, Marketing evidence roles/taxonomy и executable repository contract/freshness controls.

## [1.0.1] — 2026-09-02

Review-driven maintenance: safe-by-default mutation/API contracts, omission-preserving Metrika attribution, cross-service evidence/context semantics, URL identity, evals и dependency-aware CI.

## [1.0.0] — 2026-09-02

Первый полный marketplace release: Direct, Metrika, Webmaster, Wordstat, Search, SEO и Marketing; единый plugin standard, safety lifecycle, offline tests/evals и path-aware CI.
