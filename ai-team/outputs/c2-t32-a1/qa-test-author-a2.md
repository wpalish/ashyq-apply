# qa-test-author-a2.md — T32 A2 (repair cycle A2, campaign c2) — RC-1 / SEC-T32-01 regression tests

ROLE_PHASE: ashyq-qa / TEST_AUTHOR_A2
STATUS: TESTS_READY
CHECKED_SHA (baseline candidate): 51a52c4b39381f873bdfabac8c3aaff2fbc02de3 (branch ai/c2/t32/qa-a4, tree clean at start)
QA COMMIT_SHA: e8779da (parent 51a52c4) — trailer `Agent: ashyq-qa`; no push performed

## ENVIRONMENT

- Worktree (only place written): /Users/wpalish/ashyq-worktrees/c2-t32-qa-a4
- Venv: /Users/wpalish/ashyq-worktrees/c2-t32-qa-a4/backend/.venv (python 3.12, pytest 9.1.1)
- PostgreSQL: ephemeral via `pgserver` (tests/conftest.py `postgres_url` fixture); one migrated DB per test. No external/shared PG touched. Offline fakes only; no network fetches (Fetcher.get monkeypatched at the class seam, the existing test pattern).
- Sources read before writing: backend/app/jobs/source_scanner.py (reextract_page:190-296 — `fetcher.get(url)` at :223 validator-less/cache-enabled; 304 raises RuntimeError at :224-225), backend/app/adapters/fetching.py (get():735-878 — validators skip cache, 304 => CACHED/status 304, OK cache-puts; ResponseCache TTL from app/config.py:38 `cache_ttl_seconds: int = 86_400`), backend/tests/test_source_scan.py (ScriptedFetcher seam, worker/_drain helpers).

## TEST_FILES

- Modified: backend/tests/test_source_scan.py ONLY (+501 lines, 0 deletions — no existing tests or helpers changed; single added import `from dataclasses import replace`).
- Added: class `WarmCacheOriginFetcher` (stateful fake modeling the real warm-cache/origin split of Fetcher.get: warm hit within TTL with the cache's own fetched_at; validators -> conditional GET against origin, 304 as CACHED/status_code 304, validator mismatch -> 200; `use_cache=False` -> origin; 200 refreshes the cache like the real `cache.put`), helper `_seed_refresh_evidence` (claim value + read-time knobs), helper `_v2_body` (corpus page with IELTS band 6.0 -> 7.5 so v1/v2 claims are distinguishable by normalized_value), and class `TestReextractMustNotLaunderTheWarmCache`:
  - RC1-A `test_a_warm_cache_never_laundered_into_fresh_claims`
  - RC1-B `test_a_validators_match_completes_as_no_change_without_superseding`
  - GREEN guard `test_a_real_change_seen_through_a_fresh_cache_still_supersedes_and_appends`

The fake supports BOTH security-accepted fix shapes: validators+304 (preferred) and use_cache=False — the assertions pin the observable contract, not the implementation shape.

## COMMANDS and EXIT_CODES

| command (cwd backend/) | exit | result |
|---|---|---|
| `./.venv/bin/python -m pytest tests/test_source_scan.py -q` (baseline, before edits) | 0 | 14 passed |
| `./.venv/bin/python -m ruff format tests/test_source_scan.py` | 0 | 1 reformatted (my additions only; diff = 501+/0-) |
| `./.venv/bin/python -m ruff format --check tests/test_source_scan.py` | 0 | clean |
| `./.venv/bin/python -m ruff check tests/test_source_scan.py` | 0 | clean |
| `./.venv/bin/python -m mypy tests/test_source_scan.py` | 0 | Success: no issues |
| `./.venv/bin/python -m pytest tests/test_source_scan.py -q` (candidate, RED run) | 1 | 15 passed, 2 failed (`..............FF.`) |
| `./.venv/bin/python -m pytest tests/test_freshness_regressions.py -q` | 0 | 30 passed |

Full logs: /tmp/qa_a2_baseline.txt, /tmp/qa_a2_red_run.txt, /tmp/qa_a2_red_final.txt, /tmp/qa_a2_freshness.txt (host /tmp, not in the repo).

## RED_RESULTS (candidate 51a52c4 — real output, not asserted)

RC1-A — `test_a_warm_cache_never_laundered_into_fresh_claims` FAILED at tests/test_source_scan.py:1340:

```
E  AssertionError: RC-1 RED: the reextract re-appended the WARM-CACHE v1 body as live
   evidence (id, value, accessed_at)=[('e104fe8f2a2c48eaab62a1721e9c94ce', 6.0,
   datetime.datetime(2026, 9, 8, 5, 3, 2, 309135, tzinfo=zoneinfo.ZoneInfo(key='Asia/Almaty')))]
   although the origin had moved to v2 — a refresh may only land origin truth or an honest
   no-change completion, never stale content with a fresh read-time
```

This is the finding verbatim: the seeded live claim (v1 content, read a day earlier) was superseded and a NEW row with the SAME v1 value (6.0) was appended with the warm cache's fresher read-time, while the origin serves v2 (7.5). Also pinned in the same test (evaluated post-fix): origin truth 7.5 must be live, old rows SUPERSEDED (column+payload), page row must record the origin validator '"etag-v2"', and the handler's fetch call must carry validators or use_cache=False (on the candidate it records `{'use_cache': True, 'etag': None, 'if_modified_since': None}`).

RC1-B — `test_a_validators_match_completes_as_no_change_without_superseding` FAILED:

```
E  AssertionError: RC-1 RED: a 304-page refresh must not supersede anything (old row flipped to SUPERSEDED)
```

The "was X -> became X" churn: origin unchanged (validators match), yet the handler answered from the warm cache, superseded the live claim and re-appended it (row count 2 for 1 live claim; the handler's recorded call is `{'use_cache': True, 'etag': None, 'if_modified_since': None}` — the 304 path is unreachable). The test additionally pins post-fix: job SUCCEEDED with attempts==1 and empty last_error (no dead-letter, no retry), claim read-time not re-dated, fetched_at touched at/after refresh start (candidate records the cached copy's read-time), and the stored etag/content_hash must survive a 304 (a 304 confirms the stored copy; wiping validators would force every later scan into full fetches).

## GREEN_RESULTS

- Guard `test_a_real_change_seen_through_a_fresh_cache_still_supersedes_and_appends` PASSED on the candidate: when the origin genuinely changed (200, new content_hash — cache fresh the way the daily scan leaves it) the reextract still supersedes old + appends the new value (7.5) and records the new validators. The fix must not turn every refresh into a no-op.
- All 14 pre-existing tests in test_source_scan.py remained green; tests/test_freshness_regressions.py 30 passed, exit 0.

## ASSERTIONS (contract pinned)

1. A manual refresh lands origin truth; warm-cache content may never become live evidence with a newer read-time (RC1-A).
2. Validators that match the origin (304) => clean no-change completion: job succeeded, no supersede, no append, fetched_at touched, stored validators/content_hash intact, no retry (RC1-B).
3. A genuine change still supersedes + appends (guard, justified GREEN).
4. Shape-agnostic: satisfied by validators+304 or use_cache=False; the handler's own fetch must carry validators or use_cache=False (asserted from the fake's call log).

## BLOCKERS

None. Notes for the implementer: today `source_scanner.py:224-225` raises on `status_code == 304`, so the mandated 304-as-no-change completion needs that branch replaced (touch fetched_at, complete without supersede/append, without clobbering stored validators). RC1-B's `fetched_at >= refresh start` and validators-survival assertions are part of the pinned contract, not implementation details.

## NEXT_ACTION

Hand QA commit e8779da to the developer: implement the RC-1 fix (validators + 304-no-change preferred) on a branch cut from this commit, freeze the candidate SHA, then a NEW ashyq-qa VERIFY_CANDIDATE run in a fresh verification worktree. These RED tests must flip GREEN without editing assertions.

## UNTESTED_RISKS

- The fake models the real Fetcher cache/contract at the class seam; a fix that bypasses `Fetcher.get` entirely (new transport path) would dodge the call-log assertions (though the DB-state assertions would still hold).
- Concurrency (two simultaneous refreshes of one page) is out of RC-1 scope here; only single-worker `_drain` semantics exercised.
- The 304-with-clobbered-validators scenario is pinned only for RC1-B's end state, not for the source_scan path itself.
