# P0 Executable Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace heterogeneous `yandex-ai-approval/v1` write gates in Direct, Metrika, and Webmaster with one mechanically convergent `yandex-ai-approval/v2` contract that binds target, authenticated principal, operation scale, risk context, and declared safety capability, adds a mechanical bulk gate, and returns `yandex-ai-execution/v1` receipts.

**Architecture:** Direct is the reference implementation. Each independently installable write-capable plugin keeps its own local `_approval.py` canonicalizer and gains its own local `_safety.py`; no root runtime dependency is introduced. Repository tests verify behavioural convergence by running each plugin in isolation. Generic operations whose cardinality cannot be derived safely are `UNKNOWN` scale and require `--ack-bulk`.

**Tech Stack:** Python 3.10/3.13 stdlib only, `unittest`, argparse, existing repository validator/contract matrix, existing generic immutable release publisher.

**Spec:** `docs/superpowers/specs/2026-09-05-p0-executable-safety-design.md`

## Global constraints

- Approval schema is exactly `yandex-ai-approval/v2`.
- Execution receipt schema is exactly `yandex-ai-execution/v1`.
- Repository safety policy is `BULK_THRESHOLD = 20`.
- Cardinality shape is `scale=KNOWN|UNKNOWN`; unknown uses `items=null`, `bulk=true`.
- Bulk or unknown-scale execution requires exact `--approve <preview_id>` plus `--ack-bulk`.
- A `yandex-ai-approval/v1` digest never authorizes a v2 write.
- Raw OAuth/API credentials never appear in previews, receipts, errors, fixtures, or committed docs.
- Read-only operations stay approval-free.
- SEO and Marketing remain Yandex-credential/transport-free; owning service plugins execute writes.
- P0 creates no `.yandex-ai/`, `decisions.jsonl`, durable rollback storage, dashboard, Electron app, or new Yandex plugin.
- Rollback is never automatic. Until a callable, separately approved restore/compensating path has executable tests, advertise `rollback=NOT_AVAILABLE`.
- `EXECUTED` and `VERIFIED` are separate facts. The initial P0 implementation uses `RESPONSE_ONLY` + `UNVERIFIED` unless a deliberately added operation-specific test proves a stronger read-back contract.
- Version/release surfaces are staged only after runtime, plugin, root, and documentation tests are green.

## File map

### New local runtime files

- `plugins/yandex-direct/scripts/_safety.py`
- `plugins/yandex-metrika/scripts/_safety.py`
- `plugins/yandex-webmaster/scripts/_safety.py`

Each local kernel exposes these exact interfaces:

```text
APPROVAL_SCHEMA: str = "yandex-ai-approval/v2"
EXECUTION_SCHEMA: str = "yandex-ai-execution/v1"
BULK_THRESHOLD: int = 20
principal_binding(token: str, *, domain: bytes) -> str
known_cardinality(items: int, *, artifact_rows: int | None = None) -> dict[str, object]
unknown_cardinality(*, artifact_rows: int | None = None) -> dict[str, object]
require_bulk_ack(cardinality: dict[str, object], ack_bulk: bool) -> None
execution_receipt(preview_id: str, plugin: str, operation: str, target: dict[str, object], cardinality: dict[str, object], result: object, verification_capability: str, verification_state: str, rollback_capability: str) -> dict[str, object]
```

`_approval.py` remains the local deterministic SHA-256 canonicalizer; P0 changes envelopes passed into it, not its hashing algorithm.

### Runtime files modified

- `plugins/yandex-direct/scripts/yd_api.py`
- `plugins/yandex-metrika/scripts/ym_api.py`
- `plugins/yandex-metrika/scripts/ym_logs.py`
- `plugins/yandex-metrika/scripts/ym_import.py`
- `plugins/yandex-webmaster/scripts/yw_api.py`

### Tests

- Direct: `test_approval.py`, `test_yd_api.py`, new `test_safety.py`.
- Metrika: `test_approval.py`, `test_ym_api.py`, `test_ym_logs.py`, `test_ym_import.py`, new `test_safety.py`.
- Webmaster: `test_approval.py`, `test_yw_api.py`, new `test_safety.py`.
- Root: new `tests/test_p0_executable_safety_contract.py`, modified `tests/test_documentation_ux_contracts.py`, new final-stage `tests/test_repository_1_1_0_release_surfaces.py`.
- Traceability: `docs/CONTRACT_MATRIX.json`.

### Production documentation and release files

- `docs/PLUGIN_STANDARD.md`, `docs/PLUGIN_STANDARD.en.md`.
- `docs/ARCHITECTURE.md`, `docs/ARCHITECTURE.en.md`.
- `SECURITY.md`, `SECURITY.en.md`.
- Direct/Metrika/Webmaster `references/safety.md`.
- Direct/Metrika/Webmaster `README.md`, `README.en.md`, `CHANGELOG.md`, `CHANGELOG.en.md`.
- Direct/Metrika/Webmaster `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`.
- `.claude-plugin/marketplace.json`.
- root `README.md`, `README.en.md`, `CHANGELOG.md`, `CHANGELOG.en.md`.
- `.github/releases/1.1.0.md`.
- `.github/releases/yandex-direct-2.1.0.md`.
- `.github/releases/yandex-metrika-2.1.0.md`.
- `.github/releases/yandex-webmaster-2.1.0.md`.
- `.github/releases/release.json`.

---

## Task 1: Direct approval/v2 kernel and reference envelope

**Files**
- Create `plugins/yandex-direct/scripts/_safety.py`.
- Create `plugins/yandex-direct/tests/test_safety.py`.
- Modify `plugins/yandex-direct/tests/test_approval.py`.
- Modify `plugins/yandex-direct/scripts/yd_api.py`.
- Modify `plugins/yandex-direct/tests/test_yd_api.py`.
- Create `tests/test_p0_executable_safety_contract.py`.

- [ ] **Step 1: Write Direct local-kernel RED tests**

Create tests that assert:

```python
self.assertEqual(_safety.APPROVAL_SCHEMA, "yandex-ai-approval/v2")
self.assertEqual(_safety.EXECUTION_SCHEMA, "yandex-ai-execution/v1")
self.assertEqual(_safety.BULK_THRESHOLD, 20)
self.assertEqual(
    _safety.known_cardinality(3),
    {"scale": "KNOWN", "items": 3, "threshold": 20, "bulk": False},
)
self.assertEqual(
    _safety.unknown_cardinality(),
    {"scale": "UNKNOWN", "items": None, "threshold": 20, "bulk": True},
)
with self.assertRaisesRegex(ValueError, "ack-bulk"):
    _safety.require_bulk_ack(_safety.known_cardinality(21), False)
with self.assertRaisesRegex(ValueError, "ack-bulk"):
    _safety.require_bulk_ack(_safety.unknown_cardinality(), False)
_safety.require_bulk_ack(_safety.known_cardinality(20), False)
_safety.require_bulk_ack(_safety.known_cardinality(21), True)
first = _safety.principal_binding("secret-a", domain=b"yandex-direct-auth-principal/v2")
changed = _safety.principal_binding("secret-b", domain=b"yandex-direct-auth-principal/v2")
self.assertNotEqual(first, changed)
self.assertNotIn("secret-a", first)
```

- [ ] **Step 2: Update Direct approval canonicalizer samples to v2**

In `test_approval.py`, replace sample schema literals with `yandex-ai-approval/v2`. Preserve key-order determinism and the existing requirement that missing/wrong approval errors do not reveal the expected digest.

- [ ] **Step 3: Add Direct v2 envelope RED tests**

For `campaigns.update` with two `Campaigns`, assert:

```python
self.assertEqual(envelope["schema"], "yandex-ai-approval/v2")
self.assertEqual(envelope["target"]["client_login"], "client-a")
self.assertIn("auth_principal_binding", envelope["target"])
self.assertEqual(envelope["cardinality"]["items"], 2)
self.assertFalse(envelope["cardinality"]["bulk"])
self.assertNotIn("secret-token", str(envelope))
```

Construct a legacy v1 envelope using the current v1 shape, hash it with `preview_id`, pass that digest to the new write path, assert `ValueError`, and assert `_http.request_json` was not called.

- [ ] **Step 4: Add a Direct-only root smoke RED test**

Create `tests/test_p0_executable_safety_contract.py` with class `P0ExecutableSafetyContractTests` and method `test_direct_has_local_v2_kernel`. It reads `plugins/yandex-direct/scripts/_safety.py` and asserts the exact approval schema and threshold literals. Task 5 replaces this Direct-only smoke assertion with three-plugin behavioural convergence.

- [ ] **Step 5: Run RED**

```bash
(cd plugins/yandex-direct && python -m unittest tests.test_safety tests.test_approval tests.test_yd_api -v)
python -m unittest tests.test_p0_executable_safety_contract -v
```

Expected failure cause: missing `_safety.py` and missing v2 envelope semantics. Authorization failures must happen before transport.

- [ ] **Step 6: Implement Direct local kernel**

Create `_safety.py` with these exact mechanics:

```python
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

APPROVAL_SCHEMA = "yandex-ai-approval/v2"
EXECUTION_SCHEMA = "yandex-ai-execution/v1"
BULK_THRESHOLD = 20


def principal_binding(token: str, *, domain: bytes) -> str:
    return hmac.new(token.encode("utf-8"), domain, hashlib.sha256).hexdigest()


def known_cardinality(items: int, *, artifact_rows: int | None = None) -> dict[str, object]:
    if items < 0:
        raise ValueError("cardinality items must be non-negative")
    result: dict[str, object] = {
        "scale": "KNOWN",
        "items": items,
        "threshold": BULK_THRESHOLD,
        "bulk": items > BULK_THRESHOLD,
    }
    if artifact_rows is not None:
        result["artifact_rows"] = artifact_rows
    return result


def unknown_cardinality(*, artifact_rows: int | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "scale": "UNKNOWN",
        "items": None,
        "threshold": BULK_THRESHOLD,
        "bulk": True,
    }
    if artifact_rows is not None:
        result["artifact_rows"] = artifact_rows
    return result


def require_bulk_ack(cardinality: dict[str, object], ack_bulk: bool) -> None:
    if cardinality.get("bulk") is True and not ack_bulk:
        raise ValueError(
            "bulk or unknown-scale execution requires --ack-bulk after reviewing the exact preview"
        )


def execution_receipt(
    *,
    preview_id: str,
    plugin: str,
    operation: str,
    target: dict[str, object],
    cardinality: dict[str, object],
    result: Any,
    verification_capability: str,
    verification_state: str,
    rollback_capability: str,
) -> dict[str, object]:
    return {
        "schema": EXECUTION_SCHEMA,
        "execution_id": secrets.token_hex(16),
        "preview_id": preview_id,
        "plugin": plugin,
        "operation": operation,
        "target": target,
        "cardinality": cardinality,
        "execution": {"state": "EXECUTED"},
        "verification": {
            "capability": verification_capability,
            "state": verification_state,
        },
        "rollback": {
            "capability": rollback_capability,
            "snapshot_available": False,
        },
        "result": result,
    }
```

- [ ] **Step 7: Convert Direct envelope to v2**

Add `_safety` import. Add exact entity-list mapping:

```python
ENTITY_LIST_KEYS = {
    "campaigns": "Campaigns",
    "adgroups": "AdGroups",
    "ads": "Ads",
    "keywords": "Keywords",
    "bids": "Bids",
    "feeds": "Feeds",
    "creatives": "Creatives",
}
```

`mutation_cardinality(service, params)` returns known list length only for this mapping; all other write shapes return `_safety.unknown_cardinality()`.

Keep `auth_principal_binding(token)` as compatibility function, but implement it through `_safety.principal_binding` with domain `b"yandex-direct-auth-principal/v2"`.

The v2 envelope fields are exactly:

```text
schema
plugin
operation
request.method
request.environment
request.api_version
request.url
request.path
request.query
request.body
target.client_login
target.auth_principal_binding
artifacts
cardinality
safety.verification
safety.rollback
safety.risk_flags
```

Use `request.api_version="v501"`, `safety.verification="RESPONSE_ONLY"`, `safety.rollback="NOT_AVAILABLE"`, and empty risk flags.

Preview output exposes `approval_schema`, `cardinality`, `safety`, and `preview_id` without exposing the raw principal credential.

- [ ] **Step 8: Run GREEN and commit**

```bash
(cd plugins/yandex-direct && python -m unittest discover -s tests -v && python -m compileall -q scripts)
python -m unittest tests.test_p0_executable_safety_contract -v
git add plugins/yandex-direct/scripts/_safety.py plugins/yandex-direct/scripts/yd_api.py plugins/yandex-direct/tests/test_safety.py plugins/yandex-direct/tests/test_approval.py plugins/yandex-direct/tests/test_yd_api.py tests/test_p0_executable_safety_contract.py
git commit -m "feat(direct): introduce approval v2 safety kernel"
```

---

## Task 2: Direct bulk gate and execution receipt

**Files**
- Modify `plugins/yandex-direct/scripts/yd_api.py`.
- Modify `plugins/yandex-direct/tests/test_yd_api.py`.

- [ ] **Step 1: Write RED tests for scale gate and receipt**

Add tests proving:
- 21 `Campaigns` with exact approval and `ack_bulk=False` fail before transport with an `ack-bulk` error.
- an opaque `strategies.update` mutation is `UNKNOWN` and fails before transport without scale acknowledgement.
- one `Campaigns` mutation with exact approval returns receipt schema `yandex-ai-execution/v1`, execution state `EXECUTED`, verification `{capability: RESPONSE_ONLY, state: UNVERIFIED}`, rollback capability `NOT_AVAILABLE`, and the exact `preview_id`.

- [ ] **Step 2: Run RED**

```bash
(cd plugins/yandex-direct && python -m unittest tests.test_yd_api -v)
```

- [ ] **Step 3: Add explicit `ack_bulk: bool = False` parameter to `YandexDirectClient.request`**

For consequential writes execute in this order:

```python
approved_preview = require_approval(envelope, approve)
_safety.require_bulk_ack(envelope["cardinality"], ack_bulk)
```

Only then invoke `_http.request_json`. Wrap successful write result using `_safety.execution_receipt`. Read operations keep the current raw result/transport shape.

- [ ] **Step 4: Add CLI `--ack-bulk`**

Use:

```python
parser.add_argument(
    "--ack-bulk",
    action="store_true",
    help="Acknowledge bulk or unknown operation scale after reviewing the exact preview",
)
```

Forward `args.ack_bulk` to `client.request`. Update CLI mocks to assert forwarding.

- [ ] **Step 5: Run GREEN and commit**

```bash
(cd plugins/yandex-direct && python -m unittest discover -s tests -v && python -m compileall -q scripts)
git add plugins/yandex-direct/scripts/yd_api.py plugins/yandex-direct/tests/test_yd_api.py
git commit -m "feat(direct): enforce bulk acknowledgement and receipts"
```

---

## Task 3: Metrika v2 parity for Management, Logs, and imports

**Files**
- Create `plugins/yandex-metrika/scripts/_safety.py`.
- Create `plugins/yandex-metrika/tests/test_safety.py`.
- Modify `plugins/yandex-metrika/tests/test_approval.py`.
- Modify `plugins/yandex-metrika/scripts/ym_api.py`.
- Modify `plugins/yandex-metrika/scripts/ym_logs.py`.
- Modify `plugins/yandex-metrika/scripts/ym_import.py`.
- Modify `plugins/yandex-metrika/tests/test_ym_api.py`.
- Modify `plugins/yandex-metrika/tests/test_ym_logs.py`.
- Modify `plugins/yandex-metrika/tests/test_ym_import.py`.

- [ ] **Step 1: Write Metrika kernel RED tests**

Assert exact schema constants, threshold, `known_cardinality(1, artifact_rows=37)`, `unknown_cardinality()`, missing bulk acknowledgement rejection, successful bulk acknowledgement, and token-sensitive principal binding using domain `b"yandex-metrika-auth-principal/v2"`.

- [ ] **Step 2: Update Metrika approval canonicalizer samples to v2**

Replace sample schema literals in `test_approval.py`; preserve canonicalization and digest non-leak tests.

- [ ] **Step 3: Write Management RED tests**

Assert a consequential generic Management preview:

```text
approval_schema = yandex-ai-approval/v2
cardinality.scale = UNKNOWN
cardinality.items = null
cardinality.bulk = true
```

Build preview with token A and execute same method/path/body with token B plus `ack_bulk=True`; assert approval mismatch before `request_json`. Exact approval with no `ack_bulk` also fails before transport. Exact approval plus `ack_bulk=True` returns response-only/unverified receipt.

- [ ] **Step 4: Write Logs RED tests**

For `create` and `clean`, assert known cardinality one. Token mutation invalidates exact approval before `request_json`. Exact single-operation approval executes without bulk acknowledgement and returns receipt.

- [ ] **Step 5: Write import RED tests**

For one-row CSV assert:

```text
approval_schema = yandex-ai-approval/v2
cardinality.scale = KNOWN
cardinality.items = 1
cardinality.artifact_rows = 1
```

Assert token mutation invalidates approval; file-byte mutation after preview still invalidates approval before upload. Keep Direct-expense risk tests green. A CSV with more than 20 rows remains one upload operation; `artifact_rows` changes the preview but does not turn API operation cardinality into bulk.

- [ ] **Step 6: Run RED**

```bash
(cd plugins/yandex-metrika && python -m unittest discover -s tests -v)
```

- [ ] **Step 7: Create Metrika local kernel**

From repository root copy the already-green local implementation, then keep it as a plugin-owned file:

```bash
cp plugins/yandex-direct/scripts/_safety.py plugins/yandex-metrika/scripts/_safety.py
```

No runtime import crosses plugin boundaries.

- [ ] **Step 8: Convert Metrika envelopes to token-bound v2**

Set exact signatures:

```text
ym_api.approval_envelope(method: str, path: str, token: str, query: dict[str, Any] | None = None, body: Any | None = None) -> dict[str, Any]
ym_logs.logs_approval_envelope(counter_id: int, action: str, token: str, request_id: int | None = None, part_number: int | None = None, query: dict[str, Any] | None = None) -> dict[str, Any]
ym_import.import_approval_envelope(kind: str, counter_id: int, file_path: Path, token: str, source: str | None = None, allow_direct_risk: bool = False, _file_bytes: bytes | None = None, **query: Any) -> dict[str, Any]
```

Update every existing test/helper call to supply its test token. Bind principal with domain `b"yandex-metrika-auth-principal/v2"`.

Use exact scale policy:

```text
Management generic consequential request -> unknown_cardinality()
Logs create/clean                         -> known_cardinality(1)
Import upload                             -> known_cardinality(1, artifact_rows=file_info["rows"])
```

Include existing import Direct-risk warning tokens in approval-bound `safety.risk_flags`.

Each consequential preview exposes `approval_schema`, `cardinality`, `safety`, and `preview_id`.

- [ ] **Step 9: Enforce scale and receipts**

Add `ack_bulk: bool = False` to `ym_api.run_request`; generic Management writes require it after exact approval. Logs/import need no CLI bulk flag in P0 because their API operation cardinality is always one. Every successful consequential Metrika path returns `yandex-ai-execution/v1` with `RESPONSE_ONLY`, `UNVERIFIED`, `NOT_AVAILABLE`.

- [ ] **Step 10: Add Management CLI `--ack-bulk`, run GREEN, commit**

```bash
(cd plugins/yandex-metrika && python -m unittest discover -s tests -v && python -m compileall -q scripts)
git add plugins/yandex-metrika/scripts plugins/yandex-metrika/tests
git commit -m "feat(metrika): converge writes on approval v2"
```

---

## Task 4: Webmaster v2 parity and descriptor-derived scale

**Files**
- Create `plugins/yandex-webmaster/scripts/_safety.py`.
- Create `plugins/yandex-webmaster/tests/test_safety.py`.
- Modify `plugins/yandex-webmaster/tests/test_approval.py`.
- Modify `plugins/yandex-webmaster/scripts/yw_api.py`.
- Modify `plugins/yandex-webmaster/tests/test_yw_api.py`.

- [ ] **Step 1: Write Webmaster kernel RED tests**

Assert exact schemas, threshold, 21-item bulk classification, unknown classification, bulk acknowledgement, and token-sensitive principal binding using domain `b"yandex-webmaster-auth-principal/v2"`.

- [ ] **Step 2: Update Webmaster approval canonicalizer samples to v2**

Replace sample v1 schema literals; preserve canonicalization and digest non-leak tests.

- [ ] **Step 3: Write exact scale RED tests**

Assert known single cardinality for existing paths ending in:

```text
/recrawl/queue
/user-added-sitemaps
/user-added-sitemaps/<sitemap_id>
/sitemaps/<sitemap_id>/recrawl
/feeds/add/start
/indexing/archive
```

Assert `/feeds/batch/add` uses `len(body["feeds"])` and `/feeds/batch/remove` uses `len(body["urls"])`. A 21-feed batch is bulk. An unrecognized generic mutation is unknown scale.

- [ ] **Step 4: Write principal, secret, bulk, and receipt RED tests**

A token-A preview cannot execute under token B, even without embedded basic-auth credentials. Existing embedded feed credentials stay redacted and OAuth-keyed. A 21-feed exact preview without `ack_bulk` fails before transport. With `ack_bulk=True`, successful transport returns response-only/unverified receipt.

- [ ] **Step 5: Run RED**

```bash
(cd plugins/yandex-webmaster && python -m unittest discover -s tests -v)
```

- [ ] **Step 6: Create Webmaster local kernel**

```bash
cp plugins/yandex-direct/scripts/_safety.py plugins/yandex-webmaster/scripts/_safety.py
```

No cross-plugin runtime import is introduced.

- [ ] **Step 7: Implement `webmaster_cardinality(path, body)`**

Use exact decision order:

```text
feeds/batch/add + list feeds      -> known length of feeds
feeds/batch/remove + list urls    -> known length of urls
recrawl/queue                     -> known 1
user-added-sitemaps exact suffix  -> known 1
user-added-sitemaps/<id>          -> known 1
any path ending /recrawl          -> known 1
feeds/add/start                   -> known 1
indexing/archive                  -> known 1
otherwise                         -> unknown
```

Do not modify specialized descriptor modules; classify their existing paths.

- [ ] **Step 8: Convert `yw_api.approval_envelope` to v2**

Set exact signature:

```text
approval_envelope(method: str, path: str, token: str, params: dict[str, Any] | None = None, body: Any | None = None, version: str = "v4") -> dict[str, Any]
```

Preserve `_approval_url_credentials` and preview redaction. Bind OAuth principal with domain `b"yandex-webmaster-auth-principal/v2"`. Bind API version/path/query/body/cardinality/safety. Preview exposes `approval_schema`, `cardinality`, `safety`, and `preview_id`.

- [ ] **Step 9: Enforce approval then scale before transport**

Add `ack_bulk: bool = False` to `run_request`. Consequential order is exact approval, bulk acknowledgement, transport, then receipt. Reads keep current response shape.

- [ ] **Step 10: Add CLI `--ack-bulk`, run GREEN, commit**

```bash
(cd plugins/yandex-webmaster && python -m unittest discover -s tests -v && python -m compileall -q scripts)
git add plugins/yandex-webmaster/scripts/_safety.py plugins/yandex-webmaster/scripts/yw_api.py plugins/yandex-webmaster/tests/test_safety.py plugins/yandex-webmaster/tests/test_approval.py plugins/yandex-webmaster/tests/test_yw_api.py
git commit -m "feat(webmaster): converge writes on approval v2"
```

---

## Task 5: Repository behavioural convergence and ownership guard

**Files**
- Modify `tests/test_p0_executable_safety_contract.py`.
- Modify `docs/CONTRACT_MATRIX.json`.

- [ ] **Step 1: Expand root test to isolated three-plugin behaviour**

Add helper `run_plugin_python(plugin: str, source: str) -> dict[str, object]` using `subprocess.run([sys.executable, "-c", source], cwd=ROOT / "plugins" / plugin, check=True, text=True, capture_output=True)` and JSON output.

Rename the Direct-only smoke method to `test_local_safety_kernels_converge`. For each of `yandex-direct`, `yandex-metrika`, `yandex-webmaster`, execute isolated code that returns schema constants, threshold, known(20), known(21), and unknown cardinality; assert exact parity.

- [ ] **Step 2: Add secret-sentinel convergence test**

Use token `P0_SENTINEL_SECRET_6c90b2` in each isolated plugin, generate principal binding and representative receipt, serialize them, and assert the sentinel is absent.

- [ ] **Step 3: Update exact contract-matrix traceability**

Keep existing IDs `direct.preview-bound-write`, `metrika.preview-bound-write`, `webmaster.preview-bound-write`. Their exact `test_refs` must cover v2 target/principal binding, pre-transport approval rejection, pre-transport bulk rejection, and receipt semantics.

Add:

```json
{
  "id": "repository.p0-safety-convergence",
  "plugin": "repository",
  "status": "infrastructure",
  "skills": [],
  "helpers": [
    "plugins/yandex-direct/scripts/_safety.py",
    "plugins/yandex-metrika/scripts/_safety.py",
    "plugins/yandex-webmaster/scripts/_safety.py"
  ],
  "test_refs": [
    "tests/test_p0_executable_safety_contract.py::P0ExecutableSafetyContractTests::test_local_safety_kernels_converge"
  ],
  "references": [],
  "freshness_controlled_references": []
}
```

- [ ] **Step 4: Verify existing SEO/Marketing ownership guard**

```bash
python -m unittest tests.test_validate_repo.ValidateRepositoryTests.test_cross_service_transport_is_rejected -v
```

The planned implementation does not modify `scripts/validate_repo.py` because this existing test already owns the boundary.

- [ ] **Step 5: Run root GREEN and commit**

```bash
python scripts/validate_repo.py
python -m unittest discover -s tests -v
git add tests/test_p0_executable_safety_contract.py docs/CONTRACT_MATRIX.json
git commit -m "test: enforce P0 write safety convergence"
```

---

## Task 6: Production docs and exact claims

**Files**
- Modify `tests/test_documentation_ux_contracts.py`.
- Modify `docs/PLUGIN_STANDARD.md`, `docs/PLUGIN_STANDARD.en.md`.
- Modify `docs/ARCHITECTURE.md`, `docs/ARCHITECTURE.en.md`.
- Modify `SECURITY.md`, `SECURITY.en.md`.
- Modify Direct/Metrika/Webmaster `references/safety.md`, `README.md`, `README.en.md`.

- [ ] **Step 1: Add docs RED assertions**

In `tests/test_documentation_ux_contracts.py`, load both Plugin Standard language files and assert both contain:

```text
yandex-ai-approval/v2
--ack-bulk
yandex-ai-execution/v1
RESPONSE_ONLY
NOT_AVAILABLE
```

Also assert each language explicitly says standalone CLI cannot prove that a human supplied approval in a later conversational turn.

- [ ] **Step 2: Run RED**

```bash
python -m unittest tests.test_documentation_ux_contracts tests.test_bilingual_docs tests.test_bilingual_docs_contracts -v
```

- [ ] **Step 3: Update canonical docs**

State explicitly:

```text
Mechanically enforced by helper:
- exact v2 operation binding
- target/authenticated-principal binding
- scale/bulk gate
- service-owned execution boundary
- structured receipt and truthful capability declaration

Host/operator policy, not proven by standalone CLI:
- user actually saw the preview
- user personally supplied approval in a later conversational turn
```

Never call `RESPONSE_ONLY + UNVERIFIED` verified final state.

- [ ] **Step 4: Update service docs**

Describe threshold 20 as repository policy, not Yandex API limit. Direct/Webmaster document bulk/unknown acknowledgement. Metrika Management documents unknown-scale acknowledgement; Logs/import document single API-operation cardinality and separate import-row risk context.

- [ ] **Step 5: Run GREEN and commit**

```bash
python -m unittest tests.test_documentation_ux_contracts tests.test_bilingual_docs tests.test_bilingual_docs_contracts -v
python scripts/validate_repo.py
git add tests/test_documentation_ux_contracts.py docs/PLUGIN_STANDARD.md docs/PLUGIN_STANDARD.en.md docs/ARCHITECTURE.md docs/ARCHITECTURE.en.md SECURITY.md SECURITY.en.md plugins/yandex-direct/README.md plugins/yandex-direct/README.en.md plugins/yandex-direct/references/safety.md plugins/yandex-metrika/README.md plugins/yandex-metrika/README.en.md plugins/yandex-metrika/references/safety.md plugins/yandex-webmaster/README.md plugins/yandex-webmaster/README.en.md plugins/yandex-webmaster/references/safety.md
git commit -m "docs: document executable write safety v2"
```

---

## Task 7: Full pre-release verification

**Files:** no planned file changes.

- [ ] **Step 1: Compile repository scripts**

```bash
python -m compileall -q scripts plugins
```

- [ ] **Step 2: Run root validation**

```bash
python scripts/validate_repo.py
python -m unittest discover -s tests -v
```

- [ ] **Step 3: Run exact CI-equivalent commands for all seven plugins**

```bash
(cd plugins/yandex-direct && python -m unittest discover -s tests -v && python -m compileall -q scripts)
(cd plugins/yandex-metrika && python -m unittest discover -s tests -v && python -m compileall -q scripts)
(cd plugins/yandex-webmaster && python -m unittest discover -s tests -v && python -m compileall -q scripts)
(cd plugins/yandex-wordstat && python -m unittest discover -s tests -v && python -m compileall -q scripts)
(cd plugins/yandex-search && python -m unittest discover -s tests -v && python -m compileall -q scripts)
(cd plugins/yandex-seo && python -m unittest discover -s tests -v && python -m compileall -q scripts)
(cd plugins/yandex-marketing && python -m unittest discover -s tests -v && python -m compileall -q scripts)
```

- [ ] **Step 4: Inspect exact scope against base**

```bash
git diff --stat d036200564f9f1d66352894b71fd6a8b25a9c51f...HEAD
git diff --name-only d036200564f9f1d66352894b71fd6a8b25a9c51f...HEAD
```

Expected pre-release scope: Direct/Metrika/Webmaster safety runtime/tests, repository convergence matrix/test, bilingual safety docs, approved spec/plan. No Wordstat/Search runtime change, no SEO/Marketing Yandex transport, no `.yandex-ai/`.

- [ ] **Step 5: Apply defect rule**

Any defect found here gets the smallest reproducing regression test first; observe RED, patch owning implementation, rerun Steps 1–4. Do not create an empty verification commit.

---

## Task 8: Stage Repository 1.1.0 and three plugin 2.1.0 releases

**Files**
- Create `tests/test_repository_1_1_0_release_surfaces.py`.
- Modify Direct/Metrika/Webmaster `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`.
- Modify `.claude-plugin/marketplace.json`.
- Modify Direct/Metrika/Webmaster `CHANGELOG.md`, `CHANGELOG.en.md`.
- Modify root `README.md`, `README.en.md`, `CHANGELOG.md`, `CHANGELOG.en.md`.
- Create four release-note files listed in File map.
- Modify `.github/releases/release.json`.

**Exact version target**

```text
Repository            1.1.0
Yandex Direct          2.1.0
Yandex Metrika         2.1.0
Yandex Webmaster       2.1.0
Yandex Wordstat        1.1.2 unchanged
Yandex Search          1.0.2 unchanged
Yandex SEO             1.1.2 unchanged
Yandex Marketing       1.1.0 unchanged
```

- [ ] **Step 1: Create intentional release RED test**

`tests/test_repository_1_1_0_release_surfaces.py` loads release manifest, marketplace entries, and all seven Claude/Codex manifests. It asserts the exact version target above, exact three plugin tags, and existence of all four new release notes. Run while current surfaces remain 1.0.10/2.0.x and record release-only failure.

- [ ] **Step 2: Bump exactly three plugin manifests and marketplace entries**

Set Direct/Metrika/Webmaster Claude and Codex manifests plus marketplace entries to 2.1.0. Leave the other four plugin manifests untouched.

- [ ] **Step 3: Add bilingual plugin changelog entries**

Each 2.1.0 entry describes v2 target/principal/scale binding, bulk acknowledgement where applicable, structured execution receipt, and truthful verification/rollback declaration.

- [ ] **Step 4: Create exact release notes**

```text
.github/releases/1.1.0.md
.github/releases/yandex-direct-2.1.0.md
.github/releases/yandex-metrika-2.1.0.md
.github/releases/yandex-webmaster-2.1.0.md
```

Repository note states the other four plugin versions remain unchanged. Plugin notes describe only their owning plugin change.

- [ ] **Step 5: Replace release manifest with exact accepted schema**

```json
{
  "schema_version": 1,
  "repository": {
    "version": "1.1.0",
    "tag": "1.1.0",
    "title": "Repository 1.1.0",
    "notes_file": ".github/releases/1.1.0.md"
  },
  "plugins": [
    {
      "plugin": "yandex-direct",
      "version": "2.1.0",
      "tag": "yandex-direct-v2.1.0",
      "title": "Yandex Direct 2.1.0",
      "notes_file": ".github/releases/yandex-direct-2.1.0.md"
    },
    {
      "plugin": "yandex-metrika",
      "version": "2.1.0",
      "tag": "yandex-metrika-v2.1.0",
      "title": "Yandex Metrika 2.1.0",
      "notes_file": ".github/releases/yandex-metrika-2.1.0.md"
    },
    {
      "plugin": "yandex-webmaster",
      "version": "2.1.0",
      "tag": "yandex-webmaster-v2.1.0",
      "title": "Yandex Webmaster 2.1.0",
      "notes_file": ".github/releases/yandex-webmaster-2.1.0.md"
    }
  ]
}
```

- [ ] **Step 6: Update root RU/EN release surfaces**

README current release marker becomes `release-1.1.0`; changelogs prepend `## [1.1.0]`. State exact three plugin bumps and unchanged versions of other four.

- [ ] **Step 7: Run release GREEN**

```bash
python scripts/release_manifest.py validate
python scripts/validate_repo.py
python -m unittest tests.test_repository_1_1_0_release_surfaces -v
python -m unittest discover -s tests -v
python -m compileall -q scripts plugins
```

- [ ] **Step 8: Commit release staging**

```bash
git add .claude-plugin/marketplace.json .github/releases/release.json .github/releases/1.1.0.md .github/releases/yandex-direct-2.1.0.md .github/releases/yandex-metrika-2.1.0.md .github/releases/yandex-webmaster-2.1.0.md README.md README.en.md CHANGELOG.md CHANGELOG.en.md plugins/yandex-direct plugins/yandex-metrika plugins/yandex-webmaster tests/test_repository_1_1_0_release_surfaces.py
git diff --cached --name-only
git commit -m "release: stage executable safety 1.1.0"
```

The staged-name review must show no historical release-note edits and no changes under Wordstat/Search/SEO/Marketing.

---

## Task 9: PR, exact-head CI, merge, exact-main CI, immutable publish

**Files:** no planned implementation changes.

- [ ] **Step 1: Open one PR from implementation branch**

PR body records exact base SHA, final head SHA, RED/GREEN evidence, local verification commands, scope, human-approval limitation, verification/rollback limitations, intended versions/tags, and independent-review evidence or explicit absence.

- [ ] **Step 2: Require exact-head CI before merge**

All ten expected CI jobs must be successful on current PR head: root Python 3.10, root Python 3.13, detect, and seven plugin jobs. Any head change invalidates prior CI evidence.

- [ ] **Step 3: Inspect review state**

Fetch reviews, review threads, comments. Empty review state is absence of independent review, not clean independent review.

- [ ] **Step 4: Merge with expected-head guard**

Use squash merge with exact verified PR head SHA.

- [ ] **Step 5: Require exact-main CI**

Post-merge CI must be completed/successful and its `head_sha` equal current `main` SHA.

- [ ] **Step 6: Let repository-native publisher publish declared set**

Publisher is triggered by successful main CI. Do not manually create or move tags/releases.

- [ ] **Step 7: Verify exact immutable set**

All four tags resolve to same merge/main SHA:

```text
1.1.0
yandex-direct-v2.1.0
yandex-metrika-v2.1.0
yandex-webmaster-v2.1.0
```

For all four releases verify `draft=false`, `prerelease=false`, `immutable=true`, exact target SHA. Verify Repository 1.0.10 and previous plugin releases unchanged. Verify no Wordstat/Search/SEO/Marketing tag points to P0 SHA.

- [ ] **Step 8: Record final PR evidence**

Record exact merge/main SHA, post-merge CI run ID, publisher run ID, release IDs, tag SHAs, historical immutability result, and review-evidence status.

---

## Self-review mapping

- Spec §§6–8 -> Tasks 1, 3, 4.
- Spec §9 -> Tasks 1–4 and convergence Task 5.
- Spec §§10–14 -> Tasks 1–4 without unsupported read-back/rollback claims.
- Spec §15 -> Task 6 human-approval boundary.
- Spec §16 -> Tasks 2–4 preserve `--execute --approve` and add exact scale acknowledgement.
- Spec §17 -> Tasks 1–4 fail closed before transport.
- Spec §18 -> Task 5 behavioural convergence and matrix traceability.
- Spec §19 -> Direct, Metrika, Webmaster, convergence, docs, verification, release order.
- Spec §§20–21 -> Tasks 7–9 green-before-version, exact-head, exact-main, immutable publish.
- Spec §22 -> no P1 project-memory surface.
