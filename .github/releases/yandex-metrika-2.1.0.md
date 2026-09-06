Yandex Metrika 2.1.0 — executable write-safety v2.

- Consequential Metrika operations use `yandex-ai-approval/v2` with authenticated-principal binding, exact target/request, cardinality, and declared safety capability.
- Generic Management writes are `UNKNOWN` scale and require `--ack-bulk` after exact preview approval before transport. Repository threshold `20` is internal safety policy, not a Yandex API limit.
- Logs `create`/`clean` and each import are one API operation (`KNOWN`, `items=1`); CSV row count does not redefine API-operation cardinality.
- Import approval continues to bind SHA-256 of exact file bytes and now explicitly carries `artifact_rows` and expense `risk_flags`; Direct/unverified expense provenance retains its separate explicit risk override.
- Successful consequential calls return `yandex-ai-execution/v1`; P0 verification is `RESPONSE_ONLY` / `UNVERIFIED` and rollback is `NOT_AVAILABLE`.
- Standalone CLI exact-preview enforcement does not prove later-turn human authorization; the host/operator remains responsible for that approval provenance.
