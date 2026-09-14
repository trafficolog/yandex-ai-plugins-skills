---
name: yandex-wordstat-research
description: Use when the user wants an end-to-end Wordstat demand study, niche research, content-demand brief, missed-demand analysis, or multi-step keyword investigation.
---

# Wordstat research

Workflow:

1. Define **what the business sells/provides**, the business objective, region/device assumptions and seed set; do not invent missing commercial intent.
2. Estimate planned calls by method. Current documented hourly limit is **100**; use a default safety budget of **90**.
3. Produce a **cost preview** using current dated rates before a large batch.
4. Run GetTop expansion, then targeted Dynamics/Regions only for candidates worth the extra paid calls.
5. Classify candidates as **target demand**, adjacent/non-target, informational, navigational, or ambiguous as applicable. Keep a reason for rejected/adjacent candidates rather than silently dropping them.
6. Validate high-priority or **ambiguous** intent with Yandex Search when available. Ask whether the query is likely to lead to the product/service the business actually offers, not merely a related accessory, DIY/repair task, or informational need.
7. Keep nested results, associations, filters, provenance and collection time.
8. Summarize demand patterns without summing overlapping phrase counts into market size.
9. Write large datasets to an artifact/file and keep the conversational summary compact.

For large semantic collections, validate representative/high-value clusters and ambiguous candidates instead of paying for a Search request for every row.

## Missed demand against existing Direct semantics

When the user wants opportunities missing from an existing Yandex Direct campaign/export:

1. Read normalized current phrases/groups and their group/campaign context; do not require a new XLSX parser if the data is already available as API/export/file rows.
2. Classify each group intent before expansion: transactional, branded, navigational, informational, or mixed/ambiguous.
3. Expand only with intent-compatible variants. Do not turn branded groups into generic competitors, or informational groups into transactional groups merely to inflate volume.
4. Compare normalized Wordstat candidates with current Direct semantics and negatives; preserve source seed/group provenance for every uncovered candidate.
5. Use Yandex Search to verify high-priority or ambiguous uncovered intent when available.
6. Return proposed additions grouped by Direct destination with evidence/reason, plus rejected/adjacent candidates and why they were excluded.
7. Any actual Direct change is routed back to the Direct plugin and remains subject to its exact-preview/later-turn approval contract.

Stop if the plan exceeds the safety budget without user awareness, credentials are missing, or the requested metric cannot be supported by Wordstat data.

References: `references/quota-pricing.md`, `references/semantics.md`, `references/safety.md`.
