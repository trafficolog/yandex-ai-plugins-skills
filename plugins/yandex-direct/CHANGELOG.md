# Журнал изменений — Yandex Direct

[**Русский**](CHANGELOG.md) · [English](CHANGELOG.en.md)

## [2.1.0] — 2026-09-05

- Consequential Direct writes переведены на `yandex-ai-approval/v2`: exact service/method/environment/body, `Client-Login`, authenticated-principal binding, cardinality и safety capability входят в один approval digest.
- Для известных entity-list writes helper связывает exact item count; непрозрачные write shapes получают `UNKNOWN` scale. Repository threshold `20` — внутренняя safety policy, а не лимит Yandex API.
- Bulk `>20` и `UNKNOWN` execution требуют отдельный `--ack-bulk` после exact `--approve <preview_id>` и блокируются до HTTP transport без acknowledgement.
- Успешный consequential write возвращает structured `yandex-ai-execution/v1` receipt с исходным `preview_id` и declared execution capability.
- P0 честно объявляет verification как `RESPONSE_ONLY` / `UNVERIFIED`, rollback как `NOT_AVAILABLE`: успешный API response не считается read-back verification и не обещает автоматический rollback.
- Standalone CLI механически проверяет exact preview binding, но не может доказать, что человек видел preview и подтвердил его в отдельном later conversational turn; эта provenance boundary остаётся обязанностью host/operator.

## [2.0.1] — 2026-09-04

- Reports CLI переведён на env-only OAuth: `yd_report.py` читает token только из `YANDEX_DIRECT_TOKEN`; argv `--token` удалён.
- HTTP error body Reports helper ограничен 4096 bytes и декодируется с replacement semantics; `URLError` становится secret-free operational failure.
- Transport opener и sleep injectable для deterministic tests; Reports-specific `201/202 + retryIn` polling сохранён, HTTP `500` ретраится не более одного раза.
- Добавлены explicit contracts `direct.reports-async-transport`, `direct.reports-kpi-provenance`, `direct.creation-not-activation` и freshness control для `references/sources.md`.
- Internal-linking tests SEO исправлены так, чтобы проверять именно unknown-endpoint и forced exact-match guards; production SEO behavior не изменился, поэтому SEO остаётся `1.1.2`.
- Helper-level safety boundary документирован честно: rollback context и bulk `>20` пока agent/operator policy, не generic executable guarantee.

## [2.0.0] — 2026-09-03

- Breaking safety contract: consequential Direct writes теперь требуют exact `preview_id`; одного `--execute` недостаточно.
- Новый flow: preview → approval exact preview в следующем пользовательском turn → `--execute --approve <preview_id>`.
- Approval связывает service, method, `Client-Login`, environment, body и pseudonymous HMAC-SHA256 auth-principal binding; смена OAuth token или payload инвалидирует permission без раскрытия token.
- OAuth credential удалён из argv: helper принимает token только из `YANDEX_DIRECT_TOKEN`.
- Добавлен explicit `--sandbox` с официальным `https://api-sandbox.direct.yandex.com/json/v5/{service}`; production и sandbox имеют разные approval digests.
- Direct API transport вынесен в service-local `_http.py`: HTTP error body ограничен 4096 bytes, invalid UTF-8 декодируется безопасно, opener/timeout injectable для тестов, consequential POST не получает automatic retry.
- Live response сохраняет исходный API payload отдельно от safe metadata `RequestId`, `Units`, `Units-Used-Login`.
- CLI operational failures возвращают structured stderr JSON (`validation`, `input`, `network`, `http`, `api`) и exit code `2` без обычного traceback.
- Service URL строится только после strict allowlist validation текущих official v5 endpoints.
- API/account/file content трактуется как данные, а не инструкции; adjacent service work маршрутизируется в owning plugin.

Migration:

```bash
# 1.x
python scripts/yd_api.py campaigns update --params-file update.json --execute

# 2.0.0+
export YANDEX_DIRECT_TOKEN='...'
python scripts/yd_api.py campaigns update --params-file update.json
python scripts/yd_api.py campaigns update --params-file update.json --execute --approve <preview_id>
# sandbox — отдельная approval-bound environment
python scripts/yd_api.py campaigns get --params '{}' --sandbox
```

## [1.0.1] — 2026-09-02

- API safety переведён на allowlist: unknown и mutating methods preview-first по умолчанию.
- Reports attribution/goals стали explicit; удалён obsolete `IncludeDiscount`; первый HTTP 500 ретраится один раз.
- TSV reports получили KPI provenance metadata sidecars без выдумывания currency.
- Добавлены regression eval expectations для write safety и report context.

## [1.0.0] — 2026-09-01

- Монолитные знания Direct разделены на 8 discoverable skills.
- Core API workflow обновлён до v501 и EPK-first модели.
- Добавлены safe API helper, Reports helper, autotargeting/shared negatives guidance, offline tests и marketplace manifests.
