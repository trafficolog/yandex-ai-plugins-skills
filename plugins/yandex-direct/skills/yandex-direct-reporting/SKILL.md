---
name: yandex-direct-reporting
description: Use when producing Yandex Direct performance reports, period comparisons, campaign or keyword statistics, search-query reports, conversion analysis, or KPI summaries.
---

# Report on Yandex Direct

Read `../../references/reporting.md` and `../../references/api-2026.md`.

## Before fetching

State the exact date range, comparison range, account currency, VAT treatment, conversion goals, and attribution model when those affect the answer.

Before CPA/CR or economic conclusions, identify the **business conversion goals** that represent valuable outcomes. Do not silently substitute the first goal, a strategy goal, or an aggregate of all goals for business intent. When the business goal is unknown, show the available goal names/IDs and keep the conclusion provisional until the relevant goal set is clear.

Use Reports v501. If a report is queued (201) or still generating (202), resend the same request after `retryIn`; do not regenerate `ReportName` or mutate fields while polling.

## Comparable evidence

Compare periods only on a comparable basis: same business goals, attribution, account currency/VAT treatment and material filters/placements. Surface conversion delay and incomplete periods before calling a recent change better or worse.

For aggregate KPIs, **aggregate raw** impressions, clicks, spend, conversions and revenue first, then recompute CTR/CPC/CR/CPA/ROAS from the totals. Do not take an ordinary mean of row-level ratios. A **zero denominator** means the ratio is unavailable, not that performance equals zero.

Multiple goals may be reached by the same visit/user; do not sum goal reaches and call the result unique leads/orders unless uniqueness is independently established.

## Interpretation

Calculate only metrics supported by available data. If revenue is missing, do not infer ROAS/DRR. If goals are ambiguous, show conversion metrics by goal or label the ambiguity.

For keyword/query decisions include spend, clicks, conversions, and criterion type. Separate autotargeting when useful. For placement decisions include `AdNetworkType` or equivalent supported grouping.

Use a practical evidence chain for recommendations: **observation → possible cause → verification → proposed action → effect metric**. Low volume is a data-sufficiency limitation, not proof of a cause.

## Helper

When local Python is available, `../../scripts/yd_report.py` provides v501 presets and correct offline polling behavior. Inspect and customize fields/filters rather than assuming a preset is sufficient for every question.
