# Claude search relay — 7 October 2026

## Start here

Status: ready for review, baton released. Draft PR: https://github.com/wpalish/ashyq-apply/pull/61. Branch: `task/search-claude-relay`. Base: `1b2a554129f5744eb297848472f1c8fe8c7fde26` (main, PR #60 merged).
Local checkout: `/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply`.
This journal is committed/pushed so Claude can resume without this chat. Newest entries take precedence over older HANDOFF paragraphs.

## Authorization and session reviewed

Owner: “проанализируй сессию и продолжи его работу ... записывай в какой то файл”. Read-only native Claude session reviewed through computer use, no prompt sent and no model request made. Session ID `session_0142YLhoNdiGxNVtxJBDaNfX`, name “Привет”, branch `claude/greeting-16wj2z`.
Latest response: PR #60 merged; RL-1 in main; four open decisions: development-cohort extension, G-1 gold signature, free Exa capacity, Aalto/NTU Fly recheck. Earlier owner delegation is reported in the PR as “делай по своим рекомендациям”. The new continuation authorizes ordinary engineering decisions; it does not sign gold or authorize purchases.

## Confirmed starting state

- PR #59 and #60 are merged. Current main is `1b2a554`.
- Default rules: DF-1 and RL-1 on; TS-2/SR-2/SP-1 off after no measured gain. Check constants for exact implementation.
- Original fresh measurements are in `backend/evaluation/research/runs/2026-10-06/`; reviewed9 has 73 known labels.
- Control two-pass: reported 20/73 labels, 10/60 core. RL-1: reported 12/60 core, precision 1.0; this describes saved runs, not current general reliability.
- Heldout run 37554279823 timed out at 55 minutes. Claude reported 5/216 core, 7/9 programme misses and failed target 6. Completeness/denominator must be audited before treating this as a completed evaluation.
- `docs/process/HANDOFF.md` was stale: it still described draft8 and pending DL-2/BL-1. Updated active branch-specific entries; preserved history.
- Other local `task/expert-500-phase1` checkout has uncommitted funnel work. It was inspected only and not modified. No duplication of that work planned.
- Takeover script: clean tree, zero ahead/behind main, 19 migrations with sole head `d8e412c6a901`. Complete script output retained locally in `work/handoff-initial.log` (large historical HANDOFF included).

## Write-ahead plan

1. Archive current Fly status and repeat unchanged production Fetcher probe only for Aalto and NTU. No settings, secrets or deployment changes.
2. Download original heldout and RL-1 artifacts; audit completed/partial captures, core counts and budgets offline.
3. Fix a reproduced measuring-stick defect first if present. Do not tune rules on the nine heldout cases or touch the separate expert500 HELDOUT150.
4. Continue with a general discovery improvement on a disjoint development cohort, retaining 6/60/120 limits, truthful unknowns and existing Fetcher protections.
5. Run required source gates, push each green step, prepare a reviewable PR; owner merges.

## Decisions still pending

G-1/G-2 gold corrections are not applied. Paid Exa is not authorized. A free query cache requires inspection of the existing cache/budget/privacy semantics before proposing a change. Source availability must remain distinct from programme discovery or claim accuracy.

## Resume checkpoint

Next action: execute step 1, inspect the saved heldout artifact and add actual results below. No source edits made at takeover.

## Step 1 / step 2 findings (before source edits)

- Owner supplied fresh NTU DNS evidence on the same Fly machine: `socket.getaddrinfo` returned `104.16.4.14`; `nslookup` is unavailable. This does not itself prove a page read.
- Repeated production probe completed: NTU pages readable; Aalto robots unreachable. Raw output under `evidence/claude-relay/2026-10-07/`. Full details to be added after parsing.
- Downloaded original artifacts for heldout 37554279823 and RL-1 37545452839 into local work. Heldout has 35 capture files (36 planned); NU-off has only one repetition. All 18 on files exist, so the original nine-case on-arm measurement can still be examined separately.
- Reproduced measuring-stick defects by reading code and original telemetry: `cost()` rounds seconds before checking the cap (Masaryk 120.003–120.006 s becomes 120.0); null counters are treated as zero; `load_run()` silently merges an incomplete second repetition and `stable_changes()` can declare a gain from missing cases.
- Write-ahead: repair those scorecard behaviours with independent synthetic tests; preserve original artifacts, scorer decisions, corpus, production flags and heldout facts. Keep ordinary completed budget exhaustion as a measured outcome, distinguish it from an unfinished capture or an absent repetition.

## Step 3 write-ahead: disjoint development cohort

Choose five deterministic existing catalogue seed identities from the frozen DEV split, sorted by stable id and taking a distinct country each time: Dalian University of Technology, Nagoya University, University of Witwatersrand, AUT, Caltech. None is in the ten-case cohort, the nine curated heldout cases, or the expert500 HELDOUT150. This is an identity-only working set, not signed gold.

The live harness currently accepts only the curated 19, so extend its opt-in case selectors and canary diagnostics to select an existing imported seed identity. Do not add these to the production curated registry or import seed costs/admission hints as claims. Preserve the default ten-case run. Run the five-case baseline in strict mode before any rule tuning.

## Green checkpoint: scorecard repair and access audit

- Source tests: 15 scorecard tests pass (9 new). Ruff check/format and mypy 336 source files pass. Full backend: **3619 passed, 2 warnings, 94.86% coverage, 520.35 s**. Frontend: typecheck/lint/build pass, **232 tests** pass. No app/pipeline/ranking/schema/Fetcher or production defaults changed.
- RL-1 replay still has the same two stable gains and zero losses. All evidence and precise heldout audit are under `docs/process/evidence/claude-relay/2026-10-07/README.md`.
- G-1 now has a concrete unsigned proposal (6.0 overall / each component) and owner was asked asynchronously; no gold change is applied.
- Five-case development manifest prepared; no baseline yet. Before launching it, add opt-in catalogue identity selection and explicit global stop on any provider failure; current paired shell workflow alone is not safe for that requirement.

## Committed checkpoint / exact next step

Takeover: `96f0b14`. Green scorecard source + evidence: `0bc152226cb1aacf89e293a4dba82507e324abf6`. Current code is reviewable; original search algorithm defaults are unchanged.

The next source task is opt-in development-case support and a controlled five-case baseline. Implementation has **not started**. The manifest gives identity ids and source hashes. Required files: `backend/evaluation/research/live.py`, `backend/scripts/canary_discovery.py`, offline selector/controller tests. `live.py --case` currently permits only the curated 19 and canary selects only their registry entries. Use existing imported catalogue ids for the five seed identities, without declaring their hints verified or adding seed estimates to claims. Add explicit global batch stop on provider/auth/quota refusal before new live work; the paired shell workflow currently continues to the next command after a provider refusal. Preserve defaults and 6/60/120 budgets, obtain a baseline before any discovery rule, retain raw logs and actual attempted/remaining ids. Do not tune on the nine heldout cases or expert500 HELDOUT150.

After source PR review/merge, resume with:

```bash
git fetch origin --prune
git show origin/task/search-claude-relay:docs/process/CLAUDE_SEARCH_RELAY_2026-10-07.md
```

If using a different checkout, do not reset local changes. The private expert500 branch's dirty funnel work is a separate workstream. No fresh model, expert, provider search, or new university benchmark was launched in this relay step. No main merge or deployment was performed.

## Released checkpoint / PR #61

The bounded relay step is complete and pushed: measuring-stick repair, raw evidence audit, production access recheck and next development plan. The holder is now nobody. Review the Draft PR before merging; the owner merges. This is not a claim that the whole search product is finished.

A final additional CI-scope check (`app tests evaluation`) passed Ruff check, Ruff format (365 files) and mypy (365 source files). Local full backend3619 /94.86% and frontend232 remain the source gate results. At the time this journal was written, cloud release-gates on the PR were still running; read the PR check rollup for the eventual exact-head result. Future agents must not infer success from this pending entry.

To resume, fetch this branch and read this journal plus HANDOFF's newest branch-specific entries. First review/merge PR #61, then implement the opt-in catalogue seed-case harness and global provider-failure stop described above. The five-case baseline is still PREPARED_NOT_RUN. The G-1 signature question is pending; reviewed9 and historical scoring are unchanged.

## Owner continuation / two experts

Owner now says “продолжай работать ... на 2ух субагентах запустить экспертов на новые уники”. Main engineer continues on `task/search-development-baseline` explicitly branched from PR #61's checkpoint e3d77d4, without waiting for a main merge. PR #61 stays reviewable. Two collaboration experts have disjoint evidence-only assignments; their work is independent of the upcoming algorithm baseline but is not an OS-blinded experiment. All new live work shares one refusal stop sentinel. Source/ledger/selector changes and tests are declared in HANDOFF §5 before edits. Groningen remains unsigned.

## Permission interruption and restoration

After the two experts started, filesystem/network permissions changed to read-only/restricted. All new live/write work stopped. Expert A retained one successful Dalian Exa discovery (0 Fetcher reads,1 query,2737 tool ms); other four were not started. No facts from snippets accepted. Parent could not update files until permissions restored.

On owner restoring full access (7 October,16:07UTC), the parent resumed. Old child contexts still retained their read-only policy, so they completed without further I/O. Two fresh delegations resume the same disjoint assignments and existing ledger, without resetting Dalian's original15-minute guard or request counters. The other four per-case guards have not started. PR #61's exact e3d77d4 cloud check rollup was verified8/8SUCCESS before the interruption; no merge/deployment. Main source work remains the opt-in seed selector and fail-closed controlled batch declared in HANDOFF §5.

## Development harness verification in progress

Opt-in `--catalogue-id` now selects only imported identity/name/country/domain hints, never seed fact estimates or registry promotion. A shared STOP blocks source/search actions and each HTTP hop; first provider failure is sanitized and sticky. Parent batch preserves the planned, attempted and remaining ids, including a pre-start refusal with no observations; missing checkpoints stop as unmeasured. The ordinary curated selector and app defaults stay unchanged.

Targeted offline suite:53 passed. Ruff check/format367 and mypy366 passed. Frontend232 tests/typecheck/lint/build passed. The first full backend run was intentionally interrupted after request-hop stop protection was added; its original log is preserved, and a complete run on the final source is in progress. No new algorithm baseline has started yet.

Experts independently completed source reads for the five DEV identities. Dalian keeps all exact2027 questions unresolved because only2026/general sources were accessible; Nagoya distinguishes Japanese April Computer Science from October G30; AUT reports official403 access failures. These findings are still unsigned/unreviewed. All expert logs, counters and excerpts will be audited before comparison. No facts were inserted into gold or production.

Next frozen capture command uses existing keyed `exa`, six queries/60coldFetcher/120active seconds with3000ms finalization reserve inside that cap, browser off, robots respected, explicit prepared ids, the shared development-STOP.json and no experimental flags. Keyed Exa differs from Claude's historical exa_mcp captures; do not infer like-for-like provider comparisons. No purchase or retry after refusal is authorized.

## Offline gate environment isolation

Final full gate:3633 passed,1 failure,2 warnings,94.86%,436.43s. The only failure is the existing no-key Exa configuration test: the dedicated `.env` symlink introduced for live research makes a key present. Temporarily detach that ignored symlink only, preserve the original failure log, repeat full offline gate and restore before live work. Neither original configuration nor test assertions change. Required Ruff/format367/mypy366 and frontend232/typecheck/lint/build are green. Current demo executes, Groningen first; its current product classification output is not the old v2-table vocabulary from the brief.

Both experts have submitted all five cases, no unrun assignments and no provider refusal. Parent independently checked79original logs, body hashes, monotone exact counters and100verbatim source substrings, with0issues. This is integrity verification, not semantic gold acceptance.

## Green development source checkpoint

The complete clean-env gate on final source passed3635tests/2warnings/94.86%/449.26s. Focused54passed, Ruff/format367 and mypy366 clean; frontend232/typecheck/lint/build clean. The only earlier complete run's failure was the keyless configuration test seeing the dedicated dotenv symlink; no assertions weakened. Symlink restored, original untouched. One migrationhead d8e412c6a901. App tree5c4f52b7e00b15544c2324fc5b84cfd99ec2d4c0 remains equal to main.

All385archived expert files independently hash-verified. Original79actions and100exact verbatim substrings pass integrity checks; all semantic findings remain unreviewed. All5assignments attempted, no provider refusal. Final reporting regression distinguishes an absent checkpoint from provider refusal; source now has16new regressions. Next: freeze committed HEAD and source hashes, execute the prepared single5case strict baseline unchanged, retain source cache/metadata without synthetic profile DB rows, then record a supported loss review. No new university algorithm baseline has started before this checkpoint.

## Frozen five-case baseline and first supported error

Actual source89fc891228d9b8987fce19b2ddc0254d69837c2e,5/5terminal case outputs,75Fetcher/15Exaqueries,194452active checkpointms total. Every case stays within6/60/120000; no provider failure or shared STOP. Original captures/child logs/checkpoints, frozen launch manifest, source-cache hashes and metadata retained under search-development evidence. No synthetic profile DB rows archived. Programme URLs are candidate leads, not verified full-degree/intake claims.

Only emitted prediction: Nagoya IELTS5.5. Retained official language page has separate G30 and Exchange programs(NUPACE) sections;5.5 belongs to exchange. This is a confirmed population-transfer error, not a missing-year or access guess. Parent prioritizes a general section-scope repair before the Dalian title/recall hypothesis. Two experts re-engaged for offline independent review only, no new network. Scope filter must preserve genuine full-degree sibling evidence and tables; no page/acronym hardcode, cap/default/gold change.
