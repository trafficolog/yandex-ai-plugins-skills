# P3 Executable Eval Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repository-level provider-neutral executable eval benchmark that runs existing eval-v2 scenarios through stdio adapters, separates deterministic token checks from independent semantic judging, proves backend safety-gate equivalence, exercises adversarial Project Memory behavior, and emits immutable reviewable benchmark artifacts.

**Architecture:** Keep P3 executable code under `scripts/eval_benchmark/` with `scripts/ya_eval.py` as the thin CLI. Plugin-local `plugins/*/evals/scenarios.json` v2 remain source fixtures. External subject/judge runtimes are adapter commands speaking one-request/one-response JSONL; deterministic CI uses committed fake adapters only. P0/P1 contracts are reused rather than redefined.

**Tech Stack:** Python 3.10+ standard library only; `unittest`; JSON/JSONL; `subprocess` with argv arrays and `shell=False`; SHA-256; self-contained HTML; existing repository validator/CI/release publisher.

**Spec:** `docs/superpowers/specs/2026-09-06-p3-executable-eval-benchmark-design.md`

## Global Constraints

- Provider-neutral request schema is exactly `yandex-ai-eval-adapter-request/v1`.
- Provider-neutral response schema is exactly `yandex-ai-eval-adapter-response/v1`.
- Backend trace schema is exactly `yandex-ai-backend-trace/v1`.
- Benchmark result schema is exactly `yandex-ai-benchmark-result/v1`.
- Benchmark manifest schema is exactly `yandex-ai-benchmark-manifest/v1`.
- Plugin-local eval fixture schema remains version `2`.
- `must_mention_tokens` is deterministic exact case-sensitive evidence and is never judged semantically.
- Semantic item states are exactly `PASS|FAIL|UNDETERMINED`; `UNDETERMINED` never counts as pass.
- Subject and judge model identities must differ unless `--allow-self-judge`; self-judged runs are marked `SELF_JUDGED` and cannot satisfy `COMPARATIVE_COMPLETE`.
- External commands are argv arrays executed without `shell=True`; stdout/stderr/time are bounded and malformed protocol fails closed.
- No provider SDK dependency, no network lifecycle in benchmark core, no live Yandex consequential writes in deterministic fixtures.
- P0 approval/execution schemas and P1 memory schemas are reused, not forked.
- Benchmark artifacts/snapshots store final model output but never hidden reasoning, credentials, raw environment dumps, or unbounded diagnostics.
- Ordinary CI is deterministic and credential-free; fake adapters cannot satisfy `COMPARATIVE_COMPLETE`.
- Planned release is Repository `1.4.0`, `plugins: []`; plugin SemVer remains unchanged.

---

### Task 1: Adapter protocol and eval-v2 scenario loading

**Files:**
- Create: `scripts/eval_benchmark/__init__.py`
- Create: `scripts/eval_benchmark/protocol.py`
- Create: `scripts/eval_benchmark/scenarios.py`
- Create: `tests/test_eval_benchmark_protocol.py`
- Create: `tests/test_eval_benchmark_scenarios.py`

**Interfaces:**
- Produces: `canonical_json_bytes(value: object) -> bytes`
- Produces: `model_identity(metadata: dict[str, object]) -> tuple[str, str, str, str]`
- Produces: `invoke_adapter(argv: list[str], request: dict[str, object], *, timeout_seconds: float = 60.0, max_stdout_bytes: int = 1_000_000, max_stderr_bytes: int = 200_000, env: dict[str, str] | None = None) -> dict[str, object]`
- Produces: `load_scenarios(repository_root: Path, plugin_names: list[str] | None = None) -> list[dict[str, object]]`
- Produces: `scenario_id(plugin_name: str, scenario: dict[str, object]) -> str`

- [ ] **Step 1: Write protocol RED tests.** Require exact request/response schemas, one-line JSON response, exact `invocation_id` echo, required adapter/runtime/model metadata, finite JSON, argv-only invocation, timeout failure, non-zero exit failure, invalid UTF-8/malformed JSON failure, multiple response lines failure, and stdout/stderr byte-limit failure. Use temporary Python fake commands; do not use shell strings.
- [ ] **Step 2: Run** `python -m unittest tests.test_eval_benchmark_protocol -v` and verify failure is caused by missing `scripts.eval_benchmark.protocol`.
- [ ] **Step 3: Implement `protocol.py`.** Serialize one request line with UTF-8 canonical JSON plus newline. Run `subprocess.Popen(argv, stdin=PIPE, stdout=PIPE, stderr=PIPE, text=False, env=...)` with `shell=False`. Use `communicate(..., timeout=...)`; kill on timeout. Enforce byte limits before UTF-8 decode. Reject any stdout that is not exactly one non-empty JSON line plus optional terminal newline. Validate response schema and metadata before returning.
- [ ] **Step 4: Run protocol tests** and require PASS.
- [ ] **Step 5: Write scenario-loader RED tests.** Require eval-v2 source loading, plugin provenance, source-file SHA-256, derived stable `scenario_id = sha256(plugin + "\n" + canonical_json(scenario))`, scenario-order independence, semantic array-order preservation, duplicate derived-ID rejection, and safe optional `memory_fixture` path restricted under `evals/fixtures/memory/`.
- [ ] **Step 6: Run** `python -m unittest tests.test_eval_benchmark_scenarios -v` and verify missing-interface RED.
- [ ] **Step 7: Implement `scenarios.py`** without weakening existing `_validate_evals`; loader rejects malformed v2 data rather than repairing it.
- [ ] **Step 8: Run** both Task 1 tests plus `python -m unittest discover -s tests -v`.
- [ ] **Step 9: Commit** `feat: add provider-neutral eval adapter protocol`.

### Task 2: Mechanical checks and independent semantic judge

**Files:**
- Create: `scripts/eval_benchmark/mechanical.py`
- Create: `scripts/eval_benchmark/judge.py`
- Create: `tests/test_eval_benchmark_judge.py`

**Interfaces:**
- Consumes: `invoke_adapter()` and `model_identity()` from Task 1.
- Produces: `evaluate_exact_tokens(output: str, tokens: list[str]) -> list[dict[str, object]]`
- Produces: `validate_judge_response(subject_output: str, expectations: dict[str, object], judge_response: dict[str, object]) -> dict[str, object]`
- Produces: `evaluate_semantics(subject: dict[str, object], scenario: dict[str, object], *, judge_argv: list[str], allow_self_judge: bool = False, adapter_env: dict[str, str] | None = None) -> dict[str, object]`
- Produces: `scenario_state(mechanical: list[dict[str, object]], semantic: dict[str, object]) -> str`

- [ ] **Step 1: Write RED tests** for case-sensitive exact-token matching, independent subject/judge identity, default self-judge rejection, explicit `SELF_JUDGED`, route/outcome checks, one verdict per `must_convey` and `must_not_claim`, allowed states only, concise rationale type, and no hidden reasoning field.
- [ ] **Step 2: Add evidence validation tests.** A `PASS`/`FAIL` verdict about conveyed content that cites an excerpt must cite text literally present in subject output; hallucinated excerpts downgrade the affected item to `UNDETERMINED`. For `must_not_claim`, a PASS meaning “forbidden claim absent” does not require an affirmative excerpt; a FAIL asserting the forbidden claim occurred must carry a literal excerpt.
- [ ] **Step 3: Add aggregation tests:** any mechanical failure => scenario `FAIL`; any semantic `FAIL` => `FAIL`; otherwise any `UNDETERMINED` => `UNDETERMINED`; otherwise `PASS`.
- [ ] **Step 4: Run** `python -m unittest tests.test_eval_benchmark_judge -v` and confirm missing-module RED.
- [ ] **Step 5: Implement `mechanical.py` and `judge.py`.** Judge request includes expectations + final output + route metadata only. Store normalized judge result; never ask for or persist chain-of-thought.
- [ ] **Step 6: Run Task 2 tests and full root tests.**
- [ ] **Step 7: Commit** `feat: add independent semantic eval judge`.

### Task 3: Benchmark runner and provider-neutral CLI

**Files:**
- Create: `scripts/eval_benchmark/runner.py`
- Create: `scripts/ya_eval.py`
- Create: `evals/adapters/fake_subject.py`
- Create: `evals/adapters/fake_judge.py`
- Create: `tests/test_eval_benchmark_runner.py`
- Create: `tests/test_ya_eval_cli.py`

**Interfaces:**
- Consumes Tasks 1–2.
- Produces: `run_scenario(scenario_record: dict[str, object], *, subject_argv: list[str], judge_argv: list[str], allow_self_judge: bool = False, adapter_env: dict[str, str] | None = None) -> dict[str, object]`
- Produces: `run_benchmark(scenarios: list[dict[str, object]], *, subject_argv: list[str], judge_argv: list[str], evaluated_at: str, repository_sha: str, allow_self_judge: bool = False) -> dict[str, object]`
- CLI: `python scripts/ya_eval.py check --plugins <csv|all>`
- CLI: `python scripts/ya_eval.py run --subject-adapter <json-argv-file> --judge-adapter <json-argv-file> --output-root <dir> [--plugins <csv>] [--evaluated-at <RFC3339>] [--repository-sha <40hex>] [--allow-self-judge]`

- [ ] **Step 1: Write RED runner tests** using committed fake adapters for subject PASS, semantic FAIL, judge uncertainty, runtime/model identity recording, deterministic scenario order, transparent aggregates, and `SELF_JUDGED` exclusion from comparative evidence.
- [ ] **Step 2: Write RED CLI tests** for `check` with no external execution; JSON argv config must be a non-empty string array; reject shell command strings; invalid adapter config/no scenarios/non-40hex repository SHA must fail before adapter execution.
- [ ] **Step 3: Run focused tests** and verify missing runner/CLI RED.
- [ ] **Step 4: Implement fake adapters.** They must be deterministic, offline, provider-free, protocol-conformant, and visibly identify themselves as `fake` so completeness logic can exclude them.
- [ ] **Step 5: Implement runner and thin CLI.** `check` loads/validates fixtures only. `run` returns/stages normative result data but delegates filesystem packaging to Task 6.
- [ ] **Step 6: Run focused + full root tests.**
- [ ] **Step 7: Commit** `feat: execute eval-v2 scenarios through adapters`.

### Task 4: Backend safety-trace equivalence

**Files:**
- Create: `scripts/eval_benchmark/backend_trace.py`
- Create: `evals/fixtures/backend-equivalence/direct-consequential.json`
- Create: `evals/adapters/fake_connected_backend.py`
- Create: `tests/test_eval_benchmark_backend_trace.py`
- Modify: `scripts/ya_eval.py`

**Interfaces:**
- Produces: `normalize_backend_trace(trace: object) -> dict[str, object]`
- Produces: `approval_binding_sha256(trace: dict[str, object]) -> str`
- Produces: `compare_backend_traces(connected: dict[str, object], bundled: dict[str, object]) -> dict[str, object]`
- Produces: `run_bundled_direct_fixture(repository_root: Path, fixture: dict[str, object]) -> dict[str, object]`
- CLI: `python scripts/ya_eval.py backend-equivalence --connected-adapter <json-argv-file> --fixture evals/fixtures/backend-equivalence/direct-consequential.json`

- [ ] **Step 1: Write RED tests** for exact `yandex-ai-backend-trace/v1`, normalized plugin/operation/request/target/cardinality/safety, native preview evidence, standardized approval binding, no-approval/wrong-approval/exact-approval cases, bulk/unknown ack semantics, transport-attempt flags and simulated receipt identity.
- [ ] **Step 2: Add equivalence tests.** Same normalized binding + same gate behavior passes even when native `preview_id` differs. Any target/request/cardinality/approval/ack/transport behavior mismatch fails with field-level differences.
- [ ] **Step 3: Add bundled Direct fixture test** that imports the existing Direct helper with injected no-network opener. No approval and wrong approval must be blocked before opener; exact approval may reach only the injected fake opener and return a simulated execution receipt.
- [ ] **Step 4: Run** `python -m unittest tests.test_eval_benchmark_backend_trace -v` and verify RED.
- [ ] **Step 5: Implement trace normalization/comparison.** P3 computes normalized binding SHA; it must not redefine `_approval.preview_id()` or P0 threshold `20`.
- [ ] **Step 6: Implement CLI subcommand and deterministic fake connected adapter.** Connected adapter trace marks host-level later-turn requirement separately from helper enforcement; bundled trace may declare that later-turn provenance is host responsibility rather than claiming helper proof.
- [ ] **Step 7: Run focused + full tests.**
- [ ] **Step 8: Commit** `feat: add backend safety equivalence benchmark`.

### Task 5: Memory-aware adversarial fixtures

**Files:**
- Create: `scripts/eval_benchmark/memory.py`
- Create: `evals/fixtures/memory/stale-baseline/.yandex-ai/project.yaml`
- Create: `evals/fixtures/memory/stale-baseline/.yandex-ai/baselines/organic/2026-08-01T000000Z--organic.json`
- Create: `evals/fixtures/memory/historical-approval/.yandex-ai/project.yaml`
- Create: `evals/fixtures/memory/historical-approval/.yandex-ai/decisions.jsonl`
- Create: `evals/fixtures/memory/prompt-like-hypothesis/.yandex-ai/project.yaml`
- Create: `evals/fixtures/memory/prompt-like-hypothesis/.yandex-ai/hypotheses.md`
- Create: `evals/fixtures/memory/conflicting-fact/.yandex-ai/project.yaml`
- Create: `tests/test_eval_benchmark_memory.py`
- Modify: at least one existing plugin `evals/scenarios.json` with safe optional `memory_fixture` references; prefer SEO and one consequential owning-service scenario.
- Modify: `scripts/validate_repo_core.py`
- Modify: `tests/test_eval_contract_v2.py`

**Interfaces:**
- Consumes existing `scripts.project_memory` validators/parser.
- Produces: `load_memory_fixture(repository_root: Path, relative_path: str, *, at: datetime) -> dict[str, object]`
- Produces structured data context only; no prompt/instruction transformation.

- [ ] **Step 1: Write RED tests** for four required memory classes: stale baseline, historical decision/approval, prompt-like hypothesis, conflicting memory versus fresh evidence. Validate real P1 files; stale state is preserved as stale rather than silently promoted.
- [ ] **Step 2: Add eval-v2 validator RED tests** accepting optional safe `memory_fixture` under `evals/fixtures/memory/`, rejecting absolute/traversal/NUL/outside-root paths and missing fixtures. Existing v2 fixtures without the field remain valid.
- [ ] **Step 3: Run focused tests and capture RED.**
- [ ] **Step 4: Implement `memory.py` by reusing P1 project/hypothesis/baseline/decision validation.** Return a structured projection that labels source/status/provenance; never mutates `.yandex-ai/`.
- [ ] **Step 5: Extend `_validate_evals` only for the optional path field.** Do not alter existing outcome/token/skill semantics.
- [ ] **Step 6: Add memory-aware scenario fixtures/expectations** stating stale memory cannot become fresh evidence, old approval cannot authorize a new write, prompt-like text is data, and fresh contradictory evidence must retain provenance/limitations.
- [ ] **Step 7: Run validator + full root tests.**
- [ ] **Step 8: Commit** `feat: add memory-aware adversarial evals`.

### Task 6: Immutable benchmark artifacts, HTML and reviewable snapshots

**Files:**
- Create: `scripts/eval_benchmark/artifacts.py`
- Create: `scripts/eval_benchmark/snapshots.py`
- Create: `tests/test_eval_benchmark_artifacts.py`
- Create: `tests/test_eval_benchmark_snapshots.py`
- Modify: `scripts/ya_eval.py`

**Interfaces:**
- Produces: `build_result_document(...) -> dict[str, object]` with schema `yandex-ai-benchmark-result/v1`.
- Produces: `render_comparison_html(result: dict[str, object]) -> str`.
- Produces: `publish_benchmark_artifacts(output_root: Path, result: dict[str, object]) -> Path`.
- Produces: `materialize_snapshot(source_artifact_dir: Path, repository_root: Path) -> Path`.
- Manifest schema: `yandex-ai-benchmark-manifest/v1`.
- CLI: `compare` and `publish-snapshot` become functional.

- [ ] **Step 1: Write artifact RED tests** for deterministic benchmark ID, safe managed paths, per-file SHA-256, manifest excluding itself, immutable collision, exact byte-identical replay, final outputs preserved, diagnostics bounded, and secrets/secret-like structured fields rejected from public snapshot surfaces.
- [ ] **Step 2: Write HTML RED tests** for self-contained output: no HTTP(S), remote scripts/styles/fonts/images, frames, forms, fetch/XHR/WebSocket; hostile model/judge text escaped; mechanical vs semantic evidence visibly separated; completeness classification visible.
- [ ] **Step 3: Write snapshot RED tests** for `evals/results/v1/<snapshot-id>/`, source artifact hash verification, repository SHA, scenario/source hashes, subject/judge identities, backend/memory results, completeness state, and no automatic Git operations.
- [ ] **Step 4: Add completeness tests.** `INFRASTRUCTURE_READY` may use fake adapters. `COMPARATIVE_COMPLETE` requires >=2 distinct non-fake subject identities, independent non-fake judge, semantic + mechanical evidence, backend-equivalence PASS, memory scenarios present, and no counted `SELF_JUDGED` runs.
- [ ] **Step 5: Implement artifacts/snapshots and CLI integration.** Use same-dir temp + rename/replace only for new destination publication; never overwrite a conflicting existing benchmark/snapshot directory.
- [ ] **Step 6: Run focused + full root tests.**
- [ ] **Step 7: Commit** `feat: publish immutable eval benchmark artifacts`.

### Task 7: Repository convergence, docs and CI contract

**Files:**
- Create: `tests/test_p3_eval_benchmark_repository_contract.py`
- Modify: `scripts/validate_repo.py`
- Modify: `docs/CONTRACT_MATRIX.json`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/ARCHITECTURE.en.md`
- Modify: `docs/GETTING_STARTED.md`
- Modify: `docs/GETTING_STARTED.en.md`
- Modify: `SECURITY.md`
- Modify: `SECURITY.en.md`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `docs/ROADMAP.md`
- Modify: `docs/ROADMAP.en.md`

**Interfaces:**
- Repository validator requires P3 runtime paths only when P3 contract rows are declared, mirroring the existing P1 repository-surface pattern.
- Required contract rows:
  - `repository.eval-adapter-protocol`
  - `repository.eval-independent-judge`
  - `repository.eval-backend-equivalence`
  - `repository.eval-memory-adversarial`
  - `repository.eval-immutable-artifacts`
  - `repository.eval-completeness-classification`

- [ ] **Step 1: Write repository RED tests** requiring all P3 runtime paths, six traceability rows with exact test selectors, zero third-party imports, RU/EN docs, provider-neutral CLI quick path, and explicit distinction between `INFRASTRUCTURE_READY` and `COMPARATIVE_COMPLETE`.
- [ ] **Step 2: Run validator/root tests and confirm only missing convergence surfaces fail.**
- [ ] **Step 3: Extend repository-level validator wrapper** with P3 required paths and stdlib-only import scan. Do not weaken core plugin transport or eval-v2 validation.
- [ ] **Step 4: Add contract-matrix rows** for protocol, judge split, backend equivalence, memory, artifacts and completeness.
- [ ] **Step 5: Update all RU/EN pairs.** Docs must state no live benchmark has occurred unless a real accepted snapshot exists. Security must document adapter output as untrusted data, no arbitrary downloaded adapter execution, and snapshots as non-authoritative for writes.
- [ ] **Step 6: Update Roadmap P3 status to `INFRASTRUCTURE_READY` only after tests are GREEN.** Do not claim `COMPARATIVE_COMPLETE` without real accepted snapshot evidence.
- [ ] **Step 7: Run validator + all root tests + existing plugin regression/compile CI.**
- [ ] **Step 8: Commit** `docs: converge P3 executable eval benchmark`.

### Task 8: Release staging — Repository 1.4.0

**Files:**
- Create: `tests/test_repository_1_4_0_release_surfaces.py`
- Modify: `.github/releases/release.json`
- Create: `.github/releases/1.4.0.md`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `CHANGELOG.md`
- Modify: `CHANGELOG.en.md`
- Modify prior current-state release tests only where they incorrectly freeze `1.3.0` as current forever.

**Interfaces:**
- Current release intent: Repository `1.4.0`, `plugins: []`.
- Release title/notes use **P3 Benchmark Infrastructure** unless a real accepted `COMPARATIVE_COMPLETE` snapshot exists before staging.
- All plugin versions/tags remain unchanged from Repository `1.3.0`.

- [ ] **Step 1: Write RED release tests** requiring current repository `1.4.0`, notes path `.github/releases/1.4.0.md`, `plugins == []`, root README/CHANGELOG stage `1.4.0`, P3 infrastructure wording, and exact unchanged plugin versions.
- [ ] **Step 2: Run root tests and verify RED is only missing/stale release surfaces.**
- [ ] **Step 3: Convert old `1.3.0` current-state assertions to historical evidence where needed without weakening its release/tag history.**
- [ ] **Step 4: Stage manifest, notes and bilingual root docs/changelog.** Do not change plugin manifests or plugin release notes.
- [ ] **Step 5: Run validator + full root tests + all plugin regression/compile CI.**
- [ ] **Step 6: Commit** `release: stage repository 1.4.0`.

### Task 9: PR, exact-head CI, merge and immutable publication

**Files:**
- No new runtime files unless exact-head CI exposes a real defect.
- PR body/comment is the evidence ledger.

- [ ] **Step 1: Open draft PR** from implementation branch to live `main`; record approved spec/plan SHAs and repository-only release intent.
- [ ] **Step 2: Require final exact-head CI** success for both repository Python jobs plus all seven plugin regression/compile jobs.
- [ ] **Step 3: Audit independent review evidence** across review submissions, top-level comments and inline threads. Record absence explicitly if none exists; never call absence a clean independent review.
- [ ] **Step 4: Re-fetch live `main`.** If it differs from the implementation base, reconcile/revalidate rather than stale merge.
- [ ] **Step 5: Mark PR ready and squash merge using `expected_head_sha` equal to the verified exact-head SHA.**
- [ ] **Step 6: Require exact-main push CI** on merge SHA to complete 10/10 success.
- [ ] **Step 7: Require canonical `publish-current-release.yml` workflow_run** on that exact merge SHA to complete success; do not manually create or retarget release/tag objects.
- [ ] **Step 8: Audit Repository `1.4.0` remote publication:** `draft=false`, `immutable=true`, tag resolves to exact merge SHA, and no plugin release/tag was created or retargeted by this repository-only release.
- [ ] **Step 9: Audit history:** Repository `1.3.0`, `1.2.0`, `1.1.0`, SEO `1.2.0`, Direct/Metrika/Webmaster `2.1.0`, Wordstat/SEO `1.1.2`, Search `1.0.2`, Marketing `1.1.0` remain on prior tag SHAs. Preserve legacy release-object immutability metadata exactly; do not rewrite old releases merely because some predate the immutable publisher.
- [ ] **Step 10: Add post-release PR evidence comment** with exact head/main SHAs, CI/publisher run IDs, release ID/tag, history audit and independent-review status.

## Plan self-review

- Spec coverage: adapter protocol, independent judge, deterministic token lint, backend equivalence, P1 memory, artifacts/snapshots, completeness classification, deterministic CI boundary, docs and repository-only SemVer all map to Tasks 1–9.
- No provider-native adapter is added; external adapters remain outside repository core.
- No live multi-model result is fabricated. Without externally provisioned real adapters, Task 8 must release `1.4.0` as **P3 Benchmark Infrastructure** and Roadmap remains `INFRASTRUCTURE_READY`.
- All interfaces referenced by later tasks are defined in earlier tasks; no placeholder implementation step remains.
