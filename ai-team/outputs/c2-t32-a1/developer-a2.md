# developer-a2.md — T32 A2 (repair cycle A2, campaign c2) — RC-1 fix

ROLE_PHASE: ashyq-developer / IMPLEMENTING
STATUS: IMPLEMENTED
CHECKED_SHA (start): e8779dab56806793d1adcc5d71042fbd7ba059ba (QA A2 RED commit, branch ai/c2/t32/dev-a2, tree clean at start)
CANDIDATE_SHA: 1b363c707240a1f0fb92419b2f06eee4fed06399 (commit "fix: T32 A2 reextract reads origin via stored validators; 304 completes as no-change (RC-1)", trailer `Agent: ashyq-developer`; parent e8779da; NOT pushed)

## CHANGED_FILES

- `backend/app/jobs/source_scanner.py` ONLY (+23 / -2). `reextract_page` fetch is now a conditional GET with the page's stored validators, and the 304 branch completes as an honest no-change. No test file touched (QA assertions byte-untouched); no Fetcher/store/worker/migration changes.

## THE FIX (in reextract_page, backend/app/jobs/source_scanner.py:222-247)

1. Validator plumbing: `await fetcher.get(url, use_cache=False, etag=page.etag or None, if_modified_since=page.last_modified_header or None)` — the page row is already loaded at :217. Validators only when present; a validator-less row fetches unconditionally (nothing to condition on).
2. 304 branch (replaces the old `or res.status_code == 304` raise): `page.fetched_at = datetime.now(UTC); session.add(page); log.info(...); return` — no supersession, no appends, no `_record_page` (a 304 FetchResult carries empty etag/content_hash and `record()` OVERWRITES validators on conflict — only institution_key/lastmod_seen coalesce — so calling it would wipe the stored validators). The early return lets the worker complete the job SUCCEEDED in the same transaction (same shape as `_check_page`'s 304 branch, :460-463).
3. 200 path unchanged: extraction via WebRequirementsAdapter, supersede (column+payload) + append, `_record_page` records the NEW validators, one-transaction semantics intact (flip+append+record+completion).
4. `if not res.ok: raise ...` kept after the 304 branch for genuine failures (retry via backoff, live claims stand).

## DESIGN_NOTES (deviation, deliberate)

- The packet's literal call was `fetcher.get(url, etag=..., if_modified_since=...)` (use_cache defaulting True). I pass `use_cache=False` as well, because with no validators present a default-True read hits the warm disk cache (fetching.py:778 `if use_cache and not validators`) — that would reintroduce RC-1 for validator-less rows and contradict the packet's own parenthetical ("a row with no validators fetches unconditionally"). With validators present, `use_cache` is moot (fetching.py:778 skips the cache whenever a validator is sent), so the T28 conditional GET is fully exercised and 304 is reachable — this is byte-identical to the call `_check_page` already makes (:457-459). Result: the warm cache can never feed the reextract for ANY row.
- RC1-B pins validators/content_hash surviving the 304: satisfied by touching `fetched_at` directly on the persistent instance instead of `record()`.
- Call-log assertions (RC1-A/RC1-B: etag or if_modified_since not None, or use_cache False): satisfied on all three axes.

## GATES (real runs, cwd backend/)

| gate | command | result |
|---|---|---|
| a | `./.venv/bin/python -m pytest tests/test_source_scan.py` | 17 passed, 1 warning in 3.85s (exit 0) |
| b | `./.venv/bin/python -m pytest tests/test_freshness_regressions.py tests/test_worker.py tests/test_jobs.py` | 96 passed in 15.06s (exit 0) |
| c | `./.venv/bin/python -m pytest tests/test_pipeline.py tests/test_api.py tests/test_source_pages.py` | 102 passed, 1 warning in 47.67s (exit 0) |
| d | `./.venv/bin/python -m mypy app tests` | Success: no issues found in 163 source files |
| e | `./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m ruff format --check app tests` | All checks passed! / 163 files already formatted |

Baseline RED run (pre-fix, same worktree): `15 passed, 2 failed` — exactly `TestReextractMustNotLaunderTheWarmCache::test_a_warm_cache_never_laundered_into_fresh_claims` and `::test_a_validators_match_completes_as_no_change_without_superseding`.

## RED_TO_GREEN

- RC1-A test_a_warm_cache_never_laundered_into_fresh_claims: RED at baseline (warm-cache v1 re-appended as live) → GREEN: conditional GET with stored '"etag-v1"' reaches the moved origin, 200 v2 supersedes old rows and appends 7.5 with fresh read-time, page row records '"etag-v2"'.
- RC1-B test_a_validators_match_completes_as_no_change_without_superseding: RED (304 unreachable; raise → retry; churn) → GREEN: 304 completes SUCCEEDED attempts==1 empty last_error, nothing superseded/appended, claim read-time preserved, fetched_at touched, etag '"etag-same"' + content_hash survive.
- Guard test_a_real_change_seen_through_a_fresh_cache_still_supersedes_and_appends: stays GREEN (validator mismatch → 200 → supersede + append 7.5, new validators recorded).
- All 14 pre-existing test_source_scan.py tests green before and after.

## MIGRATIONS

None. No schema change.

## RESIDUALS

- The 304-with-clobbered-validators scenario is pinned only at RC1-B's end state, not for the scan path itself (QA note).
- Concurrency (two simultaneous refreshes of one page) out of RC-1 scope; single-worker `_drain` semantics exercised.
- SEC-T32-02/03/04 and the reviewer followups remain open tickets, deliberately untouched.
- Candidate NOT reviewed by independent QA/reviewer yet — next step is a NEW ashyq-qa VERIFY_CANDIDATE run on 1b363c7 in a fresh verification worktree.

## BLOCKERS

None. QA tests implemented as written; zero assertion edits.

## NEXT_ACTION

Freeze candidate 1b363c707240a1f0fb92419b2f06eee4fed06399; hand to coordinator for independent QA verification (and then reviewer/security re-review of RC-1) on this SHA. No push performed.
