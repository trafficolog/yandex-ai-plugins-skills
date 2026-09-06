# Roadmap

[Русский](ROADMAP.md) · [**English**](ROADMAP.en.md)

The first-release scope is frozen after Phase 6B. The phases below are shipped architectural milestones and post-first-release releases; backlog items are not delivery-date or next-release promises.

RU-primary policy permits English product names, identifiers, code, API names, and established technical terms in Russian mirrors, but ordinary prose sentences should remain Russian unless quoted or translation would distort an exact external contract.

## First release — completed

### Phase 1 — Marketplace foundation
Direct moved under `plugins/yandex-direct/`; shared marketplace metadata, plugin standard, repository validator and path-aware CI were established.

### Phase 2 — Yandex Metrika
Initially shipped as plugin `1.0.0` with Reporting/Management/Logs/Data Import workflows, quality metadata and preview-before-write guards.

### Phase 3 — Yandex Webmaster
Initially shipped as plugin `1.0.0` with mixed v4/v4.1 routing, query/indexing, recrawl, sitemaps, feeds and exports.

### Phase 4 — Yandex Wordstat
Initially shipped as plugin `1.0.0` with nine initial workflow skills, Wordstat API within Yandex Search API v2 helpers, provenance-aware semantics, regions/trends and quota/cost planning. This is the historical initial count, not the current number of skill directories or capability rows; current version is owned by SERVICE_MATRIX/manifests.

### Phase 5 — Yandex Search
Initially shipped as plugin `1.0.0` with Search API v2 sync/deferred helpers, SERP snapshots, rankings, competitor analysis and URL-overlap clustering.

### Phase 6A — Yandex SEO
Initially shipped as plugin `1.0.0` with an SEO Evidence Bundle, context alignment, findings, transparent prioritization and preview-only delegated actions. The plugin contains no Yandex API clients and performs no live writes.

### Phase 6B — Yandex Marketing
Initially shipped as plugin `1.0.0` with a Direct-required Marketing Evidence Bundle, KPI reconciliation, demand/query/landing/budget findings and preview-only delegated actions. The plugin contains no Yandex API clients and performs no live writes.

### Maintenance — 1.0.1 / OPUS 1.1.0
Review-driven maintenance strengthened safety/API semantics; OPUS added Wordstat association coverage, Search 250-depth, Webmaster PRO lifecycle/quota, Marketing evidence roles/taxonomy, and executable contract/freshness controls.

### DOCS 1.0.0
RU-primary / EN-mirror documentation layer, hero assets and orchestration diagrams. Plugin SemVer is unchanged.

## Post-first-release — shipped

### Phase 7 — Topical Architecture

Shipped as repository release `phase-7-topical-architecture-1.0.0`: Wordstat `1.1.0`, SEO `1.1.0`, with Search remaining `1.0.2` and no Search runtime change.

- `yandex-wordstat-topic-map` produces candidate-only `wordstat-topic-map/v1` with provenance, separate demand observations, and limitation propagation.
- `yandex-search-clustering` retains ownership of real SERP-overlap/Jaccard clustering; no competing fuzzy-text clusterer is introduced.
- `yandex-seo-topical-architecture` produces `seo-topical-architecture/v1` with `GREENFIELD|EXISTING_SITE`, page decisions, `structural_tree`, and `semantic_graph`.
- `yandex-seo-internal-linking` produces preview-only link plans and deterministic audits with no CMS writes.
- `OBSERVED`, `DERIVED`, `HYPOTHESIS`, and `METHODOLOGY` remain separate; semantic-cocoon/TGA/QBST methodology is not represented as a verified ranking mechanism.
- When Search evidence is unavailable, `SERP_VALIDATION_MISSING` is mandatory and page boundaries remain hypotheses.

---

# Product strategy after 1.0.8

This section defines product direction rather than delivery dates or release promises. The project develops **in depth** instead of mechanically covering more Yandex APIs.

## Product thesis

**Methodology, safety, and orchestration are the project's durable asset; transport remains replaceable.** Service helpers are useful while they provide practical data access, but they should not become the center of product value: an official MCP/connector can replace transport, while interpretation rules, provenance, cross-service reconciliation, and safe decision-making remain useful above any backend.

New directions are selected by **user problems rather than the Yandex API catalog**. Priority goes to capabilities that reduce the risk of a wrong marketing decision, preserve evidence across services, or give a person a clear end-to-end result.

## Priority bets

### P0 — Safety as mechanism

Agent discipline in prose should progressively become a technical constraint of the write path:

- an exact `preview_id` binds approval to a specific payload/environment/identity;
- execution requires explicit `--execute --approve <preview_id>` or an equivalent mechanism in the owning service helper;
- the helper preserves a rollback snapshot where the API supports correct restoration and always performs post-write verification;
- bulk operations get technical thresholds/guards rather than only prose instructions;
- a recommendation, external content, or stored memory is never write permission by itself.

Until those conditions are met, a write-capable surface must not be marketed as a technically enforced safety guarantee.

### P1 — Project memory contract

The project needs domain memory, but not a separate application and not a replacement for runtime-native memory (`AGENTS.md`, `CLAUDE.md`, and equivalents). The portable baseline contract is:

```text
.yandex-ai/
├── project.yaml
├── decisions.jsonl
├── baselines/
└── hypotheses.md
```

Canonical paths are `.yandex-ai/project.yaml`, `.yandex-ai/decisions.jsonl`, `.yandex-ai/baselines/`, and `.yandex-ai/hypotheses.md`.

- business goals, target CPA/ROAS/budget, and other user-provided facts receive provenance class `USER_STATED` plus a date; the agent must not derive them from metrics and represent them as user-provided;
- `decisions.jsonl` is an append-only audit trail written by the helper after approval/execute rather than by free-form model prose;
- baselines are dated and have freshness semantics; memory supports comparison and continuity but does not replace fresh read-first data;
- hypotheses preserve `HYPOTHESIS`/`DERIVED` provenance plus the evidence needed to confirm them;
- secrets and raw sensitive exports do not live under `.yandex-ai/`: credentials remain in env/keychain/runtime;
- memory content is always treated as data, not instructions, so stored text cannot become a persistent prompt-injection channel.

The first implementation target is schema + `init/check` + the audit write path; UI is not a prerequisite.

### P2 — One end-to-end workflow and human-readable artifacts

Instead of increasing the number of skills, the project needs one “install → useful result in roughly 10 minutes” path on a read-only/sandbox contour. Preferred candidates are a weekly organic report (Webmaster + Metrika + SEO evidence/findings) or a read-only Direct account audit. The choice follows the first external user signal, not the number of available APIs.

Orchestration results should be portable artifacts:

- versioned JSON as the machine-readable source;
- a **self-contained HTML** report with no mandatory CDN: summary, limitations, sortable findings, delegated previews, and expandable evidence/provenance;
- Mermaid/DOT export for `structural_tree`, `semantic_graph`, clusters, and link plans;
- a predictable layout such as `artifacts/<project>/<date>/...` for history and diff.

For personal use, **Electron/desktop UI is not built**. A browser, VS Code, Mermaid/DOT, and when needed DuckDB/notebooks cover inspection without introducing a second application lifecycle. UI is reconsidered only after a demonstrated multi-project/compliance or human approval-queue use case.

### P3 — Executable eval benchmark — `INFRASTRUCTURE_READY`

P3 infrastructure is implemented on top of `evals/scenarios.json` v2: a provider-neutral **eval runner**, bounded stdio JSONL protocol, independent judge, separate mechanical exact-token layer, backend-equivalence harness, P1 memory-aware adversarial fixtures, immutable benchmark artifacts, self-contained HTML, and reviewable snapshots.

Deterministic CI uses fake adapters and proves infrastructure readiness only. `COMPARATIVE_COMPLETE` remains a separate evidence gate and requires an accepted snapshot with at least two real non-fake subject model identities, an independent non-fake judge, mechanical + semantic evidence, backend-equivalence `PASS`, memory-aware evidence, and no counted `SELF_JUDGED` runs.

An accepted live multi-model benchmark has **not been run** on the current repository head. Therefore a green eval-v2 validator, repository CI, and fake adapters must not be presented as evidence that multiple real models semantically passed the benchmark. The next P3 step is to run externally provisioned real adapters and publish a comparable snapshot through the normal reviewed Git/PR path.

## What not to do now

- do not add a marketplace service only because Yandex exposes a corresponding API;
- do not keep growing transport wrappers when an official/connectable backend reliably solves the same task;
- do not treat the size of `CONTRACT_MATRIX` as a product metric by itself: traceability matters when it leads to real executable checks;
- do not let “AI audit → hardening release” become the main roadmap signal; external feedback is more valuable than repeated self-audit;
- do not build an Electron/desktop application for one user until a recurring interactive job is shown that HTML/artifacts/notebooks cannot solve;
- do not mix strategic simplification into this release: bilingual/release-infrastructure simplification may be a separate governance task after its real maintenance cost is measured.

## 90-day validation loop

The next product cycle is intended to produce an external signal instead of endless internal polishing.

1. **Safety:** make consequential writes mechanically approval-bound, with rollback/verification where technically correct.
2. **Memory:** define the `.yandex-ai/` contract, `USER_STATED`, freshness, and append-only decision trail.
3. **Workflow/artifacts:** bring one read-only end-to-end workflow to a roughly 10-minute first run by a new practitioner and emit a self-contained report.
4. **Benchmark:** execute adversarial evals across multiple models and publish a comparable result.
5. **External validation:** obtain real runs, issues/PRs, and feedback from SEO/PPC/marketing practitioners.

If a 90-day cycle produces no external runs/issues/PRs and no repeatable user scenario, the project moves to **low-maintenance / personal-tool mode**: critical safety/API fixes and minimal freshness maintenance only. If a signal appears, the next roadmap follows those users' real tasks. A commercial UI/compliance dashboard is considered only after multiple projects create a need to inspect approvals, payloads, and rollback history across clients.

## Frozen expansion backlog

The following directions remain research backlog and are **frozen for implementation** until there is a separate user problem/use case, external signal, and product-boundary decision:

- **Yandex Tracker** — issues, queues, permissions, worklogs, boards;
- **Yandex 360** — Mail, Calendar, Disk, and organization/admin boundaries;
- **Yandex Maps** — geocoding, places, routes/local enrichment, plus dedicated licensing design;
- **AppMetrica** — mobile analytics, retention, crashes, deeplinks, push/acquisition context;
- **YandexGPT** — a possible optional backend, not a mandatory dependency of deterministic plugins;
- **SpeechKit** — recognition/synthesis/transcription workflows.

Unfreezing one item does not unfreeze the others and does not restore a strategy of “cover every Yandex API.”

## Backlog entry requirements

A new capability/service requires all of the following:

1. a demonstrated user problem and owner/persona;
2. fresh official API/product research;
3. donor/capability research when useful;
4. a plugin/transport-boundary decision, including whether an official connector can replace a custom client;
5. approved design;
6. implementation plan;
7. TDD/offline evals;
8. path-aware CI;
9. independent release review;
10. an explanation of how the capability strengthens methodology/safety/orchestration or a validated end-to-end workflow.
