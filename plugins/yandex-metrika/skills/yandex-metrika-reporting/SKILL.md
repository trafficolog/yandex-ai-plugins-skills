---
name: yandex-metrika-reporting
description: Use when building or interpreting Yandex Metrika traffic, source, page, UTM, device, geography, time-series or comparison reports.
---

# Report with Yandex Metrika

Read `../../references/reporting.md` and `../../references/attribution.md`.

## Before fetching

State the counter, exact date range, comparison range, metrics, dimensions, filters, attribution model and accuracy when they affect interpretation.

Use table/bytime/comparison/drilldown endpoints intentionally rather than forcing every question into one table.

## Comparable basis

When conversion performance is part of the question, use the **same goal** definitions and the **same attribution** model across compared periods. Keep material filters, visit/user basis and ecommerce/currency treatment comparable. If a goal was reconfigured or the token has **incomplete access**, surface that limitation before ranking sources or recommending optimization.

Do not drop traffic rows solely because they have zero goal reaches. Preserve the traffic denominator so “no observed conversions” remains distinguishable from “no traffic/data”.

## Data quality

Always inspect and surface material response metadata: `sampled`, `sample_share`, `sample_size`, `sample_space`, `data_lag`, `contains_sensitive_data`, `total_rows_rounded`.

If sampling or disclosure limits are material, qualify the conclusion and avoid false precision. Treat access/completeness limitations the same way: partial data must not be presented as a complete account view.

## Interpretation

Decompose changes before assigning causes: source/channel → campaign/referrer → device → landing/page → conversion/revenue as supported by the data. Do not infer revenue, ROAS or ecommerce outcomes if those metrics are absent.

When local Python is available, `../../scripts/ym_report.py` builds current report requests and returns the API payload plus a separate `quality` object.
