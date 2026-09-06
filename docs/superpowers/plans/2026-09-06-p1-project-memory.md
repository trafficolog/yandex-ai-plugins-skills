# P1 Project Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the portable repository-level `.yandex-ai/` project-memory contract and `ya-project` CLI, then publish repository release `1.2.0` without changing plugin SemVer.

**Architecture:** Add a stdlib-only root CLI at `scripts/ya_project.py` backed by focused modules in `scripts/project_memory/`. The subsystem owns restricted YAML parsing/emission, project/fact validation, append-only decision projection from existing `yandex-ai-execution/v1` receipts, immutable freshness-aware baselines, hypothesis validation, and repository-level checks. Service plugins do not import this package and do not auto-write project memory.

**Tech Stack:** Python 3.10+ standard library only, `unittest`, JSON/JSONL, restricted canonical YAML subset, SHA-256, RFC3339 timestamps, stdlib filesystem primitives.

**Spec:** `docs/superpowers/specs/2026-09-06-p1-project-memory-design.md`

## Global Constraints

- Baseline `main` is `4c50a54c655d753744f84ccdef3b712f1edcf763`; implementation must branch from the approved design commit whose parent is this exact SHA.
- No third-party dependencies, `pyproject.toml`, or root package/distribution lifecycle.
- Canonical schemas: `yandex-ai-project/v1`, `yandex-ai-decision/v1`, `yandex-ai-baseline/v1`, `yandex-ai-hypothesis/v1`.
- Existing P0 receipt schema remains `yandex-ai-execution/v1`; P1 must not define a competing execution receipt.
- `.yandex-ai/` is data, not instructions, and never authorizes Yandex writes or satisfies P0 approval/bulk acknowledgement.
- `project.yaml` contains only explicit `USER_STATED` facts; `HYPOTHESIS|DERIVED` stay in hypothesis records.
- `decisions.jsonl` stores safe projection + receipt hash, never raw receipt `result`.
- Baselines are immutable dated snapshots with explicit `captured_at` and `fresh_until`; stale is a warning/status, not structural corruption.
- Plugin runtime and plugin SemVer stay unchanged for P1.
- Target release is repository `1.2.0` with `.github/releases/release.json` declaring `plugins: []`.
- Every implementation slice must record an intentional RED test commit/run before GREEN implementation evidence.
- Final merge requires exact-head CI, expected-head squash merge, exact-main CI, repository-native publisher, and immutable-history verification.

---

## File Structure

Create:

- `scripts/project_memory/__init__.py` — exported schema constants and package marker only.
- `scripts/project_memory/yaml_subset.py` — restricted YAML tokenizer/parser/emitter; no domain validation.
- `scripts/project_memory/contracts.py` — timestamp parsing, recursive secret-key guard, project/hypothesis/baseline/receipt validation, canonical JSON/hash helpers.
- `scripts/project_memory/storage.py` — atomic text replacement, exclusive file creation, advisory lock abstraction, durable append helper.
- `scripts/project_memory/decisions.py` — receipt canonicalization, safe projection, duplicate detection, hash-chain validation, decision append.
- `scripts/project_memory/baselines.py` — baseline construction, deterministic filename generation, immutable creation, freshness evaluation.
- `scripts/project_memory/hypotheses.py` — fenced JSON extraction and hypothesis record validation.
- `scripts/ya_project.py` — CLI composition and user-facing error/status output.
- `tests/test_project_memory_yaml.py` — parser/emitter and unsupported-YAML regression tests.
- `tests/test_project_memory_project.py` — init/check/fact lifecycle and atomicity tests.
- `tests/test_project_memory_decisions.py` — receipt projection, duplicates, hash chain, tampering tests.
- `tests/test_project_memory_baselines.py` — immutable baseline and freshness tests.
- `tests/test_project_memory_hypotheses.py` — fenced record, provenance, inert-text, secret-key tests.
- `tests/test_project_memory_cli.py` — subprocess CLI behavior and exit/status contracts.
- `tests/test_repository_1_2_0_release_surfaces.py` — repository-only release contract.
- `.github/releases/1.2.0.md` — repository release notes.

Modify:

- `scripts/validate_repo.py` — add repository-level P1 source/contract presence validation without requiring a user project `.yandex-ai/` directory in this repository.
- `docs/CONTRACT_MATRIX.json` — add repository P1 traceability contracts.
- `docs/ARCHITECTURE.md`, `docs/ARCHITECTURE.en.md` — project-memory layer, authorization boundary, orchestration.
- `docs/GETTING_STARTED.md`, `docs/GETTING_STARTED.en.md` — `ya-project init/check/record-execution/add-baseline` workflow.
- `SECURITY.md`, `SECURITY.en.md` — data-not-instructions, secret-field guard limitations, no authorization from memory.
- `README.md`, `README.en.md` — repository `1.2.0` and P1 capability summary.
- `CHANGELOG.md`, `CHANGELOG.en.md` — repository `1.2.0` entry.
- `.github/releases/release.json` — repository `1.2.0`, `plugins: []`.
- Current-state release/version tests only where they intentionally track the repository's current release.

---

### Task 1: Restricted YAML subset

**Files:**
- Create: `scripts/project_memory/__init__.py`
- Create: `scripts/project_memory/yaml_subset.py`
- Test: `tests/test_project_memory_yaml.py`

**Interfaces:**
- Produces: `YamlSubsetError`, `loads(text: str) -> object`, `dumps(value: object) -> str`.
- Consumers: `contracts.py`, `ya_project.py`, Task 2 tests.

- [ ] **Step 1: Write failing parser/emitter tests**

Tests must cover canonical project maps/sequences/scalars, round-trip stability, 2-space indentation, double-quoted emitted strings, and rejection of tabs, anchors (`&`), aliases (`*`), tags (`!`), merge keys (`<<:`), block scalars (`|`/`>`), and unsupported implicit scalar forms.

Core expectations:

```python
from scripts.project_memory.yaml_subset import YamlSubsetError, dumps, loads

class RestrictedYamlTests(unittest.TestCase):
    def test_round_trip_project_shape(self):
        value = {
            "schema": "yandex-ai-project/v1",
            "project": {"id": "demo", "name": "Demo", "created_at": "2026-09-06T07:30:00Z"},
            "facts": [{"fact_id": "f1", "key": "target_roas", "value": 4.5, "stated_at": "2026-09-06T07:30:00Z", "provenance": "USER_STATED", "status": "ACTIVE"}],
        }
        rendered = dumps(value)
        self.assertEqual(loads(rendered), value)
        self.assertIn('schema: "yandex-ai-project/v1"', rendered)

    def test_unsafe_yaml_features_are_rejected(self):
        for text in ("a: &x 1\nb: *x\n", "a: !python/object 1\n", "a: |\n  x\n", "<<: {}\n", "a:\t1\n"):
            with self.subTest(text=text), self.assertRaises(YamlSubsetError):
                loads(text)
```

- [ ] **Step 2: Commit and run RED**

Commit only the test file and empty package marker. Push branch and require CI/root test failure because `yaml_subset.py`/interfaces do not exist yet. Record exact commit SHA and CI run ID.

- [ ] **Step 3: Implement minimal deterministic parser/emitter**

Implementation constraints:

```python
class YamlSubsetError(ValueError):
    pass

def loads(text: str) -> object:
    # Reject unsupported lexical constructs before parsing.
    # Parse indentation-based maps/sequences recursively.
    # Scalars: double-quoted JSON strings, true/false/null, strict JSON number grammar.
    # Reject duplicate mapping keys.
    ...

def dumps(value: object) -> str:
    # Accept only dict/list/str/int/float/bool/None.
    # Emit mapping keys from a conservative identifier grammar and values deterministically.
    # Preserve insertion order; strings via json.dumps(..., ensure_ascii=False).
    ...
```

Do not implement general YAML 1.1/1.2 compatibility.

- [ ] **Step 4: Run focused tests and full root suite**

Expected: YAML tests PASS and no existing root regressions.

- [ ] **Step 5: Commit GREEN**

Commit message: `feat: add restricted project yaml codec`.

---

### Task 2: Project scaffold, validation, and USER_STATED facts

**Files:**
- Create: `scripts/project_memory/contracts.py`
- Create: `scripts/project_memory/storage.py`
- Create: `scripts/ya_project.py`
- Test: `tests/test_project_memory_project.py`
- Test: `tests/test_project_memory_cli.py`

**Interfaces:**
- Produces:
  - `PROJECT_SCHEMA = "yandex-ai-project/v1"`
  - `parse_rfc3339(value: str) -> datetime`
  - `validate_project(doc: object, *, at: datetime) -> list[str]`
  - `find_secret_like_paths(value: object) -> list[str]`
  - `atomic_write_text(path: Path, text: str) -> None`
  - CLI commands `init`, `check`, `add-fact`, `supersede-fact`.
- Consumes: `yaml_subset.loads/dumps`.

- [ ] **Step 1: Write failing project/fact tests**

Cover:

- `init` creates exactly `.yandex-ai/project.yaml`, empty `decisions.jsonl`, `baselines/`, and `hypotheses.md`.
- `init` refuses collisions and never overwrites.
- generated project document validates.
- only `USER_STATED` provenance is accepted in facts.
- duplicate `fact_id` rejected.
- more than one ACTIVE fact for the same `key` rejected unless history is properly superseded.
- `supersede-fact` marks old fact `SUPERSEDED`, creates a new ID, and sets `supersedes`.
- materially future `created_at`/`stated_at` rejected using injected `--at`.
- secret-like nested keys rejected.
- prompt-injection-like string values remain valid inert strings and are never parsed as commands.
- failed mutation leaves original `project.yaml` byte-identical.

- [ ] **Step 2: Commit and run RED**

Push tests only; record exact RED SHA/run.

- [ ] **Step 3: Implement timestamp, secret-key, project lifecycle, and atomic storage**

Required behavior:

```python
PROJECT_SCHEMA = "yandex-ai-project/v1"
FUTURE_SKEW = timedelta(minutes=5)

_SECRET_NORMALIZED = {"token", "authorization", "password", "secret", "apikey", "credentials"}

def normalize_field_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())

def find_secret_like_paths(value: object, path: str = "$") -> list[str]:
    # recurse through dict/list; reject normalized key matches/suffixes conservatively
    ...
```

`atomic_write_text` must create a same-directory temp file, write UTF-8, flush, `os.fsync`, `os.replace`, then best-effort fsync the parent directory on POSIX.

- [ ] **Step 4: Implement CLI scaffold/fact commands**

`main(argv=None) -> int` uses `argparse`; domain validation errors return non-zero with concise stderr. `--root` defaults to current directory. `--value` is strict JSON parsed with `json.loads`.

- [ ] **Step 5: Run focused + root tests and commit GREEN**

Commit message: `feat: add project memory scaffold and facts`.

---

### Task 3: Execution receipt ingestion and decision hash chain

**Files:**
- Create: `scripts/project_memory/decisions.py`
- Modify: `scripts/project_memory/contracts.py`
- Modify: `scripts/project_memory/storage.py`
- Modify: `scripts/ya_project.py`
- Test: `tests/test_project_memory_decisions.py`
- Test: `tests/test_project_memory_cli.py`

**Interfaces:**
- Produces:
  - `EXECUTION_SCHEMA = "yandex-ai-execution/v1"`
  - `DECISION_SCHEMA = "yandex-ai-decision/v1"`
  - `canonical_json_bytes(value: object) -> bytes`
  - `sha256_hex(data: bytes) -> str`
  - `validate_execution_receipt(receipt: object) -> list[str]`
  - `safe_execution_projection(receipt: dict[str, object], *, recorded_at: str, previous_record_hash: str | None, record_id: str) -> dict[str, object]`
  - `validate_decision_chain(path: Path) -> tuple[list[dict[str, object]], list[str]]`
  - `record_execution(memory_root: Path, receipt: dict[str, object], *, now: datetime) -> dict[str, object]`.

- [ ] **Step 1: Write failing decision tests**

Use a realistic P0 receipt fixture with `result` containing sensitive-looking response data. Assert:

- exact schema required;
- required fields include execution/preview/plugin/operation/target/cardinality/execution/verification/rollback/result;
- `execution.state == "EXECUTED"`;
- raw `result` never appears in the stored decision line;
- `receipt_sha256` changes when raw result changes;
- duplicate `execution_id` or receipt hash fails before append;
- first `previous_record_hash` is null;
- second record points to first `record_hash`;
- editing an interior record breaks `check`;
- appending malformed JSON breaks `check`;
- record hash is deterministic canonical JSON without its own `record_hash` field.

- [ ] **Step 2: Commit and run RED**

Record exact failing SHA/run.

- [ ] **Step 3: Implement safe projection and chain validation**

The stored projection may contain only:

```python
SAFE_FIELDS = (
    "execution_id", "preview_id", "plugin", "operation", "target",
    "cardinality", "execution", "verification", "rollback",
)
```

Add `schema`, `record_id`, `recorded_at`, `kind="EXECUTION"`, `receipt_sha256`, `previous_record_hash`, then compute `record_hash` over canonical JSON excluding `record_hash`.

Never store `result`.

- [ ] **Step 4: Implement durable append with advisory locking**

Use a small cross-platform stdlib abstraction:

- POSIX: `fcntl.flock(fd, LOCK_EX)`;
- Windows: `msvcrt.locking` when available;
- unsupported platform: explicit single-process best-effort mode documented by a returned capability flag; never claim distributed locking.

Within the lock, re-read/validate complete chain, re-check duplicates, append one complete JSON line, flush/fsync.

- [ ] **Step 5: Wire `record-execution RECEIPT|-` and run GREEN**

`-` reads stdin. Parse strict JSON. Validation/mutation errors must not append bytes.

Commit message: `feat: record safe execution decisions`.

---

### Task 4: Immutable baselines and freshness

**Files:**
- Create: `scripts/project_memory/baselines.py`
- Modify: `scripts/project_memory/contracts.py`
- Modify: `scripts/ya_project.py`
- Test: `tests/test_project_memory_baselines.py`

**Interfaces:**
- Produces:
  - `BASELINE_SCHEMA = "yandex-ai-baseline/v1"`
  - `baseline_filename(kind: str, captured_at: datetime) -> str`
  - `build_baseline(...) -> dict[str, object]`
  - `freshness_state(baseline: dict[str, object], *, at: datetime) -> str`
  - `validate_baseline(...) -> list[str]`.

- [ ] **Step 1: Write failing baseline tests**

Cover valid creation, deterministic UTC filename, `fresh_until >= captured_at`, immutable exclusive create, duplicate baseline ID detection, FRESH at equality, STALE one instant after expiry, stale warning without structural failure, future `captured_at` failure, secret-like nested key rejection, and artifact reference/hash shape.

- [ ] **Step 2: Commit and run RED**

Record exact SHA/run.

- [ ] **Step 3: Implement baseline domain and immutable storage**

Canonical path:

```python
kind_dir = memory_root / "baselines" / normalized_kind
filename = captured_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ") + f"--{normalized_kind}.json"
```

Use exclusive create (`open(..., "x")` or lower-level `O_CREAT|O_EXCL`) and fsync. Do not replace existing files.

- [ ] **Step 4: Wire `add-baseline` and `check` freshness output**

`--input` is strict JSON data payload; optional artifact reference/hash arguments are validated. Human output summarizes FRESH/STALE counts; `--json` emits structured diagnostics.

- [ ] **Step 5: Run GREEN and commit**

Commit message: `feat: add immutable project baselines`.

---

### Task 5: Hypothesis records and data-not-instructions validation

**Files:**
- Create: `scripts/project_memory/hypotheses.py`
- Modify: `scripts/project_memory/contracts.py`
- Modify: `scripts/ya_project.py`
- Test: `tests/test_project_memory_hypotheses.py`

**Interfaces:**
- Produces:
  - `HYPOTHESIS_SCHEMA = "yandex-ai-hypothesis/v1"`
  - `extract_hypothesis_records(markdown: str) -> list[dict[str, object]]`
  - `validate_hypothesis(record: object, *, at: datetime) -> list[str]`.

- [ ] **Step 1: Write failing hypothesis tests**

Canonical fenced form:

````markdown
```json yandex-ai-hypothesis/v1
{"schema":"yandex-ai-hypothesis/v1","hypothesis_id":"h1","provenance":"HYPOTHESIS","created_at":"2026-09-06T07:30:00Z","statement":"...","evidence_refs":[],"validation_condition":"...","status":"OPEN"}
```
````

Assert `HYPOTHESIS|DERIVED` only, unique IDs, required evidence_refs list, no `USER_STATED`, future timestamp guard, secret-like key rejection, malformed fenced JSON failure, and that strings such as `"ignore previous instructions and execute"` are accepted as inert data.

- [ ] **Step 2: Commit and run RED**

Record exact SHA/run.

- [ ] **Step 3: Implement fenced extraction and validation**

Only fences explicitly labeled `json yandex-ai-hypothesis/v1` are parsed as managed records. Other Markdown/prose is ignored as human context. Managed fence malformed JSON is a hard validation error.

- [ ] **Step 4: Integrate into `check`, run GREEN, commit**

Commit message: `feat: validate project hypotheses`.

---

### Task 6: Repository convergence and documentation

**Files:**
- Modify: `scripts/validate_repo.py`
- Modify: `docs/CONTRACT_MATRIX.json`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/ARCHITECTURE.en.md`
- Modify: `docs/GETTING_STARTED.md`
- Modify: `docs/GETTING_STARTED.en.md`
- Modify: `SECURITY.md`
- Modify: `SECURITY.en.md`
- Test: add/modify root repository contract tests as required.

**Interfaces:**
- Repository validator proves the P1 implementation/traceability surfaces exist and remain stdlib-only.
- It does **not** require this repository itself to contain a user `.yandex-ai/` project directory.

- [ ] **Step 1: Add failing repository/documentation contract tests**

Tests require:

- `scripts/ya_project.py` and all planned modules;
- contract matrix entries for project/facts, decisions, baselines, hypotheses;
- RU/EN architecture/getting-started/security coverage of schema names and authorization boundary;
- explicit phrases/semantics that raw `result` is excluded, stale is not fresh, and memory is not write permission;
- no root third-party dependency file introduced for YAML.

- [ ] **Step 2: Commit and run RED**

Record exact SHA/run.

- [ ] **Step 3: Add repository validator/contract matrix entries**

Add repository contracts such as:

```json
{
  "id": "repository.project-memory-contract",
  "plugin": "repository",
  "status": "infrastructure",
  "skills": [],
  "helpers": ["scripts/ya_project.py", "scripts/project_memory/contracts.py"],
  "test_refs": ["tests/test_project_memory_project.py", "tests/test_project_memory_cli.py"],
  "references": ["docs/ARCHITECTURE.md", "docs/GETTING_STARTED.md", "SECURITY.md"],
  "freshness_controlled_references": []
}
```

and separate decision/baseline/hypothesis rows if needed for precise traceability.

- [ ] **Step 4: Write RU-primary / EN-mirror documentation**

Document exact commands, canonical `.yandex-ai/` tree, provenance rules, tamper-evident limitations, secret-field guard limitations, locking limitations, and P0/P1 authorization separation.

- [ ] **Step 5: Run root + all plugin suites and commit GREEN**

Commit message: `docs: document P1 project memory` or split code/docs commits if CI evidence remains exact per head.

---

### Task 7: Repository 1.2.0 release staging

**Files:**
- Create: `tests/test_repository_1_2_0_release_surfaces.py`
- Create: `.github/releases/1.2.0.md`
- Modify: `.github/releases/release.json`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `CHANGELOG.md`
- Modify: `CHANGELOG.en.md`
- Modify: only current-state release tests that intentionally track the current repository version.

**Interfaces:**
- Declared release set contains one repository item, version/tag `1.2.0`, and exactly `plugins: []`.

- [ ] **Step 1: Add intentional release RED test**

Require:

```python
self.assertEqual(manifest["repository"]["version"], "1.2.0")
self.assertEqual(manifest["repository"]["tag"], "1.2.0")
self.assertEqual(manifest["plugins"], [])
```

Also require root README/CHANGELOG RU+EN and `.github/releases/1.2.0.md` to expose the new version and P1 summary.

- [ ] **Step 2: Commit and run RED**

The failures should be only missing/stale `1.2.0` release surfaces. Record SHA/run.

- [ ] **Step 3: Stage release surfaces atomically**

Release notes must state:

- new portable `.yandex-ai/` memory contract and `ya-project` CLI;
- stdlib-only restricted YAML;
- USER_STATED / HYPOTHESIS / DERIVED separation;
- safe receipt projection + tamper-evident decision chain;
- immutable freshness-aware baselines;
- memory is not write permission;
- no plugin releases in this set.

Do not change plugin manifests/readmes/changelogs versions.

- [ ] **Step 4: Fix only genuinely stale current-state tests**

Historical release tests remain historical and must not be rewritten to current manifests. Any current-state test that freezes `1.1.0` may be updated only if its purpose is explicitly today's release surface.

- [ ] **Step 5: Run exact-head full CI and commit GREEN**

All root Python versions and seven plugin jobs must pass before PR finalization.

---

### Task 8: PR, merge, publication, and immutable-history verification

**Files:**
- No new implementation files unless CI/review reveals a real defect.

**Interfaces:**
- Final exact head → expected-head squash merge → exact main SHA → publisher.

- [ ] **Step 1: Re-check stale-main and scope**

Verify implementation branch base/behind state against live `main`. If `main` moved, stop merge and reconcile; do not claim prior exact-head CI applies to a new head.

- [ ] **Step 2: Open/update PR with evidence**

PR body records design/spec/plan paths, RED/GREEN SHAs and run IDs, exact final CI, repository-only SemVer boundary, and explicit review evidence state. Do not invent independent review.

- [ ] **Step 3: Obtain final exact-head CI**

All required jobs must be completed/success on the exact PR head.

- [ ] **Step 4: Merge with expected head SHA**

Use squash merge and `expected_head_sha=<final head>`.

- [ ] **Step 5: Verify exact-main CI**

Require CI `head_sha == merge_sha` and all jobs success.

- [ ] **Step 6: Let repository-native publisher publish declared `1.2.0`**

Do not create/move tag or release manually. Verify publisher exact target is merge SHA and final release is `draft=false`, `immutable=true`, `prerelease=false`.

- [ ] **Step 7: Verify immutable history**

At minimum re-check:

- repository `1.1.0` tag/release still targets `4c50a54c655d753744f84ccdef3b712f1edcf763` and remains immutable;
- `yandex-direct-v2.1.0`, `yandex-metrika-v2.1.0`, `yandex-webmaster-v2.1.0` tags/releases remain on `4c50a54c655d753744f84ccdef3b712f1edcf763` and immutable;
- unchanged Wordstat/Search/SEO/Marketing tags are not retargeted;
- no plugin release/tag is created by repository `1.2.0`.

- [ ] **Step 8: Add final PR audit comment**

Record merge SHA, exact-main CI, publisher run, release ID/tag, immutable-history verification, and independent review evidence state.

---

## Plan Self-Review

- Spec coverage: all approved design sections are mapped to Tasks 1–8, including restricted YAML, fact provenance, hypotheses, receipts, hash chain, baselines/freshness, secret guard, authorization boundary, mutation safety, docs, and release process.
- Placeholder scan: no TBD/TODO/"implement later" steps remain; code-facing tasks include concrete interfaces and assertions.
- Type/name consistency: CLI command names and schema constants match the approved design; P0 execution schema is reused verbatim; repository release is consistently `1.2.0` and `plugins: []`.
- Scope: no plugin runtime modification, new service, desktop UI, installable root package, generalized DLP, distributed lock, or automatic hypothesis writer is included.
