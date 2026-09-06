# Yandex SEO 1.2.0 — Weekly Organic Report

This minor release adds the transport-free read-only `yandex-seo-weekly-report` workflow and portable reporting artifacts while preserving existing service ownership and preview-only write boundaries.

## Added

- Normative `seo-weekly-organic-report/v1` report contract for normalized Webmaster/Metrika evidence, exact periods, explicit coverage, provenance, findings, limitations and delegated previews.
- `yandex-ai-artifact-manifest/v1` with SHA-256 managed-file verification and immutable snapshot semantics.
- A self-contained `report.html` renderer with restrictive CSP, escaped source/user text, no CDN, no remote fonts, no analytics and no network fetch.
- Deterministic Mermaid/DOT exports for structural, semantic, cluster and internal-link structures only when those structures are present in source evidence.
- `demo` and `build` CLI modes through `scripts/seo_weekly_report.py`; the sanitized demo needs no credentials or network access.
- Optional read-only P1 Project Memory context limited to project identity and active `USER_STATED` facts.

## Safety and ownership

- `yandex-seo` remains transport-free and has no Yandex credentials or HTTP client.
- Partial/missing source coverage remains explicit; stale/history data never masquerades as fresh evidence.
- Delegated actions are `PREVIEW-ONLY` and do not grant live-write permission or reusable approval.
- Existing P0 exact-preview, later-turn approval and bulk/unknown acknowledgement contracts remain unchanged.

## Release

Plugin version `1.2.0`, canonical tag `yandex-seo-v1.2.0`.
