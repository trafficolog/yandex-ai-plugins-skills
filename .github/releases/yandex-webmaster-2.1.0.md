Yandex Webmaster 2.1.0 — executable write-safety v2.

- Consequential Webmaster calls use `yandex-ai-approval/v2`, binding API version, exact request/target, OAuth authenticated-principal identity, credential-safe feed URL representation, cardinality, and declared safety capability.
- Embedded URL Basic Auth credentials stay secret; their approval representation uses OAuth-keyed/domain-separated HMAC material, so credential or OAuth-principal changes invalidate approval without exposing a reusable password verifier.
- Known single operations are `KNOWN`, `items=1`; feed batch add/remove bind exact `feeds`/`urls` length; opaque generic writes are `UNKNOWN`.
- Repository threshold `20` is internal safety policy, not a Yandex API limit. Batch `>20` and `UNKNOWN` execution require `--ack-bulk` after exact preview approval and fail closed before transport otherwise.
- Successful consequential writes return `yandex-ai-execution/v1`; P0 verification is `RESPONSE_ONLY` / `UNVERIFIED` and rollback is `NOT_AVAILABLE`.
- Standalone CLI exact-preview enforcement does not prove later-turn human authorization; the host/operator remains responsible for that approval provenance.
