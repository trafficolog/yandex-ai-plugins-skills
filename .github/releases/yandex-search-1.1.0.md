# Yandex Search 1.1.0

Adds bounded smart-snippet/info-context research while preserving ordinary SERP behavior.

- Synchronous semantic research may use `SEARCH_TYPE_RU` with `metadata.fields["x-genesis-info-context"]="on"`.
- Smart-snippet JSON is normalized separately from ordinary XML SERP into rank/URL/domain/title/snippet/extract evidence.
- Ordinary synchronous/deferred SERP remains the default for rankings, batch collection, snapshots, competitors, and clustering.
- The existing ordinary SERP 250-result depth contract is unchanged.
- The small smart-snippet result set is a practitioner/repository guardrail, not a claimed general official API limit.

Source methodology provenance: `artwist-polyakov/polyakov-claude-skills@f6a75133b3ad07e43991433c1d0a77f69c749f7b`.
