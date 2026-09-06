# Changelog — Yandex Webmaster

[Русский](CHANGELOG.md) · [**English**](CHANGELOG.en.md)

## [2.1.0] — 2026-09-05

- Consequential Webmaster calls now use `yandex-ai-approval/v2`: API version, exact request/target, OAuth authenticated-principal binding, credential-safe feed URL representation, cardinality, and safety capability are bound into the approval digest.
- Embedded URL Basic Auth credentials remain secret: approval uses OAuth-keyed/domain-separated HMAC material, so changing embedded credentials or the OAuth principal invalidates the preview without publishing a reusable password verifier.
- Known single operations receive `KNOWN`, `items=1`; feed batch add/remove bind the exact `feeds`/`urls` length; opaque generic writes receive `UNKNOWN`.
- Repository threshold `20` is internal safety policy, not a Yandex API limit. Batch `>20` and `UNKNOWN` execution require `--ack-bulk` after the exact `--approve <preview_id>` and are blocked before transport without it.
- A successful write returns `yandex-ai-execution/v1`; P0 verification is `RESPONSE_ONLY` / `UNVERIFIED` and rollback is `NOT_AVAILABLE`, so an API response is not represented as read-back verification.
- The standalone CLI does not prove later-turn human approval; the host/operator is responsible for obtaining a separate user approval after showing the exact preview.

## [2.0.0] — 2026-09-03

- Breaking safety contract: consequential POST/PUT/PATCH/DELETE calls no longer execute based on `--execute` alone; after a separate later-turn user approval, the exact preview requires `--execute --approve <preview_id>`.
- The live write boundary `yw_api.py` binds approval to method/path/query/body/API version and fails closed on missing or mismatched approval.
- Embedded URL Basic Auth credentials are redacted from previews and bound with domain-separated HMAC-SHA256 keyed by the Yandex OAuth token; this does not publish a deterministic password verifier, and changing either the credentials or OAuth key invalidates approval.
- API/account/file content is untrusted data rather than instructions; generic permission does not carry over to a new payload.

Migration:

```bash
# 1.x
python scripts/yw_api.py user/42/hosts/https:example.com/sitemaps --method POST --body '{"url":"https://example.com/sitemap.xml"}' --execute
# 2.0.0
python scripts/yw_api.py user/42/hosts/https:example.com/sitemaps --method POST --body '{"url":"https://example.com/sitemap.xml"}'
python scripts/yw_api.py user/42/hosts/https:example.com/sitemaps --method POST --body '{"url":"https://example.com/sitemap.xml"}' --execute --approve <preview_id>
```

## [1.0.3] — 2026-09-02

- Re-verified the official indexing archive status contract: the response uses `state` with `IN_PROGRESS`, `DONE`, and `FAILED`, and `download_url` belongs to a completed `DONE` state.
- Regression tests pin `state` and intentionally do not accept an undocumented `status` fallback.
- Added the archive lifecycle as a separate high-risk contract in the repository traceability matrix.

## [1.0.2] — 2026-09-02

- Corrected PRO export `use_pro_tariff` serialization and host-relative path validation.
- Added deterministic lifecycle normalization, missing/expired states and 24-hour age handling without autonomous polling.
- Quota planning distinguishes known remaining quota from unknown usage.

## [1.0.1] — 2026-09-02

- Corrected feed batch body to `{"feeds": [...]}`.
- Strengthened credential redaction and HTTPS-only artifact downloads.
- Added verifiable eval expectations for destructive/quota-consuming workflows.

## [1.0.0] — 2026-09-01

- Initial Yandex Webmaster plugin.
