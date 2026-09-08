# T28 A1 — QA VERIFY_CANDIDATE report (ashyq-qa, campaign c2)

- ROLE_PHASE: ashyq-qa / VERIFY_CANDIDATE
- STATUS: VERIFIED_PASS
- CHECKED_SHA: b087b9dcc0bae57d3c0b678ba3a4679869da1037 (git rev-parse HEAD; tree clean before and after gates; branch ai/c2/t28/verify)
- Worktree: /Users/wpalish/ashyq-worktrees/c2-t28-verify (read-only except pytest caches; no files modified)

## SCOPE_CHECK (per commit, verified by diff, not by trust)

- Chain: `git log --oneline 28d729c..HEAD` → exactly 4 commits, in order:
  0ce3e67 (QA RED) → 498428b (impl) → 57a1cb0 (db.py) → b087b9d (amendment).
  Parentage verified with rev-parse: b087b9d^=57a1cb0, 57a1cb0^=498428b, 498428b^=0ce3e67, 0ce3e67^=28d729c. Linear.
- `git diff 0ce3e67..498428b --stat` = fetching.py + models/__init__.py (+2) + models/source_page.py (NEW 170) + migrations/versions/b4e8a1c2f6d9_source_pages.py (NEW 63). Exactly the contract scope.
- `git diff 498428b..57a1cb0 --stat` = ONLY backend/app/db.py (+4/−1). Functional delta is one line — `config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))` — plus 3 comment lines documenting it. File scope = exactly the dispatcher-authorized file.
- `git diff 57a1cb0..b087b9d` = ONLY tests/test_live_discovery.py, +7/−1, one hunk: StubSite.fake_get signature extended (url, *, use_cache=True, etag=None, if_modified_since=None). Hunk read line by line: body (`self.requested.append(url)`, pages lookup) untouched; zero assertion/test-body/expected-value changes.
- `git diff 0ce3e67..HEAD -- backend/tests/test_fetch_pii_hops.py backend/tests/test_source_pages.py` → empty (0 bytes): QA RED tests byte-identical across the whole chain.
- `git diff 0ce3e67..HEAD --stat` full: 6 files only; NO extraction.py / web_requirements.py / network_policy.py / conftest.py / test_ssrf.py / test_jobs.py (all confirmed 0-byte diffs).

## ANTI_WEAKENING_CHECK (code read, not claimed)

- C6 hop guard: in `_request_with_redirects`, per hop — response `aclose()`d → `current = str(httpx.URL(current).join(location))` → `leak = find_pii(current)` → guard sits BEFORE the next iteration's `check_url` (poisoned URL never reaches policy/DNS; pinned by test 3). Refusal path: `log.warning("refusing %s: looks like %s", current[:120], leak)` — byte-same format as the entry guard; returns (no raise) REFUSED_PRIVACY with contract error text and final_url=hop; the hop response is closed before the guard runs. Stats incremented exactly once via get()'s non-retryable accounting (`stats[result.outcome.value] += 1`) — matches frozen `stats[...] == 1`.
- Politeness constants byte-identical to baseline 28d729c (diffed): DEFAULT_DELAY_SECONDS=1.5, MAX_PER_HOST_CONCURRENCY=2, MAX_ATTEMPTS=3; MAX_REDIRECTS=5 in network_policy.py (file 0-byte diff). Robots gate, `_space_requests`, semaphore, MAX_ATTEMPTS loop all structurally unchanged.
- C5 conditional GET: `get(..., etag=None, if_modified_since=None)`; validators only as caller-supplied headers (Fetcher never touches DB); `if use_cache and not validators` → disk cache skipped when validators present; validators ride the FIRST request only (`validators = None` right after request build — no cross-host leakage on hops, verified in code); robots/`_space_requests`/semaphore still wrap the conditional request (pinned by test 5: robots_requests==1, sleep in (2.0, 2.5]); `_read_response` tests `status_code == 304` FIRST, before 4xx/content-type/size/body; 304 → CACHED/304/b""/""/from_cache/error="not modified (304)"; in get(), 304 is non-retryable → returns immediately, no backoff sleep reached, no cache.put (only OK branch puts), no escalation (`_maybe_render` only called on OK).
- C3: FetchResult += etag/last_modified/content_hash, defaults "" — additive; NO new FetchOutcome member (app/domain/enums.py 0-byte diff). ResponseCache put/get store/restore the three meta keys; old entries restore defaults via `.get(..., "")`. All production call sites are plain `await fetcher.get(url)` — backward compatible.
- C4: `_content_hash` = sha256(NFKC-collapse(html_to_text(text))); falls back to raw text on extraction failure/empty (PDF covered); docstring documents self-consistency. Escalation in `_maybe_render`: rendered.etag="", last_modified="", content_hash recomputed from rendered text BEFORE cache.put. Fixtures never hashed (fixture path returns before hashing/caching).
- C1/C2/C7 SourcePage: exact columns/nullability per contract (url Text NN, registrable_domain String(255) NN, institution_key String(120) N, etag/last_modified_header Text N, content_hash String(64) N, lastmod_seen/fetched_at DateTime(tz) N, http_status Integer N, page_type String(40) NN default "unknown", active_claims Integer NN default 0; TimestampedBase id/created_at/updated_at match migration). 4 named indexes incl. unique(url) ALONE. `record()`: single dialect `insert().on_conflict_do_update(index_elements=[url], ...)` — pg and sqlite; NO select-then-insert decision; conflict set_ overwrites fetch fields (None overwrites), `func.coalesce(table.c.X, X)` for institution_key/lastmod_seen (existing wins), active_claims NOT in set_, updated_at refreshed; flush, no commit. The single post-execute SELECT (`session.query(cls).filter(url==).one()`) is read-only — cannot create a duplicate. RETENTION_DAYS=180 + verbatim retention docstring in BOTH model (module + is_purgeable) and migration; is_purgeable strict `>` (exactly RETENTION_DAYS ⇒ kept), active_claims>0 never purgeable.
- Migration: revision b4e8a1c2f6d9, down_revision e7c1a4d90b52; upgrade = create_table + 4 indexes; downgrade = drop 4 indexes + table; no existing table touched. `alembic heads` → exactly one: b4e8a1c2f6d9 (head).
- db.py: exactly the % escape (one functional line + comments).
- Amendment: signature mirror only, no assertion change (hunk read).

## GATES (re-run by QA on the candidate, venv ./.venv, logs in outputs dir)

| # | Command | Result | Exit |
|---|---|---|---|
| a | `./.venv/bin/python -m pytest tests/test_fetch_pii_hops.py tests/test_source_pages.py` | 17 passed in 9.33s (9+8; pgserver scenarios RAN — 0 skipped matches in log, pg fixtures fail hard when unavailable) | 0 |
| a2 | `./.venv/bin/python -m pytest tests/test_source_pages.py` | 8 collected, 8 passed, 0 skipped in 1.76s (proves per-test collection) | 0 |
| b | `./.venv/bin/python -m pytest tests/test_ssrf.py tests/test_browser_network.py tests/test_adapters.py tests/test_jobs.py` | 199 passed in 5.86s | 0 |
| c | `./.venv/bin/python -m pytest tests/test_live_discovery.py` | 112 passed in 0.63s (same count as amendment report; green) | 0 |
| d | `./.venv/bin/python -m mypy app tests` | "Success: no issues found in 158 source files" | 0 |
| e | `./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m ruff format --check app tests` | "All checks passed!" / "158 files already formatted" | 0 / 0 |
| 5 | `./.venv/bin/python -c "from app.db import head_revision; print(head_revision())"` and `./.venv/bin/alembic heads` | b4e8a1c2f6d9 / "b4e8a1c2f6d9 (head)" — exactly one | 0 / 0 |
| 6 | `./.venv/bin/python -m pytest tests/test_live_regressions.py tests/test_metrics.py tests/test_pipeline.py` | 103 passed, 1 warning in 16.19s | 0 |

Sweep pg-classification: test_live_regressions.py and test_pipeline.py — zero pg references. test_metrics.py — 2 hits, both a DSN string `"postgresql+psycopg://u:p@db/unimatch"` inside config dicts; no pgserver fixture, no server needed. Classified pg-free; sweep ran without PostgreSQL and did not conflict with any pg environment.

Sweep warning: third-party `StarletteDeprecationWarning` from fastapi's testclient inside .venv — environmental, unrelated to T28.

## ADVERSARIAL_NOTES (all examined; none blocks)

1. Unsolicited 304 on an UNCONDITIONAL request (e.g. on a hop, or a hostile server 304-ing a plain GET) is reported as CACHED/304/empty exactly like a validated 304. Contract C3 defines 304 → CACHED and mandates consumers check status_code==304; behavior is fail-safe (empty body, "keep your copy"), but a caller ignoring the status could mistake "no data" for "unchanged". Residual, out of contract; worth a line in T29/T32 caller docs.
2. record() identity-map staleness: if the caller's session ALREADY holds a SourcePage for the same URL loaded earlier in the same transaction, the post-execute SELECT returns that identity-mapped instance without refreshing attributes — the DB row is correct, but attributes read off the return value may be pre-upsert. Cannot create duplicates (pure SELECT). No production caller in T28; T29/T32 should re-fetch or expunge if they read attributes after an in-session prior load.
3. record() on a session with an aborted transaction raises SQLAlchemy PendingRollbackError — not masked; correct.
4. Empty-string etag from a 200 (header present but empty) is stored as ""/NULL and the next visit degrades to a full GET — consistent truthiness, harmless.
5. `_FractionalCrawlDelayParser` only patches `entry.delay` when the stdlib left it None, and only for groups whose user-agent list matches exactly — strictly politeness-strengthening, can only increase delays, never lower them.
6. Validator headers merged after Host in `_pinned_request` — a validator can never clobber the Host header (disjoint keys).
7. If-None-Match + If-Modified-Since both sent when both provided; RFC 7232 makes the server ignore If-Modified-Since then — contract-conformant ("If-None-Match precedence per RFC 7232").
8. Robots-per-hop remains out of scope per contract C6 (unchanged residual); ResponseCache remains unbounded (pre-existing audit gap, no contract scenario). Both carried forward, not introduced.
9. QA's RED test `_content_hash` is an independent reimplementation of the C4 formula (no fallback branch) — the pin would catch a normalization drift; it does not test the production fallback path (untested residual, low risk).

## Report-vs-reality discrepancies found (minor, non-blocking)

- developer.md says the migration creates "13 columns"; the file creates 14 (id, created_at, updated_at + 11 contract columns). Miscount in the report only; code and model agree.
- developer.md says fetching.py "+212 / −13"; the impl-commit stat is 212 ins + 13 del for that file — consistent; total +447/−13 across 4 files matches.

## BLOCKERS

None.

## ARTIFACT_REFS

- /Users/wpalish/ashyq-apply/ai-team/outputs/c2-t28-a1/qa-verify-candidate.md (this report)
- qa-verify-gate-a.log, qa-verify-gate-a-verbose.log, qa-verify-gate-b.log, qa-verify-gate-c.log, qa-verify-gate-d-mypy.log, qa-verify-gate-sweep.log (same dir)

## UNTESTED_RISKS

- Scenario 8 remains a two-session sequential-commit race test (atomic statement-level), not a deterministic interleaving — as flagged by TEST_AUTHOR.
- Unsolicited-304 semantics (adversarial note 1) and record() identity-map staleness (note 2) are code-read findings, not test-pinned.
- Full suite / --cov sweep and frontend gates were dispatcher-reserved for the integrator; not run here. E2E not in scope.

## NEXT_ACTION

Candidate b087b9d verified PASS on all re-run gates; hand to ashyq-reviewer (and security, per policy) on the frozen SHA, then integrator for full-suite/--cov and chain integration. QA does not grant merge approval.
