# T32 A1 — DEVELOPER report

- ROLE_PHASE: DEVELOPER
- STATUS: BLOCKED (implementation complete; 4 frozen QA tests carry test-side defects — one-line QA amendments proposed below; candidate frozen and reviewable)
- Baseline: 2ed4f51e1d5c1fae3f4cb36ad64982eb67184a2d; QA base: 65e15220e8d0584b7fc0878e71f2e69a3bcbd47b
- Worktree: /Users/wpalish/ashyq-worktrees/c2-t32-dev (branch ai/c2/t32/dev), tree clean after commit
- CANDIDATE_SHA: ce517c273cfa9ca2fd74ea355591b00cb06fd0cd (single commit on the QA commit; no push)

## FILES_CHANGED (9 files, +916/−31)

- backend/app/domain/freshness.py (+41/−6): `is_stale` compares UTC-normalized moments, inclusive boundary `(now_norm − accessed_norm) >= timedelta(days=max_age_days)`; `age_days` display-only; naive `now` normalized; `apply_freshness` pinned (moves VERIFIED_CURRENT only, SUPERSEDED passes through untouched).
- backend/app/domain/enums.py (+5): `ClaimStatus.SUPERSEDED = "SUPERSEDED"`. No DDL.
- backend/app/domain/conflicts.py (+9/−2): find_conflicts drops SUPERSEDED at entry (before grouping); `updated` built from the live list.
- backend/app/models/research.py (+18): `ClaimRow.source_page_id` (String(32), nullable, FK `fk_claims_source_page` → source_pages.id ON DELETE SET NULL, index=True → ix_claims_source_page); `ResearchRun.recheck_generation` (Integer, NOT NULL, server_default "0", default 0).
- backend/migrations/versions/d9c4e7a21b83_claims_source_page_and_recheck_generation.py (NEW, +59): batch_alter_table on both tables (SQLite/PG parity); exact inverse downgrade (`type_="foreignkey"`); plain `down_revision = "b4e8a1c2f6d9"` (annotated form breaks QA's dynamic locator regex); single head before/after (d9c4e7a21b83).
- backend/app/jobs/source_scanner.py (NEW, +575): scan/reextract/purge/bootstrap (details in DESIGN_NOTES).
- backend/app/jobs/worker.py (+83/−6): `_schedule_recheck` generation key + past-moment clamp + cancel of stale queued recheck siblings; `_dispatch` run-less `source_scan` branch (incl. purge payload) before the run lookup; `reextract_page` branch (run-bound, common completion+audit tail); `_complete_runless` (token-fenced completion); `reconcile_startup` bootstraps scans (new summary key `scans_bootstrapped`; existing keys untouched).
- backend/app/pipeline/runner.py (+69/−8): `_live_claim_moments` (excludes SUPERSEDED); `_noop_recheck_moment` = min over live claims of max(expiry, now+1h), `now+1h` when no live claims; `_arm_recheck` (next_recheck_at + generation bump, committed together via `_save`); used by both `recheck_stale` no-op path and `run_to_decision`; `_replace_evidence` deletes only `status != SUPERSEDED`.
- backend/app/api/routes_results.py (+88): POST /api/runs/{run_id}/results/{result_id}/refresh — `require_full_access` (404 cross-tenant via owned_run inside it, then 402 PaymentRequired body), demo run → 409 `{"detail": "demo runs are read-only"}`, 202 `{"status": "refresh_scheduled", "pages": N, "job_ids": [...], "skipped_urls": [...]}`, one generation-keyed `reextract_page` per (page, result) with reason "manual"; no fetch/extraction in the request loop; audit event + single commit.

## GATES (real runs, venv ./.venv, backend/ cwd)

a. `./.venv/bin/python -m pytest tests/test_freshness_regressions.py tests/test_source_scan.py --tb=no` → exit 1 — **40 passed, 4 failed** (the 4 failures are QA-test defects; see BLOCKERS for proof that the underlying implementation behavior is correct in all four).
b. `./.venv/bin/python -m pytest tests/test_worker.py tests/test_jobs.py --tb=line` → **66 passed** (pgserver; T10/T28 semantics green, unmodified).
c. `./.venv/bin/python -m pytest tests/test_source_pages.py tests/test_pipeline.py tests/test_api.py --tb=line` → **102 passed**.
d. `./.venv/bin/python -m mypy app tests` → Success: no issues found in 163 source files.
e. `./.venv/bin/python -m ruff check app` → clean; `./.venv/bin/python -m ruff format --check app` → clean. `ruff check tests` → 3 pre-existing I001 findings and `ruff format --check tests` → 2 files would reformat, **all inside the frozen QA test files at commit 65e1522** (tests/ untouched by me — `git status` clean for tests/); not fixable without violating the no-QA-edit rule.
f. `alembic heads` → exactly one head `d9c4e7a21b83`; `head_revision()` agrees. Round-trip mechanics proven on SQLite and PG (upgrade → downgrade b4e8a1c2f6d9 → re-upgrade with column assertions on both sides) via a throwaway probe (deleted after use): downgrade removes both columns; re-upgrade restores them, FK name fk_claims_source_page, ON DELETE SET NULL present (SQLite DDL text shows `ON DELETE SET NULL`; PG `pg_constraint.confdeltype='n'` = SET NULL), ix_claims_source_page present, recheck_generation NOT NULL DEFAULT '0'.
R6 demo byte-identity: `test_the_demo_pipeline_payload_is_byte_identical_to_baseline` GREEN on the candidate (golden sha256 aae8c595…d702 holds).

## RED_TO_GREEN (per QA scenario)

- R1 boundary/naive tests (8×2): RED (False is True / TypeError) → GREEN.
- R2 no-op recheck re-arms (new queued job, strictly future, fresh key): RED (zero jobs / past available_at) → GREEN.
- R3 two no-op cycles, one follow-up each, keys never repeat: contract RED → GREEN.
- R4 SUPERSEDED enum + find_conflicts exclusion + apply_freshness pin: AttributeError RED → GREEN; history-queryability GREEN by construction → still GREEN.
- R5 forced change supersedes+appends in one commit (PG): `unknown job kind` RED → GREEN. R5 fenced half: supersession/appends correctly rolled back (proven via amended-helper simulation) — test itself blocked by the takeover-helper defect (BLOCKER-2).
- C3 skeleton: sitemap-lastmod scan (conditional GET carries stored ETag, one reextract per (page,result) with reason sitemap_lastmod, lastmod_seen advanced, self-reschedule ≥ next UTC midnight): GREEN. 304 short-circuit (no extraction, validators untouched): GREEN. robots-disallowed (nothing recorded): GREEN. double-bootstrap (exactly one scan per institution, stagger < 1h, date key): GREEN. lease-takeover scan race: implementation proven via amended-helper simulation (exactly one surviving reextract set, page updated) — blocked by BLOCKER-2.
- C4 purge: only purgeable rows deleted, active/fresh kept: GREEN (ModuleNotFoundError RED → GREEN).
- R7 refresh: 402 free (code=payment_required), 404 cross-tenant ("Research run not found"), 409 demo exact body, 202 paid with 2 generation-keyed manual jobs + skipped_urls, zero-claims 202 no-op, double-click dedupes to one job set: all GREEN.
- R6 demo byte-identity: GREEN by construction on baseline → GREEN on candidate.
- R8 migration round-trip: locator/single-head GREEN; round-trip tests blocked by two assertion-shape defects (BLOCKER-1); mechanics + schema facts proven correct by probe (gate f).

## DESIGN_NOTES (deviations and choices)

1. Run-less dispatch restructure: `source_scan` routed before the run lookup (payment_reconcile pattern). Scan completion uses `_complete_runless` — the attempt-token fence only, deliberately without the worker-id condition: the frozen scan-takeover test requires the attempt that continues an interrupted scan to finish it, and the token is what distinguishes attempts (a stale attempt's token matches nothing). Run-bound kinds keep the full worker+token fence.
2. Extraction reuse for reextract: the handler builds the runner's own `WebRequirementsAdapter` over a synthesized Candidate/CandidateProgram (program name taken from the evidence being replaced; domain from SourcePage.registrable_domain) and lets the adapter fetch+classify+extract; the handler's own fetch warms the cache so the page is read from the origin once. Fetch failure (fetch-failed category, non-ok, or 304) raises → queue backoff retries, live claims stand; unreadable/classifier-rejected supersedes (honest: the page was read and no longer supports the values).
3. Supersession scope: run of the destination result, per source_url (contract C2 wording); old rows keep accessed_at/values, gain source_page_id, column AND payload status flip (GET /claims reads payload).
4. Reextract generation keys `reextract:{page}:{result}:{n}` with n = count of TERMINAL jobs under the prefix (never a date); dedupe collapses racing producers.
5. Purge scheduling: dedicated dated key `source_scan:__purge__:{yyyy-mm-dd}` as a real job (kind source_scan, payload {"purge": true}), enqueued by every completing scan, available next UTC midnight — store dedupe makes it once-daily; dispatch branch runs `purge_source_pages` (bulk delete via T28 `is_purgeable`, expunges instances before the bulk delete so identity maps stay honest).
6. Scan scheduling: institution-stable sha256 stagger (%3600) at next UTC midnight; handler self-reschedules on success; bootstrap in reconcile_startup skips institutions with a queued/running scan for today's/tomorrow's key.
7. C3 "No-ops in demo_mode" NOT implemented as a settings gate: the frozen QA tests (double-bootstrap and all scan skeleton tests) run under the `settings` fixture with `demo_mode=True` and require bootstrap + real scan work. The frozen tests are the operative contract here; in a demo deployment there are in practice no live source_pages to scan. Flagged for the dispatcher as a contract-vs-test conflict resolved in favor of the frozen tests.
8. Scan-generated reextracts enqueue with available_at = now + BACKOFF_SECONDS[0] (30s): the frozen `_drain(settings) == 1` pins that a scan must not leave immediately-claimable work in the same tick; manual (refresh/R5) reextracts stay immediately claimable.
9. `_schedule_recheck` cancels stale QUEUED recheck siblings of the run before enqueueing under the fresh generation key (the old date-key dedupe prevented stacking implicitly; generation keys need the explicit cancel). Also clamps a past `next_recheck_at` to now+60s so a follow-up can never be born overdue.
10. Result resolution in reextract/refresh works off claims' `result_id` (a grouping key), NOT the program_results primary key — the frozen tests seed these independently; contract C5's "result filter → 404 like get_result" applies to the RUN (owned_run), with zero-claims refresh a valid 202 no-op.

## BLOCKERS (QA test-contract amendments needed — one line each, new QA cycle)

1. R8 `_assert_t32_columns` (tests/test_freshness_regressions.py:633): `fk.get("ondelete")` — SQLAlchemy 2.0.36 reflects the action under `fk["options"]["ondelete"]` on BOTH dialects (top-level key is never populated). The DDL is proven correct: SQLite CREATE TABLE contains `ON DELETE SET NULL`; PG `pg_constraint.confdeltype='n'`; the behavioral SET NULL test (test_deleting_a_source_page_nulls_the_claims_reference) is GREEN. Suggested amendment: read `fk.get("ondelete") or (fk.get("options") or {}).get("ondelete")`. Same test, line ~646: on SQLite `gen.get("server_default")` is None (SQLite reflection exposes the DDL default as `gen["default"] == "'0'"); suggested amendment: accept `gen.get("server_default") or gen.get("default")`. Evidence: throwaway probe printed both dialects' reflected dicts (probe deleted after use).
2. R5/C3 takeover helper `_take_over` (tests/test_source_scan.py:371): after `reap_expired()` the store requeues at `available_at = now + backoff_for(attempts)` (30s for attempt 1 — frozen T28/T10 store semantics, test_jobs.py-green, store.py outside my scope), so the helper's immediate `claim(worker_id="worker-b")` returns None and the job ends QUEUED/attempt-1 instead of RUNNING/attempt-2. Proof of implementation correctness: a throwaway simulation with ONE added helper line (restore `available_at = now` after reap, before the claim) makes BOTH blocked scenarios pass completely — fenced reextract (job RUNNING/2, no superseded rows, no appended claims, rollback clean) and scan takeover (RUNNING/2 after attempt 1, exactly one surviving queued reextract with the right payload, page etag updated). Suggested amendment: that one line in `_take_over`. Alternative (rejected): changing the reaper's requeue backoff — store semantics change outside my allowed paths and a T10 hot-loop protection.

## RESIDUALS

- Demo-mode gate for source_scan intentionally absent (see DESIGN_NOTES 7) — needs a dispatcher ruling if the product wants it; would conflict with the frozen tests as written.
- ruff/mypy findings inside the frozen QA files (3 I001 + 2 formatting) — pre-existing at 65e1522; QA-side cleanup in the same new cycle.
- No push performed; candidate SHA is local to ai/c2/t32/dev.

## AMENDMENT (dispatcher-ordered, post-review commits)

- FINAL CANDIDATE_SHA: ade82fb1873c8b2de5ba7d9a69aaa6545a5b9697 (branch ai/c2/t32/dev, three commits on the QA base 65e1522; tree clean; frozen for QA amendment + verify/review).
- 60da37fc8fd3dc03fbdcbafceee82e3a9071d46e — "fix: T32 skip source_scan bootstrap in demo mode (contract C3 wiring-level guard)", +11/−4 in app/jobs/worker.py: `reconcile_startup` gained `arm_source_scans: bool = True`; the worker entry (`main()`) calls `reconcile_startup(arm_source_scans=not settings.demo_mode)`. PLACEMENT DEVIATION, disclosed: the ruling's literal placement (unconditional `if not settings.demo_mode` around the import+call inside reconcile_startup) would flip the FROZEN `test_double_bootstrap_enqueues_one_scan_per_institution` to red — that test calls `reconcile_startup()` directly under demo settings (worker.py binds `get_settings` at import time to the env-based function; `demo_mode` defaults True) and asserts 2 scans, while the ruling itself expected "same 40/4". The keyword keeps reconcile_startup's default behavior (frozen tests untouched) and skips nothing inside bootstrap_source_scans.
- ade82fb1873c8b2de5ba7d9a69aaa6545a5b9697 — "fix: T32 arm_source_scans parity at API startup (scope-granted)", +2/−1 in app/main.py:52: the API lifespan now also calls `reconcile_startup(arm_source_scans=not settings.demo_mode)` (scope extension granted by dispatcher).
- Gates re-run after both amendments: gate (a) same 40/4 (only the 4 approved QA-defect reds), gate (b) 66 passed, test_api.py 66 passed, mypy app tests clean (163 files), ruff check app clean, ruff format app clean.

## NEXT_ACTION

Dispatcher: route BLOCKERS 1–2 to QA for the two one-line amendments in a new QA cycle, then re-run gate (a) on this candidate unchanged (only the two QA files change; expected 44/44). T29 parallel files untouched; no QA assertions weakened; no store/pipeline-lease semantics changed.
