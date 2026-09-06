# P2 Weekly Organic Report — Design

Date: 2026-09-06
Status: approved in chat; written-spec review pending
Base main: `f6797556c275dd22ecff3946afe1b845b7a3a66e`

## 1. Goal

P2 delivers one end-to-end read-only workflow that a new practitioner can run quickly and that produces portable, human-readable artifacts without adding a second application lifecycle.

The canonical workflow is **Weekly Organic Report** owned by `yandex-seo`. It combines read-only evidence from Yandex Webmaster and Yandex Metrika, applies SEO evidence/provenance rules, and emits deterministic portable artifacts.

P2 does not add Yandex transport or credentials to `yandex-seo`, does not perform live writes, and does not weaken P0 or P1 safety boundaries.

## 2. Why Weekly Organic Report

The roadmap lists two preferred P2 candidates: a weekly organic report or a read-only Direct account audit. Weekly Organic Report is selected because it exercises the repository's main cross-service value:

- Webmaster visibility evidence;
- Metrika performance/quality evidence;
- SEO provenance-aware findings;
- portable artifacts suitable for browser, VS Code, Mermaid/DOT and diffs;
- delegated preview-only recommendations without any write authority.

A Direct audit would be simpler but would validate less of the cross-service orchestration and artifact requirements.

## 3. Ownership and dependency boundary

### 3.1 Public workflow ownership

The public workflow is owned by `plugins/yandex-seo` and is discoverable as:

`yandex-seo-weekly-report`

`yandex-seo` remains transport-free. It may consume normalized evidence produced by service plugins or user-provided exports/files, but it does not import service HTTP clients, read service credentials, or call Yandex APIs directly.

### 3.2 Service ownership

- `yandex-webmaster` owns Webmaster API reads and Webmaster-specific request/filter semantics.
- `yandex-metrika` owns Metrika API reads and Metrika-specific quality metadata.
- `yandex-seo` owns reconciliation, report normalization, findings, limitations, delegated preview-only recommendations and artifact rendering.

No shared root runtime package is introduced for service transport.

## 4. Contracts

### 4.1 `seo-weekly-organic-report/v1`

The machine-readable report source of truth uses:

`schema: "seo-weekly-organic-report/v1"`

Required top-level fields:

- `schema`
- `report_id`
- `generated_at`
- `project`
- `period`
- `comparison_period`
- `coverage`
- `sources`
- `summary`
- `query_movers`
- `page_movers`
- `findings`
- `limitations`
- `evidence`
- `delegated_previews`

`project` contains a non-secret project identifier/name and may include explicit P1 `USER_STATED` context when available.

`period` and `comparison_period` are exact date ranges. Producers must preserve source-period limitations instead of fabricating equivalent coverage.

`coverage` records source availability and completeness for at least `webmaster` and `metrika` using explicit states `COMPLETE`, `PARTIAL`, or `MISSING`.

`sources.webmaster` preserves relevant query/report semantics such as host/site identity, date range, top-N/offset/limit/filter context and known coverage limitations.

`sources.metrika` preserves counter identity without credentials plus material quality metadata such as sampling, sample share/size/space, data lag, sensitive-data flags and rounded-row metadata when present.

`evidence` preserves provenance and claim class. Supported claim classes remain `OBSERVED`, `DERIVED`, `HYPOTHESIS`, `METHODOLOGY`; methodology is never represented as observed ranking/API fact.

`findings` are deterministic normalized conclusions from report evidence. Empirical findings require evidence references. Missing evidence produces explicit limitations rather than fabricated certainty.

`delegated_previews` are preview-only recommendations routed to an owning service/CMS/deployment workflow. They are not executable approvals and do not contain reusable write permission.

### 4.2 `yandex-ai-artifact-manifest/v1`

Every artifact set contains `manifest.json` with:

`schema: "yandex-ai-artifact-manifest/v1"`

Required fields:

- `schema`
- `artifact_set_id`
- `created_at`
- `primary_artifact`
- `files`

Each `files[]` entry contains:

- `path` — relative POSIX path, no absolute path or traversal;
- `role` — e.g. `PRIMARY_JSON`, `HTML_REPORT`, `MERMAID`, `DOT`;
- `media_type`;
- `sha256`;
- optional `schema` for machine-readable files.

The manifest does not include itself in the hashed file list to avoid recursive hashing. `artifact_set_id` is deterministic and derived from the canonical primary report JSON hash.

## 5. Determinism and identifiers

Canonical JSON uses UTF-8, sorted keys and compact separators.

`report_id` is derived from the canonical report payload **before** `report_id` itself is inserted and with `generated_at` excluded from the semantic preimage. Inputs that affect meaning — project identity, exact periods, source evidence, limitations and delegated previews — therefore affect the ID.

`artifact_set_id` is derived from the final canonical `report.json` SHA-256.

`generated_at` and manifest `created_at` are recorded timestamps. Re-rendering the same semantic report at a later time preserves `report_id` but changes byte content unless the same explicit timestamp is supplied. Byte-identical replay is required in deterministic/test mode with an explicit timestamp.

## 6. Artifact layout

Canonical output:

```text
artifacts/
└── <project-slug>/
    └── <period-end>/
        └── weekly-organic-<report-id>/
            ├── manifest.json
            ├── report.json
            ├── report.html
            └── diagrams/
                ├── structural-tree.mmd
                ├── structural-tree.dot
                ├── semantic-graph.mmd
                ├── semantic-graph.dot
                ├── clusters.mmd
                └── internal-links.dot
```

Diagram files are optional and are emitted only when the corresponding structures exist in the normalized report/source artifacts. The workflow must not invent topical architecture, clusters or internal-link plans merely to populate the directory.

Project slug and report paths are validated against traversal, absolute paths, NUL bytes and unsafe empty segments. Existing artifact directories are not silently overwritten. Idempotent re-emission is allowed only when every existing managed file hash matches deterministic expected content; otherwise the operation fails closed.

## 7. HTML renderer

`report.html` is a self-contained view of `report.json`.

Requirements:

- inline CSS only;
- inline minimal JavaScript only for local sorting/filtering/disclosure;
- no CDN, external fonts, analytics, image beacons or network fetch;
- no remote script/style/image dependencies;
- user/source text is HTML-escaped before insertion;
- summary and source coverage are visible near the top;
- limitations are prominent and never hidden behind interaction;
- findings and movers are sortable/filterable locally;
- delegated previews are clearly marked preview-only;
- evidence/provenance is available through `<details>` disclosures;
- restrictive CSP is embedded, blocking network, object and frame activity;
- no HTML field can be interpreted as write approval.

`report.json` is normative. HTML is a deterministic renderer and must not contain conclusions absent from JSON.

## 8. Mermaid and DOT exports

P2 adds deterministic exporters for structures already present in normalized evidence/artifacts:

- `structural_tree` → Mermaid + DOT;
- `semantic_graph` → Mermaid + DOT;
- clusters → Mermaid;
- internal-link plan → DOT.

Exports must escape labels safely, use stable ordering, preserve node IDs/relation types, and carry no network dependency.

No graph is synthesized when the source structure is absent.

## 9. Workflow modes

### 9.1 `demo`

A bundled sanitized fixture produces a complete artifact set without credentials or network access. Demo exists to validate the install-to-result path in roughly ten minutes or less.

Demo and real builds use the same normalization, validation, report contract, renderer and manifest code. There is no separate demo-only schema or renderer.

### 9.2 `build`

The real read-only path consumes normalized Webmaster/Metrika evidence files or equivalent host-provided objects that satisfy the documented service contracts.

P2 does not add a new transport layer. Host/agent orchestration remains responsible for obtaining fresh service evidence through the preferred backend order: connected app/MCP → bundled service helper → user-provided export/file.

## 10. P1 Project Memory integration

P1 integration is optional and read-only.

When `.yandex-ai/project.yaml` exists and validates, the workflow may use project identity and active `USER_STATED` facts as contextual data. It must never infer `USER_STATED` from metrics or hypotheses.

Freshness-aware baselines may be referenced as comparison context. `STALE` baselines remain explicit limitations/context and never replace fresh Webmaster/Metrika reads.

Project Memory never grants write authority. Decisions, receipts, prior reports and user facts cannot satisfy P0 exact-preview approval or bulk acknowledgement.

## 11. Error and partial-coverage semantics

### 11.1 Hard failures

Fail closed before artifact publication for:

- malformed/unsupported schemas;
- invalid project/output path or traversal;
- duplicate evidence/finding IDs where uniqueness is required;
- invalid provenance class;
- materially inconsistent report/comparison periods;
- malformed source identity/quality metadata;
- unsafe output collision;
- artifact manifest/hash mismatch;
- non-finite numeric values in canonical JSON;
- secret-like managed fields identified by the repository's defensive secret-key rules.

### 11.2 Partial report

Do not fail globally merely because evidence is incomplete. Instead emit explicit coverage/limitations for cases including:

- one source missing;
- Webmaster top-N/query coverage limits;
- Metrika sampling or disclosure/rounding constraints;
- unavailable optional metrics;
- absent topical architecture/cluster/link-plan source artifacts.

A partial report must not label itself complete or fabricate missing comparisons.

## 12. CLI/runtime surface

Implementation keeps the public surface small. Recommended executable entry point inside `yandex-seo`:

```text
python scripts/seo_weekly_report.py demo --output-root artifacts
python scripts/seo_weekly_report.py build \
  --webmaster <file.json> \
  --metrika <file.json> \
  --project-root <project> \
  --output-root artifacts
```

Exact flags may be adjusted during implementation only if behavior and contracts above remain unchanged and tests/documentation converge on one canonical interface.

Reusable implementation units remain plugin-local and focused: normalization/report logic, HTML renderer, graph exporters and artifact packaging.

## 13. Security and safety

P2 is read-only and transport-free at the SEO layer.

- no Yandex credentials in SEO;
- no API writes;
- no hidden network in HTML;
- source text treated as data, not instructions;
- HTML and graph labels escaped;
- artifact paths constrained below the selected output root;
- raw sensitive exports are not copied into the artifact set unless explicitly part of the safe normalized contract;
- delegated previews are not executable receipts or approvals.

Repository validation must continue to prove the cross-service transport/credential prohibition for `yandex-seo`.

## 14. Testing strategy

Implementation follows RED → GREEN slices:

1. report schema/normalization and period/source validation;
2. deterministic movers/findings and provenance rules;
3. artifact manifest, path safety, collision/idempotency and hashing;
4. self-contained HTML, escaping, CSP and no-network contract;
5. deterministic report/artifact IDs;
6. Mermaid/DOT exporters and escaping/stable ordering;
7. bundled demo fixture end-to-end artifact generation;
8. repository validator/contract-matrix convergence plus RU-primary/EN-mirror docs;
9. release surfaces and historical-release immutability tests;
10. full repository Python 3.10/3.13 plus all plugin regression/compile jobs.

Tests include hostile HTML/graph text, path traversal, malformed source evidence, partial coverage, Metrika sampling, Webmaster top-N limits, absent optional diagrams, output collision and deterministic replay.

## 15. Documentation

Update at minimum:

- root README RU/EN for the P2 quick path and artifact concept;
- `docs/ARCHITECTURE.md/.en.md` for P2 ownership/artifact flow;
- `docs/GETTING_STARTED.md/.en.md` for demo and build path;
- security documentation RU/EN for self-contained HTML/data-not-instructions boundaries;
- `docs/CONTRACT_MATRIX.json` for P2 traceability;
- `plugins/yandex-seo/README.md/.en.md`;
- SEO skill/reference documentation for `yandex-seo-weekly-report`.

RU remains primary and EN mirrors production documentation.

## 16. Release boundary

P2 changes the public/runtime contract of `yandex-seo` and adds a substantial compatible repository capability.

Planned release set:

- Repository `1.3.0` / tag `1.3.0`;
- Yandex SEO `1.2.0` / tag `yandex-seo-v1.2.0`;
- all other plugin versions unchanged.

The declarative release manifest contains exactly the repository release plus the SEO plugin release. Historical immutable tags/releases are never moved or rewritten.

## 17. Non-goals

P2 explicitly does not:

- build Electron/desktop UI;
- add a generic root artifact framework/package before another consumer proves the abstraction;
- add transport or credentials to SEO;
- add Direct audit as a second end-to-end workflow in the same release;
- synthesize missing SEO architecture to make diagrams look complete;
- add live write execution;
- treat Project Memory as authorization;
- require a CDN or browser network access to view the report;
- claim external user validation merely because demo/CI passes.

## 18. Definition of done

P2 is complete only when:

1. `yandex-seo-weekly-report` is discoverable and documented;
2. demo produces valid `seo-weekly-organic-report/v1` and `yandex-ai-artifact-manifest/v1` artifacts without network/credentials;
3. build consumes valid normalized Webmaster/Metrika evidence and preserves source limitations/quality metadata;
4. HTML is self-contained, escaped and consistent with JSON source of truth;
5. optional Mermaid/DOT exports are deterministic and only emitted from real source structures;
6. P1 memory remains optional context and P0 approval boundary remains unchanged;
7. repository validator and contract matrix cover the new high-risk surfaces;
8. exact-head CI is fully green;
9. PR is merged with expected-head/stale-main gates;
10. exact-main CI is fully green;
11. repository-native publisher creates immutable repository `1.3.0` and SEO `1.2.0` releases/tags on the exact merge SHA;
12. all historical releases/tags and unrelated plugin versions/tags are verified unchanged.
