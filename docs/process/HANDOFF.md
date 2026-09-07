# HANDOFF — the baton

One file, always current, committed with the code. The agent who holds the baton keeps it true.
Rules for using it: `AGENTS.md`. Task definitions: `analysis/AI_TASK_BRIEF.md` §6.
Write for a reader who has **zero** chat history — because that is exactly who reads it.

## 1. Baton

| | |
|---|---|
| Holder | **nobody** |
| Since (UTC) | released 2026-09-07 14:10:54 UTC |
| Branch | `ai/c1/integration`, local-only; synchronized by merge with `origin/main@7b1fce0` |
| HEAD when written | `96c1082` (final publication handoff commit follows) |
| Origin main when checked | `7b1fce0`; campaign published as GitHub PR #7, not merged into main |
| Previous holder | gpt-6-astra on the now-merged shortlist fix; a separate ZCode/GLM campaign then produced five local task candidates without updating this baton |
| Sections 3 and 4 below | Historical: they describe the `[0.8]` recovery and are kept as a record, not as current dirty state. Read §2 and §5 for where things actually stand. |

## 2. Current task

**GLM campaign `c1` audit and release hardening — ready for review in GitHub PR #7.** The campaign
integrated T01, T04, T09, T10 and a deliberately limited T18 slice: five of the 24 task cards, not the
whole project. `25f5954` merged current `origin/main`; the original GLM candidate is preserved at
`audit/glm-c1-e533d62`. The audit fixed stale payment journal writes (`7f364cf`), Kazakhstan academic
domain handling (`135138a`) and wrong-level/subject live programme selection (`02d648c`).

All local gates now pass: backend 1153 tests / 93.00% coverage plus Ruff/format/mypy; frontend 182
unit tests plus typecheck/lint/build; ordinary E2E 75 passed/1 skipped; auth E2E 6/6; production
dependency audits report zero known vulnerabilities. A bounded NU live canary improved from 0 to 1
claim after the selection fix, with zero false positives, but remains at 0% verification completeness
because the plain fetch sees only a 42-character admissions shell. Provider-backed search/LLM,
browser-tier hardening, most of the 24-task backlog, publication and deployment remain unfinished.
The owner subsequently authorized publishing everything to GitHub. `origin/ai/c1/integration` and
PR #7 now contain the code, full evidence bundle and corrected audit. GitHub release-gates were in
progress when this handoff was written. Protected-main merge and application deployment remain
separate operations.
Status vocabulary: `not-started` · `in-progress` · `blocked` · `ready-for-review (PR #)` · `merged`.

## 3. Done in this task (commit hash per item — a claim without a hash is not done)

The original recovery entries below are historical provenance. Preserve their hashes and ancestry;
the first seven predate `AGENTS.md` and lack the required `Agent:` trailer, so do not rewrite them to
manufacture compliant history. [0.4] was committed before [0.3].

| Task mapping | Existing hash | Observed change |
|---|---|---|
| [0.1] | `f23407f` | Profile priorities, privacy field and weights override; profile tests. |
| [0.2] | `ea33051` | Priority/ROC weights module and ranking tests. |
| [0.4] | `3eefdcd` | Bucket enum and ranking/result schemas. |
| [0.3] | `0f46079` | Ranking v2 domain implementation, scoring changes and tests; inherited T3 issue (§7). |
| [0.5] | `0b8d97f` | Assessment from stored attributes, ranking config, bucket model/migration and pipeline tests. |
| [0.6] | `e1d8078` | Rerank, result sorting/filtering and balanced shortlist API; pipeline helpers and API tests. |
| [0.7] | `c924410` | Profile-field documentation and ADR 0003; ADR changes I4 interpretation without recorded owner resolution. |
| [0.8] recovery | `61df0db` | Preserving checkpoint: eight frontend files + relay sources, one red test named in the message. |
| [0.8] baton | `0bedc38` | Baton to claude-opus-5; §1/§2/§4/§5/§6/§11 reconciled with the real tree and real gate numbers. |
| [0.8] | `2f2e484` | Bucket assertion scoped to its own cell; frontend unit suite 141/141. |
| [0.8] | `d675cfe` | `CONTRACT["Bucket"]` and `bucket` on `/api/vocabulary`; 892 backend tests. |
| [0.8] | `0affab6` | Preferences disclaimer restored, per-table captions, e2e helper opens the set-aside sections; 67 e2e passed. |
| [0.8] fix-forward | `c220095` | Re-applied the orphaned shortlist-width fix after PR #2 merged. |
| [0.8] handoff | `d6e59d5` | Published PR #6 and pointed §5 at review, then `[1.1]`. |
| [0.8] review fix | `4a7171c` | Merged current main, restored the independent Confirmed column, protected longest-chip geometry, regenerated screenshots, and passed current gates/re-review. |
| GLM c1 sync | `25f5954` | Merged `origin/main@7b1fce0` into the local campaign candidate without conflicts; original `e533d62` preserved as `audit/glm-c1-e533d62`. |
| T10 follow-up | `7f364cf` | PostgreSQL regression proved a stale payment poll committed a provider journal entry; `worker.py` now turns a failed fenced retry transition into `LeaseLost`, rolling back the whole payment transaction. |
| T18 Kazakhstan domains | `135138a` | Treats `edu.kz` as a multipart public suffix, so `admissions.nu.edu.kz` belongs to `nu.edu.kz`; regression test included. |
| T18 live programme fit | `02d648c` | Fetched programme pages must match the applicant's level and subject; prevents MSc/unrelated BSc leads consuming the verification limit ahead of BSc Computer Science. |

## 4. Half-done / uncommitted at the moment of writing

### Prompt C recovery audit — gpt-6-astra, 2026-09-06 10:54 UTC

At `fix/shortlist-columns@d6e59d5`, before this session changed anything, `git status`, `git diff`,
and `git diff --cached` were all empty. Therefore the current recovery set contained **zero files**
to classify as finished, half-finished, or junk; no `wip:` checkpoint and no stash were warranted.
After `git fetch --all --prune`, `origin/main` advanced from `2be6b55` to `85352b5` through PRs #4/#5.
The resulting PR conflict was only this shared handoff file. It is being resolved with a normal merge
(no rebase/force), preserving both histories; the other staged paths are the exact `origin/main`
merge input, not abandoned cut-off work.

### Historical `[0.8]` recovery audit

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

1. Wait for and inspect all release-gates on https://github.com/wpalish/ashyq-apply/pull/7.
2. Owner reviews PR #7 and chooses whether to merge it into protected `main`.
3. For real live research, choose a search provider and optional LLM provider, provision their secrets
   outside Git, then implement T16/T25 and the remaining T18 dependencies before calling it release-ready.
4. Do not merge protected main, deploy, buy a provider, add secrets or touch production data implicitly.

## 6. Gate status at last run (numbers, not adjectives)

Run by codex, 2026-09-07, on `ai/c1/integration@02d648c`, which includes
`origin/main@7b1fce0` and the audited GLM campaign. Python gates used the worktree's Python 3.12 venv.

| Gate | Result |
|---|---|
| `ruff check app tests` | **pass** |
| `ruff format --check app tests` | **pass** — 154 files |
| `mypy app tests` | **pass** — 154 source files |
| `pytest --cov=app --cov-fail-under=92` | **pass** — **1153 passed**, coverage **93.00%** |
| frontend `tsc --noEmit` / `eslint src e2e` | **pass** |
| frontend `vitest run` | **pass** — **182 passed** / 20 files |
| frontend `vite build` | **pass** |
| frontend `playwright test` | **pass** — **75 passed, 1 skipped**; generated screenshot diffs restored |
| frontend auth Playwright | **pass** — **6 passed**; generated auth screenshot diffs restored |
| `alembic heads` | **pass** — sole head `e7c1a4d90b52` |
| `pip-audit -r requirements.txt` | **pass** — 39 production dependencies, 0 known vulnerabilities |
| `npm audit --omit=dev` | **pass** — 0 vulnerabilities at every severity |
| bounded live canary, NU, browser off | **partial** — reached; 26/0 pages ok/fail; exact BSc CS; 1 claim; 0 false positives; 0% completeness |
| migrations + `seed_demo.py`, browser off | **pass** — sole head applied; Groningen #1, UBC `OUT_OF_BUDGET` |

The React unit suite still emits pre-existing `act(...)` warnings in payment tests; it has zero test
failures. The e2e suite's crowded-default-database trap remains documented in §9; these runs avoided
it with explicitly isolated SQLite databases rather than changing user data.

## 7. Blockers / questions for the owner

### RESOLVED — I4 / T3 wording vs the approved formula (2026-09-06, owner-delegated)

The owner was shown the conflict and delegated the call ("делай так как считаешь правильным").
**Resolution: the formula stands as approved; T3's literal wording does not.** Recorded here so the
next agent does not reopen it.

- D1 (weighted geometric mean over known axes) and D2 (coverage separate, γ = 0.5) are final and were
  not reopened. The implementation matches `analysis/reference/ranking_v2.py::aggregate`.
- Literal T3 — "known → UNKNOWN never lowers fit" — cannot hold for **any** honest aggregation over
  known axes: fit is a mean, so removing an axis above the mean lowers it and removing one below it
  raises it. The only way to satisfy the literal wording is to impute unknown axes at or above the
  current mean, i.e. to score a university on data nobody verified. That is the one thing this product
  refuses to do, and imputation is rejected in `docs/adr/0003-noncompensatory-ranking.md`.
- The invariant that **is** true, and is what I4 exists to protect (brief P6): *an unverified axis is
  never scored against a row.* It leaves `fit` entirely and lowers `coverage` only, which
  `sort_key = fit · coverage^γ` then discounts. `test_an_unknown_axis_is_never_scored_as_a_failed_one`
  pins exactly that, and `test_an_unknown_axis_lowers_coverage_by_exactly_its_weight_share` pins the
  second half of T3 verbatim.
- Not changed: brief, spec, reference implementation, ADR, or any committed formula. The wording of
  I4/T3 in `analysis/AI_TASK_BRIEF.md` §4/§8 and `analysis/SPEC_matching_v2.md` §10.1 is now known to
  be stronger than the model it describes; leave the documents alone and read them through this note.

### Open

- **GLM completion claim is superseded.** Its code contribution is real and locally green, but only
  5/24 task cards were integrated. T18's declared T08/T13/T16/T17 dependencies are unmet; T25/T26 are
  backlog; live NU verification completeness is 0%; provider-backed search/LLM and deploy do not exist.
- **Evidence provenance is only partly machine-verifiable.** All five acceptance packets pass
  `check_team.py packet`, but that command checks shape/non-empty strings, not the identity of runtime
  agent IDs or the semantic authenticity of logs. Published `ai-team/` has 31 files with absolute
  `/Users/wpalish` paths; the owner explicitly accepted them as forensic evidence. No
  secret-like material was found by the audit scan.
- **Public deployment still needs a separate release-security pass.** Staging currently permits the
  console reset-mail sender, and browser egress hardening in the separate master-fix worktree has not
  been reconciled into this branch. Do not call the current candidate deployment-ready.

- **PR #6 recovery review (2026-09-06, gpt-6-astra + independent subagent): addressed locally.**
  P1: the first patch folded coverage into Match, removing the brief's independent Confirmed column
  and its screen-reader column semantics. The review fix restores a distinct `<th>/<td>` and uses an
  explicit ten-column width budget. P2: the original overlap had no regression assertion; the new
  Playwright check stresses the actual chip with `Well placed`, proves at 1440 px that its right edge
  stays before Decision, keeps the button group inside its cell, and rejects table overflow. P2: §3/§6 and the PR evidence
  were stale after PRs #4/#5; this recovery refreshes them on `origin/main@85352b5`. The findings were
  also posted to PR #6. Final independent re-review approved the corrected staged diff with no
  remaining direct-scope findings; refreshed GitHub CI remains before owner merge.
- **Resolved by PR #4:** `task/docker-stack-verification` itself remains stale, but all of its wanted
  content except the independently re-applied shortlist fix reached `main` through `docs/catch-up`.
  Do not rebase or merge that old branch; branch deletion is housekeeping for the owner.
- The `[0.1]`–`[0.7]` commits still carry no `Agent:` trailer (they predate `AGENTS.md`). Merged as
  they are; do not rewrite that history.

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
| 2026-09-06 | [0.8] | `/api/vocabulary` gains `bucket` (six values); `tests/test_frontend_contract.py::CONTRACT` gains `Bucket` → `types.ts` must keep the union in step | The contract test demands every contracted type be readable at runtime, so the UI never hard-codes a bucket string. |
| 2026-09-05 | recovery | Historical setup row above is retained append-only, not revalidated as current test counts/line anchors; [0.8] frontend contracts are uncommitted and under separate audit | Keeps history without upgrading old claims to acceptance. |
| 2026-09-07 | T10 audit | `worker.py`: failed fenced retry after a non-terminal payment poll raises `LeaseLost`; provider journal/order changes roll back with the transaction | A stale worker must commit no money-adjacent writes. |
| 2026-09-07 | T18 audit | `live_discovery.py`: `edu.kz` multipart suffix; `_confirm_programs(..., profile)` filters fetched pages by requested level and subject | Live NU run otherwise selected an MSc and Mathematics ahead of BSc Computer Science. |

## 9. Traps and lessons (things that cost a session; keep them)

- `seed_demo.py` raises `SchemaOutOfDate` until `UNIMATCH_DEMO_MODE=true alembic upgrade head` has run.
- `Fetcher(...)` takes `(cache_dir, *, delay_seconds, respect_robots, offline, cache_ttl_seconds, timeout, contact, corpus_dir)`; it has no `close()`, only `__aexit__`.
- `backend/setup.sh` needs `uv`; plain `python -m venv` + `pip install -r requirements-dev.txt` works. Without Playwright installed, run with `UNIMATCH_ENABLE_BROWSER_TIER=false`.
- E2E uses fixed ports 5173/8099 with `reuseExistingServer: true` — never two e2e runs on one machine.
- NU's normal admissions fetch currently yields only 42 readable characters and requires a safely
  hardened rendering/provider path for useful extraction. A `REACHED` canary is not a verified result;
  on 2026-09-07 it produced one programme-existence claim and 0% core completeness.
- Long-lived branches exist and are **not** part of this work: `claude/payments-phase-2` (74 commits ahead, conflicts with main in 12 files, adds 2 migrations off `c3a1f4e9b2d7` → merging it later will need one Alembic re-point), `social/community` (3 commits, merges clean, adds migration `f2a8c17d9e04`), `claude/production-completion` (Aug 30, superseded by main). Do not rebase them, do not branch from them.
- `README.md` still says "547 tests"; `docs/CURRENT_STATE.md` says 818. Trust pytest, not prose.
- Git author on recent commits is the owner's name for both agents — the `Agent:` trailer is the only reliable authorship signal. Always add it.


- `gh` is installed per-user via `winget install --id GitHub.cli --scope user`; it lands in
  `%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.cli_*in\gh.exe` and needs a new shell to be on
  PATH. `gh auth login --with-token` **rejects** the token Git Credential Manager stores, because it
  validates `read:org` which that token lacks; the same token works as `GH_TOKEN` for `gh api` / `gh pr`.
  Load it without ever printing it:
  `export GH_TOKEN=$(printf 'protocol=https
host=github.com

' | git credential fill | sed -n 's/^password=//p')`.
- **Corrected 2026-09-06:** the note below is wrong. `backend/.venv/Scripts/python.exe` runs fine and
  produced every number in §6. Keep the rest of the note only as a reminder to record the interpreter.
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

- **The demo database poisons the whole e2e suite once it grows, and it is not subtle.** On
  2026-09-06 a crowded `backend/data/unimatch.db` failed `journey.spec.ts` at its *first* assertion —
  "Who is applying" never renders, because the app restores the organisation's latest case instead of
  a blank profile — and that took five spec files' `beforeAll` down with it: `5 failed, 64 did not
  run`. Clean `main` reproduced it exactly, so it is nobody's regression. `rm backend/data/unimatch.db*`
  and re-run: the same suite is 73 passed / 1 skipped. Stop the API process first, or Windows refuses
  the delete with "Device or resource busy". Worth a real fix: restore should resolve a profile by the
  id this browser stored, never by "latest".
- `gh` is installed per-user via `winget install --id GitHub.cli --scope user`, landing in
  `%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.cli_*in\gh.exe`. `gh auth login --with-token`
  **rejects** the token Git Credential Manager stores (it validates `read:org`, which that token lacks);
  the same token works as `GH_TOKEN` for `gh api` / `gh pr`. Load it without printing it:
  `export GH_TOKEN=$(printf 'protocol=https
host=github.com

' | git credential fill | sed -n 's/^password=//p')`.
- The repository `backend/.venv` works; an earlier note claiming its base Python is missing was wrong.
- A commit pushed to a task branch *after* the owner merges its PR does not reach main. Check
  `git merge-base --is-ancestor <sha> origin/main` before assuming your last commit shipped — that is
  how `14d556b` was orphaned.
- **Corrected again 2026-09-06:** in this Codex recovery,
  `backend/.venv/Scripts/python.exe` again points at the absent uv-managed base interpreter and does
  not start. Gates use Python 3.12.14 from the bundled Codex runtime with process-local
  `PYTHONPATH=backend/.venv/Lib/site-packages`; Ruff's standalone `.venv/Scripts/ruff.exe` still works.
  This is an environment fact, not a product failure; do not rewrite or repair the user's venv during
  a task recovery.

## 10. Queue (brief §6 order; do not reorder without the owner)

**Now: GitHub review of PR #7 after all release-gates complete.** PR #6 is already merged on
`origin/main@7b1fce0`. The separate brief queue below remains the repository sequence; the GLM
24-card campaign did not replace it and is not fully completed.

`[0.8]` → `[1.1]` → `[1.2]` → `[1.3]` → `[1.4]` → `[2.1]` → `[2.2]` → `[2.3]` → `[3.1]` → `[3.2]` → `[4.1]` → `[4.2]` → `[5]`

## 11. Session log (one line per session, newest last)

| Session (UTC) | Agent | From → to | Summary |
|---|---|---|---|
| 2026-09-05 | owner | `627d42d` → `627d42d` | workflow files created; no brief task started yet (historical template entry) |
| 2026-09-05 18:31:27 UTC | gpt-6-astra, delegated recovery inventory writer | `c924410` → `c924410` (HEAD unchanged) | Prompt C audit started using clock tool UTC; reconciled stale template, seven local predecessor commits and all 74 scoped dirty/untracked file paths; 2 nested repos excluded. HANDOFF only edited; gates/frontend review pending; branch/checkpoint/push/baton not yet performed. |
| 2026-09-06 | claude-opus-5 | `c924410` → `61df0db` | Prompt C recovery: reconciled the stale §1/§5 (the branch existed, the baton did not), audited all eight frontend diffs into §4, ran every gate into §6 (backend green, 891 tests / 92.56 %; frontend one red unit test), preserved the work in one allow-listed `wip:` checkpoint, took the baton. |
| 2026-09-06 | claude-opus-5 | `61df0db` → `0affab6` | Finished [0.8]: red test fixed, bucket vocabulary contracted, preferences disclaimer restored, per-table captions, e2e helper opens the set-aside sections. All gates green (892 backend / 141 unit / 67 e2e). §7 I4-T3 conflict resolved by owner delegation. Next: open the PR. |
| 2026-09-06 | claude-opus-5 | `9ee7078` → `9ee7078` | Installed `gh`, authenticated it from the stored git credential, opened **PR #2** for stage 0. Baton stays with nobody; next is review. |
| 2026-09-06 | claude-opus-5 | `f88f77d` → `fix/shortlist-columns` | Prompt A. Found PR #2 and #3 merged, `[0.8]`'s last commit `14d556b` orphaned outside the merge, Codex's docker branch 40 commits behind main and unlogged, and the e2e suite red on clean main from the §9 database trap. Re-applied the three shortlist hunks on the new base; 164 unit and 73 e2e green. |
| 2026-09-06 16:59:45 UTC | gpt-6-astra | `d6e59d5` → `4a7171c` + this handoff commit | Prompt C completed: initial tree was clean; fetched PRs #4/#5, merged `origin/main@85352b5` without rewriting history, reviewed PR #6, fixed separate-column semantics and longest-chip overlap coverage, regenerated screenshots, ran full gates, recorded the review on the PR, and took the baton. |
| 2026-09-07 11:28:28 UTC | codex | `e533d62` → `25f5954` | Audited the local GLM campaign, independently reran backend/frontend and ordinary E2E, preserved the original candidate as `audit/glm-c1-e533d62`, merged current `origin/main@7b1fce0`, and opened a fix-forward for the stale payment-reconcile commit defect already noted by GLM security. No push/deploy. |
| 2026-09-07 12:00:10 UTC | codex | `25f5954` → `02d648c` + final handoff | Fixed and PostgreSQL-tested stale payment rollback, fixed two live NU discovery defects, ran all backend/frontend/E2E/auth/dependency gates, and field-ran the bounded NU canary. Audit verdict: useful partial campaign, not completed project. Baton released; no push/main/deploy. |
| 2026-09-07 14:10:54 UTC | codex | `ab2e70a` → `96c1082` + final publication handoff | Owner explicitly authorized GitHub publication. Secret-scanned and committed all 133 ai-team evidence files plus the corrected audit, pushed `ai/c1/integration`, and opened PR #7. Release-gates started; no protected-main merge or application deploy. |
