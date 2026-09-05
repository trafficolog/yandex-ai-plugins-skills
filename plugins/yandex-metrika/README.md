# Yandex Metrika

[**Русский**](README.md) · [English](README.en.md)

Версия `2.0.0`. Service plugin для аналитики Яндекс Метрики: reporting, conversions, ecommerce, attribution, goals, Logs API, imports и low-level Management API.

## Migration 1.x → 2.0.0

`2.0.0` вводит breaking exact-preview contract для consequential writes. Старый `--execute` без approval больше не достаточен:

```bash
# 1.x — старый контракт
python scripts/ym_api.py counter/123/goals --method POST --body '{"goal":{"name":"Lead"}}' --execute

# 2.0.0 — preview first
python scripts/ym_api.py counter/123/goals --method POST --body '{"goal":{"name":"Lead"}}'
# после approval exact preview в следующем пользовательском turn
python scripts/ym_api.py counter/123/goals --method POST --body '{"goal":{"name":"Lead"}}' --execute --approve <preview_id>
```

Management writes, Logs `create`/`clean` и imports fail-closed без exact approval. Для imports `preview_id` привязан к SHA-256 точных байтов файла; изменённый файл требует нового preview.

## Capability matrix

| Capability | Read | Write | MCP/App | Bundled API | File fallback |
|---|---:|---:|---:|---:|---:|
| Reporting / attribution / quality | yes | no | optional | yes | yes |
| Goals management | yes | approval | optional | yes | preview |
| Logs API lifecycle | yes | approval | optional | yes | yes |
| Offline conversions / calls / expenses import | preview | approval | optional | yes | yes |
| Raw Management API operations | yes | approval | optional | yes | preview |

## Ключевые контракты

- omitted attribution сохраняется как omitted provenance, а не заменяется выдуманным default;
- sampling, sample share, data lag и другие quality fields являются частью результата;
- Logs lifecycle explicit: evaluate → create → status → download → clean;
- imports защищены от duplicate-risk для native Yandex Direct expenses;
- expense guard классифицирует CSV provenance как `DIRECT`, `NON_DIRECT` или `UNVERIFIED` по UTM и `TrafficSource` / `TrafficSourceDetail` evidence;
- официальный `TrafficSourceDetail=yandex_direct_star` блокируется как `DIRECT_DUPLICATION_RISK`, даже если `UTMSource` / `UTMMedium` отсутствуют;
- generic advertising provenance без достаточного source detail блокируется как `DIRECT_SOURCE_UNVERIFIED` до explicit review/override;
- arbitrary substring вроде `MyDirect` сам по себе не считается доказанным Direct source;
- consequential writes требуют later-turn exact `preview_id` approval;
- cross-service consumers должны сохранять quality limitations.

## Safety enforcement boundary

Consequential writes используют `yandex-ai-approval/v2` с authenticated-principal binding, exact request/target и cardinality. Generic Management write считается `UNKNOWN`, поэтому после exact `--approve <preview_id>` требует `--ack-bulk` до transport. Repository threshold `20` — внутренняя safety policy, а не Yandex API limit.

Logs `create`/`clean` и каждый import — один API operation (`KNOWN`, `items=1`), поэтому row count CSV не превращает upload в bulk API operation. Для import отдельно approval-bound `artifact_rows`, SHA-256 точных file bytes и expense `risk_flags`; Direct/unverified expense provenance сохраняет собственный explicit risk override.

Успешный consequential call возвращает `yandex-ai-execution/v1`; P0 verification — `RESPONSE_ONLY` + `UNVERIFIED`, rollback — `NOT_AVAILABLE`. Standalone CLI не доказывает later-turn human approval: это обязательная host/operator policy.

## Skills

`yandex-metrika`, `-audit`, `-reporting`, `-conversions`, `-ecommerce`, `-attribution`, `-goals`, `-logs`, `-imports`, `-api`.

## Credentials и проверка

Используйте `YANDEX_METRIKA_TOKEN` локально или credentials connected app; реальные токены не коммитятся.

```bash
python -m unittest discover -s tests -v
```
