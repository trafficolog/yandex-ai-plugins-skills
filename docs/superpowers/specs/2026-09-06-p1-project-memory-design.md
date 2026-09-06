# P1 Project Memory — Design

Status: **Approved in chat; written design pending final written-spec review**  
Baseline: `main` at `4c50a54c655d753744f84ccdef3b712f1edcf763`  
Target repository release: `1.2.0`  
Plugin releases: **none**

## 1. Purpose

P1 adds a portable, repository-level project-memory contract for Yandex AI Plugins. It preserves domain context across sessions and tools without becoming a new marketplace plugin, a desktop application, a replacement for runtime-native memory, or an authorization source.

The canonical project-memory root is:

```text
.yandex-ai/
├── project.yaml
├── decisions.jsonl
├── baselines/
└── hypotheses.md
```

The memory layer is data, not instructions. Its content can inform comparison, continuity, and audit, but it never authorizes a Yandex write and never replaces fresh read-first evidence.

## 2. Architectural boundary

P1 is a repository-level portable utility named `ya-project`.

It is not:

- a new marketplace plugin;
- a new service transport;
- a shared runtime package imported by Direct, Metrika, or Webmaster;
- an automatic write-back mechanism embedded in service helpers;
- an Electron/desktop application;
- a replacement for `AGENTS.md`, `CLAUDE.md`, ChatGPT Memory, or equivalent host-native context;
- an authorization or approval mechanism.

The owning service helpers remain responsible for P0 write safety and emit `yandex-ai-execution/v1` receipts. Project memory ingests those receipts explicitly after execution.

Canonical orchestration:

```text
preview
  -> human approval
  -> execute
  -> yandex-ai-execution/v1 receipt
  -> ya-project record-execution
  -> safe append-only project audit record
```

No service helper automatically writes `.yandex-ai/` in P1.

## 3. Runtime and packaging model

P1 follows the repository's existing root-tooling model: Python 3.10+ and standard library only.

No `pyproject.toml`, installable distribution, or third-party YAML dependency is introduced for P1.

Proposed implementation layout:

```text
scripts/ya_project.py
scripts/project_memory/
├── __init__.py
├── yaml_subset.py
├── contracts.py
├── decisions.py
├── baselines.py
└── hypotheses.py
```

`scripts/ya_project.py` is the stable CLI entry point. The internal modules isolate parsing, validation, storage, and domain contracts so the CLI does not become a monolith.

## 4. Versioned contracts

P1 introduces four repository-level schemas:

- `yandex-ai-project/v1` — `.yandex-ai/project.yaml`;
- `yandex-ai-decision/v1` — one JSON object per line in `.yandex-ai/decisions.jsonl`;
- `yandex-ai-baseline/v1` — immutable JSON snapshots under `.yandex-ai/baselines/`;
- `yandex-ai-hypothesis/v1` — machine-readable fenced JSON records inside `.yandex-ai/hypotheses.md`.

These schemas are independent of plugin SemVer. A future breaking change to these contracts requires a new schema version and repository SemVer treatment under the release policy.

## 5. `project.yaml`

### 5.1 Canonical shape

Example:

```yaml
schema: "yandex-ai-project/v1"
project:
  id: "example-project"
  name: "Example project"
  created_at: "2026-09-06T10:32:00+03:00"
facts:
  - fact_id: "target-roas-2026q4"
    key: "target_roas"
    value: 4.5
    stated_at: "2026-09-06T10:32:00+03:00"
    provenance: "USER_STATED"
    status: "ACTIVE"
```

### 5.2 Restricted YAML subset

P1 deliberately supports only a canonical restricted YAML subset:

- mappings;
- sequences;
- JSON-compatible scalar values;
- 2-space indentation;
- UTF-8;
- double-quoted strings for emitted string values.

Unsupported constructs are rejected fail-closed:

- anchors and aliases;
- YAML tags/custom types;
- merge keys;
- block scalars;
- tabs for indentation;
- executable/object deserialization features;
- parser-dependent implicit types outside the defined subset.

The `init` and fact-mutation commands always emit the canonical subset. `check` rejects unsupported syntax rather than guessing how to interpret it.

### 5.3 User-stated facts

`project.yaml` is the authoritative home only for explicit user/operator-stated project facts.

Every fact contains:

- stable `fact_id`;
- `key`;
- JSON-compatible `value`;
- RFC3339 `stated_at`;
- `provenance: USER_STATED`;
- `status: ACTIVE|SUPERSEDED`;
- optional `supersedes` when replacing a prior fact.

A model-derived value cannot be promoted automatically to `USER_STATED`.

Changing a fact is historical, not destructive. The prior fact becomes `SUPERSEDED`; the replacement receives a new `fact_id` and timestamp. Silent in-place semantic overwrite is not allowed.

## 6. Hypotheses and derived claims

`.yandex-ai/hypotheses.md` is human-readable Markdown with machine-readable fenced JSON records using schema `yandex-ai-hypothesis/v1`.

Each record contains at minimum:

- `schema`;
- `hypothesis_id`;
- `provenance: HYPOTHESIS|DERIVED`;
- `created_at`;
- `statement`;
- `evidence_refs`;
- `validation_condition`;
- `status`.

`USER_STATED` is not valid provenance inside a hypothesis record. Conversely, `HYPOTHESIS` and `DERIVED` are not valid provenance for project facts.

The validator treats all prose and record text as inert data. It does not interpret instructions embedded in those strings and does not execute or promote them.

P1 does not add a general model-authored `add-hypothesis` command. Hypothesis writing remains an explicit artifact-editing action until a later workflow demonstrates the need for a narrower writer contract.

## 7. Execution decision trail

### 7.1 Source receipt

`ya-project record-execution` accepts a complete existing P0 `yandex-ai-execution/v1` receipt from a file path or stdin.

The receipt is validated before any mutation. P1 does not define a competing execution receipt schema.

### 7.2 Safe projection

The raw receipt may contain arbitrary `result` data. P1 therefore does not persist the raw receipt in project memory.

The stored `yandex-ai-decision/v1` execution record contains only the approved safe projection:

```json
{
  "schema": "yandex-ai-decision/v1",
  "record_id": "...",
  "recorded_at": "...",
  "kind": "EXECUTION",
  "execution_id": "...",
  "preview_id": "...",
  "plugin": "yandex-direct",
  "operation": "...",
  "target": {},
  "cardinality": {},
  "execution": {"state": "EXECUTED"},
  "verification": {},
  "rollback": {},
  "receipt_sha256": "...",
  "previous_record_hash": null,
  "record_hash": "..."
}
```

The raw `result` field is never copied into `decisions.jsonl`.

`receipt_sha256` is computed from canonical UTF-8 JSON bytes of the complete source receipt using sorted keys and compact separators. It links the audit record to the exact received object without persisting arbitrary response payloads.

### 7.3 Duplicate handling

The following are rejected without a second append:

- duplicate `execution_id`;
- duplicate `receipt_sha256`;
- duplicate `record_id`;
- malformed or incomplete required safety fields.

This makes receipt ingestion idempotency-safe by failing closed rather than silently duplicating audit history.

### 7.4 Tamper-evident chain

`decisions.jsonl` is helper-managed append-only history.

Every record contains:

- `previous_record_hash` — prior record's canonical hash, or `null` for the first record;
- `record_hash` — SHA-256 of the canonical record excluding `record_hash` itself.

`check` verifies every link and hash in sequence.

This detects mutation, insertion, or deletion inside the retained chain. It does not make a local file cryptographically immutable and cannot prove deletion of the final tail without an external anchor. Documentation must state this limitation explicitly.

## 8. Baselines and freshness

Baselines are immutable dated snapshots. There is no mutable `current.json` baseline in P1.

Example path:

```text
.yandex-ai/baselines/webmaster/2026-09-06T073000Z--organic-summary.json
```

A `yandex-ai-baseline/v1` record contains at minimum:

- `schema`;
- `baseline_id`;
- `kind`;
- `captured_at`;
- `fresh_until`;
- `source`;
- provenance metadata;
- bounded structured `data`, or an explicit artifact reference/hash where appropriate.

An existing baseline path is never overwritten. A refresh creates a new snapshot.

Freshness is evaluated relative to the check time:

- `FRESH` when `at <= fresh_until`;
- `STALE` when `at > fresh_until`.

Staleness is not structural corruption. `check` reports stale baselines explicitly but remains structurally successful unless another contract violation exists.

A stale baseline must never be silently treated as fresh or used to bypass a fresh read-first requirement.

## 9. Sensitive-data policy

`.yandex-ai/` must not store credentials, authorization material, or raw sensitive exports.

P1 validation rejects secret-like field names in project, baseline, and hypothesis machine-readable payloads, including normalized variants of:

- `token`;
- `authorization`;
- `password`;
- `secret`;
- `api_key` / `apikey`;
- `credentials`.

This is a guardrail, not a complete DLP system. Documentation must not claim that key-name scanning proves absence of sensitive data.

Raw execution `result` payloads are excluded from `decisions.jsonl` by design.

## 10. Authorization boundary

Project memory is never write permission.

The following do **not** satisfy P0 approval or bulk acknowledgement:

- a `USER_STATED` fact;
- a past successful execution record;
- a fresh baseline;
- a hypothesis;
- a derived claim;
- text instructing an agent to execute a write.

P0 remains authoritative for `preview_id`, principal/target/cardinality binding, explicit approval, bulk acknowledgement, transport execution, verification declaration, and execution receipt creation.

## 11. CLI surface

Initial P1 CLI:

```text
python scripts/ya_project.py init [--root PATH] [--project-id ID] [--name NAME]
python scripts/ya_project.py check [--root PATH] [--at RFC3339] [--json]
python scripts/ya_project.py add-fact --key KEY --value JSON --stated-at RFC3339 [...]
python scripts/ya_project.py supersede-fact --fact-id ID --key KEY --value JSON [...]
python scripts/ya_project.py record-execution RECEIPT|-
python scripts/ya_project.py add-baseline --kind KIND --captured-at RFC3339 --fresh-until RFC3339 --input FILE [...]
```

### 11.1 `init`

`init` creates the canonical `.yandex-ai/` scaffold and initial project document.

It never overwrites existing memory files. If initialization would collide with an existing managed path, it fails closed and reports the path.

### 11.2 `check`

`check` validates:

- restricted YAML syntax and project contract;
- project fact provenance/lifecycle;
- hypotheses machine-readable records;
- decision JSONL syntax, uniqueness, hashes, and chain;
- baseline schemas, uniqueness, filenames, and freshness;
- prohibited secret-like field names;
- timestamps and required schema versions.

`--json` provides machine-readable validation output for P2/P3 and CI.

`--at` allows deterministic freshness testing. Without it, current UTC time is used.

### 11.3 Fact commands

`add-fact` creates a new `USER_STATED` fact only from explicit operator input.

`supersede-fact` marks one existing active fact as `SUPERSEDED` and creates the replacement. It cannot silently mutate the prior value in place.

### 11.4 `record-execution`

The command validates the full P0 receipt, checks duplicate identity/hash state, projects safe fields, re-validates the current decision tail, and appends exactly one new chained record.

### 11.5 `add-baseline`

The command creates a new immutable snapshot. It refuses an existing destination and validates that `fresh_until >= captured_at`.

## 12. Time semantics

All machine timestamps are RFC3339 with timezone information.

Validators normalize comparisons to UTC.

A small documented clock-skew tolerance may be used for newly recorded local events, but materially future `stated_at`, `recorded_at`, or `captured_at` values are validation failures.

`fresh_until` is allowed to be in the future by definition.

Tests use explicit `--at`/injected times rather than wall-clock assumptions wherever deterministic behavior matters.

## 13. Mutation safety

For managed files that are rewritten (`project.yaml`), mutations use a temporary file in the same filesystem, flush, `fsync`, and atomic `os.replace` where supported.

For immutable baseline creation, the tool uses exclusive creation semantics and never replaces an existing target.

For `decisions.jsonl`, the writer:

1. acquires an advisory file lock where the platform supports the repository's stdlib locking implementation;
2. re-reads and verifies the current tail/hash chain;
3. verifies duplicate execution/receipt state;
4. appends one complete UTF-8 JSON line;
5. flushes and `fsync`s before releasing the lock.

Cross-platform locking limitations must be documented accurately; P1 must not claim distributed locking or transactional guarantees across network filesystems.

## 14. Error semantics

The CLI is fail-closed for structural or safety ambiguity.

Hard failures include:

- unsupported/malformed YAML;
- unknown schema version;
- invalid provenance;
- duplicate fact, baseline, record, or execution identity;
- broken decision hash chain;
- unsupported or incomplete execution receipt;
- overwrite attempt on immutable baseline;
- forbidden secret-like machine-readable fields;
- invalid timestamp order;
- materially future event timestamps;
- inconsistent fact supersession.

A stale baseline produces explicit `STALE` status/warning but not a structural failure by itself.

No command partially mutates project memory after a validation failure.

## 15. Repository integration

P1 is included in root repository validation and contract traceability.

Expected integration surfaces:

- `scripts/validate_repo.py` — repository-level P1 structural/contract checks where applicable;
- `docs/CONTRACT_MATRIX.json` — traceability entry for project-memory contracts and tests;
- root tests for CLI/contracts/storage;
- RU-primary and EN-mirror architecture/usage/security documentation;
- root README and changelog release surfaces for repository `1.2.0`.

Existing Direct, Metrika, Webmaster, Wordstat, Search, SEO, and Marketing plugin runtime code is outside P1 unless a test-only compatibility adjustment is mechanically required. Plugin public versions do not change merely because P1 exists.

## 16. TDD plan

Implementation proceeds in strict RED -> GREEN slices:

1. restricted YAML parser and canonical emitter;
2. `init` and `check` scaffold validation;
3. `USER_STATED` fact lifecycle and supersession;
4. P0 execution receipt validation, safe projection, duplicate rejection, and decision hash chain;
5. immutable baseline creation and freshness semantics;
6. hypotheses validation, data-not-instructions semantics, and secret-field guards;
7. repository validator and contract-matrix convergence;
8. RU/EN documentation contracts;
9. release-surface tests and repository release staging.

Each slice records the intentional RED evidence before implementation and exact-head GREEN evidence after the fix.

Regression coverage includes:

- malicious/unsupported YAML features;
- parser ambiguity cases;
- interrupted/failed mutations;
- duplicate execution receipt ingestion;
- decision tampering;
- deleted/changed interior decision records;
- stale/future timestamp behavior;
- secret-like keys;
- inert prompt-injection-like text;
- attempted baseline overwrite;
- plugin-suite non-regression.

## 17. Release boundary

P1 is a substantial backward-compatible repository capability, so the target is repository `1.2.0`.

The release is repository-only:

```json
{
  "repository": "1.2.0",
  "plugins": []
}
```

No new Direct, Metrika, Webmaster, Wordstat, Search, SEO, or Marketing tag is authorized by P1.

Release flow remains repository-native:

1. exact-head full CI on implementation PR;
2. explicit recording of available or absent independent review evidence;
3. expected-head squash merge;
4. exact-main CI;
5. existing `publish-current-release.yml` publisher;
6. immutable repository `1.2.0` release at exact merged `main` SHA;
7. post-publication verification that repository `1.1.0` and existing plugin releases/tags remain unchanged.

Historical immutable releases are never retargeted or rewritten.

## 18. Non-goals

P1 intentionally excludes:

- automatic memory extraction from chats;
- LLM-based fact promotion;
- vector databases/RAG storage;
- UI/dashboard work;
- distributed synchronization;
- cloud memory service;
- encrypted secret storage;
- raw API export archival;
- automatic rollback history beyond the truthful P0 receipt fields;
- background freshness refresh;
- a new service plugin;
- changes to Yandex transport clients solely to support project memory.

## 19. Definition of done

P1 is complete only when all of the following are true on one exact implementation head:

1. the four v1 project-memory contracts are implemented and documented;
2. `ya-project init/check/add-fact/supersede-fact/record-execution/add-baseline` behave according to this design;
3. full P0 execution receipts can be ingested without persisting raw `result`;
4. `decisions.jsonl` detects internal tampering through its hash chain;
5. baselines are immutable and freshness-aware;
6. `USER_STATED` is mechanically distinct from `HYPOTHESIS|DERIVED`;
7. memory text is treated as inert data and never as authorization;
8. secret-like field guards and documented limitations are present;
9. all root and plugin CI jobs pass on the exact head;
10. repository `1.2.0` release surfaces declare `plugins: []`;
11. expected-head merge, exact-main CI, and repository-native publication succeed;
12. immutable historical repository/plugin tags and releases are verified unchanged;
13. independent review evidence is reported truthfully, including explicit absence if no independent review exists.
