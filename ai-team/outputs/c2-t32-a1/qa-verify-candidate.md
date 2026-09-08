# T32 A1 — QA VERIFY_CANDIDATE report (campaign c2, independent invocation)

- ROLE_PHASE: QA / VERIFY_CANDIDATE
- STATUS: VERIFIED_PASS (one environmental, fully-proven non-regression on R6 — see GATES a/c)
- Worktree: /Users/wpalish/ashyq-worktrees/c2-t32-verify (branch ai/c2/t32/verify), read-only except pytest caches
- CHECKED_SHA: 7bfa715a994e973a5a8216b1713324ee74cf1fe3 (tree clean before and after all gates; re-verified after runs)
- BASELINE_SHA: 2ed4f51e1d5c1fae3f4cb36ad64982eb67184a2d; QA RED: 65e15220e8d0584b7fc0878e71f2e69a3bcbd47b

## 1. CHAIN / SCOPE CHECK (per commit) — PASS

- `git rev-parse HEAD` = 7bfa715a... ; `git status --porcelain` empty; `git rev-list --count 2ed4f51..HEAD` = 5; linear: 65e1522 → ce517c2 → 60da37f → ade82fb → 7bfa715.
- 65e1522..ce517c2: exactly 9 files — api/routes_results.py, domain/conflicts.py, domain/enums.py, domain/freshness.py, jobs/source_scanner.py (NEW, 575 lines), jobs/worker.py, models/research.py, pipeline/runner.py, migrations/versions/d9c4e7a21b83_claims_source_page_and_recheck_generation.py (NEW). Matches C10 exactly; store.py untouched (kind constants live in source_scanner.py instead — within the module's remit).
- ce517c2..60da37f: only backend/app/jobs/worker.py (+11/−4).
- 60da37f..ade82fb: only backend/app/main.py (+2/−1) — `reconcile_startup(arm_source_scans=not settings.demo_mode)`; scope-granted.
- ade82fb..7bfa715: only tests/test_freshness_regressions.py + tests/test_source_scan.py (+92/−73). `git diff 65e1522..HEAD -- backend/tests/` touches ONLY these two files. R6/golden/mask/demo-test region byte-identical to the RED commit (no diff lines in the golden/mask/demo area); amendment = FK/server_default reflection keys, `_take_over` available_at restore, ruff rewraps — asserted facts (SET NULL, default 0) unchanged. Consistent with qa-contract-amendment.md.

## 2. ANTI-WEAKENING / CONTRACT CONFORMANCE (read from code, not trusted) — PASS

- freshness.py: `is_stale` = `(now_norm - accessed_norm) >= timedelta(days=max_age_days)` — inclusive boundary; `_as_utc` normalizes both operands (naive now safe); `age_days` display-only (is_stale no longer calls it); `apply_freshness` moves VERIFIED_CURRENT only — SUPERSEDED passes through (pin test green).
- enums.py: only `SUPERSEDED = "SUPERSEDED"` added. conflicts.py: entry filter `live = [c for c in claims if status != SUPERSEDED]` applied BEFORE grouping AND before the returned updated list — an old value cannot resurrect as a conflict.
- models/research.py ↔ migration d9c4e7a21b83: `ClaimRow.source_page_id` String(32) nullable, FK `fk_claims_source_page` → source_pages.id ON DELETE SET NULL, indexed; `ResearchRun.recheck_generation` Integer NOT NULL server_default "0" default 0. Migration: down_revision "b4e8a1c2f6d9" (plain assignment), batch_alter_table, downgrade is the exact inverse (drop column → drop FK → drop index → drop recheck_generation, in reverse order). Single head verified (gate f).
- worker.py `_schedule_recheck`: key `f"recheck:{run.id}:{run.recheck_generation}"` — generation, never a date; runner `_arm_recheck` sets next_recheck_at AND bumps generation in the same transaction (`_save` commit). Extras (cancel leftover QUEUED rechecks; past `when` → now+60s) strengthen, not weaken. Run-bound completion + audit + recheck enqueue still commit atomically with the token fence (worker.py:343-353 unchanged in shape).
- Run-less dispatch: `source_scan` routed before the run lookup; `_complete_runless` drops ONLY the worker_id condition, keeps the `attempts` token fence. store.py: claim sets `attempts = Job.attempts + 1` and every fenced write conditions `Job.attempts == lease_token`, and claim stamps worker_id — a stale attempt's token matches nothing after takeover, so it can neither complete nor renew. T10 lease/heartbeat/fail/cancel paths byte-untouched. Two real-PG takeover race tests green.
- reextract_page: ONE transaction across the whole supersession — flip old live claims of (run, source_url) (status column AND payload["status"], set source_page_id, keep accessed_at/values), append fresh claims (apply_freshness applied), SourcePage.record + lastmod_seen set directly on the returned instance; zero-yield pages still supersede (never keeps VERIFIED_CURRENT the page no longer supports); any raise → whole attempt rolls back → queue backoff. Keys `reextract:{page}:{result}:{N}` with N = terminal-count for the prefix — never a date.
- runner.py: `_noop_recheck_moment` = min over live claims of max(next_recheck, now+1h), floor alone if no live claims — strictly future; `_live_claim_moments` excludes SUPERSEDED; `_replace_evidence` deletes only status != SUPERSEDED. Demo golden covered under GATES (see a/c).
- routes_results.py refresh: `require_full_access` (cross-tenant 404 via owned_run inside, then 402 standard body), demo run → 409 {"detail": "demo runs are read-only"}, 202 with {status, pages, job_ids, skipped_urls}; resolves live claims' distinct source_urls → source_pages → one generation-keyed `reextract_page` reason="manual" per (page, result); unknown URL → skipped_urls; zero live claims → 202 pages:0; request loop is DB+enqueue only (no fetch/extraction); audit event + single commit.
- source_scanner.py: conditional GET `fetcher.get(url, use_cache=False, etag=page.etag, if_modified_since=page.last_modified_header)`; 304 → fetched_at only, zero extraction; ROBOTS_DISALLOWED → skip, record nothing (sitemap and page paths); purge ONLY via T28 `is_purgeable` (active_claims>0 → False, strictly-older boundary) under key `source_scan:__purge__:{date}`; bootstrap: distinct institution_key, skips institutions with queued/running scan for today/tomorrow key, stagger = sha256(institution) % 3600 (stable across processes — better than the contract's `hash()`); only network surface is Fetcher (no socket/urllib imports). Demo guard complete: BOTH `reconcile_startup` call sites (app/main.py:53, worker.py:477) pass `arm_source_scans=not settings.demo_mode`.

## 3. GATES (targeted only; real runs, backend/ cwd, ./.venv; no retries, no timeout changes)

- a. `pytest tests/test_freshness_regressions.py tests/test_source_scan.py`
  - real clock (2026-09-08T00:0xZ): exit **1** — **1 failed, 43 passed** (only TestDemoRunIsByteIdentical::test_the_demo_pipeline_payload_is_byte_identical_to_baseline) — qa-verify-gate-a-realnow.log
  - frozen clock 2026-09-07T23:59:30Z (throwaway plugin, repo untouched): exit **0** — **44 passed** — qa-verify-gate-a-frozen.log
  - NON-REGRESSION PROOF: the identical test run against pristine baseline 2ed4f51 sources (git archive to /tmp, deleted after) under the real clock **fails the same way** (exit 1, same assertion) — qa-verify-baseline-r6-realnow.log. Root cause: runner.py writes `today.isoformat()` (date-only, UNMASKED by `_mask_volatile`'s `_ISO_TS` which requires the T-time part) into the result payload — introduced in pre-campaign commit 9cfb20b (2026-08-28), untouched by the T32 diff (`git diff 2ed4f51..7bfa715 -- runner.py` has no today/deadline_passed hunks). The golden captured 2026-09-07 is valid only on 2026-09-07 UTC; my run started 4 minutes after UTC midnight rolled. The amendment's 44-passed log (Sep 7 23:53 UTC) is consistent. Conclusion: pre-existing test-design time-bomb, NOT a candidate defect. The QA author's documented blind spot covers masked shapes only.
- b. `pytest tests/test_worker.py tests/test_jobs.py` → exit **0**, **66 passed** (pgserver real PostgreSQL) — qa-verify-gate-b.log
- c. `pytest tests/test_source_pages.py tests/test_pipeline.py tests/test_api.py tests/test_freshness_regressions.py`
  - frozen clock: exit **0**, **132 passed** — qa-verify-gate-c.log (only other test_freshness* file is test_freshness_regressions.py — confirmed by ls)
  - real clock: exit **1**, **131 passed, 1 failed** — same single R6 test, nothing else — qa-verify-gate-c-realnow.log
- d. `mypy app tests` → exit **0**, "Success: no issues found in 163 source files" — qa-verify-gate-d.log
- e. `ruff check app tests` → exit **0**, "All checks passed!"; `ruff format --check app tests` → exit **0**, "163 files already formatted" — qa-verify-gate-e1.log / qa-verify-gate-e2.log
- f. alembic ScriptDirectory.get_heads() → **['d9c4e7a21b83']** exactly one head.

Environment: offline tests; demo corpus pipeline; scripted Fetcher seam; PG via conftest pgserver (pg_engine / pg_factory / pg_worker_env) — no skips in any gate log. A transient one-off plugin-import error on the first gate-c invocation (freshly written plugin file; plugin imported fine standalone immediately after; retry identical command exit 0) — not a test failure, disclosed for honesty.

## 4. ADVERSARIAL NOTES (none blocking)

1. R6 golden date-bound (found): mask `^\d{4}-\d{2}-\d{2}$` too, or freeze the runner clock inside the test — TEST-CONTRACT change; NOT applied by me (no self-service test edits at verify stage). Owner/dispatcher should schedule an amendment; until then the golden is only meaningful on its capture date.
2. reextract generation-key race (narrow): `enqueue_reextract` counts TERMINAL jobs for the prefix, then enqueues. If a reextract for the same (page, result) completes between the count and the insert, the new job's key collides with the just-completed one and the dedupe returns it — that change is dropped until the next daily scan re-detects the content_hash delta. Self-healing next scan; low probability; candidate for a follow-up (e.g. count non-terminal+terminal, or include a monotonic component).
3. Recheck 60s re-arm loop: `_schedule_recheck` pushes a past `when` to now+60s. If a page persistently fails re-verification (its claims keep the old accessed_at), the run re-enters recheck roughly every minute. Cost concern (repeated fetch attempts through Fetcher rate limits), not a correctness bug; the old behavior was worse (chain dead). Watch in production; possible follow-up backoff.
4. Refresh endpoint abuse: no rate limit; the generation-key dedupe only holds while the previous job set is non-terminal, so a paid user spamming refresh sequentially gets one re-read per completed cycle. Behind require_full_access and Fetcher rate limits; accepted-risk/follow-up (contract has no rate-limit requirement).
5. Missing result_id on refresh returns 202 pages:0, not 404: developer.md note 55 documents the interpretation that C5's "result filter → 404" applies to the RUN (owned_run), zero-claims refresh being a valid 202 no-op; the frozen QA tests encode exactly that. Disclosed interpretation, not silently introduced — flagging for the record.
6. Purge safety verified in code + tests: is_purgeable returns False for active_claims>0; FK ON DELETE SET NULL keeps SUPERSEDED history rows when a page is purged (PG test green); purge executes the predicate only (expunge before bulk delete, count+log).
7. Scan transaction shape: no heartbeat/lease renewal inside the scan transaction (documented deadlock-avoidance); the worker's heartbeat task keeps the lease; takeover race covered by the PG tests.
8. Sitemap partial-lastmod edge: when the sitemap parses but lacks entries for some stored pages, those pages are checked only if lastmod_seen is unset, or via the content-hash sweep only when the map is entirely empty — a page with lastmod_seen set and absent from a non-empty sitemap is skipped that cycle. Defensible reading of C3 ("per sitemap URL"); noted for completeness.

## 5. BLOCKERS

None. No production file touched; no T29 files touched; no push; worktree left clean at 7bfa715.

## 6. ARTIFACT_REFS (all under /Users/wpalish/ashyq-apply/ai-team/outputs/c2-t32-a1/)

- qa-verify-gate-a-realnow.log / qa-verify-gate-a-frozen.log / qa-verify-gate-b.log
- qa-verify-gate-c.log / qa-verify-gate-c-realnow.log
- qa-verify-gate-d.log / qa-verify-gate-e1.log / qa-verify-gate-e2.log
- qa-verify-baseline-r6-realnow.log (baseline non-regression proof)
- qa_verify_freetime_plugin.py (throwaway probe; freezes app.pipeline.runner datetime; kept for reproduction, lives outside the repo)

## 7. NEXT_ACTION

Dispatcher may freeze 7bfa715 as VERIFIED. Queue (owner-visible): (1) R6 golden masking/clock amendment as a test-contract change; (2) follow-up ticket for the reextract generation-key race and recheck 60s loop economics; refresh rate-limit as product decision. This verification does not constitute merge approval.
