# Yandex Direct

[Русский](README.md) · [**English**](README.en.md)

Version `2.0.1`. Service plugin for Yandex Direct campaigns, Reports API, audits, keywords/negatives, budgets, optimization and low-level API workflows.

## Execution model

Preference: compatible connected MCP/app → bundled Python helper → export/file fallback. Consequential changes follow `read → analyze → preview → explicit approval → write → verify`.

### Migration 1.x → 2.0.0

`2.0.0` introduced the breaking write-safety contract. The old `--execute`-only invocation is no longer sufficient authorization:

```bash
# 1.x — old contract
python scripts/yd_api.py campaigns update --params-file update.json --execute

# 2.x — preview first
export YANDEX_DIRECT_TOKEN='...'
python scripts/yd_api.py campaigns update --params-file update.json
# then, only after the exact preview is approved in a later user turn
python scripts/yd_api.py campaigns update --params-file update.json --execute --approve <preview_id>
```

The `preview_id` binds service, method, `Client-Login`, OAuth auth principal, environment, and body. Changing the token, payload, or environment requires a fresh preview/approval. OAuth is supplied only through `YANDEX_DIRECT_TOKEN`; there is no `--token` argv option.

### Patch 2.0.1 — Reports hardening

`yd_report.py` now uses the same credential boundary: OAuth only from `YANDEX_DIRECT_TOKEN`, with no `--token`. HTTP error bodies are capped at 4096 bytes and decoded with `errors="replace"`; `URLError` becomes a secret-free operational failure. The transport opener and sleep function are injectable for deterministic tests. Reports-specific semantics are preserved: `200` returns TSV, `201/202` continue polling according to `retryIn`, and HTTP `500` allows at most one automatic retry.

## Production and sandbox

The helper uses production `https://api.direct.yandex.com/json/v501/{service}` by default. Use the explicit flag for the official sandbox:

```bash
python scripts/yd_api.py campaigns get --params '{}' --sandbox
```

Sandbox uses `https://api-sandbox.direct.yandex.com/json/v5/{service}`. Production and sandbox are distinct approval-bound environments: a production preview cannot authorize a sandbox write and vice versa.

## Transport metadata and errors

A live API-helper call keeps the exact Yandex Direct JSON payload under `result` and exposes selected safe transport headers separately under `transport`: `RequestId` → `request_id`, `Units` → `units`, and `Units-Used-Login` → `units_used_login`. Other response headers are not copied by default.

Expected `yd_api.py` CLI failures (`validation`, `input`, `network`, `http`, `api`) are emitted as JSON to stderr with exit code `2`, without a normal traceback. HTTP error bodies are capped at 4096 bytes and decoded with replacement semantics. The Reports helper also uses bounded error reads and secret-free network failures while retaining its read-only polling contract.

## Capability matrix

| Capability | Read | Write | MCP/App | Bundled API | File fallback |
|---|---:|---:|---:|---:|---:|
| Campaign discovery / state | yes | — | optional | yes | yes |
| Campaign draft / update payloads | yes | approval | optional | yes | yes |
| Audit | yes | — | optional | yes | yes |
| Reports / KPI analysis | yes | — | optional | yes | yes |
| Keywords / negatives | yes | approval | optional | yes | yes |
| Budget analysis / changes | yes | approval | optional | yes | yes |
| Optimization recommendations / writes | yes | approval | optional | yes | yes |

## Skills

`yandex-direct` router; `yandex-direct-create`; `yandex-direct-audit`; `yandex-direct-reporting`; `yandex-direct-optimize`; `yandex-direct-keywords`; `yandex-direct-budget`; `yandex-direct-api`.

## Key correctness rules

- production API uses v501; sandbox uses the separately documented `/json/v5/` contract;
- service names are checked against a strict allowlist before URL construction;
- queued 201/202 Reports repeat the same payload/report name and honor `retryIn`;
- report artifacts preserve goal/attribution/VAT provenance and do not invent currency;
- autotargeting and keyword criteria stay distinct;
- unknown/mutating methods are safe-by-default and preview before execute;
- consequential writes require exact `preview_id` approval;
- no universal CPA/CPC/CTR/ROAS kill rules;
- campaign creation is distinct from activation.

## Safety enforcement boundary

A consequential preview uses `yandex-ai-approval/v2`: exact service/method/environment/body, `Client-Login`, authenticated-principal binding, cardinality, and safety capability are bound in one digest. For known entity-list writes the helper counts exact items; opaque write shapes receive `UNKNOWN` scale. Repository threshold `20` is internal safety policy, not a Yandex API limit. Bulk `>20` and `UNKNOWN` execution are blocked before transport without `--ack-bulk`, even with a correct `--approve <preview_id>`.

A successful write returns a `yandex-ai-execution/v1` receipt with the same `preview_id`. The current capability declaration remains truthfully `RESPONSE_ONLY` + `UNVERIFIED`; rollback is `NOT_AVAILABLE`. This is not read-back verification or automatic rollback. A standalone CLI also cannot prove later-turn human approval: the host/operator must show the exact preview and obtain a separate later user approval.

## Helpers

```bash
export YANDEX_DIRECT_TOKEN='...'
python scripts/yd_api.py campaigns get --params '{"SelectionCriteria":{},"FieldNames":["Id","Name","Status"]}'
python scripts/yd_api.py campaigns update --params-file update.json # preview
python scripts/yd_api.py campaigns update --params-file update.json --execute --approve <preview_id>
python scripts/yd_api.py campaigns update --params-file bulk-update.json --execute --approve <preview_id> --ack-bulk
python scripts/yd_api.py campaigns get --params '{}' --sandbox
python scripts/yd_report.py campaign 2026-08-01 2026-08-31 --output report.tsv
```

## Verification

```bash
python -m unittest discover -s tests -v
python -m compileall -q scripts
```

Sources and upstream attribution: `THIRD_PARTY_NOTICES.md`, `references/sources.md`, `references/api-2026.md`.
