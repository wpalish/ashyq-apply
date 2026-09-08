# T28 A1 — QA TEST_AUTHOR report (ashyq-qa, campaign c2)

- ROLE_PHASE: ashyq-qa / TEST_AUTHOR
- STATUS: TESTS_READY
- CHECKED_SHA: 28d729ca76cdf8d52344517a8316e2e805099d11 (git rev-parse HEAD verified; tree clean at start; branch ai/c2/t28/qa)
- COMMIT_SHA: 0ce3e67b34fffa203f32b7ff4140d62ca9d2b680 (QA commit; exactly 2 files, 715 insertions; no production edits; not pushed)

## Files created

- backend/tests/test_fetch_pii_hops.py (9 tests: scenarios 1-7 + stream pin)
- backend/tests/test_source_pages.py (8 tests: scenarios 8-14)

## Baseline runs

| Command | Result | Exit |
|---|---|---|
| `./.venv/bin/python -m pytest tests/test_fetch_pii_hops.py tests/test_source_pages.py` | 14 failed, 3 passed in 8.35s | 1 |
| `./.venv/bin/python -m pytest tests/test_ssrf.py tests/test_browser_network.py tests/test_adapters.py` | 169 passed in 0.82s | 0 |
| `ruff check` + `ruff format --check` on the two new files | clean (after one I001 fix + format) | 0 |

Pre-test manual repro (throwaway /tmp/t28-qa/repro_hop_pii.py, not in repo): poisoned hop
`https://other.example.com/jump?token=abc123` WAS fetched on baseline — outcome `ok`,
second host requested once, `stats['refused_privacy'] == 0`. The find_pii-on-hops gap is real:
find_pii only at fetching.py:564 (entry); hop loop 339-385 calls check_url per hop only.
T16 stream closure confirmed present at fetching.py:363,374 (not re-implemented, only pinned).

## RED_RESULTS (per scenario, real failure modes)

| # | Scenario | Mode | Snippet |
|---|---|---|---|
| 1 | credential in hop refused, 2nd host 0 reqs, stats bucket, content b"" | assertion | `AssertionError: assert <FetchOutcome.OK: 'ok'> is <FetchOutcome.REFUSED_PRIVACY>` (FetchResult carried the leaky body; final_url=hop) |
| 2 | 9+ digit hop query refused | assertion | same shape; `final_url='https://other.example.com/lookup?id=123456789'` — hop fetched |
| 3 | poisoned hop never reaches check_url/DNS (seam) | assertion | `AssertionError: poisoned hop reached check_url: ['https://ok.example.com/start', 'https://ok.example.com/start', 'https://other.example.com/jump?token=abc123']` (entry checked twice by design: get() + hop loop; hop URL is the RED signal) |
| 4 | conditional GET 304 -> CACHED/empty/from_cache | missing API | `AttributeError: 'FetchResult' object has no attribute 'etag'` (evaluating the kwarg before the call) |
| 5 | conditional request still pays robots + spacing | missing API (classified honestly) | `TypeError: Fetcher.get() got an unexpected keyword argument 'etag'` — politeness assertions themselves are only exercisable post-implementation |
| 6a | 200 records etag/last_modified/content_hash | missing API | `AttributeError: 'FetchResult' object has no attribute 'etag'`; content_hash pins the C4 formula (sha256 over NFKC of " ".join(html_to_text(text).split())) |
| 6b | escalation resets validators, recomputes hash | assertion (contained cause) | `assert <UNPARSEABLE> is <OK>`; result.error: `browser tier failed: FetchResult.__init__() got an unexpected keyword argument 'etag'` (existing escalation guard contained the missing API) |
| 8 | two PG sessions record same url -> 1 row, fields from B, claims kept | ImportError (accepted new-module pattern) | `ImportError: cannot import name 'SourcePage' from 'app.models'` (pg fixture itself worked) |
| 9 | raw duplicate insert -> IntegrityError, count 1 | ImportError | same |
| 10 | record() coalesce/overwrite semantics (SQLite) | ImportError | same |
| 11 | migration round-trip SQLite (down to e7c1a4d90b52 + re-upgrade) | assertion | `assert False` where `False = has_table('source_pages')` after upgrade head |
| 12 | migration round-trip PostgreSQL | assertion | same on PGInspector (pgserver provisioned, database created+migrated) |
| 13a | retention constant agreement (migration located by content) | assertion (clear, per contract design) | `AssertionError: no migration file defines SOURCE_PAGE_RETENTION_DAYS` |
| 13b | is_purgeable truth table incl. exact-boundary not purgeable | ImportError | `ModuleNotFoundError: No module named 'app.models.source_page'` |

## GREEN_RESULTS (justified)

- Scenario 7 politeness constants tripwire: MAX_PER_HOST_CONCURRENCY==2, DEFAULT_DELAY_SECONDS==1.5,
  MAX_REDIRECTS==5, MAX_ATTEMPTS==3 — existing correct behavior pinned (contract: byte-identical politeness).
- Stream pin: redirect hop streams stay closed (T16, fetching.py:363,374) — regression pin for the loop T28 edits.
- Scenario 14: exactly one alembic head and it == app.db.head_revision() — model-free by design; GREEN before and after T28.

## ENVIRONMENT

darwin arm64; Python 3.12.13; venv /Users/wpalish/ashyq-worktrees/c2-t28-qa/backend/.venv;
pytest 9.1.1 (asyncio_mode=auto), SQLAlchemy 2.0.36; offline HTTP via httpx.MockTransport + stub
resolver (technique copied from test_ssrf.py, not imported); PG scenarios on conftest pgserver
(local, in-process). No real network. Parallel-task files (extraction.py, web_requirements.py) untouched;
conftest.py / test_ssrf.py / test_jobs.py untouched.

## ARTIFACT_REFS

- /Users/wpalish/ashyq-apply/ai-team/outputs/c2-t28-a1/pytest_new_tests_baseline.log
- /Users/wpalish/ashyq-apply/ai-team/outputs/c2-t28-a1/pytest_collateral_baseline.log
- QA commit 0ce3e67b34fffa203f32b7ff4140d62ca9d2b680 on ai/c2/t28/qa

## UNTESTED_RISKS

- Scenario 8 exercises two independent sessions committing against the same URL (atomic
  ON CONFLICT at statement level), not a deterministic interleaved race.
- Robots-per-hop stays out of scope per contract C6 (residual).
- ResponseCache unbounded growth (audit gap) has no contract scenario — not covered here.
- Downgrade target hardcoded to e7c1a4d90b52 (frozen contract down_revision); if the integrator
  rebases the chain, only that constant and this note change.

## BLOCKERS

None.

## NEXT_ACTION

Developer branches from QA commit 0ce3e67 and implements per contract C1-C7;
VERIFY_CANDIDATE then runs in a fresh verification worktree against the candidate SHA.
