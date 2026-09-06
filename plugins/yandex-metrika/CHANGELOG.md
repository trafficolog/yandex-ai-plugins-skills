# Журнал изменений — Yandex Metrika

[**Русский**](CHANGELOG.md) · [English](CHANGELOG.en.md)

## [2.1.0] — 2026-09-05

- Consequential Metrika operations переведены на `yandex-ai-approval/v2` с authenticated-principal binding, exact target/request, cardinality и safety capability.
- Generic Management write получает `UNKNOWN` scale и после exact `--approve <preview_id>` дополнительно требует `--ack-bulk` до transport; repository threshold `20` — safety policy, не лимит Yandex API.
- Logs `create`/`clean` и каждый import моделируются как один API operation (`KNOWN`, `items=1`), поэтому число CSV rows само по себе не превращает upload в bulk API operation.
- Import preview сохраняет прежнюю защиту exact artifact bytes: SHA-256 файла, `artifact_rows` и expense `risk_flags` approval-bound; Direct/unverified expense provenance по-прежнему требует отдельный explicit risk override.
- Успешный consequential call возвращает `yandex-ai-execution/v1`; verification объявлена как `RESPONSE_ONLY` / `UNVERIFIED`, rollback как `NOT_AVAILABLE`, без ложного read-back/rollback claim.
- Standalone CLI проверяет exact approval механически, но не доказывает later-turn human approval; эту provenance boundary обеспечивает host/operator.

## [2.0.0] — 2026-09-03

- Breaking safety contract: `--execute` больше не является достаточным разрешением на consequential write; после отдельного later-turn user approval требуется `--execute --approve <preview_id>` для exact preview.
- Management API writes, Logs `create`/`clean` и imports теперь fail-closed при missing/mismatched approval.
- Import approval привязан к SHA-256 точных байтов файла, поэтому изменение содержимого требует нового preview и нового approval.
- API/account/file content трактуется как untrusted data, а не инструкции; generic permission не переносится на другой payload.

Migration:

```bash
# 1.x
python scripts/ym_api.py counter/123/goals --method POST --body '{"goal":{"name":"Lead"}}' --execute
# 2.0.0
python scripts/ym_api.py counter/123/goals --method POST --body '{"goal":{"name":"Lead"}}'
python scripts/ym_api.py counter/123/goals --method POST --body '{"goal":{"name":"Lead"}}' --execute --approve <preview_id>
```

## [1.0.3] — 2026-09-03

- Закрыта остаточная щель Direct expense guard для CSV без `UTMSource` / `UTMMedium`.
- Добавлена provenance-классификация `DIRECT` / `NON_DIRECT` / `UNVERIFIED` по UTM и `TrafficSource` / `TrafficSourceDetail` evidence.
- Официальный `TrafficSourceDetail=yandex_direct_star` теперь детектируется как `DIRECT_DUPLICATION_RISK` независимо от UTM-полей.
- Недостаточная source provenance, например generic `TrafficSource=ad` без source detail, fail-closed как `DIRECT_SOURCE_UNVERIFIED` и требует explicit `--allow-direct-risk` после review.
- Explicit non-Direct detail вроде `google_adwords` остаётся разрешённым; arbitrary provider label `MyDirect` не объявляется Direct по substring alone.

## [1.0.2] — 2026-09-02

- Усилен Direct expense duplication guard: помимо exact aliases блокируются явные tokenized labels (`Yandex Direct RU`, `direct_ads`, `Яндекс Директ агентство`).
- CSV-content guard по `UTMSource` / `UTMMedium` остаётся независимым вторым слоем и сохраняет explicit `--allow-direct-risk` override.
- Arbitrary substring вроде `MyDirect` не объявляется Direct provenance без дополнительного evidence.
- Guard добавлен в repository contract matrix как high-risk traceability contract.

## [1.0.1] — 2026-09-02

- Усилено обнаружение duplicate-risk для Yandex Direct expense imports.
- Reporting attribution metadata сохраняет explicit-vs-omitted provenance без invented default.
- Nested producer quality metadata сохранена для cross-service consumers.
- Добавлены verifiable eval expectations для reporting, imports, Logs и write safety.

## [1.0.0] — 2026-09-01

- Первый Yandex Metrika plugin: специализированные analytics/data-quality/goals/Logs/import skills и dependency-light helpers с preview-before-write.
