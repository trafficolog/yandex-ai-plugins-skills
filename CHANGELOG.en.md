# Changelog

[Русский](CHANGELOG.md) · [**English**](CHANGELOG.en.md)

All notable repository-level changes are documented here. Plugins use independent SemVer and keep their own changelogs.

## [1.1.0] — 2026-09-05

P0 executable write-safety release: the repository contract and three write-capable service plugins move to one approval/scale/receipt baseline without claiming unsupported read-back verification or rollback.

### Changed

- Direct, Metrika, and Webmaster use `yandex-ai-approval/v2`, binding exact target/request, authenticated-principal identity, cardinality, and declared safety capability; secrets are not exposed in previews.
- Repository safety threshold `20` is explicitly internal policy, not a Yandex API limit. Bulk `>20` and `UNKNOWN` scale require a separate `--ack-bulk` after exact `preview_id` approval and are blocked before transport without it.
- Successful consequential execution returns `yandex-ai-execution/v1`; current verification capability is truthfully declared as `RESPONSE_ONLY` / `UNVERIFIED`, with rollback `NOT_AVAILABLE`.
- Metrika preserves exact-file SHA-256, `artifact_rows`, and expense `risk_flags`; Logs/import remain single API operations (`KNOWN`, `items=1`) regardless of file row count.
- Webmaster preserves credential-safe binding for embedded URL Basic Auth through OAuth-keyed/domain-separated HMAC and exact cardinality for feed batches.
- Repository convergence tests and `CONTRACT_MATRIX.json` check behavioral agreement across the three local safety kernels without introducing a root shared runtime dependency.
- A standalone CLI mechanically proves exact preview binding but cannot prove that a human approved the preview in a separate later conversational turn; human provenance remains mandatory host/operator policy.

### Plugin releases

Direct `2.1.0`, Metrika `2.1.0`, Webmaster `2.1.0`.

### Other plugin versions unchanged

Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.10] — 2026-09-05

Repository-only supply-chain hardening release closing issue #43. Production runtime and plugin SemVer are unchanged.

### Changed

- Every external GitHub Action in the three active workflows is pinned to a full immutable 40-hex commit SHA instead of a mutable major tag.
- Active workflows also move to the Node 24 action generation: `actions/checkout` v5, `actions/setup-python` v6, and `actions/github-script` v8.
- Added `.github/dependabot.yml` for weekly `github-actions` update PRs so pinned SHA refreshes arrive as reviewable changes.
- Added a fail-closed regression contract rejecting mutable/non-SHA external `uses:` refs and requiring the Dependabot GitHub Actions update contract.
- Exact-head PR CI verifies that the previous Node 20 action-runtime deprecation warning is no longer emitted.
- Release intent remains repository-only: `.github/releases/release.json` contains `plugins: []`, so no new plugin tags are published.

### Plugin versions unchanged

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.9] — 2026-09-05

Repository-only release defining a depth-first product strategy after the Fable 5.1 review. Production runtime and plugin SemVer are unchanged.

### Changed

- ROADMAP shifts the primary direction from catalog-style Yandex API expansion toward methodology/safety/orchestration and user-problem-driven development; transport is treated as a replaceable layer.
- P0 prioritizes mechanically enforced write safety: exact `preview_id`/approval binding, rollback where technically correct, post-write verification, and bulk guards.
- P1 introduces the planned `.yandex-ai/` domain-memory contract: `project.yaml`, append-only `decisions.jsonl`, freshness-aware baselines, hypotheses, `USER_STATED`, no secrets, and memory-as-data semantics.
- P2 places one roughly 10-minute read-only end-to-end workflow plus portable artifacts (versioned JSON, self-contained HTML, Mermaid/DOT, predictable artifact folders) ahead of desktop UI; Electron is explicitly unnecessary at the personal-use stage.
- P3 evolves eval fixtures into an executable multi-model benchmark with semantic judging, backend equivalence, and memory-aware adversarial scenarios.
- Tracker, Yandex 360, Maps, AppMetrica, YandexGPT, and SpeechKit move to a Frozen expansion backlog until a distinct external user signal/use case justifies them.
- A 90-day external-validation loop is defined; without real runs/issues/PRs the project moves to low-maintenance/personal-tool mode.
- Release intent remains repository-only: `.github/releases/release.json` contains `plugins: []`, so no new plugin tags are published.

### Plugin versions unchanged

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.8] — 2026-09-05

Repository-only release closing the remaining Fable Round 2 governance/documentation gaps. Production runtime and plugin SemVer are unchanged.

### Changed

- Production-facing plugin documentation no longer treats `docs/superpowers/` as a normative source; historical implementation context remains available while canonical contracts live in production docs/tests.
- Current Wordstat naming is normalized, Russian remains the primary prose language, and RU/EN pairs are mechanically checked.
- `PLUGIN_STANDARD` adds `REQ-SKILL-CONTENT`, linking progressive disclosure, body semantics, and validator-enforced bounds under one explicit repository requirement.
- Long-form cross-service `authentication: ON_USE` / deferred-auth semantics are centralized in `ARCHITECTURE`; SEO/Marketing retain concise references plus the transport-ownership boundary.
- The ROADMAP separates initial shipped versions from current versions and explicitly leaves a model semantic eval runner/backend equivalence in backlog rather than treating structural fixture validation as semantic model proof.
- Added community-governance templates/Code of Conduct and a bilingual dated Fable Round 2 closure artifact.
- Release intent remains repository-only: `.github/releases/release.json` contains `plugins: []`, so no new plugin tags are published.

### Plugin versions unchanged

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.7] — 2026-09-05

Repository-only release for governance and contract-traceability hardening. Production runtime and plugin SemVer are unchanged.

### Changed

- `CONTRACT_MATRIX.json` moves to schema v2: file-only test links are replaced by exact Python selectors `test_file.py::test_function` / `test_file.py::TestClass::test_method`.
- Contract validation resolves selectors through `ast.parse` without importing or executing test modules, handles invalid Python/non-UTF8 fail-closed, and rejects statically skipped tests.
- `PLUGIN_STANDARD` RU/EN now carries 17 stable `REQ-ID` values with explicit enforcement ownership while preserving the boundary between mechanical validation and semantic review/policy.
- Added bilingual repository-owned review artifacts with exact PR #56 evidence and an explicit record of the exact-head Codex code-review quota limitation; absence of review is not represented as a clean review.
- Added `SECURITY.md` / `SECURITY.en.md` covering secret exposure, approval bypass, prompt-injection/data-as-instructions, transport ownership, immutable release history, and supply-chain concerns without inventing contact details or response SLAs.
- `docs/superpowers/` is explicitly classified as historical implementation context rather than canonical production authority; the RU/EN root README now links the dated review index.

### Plugin versions unchanged

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.6] — 2026-09-05

Repository-only release consolidating release infrastructure. Production runtime and plugin SemVer are unchanged.

### Changed

- Release intent now lives in declarative `.github/releases/release.json`; one `publish-current-release.yml` handles future repository and explicitly declared plugin releases without adding a workflow per release.
- The generic manifest validator checks schema, strict repository SemVer, notes paths, existing plugin directories, Codex/Claude manifest versions, canonical plugin tags, and release-set uniqueness.
- The hardened publisher preserves successful exact-main CI gating, stale-main no-op, common-target draft recovery, fail-closed remote tag probes, detached-target validation, immutable verification, and a safe rollback window.
- All 12 historical OPUS/FABLE/PHASE/DOCS/release-specific publisher workflows are removed from the active default-branch workflow set after their completed immutable releases; their exact source remains available through Git history/tags.
- Workflow-specific publisher tests are replaced by generic manifest/publisher/migration contracts while preserving reusable safety assertions.
- Release policy now requires every new release set to receive a new repository SemVer/tag; `plugins: []` means repository-only and creates no plugin tags.

### Plugin versions unchanged

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.5] — 2026-09-04

Repository-level documentation UX/governance release. Production runtime and plugin SemVer are unchanged.

### Changed

- Root README RU/EN are reworked as a human-first landing: marketplace purpose, plugin selection, safe quick start, practical workflow, project boundaries, and documentation navigation now come before low-level implementation details.
- Added mandatory bilingual `GETTING_STARTED`, `ARCHITECTURE`, `GLOSSARY`, and `RELEASE_POLICY`; repository validation treats them as key-doc pairs with reciprocal links, heading-level parity, and SemVer parity.
- Added `CONTRIBUTING.md` as a concise entrypoint into the production plugin standard, TDD/CI, and release rules.
- `PLUGIN_STANDARD` and the independent review guide now make the human release gate explicit: green CI is necessary but does not by itself authorize merge/release; publication happens only after the accepted change is on `main` and exact-SHA CI succeeds.
- Wordstat README RU/EN now uses the unambiguous name “Wordstat API within Yandex Search API v2” / «Wordstat API в составе Yandex Search API v2», without changing API behavior or plugin version `1.1.2`.
- Historical repository/plugin codenames and tags remain immutable history; the current repository line uses the single SemVer `1.0.5`.

### Release

- Added the repository-only `1.0.5` publisher using the existing hardened exact-main pattern: successful exact-SHA `CI` push, stale-main guard, immutable/draft recovery, fail-closed rollback, and repeated validator/test verification at the release target.
- The publisher creates no plugin tags and verifies that the manifest matrix remains Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

### Plugin versions unchanged

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.4] — 2026-09-04

FABLE 5.1 audit-3 repository maintenance release. Production plugin versions are unchanged.

### Fixed

- The SEO/Marketing cross-service transport boundary is now AST-checked across the complete Python tree, blocks transport/dynamic import roots and real Yandex endpoint forms, and handles unreadable/non-UTF8 source fail-closed.
- The generic `SKILL.md` contract now checks `name == directory`, marketplace-wide uniqueness, bounded description/size, and exact-preview/untrusted-data markers for `approval-required` writes.
- Plugin manifest versions are now reconciled against canonical RU/EN README, changelog, root version surfaces, and `SERVICE_MATRIX`; previously hidden SEO and Wordstat README drift from `1.1.1` to the already-published `1.1.2` is corrected without a new plugin release.
- Bilingual validation now recognizes `PHASE 7`/`FABLE` release markers and checks heading-level structure plus SemVer-set parity; the real drift it exposed in the root README and `PLUGIN_STANDARD` is corrected.
- The validator no longer pollutes its namespace with invalid marketplace paths, detects orphan plugin directories, recognizes `~/.agents/`, `$HOME/`, `${HOME}/`, and accepts BOM/CRLF/terminal-delimiter frontmatter.
- Added a repository-only immutable `1.0.4` publisher gated on a successful `CI` push for the exact `main` SHA; no plugin tags are created.

### Plugin versions unchanged

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [1.0.3] — 2026-09-04

FABLE 5.1 review-5 maintenance release after the published immutable `2.0.0` safety generation.

### Fixed

- Yandex Direct `2.0.1`: the Reports CLI no longer accepts OAuth through argv; the token is read only from `YANDEX_DIRECT_TOKEN`.
- Direct Reports HTTP errors are capped at 4096 bytes, invalid UTF-8 uses replacement decoding, and `URLError` becomes a secret-free operational failure; opener/sleep are injectable for deterministic tests.
- Reports `201/202 + retryIn` polling and one retry of the first HTTP `500` are preserved as a separate read-only async contract.
- `CONTRACT_MATRIX.json` adds explicit Direct contracts for Reports async transport, KPI provenance, and creation≠activation; `references/sources.md` is freshness-controlled with a canonical `Verified:` marker.
- Repaired false-positive SEO internal-linking tests: unknown endpoint and forced exact-match are now exercised with otherwise-valid candidate metadata and exact failure messages. Production SEO code is unchanged; SEO remains `1.1.2`.
- The repository secret scanner now checks committed `.env` / `.env.*` files while preserving safe placeholder semantics for `.env.example`.
- RU/EN root documentation is synchronized with the already-published immutable FABLE `2.0.0` generation and Direct `2.0.1`; verification examples use `python -m compileall -q scripts`.
- Safety documentation distinguishes executable helper guarantees from agent/operator policy: generic rollback snapshots and bulk `>20` enforcement are deferred to a separate safety design.

### Release matrix

Direct `2.0.1`, Metrika `2.0.0`, Webmaster `2.0.0`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [OPUS 1.1.3] — 2026-09-03

Phase 7 contract hardening from the new Opus 5 audit.

### Fixed

- Yandex SEO `1.1.2`: empirical boundary-changing decisions require Search-owned provenance; empirical `MERGE`/`REDIRECT` also require existing-page/URL evidence.
- `coverage.search=PARTIAL` is now exposed as `SERP_VALIDATION_PARTIAL`; Search cluster ingress is validated and bridge/source limitations propagate downstream automatically.
- `METHODOLOGY` is now a first-class qualitative Evidence Bundle kind but cannot masquerade as quantitative metric evidence.
- Not-evaluated `link_plan`/`audits` are distinct from evaluated empty results (`null` vs explicitly attached `[]`).
- Internal-link audit defines orphaning by missing inbound links, preserves/flags duplicates, and treats a rootless `BRIDGE` without inbound links as orphan/broken bridge. Explicit `ROOT` and a legacy parentless node without `page_role` remain exempt; explicit non-root roles are still audited for orphaning. Self-links are reported as `SELF_LINK` and excluded from valid/inbound reachability counts.
- Yandex Wordstat `1.1.2`: topic-map query normalization uses Unicode NFKC + casefold + whitespace folding without invented demand summation.
- The legacy OPUS 1.1.0 publisher now uses the canonical `trafficolog/yandex-ai-plugins-skills` repository guard; a repository-level regression prevents the old name from returning.

### Published plugin matrix

Direct `1.0.1`, Metrika `1.0.3`, Webmaster `1.0.3`, Wordstat `1.1.2`, Search `1.0.2`, SEO `1.1.2`, Marketing `1.1.0`.

## [OPUS 1.1.2] — 2026-09-03

Residual hardening for the remaining findings from the final Opus 5 audit.

### Fixed

- Yandex Metrika `1.0.3` closes the Direct expense provenance gap for CSV files without `UTMSource` / `UTMMedium`: official `TrafficSourceDetail=yandex_direct_star` is blocked as `DIRECT_DUPLICATION_RISK`.
- Insufficient expense provenance now fails closed as `DIRECT_SOURCE_UNVERIFIED`; generic `TrafficSource=ad` without source detail requires explicit review/`--allow-direct-risk` instead of silently passing.
- Explicit non-Direct source detail remains allowed; arbitrary provider labels such as `MyDirect` are not declared Direct from substring matching alone.
- The shared-code rule now includes an installability/distribution gate: duplication plus a stable interface is insufficient for a root runtime package until independently installed plugins can reliably receive the shared dependency.
- N3/N5/N6/N8 were re-verified against current contracts/docs and are not reopened: traceability is not semantic proof, cross-service `ON_USE` matches the marketplace schema, Webmaster `state`/`download_url` are verified, and the Marketing spec is already normatively reconciled.

### Published plugin matrix

Direct `1.0.1`, Metrika `1.0.3`, Webmaster `1.0.3`, Wordstat `1.1.1`, Search `1.0.2`, SEO `1.1.1`, Marketing `1.1.0`.

## [1.0.2] — 2026-09-03

Repository-level maintenance release for release-infrastructure hardening after Phase 7.

### Fixed

- The legacy `OPUS 1.1.1` publisher now recognizes a fully published historical release set at one ancestor SHA and completes later `main` runs as a verified no-op.
- A partial OPUS release set resumes against its already-published common SHA instead of being moved to current `main`.
- Inconsistent or multi-SHA historical release state remains a hard failure; historical tags are never retargeted or mutated.
- Added regression contract `tests/test_opus_publisher_idempotency.py` for immutable/no-op/partial-recovery semantics.
- Added the repository `1.0.2` publisher, gated on a successful `CI` push for the exact `main` SHA.

### Plugin versions unchanged

Direct `1.0.1`, Metrika `1.0.2`, Webmaster `1.0.3`, Wordstat `1.1.1`, Search `1.0.2`, SEO `1.1.1`, Marketing `1.1.0`.

## [PHASE 7 1.0.1] — 2026-09-03

Post-release hardening patch for the Topical Architecture / Semantic Cocoons baseline.

### Fixed

- Yandex Wordstat `1.1.1` rejects duplicate `seeds[].seed`, keeping `source_seed` an unambiguous provenance key.
- Yandex Wordstat `1.1.1` rejects candidate topic self-relations (`from_topic_id == to_topic_id`).
- Yandex SEO `1.1.1` normalizes `structural_tree.nodes` through an explicit field whitelist and does not carry caller execution/recommendation state (`decision`, `status`, `write`, `execution_id`).
- Yandex SEO `1.1.1` requires list-typed candidate-link `evidence`; scalar/object payloads are rejected before preview serialization.
- Service ownership, Search `1.0.2`, the transport-free SEO boundary, and preview-only internal-link semantics are unchanged.

### Published plugin matrix

Direct `1.0.1`, Metrika `1.0.2`, Webmaster `1.0.3`, Wordstat `1.1.1`, Search `1.0.2`, SEO `1.1.1`, Marketing `1.1.0`.

## [PHASE 7 1.0.0] — 2026-09-02

Evidence-first Topical Architecture / Semantic Cocoons release.

### Architecture

- Yandex Wordstat `1.1.0` adds `yandex-wordstat-topic-map` and `wordstat-topic-map/v1`: candidate-only topic maps, provenance-preserving query deduplication, separate demand observations, and explicit limitation propagation.
- Yandex Search remains `1.0.2` and the sole owner of real SERP-overlap/Jaccard clustering; Phase 7 adds no competing fuzzy-text clusterer and makes no Search runtime change.
- Yandex SEO `1.1.0` adds `yandex-seo-topical-architecture` and `seo-topical-architecture/v1` for `GREENFIELD|EXISTING_SITE`, page decisions, and separate `structural_tree` / `semantic_graph` layers.
- Yandex SEO `1.1.0` adds `yandex-seo-internal-linking`: preview-only link planning and deterministic audit with no CMS writes.

### Evidence and safety contracts

- `OBSERVED`, `DERIVED`, `HYPOTHESIS`, and `METHODOLOGY` remain distinct; semantic-cocoon/TGA/QBST methodology is not represented as a verified ranking mechanism.
- Without Search evidence, `SERP_VALIDATION_MISSING` is mandatory and page boundaries remain hypotheses.
- Wordstat associations/co-occurrence are not represented as final page boundaries and are never aggregated into fictitious total demand.
- SEO remains transport-free: no new Yandex HTTP clients, credentials, or live mutations.
- `CONTRACT_MATRIX.json` pins `wordstat.topic-map-candidate-boundary`, `seo.topical-architecture-structural-tree`, `seo.topical-architecture-evidence-classes`, and `seo.internal-linking-preview-only`.

### Published plugin matrix

Direct `1.0.1`, Metrika `1.0.2`, Webmaster `1.0.3`, Wordstat `1.1.0`, Search `1.0.2`, SEO `1.1.0`, Marketing `1.1.0`.

## [OPUS 1.1.1] — 2026-09-02

Follow-up fix release from the final Opus 5 review.

### Repository controls

- The 90-day freshness gate is no longer a time bomb for unrelated PRs: age is a hard failure for a changed freshness-controlled reference, while a scheduled strict workflow checks the entire controlled set and synchronizes a dedicated GitHub issue.
- `CONTRACT_MATRIX.json` now includes Metrika Direct-expense duplication guard, Webmaster indexing archive lifecycle, SEO unknown Webmaster impressions, and Marketing quality metadata shape contracts.
- `PLUGIN_STANDARD` explicitly defines the contract matrix as a traceability index rather than semantic proof and states that eval fixtures are structurally validated but are not yet executed against a model.
- Cross-service `authentication: ON_USE` is documented as schema-compatible deferred-auth metadata with no local credential/transport surface.
- Marketing taxonomy is reconciled with the actual nine executable finding types plus an explicit deferred set through a normative spec amendment.

### Plugin releases

- Yandex Metrika `1.0.2`: the Direct-expense source-label guard recognizes tokenized labels while retaining the independent CSV UTM risk layer.
- Yandex Webmaster `1.0.3`: the official indexing archive `state` field (`IN_PROGRESS` / `DONE` / `FAILED`) is re-verified and pinned by regression/traceability contracts.
- Direct `1.0.1`, Wordstat `1.0.2`, Search `1.0.2`, SEO `1.0.1`, and Marketing `1.1.0` are unchanged.

## [DOCS 1.0.0] — 2026-09-02

### Changed

- Russian became the primary language for root README/CHANGELOG and key repository documentation; English versions are published as `.en.md` mirrors.
- All seven production plugins gained bilingual README/CHANGELOG pairs without changing plugin SemVer.
- Added local RU/EN SVG hero banners under `docs/assets/readme/`.
- Added Mermaid orchestration diagrams to `yandex-seo` and `yandex-marketing` READMEs, making evidence flow, the no-transport boundary, and delegated previews explicit.
- Repository validation now checks bilingual pairs, reciprocal language links, and identical release markers across RU/EN changelogs.
- `docs/PLUGIN_STANDARD.md` now treats bilingual documentation as a production contract.

### Plugin versions unchanged

Direct `1.0.1`, Metrika `1.0.1`, Webmaster `1.0.2`, Wordstat `1.0.2`, Search `1.0.2`, SEO `1.0.1`, Marketing `1.1.0`.

## [OPUS 1.1.0] — 2026-09-02

Contract-hardening milestone: Wordstat association coverage cap, Search 250-result depth, Webmaster PRO lifecycle/quota semantics, Marketing evidence roles/taxonomy, and executable repository contract/freshness controls.

## [1.0.1] — 2026-09-02

Review-driven maintenance covering safe-by-default mutations/API contracts, omission-preserving Metrika attribution, cross-service evidence/context semantics, URL identity, evals, and dependency-aware CI.

## [1.0.0] — 2026-09-02

First complete marketplace release: Direct, Metrika, Webmaster, Wordstat, Search, SEO and Marketing, with a shared plugin standard, safety lifecycle, offline tests/evals, and path-aware CI.
