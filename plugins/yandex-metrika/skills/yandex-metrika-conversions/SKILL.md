---
name: yandex-metrika-conversions
description: Use when analyzing Yandex Metrika goals, conversion rate, funnels, goal reach or conversion changes.
---

# Analyze conversions

Read `../../references/reporting.md` and `../../references/audit-framework.md`.

## Workflow

1. Read the configured goals.
2. Identify which goals represent **business outcomes** versus micro/technical events. Do not silently treat the first goal or all goals as equivalent business conversions.
3. State whether the metric basis is visits, users, reaches or ecommerce transactions.
4. Compare explicit periods with the same goal definitions and attribution context.
5. Preserve traffic rows/sources with **zero** goal reaches when evaluating conversion quality: zero conversions do not remove visits from the **denominator**.
6. Drill down by source/device/landing or another relevant dimension only after confirming enough data.

Do not combine unrelated goals into one CPA/CR without explaining the aggregation. If a goal was renamed/reconfigured during the period, flag comparability risk.

A zero denominator makes the corresponding ratio unavailable; do not report it as 0% performance. Low-volume zero-conversion rows are evidence of current observations, not proof that the source can never convert.

For writes such as creating or changing a goal, hand off to `yandex-metrika-goals`.
