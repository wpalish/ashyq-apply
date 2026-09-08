# qa-verify-candidate-a2.md — T32 A2 (repair cycle A2, campaign c2) — VERIFY_CANDIDATE on 1b363c7

ROLE_PHASE: ashyq-qa / VERIFY_CANDIDATE (independent new invocation)
STATUS: VERIFIED_PASS
CHECKED_SHA: 1b363c707240a1f0fb92419b2f06eee4fed06399 (branch ai/c2/t32/verify-a2, tree clean before and after all runs)
WORKTREE: /Users/wpalish/ashyq-worktrees/c2-t32-verify-a2 (read-only except pytest caches; no file under the worktree was written by QA)
VENV: /Users/wpalish/ashyq-worktrees/c2-t32-verify-a2/backend/.venv (Python 3.12.13, provisioned; no extra pytest flags)

## SCOPE_CHECK — PASS

- `git rev-parse HEAD` → 1b363c707240a1f0fb92419b2f06eee4fed06399; `git status --porcelain` empty (checked before and after all gates/adversarial runs); branch ai/c2/t32/verify-a2.
- Ancestry: `git merge-base --is-ancestor` 51a52c4→e8779da OK, e8779da→1b363c7 OK. `git log 51a52c4..1b363c7 --oneline` = exactly two commits (e8779da QA RED with `Agent: ashyq-qa`, 1b363c7 fix with `Agent: ashyq-developer`).
- `git diff e8779da..1b363c7 --stat` → ONLY backend/app/jobs/source_scanner.py (+23/−2).
- `git diff e8779da..1b363c7 -- backend/tests/` → EMPTY (QA A2 test file byte-identical; zero assertion edits).
- `git diff 51a52c4..1b363c7 --stat` → backend/app/jobs/source_scanner.py + backend/tests/test_source_scan.py ONLY (+524/−2). No T29 files, no migrations, no store/worker/fetcher changes.

## DIFF_REVIEW — PASS (one wording nit, no functional impact)

The candidate diff is one hunk (@@ -220,8 +220,29 @@) inside `reextract_page` only; `source_scan`'s own `_check_page` fetch and 304 branch (:456-463) are untouched.

1. Validators from the loaded row: `page = session.get(SourcePage, source_page_id)` at :217 (LookupError if gone), then `fetcher.get(url, use_cache=False, etag=page.etag or None, if_modified_since=page.last_modified_header or None)` (:230-235). None-safe via `or None` (also normalizes empty strings).
2. `use_cache=False` deviation — VERIFIED JUSTIFIED at the source: fetching.py `if use_cache and not validators:` (~:778) reads the warm cache whenever no validator is sent; with default True a validator-less row would warm-cache-read and reintroduce RC-1, contradicting the packet's own "a row with no validators fetches unconditionally". With validators present, `use_cache` is moot (cache skipped) and the conditional GET is fully exercised. Developer's disclosure is accurate.
   - Nit: developer-a2.md calls the call "byte-identical to `_check_page` (:457-459)". It is functionally equivalent, not byte-identical: `_check_page` passes `page.etag` directly while reextract normalizes `page.etag or None`. Divergence only for empty-string values, which `if etag:` in fetching.py treats identically. No behavioral difference (mypy passes both).
3. 304-first branch (:236-244): touches `page.fetched_at` directly on the persistent instance + `session.add(page)` + log + `return`. NO `_record_page` — verified at models/source_page.py `record()`: `on_conflict_do_update` sets `etag`/`last_modified_header`/`content_hash` unconditionally from the passed values ("a None overwrites"), only `institution_key`/`lastmod_seen` coalesce. A 304 FetchResult carries empty validators, so `_record_page` would have wiped the stored ones. The skip is correct and required by RC1-B's survival assertions.
4. No supersede/no append on 304: the early return precedes the supersede query (:272+), the append loop, and the 200-path `_record_page` (:310).
5. Early return → job completes SUCCEEDED in the same transaction: worker.py :333-336 `await reextract_page(...)` then :347 `store.complete(...)` — proven behaviorally by RC1-B (SUCCEEDED, attempts==1, empty last_error).
6. `if not res.ok: raise RuntimeError(...)` retained after the 304 branch (:245-246); 200 path unchanged; one-transaction semantics unchanged.
7. Imports: `datetime`/`UTC` already imported at module top; robots/PIG guard untouched (all network still via `Fetcher`).

## GATES (real runs, cwd /Users/wpalish/ashyq-worktrees/c2-t32-verify-a2/backend)

| gate | command | exit | result |
|---|---|---|---|
| a | `./.venv/bin/python -m pytest tests/test_source_scan.py` | 0 | 17 passed, 1 warning in 11.72s (14 pre-existing + RC1-A + RC1-B + guard) |
| b | `./.venv/bin/python -m pytest tests/test_freshness_regressions.py tests/test_worker.py tests/test_jobs.py` | 0 | 96 passed in 15.12s (pgserver) |
| c | `./.venv/bin/python -m pytest tests/test_pipeline.py tests/test_api.py tests/test_source_pages.py` | 0 | 102 passed, 1 warning in 47.40s (pgserver) |
| d | `./.venv/bin/python -m mypy app tests` | 0 | Success: no issues found in 163 source files |
| e | `./.venv/bin/python -m ruff check app tests` then `./.venv/bin/python -m ruff format --check app tests` | 0 / 0 | All checks passed! / 163 files already formatted |
| f | `UNIMATCH_DEMO_MODE=true ./.venv/bin/python -m alembic heads` | 0 | exactly one head: d9c4e7a21b83 |

Logs: qa-a2v-gate-a.log, qa-a2v-gate-b.log, qa-a2v-gate-c.log, qa-a2v-gate-d.log, qa-a2v-gate-e1.log, qa-a2v-gate-e2.log, qa-a2v-gate-f.log (this directory). No --cov run (integrator's), no full-suite run, no retries/timeouts inflated, no assertion edits.

## ADVERSARIAL_NOTES — 13/13 PASS (real runtime, /tmp script + own ephemeral pgserver instance)

Script: /tmp/qa_a2_adversarial.py; log: qa-a2v-adversarial.log (exit 0; the StaleDataError traceback inside it is the worker's own expected logging of scenario 2).

1. NULL-validator row (never fetched), RC-1 topology (warm cache v1 / origin v2): handler's call was `{use_cache: False, etag: None, if_modified_since: None}` → unconditional origin fetch; job SUCCEEDED; old v1 claim SUPERSEDED (column+payload); live ielts_min_overall = 7.5 (origin truth, NOT warm-cache 6.0); page row recorded etag '"etag-v2"' + new content_hash. Honest, no laundering.
2. Row deleted between load and fetch (purge wins the race; origin then answers 304): handler sent the stored validators (`'"etag-same"'` + Last-Modified); the 304 branch's `UPDATE source_pages` matched 0 rows → `sqlalchemy.orm.exc.StaleDataError` → worker recorded the failure (job back to queued, last_error=StaleDataError...). NO false no-change success over a ghost row; live claim stayed VERIFIED_CURRENT; nothing appended; the deleted row was NOT resurrected (no `record()` on the 304 path). The retry leg (row still gone → LookupError at :217-219) is code-verified only: the in-process re-claim did not fire within the drain window (lease/backoff), so `retried=False` was observed; the failure semantics on retry follow the pre-existing A1 path.
3. 304 with stored validators preserving etag/content_hash: pinned by RC1-B (test_source_scan.py:1479-1484: etag '"etag-same"' AND content_hash survive) — green in gate a.
4. `_check_page` untouched: diff = single reextract-only hunk; scan-path behavior still pinned green by pre-existing tests (stored-ETag conditional GET :456-508; 304 short-circuit preserves '"v1"' :530-575).

## BLOCKERS

None.

## RESIDUALS / UNTESTED_RISKS

- Scenario 2's retry-LookupError leg: code-read only (lease backoff prevented an in-process re-claim); not executed.
- Concurrency beyond the single raced delete (two simultaneous refreshes of one page) remains out of RC-1 scope, as QA-A2 and developer already flagged.
- The 200-path's `record()` INSERT..ON CONFLICT can re-create a deleted page row during a genuine change — pre-existing A1 behavior, unchanged by this candidate, out of A2 delta.
- SEC-T32-02/03/04 and reviewer followups remain open, untouched.

## NEXT_ACTION

Candidate 1b363c707240a1f0fb92419b2f06eee4fed06399 is verified by QA (VERIFIED_PASS). Hand to the independent ashyq-reviewer (and security re-review of RC-1) on this exact SHA; no further code changes without a new candidate + new verification. QA does not grant merge approval; integrator + user gates follow per TEAM_RULES.
