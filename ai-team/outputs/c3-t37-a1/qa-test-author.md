# T37 A1 — QA test-author report (ashyq-qa)

- ROLE_PHASE: ashyq-qa / TEST_AUTHOR (campaign c3, task T37, finding S7, attempt A1)
- STATUS: TESTS_READY (RED captured on baseline; existing suite green)
- CHECKED_SHA: edf546de9f998c0909337d0abe6f8e1c9c4a0be5 (verified `git rev-parse HEAD` before work; branch `ai/c3/t37/qa`; tree clean)
- COMMIT_SHA: 25af8ff2ac4e41a73d4eb493a29a14c11bf9b2a0 (only `backend/tests/test_pipeline.py`, +145 lines, 0 removed — pure append; trailer `Agent: ashyq-qa`; not pushed)

## Environment

- Worktree: /Users/wpalish/ashyq-worktrees/c3-t37-qa (QA-only; developer checkout untouched)
- Venv: /Users/wpalish/ashyq-worktrees/c3-t37-qa/backend/.venv (as provisioned; no extra pytest args)
- Storage: SQLite via the `session` fixture (tmp db); demo corpus; offline. No PostgreSQL/E2E involved, so no resource slot contention.
- Re-entry path proven real: captured runner log in the RED run shows `skipping profile_validation, already completed` and `skipping program_verification, already completed` — only funding_discovery + assessment re-ran after the stage_state reset (routes_research.py:429-439 pattern for `?stage=funding_discovery`). NOT recheck_stale, NOT full retry, so `_replace_evidence` never runs — the duplicate is not masked.

## Test

`backend/tests/test_pipeline.py`, appended `class TestFundingReEntry` (one method, five assertion groups):
`test_reentering_funding_duplicates_nothing_and_keeps_the_applicant`
- completed_run; per-result ClaimRow totals / SCHOLARSHIP_* sums / verify-family counts / ConflictRow counts snapshotted
- user_decision=approved, reason="shortlisted", notes="call the office", decided_at set on the Groningen row + its payload (routes_results.py:276-286 recipe, runner-level)
- one SUPERSEDED ClaimRow inserted on the Delft row (claim_type `scholarship_amount`, status column AND payload["status"]="SUPERSEDED"; pattern test_freshness_regressions.py:415-450). Chosen inside the funding claim family so the fix's required `status != SUPERSEDED` delete filter is actually pinned.
- stage_state funding_discovery+assessment -> "pending" exactly as routes_research.py:429-439; run.stage=queued; cancelled=False; fresh `ResearchRunner(...).run_to_decision()`

## RED results (baseline, real run)

Command: `cd backend && ./.venv/bin/python -m pytest tests/test_pipeline.py -k TestFundingReEntry` → PYTEST_EXIT=1, `1 failed, 31 deselected in 1.46s`

- (1) ClaimRow totals per result unchanged incl. SCHOLARSHIP_* sums → FAIL (RED, expected by contract).
  `AssertionError: re-entering funding_discovery changed the stored claim totals; Groningen 40 -> 58`
- (2) verify-family counts unchanged → PASS on baseline (guard vs blanket-replace regression)
- (3) user_decision/reason/notes/decided_at on row AND in payload → PASS on baseline
- (4) SUPERSEDED row alive (status column + payload["status"]) → PASS on baseline
- (5) ConflictRow counts per result unchanged → PASS on baseline. DEVIATION from the frozen contract ("baseline: (1) и (5) красные"): the bundled corpus's funding stage emits **zero** ConflictRows (only conflict in the corpus is Delft's verify-stage `ielts_min_overall`, untouched 1→1). The conflict-doubling mechanism is the same unclean append in `_update_result` (runner.py:1117-1120) — verified by code flow — but there is no funding conflict in the corpus to double. Honest classification: (5) is a guard, not RED. Flagging to planner; no assertion was weakened.

### Before/after per-result counts (baseline re-entry, probe run, exit 0)

| result | total before | total after | sch before | sch after | verify before | verify after | conflicts before | conflicts after |
|---|---|---|---|---|---|---|---|---|
| University of Vienna | 14 | 14 | 0 | 0 | 14 | 14 | 0 | 0 |
| Eindhoven University of Technology | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 |
| Delft University of Technology | 30 | 41 | 11 | 22 | 19 | 19 | 1 | 1 |
| University of Amsterdam | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 |
| National University of Singapore | 33 | 47 | 14 | 28 | 19 | 19 | 0 | 0 |
| University of British Columbia | 26 | 35 | 9 | 18 | 17 | 17 | 0 | 0 |
| Arizona State University | 29 | 38 | 9 | 18 | 20 | 20 | 0 | 0 |
| Technical University of Munich | 28 | 37 | 9 | 18 | 19 | 19 | 0 | 0 |
| University of Groningen | 40 | 58 | 18 | 36 | 22 | 22 | 0 | 0 |
| McGill University | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 |
| University of Tokyo | 27 | 37 | 10 | 20 | 17 | 17 | 0 | 0 |
| Trinity College Dublin | 23 | 30 | 7 | 14 | 16 | 16 | 0 | 0 |
| University of Oslo | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| University of Warsaw | 24 | 33 | 9 | 18 | 15 | 15 | 0 | 0 |
| Aalto University | 25 | 34 | 9 | 18 | 16 | 16 | 0 | 0 |
| EPFL | 27 | 36 | 9 | 18 | 18 | 18 | 0 | 0 |
| University of Toronto | 27 | 37 | 10 | 20 | 17 | 17 | 0 | 0 |
| KU Leuven | 32 | 48 | 16 | 32 | 16 | 16 | 0 | 0 |
| University of Melbourne | 26 | 34 | 8 | 16 | 18 | 18 | 0 | 0 |
| University of Edinburgh | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

14 of 20 results double their SCHOLARSHIP_* claims; verify-family unchanged everywhere; conflicts unchanged (no funding conflicts in corpus).

## GREEN results / suite health

`cd backend && ./.venv/bin/python -m pytest tests/test_pipeline.py` → PYTEST_EXIT=1 with `1 failed, 31 passed in 16.85s` (pre-format) and `1 failed, 31 passed in 16.50s` (post-format). The single failure is the new RED test; all 31 existing tests green. Ruff: `ruff check app tests` exit 0; `ruff format --check tests/test_pipeline.py` exit 0 (after formatting my appended block; initial check exited 1 and the fix touched only my added lines — diff remains append-only, verified 0 removed lines). mypy config is `files = app`, tests not type-checked.

## EXTRA_RUNS (evidence, not committed)

- Probe script: /Users/wpalish/ashyq-apply/ai-team/outputs/c3-t37-a1/probe_reentry.py (exit 0) — produced the count table and the per-assertion baseline classification (1 FAIL/FAIL, 2-5 PASS) on a second fresh scenario run.
- Diagnostic exit codes: probe exit 0 does NOT mean the bug is fixed — assertion (1) fails inside pytest (exit 1).

## BLOCKERS

None blocking TESTS_READY. Open item for planner/dispatcher: contract expectation "(5) красные on baseline" is not reproducible with the bundled corpus (no funding ConflictRows exist to double). If a red (5) is required, the corpus would have to gain a conflicting funding source — outside my allowed_paths (runner.py + test_pipeline.py only).

## NEXT_ACTION

Developer implements the fix per frozen contract in `backend/app/pipeline/runner.py` `_update_result` (extra_claims `is not None` branch: targeted delete of funding-family ClaimRows with `status != SUPERSEDED` + funding-family ConflictRows before re-store, plus module-level FUNDING_CLAIM_TYPES constant), branching from QA commit 25af8ff2ac4e41a73d4eb493a29a14c11bf9b2a0. Then VERIFY_CANDIDATE: this test must flip GREEN while (2)/(3)/(4) stay green and TestRetry/test_source_scan/test_freshness_regressions stay green.
