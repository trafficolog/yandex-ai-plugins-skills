# Implementation plan: practitioner-informed workflows

## Goal

Integrate practice-proven decision workflows from the pinned Polyakov skill set into the five matching Yandex plugins while preserving repository safety contracts and minimizing new runtime surface.

## Architecture

Keep the current decomposed plugin architecture. Behavioral guidance is added to the smallest owning skill. Only Yandex Search receives runtime code because smart snippets are an official API feature missing from the shipped helper layer.

## Tech stack

- Markdown skills/references/evals
- Python stdlib helpers and `unittest`
- repository validators and GitHub Actions CI
- existing independent plugin SemVer/release manifest process

## Global constraints

- SDD spec: `docs/superpowers/specs/2026-09-14-practitioner-workflows.md`
- source provenance: `artwist-polyakov/polyakov-claude-skills@f6a75133b3ad07e43991433c1d0a77f69c749f7b`
- strict RED -> GREEN -> REFACTOR for production changes
- no new shared release framework
- no weakening of exact-preview write safety
- DRY/KISS/YAGNI: reuse existing skill boundaries, no private Alice scraping, no new Search cache subsystem

## Task 1 — RED: Search smart-snippet runtime contract

Files:
- modify `plugins/yandex-search/tests/test_ys_request.py`
- modify `plugins/yandex-search/tests/test_ys_parse.py`

Tests first:
- smart snippets add `metadata.fields.x-genesis-info-context=on`;
- reject async smart snippets;
- reject non-RU smart snippets;
- reject smart-snippet result depth >20 with a practitioner-observed guardrail message;
- Base64 JSON response normalizes flat and `rich_data` fields and includes `extract`.

Expected RED reason: current request builder has no smart-snippet argument/metadata and parser supports only XML/HTML.

## Task 2 — RED: practical skill behavior contracts

Files:
- extend existing plugin layout/contract tests in Direct, Metrika, Webmaster, Wordstat;
- add only focused assertions for stable behavioral markers, not prose snapshots.

Expected contracts:
- Direct: meaningful goal selection, comparability, observation/hypothesis/verification/action/effect, data sufficiency and experiment stop criteria.
- Metrika: business vs micro goals, compatible comparison basis, zero-conversion denominator preservation, compatible cost/revenue PnL.
- Webmaster: summary-first triage, live volatile evidence, evidence-gated recrawl.
- Wordstat: business/region context, intent verification via Search for high-priority/ambiguous candidates, explicit rejected-demand reasoning, missed-demand route.

Expected RED reason: current skills are less explicit about these practitioner workflows.

## Task 3 — GREEN: Search runtime

Files:
- `plugins/yandex-search/scripts/ys_request.py`
- `plugins/yandex-search/scripts/ys_parse.py`
- minimal skill/reference docs as required.

Implementation:
- optional `smart_snippets: bool = False` in request builder;
- fail closed on async/non-RU/>20;
- metadata flag only when enabled;
- parser detects JSON smart-snippet payload and normalizes flat/rich-data variants;
- preserve classic XML/HTML behavior.

Run exact Search tests through CI after commit.

## Task 4 — GREEN: Direct practical workflow

Files expected:
- `skills/yandex-direct-reporting/SKILL.md`
- `skills/yandex-direct-audit/SKILL.md`
- `skills/yandex-direct-keywords/SKILL.md`
- `skills/yandex-direct-optimize/SKILL.md`
- `skills/yandex-direct-budget/SKILL.md`
- one compact practitioner reference if duplication becomes material.

Implementation should prefer a single reference only for genuinely shared decision-loop rules; service-specific rules stay in owning skills.

## Task 5 — GREEN: Metrika practical workflow

Files expected:
- `skills/yandex-metrika/SKILL.md`
- `skills/yandex-metrika-reporting/SKILL.md`
- `skills/yandex-metrika-conversions/SKILL.md`
- `skills/yandex-metrika-ecommerce/SKILL.md`

Do not change modern attribution defaults/contracts.

## Task 6 — GREEN: Webmaster practical workflow

Files expected:
- `skills/yandex-webmaster/SKILL.md`
- `skills/yandex-webmaster-audit/SKILL.md`
- `skills/yandex-webmaster-indexing/SKILL.md`
- `skills/yandex-webmaster-recrawl/SKILL.md`

No Alice/private SSR support.

## Task 7 — GREEN: Wordstat practical workflow

Files expected:
- `skills/yandex-wordstat/SKILL.md`
- `skills/yandex-wordstat-research/SKILL.md`
- `skills/yandex-wordstat-semantics/SKILL.md`
- add focused `yandex-wordstat-missed-demand` skill only if routing remains clearer than overloading semantics/research; otherwise keep within existing skills.

KISS preference: extend existing skills unless a new skill has an independently discoverable user intent and avoids duplicated instructions.

## Task 8 — Eval scenarios and documentation

Add/adjust v2 eval scenarios so practitioner workflows are semantically testable, especially:
- Direct low-volume/ambiguous optimization;
- Metrika microgoal-vs-business-goal ambiguity;
- Search answer task vs rank-only batch choice;
- Webmaster blanket recrawl request;
- Wordstat adjacent-demand false positive.

Update RU/EN plugin README/CHANGELOG surfaces only for released public contract changes.

## Task 9 — SemVer/release set

After implementation and before publication, inspect actual changed public contracts and apply repository policy:
- repository minor for coordinated compatible capability change;
- plugin minor only for plugins whose public/runtime/documentation contract changed materially;
- no version bump for untouched SEO/Marketing.

Expected candidate release set, subject to exact changed scope:
- repository `1.5.0`
- Direct `2.2.0`
- Metrika `2.2.0`
- Search `1.1.0`
- Webmaster `2.2.0`
- Wordstat `1.2.0`

The release manifest is updated only after GREEN implementation and release-surface tests.

## Task 10 — Verification and merge

1. PR exact-head CI GREEN.
2. Record review availability truthfully; do not equate CI with independent review.
3. Human authorization is supplied by the user request for this implementation/release workflow unless they later narrow it.
4. Squash merge with expected exact head SHA.
5. Exact-main CI GREEN.
6. Canonical `publish-current-release.yml` publishes only the declared set.
7. Verify repository and plugin tags/releases point to the exact merge SHA and older immutable releases remain unchanged.
