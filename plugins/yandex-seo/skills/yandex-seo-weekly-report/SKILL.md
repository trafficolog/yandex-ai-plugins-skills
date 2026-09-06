---
name: yandex-seo-weekly-report
description: Use when producing a read-only weekly organic performance report from Yandex Webmaster and Yandex Metrika evidence with portable artifacts.
---

# Weekly Organic Report

Build a **read-only** Weekly Organic Report from normalized Webmaster and Metrika evidence. Preserve exact current/comparison periods, source coverage, Webmaster top-N/filter limitations, and Metrika sampling/data-quality metadata before interpreting changes.

The machine source of truth is `seo-weekly-organic-report/v1`. The artifact set is described by `yandex-ai-artifact-manifest/v1` and contains deterministic `report.json`, a self-contained `report.html`, plus Mermaid/DOT files only when matching source structures actually exist.

Use `../../scripts/seo_weekly_report.py demo` for the bundled credential-free fixture. Use `build` only with read-only evidence produced by the owning service plugins or equivalent normalized files. This SEO workflow owns no Yandex transport or credentials.

Treat missing sources as explicit partial coverage instead of inventing completeness. Keep `OBSERVED`, `DERIVED`, `HYPOTHESIS`, and `METHODOLOGY` distinct. Project Memory is optional context only and never replaces fresh reads.

Delegated recommendations are **PREVIEW-ONLY**. They are not P0 approval, do not grant write permission, and must be routed to the owning service/CMS/deployment workflow if the user later requests a consequential mutation.

Read `../../references/weekly-organic-report.md` for the input and artifact contract.
