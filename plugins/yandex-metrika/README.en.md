# Yandex Metrika

[Русский](README.md) · [**English**](README.en.md)

Version `2.0.0`. Service plugin for Yandex Metrika reporting, conversions, ecommerce, attribution, goals, Logs API, imports and low-level Management API workflows.

## Migration 1.x → 2.0.0

`2.0.0` introduces a breaking exact-preview contract for consequential writes. The old `--execute` flag without approval is no longer sufficient:

```bash
# 1.x — old contract
python scripts/ym_api.py counter/123/goals --method POST --body '{"goal":{"name":"Lead"}}' --execute

# 2.0.0 — preview first
python scripts/ym_api.py counter/123/goals --method POST --body '{"goal":{"name":"Lead"}}'
# after approval of that exact preview in a later user turn
python scripts/ym_api.py counter/123/goals --method POST --body '{"goal":{"name":"Lead"}}' --execute --approve <preview_id>
```

Management writes, Logs `create`/`clean`, and imports fail closed without exact approval. For imports, `preview_id` is bound to the SHA-256 digest of the exact file bytes; changing the file requires a new preview.

## Capability matrix

| Capability | Read | Write | MCP/App | Bundled API | File fallback |
|---|---:|---:|---:|---:|---:|
| Reporting / attribution / quality | yes | no | optional | yes | yes |
| Goals management | yes | approval | optional | yes | preview |
| Logs API lifecycle | yes | approval | optional | yes | yes |
| Offline conversions / calls / expenses import | preview | approval | optional | yes | yes |
| Raw Management API operations | yes | approval | optional | yes | preview |

## Key contracts

- omitted attribution remains explicit omission provenance rather than an invented default;
- sampling, sample share, data lag and quality fields are part of the result contract;
- Logs lifecycle is explicit: evaluate → create → status → download → clean;
- imports guard against duplicate native Yandex Direct expenses;
- the expense guard classifies CSV provenance as `DIRECT`, `NON_DIRECT`, or `UNVERIFIED` from UTM and `TrafficSource` / `TrafficSourceDetail` evidence;
- official `TrafficSourceDetail=yandex_direct_star` is blocked as `DIRECT_DUPLICATION_RISK` even when `UTMSource` / `UTMMedium` are absent;
- generic advertising provenance without enough source detail is blocked as `DIRECT_SOURCE_UNVERIFIED` until explicit review/override;
- an arbitrary substring such as `MyDirect` is not treated as proven Direct provenance by label alone;
- consequential writes require later-turn approval of the exact `preview_id`;
- cross-service consumers preserve quality limitations.

## Safety enforcement boundary

Consequential writes use `yandex-ai-approval/v2` with authenticated-principal binding, exact request/target, and cardinality. A generic Management write is `UNKNOWN`, so after exact `--approve <preview_id>` it also requires `--ack-bulk` before transport. Repository threshold `20` is internal safety policy, not a Yandex API limit.

Logs `create`/`clean` and each import are one API operation (`KNOWN`, `items=1`), so CSV row count does not turn an upload into a bulk API operation. Imports separately bind `artifact_rows`, the SHA-256 of exact file bytes, and expense `risk_flags`; Direct/unverified expense provenance keeps its own explicit risk override.

A successful consequential call returns `yandex-ai-execution/v1`; P0 verification is `RESPONSE_ONLY` + `UNVERIFIED`, and rollback is `NOT_AVAILABLE`. A standalone CLI does not prove later-turn human approval; that remains mandatory host/operator policy.

## Skills

`yandex-metrika`, `-audit`, `-reporting`, `-conversions`, `-ecommerce`, `-attribution`, `-goals`, `-logs`, `-imports`, `-api`.

## Credentials and verification

Use `YANDEX_METRIKA_TOKEN` locally or connected-app credentials; never commit real tokens.

```bash
python -m unittest discover -s tests -v
```
