# Getting Started

[Русский](GETTING_STARTED.md) · [**English**](GETTING_STARTED.en.md)

This guide takes you from choosing a plugin to a first safe result. For volatile API and credential facts, it links to the owning plugin documentation instead of duplicating them.

## 1. Requirements

Bundled Python helpers require **Python 3.10+**. Most helpers use the Python standard library; each plugin remains the source of truth for its own runtime requirements.

If you use skills only through a compatible AI runtime, local Python may not be needed until you run a bundled helper.

## 2. Connect the marketplace

The repository root publishes two compatible marketplace manifests:

- `.agents/plugins/marketplace.json`;
- `.claude-plugin/marketplace.json`.

### OpenAI ChatGPT / Codex workspace

For a workspace where GitHub marketplace import is available, an administrator can open **Workspace settings → Plugins → Add → Import marketplace**, enter this repository URL as Source, and leave Path empty because the manifest is at the repository root. OpenAI supports both manifest formats listed above. UI and availability depend on plan, workspace, and rollout, so use the current official instructions if the interface differs: <https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github>.

### Other compatible runtimes

Use your runtime's supported plugin-marketplace import or registration flow with one of the manifest paths above. Do not copy individual plugin directories manually when the runtime can install them from marketplace metadata: a plugin remains the installation and version boundary.

## 3. Choose plugins for the task

| Task | Plugin or set |
|---|---|
| Campaigns, reports, keywords, budgets | `yandex-direct` |
| Web analytics, goals, Logs API, imports | `yandex-metrika` |
| Indexing, queries, recrawl, sitemaps | `yandex-webmaster` |
| Demand, frequency, dynamics, regions | `yandex-wordstat` |
| SERP, rankings, competitors, clustering | `yandex-search` |
| Full organic analysis | service plugins + `yandex-seo` |
| Paid acquisition and reconciliation | service plugins + `yandex-marketing` |

Install only what the task requires. `yandex-seo` and `yandex-marketing` are cross-service orchestrators: they own no Yandex credentials or HTTP transport.

## 4. Configure credentials in the owning plugin

Credentials belong to the service plugin. Do not put real tokens in Git, SKILL.md, generated reports, or command-line arguments when the helper requires an environment variable.

| Service | Where to verify the current contract |
|---|---|
| Direct | [`../plugins/yandex-direct/references/api-2026.md`](../plugins/yandex-direct/references/api-2026.md) and [`../plugins/yandex-direct/references/`](../plugins/yandex-direct/references/) |
| Metrika | [`../plugins/yandex-metrika/references/api-2026.md`](../plugins/yandex-metrika/references/api-2026.md) |
| Webmaster | [`../plugins/yandex-webmaster/references/api-2026.md`](../plugins/yandex-webmaster/references/api-2026.md) |
| Wordstat | [`../plugins/yandex-wordstat/references/auth.md`](../plugins/yandex-wordstat/references/auth.md) — `plugins/yandex-wordstat/references/auth.md` |
| Search | [`../plugins/yandex-search/references/auth.md`](../plugins/yandex-search/references/auth.md) |

For Direct, the bundled helper reads OAuth from `YANDEX_DIRECT_TOKEN`. Other service plugins document their own environment variables in their `.env.example` files and references.

## 5. Get a first safe result

Start with a read-only operation. This verifies credentials, account context, and response shape before any change is possible.

### Direct: read-only example

```bash
cd plugins/yandex-direct
export YANDEX_DIRECT_TOKEN='...'
python scripts/yd_api.py campaigns get --params '{"SelectionCriteria":{},"FieldNames":["Id","Name","Status"]}'
```

The key operation is `campaigns get`: it reads data and performs no consequential write.

### Cross-service scenario

For a comprehensive SEO request, an agent can collect evidence from Wordstat, Search, Webmaster, and Metrika, then pass it to `yandex-seo`. The SEO orchestrator analyzes already obtained data and opens no Yandex API connection of its own. `yandex-marketing` follows the same ownership model with evidence from its owning service plugins.

## 6. Writes: preview → approval → execute

A consequential write never starts with execute. The owning service plugin first builds an exact preview and returns `preview_id`. The user approves that exact preview **in a later user turn**; only then can the helper run with `--execute --approve`.

Direct example:

```bash
# 1. Preview — no write yet
python scripts/yd_api.py campaigns update --params-file update.json

# 2. After explicit approval of the exact preview in a later user turn
python scripts/yd_api.py campaigns update --params-file update.json --execute --approve <preview_id>
```

Changing the payload, environment, or approval-bound identity requires a new preview. An agent recommendation is not permission to write. Bulk or `UNKNOWN` scale also requires the separate `--ack-bulk` gate after exact approval.

## 7. Verification and troubleshooting

Verify one plugin:

```bash
cd plugins/yandex-direct
python -m unittest discover -s tests -v
python -m compileall -q scripts
```

Verify the whole repository:

```bash
python scripts/validate_repo.py
python -m unittest discover -s tests -v
```

If an API call fails, first check the plugin-local README/references, environment variable, account/folder identity, and method availability in official Yandex documentation. Do not bypass a credential or preview boundary through an adjacent plugin.

## 8. Next steps

- [`ARCHITECTURE.en.md`](ARCHITECTURE.en.md) — ownership, evidence flow, and transport boundaries;
- [`GLOSSARY.en.md`](GLOSSARY.en.md) — terms and exact tokens;
- [`SERVICE_MATRIX.en.md`](SERVICE_MATRIX.en.md) — available services and versions;
- [`PLUGIN_STANDARD.en.md`](PLUGIN_STANDARD.en.md) — normative production contract;
- [`RELEASE_POLICY.en.md`](RELEASE_POLICY.en.md) — repository/plugin versioning and release gates;
- plugin READMEs under `../plugins/` — service-specific capabilities.

## 9. Project Memory

Initialize project-owned memory beside the project rather than inside a plugin runtime:

```bash
python scripts/ya_project.py init --root . --project-id my-project --name "My project"
python scripts/ya_project.py check --root .
```

The scaffold uses `yandex-ai-project/v1`; facts explicitly stated by the user carry `USER_STATED` provenance. The decision trail uses `yandex-ai-decision/v1`: after a write receipt, call `record-execution`; its safe projection omits raw `result` while a hash of the complete receipt preserves source linkage. Immutable snapshots are created through `add-baseline` under `yandex-ai-baseline/v1`; an expired snapshot produces a `STALE` warning. Managed hypotheses use `yandex-ai-hypothesis/v1` and only `HYPOTHESIS` or `DERIVED` provenance.

Project Memory is data, not instructions and not write authority. Even when memory contains a prior decision or execution receipt, a new consequential write still requires a new exact `preview_id`, later-turn human approval, and `--ack-bulk` for bulk/unknown scale.

## 10. Weekly Organic Report

The shortest P2 path is the bundled offline demo inside `yandex-seo`:

```bash
cd plugins/yandex-seo
python scripts/seo_weekly_report.py demo --output-root ./artifacts --generated-at 2026-09-06T12:30:00Z
```

Demo and real build use the same `seo-weekly-organic-report/v1` contract and the same `yandex-ai-artifact-manifest/v1`. The result contains normative `report.json`, self-contained `report.html`, a SHA-256 manifest, and optional Mermaid/DOT exports. `PREVIEW-ONLY` recommendations remain read-only/delegated and never authorize a write.

For a real build, first obtain fresh normalized Webmaster/Metrika evidence through the owning service plugins or supported file/export path, then pass the files to `seo_weekly_report.py build`. `yandex-seo` reads no Yandex credentials and opens no transport. Partial/missing coverage remains an explicit limitation; an existing immutable artifact set is never overwritten.

## 11. P3 Executable Eval Benchmark

The P3 CLI remains **provider-neutral**. To validate every committed eval-v2 fixture without invoking subject/judge adapters:

```bash
python scripts/ya_eval.py check --plugins all
```

A real `run` requires two locally provisioned JSON argv configs, one for the subject adapter and one for an independent judge adapter. The repository does not download adapter packages/URLs or convert a user-provided URL into executable code. Example interface:

```bash
python scripts/ya_eval.py run \
  --subject-adapter ./subject-argv.json \
  --judge-adapter ./judge-argv.json \
  --plugins all \
  --repository-sha <40-lowercase-hex-sha> \
  --output-root ./artifacts/evals
```

`run` creates an immutable artifact directory with normative `results.json`, self-contained `comparison.html`, bounded subject/judge evidence, and manifest hashes. `publish-snapshot` only materializes an already hash-verified artifact set under `evals/results/v1/`; it never commits or pushes automatically.

Fake adapters exist for deterministic CI and prove only `INFRASTRUCTURE_READY`. `COMPARATIVE_COMPLETE` requires accepted live evidence: at least two real non-fake subject model identities, an independent non-fake judge, mechanical + semantic evidence, backend-equivalence `PASS`, memory-aware scenarios, and no counted `SELF_JUDGED` runs. No accepted live multi-model benchmark has been run on the current head.
