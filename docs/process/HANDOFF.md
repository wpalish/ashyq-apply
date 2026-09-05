# HANDOFF — the baton

One file, always current, committed with the code. The agent who holds the baton keeps it true.
Rules for using it: `AGENTS.md`. Task definitions: `analysis/AI_TASK_BRIEF.md` §6.
Write for a reader who has **zero** chat history — because that is exactly who reads it.

## 1. Baton

| | |
|---|---|
| Holder | nobody |
| Since (UTC) | — (recovery inventory in progress; baton not yet taken) |
| Branch | `main` (observed; planned recovery branch `task/0.8-ranking-ui` does not yet exist as an action of this writer) |
| HEAD when written | `c924410a1adcdc7d131d4e0630e3e392fc1cf038` |
| Origin main when checked | `627d42d5fd42c1489dbeb7bd2dea43763914c7f5`; local main 7 ahead / 0 behind |
| Previous holder | template recorded owner; predecessor commits have Claude co-author lines but no required Agent trailers; no valid baton acquisition recorded |
| Recovery audit started (UTC) | 2026-09-05 18:31:27 UTC |

The coordinating task verified successful fetch. This writer independently checked branch, log,
ahead/behind and the empty index. This is an initial recovery record, not a claim that a branch,
checkpoint, push, baseline gates or baton commit has completed.

## 2. Current task

`[0.8] Frontend этапа 0` — **in-progress (prompt C recovery)**, inferred from the eight dirty frontend
paths and preceding [0.1]–[0.7] commits. Recovery checkpoint and baton acquisition are pending.
The stale template's `none` / next `[0.1]` / HEAD `627d42d` did not describe the checkout.
Predecessor acceptance remains unverified; the inherited I4/T3 contradiction is open (§7).
Status vocabulary: `not-started` · `in-progress` · `blocked` · `ready-for-review (PR #)` · `merged`.

## 3. Done in this task (commit hash per item — a claim without a hash is not done)

No recovered [0.8] commit exists yet. The following are **historical local commits**, verified by
`git log` and the changes from `627d42d..c924410`; they are not a claim of acceptance, review or merge
to origin/main. Preserve their hashes and ancestry. All seven lack the required `Agent:` trailer;
do not rewrite them to manufacture compliant history. [0.4] was committed before [0.3].

| Task mapping | Existing hash | Observed change |
|---|---|---|
| [0.1] | `f23407f` | Profile priorities, privacy field and weights override; profile tests. |
| [0.2] | `ea33051` | Priority/ROC weights module and ranking tests. |
| [0.4] | `3eefdcd` | Bucket enum and ranking/result schemas. |
| [0.3] | `0f46079` | Ranking v2 domain implementation, scoring changes and tests; inherited T3 issue (§7). |
| [0.5] | `0b8d97f` | Assessment from stored attributes, ranking config, bucket model/migration and pipeline tests. |
| [0.6] | `e1d8078` | Rerank, result sorting/filtering and balanced shortlist API; pipeline helpers and API tests. |
| [0.7] | `c924410` | Profile-field documentation and ADR 0003; ADR changes I4 interpretation without recorded owner resolution. |

## 4. Half-done / uncommitted at the moment of writing

Audit started **2026-09-05 18:31:27 UTC**. Read `git status --short --untracked-files=all`,
`git ls-files --others --exclude-standard`, `git diff -- docs/screenshots`, and `git diff --cached`.
The index is empty. All 36 screenshot paths have binary differences; no screenshot is staged.
Untracked files do not appear in ordinary `git diff`: their actual text was inspected and template/
duplicate hashes compared. At audit start: **44 tracked modifications = 36 screenshots + 8 frontend;
30 untracked files outside independent worktrees = 22 workflow/source files + 8 docs/v2 copies**.
The frontend audit agent owns the detailed review of all eight frontend diffs; its verdicts are pending.
No path is classified as junk. "Coherent source" means preservable source material, not approved
requirements, validated experiments, or accepted implementation.

### Frontend [0.8], per file — verdict from `git diff` (claude-opus-5, 2026-09-06)

Read every diff. All eight are one coherent change: the shortlist reads the v2 ranking instead of the
v1 sum. Typecheck, lint and the production build are green on this tree; one unit test is red and is
named below. **Finished code** = compiles, is used, and its behaviour is covered.

| Path | Verdict | What it is |
|---|---|---|
| `frontend/src/types.ts` | finished | `Bucket`, `PriorityGroup`, `AxisScore`, `RankingV2`, `RerankIn`, `BalancedShortlist`; `ProgramResult.ranking` / `catalog_attributes` / `catalog_attributes_source`, plus `size_fit` / `campus_fit` which the backend always sent and TS never declared. |
| `frontend/src/api/client.ts` | finished | `api.rerank(runId, body)` and `api.shortlist(runId)` over the [0.6] endpoints. |
| `frontend/src/lib/format.ts` | finished | `bucketTone`, `FIT_DISCLAIMER`, `ratio()`, `percent()`, bucket meanings. No bucket entered `STATUS_LABEL`: `humanize()` already renders them and the vocabulary test requires a real shortening. |
| `frontend/src/lib/store.tsx` | finished | `rerank()` and a `shortlist` that follows the rows through one effect, so no call site has to remember to refresh it. |
| `frontend/src/screens/ShortlistScreen.tsx` | finished | Match / Confirmed / Bucket columns, default sort `key` with an id tie-break, the balanced-shortlist panel with its notes, and OUT_OF_BUDGET / NEEDS_CLARIFICATION / EXCLUDED as collapsed sections under the ranked table. The large diff is one table extracted into `renderTable()` and reused by all four places. |
| `frontend/src/screens/PreferencesScreen.tsx` | finished | "What matters more?" — six ranked cards with up/down buttons, `weights_override` in the advanced spoiler, and "Recompute the shortlist" calling `rerank`. |
| `frontend/src/components/ResultDetail.tsx` | finished | `Axes` panel: per-axis value, weight, reason and state; knock-out reasons; falls back to the v1 breakdown when a row has no `ranking`. |
| `frontend/src/screens/ShortlistScreen.test.tsx` | **half-finished — one red test** | Four new cases. `shows the match, what is confirmed, and the bucket` fails: `getByText('Plausible')` matches twice, because `PLAUSIBLE_FIT` and the `PLAUSIBLE` bucket both render as "Plausible". The assertion is ambiguous; the component is not wrong. Fix by scoping the query to the `[data-label="Bucket"]` cell. |

No junk. Nothing stashed. The screenshots and the `docs/v2` duplicates stay out of the snapshot, exactly
as the previous inventory ruled.

### Workflow and source bundle — intended recovery snapshot

| Path | Verdict | Reason / treatment |
|---|---|---|
| `.github/PULL_REQUEST_TEMPLATE.md` | Finished/coherent source document or source artifact | Relay review checklist; matches supplied template. Include in explicit snapshot allowlist. |
| `AGENTS.md` | Finished/coherent source document or source artifact | Root relay rules; matches analysis/agents/AGENTS.md. Include in explicit snapshot allowlist. |
| `CLAUDE.md` | Finished/coherent source document or source artifact | Claude-specific relay instructions; matches template. Include in explicit snapshot allowlist. |
| `analysis/AI_TASK_BRIEF.md` | Finished/coherent source document or source artifact | Canonical task brief and fixed decisions; inherited I4/T3 conflict remains (§7). Include in explicit snapshot allowlist. |
| `analysis/ANALYSIS.md` | Finished/coherent source document or source artifact | Historical v1 algorithm audit; reported counts are historical, not current gates. Include in explicit snapshot allowlist. |
| `analysis/DEPLOYMENT_SECURITY_LEGAL.md` | Finished/coherent source document or source artifact | Source planning memorandum; preserve as supplied, no legal/deployment validation claimed. Include in explicit snapshot allowlist. |
| `analysis/DESIGN_agentic_search.md` | Finished/coherent source document or source artifact | Agent research architecture source and rationale. Include in explicit snapshot allowlist. |
| `analysis/README.md` | Finished/coherent source document or source artifact | Index connecting the analysis source bundle. Include in explicit snapshot allowlist. |
| `analysis/SPEC_matching_v2.md` | Finished/coherent source document or source artifact | Canonical detailed spec; same unresolved literal T3 conflict (§7). Include in explicit snapshot allowlist. |
| `analysis/TWO_AGENT_WORKFLOW.md` | Finished/coherent source document or source artifact | Relay design memorandum; includes historical checkout observations. Include in explicit snapshot allowlist. |
| `analysis/agents/AGENTS.md` | Finished/coherent source document or source artifact | Distributed root-rule template; byte-identical to root at audit start. Include in explicit snapshot allowlist. |
| `analysis/agents/CLAUDE.md` | Finished/coherent source document or source artifact | Distributed Claude template; byte-identical to root. Include in explicit snapshot allowlist. |
| `analysis/agents/HANDOFF.md` | Finished/coherent source document or source artifact | Unmodified initial baton template; coherent template, stale as live state. Include in explicit snapshot allowlist. |
| `analysis/agents/KICKOFF_PROMPTS.md` | Finished/coherent source document or source artifact | Supplied prompts A–D; C governs this recovery. Include in explicit snapshot allowlist. |
| `analysis/agents/PULL_REQUEST_TEMPLATE.md` | Finished/coherent source document or source artifact | Distributed PR template; byte-identical to installed copy. Include in explicit snapshot allowlist. |
| `analysis/agents/handoff_check.py` | Finished/coherent source document or source artifact | Distributed diagnostic script; byte-identical to installed copy, inspected, not edited. Include in explicit snapshot allowlist. |
| `analysis/reference/ranking_v2.py` | Finished/coherent source document or source artifact | Executable formula reference; arithmetic also exhibits the T3 contradiction; not a fresh gate result. Include in explicit snapshot allowlist. |
| `analysis/scripts/01_discovery_sensitivity.py` | Finished/coherent source document or source artifact | Historical v1 discovery/rescoring experiment; source preserved, not executed. Include in explicit snapshot allowlist. |
| `analysis/scripts/02_score_components.py` | Finished/coherent source document or source artifact | Historical v1 score decomposition experiment; source preserved, not executed. Include in explicit snapshot allowlist. |
| `analysis/scripts/03_climate_sensitivity.py` | Finished/coherent source document or source artifact | Historical v1 climate experiment; not yet a v2 acceptance check. Include in explicit snapshot allowlist. |
| `docs/process/HANDOFF.md` | Finished/coherent source document or source artifact | Live baton was identical to initial template; reconciled by this recovery audit. Include in explicit snapshot allowlist. |
| `scripts/handoff_check.py` | Finished/coherent source document or source artifact | Installed read-only relay diagnostic; UTF-8 runtime invocation required locally (§9). Include in explicit snapshot allowlist. |

### Frontend — provisional until the dedicated audit returns

| Path | Verdict | Scope / next evidence |
|---|---|---|
| `frontend/src/api/client.ts` | Half-finished frontend [0.8] | API client additions for rerank and balanced shortlist. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/components/ResultDetail.tsx` | Half-finished frontend [0.8] | Ranking axis presentation. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/lib/format.ts` | Half-finished frontend [0.8] | Fit/coverage/bucket display helpers. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/lib/store.tsx` | Half-finished frontend [0.8] | Ranking/shortlist state and actions. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/screens/PreferencesScreen.tsx` | Half-finished frontend [0.8] | Priority order, advanced weights and rerank controls. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/screens/ShortlistScreen.test.tsx` | Half-finished frontend [0.8] | Updated shortlist unit expectations; acceptance coverage pending audit. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/screens/ShortlistScreen.tsx` | Half-finished frontend [0.8] | Ranking columns, buckets and balanced shortlist. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |
| `frontend/src/types.ts` | Half-finished frontend [0.8] | Ranking and API payload types. Detailed audit and gates pending; preserve, snapshot only after coherence verdict. |

### Duplicate source bundle — preserve outside the recovery snapshot

| Path | Verdict | Reason / treatment |
|---|---|---|
| `docs/v2/AI_TASK_BRIEF.md` | Finished/coherent source copy | Diff against analysis copy changes only reference launch path from ../analysis/ to ../../analysis/; preserve this difference, do not silently normalize. Preserve untracked outside snapshot. |
| `docs/v2/ANALYSIS.md` | Finished/coherent source copy | Byte-identical to analysis/ANALYSIS.md. Preserve untracked outside snapshot. |
| `docs/v2/DESIGN_agentic_search.md` | Finished/coherent source copy | Byte-identical to analysis/DESIGN_agentic_search.md. Preserve untracked outside snapshot. |
| `docs/v2/SPEC_matching_v2.md` | Finished/coherent source copy | Byte-identical to analysis/SPEC_matching_v2.md. Preserve untracked outside snapshot. |
| `docs/v2/reference/ranking_v2.py` | Finished/coherent source copy | Byte-identical to analysis/reference/ranking_v2.py. Preserve untracked outside snapshot. |
| `docs/v2/scripts/01_discovery_sensitivity.py` | Finished/coherent source copy | Byte-identical to analysis/scripts/01_discovery_sensitivity.py. Preserve untracked outside snapshot. |
| `docs/v2/scripts/02_score_components.py` | Finished/coherent source copy | Byte-identical to analysis/scripts/02_score_components.py. Preserve untracked outside snapshot. |
| `docs/v2/scripts/03_climate_sensitivity.py` | Finished/coherent source copy | Byte-identical to analysis/scripts/03_climate_sensitivity.py. Preserve untracked outside snapshot. |

`backend/app/schemas/profile.py:225` mentions `docs/v2/AI_TASK_BRIEF.md` in a comment.
This is a documentary reference, not a runtime dependency; the canonical `analysis/AI_TASK_BRIEF.md`
is included. No duplicate is required to execute [0.8]. If a later concrete reference dependency
requires a duplicate, add that exact path to §5 before staging it; do not bulk-add `docs/v2`.

### Pre-existing screenshots — each preserved outside the recovery snapshot

The coordinating recovery task reports that these modifications existed before initial [0.1].
Their presence cannot be attributed to the frontend cut-off. Binary diff inspection establishes
changed assets, not a reason to discard them; no visual acceptance review is claimed.

| Path | Verdict / treatment |
|---|---|
| `docs/screenshots/01-profile.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/02-preferences.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/03-progress-running.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/04-progress-complete.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/05-shortlist.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/06-university-detail-funding.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/07-university-detail-requirements.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/08-funding-comparison.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/09-sources-conflicts.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/10-approved.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/11-documents.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/12-export.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/01-profile.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/02-preferences.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/03-progress-running.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/04-progress-complete.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/05-shortlist.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/06-university-detail-funding.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/07-university-detail-requirements.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/08-funding-comparison.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/09-sources-conflicts.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/10-approved.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/11-documents.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/12-export.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/responsive-1024.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/responsive-1440.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/responsive-320.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/responsive-768.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/theme-dark.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/mobile/theme-light.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/responsive-1024.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/responsive-1440.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/responsive-320.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/responsive-768.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/theme-dark.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |
| `docs/screenshots/theme-light.png` | Unrelated pre-existing screenshot asset — preserve, do not stage/revert/delete. |

`.claude/worktrees/payments-phase-1/` and `.claude/worktrees/social-module/` are independent user
repositories, reported as directory entries by parent Git. Their contents are excluded from this
inventory; do not traverse, stage, stash, reset or otherwise modify them. They are not junk.

This writer changes only `docs/process/HANDOFF.md`; no optional long audit file was needed.
No branch, commit, push or stash has been performed by this writer.

## 5. NEXT STEP — exact and executable

Recovery write-ahead for the coordinating agent; **none of the Git mutations below has been executed
by this inventory writer**. Its write scope is only this file. Prompt C explicitly authorizes a
preserving recovery checkpoint; it does not resolve the requirement conflict in §7.

**Predecessor branch exception (AGENTS §4):** branch [0.8] from the current local predecessor tip
`main@c924410`, which contains [0.1]–[0.7], even though these predecessors are not on `origin/main`.
The intended relationship is `origin/main@627d42d → seven preserved local predecessor commits →
task/0.8-ranking-ui → recovery checkpoint → baton commit`. This is an explicit recovery exception,
not acceptance of the predecessors or permission to push main. Do not reset, rebase, amend, cherry-pick
or restart [0.1]. Do not use the stale template's one-time bootstrap push to main.

1. Finish prompt A/C baseline reconciliation: paste the successful UTF-8 handoff-check output and
   full gate results from the coordinator into §6, including failures, skipped/blocked checks and
   exact command/runtime. Incorporate the dedicated frontend audit's per-file verdicts into §4
   and its actionable findings into §7. Before any feature edit, keep its exact file/function/test
   step written here. Gate failures can be preserved in a named `wip:` checkpoint; never call them green.
2. Recheck `git status --short --untracked-files=all`, `git diff`, `git diff --cached`,
   `git rev-parse HEAD` and `git branch --list task/0.8-ranking-ui`. Expect current `c924410` and an
   empty index. If another agent changed them, reconcile first. If the target is absent, run
   `git switch -c task/0.8-ranking-ui c924410` to carry the existing dirty files onto the recovery branch.
   If it already exists, inspect its tip and relationship before switching; do not overwrite it.
3. Once the audit confirms the frontend is coherent enough to preserve, explicitly stage the
   **30 paths below only** (22 workflow/source paths plus eight frontend paths). Record any justified
   allowlist adjustment here before doing it. Do not use `git add .`, `git add -A`, or `git commit -am`:
   screenshots must stay out. Preserve the eight `docs/v2` copies and both nested repos outside staging.

```powershell
git add -- ".github/PULL_REQUEST_TEMPLATE.md" `
  "AGENTS.md" `
  "CLAUDE.md" `
  "analysis/AI_TASK_BRIEF.md" `
  "analysis/ANALYSIS.md" `
  "analysis/DEPLOYMENT_SECURITY_LEGAL.md" `
  "analysis/DESIGN_agentic_search.md" `
  "analysis/README.md" `
  "analysis/SPEC_matching_v2.md" `
  "analysis/TWO_AGENT_WORKFLOW.md" `
  "analysis/agents/AGENTS.md" `
  "analysis/agents/CLAUDE.md" `
  "analysis/agents/HANDOFF.md" `
  "analysis/agents/KICKOFF_PROMPTS.md" `
  "analysis/agents/PULL_REQUEST_TEMPLATE.md" `
  "analysis/agents/handoff_check.py" `
  "analysis/reference/ranking_v2.py" `
  "analysis/scripts/01_discovery_sensitivity.py" `
  "analysis/scripts/02_score_components.py" `
  "analysis/scripts/03_climate_sensitivity.py" `
  "docs/process/HANDOFF.md" `
  "scripts/handoff_check.py" `
  "frontend/src/api/client.ts" `
  "frontend/src/components/ResultDetail.tsx" `
  "frontend/src/lib/format.ts" `
  "frontend/src/lib/store.tsx" `
  "frontend/src/screens/PreferencesScreen.tsx" `
  "frontend/src/screens/ShortlistScreen.test.tsx" `
  "frontend/src/screens/ShortlistScreen.tsx" `
  "frontend/src/types.ts"
git diff --cached --name-status
git diff --cached --stat
git diff --cached --check
```

4. Confirm that the staged list exactly matches the allowlist and contains no screenshots, nested
   repository entries, data, credentials or unrelated files. Update §4–§6 with the actual audit and
   baseline. Create a recovery commit whose subject records the remaining failure if any, e.g.
   `wip: [0.8] preserve ranking ui and relay sources (recovered from cut-off)`, and body lists the
   actual red/blocked gates plus inherited I4/T3 acceptance blocker; trailer `Agent: gpt-6-astra`.
   No snapshot hash can be written before the commit exists; record the real hash in the next baton update.
   If coherence is not established, preserve the working files and document the exact issue; this
   writer has no stash authorization and does not execute prompt C's stash alternative.
5. Push **the task branch only**:
   `git push -u origin task/0.8-ranking-ui`. Verify `git rev-parse HEAD` against
   `git ls-remote --heads origin task/0.8-ranking-ui`. Record the actual snapshot hash and push result
   in §3/§11. If push fails, retain `Holder: nobody` and record the failure; never fall back to pushing main.
6. Only after the preserving checkpoint is pushed, take the baton: set §1 Holder to `gpt-6-astra`,
   actual since UTC, task branch and then-current HEAD; append §11. Stage **only**
   `docs/process/HANDOFF.md`, commit `handoff: gpt-6-astra takes the baton at [0.8]`
   with `Agent: gpt-6-astra`, and push the task branch. Verify remote tip again. In the committed
   HANDOFF, "HEAD when written" describes the predecessor HEAD; report the baton commit hash afterward
   rather than attempting a self-referential hash.
7. With the baton acquired, fix independent [0.8] frontend failures identified by the audit/gates:
   write the exact file, function and validating test here first, then edit those scoped frontend files,
   rerun affected checks and required gates, checkpoint and push. Main supplies the concrete findings;
   no invented frontend verdicts or preemptive formula/test changes. The inherited I4/T3 issue does not
   prevent independent UI recovery, but blocks acceptance/review claims until the owner resolves it.
8. Before `ready-for-review`, complete [0.8] acceptance (including `journey.spec.ts`), account for
   predecessor review and resolve §7's requirement contradiction explicitly. Use real gate output
   in the PR. Next task remains [1.1] only after the normal review/merge handoff.

## 6. Gate status at last run (numbers, not adjectives)

Run by claude-opus-5 on 2026-09-06 UTC, on the dirty recovery tree at `c924410` (interpreter
`backend/.venv/Scripts/python.exe`, which works — see the correction in §9).

| Gate | Result | Command / note |
|---|---|---|
| `ruff check app tests` | **pass** — "All checks passed!" | exit 0 |
| `ruff format --check app tests` | **pass** — 118 files already formatted | exit 0 |
| `mypy app tests` | **pass** — no issues in 118 source files | exit 0 |
| `pytest --cov=app --cov-fail-under=92` | **pass** — **891 passed**, coverage **92.56 %**, 677 s | SQLite only; PostgreSQL run not performed here |
| frontend `tsc --noEmit` | **pass** | exit 0 |
| frontend `eslint src e2e` | **pass** | exit 0 |
| frontend `vitest run` | **RED — 140 passed, 1 failed** | `ShortlistScreen.test.tsx > shows the match, what is confirmed, and the bucket`: ambiguous `getByText('Plausible')`, see §4 |
| frontend `vite build` | **pass** — 308.32 kB js / 63.99 kB css, 2.96 s | exit 0 |
| e2e `journey.spec.ts` | **not run** | required for [0.8] acceptance; ports 5173/8099 must be free |
| `seed_demo.py` order (brief §5.7) | **pass** — Groningen #1 (0.795, PLAUSIBLE), UBC #11 **OUT_OF_BUDGET** (0.401), 20 rows | `UNIMATCH_DEMO_MODE=true UNIMATCH_ENABLE_BROWSER_TIER=false`, after `alembic upgrade head` |
| alembic chain | **pass** — 9 revisions, single head `a4d1c7e58b92`; upgrade from empty DB succeeded | run during the seed gate |
| `pip-audit` / `npm audit` | **not run** | no CI-parity claim |

Deviation from brief §5.7 to note, not a failure: TU Delft, Melbourne and EPFL are `EXCLUDED`, not
ranked. Brief §5.4 rule 2 knocks out a **confirmed** hard filter, and the demo profile's IELTS writing
6.0 fails a published 6.5 per-band minimum at all three. The §5.7 table comes from
`analysis/reference/ranking_v2.py`, whose `_demo` never applied that rule. Spec beats reference sample.

## 7. Blockers / questions for the owner

- **Inherited I4/T3 contradiction, unresolved.** `analysis/AI_TASK_BRIEF.md` §4 I4 and §8 T3, and
  `analysis/SPEC_matching_v2.md` §10.1 T3 literally require known → UNKNOWN never to lower fit.
  The approved weighted geometric mean over known axes (brief §5 / spec §4.3), executable reference
  `analysis/reference/ranking_v2.py::aggregate`, and committed domain implementation do not guarantee it:
  equal weights, known values 0.25 and 1.0 yield fit 0.5 and coverage 1.0; changing the **1.0** axis to
  UNKNOWN leaves fit 0.25 and coverage 0.5. Thus coverage separation alone does not satisfy literal T3.
- The inherited test `backend/tests/test_ranking_v2.py::TestAggregation.test_an_unknown_axis_is_never_scored_as_a_failed_one`
  (identify by function name if its containing class changes) checks an unknown versus a mismatched
  climate, not literal monotonicity for every known-axis removal. The predecessor changed test semantics.
  `docs/adr/0003-noncompensatory-ranking.md`, Consequences around line 81 at `c924410`, expressly
  says dropping a known axis moves fit and substitutes "never scored against the row"; Alternatives
  also rejects mean imputation. This is an inherited documentary contradiction, not owner approval.
  No express owner resolution is present in the supplied conversation. Preserve brief, spec, reference,
  ADR and tests unchanged during recovery; ask the owner to resolve the requirement before acceptance.
- Prompt C preservation/checkpoint is authorized despite this conflict. It blocks predecessor/phase-0
  acceptance and review claims, not the preserving snapshot or independent [0.8] gate fixes.
- Detailed frontend defects and gate failures are **pending** from their owning agents. Do not fill
  in assumed failures or mark [0.8] ready-for-review before those results arrive.

## 8. Contract changes since the brief (append-only; the other agent reads this before coding)

| Date | Task | Change (path · field/signature) | Why |
|---|---|---|---|
| 2026-09-05 | setup | Brief §1 counts are stale: main now has **818** backend tests (not 785), **19** institutions in `institution_registry.json` (not 10), `domain/transcript.py`, i18n scaffolding in `frontend/src/lib/i18n.ts`, and `types.ts` grew. Anchors in the brief (`_stage_verify` L344, `_stage_assess` L722, `_update_result` L973, `ExplainableScore` L166, `UnresolvedQuestion` L96) are still correct. | keeps the brief honest without rewriting it |


| 2026-09-05 | [0.1] f23407f | `schemas/profile.py`: `PriorityGroup` six literals; `Preferences.priorities=[]` with uniqueness validation, `research_privacy="preferences_only"`; `ApplicantProfileIn.weights_override=False`; default priorities constant | Observed committed schema; not acceptance. |
| 2026-09-05 | [0.2] ea33051 | `domain/priorities.py`: priority/ROC axis weights module | Observed committed weighting source. |
| 2026-09-05 | [0.4] 3eefdcd | `domain/enums.py::Bucket`: WELL_PLACED, PLAUSIBLE, AMBITIOUS, OUT_OF_BUDGET, NEEDS_CLARIFICATION, EXCLUDED | Six committed portfolio categories. |
| 2026-09-05 | [0.4] 3eefdcd | `schemas/result.py::AxisScore`: axis/value/state/weight/reason/evidence_claim_ids; `RankingV2`: fit/coverage/sort_key/gamma/axes/unknown_axes/not_applicable_axes/knocked_out_by/bucket/bucket_reason/weights_source/version/disclaimer | Observed serialized ranking contract. |
| 2026-09-05 | [0.4] 3eefdcd | `ProgramResult.ranking`, `catalog_attributes`, `catalog_attributes_source`; `preference_score` retained | Stored attributes permit recalculation; v1 remains represented. |
| 2026-09-05 | [0.3] 0f46079 | `domain/ranking_v2.py` and `domain/scoring.py` changes | Geometric ranking and portfolio implementation; unresolved T3 semantics (§7). |
| 2026-09-05 | [0.5] 0b8d97f | `config.py::Settings.ranking_version=2`, `ranking_gamma=0.5` (`UNIMATCH_RANKING_VERSION`, `UNIMATCH_RANKING_GAMMA`) | Committed config defaults. |
| 2026-09-05 | [0.5] 0b8d97f | `ProgramResultRow.bucket`; migration `a4d1c7e58b92` from `e7c4a91b6f20`, adds non-null `program_results.bucket` string(40), server default empty, index `ix_results_bucket` | Observed ninth revision; do not rewrite an existing main migration. |
| 2026-09-05 | [0.6] e1d8078 | `pipeline/runner.py::apply_fit_labels`, `store_result`; `POST /api/runs/{run_id}/rerank` | Request priorities/preferences/funding/weights/gamma (0–2)/persist(false); response rows/gamma/weights_source; persisted audit action `results_reranked`. |
| 2026-09-05 | [0.6] e1d8078 | `GET /api/runs/{run_id}/results`: bucket filter, sort key/fit/coverage/gap/deadline (default key) | Observed list API additions. |
| 2026-09-05 | [0.6] e1d8078 | `GET /api/runs/{run_id}/shortlist`: chosen/notes/quotas; defaults size=10, min_well_placed=2, min_plausible=4, max_ambitious=3, max_per_country=3 | Observed balanced-list API; rejected rows omitted. |
| 2026-09-05 | recovery | Historical setup row above is retained append-only, not revalidated as current test counts/line anchors; [0.8] frontend contracts are uncommitted and under separate audit | Keeps history without upgrading old claims to acceptance. |

## 9. Traps and lessons (things that cost a session; keep them)

- `seed_demo.py` raises `SchemaOutOfDate` until `UNIMATCH_DEMO_MODE=true alembic upgrade head` has run.
- `Fetcher(...)` takes `(cache_dir, *, delay_seconds, respect_robots, offline, cache_ttl_seconds, timeout, contact, corpus_dir)`; it has no `close()`, only `__aexit__`.
- `backend/setup.sh` needs `uv`; plain `python -m venv` + `pip install -r requirements-dev.txt` works. Without Playwright installed, run with `UNIMATCH_ENABLE_BROWSER_TIER=false`.
- E2E uses fixed ports 5173/8099 with `reuseExistingServer: true` — never two e2e runs on one machine.
- Long-lived branches exist and are **not** part of this work: `claude/payments-phase-2` (74 commits ahead, conflicts with main in 12 files, adds 2 migrations off `c3a1f4e9b2d7` → merging it later will need one Alembic re-point), `social/community` (3 commits, merges clean, adds migration `f2a8c17d9e04`), `claude/production-completion` (Aug 30, superseded by main). Do not rebase them, do not branch from them.
- `README.md` still says "547 tests"; `docs/CURRENT_STATE.md` says 818. Trust pytest, not prose.
- Git author on recent commits is the owner's name for both agents — the `Agent:` trailer is the only reliable authorship signal. Always add it.


- Recovery environment: the repository `backend/.venv` launcher refers to missing base Python
  `C:\Users\Dias\AppData\Roaming\uv\python\cpython-3.12.14-windows-x86_64-none`
  (base-missing diagnosis supplied by coordinator; path read from `pyvenv.cfg`). Do not equate a launcher
  failure with a code/test failure. Record the coordinator's working interpreter and dependency setup
  in §6; do not silently repair global runtime/configuration in this documentation-only task.
- The first plain-runtime `scripts/handoff_check.py` call failed with `UnicodeEncodeError` under cp1251
  when printing an arrow. Coordinator verified `-X utf8` / `PYTHONIOENCODING=utf-8` succeeds.
  Use `& <verified-python.exe> -X utf8 scripts/handoff_check.py` from repo root (or set process-local
  encoding); no script-source fix is needed.
- The check script warns to push unpushed work, but here **never push main**: use the predecessor
  recovery branch relationship in §5. Its zero exit code is diagnostic completion, not green gates.
- Screenshot changes predate [0.1] according to supplied recovery context. Do not attribute them to
  the cut-off, regenerate them during inventory, stage them via `-am`, or call them disposable.
- Nested `.claude/worktrees/payments-phase-1` and `social-module` are independent user checkouts.
  Parent-repository "untracked" output does not authorize operations inside them.
- Seven `docs/v2` copies match `analysis` byte-for-byte; the brief has a different relative reference
  command. Keep these copies outside the snapshot unless a concrete reference need is documented.
- The legacy branch-ahead/conflict counts and line anchors above are historical template observations;
  this writer did not refresh those unrelated branches.

## 10. Queue (brief §6 order; do not reorder without the owner)

**Now: finish recovery and [0.8], not restart [0.1].** [0.1]–[0.7] have local implementation history
listed in §3, with acceptance/review outstanding and inherited I4/T3 blocker in §7.
After [0.8] and its predecessor acceptance/review obligations:

`[0.8]` → `[1.1]` → `[1.2]` → `[1.3]` → `[1.4]` → `[2.1]` → `[2.2]` → `[2.3]` → `[3.1]` → `[3.2]` → `[4.1]` → `[4.2]` → `[5]`

## 11. Session log (one line per session, newest last)

| Session (UTC) | Agent | From → to | Summary |
|---|---|---|---|
| 2026-09-05 | owner | `627d42d` → `627d42d` | workflow files created; no brief task started yet (historical template entry) |
| 2026-09-05 18:31:27 UTC | gpt-6-astra, delegated recovery inventory writer | `c924410` → `c924410` (HEAD unchanged) | Prompt C audit started using clock tool UTC; reconciled stale template, seven local predecessor commits and all 74 scoped dirty/untracked file paths; 2 nested repos excluded. HANDOFF only edited; gates/frontend review pending; branch/checkpoint/push/baton not yet performed. |
