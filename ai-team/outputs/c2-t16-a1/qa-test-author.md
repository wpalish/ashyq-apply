# T16 A1 — QA TEST_AUTHOR report (ashyq-qa)

- ROLE_PHASE: TEST_AUTHOR
- STATUS: TESTS_READY
- Baseline checked: `git rev-parse HEAD` on `ai/c2/t16/qa` = `4d2125c00e2a320d6f6c31a79600bf97237ce218` (matches frozen baseline; tree was clean before my changes)
- QA commit: `65e63ec69dda5b06b2bcdc9754cdf8fcf2f53f24` (parent = baseline; only the two test files; NOT pushed)

## FILES_CREATED_OR_MODIFIED

- NEW `/Users/wpalish/ashyq-worktrees/c2-t16-qa/backend/tests/test_browser_network.py` (421 lines)
- APPEND-ONLY `/Users/wpalish/ashyq-worktrees/c2-t16-qa/backend/tests/test_ssrf.py` (+71 lines at end; existing lines untouched, diff = 71 insertions, 0 deletions)

No production code touched. No conftest.py/test_api.py/test_pipeline.py/test_live_regressions.py edits.

## RED_RESULTS (all real failures on baseline, `12 failed, 86 passed in 0.63s`)

| Scenario | Expected defect evidence | Actual baseline failure mode (pytest output snippet) |
|---|---|---|
| R1a `TestRenderedStatusReporting::test_browser_error_page_is_not_ok` | browser.py:141-150 | `assert <FetchOutcome.OK: 'ok'> is <FetchOutcome.HTTP_ERROR: 'http_error'>` — rendered 404 came back as `FetchResult(outcome=OK, status_code=404, ...)` |
| R1b `TestRenderedStatusReporting::test_render_with_no_response_is_not_ok` | browser.py:134 | `assert True is False ... .ok` — goto()=None gave `outcome=OK, status_code=None, error=''` |
| R2 `TestEscalationGuard::test_error_rendering_is_not_escalated_or_cached` | fetching.py:459-464 | get() returned `outcome=OK, status_code=404, fetch_tier='browser'`; log shows `unimatch.fetch: escalated ... to the browser tier` (fetching.py:462); cache poisoned with the error page |
| R3 `TestRedirectStreamHygiene::test_redirect_hop_response_is_closed` | fetching.py:358-371 | `assert False is True ... hop_stream.closed` — 302 hop stream never closed |
| R4a `TestBrowserInfraFailure::test_browser_infra_failure_is_a_result_not_a_crash` | fetching.py:619 else-branch | real `playwright._impl._errors.Error: Target page, context or browser has been closed` propagated out of `Fetcher.get` (playwright IS installed in the venv; the real exception class was used, not the fallback) |
| R4b `TestBrowserInfraFailure::test_render_infra_exception_does_not_crash_the_fetcher` | browser.py:113-125 (outside inner try) | `playwright._impl._errors.Error: Browser has been closed` from `new_context` escaped `BrowserFetcher.render` |
| R5 `TestSpecialPurposeRanges::test_as112_and_6to4_ranges_are_blocked[4 addrs]` + `test_6to4_relay_and_as112_urls_are_refused[2 addrs]` | network_policy.py:27-37 | `is_blocked_address('192.88.99.1') -> (False, '')`, `is_allowed('http://192.88.99.1/') -> (True, '')` — all four addresses (192.88.99.1, 192.31.196.1, 192.52.193.1, 192.175.48.1) currently allowed; verified independently with `ipaddress` flags: none of is_private/is_reserved/etc. is set on Python 3.12.13 |

## GREEN_RESULTS (justified)

- R6 `TestRouteGateNegativeControl` (2 tests): `is_allowed('http://169.254.169.254/latest/meta-data/')` is already False (real policy, literal IP, no DNS), and `BrowserFetcher._gate_request` aborts it while continuing an allowed stylesheet request (gate branching verified with fake route/request objects). Negative control only — not claimed as a fix.
- test_ssrf.py additions `TestErrorStatusesAreErrors` (3 tests): HTTP 403/404 → `HTTP_ERROR`, status preserved, `text == ''`, `content == b''`; HTTP 429 → exactly 3 attempts (MAX_ATTEMPTS) with backoff sleeps `[2, 4]` (sleeps stubbed via monkeypatch so the shape is proven without paying 6s) then `HTTP_ERROR` with status 429. All pass on baseline — explicit guards for existing correct behavior, so the browser-tier fix cannot regress the HTTP tier.
- All 81 pre-existing test_ssrf.py test items still pass (baseline file collects 81 items; current file 84 — append-only, verified against `git show 4d2125c:backend/tests/test_ssrf.py`).

## CONTRACT VERIFICATION (planner claims checked against code before writing tests)

All confirmed by reading source: browser.py:134,141-150 unconditional OK; fetching.py:459 `rendered.ok` alone + :463 cache.put; fetching.py:360-371 redirect `continue` without aclose; fetching.py:614-619 else-branch not covered by excepts at :604-613; network_policy.py:27-37 lacks the four ranges. Frozen semantics encoded as assertions: nav >=400 → `HTTP_ERROR` w/ status preserved + empty text; resp None → `UNPARSEABLE` w/ diagnostic; browser-infra failure → non-OK FetchResult, never raises.

## TEST DESIGN (offline; no Chromium; no network)

- Playwright faked at the `BrowserFetcher._browser` attribute seam: `_ensure()` short-circuits when a browser is set, so nothing imports/launches Playwright. FakeBrowser/FakeContext/FakePage implement exactly the calls browser.py makes.
- HTTP tier: `httpx.MockTransport` + `fetcher._client` replacement (established test_ssrf.py pattern); DNS bypassed via a stub resolver through `monkeypatch.setattr("app.adapters.fetching.check_url", ...)`; R1/R4 browser URLs use a literal public IP so `check_url` needs no DNS.
- R3 aclose observability: custom `httpx.AsyncByteStream` subclass; verified empirically that httpx 0.28.1's client wraps but delegates `aclose()` to the handler-provided stream (terminal 200's stream reports closed=True; the redirect hop reports False on baseline).
- R6 continue-path uses `monkeypatch.setattr("app.adapters.browser.is_allowed", ...)` so no DNS happens in the gate test.
- Local fixtures only; conftest.py untouched.

## COMMANDS AND EXIT CODES

1. `git rev-parse HEAD` → `4d2125c00e2a320d6f6c31a79600bf97237ce218`; `git status --porcelain` → empty (clean)
2. `./.venv/bin/python -m pytest tests/test_browser_network.py tests/test_ssrf.py -q` → exit 1: `12 failed, 86 passed in 0.63s` (intended: 12 RED / 86 GREEN)
3. `./.venv/bin/python -m pytest "tests/test_browser_network.py::TestRouteGateNegativeControl" "tests/test_ssrf.py::TestErrorStatusesAreErrors" -v` → exit 0: `5 passed in 0.50s`
4. `./.venv/bin/python -m ruff check tests/test_browser_network.py tests/test_ssrf.py` → exit 0 `All checks passed!`
5. `./.venv/bin/python -m ruff format --check ...` → exit 0 `2 files already formatted`
6. `./.venv/bin/python -m mypy tests/test_browser_network.py tests/test_ssrf.py` → exit 0 `Success: no issues found in 2 source files`
7. Affected-suite run (no PostgreSQL, fetch/browser boundary only):
   `./.venv/bin/python -m pytest tests/test_browser_network.py tests/test_ssrf.py tests/test_adapters.py tests/test_security.py tests/test_live_regressions.py tests/test_live_discovery.py tests/test_live_extraction.py tests/test_metrics.py` → exit 1: `12 failed, 382 passed, 1 warning in 11.59s` — the only 12 failures are exactly the planned REDs; zero unexpected failures.
   (Full `tests/` run deliberately not executed: it pulls in the shared PostgreSQL/pgserver suites; per TEAM_RULES those need a resource slot from the dispatcher. The fetch-boundary-adjacent files listed above do not use pg fixtures — checked by grep.)
8. `git add` (2 files only) + `git commit` → `65e63ec69dda5b06b2bcdc9754cdf8fcf2f53f24`, parent = baseline, tree clean after.

## NOTES FOR DEVELOPER / REVIEWER

- R2's fake renderer deliberately returns the baseline-buggy shape (`outcome=OK, status_code=404`) so the test pins the fetching.py:459-464 escalation guard independently of the browser.py fix. R4a likewise pins the fetching.py:619 guard with a plain raising renderer; R4b pins the browser.py:107-125 catch. Defense at either single site alone does not turn the whole file green — both layers of the frozen contract are covered.
- Assertions encode the frozen contract mappings exactly (HTTP_ERROR/UNPARSEABLE/non-OK). If the developer prefers a different remedy (e.g. infra failure falling back to the original HTTP result), that is a test-contract change and must be agreed before a new candidate, per TEAM_RULES.
- MAX_REDIRECTS-in-browser, final_url recording, and the rebinding TOCTOU (S1) were NOT tested: S1 is a documented residual (Chromium does its own DNS/connect; not offline-fixable), and the contract lists them as out of R1-R6 scope.
- R4 uses the real `playwright.async_api.Error` when playwright is installed (it is, in this venv) with an offline fallback class — the test file runs on machines without playwright too.

## UNTESTED_RISKS

- S1 rebinding TOCTOU (browser performs its own DNS+connect after the is_allowed gate) — not reproducible offline; documented residual.
- Browser-internal redirects unbounded by MAX_REDIRECTS and final_url never recorded — contract says leave to developer scope; no RED test authored for them (not in R1-R6).
- Anything requiring a live Chromium render or real network was excluded by design.
