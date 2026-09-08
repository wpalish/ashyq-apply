# T38 A1 — Developer report

- STATUS: IMPLEMENTED (docs only; candidate frozen, not pushed)
- CHECKED_SHA (start): 810bb0064f45045f5f657ac89e653d2e551e140f (branch ai/c3/t38/dev, worktree /Users/wpalish/ashyq-worktrees/c3-t38-dev, tree clean at start, confirmed)
- CANDIDATE_SHA: d4908ae6111d007903e45b550f82fdb975a3d92b (branch ai/c3/t38/dev, tree clean after commit)
- Commit: `docs: state the measured c2/c3 numbers in README, RELEASE_CHECKLIST and CURRENT_STATE (T38)` + trailer `Agent: ashyq-developer`

## CHANGED_FILES

- README.md (+32/-18 across 8 hunks)
- RELEASE_CHECKLIST.md (+27/-22 across 10 hunks)
- docs/CURRENT_STATE.md (+35/-0, one appended section)

`git diff 810bb00..HEAD --stat` = exactly these 3 files (94 insertions, 44 deletions). No code, no CI, no HANDOFF, no LIVE_DISCOVERY_REPORT.md, no DOCKER_VERIFICATION.md.

## WHAT WAS APPLIED (all 23 contract edits)

README (1-12): blockers blockquote → person-gate phrasing + 7/10 recall + green-since-2026-09-07; tree counts 1110→1402 (810bb00, 2026-09-08), 74→"76 Playwright specs … + 6 auth specs"; live-audit sentence but→and, 7 of 10 (T30 canary, 2026-09-08); commands comments 1110→1402, 93%→"94%; CI floor 92", 47 Vitest→182 unit, 50 Playwright→"75 passed + 1 intentional skip … e2e:auth adds 6"; verification table Backend tests / coverage / pip-audit / mypy / Frontend unit / E2E rows replaced with the c2-CI + c3-local(810bb00) values, ruff and FE typecheck/lint rows already equal "clean" (left byte-identical), axe/console/overflow/bundle rows kept BYTE-IDENTICAL, note "fix-plan-era measurements retained unchanged" added after that table; crash-recovery/migrations rows untouched; container row → run for real 2026-09-06 + DOCKER_VERIFICATION.md link; limitation 5 → 7 of 10 + registry nineteen + no claim about unlike sites.

RELEASE_CHECKLIST (13-22): CI paragraph → green since 2026-09-07 with the four run ids and the standing refresh/hotfix rule; gate 1 evidence + supersession pointer "(1358 on the c2 merge, 1402 at `810bb00`)"; gate 2 PARTIAL→PASS with the full new evidence incl. red history; gate 22 trailing "**WRITTEN, NOT RUN…**" sentence deleted, rest kept incl. "Earlier finding, kept:"; gate 28 → "Programme recall 7/10, category recall 26/30, 0 material false positives (T30 canary, 2026-09-08)"; gate 79 → "the registry's institutions (ten then, nineteen since gate 89)"; gate 89 appended "; superseded by the 2026-09-08 T30 canary: programme pages 7/10 (gate 28)"; summary re-counted (PASS 92, PARTIAL 2) + gate-2-back-to-PASS sentence appended to the summary paragraph; order item 5 → done strikethrough; order item 9 → "183 of 194 dictionary keys … only the shell and the community screens".

CURRENT_STATE (23): appended "## Update — after campaigns c2 and c3 (2026-09-08)" — supersedes note, c2 measured paragraph (1358/93.81% CI, runs 34115345524/34188244906/34188286259/34189211422; FE 182/75+1 skip/e2e:auth 6/6 labelled), c3 measured paragraph (LOCAL @ 810bb00, 1402/0 skipped, 94.04%, 166 files, FE not re-run — zero diffs, not a fresh pass), "### What is open" table with exactly the 9 contracted rows each with source (registry 19→60 PARTIAL / i18n 183 of 194 / lawyer gate 87 / live ApiPay gate 94 / deployment NOT DONE / T31 BLOCKED / T26 BLOCKED_SCOPE_CONTRACT / verify_compose.sh NOT_RUN owner-gate / T33-F1 owner decision). Nothing else in the file changed; all dated historical sections untouched.

## DEVIATIONS / INTERPRETATIONS

- No OLD-text mismatch was encountered; every quoted old string matched (multi-line blockquote/cell text matched across the file's existing hard wraps).
- README verification-table row "Frontend typecheck/lint → clean" was read as "both existing rows keep the value clean" (they already equalled it), not as merging the two rows into one — consistent with "Backend lint (ruff) → clean" likewise being a no-op member of the same list. Zero diff on those lines.
- The "after the table" note was placed directly after the first verification table (the one containing the kept axe/console/overflow/bundle rows), before the crash-recovery/migrations/container rows.
- CURRENT_STATE section body: the packet/planner fix the structure (heading, supersedes note, two measured paragraphs, 9-row table, each row with source) but not verbatim row text; rows were composed strictly from the verified sources below.

## SOURCES VERIFIED IN-TREE / IN-ARTIFACTS (numbers written are true)

- registry = 19 (re-counted from backend/app/adapters/discovery/institution_registry.json); 7/10, 26/30, 0 material FP, 1319.9 s from docs/LIVE_DISCOVERY_REPORT.md:10-14 + "Registry status" paragraph.
- i18n: re-counted frontend/src/lib/i18n.ts → EN 194 / RU 183 / KK 183 keys (11 untranslated per locale); readers of useTranslation = App.tsx (shell) + Discover/Feed/Messages/Moderation/Person screens (community) — "only the shell and the community screens" holds.
- e2e: 38 ordinary test cases × 2 projects (desktop-chromium 1440×900 + Pixel 7) = 76, auth-journey = 6 tests (frontend/e2e + playwright.config.ts).
- c3 LOCAL numbers (1402/0 skipped/94.04%/166 files/ruff+mypy clean, FE SKIPPED not PASS, verify_compose live NOT_RUN) from ai-team/outputs/c3-integration-a1/integrator.md (GATE_RESULTS a-g, COMBINED_SHA 810bb00).
- T31 BLOCKED (owner LLM provider/keys, no silent paid API), T26 BLOCKED_SCOPE_CONTRACT, T30 PARTIAL_VERIFIED from ai-team/ledger.json; T26 rationale from ai-team/outputs/c2-t26-a0/contract-audit.md; T33-F1 owner decision from ai-team/outputs/c3-t33-a1/reviews.md.

## GATES

- `cd /Users/wpalish/ashyq-worktrees/c3-t38-dev && python3 scripts/handoff_check.py` → exit 0 at baseline, with edits uncommitted, and after the commit (verdict notes are informational: branch has no upstream — push is forbidden for this role; pre-existing stash and unpushed local branches).
- `git diff 810bb00..HEAD --stat` → exactly README.md, RELEASE_CHECKLIST.md, docs/CURRENT_STATE.md.
- Self-run QA-method sweeps on the diff: added lines contain no «2 of 9», «1 of 10», «one institution in ten», present-tense «red since 2026-09-04» (only the contracted past tense "had been red"), «written, never run», «WRITTEN, NOT RUN», «1110», «547 passed», «47 Vitest», «50 Playwright», «74 Playwright», «184 of 378», «89%», «latest», «not yet pushed», «unpublished». Remaining old tokens sit only in contracted historical contexts (gate 1 "measured on `2be6b55`", gate 89 "2 of 9; superseded by …", CURRENT_STATE dated sections). No trailing whitespace introduced.

## MIGRATIONS

None (documentation only).

## REMAINING_RISKS

- Independent QA verification and review of candidate d4908ae have NOT run yet; this report claims implementation only.
- mypy "164 files (c2 CI)" is carried from the frozen contract's c2 CI record (not re-derived here); the 166 figure at `810bb00` is the integrator's real run.
- Historical sections in CURRENT_STATE still state older numbers ("1 of 10", "2 of 9", "184 of 378") by contract — the new section supersedes them explicitly.
