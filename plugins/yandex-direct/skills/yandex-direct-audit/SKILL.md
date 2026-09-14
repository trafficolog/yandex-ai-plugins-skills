---
name: yandex-direct-audit
description: Use when auditing a Yandex Direct account, campaign export, PPC setup, tracking quality, search-query waste, bidding configuration, or account hygiene.
---

# Audit Yandex Direct

Read `../../references/audit-framework.md`, `../../references/reporting.md`, and `../../references/api-2026.md`.

## Audit method

Collect evidence first. Separate configuration evidence from performance evidence. Mark checks PASS, ISSUE, REVIEW, or N/A; do not penalize N/A.

Before economic scoring, identify which configured goals are meaningful business outcomes and whether the audited period has enough mature conversion data. A technical goal, strategy goal or low-volume sample must not silently become the account's business KPI.

Audit these domains: measurement, economics, query quality, structure/EPK placements, ads/assets, strategy, device/audience/placement segmentation, and recent change risk.

For every material ISSUE/REVIEW item use the practical chain: **observation → possible cause → verification → next action → effect metric**. State data-sufficiency limitations and distinguish a confirmed defect from an experiment worth testing.

## Important corrections to older audit templates

- Do not require separate Search and Network campaigns universally; EPK can combine placements. Judge separation by control/measurement need.
- Do not require “2 ads per group” or “keyword in title” as universal pass/fail rules.
- Do not treat a fixed CTR/CPC/CPA benchmark as proof of quality without industry/account context.
- Do not auto-pause on a fixed 2×/3× CPA heuristic without sample size and conversion-delay analysis.
- Treat autotargeting as a first-class criterion and report it separately where possible.
- Treat `RARELY_SERVED` as a data-sufficiency/structure signal, not an automatic reason to delete a phrase or create more fragmented groups.
- Verify current moderation, asset, and strategy rules before calling them violations.

## Deliverable

Return: executive summary, evidence table, high-impact issues, quick fixes, experiments, items requiring more data, and optionally a transparent score with published weights. Experiments should include baseline, observation window, success criterion and stop/revert criterion before any consequential change is proposed for execution.
