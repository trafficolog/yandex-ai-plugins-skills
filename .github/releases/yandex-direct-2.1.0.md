Yandex Direct 2.1.0 — executable write-safety v2.

- Consequential Direct previews use `yandex-ai-approval/v2` and bind exact service/method/environment/body, `Client-Login`, authenticated-principal identity, cardinality, and declared safety capability.
- Known entity-list writes bind exact item count; opaque write shapes are `UNKNOWN`. Repository threshold `20` is internal safety policy, not a Yandex API limit.
- Bulk `>20` and `UNKNOWN` execution require `--ack-bulk` after exact `--approve <preview_id>` and are blocked before transport without it.
- Successful consequential writes return `yandex-ai-execution/v1` receipts carrying the approved preview identity.
- P0 verification is `RESPONSE_ONLY` / `UNVERIFIED`; rollback capability is `NOT_AVAILABLE`. The release does not claim read-back verification or automatic rollback.
- Standalone CLI exact-preview enforcement does not prove later-turn human authorization; the host/operator remains responsible for that approval provenance.
