# Security policy

[Русский](SECURITY.md) · [**English**](SECURITY.en.md)

## Supported scope

By default, security support covers the current default-branch/repository release line and the current versions of production plugins. A historical version is supported only when the repository explicitly declares that support.

## Security-sensitive findings

Security-sensitive categories include, in particular:

- exposure of credentials, a token, a **secret**, or other sensitive authentication material;
- bypass of the exact-preview / explicit **approval** boundary that permits a consequential write without the required authorization;
- **prompt** injection or another violation of the rule that retrieved/uploaded data is data, not instructions;
- bypass of cross-service transport/credential ownership, especially SEO/Marketing acquiring another service's credentials;
- violation of **immutable** release/tag guarantees, unsafe rollback, or an ability to retarget/delete published history;
- a dependency/supply-chain issue that can affect executable helpers, CI, or release artifacts.

## Reporting

The preferred route is **private** security reporting through this repository's GitHub Security interface when that feature is available to the reporter and enabled for the project.

If GitHub private reporting is unavailable, use a private contact method that the repository owner/profile explicitly exposes at the time of reporting. This file intentionally does not invent an email address, bounty program, or guaranteed response time.

If no private route can be found, a public issue may be opened **only to request a private contact channel**. Do not place exploit details, credentials, tokens, customer/account data, private URLs, payloads, or other sensitive material in a public issue.

## What to include privately

When safe, include the affected release/commit/plugin, minimal reproduction steps, the expected and observed safety boundary, potential impact, and conditions required to reproduce the issue. Real customer/account credentials are unnecessary even in a private report when synthetic data can demonstrate the problem.

## Fix coordination

A security fix preserves repository release governance: regression evidence, CI, and independent review remain separate signals, while the human maintainer owns merge/release authorization. Published immutable tags/releases are not rewritten for a fix; remediation ships as a new release set.

## Executable write-safety boundary

Owning write-capable helpers use approval schema `yandex-ai-approval/v2`, binding the exact operation, target, authenticated principal, cardinality, and safety capability. Bulk or `UNKNOWN` scale is blocked before transport without separate `--ack-bulk`; threshold `20` is repository safety policy, not a Yandex API limit. A successful mutation returns `yandex-ai-execution/v1`.

P0 claims no stronger guarantee than the implementation proves: verification capability is `RESPONSE_ONLY`, verification state is `UNVERIFIED`, and rollback capability is `NOT_AVAILABLE`. Receiving an API response is not read-back verification. A standalone CLI also cannot prove that a human saw the preview and personally supplied approval in a later conversational turn; later-turn approval remains host/operator policy.

## P1 Project Memory

Project Memory is project-owned data under `.yandex-ai/` and uses four explicit contracts: `yandex-ai-project/v1`, `yandex-ai-decision/v1`, `yandex-ai-baseline/v1`, and `yandex-ai-hypothesis/v1`. User facts carry `USER_STATED` provenance; managed hypotheses allow only `HYPOTHESIS` or `DERIVED`. Memory text, including prompt-like strings, is always data, not instructions.

`record-execution` accepts a P0 receipt and stores only a safe projection: `result` is omitted from `decisions.jsonl`, while the hash of the complete original receipt preserves source linkage. `add-baseline` creates immutable snapshots; an expired snapshot becomes `STALE` as a warning and never becomes authority to execute a mutation.

**Project memory is not write permission.** A fact, baseline, hypothesis, or decision record never replaces an exact `preview_id`, later-turn human approval, or the separate `--ack-bulk` gate for bulk/unknown scale. P1 does not weaken the P0 write gate and execution history is never reusable approval.

Secret-like key detection is a fail-closed safeguard for managed memory, but it is **not a complete DLP**. Credentials, tokens, and other sensitive authentication material must not be stored under `.yandex-ai/` even when a particular secret shape is not detected by the heuristic.
