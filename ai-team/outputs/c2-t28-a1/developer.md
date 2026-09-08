# T28 A1 — DEVELOPER report (ashyq-developer, campaign c2)

- ROLE_PHASE: ashyq-developer / IMPLEMENT (final, after dispatcher scope expansion)
- STATUS: IMPLEMENTED
- CHECKED_SHA: 0ce3e67b34fffa203f32b7ff4140d62ca9d2b680 (QA RED commit; parent 28d729ca76cdf8d52344517a8316e2e805099d11 = baseline; worktree clean at start, branch ai/c2/t28/dev)
- CANDIDATE_SHA: 57a1cb0 (HEAD of ai/c2/t28/dev; two commits: 498428b implementation + 57a1cb0 dispatcher-approved db.py seam fix; not pushed)
- Worktree: /Users/wpalish/ashyq-worktrees/c2-t28-dev
- Scope expansion recorded: dispatcher decision 2026-09-07 approved ONE line in backend/app/db.py (test_live_discovery.py explicitly NOT authorized for developer — QA contract amendment, not touched).

## CHANGED_FILES (exact, vs QA commit)

| File | Change |
|---|---|
| backend/app/adapters/fetching.py | +212 / −13 |
| backend/app/models/source_page.py | NEW, 170 lines |
| backend/app/models/__init__.py | +2 (SourcePage import + __all__ entry) |
| backend/migrations/versions/b4e8a1c2f6d9_source_pages.py | NEW, 63 lines — revision id b4e8a1c2f6d9, down_revision e7c1a4d90b52 |
| backend/app/db.py | +4 / −1 (escape % in `_alembic_config` before set_main_option; dispatcher-approved scope expansion 2026-09-07) |

Totals: 5 files, +451 / −14 across commits 498428b + 57a1cb0. Frozen QA test files, conftest.py,
test_ssrf.py, test_jobs.py, test_live_discovery.py, extraction.py, web_requirements.py: untouched.

## RED_TO_GREEN (per former-RED)

- 1, 2 (poisoned hop refused): `_request_with_redirects` calls `find_pii(current)` after
  `current = join(location)` and before the next `check_url`; on leak it logs with the entry-level
  format and returns REFUSED_PRIVACY with final_url=hop before any request to the second host.
- 3 (poisoned hop never reaches check_url/DNS): the guard sits before the loop's next iteration.
- 4 (conditional 304 → CACHED/empty/from_cache): `get(etag=..., if_modified_since=...)` skips the
  disk cache, sends If-None-Match/If-Modified-Since on the first request only; `_read_response`
  tests 304 before every other branch → CACHED/304/""/b""/from_cache/"not modified (304)"; no
  cache.put, no retry, no escalation. httpx 0.28 counts every 3xx as `is_redirect`, so the loop
  routes `status_code == 304 or not is_redirect` to `_read_response` before the redirect branch.
- 5 (conditional request still polite): conditional path runs the unchanged robots gate and
  `_space_requests`; honoring the crawl-delay required teaching the robots parser fractional values
  (DESIGN_NOTES 3).
- 6a/6b: 200 records header validators + pinned C4 hash; escalation resets validators to "" and
  rehashes from the rendered text before cache.put.
- 8, 9, 10: SourcePage with named unique index uq_source_pages_url; `record()` = single dialect
  insert().on_conflict_do_update (pg + sqlite), flush no commit, returns persistent instance;
  fetch metadata overwrites (None overwrites), institution_key/lastmod_seen coalesce (existing
  wins over None), active_claims never in the update-set; raw dup insert hits the unique index.
- 11, 12 (migration round-trip SQLite + PostgreSQL): both green after the db.py % escape.
- 13 (retention agreement + is_purgeable truth table, strict boundary): green.
- 14 (single head == app.db.head_revision()): green, head b4e8a1c2f6d9.

## GATES (real runs, worktree backend/, venv ./.venv, on candidate 57a1cb0)

| # | Command | Result |
|---|---|---|
| a | `./.venv/bin/python -m pytest tests/test_fetch_pii_hops.py tests/test_source_pages.py` | 17 passed (scenario 8/12 ran on real pgserver PostgreSQL, not skipped) |
| b | `./.venv/bin/python -m pytest tests/test_ssrf.py tests/test_browser_network.py tests/test_adapters.py tests/test_jobs.py` | 199 passed |
| c | `./.venv/bin/python -m mypy app tests` | app/: 0 errors. Whole invocation: 1 error, tests/test_live_discovery.py:78 — EXPECTED and classified per dispatcher: test-only, caused by the contract-mandated get(etag=, if_modified_since=) signature meeting StubSite.fake_get's older stub; runtime test passes; queued for QA contract amendment; NOT a candidate blocker |
| d | `./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m ruff format --check app tests` | clean (158 files formatted) |
| e | `./.venv/bin/python -c "from app.db import head_revision; print(head_revision())"` and `./.venv/bin/alembic heads` | both: exactly one head, b4e8a1c2f6d9 |
| + | full suite `./.venv/bin/python -m pytest tests/` | 1187 passed, 0 failed |

## DESIGN_NOTES (deviations and why)

1. Hop PII guard does not increment stats itself: the guard's result flows through get()'s
   existing terminal-outcome accounting (`stats[result.outcome.value] += 1`), which increments
   exactly once — incrementing in the guard too would make the frozen `stats[...] == 1` fail with
   2. Mirrors the established in-loop pattern (redirect-without-Location returns HTTP_ERROR
   uncounted; get() counts it).
2. httpx 0.28's `is_redirect` is True for all 3xx incl. 304, so a 304 was diverted into the
   redirect branch before `_read_response` could run. Fixed by the combined early return at the
   loop head; the loop's old trailing read became dead code and was removed.
3. Fractional Crawl-delay support (`_FractionalCrawlDelayParser` in fetching.py): the stdlib
   parser stores a crawl-delay only when the value `.isdigit()` — "2.5" was silently dropped and
   the fetcher fell back to its (usually smaller) default. Frozen scenario 5 pins sleep in
   (2.0, 2.5] for `Crawl-delay: 2.5`, so this was required; it is strictly politeness-
   strengthening and additive (`_space_requests`, semaphore, MAX_ATTEMPTS/backoff, MAX_REDIRECTS,
   constants all byte-identical). The subclass re-reads only crawl-delay lines with float
   semantics and patches them onto the stdlib-parsed entries for the same user-agent groups.
4. `record()` does one post-execute SELECT to return a persistent instance — required by QA
   scenario 8, which mutates the returned object and commits; the upsert decision itself is still
   a single atomic statement (no select-then-insert).
5. `is_purgeable` uses strict `>` (exactly RETENTION_DAYS old ⇒ kept), matching C7 text and the
   frozen boundary assertions.
6. `_content_hash` falls back to raw text on extraction failure/empty; `except Exception` is
   deliberate (never break a fetch whose body we already hold).
7. db.py `%` escape is a no-op for %-free URLs (SQLite paths, plain DSNs); alembic un-escapes %%
   when reading the value back, so env.py receives the original URL — proven by the PG round-trip.

## MIGRATIONS

- One new file: migrations/versions/b4e8a1c2f6d9_source_pages.py, down_revision = "e7c1a4d90b52"
  (verified in migrations/versions/). upgrade: create source_pages (13 columns) + 4 indexes
  (uq_source_pages_url unique, ix_source_pages_domain, ix_source_pages_institution,
  ix_source_pages_retention(active_claims, fetched_at)); downgrade: drop indexes + table. No
  existing table touched. Heads: exactly one before and after (gate e). Revision id follows house
  style (random 12-hex like e7c1a4d90b52 / d4b2c8f17a90).

## RESIDUALS

- Robots-per-hop stays out of scope per contract C6 (unchanged residual).
- ResponseCache remains unbounded (audit gap, no contract scenario).
- 304 results do not touch tier_counts (stats[CACHED] only); contract silent.
- Empty-string etag passed by a caller is treated as "no validator" (header omitted, cache read
  allowed) — consistent truthiness on both cache-skip and header emission.
- test_live_discovery.py:78 mypy [assignment] remains until QA's contract amendment lands; the
  classification and one-line fix options are recorded above and in the queued coordinator
  message (response_68bd7479).

## BLOCKERS

None on the developer side.

## NEXT_ACTION

Hand candidate 57a1cb0 to VERIFY_CANDIDATE (fresh verification worktree) and reviewer. QA contract
amendment invocation to update the test_live_discovery.py:78 stub (add `etag: str | None = None,
if_modified_since: str | None = None` to fake_get, or widen the ignore) so gate c reaches 0 errors
suite-wide. No push performed.
