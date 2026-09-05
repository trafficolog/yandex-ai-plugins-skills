# P0 Executable Safety — Design

**Date:** 2026-09-05  
**Status:** approved design, implementation not started  
**Target:** depth-first P0 milestone after Repository `1.0.10`  
**Scope:** Yandex Direct, Yandex Metrika, Yandex Webmaster write-capable helper surfaces

> `docs/superpowers/` is implementation/design context, not canonical production authority. After implementation, normative guarantees must live in production docs, executable tests, plugin contracts, and release surfaces.

## 1. Purpose

P0 converts the repository's existing safe-write guidance into a mechanically enforced execution contract.

The repository already has a common lifecycle:

```text
read -> analyze -> preview -> approval -> write -> verify
```

Direct, Metrika, and Webmaster already implement exact `preview_id` checks using local `_approval.py` helpers, but their envelopes bind different sets of consequential inputs. P0 does not replace this lifecycle. It standardizes and hardens it so that independently installable service plugins enforce the same safety semantics without depending on a root runtime package.

The durable product property is:

> A consequential service write cannot execute through a supported helper unless the supplied approval identifier matches the exact consequential operation envelope that the helper is about to execute.

P0 also makes operation scale, verification capability, rollback capability, and execution outcome explicit rather than leaving them only in prose.

## 2. Goals

P0 MUST:

1. Introduce `yandex-ai-approval/v2` as the common consequential-operation envelope.
2. Bind an approval to all material execution inputs, including target identity and operation scale.
3. Keep secrets out of preview/output while still preventing approval reuse across different authenticated principals where the service supports a stable local binding.
4. Add a mechanical bulk-operation guard.
5. Return a structured execution receipt for consequential writes.
6. Declare verification and rollback capability before execution.
7. Perform post-write verification where a reliable read-back contract exists.
8. Preserve independent plugin installability; no root shared runtime dependency is introduced.
9. Add repository-level behavioural convergence tests so safety semantics cannot drift silently between Direct, Metrika, and Webmaster.
10. Preserve the service-ownership boundary: SEO/Marketing may recommend or delegate previews, but the owning service plugin is the only component that executes the Yandex write.

## 3. Non-goals

P0 MUST NOT:

- implement `.yandex-ai/` project memory;
- write `decisions.jsonl`;
- introduce Electron, a dashboard, or an approval queue UI;
- add new Yandex service plugins;
- create a root/shared runtime package that independently installed plugins must import;
- claim that a standalone CLI can cryptographically prove that a human approved the operation in a later conversational turn;
- claim universal rollback support;
- make read-only operations require approval;
- make repository governance itself the product outcome.

Project memory and durable decision logging are P1. A future trusted host/runtime may provide signed or otherwise trusted human-approval receipts; that is outside P0.

## 4. Existing baseline

### Direct

Direct already binds consequential approval to:

- plugin and operation;
- production vs sandbox environment;
- client login;
- an HMAC-based authenticated-principal binding;
- endpoint;
- exact request body.

This is the closest current implementation to the P0 target and will be the reference implementation.

### Metrika

Metrika Management writes already bind method/path/query/body. Metrika imports additionally bind the counter, import kind, source/risk override, URL, and exact uploaded file SHA-256.

P0 must preserve those strong artifact semantics while adding principal/target parity and the shared v2 safety fields.

### Webmaster

Webmaster already binds API version, path/query/body and safely replaces embedded basic-auth credentials with an OAuth-keyed HMAC in the approval representation. P0 must preserve that secret-safe behaviour while adding a uniform target/principal model, operation scale, and execution capability metadata.

## 5. Architectural decision

### Chosen approach: canonical contract + local safety kernels

Each write-capable plugin keeps its own local implementation:

```text
Repository behavioural contract
             |
     +-------+--------+
     |       |        |
  Direct   Metrika  Webmaster
  local     local      local
  kernel    kernel     kernel
```

The local kernel may continue to be named `_approval.py` or be split into small service-local modules if implementation clarity requires it. The repository does not require byte-identical source code.

The repository-level contract tests enforce behavioural equivalence.

### Rejected: root shared runtime package

A root package would reduce duplication but would violate the existing independently installable plugin model unless distribution/installability guarantees were redesigned. P0 will not introduce that architecture.

### Rejected: fully independent plugin-specific safety designs

This preserves installability but allows semantic drift. Repository-owned behavioural contract tests solve that without a shared runtime dependency.

## 6. Approval envelope v2

All supported consequential operations MUST construct a canonical envelope with schema:

```text
yandex-ai-approval/v2
```

The conceptual structure is:

```json
{
  "schema": "yandex-ai-approval/v2",
  "plugin": "yandex-direct",
  "operation": "campaigns.update",
  "request": {
    "method": "POST",
    "environment": "production",
    "api_version": "v501",
    "url": "...",
    "path": "...",
    "query": {},
    "body": {}
  },
  "target": {
    "account": "service-specific stable non-secret identity",
    "auth_principal_binding": "secret-safe keyed binding"
  },
  "artifacts": [],
  "cardinality": {
    "scale": "KNOWN",
    "items": 3,
    "threshold": 20,
    "bulk": false
  },
  "safety": {
    "verification": "READ_BACK|RESPONSE_ONLY|NOT_AVAILABLE",
    "rollback": "SNAPSHOT_RESTORE|COMPENSATING_ACTION|NOT_AVAILABLE",
    "risk_flags": []
  }
}
```

For uncomputable operation scale, the canonical representation is:

```json
{
  "scale": "UNKNOWN",
  "items": null,
  "threshold": 20,
  "bulk": true
}
```

This is a conceptual contract, not a requirement that every service expose meaningless empty fields. Local implementations may normalize unavailable values to explicit `null`/empty forms as defined by tests, but two semantically identical previews within one helper/version must serialize identically.

### 6.1 Canonicalization

`preview_id` remains SHA-256 over deterministic canonical JSON:

- UTF-8;
- recursively deterministic object ordering through the existing JSON canonicalization approach;
- compact separators;
- no dependence on incidental Python object ordering;
- no secrets in the canonical envelope.

The full `preview_id` remains the approval token supplied through the current `--approve` flow.

### 6.2 Bound fields

Changing any consequential field MUST invalidate the previous approval. At minimum this includes:

- plugin;
- operation;
- method;
- environment;
- API version when applicable;
- target account/host/counter/client identity;
- authenticated-principal binding when applicable;
- URL/path/query;
- exact body;
- artifact content digest;
- artifact identity where meaningful;
- bulk scale state and cardinality;
- bulk threshold used for classification;
- risk override flags that change whether execution is permitted;
- declared safety capability when that declaration changes the user's decision context.

Incidental display-only fields, timestamps generated after execution, redacted headers, pretty-print formatting, and transport response metadata MUST NOT alter the preview identifier unless they change the actual consequential request or pre-execution safety meaning.

## 7. Secret-safe principal binding

Approval must not be reusable across authenticated principals merely because the visible payload is identical.

The binding MUST NOT expose the raw OAuth/API token or a reusable unsalted password verifier.

Service-local code should use a domain-separated keyed digest derived from the active credential, following the current Direct/Webmaster pattern. The digest is used only to distinguish the local authenticated principal in the approval envelope.

Properties:

- token A and token B produce different approval envelopes;
- changing token invalidates a prior consequential preview;
- the raw token never appears in preview JSON, execution receipts, errors, or logs;
- each service uses a distinct domain separator so bindings cannot be confused across plugins.

For target identity that is available independently of the token (Direct client login, Metrika counter, Webmaster user/host), that identity MUST also be bound explicitly.

## 8. Service-specific target bindings

### 8.1 Direct

Direct v2 target binding MUST include:

- environment (`production` or `sandbox`);
- effective client login or explicit `null`;
- authenticated-principal binding;
- service + method through the operation/request fields.

The current service allowlist and sandbox isolation remain unchanged.

### 8.2 Metrika Management

Metrika v2 target binding MUST include:

- authenticated-principal binding;
- path-derived counter identity when the endpoint is counter-scoped;
- explicit counter identity in specialized helpers where already available;
- exact path/query/body.

If a Management endpoint cannot reliably expose a stable counter/account identifier beyond its canonical path, the canonical normalized path remains part of the target binding; the implementation must not invent an account identity.

### 8.3 Metrika imports

Metrika import approval MUST preserve:

- counter ID;
- import kind;
- normalized query;
- provider/source label;
- `allow_direct_risk` state;
- exact file size and SHA-256;
- CSV row count as bound scale/risk context;
- expense provenance risk flags;
- authenticated-principal binding.

The uploaded multipart boundary is transport-incidental and MUST NOT affect `preview_id`.

### 8.4 Webmaster

Webmaster v2 target binding MUST include:

- OAuth principal binding;
- API version;
- canonical path;
- user ID and host ID where the specialized operation has them structurally available;
- exact query/body;
- the existing keyed binding for embedded URL credentials where such credentials are present.

The helper MUST NOT invent a host identity when it has only an opaque generic path; in that case the path itself remains part of the exact target.

## 9. Bulk-operation guard

Exact approval alone does not make a large operation safe. P0 introduces a mechanical bulk classification.

### 9.1 Default threshold

The repository policy default is:

```text
BULK_THRESHOLD = 20 items
```

This is a repository safety policy, not a Yandex API limit.

The threshold MUST be present in the consequential envelope so changing repository/helper policy invalidates an old approval.

For known scale, `bulk=true` when `items > threshold`; exactly 20 items remains a normal-scale operation under the default policy.

### 9.2 Cardinality

Each supported consequential helper MUST compute operation cardinality deterministically from the actual mutation payload where meaningful.

Examples:

- Direct `campaigns.update` with 3 campaign items -> `scale=KNOWN`, `items=3`, `bulk=false`;
- a single Webmaster recrawl submission -> `scale=KNOWN`, `items=1`, `bulk=false`;
- a Metrika file import is one upload operation, but CSV row count remains separately bound risk/scale context; the helper must not pretend that every CSV row maps to an independently reversible API mutation.

If cardinality cannot be derived reliably, the canonical state is `scale=UNKNOWN`, `items=null`, `bulk=true`. Unknown scale therefore always takes the stronger acknowledgement path and can never silently fall back to normal-scale execution.

### 9.3 Bulk acknowledgement

For `bulk=true`, exact `--approve <preview_id>` alone is insufficient.

The CLI flag is standardized as:

```text
--ack-bulk
```

The equivalent programmatic helper parameter is:

```text
ack_bulk=True
```

Execution semantics are therefore:

```text
normal write:
  --execute --approve <preview_id>

bulk or unknown-scale write:
  --execute --approve <preview_id> --ack-bulk
```

The bulk acknowledgement is not a second preview identifier; it acknowledges operation scale that is already bound into the exact preview. Supplying `--ack-bulk` for a non-bulk operation is permitted but has no authorization effect beyond the exact `preview_id`.

## 10. Safety capability declaration

Every consequential preview MUST tell the user what the helper can guarantee after execution.

### Verification capability

Allowed values:

- `READ_BACK` — helper has a reliable read operation to compare intended and observed state;
- `RESPONSE_ONLY` — helper can verify only the owning API's mutation response/identifier, not a complete read-back of final state;
- `NOT_AVAILABLE` — no reliable verification is implemented.

### Rollback capability

Allowed values:

- `SNAPSHOT_RESTORE` — helper can capture sufficient previous state and expose a tested restore operation;
- `COMPENSATING_ACTION` — no exact state restore exists, but a defined tested compensating operation is available;
- `NOT_AVAILABLE` — no reliable invocable rollback path is provided.

Capability metadata is descriptive of implemented mechanics. A plugin MUST NOT advertise a stronger capability than tests demonstrate.

## 11. Rollback semantics

P0 does not create a universal rollback framework and MUST NOT auto-rollback silently after a verification failure.

Rollback is itself consequential. A restore or compensating action MUST go through its own preview -> exact approval -> execution lifecycle.

An operation may advertise `SNAPSHOT_RESTORE` only when all of the following are true:

1. the helper can read and capture sufficient pre-write state;
2. the captured state is secret-free;
3. the helper can materialize enough restore input in a safe execution receipt/artifact or other explicitly designed local mechanism so restoration remains invocable after the original write returns;
4. a supported restore operation exists and has executable tests;
5. the restore operation itself uses `yandex-ai-approval/v2`.

If any of these conditions is absent, the operation MUST advertise `NOT_AVAILABLE` rather than implying rollback support.

P0 does not require any current operation to advertise rollback. Shipping explicit `NOT_AVAILABLE` is correct when no safe tested restore path exists.

Operations that are naturally queue submissions, imports, or irreversible server-side actions should normally declare `NOT_AVAILABLE` unless the Yandex API exposes and the helper implements a reliable compensating operation.

## 12. Execution lifecycle

Consequential helper execution follows:

```text
1. normalize requested operation
2. calculate target/principal binding
3. calculate cardinality and safety capabilities
4. build approval/v2 envelope
5. produce preview_id and human-readable preview
6. require exact preview_id
7. require --ack-bulk / ack_bulk=True when bulk=true
8. capture rollback material if and only if advertised capability requires it
9. execute the exact bound request
10. verify according to declared capability
11. return execution receipt
```

If the effective payload changes between steps 5 and 9, the helper MUST rebuild the envelope and fail the old approval.

For file uploads, the helper MUST execute the exact bytes whose digest was previewed. The current Metrika import behaviour of reading one snapshot and reusing those bytes for approval and multipart construction is the intended pattern.

## 13. Execution receipt

Every successful or partially successful consequential execution MUST return a structured receipt rather than only raw API payload.

Conceptual shape:

```json
{
  "schema": "yandex-ai-execution/v1",
  "execution_id": "...",
  "preview_id": "...",
  "plugin": "yandex-direct",
  "operation": "campaigns.update",
  "target": {
    "account": "..."
  },
  "cardinality": {
    "scale": "KNOWN",
    "items": 3,
    "bulk": false
  },
  "execution": {
    "state": "EXECUTED"
  },
  "verification": {
    "capability": "READ_BACK",
    "state": "VERIFIED"
  },
  "rollback": {
    "capability": "NOT_AVAILABLE"
  },
  "result": {}
}
```

### 13.1 Execution ID

`execution_id` MUST be generated by the owning helper after the write attempt begins and MUST NOT be used as authorization. Its purpose is result correlation and later P1 decision logging.

### 13.2 Outcome vocabulary

Execution and verification must not be collapsed into one boolean.

Minimum states:

Execution:

- `EXECUTED`
- `EXECUTION_FAILED`

Verification:

- `VERIFIED`
- `UNVERIFIED`
- `VERIFICATION_FAILED`
- `NOT_AVAILABLE`

A successful mutation with failed read-back is therefore represented as executed but verification-failed, not as a clean success.

If execution fails before the server can plausibly accept the mutation, no success receipt is emitted. If the transport outcome is ambiguous, the helper must not invent certainty; a service-specific ambiguous/unknown execution state may be added only when implementation evidence proves that the API/transport can produce such ambiguity.

## 14. Post-write verification

Verification is service- and operation-specific.

P0 requires a verification registry/decision at the local helper level, not one generic read-back algorithm.

For `READ_BACK` operations:

- identify a stable read endpoint;
- read only the affected objects when practical;
- compare only fields whose server-side normalization semantics are known;
- preserve omissions/unknowns instead of converting them to zero/false;
- return evidence for mismatch without silently retrying additional writes.

For `RESPONSE_ONLY` operations:

- capture stable server-provided identifiers/state from the mutation response;
- label the result as response-only verification;
- do not call it equivalent to read-back verification.

For `NOT_AVAILABLE`, the execution receipt MUST make the absence of verification explicit rather than treating a successful HTTP/API response as verified final state.

## 15. Human approval boundary

P0 mechanically enforces exact-operation approval data, but not conversational authorship.

A standalone helper can prove:

```text
supplied approval == preview_id(exact operation envelope)
```

It cannot prove:

```text
a human, rather than the model/process itself, supplied this value in a later chat turn
```

Therefore production docs MUST distinguish:

- **mechanically enforced by helper:** exact preview binding, target/principal binding, bulk guard, execution gate, capability declaration, supported verification;
- **host/operator policy:** the user must see the preview and approve it in a later interaction before the agent invokes execution.

A future trusted runtime approval receipt can strengthen this boundary without replacing approval/v2.

## 16. CLI compatibility

Existing high-level CLI semantics remain recognizable:

```text
preview by default for consequential operation
--execute --approve <preview_id>
```

P0 adds `--ack-bulk` only for the stronger bulk/unknown-scale acknowledgement path. Existing `--approve` remains a full exact `preview_id`, not a free-form confirmation string.

Read methods remain executable without preview approval.

Old `yandex-ai-approval/v1` preview IDs MUST NOT authorize v2 execution. Approval tokens are intentionally ephemeral; users regenerate previews after upgrading.

## 17. Error handling

Safety failures are fail-closed and must be distinguishable from transport/API failures.

Minimum categories:

- approval missing/mismatch;
- bulk acknowledgement missing;
- unknown/uncomputable scale classification failure;
- invalid target identity;
- snapshot/precondition failure;
- mutation transport/API failure;
- verification failure.

Errors MUST remain secret-free. A verification failure after a successful mutation MUST explicitly say the mutation may already have occurred.

## 18. Repository behavioural convergence contract

Repository tests will exercise service-local implementations through common behavioural fixtures.

The contract MUST prove at least:

1. deterministic preview IDs;
2. payload mutation invalidates approval;
3. target mutation invalidates approval;
4. credential/principal mutation invalidates approval where applicable;
5. environment/API-version mutation invalidates approval;
6. artifact-byte mutation invalidates approval;
7. risk-override mutation invalidates approval;
8. bulk scale/cardinality mutation invalidates approval;
9. normal approval cannot execute `bulk=true` operation without `--ack-bulk` / `ack_bulk=True`;
10. unknown scale is represented explicitly and uses the bulk path;
11. secrets are absent from preview/receipt/errors;
12. v1 preview IDs do not authorize v2 writes;
13. read-only paths remain approval-free;
14. receipt distinguishes execution from verification;
15. advertised rollback/verification capabilities match executable tests;
16. rollback, where advertised, is a separately approved consequential operation;
17. SEO/Marketing retain no credential-owning Yandex transport or direct execution path.

The tests validate semantics, not source-code duplication.

## 19. TDD implementation order

Implementation will proceed in this order:

1. Repository and Direct RED tests for `approval/v2` core semantics.
2. Direct reference implementation to GREEN.
3. Direct bulk guard, receipt, and capability/verification semantics.
4. Metrika RED parity tests, then Management/import implementation.
5. Webmaster RED parity tests, then generic/specialized implementation.
6. Repository convergence/adversarial tests across all three plugins.
7. Production documentation and contract-matrix updates.
8. Exact-head CI, scope verification, release staging, post-merge exact-main CI, generic publisher verification.

Each service implementation must become GREEN before using it as the template for the next service.

## 20. Release boundary

The intended product milestone is one coherent safety generation rather than a sequence of governance-only patch releases.

Provisional target after implementation and full verification:

```text
Repository            1.1.0
Yandex Direct          2.1.0
Yandex Metrika         2.1.0
Yandex Webmaster       2.1.0
```

Wordstat, Search, SEO, and Marketing versions remain unchanged unless implementation proves that their production behaviour must change.

These versions are design intent only. The release manifest MUST NOT be staged until runtime/tests/docs are complete and exact-head CI is green.

## 21. Acceptance criteria

P0 is complete only when all of the following are true:

- all supported Direct/Metrika/Webmaster consequential writes use `yandex-ai-approval/v2`;
- no active supported v1 path can authorize a v2 write;
- exact payload/target/principal/artifact/scale/risk changes invalidate approval;
- bulk/unknown-scale operations require `--ack-bulk` / `ack_bulk=True` in addition to exact approval;
- consequential previews declare verification and rollback capability;
- consequential executions return structured execution receipts;
- operations claiming `READ_BACK` are actually verified with tested read-back logic;
- operations claiming rollback have a separately invocable, separately approved, tested mechanism matching the advertised capability;
- no operation is required to claim rollback when no safe restore path exists;
- no secret appears in preview, receipt, error, or committed fixture;
- repository behavioural convergence tests are green on Python 3.10 and 3.13;
- all seven plugin CI jobs are green;
- independently installed Direct/Metrika/Webmaster plugins do not require a root runtime package;
- production docs explicitly distinguish mechanical helper enforcement from later-turn human-approval policy;
- release is published only through the existing exact-main immutable generic publisher;
- historical releases/tags remain immutable.

## 22. Follow-on boundary to P1

P0 receipts are intentionally designed as the input to P1 project memory.

P1 may append verified execution receipts to:

```text
.yandex-ai/decisions.jsonl
```

but P0 itself does not create or mutate that file.

This keeps authorization/execution mechanics independent from persistent project memory while giving P1 a trustworthy machine-produced event to record.