# T32 A1 — QA TEST_AUTHOR report

- ROLE_PHASE: TEST_AUTHOR
- STATUS: TESTS_READY
- Baseline verified: `git rev-parse HEAD` = `2ed4f51e1d5c1fae3f4cb36ad64982eb67184a2d`, branch `ai/c2/t32/qa`, tree clean before work.
- QA commit: `65e1522` (parent = baseline). No push. Only the two new test files were committed; no production edits, no edits to existing test files, no T29 files.

## FILES_CREATED

- `/Users/wpalish/ashyq-worktrees/c2-t32-qa/backend/tests/test_freshness_regressions.py` (R1-R4, R6, R8, apply_freshness pin)
- `/Users/wpalish/ashyq-worktrees/c2-t32-qa/backend/tests/test_source_scan.py` (R5, R7, source_scan skeleton C3, purge C4, two-PG-session races)

## RED_RESULTS (per scenario, on baseline 2ed4f51)

True baseline-bug REDs (assertion failures reproducing J01):

- **R1** `test_exactly_at_ttl_is_stale[admission_deadline|tuition]`, `test_ttl_plus_two_minutes_is_stale[...]`, `test_naive_accessed_at_agrees_with_aware[...]`, `test_apply_freshness_downgrades_at_the_boundary[...]` — `AssertionError: assert False is True`. Root cause pinned at `backend/app/domain/freshness.py:35` (`age_days(...) > max_age_days(...)`, whole-day floor). Plus `test_naive_now_does_not_crash_and_agrees_with_aware_now[...]` — TypeError on baseline (naive `now` reaches the aware-naive subtraction; C7 requires both operands normalized).
- **R2** `test_a_noop_recheck_leaves_a_new_queued_recheck_with_a_fresh_key` — `AssertionError: the no-op recheck must re-arm the chain ... assert []` (zero new queued jobs: recomputed key collides with the finished job's date-granular key, worker.py:193 / store.py:107-112 dedupe). Extends test_worker.py:490 without touching that file.
- **R2** `test_a_recheck_fired_at_the_deadline_rearms_strictly_into_the_future` — `AssertionError: re-armed into the past (run.next_recheck_at=2026-09-07T22:08:43.386163)` — the follow-up job's `available_at` is microseconds in the past relative to execution (earliest_recheck recomputes from the same immutable accessed_at).

Contract RED-pending (behavior does not exist yet; failure modes recorded):

- **R3** two no-op cycles — assertion (dies at cycle 1 with the R2 chain death; pins generation-key uniqueness post-fix).
- **R4** `test_the_enum_has_a_superseded_member` — `AttributeError: type object 'ClaimStatus' has no attribute 'SUPERSEDED'`; `test_apply_freshness_never_touches_superseded` — AttributeError (the pin the contract names); `test_a_superseded_value_does_not_conflict_with_its_successor` — `ValueError: 'SUPERSEDED' is not a valid ClaimStatus`.
- **R5** forced change: `assert 'dead' == 'succeeded'`, `last_error="unknown job kind 'reextract_page'"`; fenced attempt: `assert 'dead' == 'running'` (takeover mid-handler never happens on baseline).
- **C3 skeleton**: sitemap-lastmod/304/robots — `assert 'dead' == 'succeeded'` (baseline `last_error='run None no longer exists'` — source_scan is run-less and dispatch has no branch for it); double-bootstrap `assert 0 == 2`; lease-takeover race `assert 'dead' == 'running'`.
- **C4** purge — `ModuleNotFoundError: No module named 'app.jobs.source_scanner'`.
- **R7** refresh endpoint — `assert 404 == 402`; cross-tenant: `assert 'Not Found' == 'Research run not found'`; demo: `assert 404 == 409`; paid/no-op/double-click: `assert 404 == 202`.
- **R8** — `AssertionError: no migration with down_revision == 'b4e8a1c2f6d9': the T32 revision does not exist yet` (revision located dynamically by parent, so the developer's id choice is free).

## GREEN_RESULTS on baseline (justified; none is a masked RED)

- **R6** `test_the_demo_pipeline_payload_is_byte_identical_to_baseline` — GREEN by construction: golden sha256 `aae8c595ab8f78c8a03a87eddde03a811b8986e4725817d05c65059327e4d702` captured ON baseline 2ed4f51 from the demo corpus pipeline (conftest settings/profile fixtures; payloads `json.dumps(..., sort_keys=True, indent=1)` after masking uuid-shaped ids and ISO timestamps). Verified deterministic across 3 processes with different `PYTHONHASHSEED`. This is the byte-identity guard: the developer's T32 changes must keep demo output byte-identical; a drift failure is a regression unless re-captured deliberately. Documented blind spot: a change confined to masked shapes only (uuids/timestamps) is not caught.
- C6 `test_superseded_history_stays_queryable_with_its_value` — GREEN by construction (status column is a free String(40)); guards history preservation during reextract.
- R8 `test_there_is_exactly_one_head` — GREEN structural (single-head invariant, model-free).
- R1 negative cases (TTL−1s not stale ×2, fresh-claim apply_freshness ×2, next_recheck_at basis ×2) — GREEN and must stay GREEN.

## COMMANDS (run in `/Users/wpalish/ashyq-worktrees/c2-t32-qa/backend`, venv `./.venv`)

1. `./.venv/bin/python -m pytest tests/test_freshness_regressions.py tests/test_source_scan.py --tb=no -q` → exit **1** — `34 failed, 10 passed` (all planned: 20 REDs in freshness file + 14 contract REDs in source_scan; 10 GREENs as listed).
2. `./.venv/bin/python -m pytest tests/test_worker.py tests/test_jobs.py tests/test_freshness_regressions.py --tb=no` → exit **1** — `20 failed, 76 passed in 14.50s`; all 20 FAILED lines are the planned test_freshness_regressions.py REDs; **tests/test_worker.py and tests/test_jobs.py fully green, untouched** (pgserver provisioned real PostgreSQL).

Logs: `pytest_new_files.log`, `pytest_worker_jobs_freshness.log`, `pytest_worker_jobs_freshness_summary.log` in this directory. Note: an earlier combined run's exit code was lost to a pipe (tail's exit captured); it was re-run to capture the true pytest exit codes above.

## ENVIRONMENT

- Offline: no network calls; demo corpus pipeline for R2/R3/R6; scripted fake bound over `Fetcher.get` (class-level seam) for scan/reextract; PG via conftest pgserver fixtures (`pg_engine`, two independent sessions per race test). No retries, no timeout increases, no assertion weakened.

## NOTES FOR DEVELOPER / NEXT QA

- source_scan (C3) is a run-less job: today `_dispatch` fails every run-less non-payment job at the `run is None` lookup before any kind branch — the restructure is part of the contract work.
- R7 assumes response fields `status`/`pages`/`job_ids`/`skipped_urls` and refresh job keys `reextract:{page}:{result}:{generation}` per C2/C5; if implementation names differ, that is a test-contract change to negotiate first, not a silent edit.
- R5's "new claims appended" is grounded on the corpus page `app/corpus/pages/tu-delft/admissions.html` (proven to extract `ielts_min_overall` via the html_rule extractors).
- Constraints honored: no T29 files (discovery/catalog_walker/page_classifier/live_discovery/test_live_discovery/fixtures untouched), no production edits, no push.
