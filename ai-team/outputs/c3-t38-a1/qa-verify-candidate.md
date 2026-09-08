# T38 A1 — QA verification of candidate (VERIFY_CANDIDATE)

- ROLE: ashyq-qa, PHASE: VERIFY_CANDIDATE (independent invocation, campaign c3)
- STATUS: **VERIFIED_PASS**
- CHECKED_SHA: d4908ae6111d007903e45b550f82fdb975a3d92b (worktree /Users/wpalish/ashyq-worktrees/c3-t38-qa, branch ai/c3/t38/qa, tree clean, HEAD = frozen candidate, verified)
- BASE: 810bb0064f45045f5f657ac89e653d2e551e140f
- No files modified, nothing pushed.

## DIFF_HYGIENE — PASS

`git diff 810bb00..d4908ae --stat` = exactly README.md (50 lines changed), RELEASE_CHECKLIST.md (53), docs/CURRENT_STATE.md (35); 94 insertions, 44 deletions, 3 files. `--name-only` = exactly those three. `git status --porcelain` = 0 lines. No code, no CI, no HANDOFF, no LIVE_DISCOVERY_REPORT.md, no DOCKER_VERIFICATION.md.

## NUMBER_MAPPING_TABLE (every numeric token in ADDED lines)

Legend: LDR = docs/LIVE_DISCOVERY_REPORT.md; LEDGER = ai-team/ledger.json; INTEG = ai-team/outputs/c3-integration-a1/integrator.md; CODEx = ledger codex_audit_2026_09_07; RC = RELEASE_CHECKLIST.md; DV = docs/DOCKER_VERIFICATION.md.

| Token(s) | Source (verified by me) | Verdict |
|---|---|---|
| 7/10 (README x4, RC gate 28/89, CS) | LDR T30 combined row + "programme recall is 7/10"; ledger next_up "KPI canary complete at 7/10" | PASS |
| 26/30 | LDR combined row "26/30"; ledger next_up | PASS |
| 0 material false positives | LDR combined "Material FP 0" | PASS |
| 1319.9 s (638.3/681.6 not used in docs) | LDR combined "1,319.9 s" | PASS |
| 10 institutions ("Ten official domains" pre-existing) | LDR combined batch count | PASS |
| 1358 (README table, RC gate 1/2, CS) | LEDGER campaign_c2_progress "LOCAL: 1358 pytest passed" | PASS (see nuance N1) |
| 93.81% (x3) | LEDGER "cov 93.81% (threshold 92)"; INTEG gate c "baseline 93.81%" | PASS (N1) |
| 182 vitest (x4) | LEDGER "vitest 182/build clean"; codex "Vitest 182/182" | PASS |
| 75 passed + 1 intentional skip (x4) | LEDGER "Playwright ordinary 75 passed + 1 intentional skip"; codex audit | PASS |
| 6/6 auth (x4) + "adds 6"/"6 auth specs" | LEDGER "auth 6/6"; my count: frontend/e2e/auth-journey.spec.ts = 6 tests | PASS |
| 76 Playwright specs (README tree) | MY COUNT: 38 ordinary test cases in 5 spec files (journey 16, accessibility 9, community 7, messages 3, profile-persistence 3) × 2 projects (desktop-chromium 1440×900, mobile Pixel 7, playwright.config.ts:24-26) = 76; consistent with 75+1 | PASS |
| 0 known vulnerabilities (2026-09-08) | LEDGER "pip-audit and npm audit --omit=dev found 0 known vulnerabilities"; codex "0 known vulnerabilities" | PASS |
| 36 advisories | carried unchanged from pre-edit README row ("36 advisories found and fixed at baseline") | PASS |
| run ids 34115345524 / 34188244906 / 34188286259 / 34189211422 | 34115345524: codex audit history "public release-gates run 34115345524 succeeded" (2026-09-07, main 7b1fce0); other three: LEDGER campaign_c2_progress GITHUB section "PR runs 34188244906 and 34188286259 all green; post-merge main run 34189211422 all green"; all four run ids appear nowhere else in artifacts — mapping exact | PASS |
| 1402 / 0 skipped (x6) | INTEG gate c "1402 passed, 0 skipped" at COMBINED_SHA 810bb00 | PASS |
| 94.04% (x3) + README comment "94%" | INTEG gate c "coverage 94.04% ≥ 92" | PASS |
| 810bb00 (x10) | INTEG COMBINED_SHA | PASS |
| 166 files (x2) | INTEG gates a+b ("166 files already formatted" / "166 source files") | PASS |
| 164 files (c2 CI) | LEDGER "mypy 0/164" | PASS |
| 2026-09-07 "green since" | planner frozen contract assertion + run 34115345524 (2026-09-07 green) + 34189211422 | PASS (see N2) |
| 2026-09-04 red (past tense only) | pre-existing RC text + CS:416 "failed on every push since 2026-09-04" | PASS |
| registry nineteen / 19 (x4, incl. "19→60") | MY COUNT: institution_registry.json is a JSON list of length 19; grep -c '"name":' = 19; LDR "still 19 entries"; "requested 19→60 expansion is not claimed"; ledger T30 PARTIAL_VERIFIED | PASS |
| i18n 183 of 194, 11 per locale (x3) | MY COUNT in frontend/src/lib/i18n.ts: EN block (l.40-289) = 194 unique keys; RU block (l.297-527) = 183; KK block (l.530-759) = 183; RU/KK keys ⊆ EN; missing = 11 per locale (identical key sets). Matches docs exactly | PASS |
| gates 87 PARTIAL / 92 PARTIAL / 94 BLOCKED | git show 810bb00:RELEASE_CHECKLIST.md rows verified unchanged by the diff | PASS |
| summary PASS 92 / PARTIAL 2 (RC + CS) | MY OWN RE-COUNT of the candidate file: 92 PASS, 2 PARTIAL (87, 92), 2 BLOCKED (29, 94 — one styled "BLOCKED — needs the owner"), total 96 rows; pre-edit count 91/3/2 — exactly gate 2 PARTIAL→PASS | PASS |
| 2026-09-06, migrations exited 0, 20 results, :8080, 4.89.0, 29.7.2, WSL2 (README container row, RC gate 22) | DV header + body (20 results at awaiting_user_decision, postgres/api/web healthy, migrate exited 0) | PASS |
| gate 1 historical 1110+164+74+6, 240+39+42, 14/65/50/21/8, "measured on 2be6b55" | carried byte-identical pre-existing row text inside explicit historical marker + supersession pointer appended | PASS |
| gate 89 historical "2 of 9", 52 seeds, nine | carried pre-existing text + supersession pointer appended | PASS |
| 1440×900, Pixel 7 | playwright.config.ts:25-26 | PASS |
| five tasks T33/T34/T35/T36/T37 | INTEG input table (5 candidates) | PASS |
| T30 PARTIAL_VERIFIED, T31 BLOCKED ("no silent paid API"), T26 BLOCKED_SCOPE_CONTRACT | LEDGER tasks + campaign_c2.blocked + next_up | PASS |
| verify_compose NOT_RUN | INTEG gate g "Live run NOT_RUN ... NOT_RUN is not PASS" | PASS |
| T33-F1 owner decision | INTEG BLOCKERS item 3; outputs/c3-t33-a1/reviews.md exists | PASS |
| deployment NOT DONE | LEDGER publication "Application infrastructure deployment NOT DONE"; RC "Needs the user" | PASS |

No un sourced numeric token found in any added line. Dates 2026-09-08/09-07/09-06/09-04 all map to the same sources as their sentences.

## STALE_TOKEN_SWEEP (working tree, all three files)

| Token | Hits | Context | Verdict |
|---|---|---|---|
| "2 of 9" | RC:153 (gate 89), CS:330, CS:426 | gate 89 has explicit supersession pointer "(...superseded by the 2026-09-08 T30 canary: programme pages 7/10 (gate 28))"; CS hits are inside the closed fix-plan phase/`2be6b55` history that the new 2026-09-08 section explicitly supersedes ("supersedes the 'Still open' lists above") | acceptable |
| "1 of 10" | CS:128, 165, 202, 252 | inside "Update — Phase N of the audit fix plan" narrative sections of the finished plan; protected by the frozen contract ("датированные исторические секции НЕ трогать"); superseded by the appended section | acceptable (noted: phase headers carry no internal date — see N3) |
| "one institution in ten" | 0 | — | clean |
| "red since 2026-09-04" present tense | RC:17 only, as "had been red since 2026-09-04" (past tense, "was fixed before that merge"); RC summary retains pre-existing "has been red ... since 2026-09-04" inside the PASS→PARTIAL→PASS history narrative immediately followed by "moved back to PASS at the c2 merge" | acceptable |
| "written, never run" / "WRITTEN, NOT RUN" | 0 | — | clean |
| "1110" | RC:33 (gate 1, "measured on `2be6b55`" + supersession pointer), CS:404 (table pinned "On `2be6b55`, which is `main`") | acceptable |
| "547 passed", "47 Vitest", "50 Playwright", "74 Playwright", "184 of 378", "89%" | 0 | — | clean |

## WORDING_STABILITY — PASS

grep added lines for "latest" / "not yet pushed" / "unpublished" → 0 hits (case-insensitive). No trailing whitespace introduced in added lines.

## HANDOFF_CHECK — PASS

`python3 scripts/handoff_check.py` in the QA worktree → exit 0. Output: branch ai/c3/t38/qa, HEAD d4908ae (candidate), working tree clean; verdict notes informational only (no upstream for the QA branch — push is forbidden for this role anyway; pre-existing stash "pre-c2-main-sync-2026-09-08"; unpushed local campaign branches — expected).

## INTERPRETATION_RULINGS

1. Rows kept, not merged (ruff + FE typecheck/lint left byte-identical "clean"): ACCEPT. The contract said those rows "already equal clean"; merging them would be an uncontracted structural edit. Diff shows all three as untouched context lines.
2. Note placement (fix-plan-era note directly after the first verification table): ACCEPT. Pre-edit file already had a blank line between the "Production bundle" row and the "Crash recovery" row (verified via `git show 810bb00:README.md` — the table was already split there); the note was inserted into that pre-existing gap. No table structure changed.
3. CURRENT_STATE row composition from sources: ACCEPT. The packet/planner fix structure, not verbatim text; I verified each of the 9 rows against its cited source (see mapping table) — registry 19/19→60, i18n 183/194 + 11/locale, gate 87/94, deployment, T31, T26, verify_compose NOT_RUN, T33-F1. No row asserts anything its source does not support; NOT_RUN is explicitly "not PASS".

## HONESTY CONSTRAINTS

- c3 numbers LOCAL+SHA+date: satisfied everywhere they are measurement claims (README tree/commands "1402 tests (810bb00, 2026-09-08)", table "1402 ... (local, 2026-09-08)", "94.04% at `810bb00`", CS c3 paragraph "(local, at `810bb00`, 2026-09-08)"). Minor: bare command comments "94%", "182 unit tests", "75 passed + 1 intentional skip" carry no inline label — no CI claim is made there and the labelled forms sit in the adjacent table/sections; noted, not blocking.
- FE numbers as c2 measurements: satisfied — README FE row "frontend unchanged by c3 — zero frontend diffs at `810bb00`"; CS "the frontend numbers above stay the c2 measurements — a reason to expect they hold, not a fresh pass"; integrator gate f confirms FE SKIPPED (0 diffs), never claimed PASS.
- verify_compose live NOT_RUN, never PASS: satisfied (CS row verbatim "NOT_RUN is not PASS"; README container row claims only the 2026-09-06 DOCKER_VERIFICATION run, which itself says the shell script was inspected, not used).
- "green since 2026-09-07" phrasing: present in 4 places, each tied to evidence run ids; matches the planner's frozen assertion.

## NOTES / NON-BLOCKING NUANCES

- N1: The ledger records 1358 / 93.81% under "LOCAL:" and asserts the GitHub runs merely "all green" (no CI-side count captured in any offline artifact). The docs' "1358 passed in CI on the merge commit / on both databases" is an attribution of the locally-measured count to the green CI runs of the same content. Supported by: PR #8 merged exactly origin/ai/c2/integration@e4f5ee3 to main@04a3058 (ledger publication), and ci.yml runs the full pytest on a sqlite+postgresql matrix. Per the frozen contract's ONE-source framing this is acceptable; recorded so a reviewer can see the inference.
- N2: "green since 2026-09-07" is asserted by the frozen planner contract and backed by runs 34115345524 (2026-09-07) and 34189211422 (2026-09-08); GitHub-side history between those runs (e.g. any post-PR-#7 main run) is not evidenced in offline artifacts — accepted on the planner's frozen verified fact, not re-derivable offline.
- N3: CURRENT_STATE Phase 1–6 sections contain "1 of 10"/"2 of 9" without internal date pins; they are phase-pinned history of the finished fix plan, explicitly left untouched by the contract and superseded by the new dated section.

## BLOCKERS

None.

## NEXT_ACTION

Proceed to reviewer (and security if the dispatcher schedules one) on the same frozen candidate SHA d4908ae6111d007903e45b550f82fdb975a3d92b. QA does not grant merge approval.
