# T16 A1 — DEVELOPER report (ashyq-developer)

- ROLE: ashyq-developer, TASK_ID: T16, FINDING_IDS: H02, ATTEMPT_ID: A1, campaign c2
- STATUS: IMPLEMENTED
- BASELINE_SHA: 65e63ec69dda5b06b2bcdc9754cdf8fcf2f53f24 (QA RED commit; parent = baseline 4d2125c00e2a320d6f6c31a79600bf97237ce218)
- CANDIDATE_SHA: 28d729ca76cdf8d52344517a8316e2e805099d11 (branch ai/c2/t16/dev, frozen, not pushed)

## CHANGED_FILES (exact, +/- per file)

- `/Users/wpalish/ashyq-worktrees/c2-t16-dev/backend/app/adapters/browser.py` (+56 / -24)
- `/Users/wpalish/ashyq-worktrees/c2-t16-dev/backend/app/adapters/fetching.py` (+30 / -1)
- `/Users/wpalish/ashyq-worktrees/c2-t16-dev/backend/app/adapters/network_policy.py` (+4 / -0)
- `/Users/wpalish/ashyq-worktrees/c2-t16-dev/SECURITY.md` (+23 / -6)

QA test files (`backend/tests/test_browser_network.py`, `backend/tests/test_ssrf.py`) untouched — verified `git status`/diff contains only the four allowed files.

## ROOT_CAUSE_FIXED

1. browser.py reported OK for whatever `page.goto` produced (status ignored, `None` treated as OK). Now the final navigation's status decides: `>=400` -> `HTTP_ERROR` with `status_code` preserved and empty text/content; `resp is None` -> `UNPARSEABLE` with a diagnostic; only a successful final navigation yields OK.
2. fetching.py `_maybe_render` accepted on `rendered.ok` alone, so an error render was returned and `cache.put` poisoned the disk cache. Now any rendered result carrying `status_code >= 400` is refused: the original HTTP result stands and nothing error-shaped reaches the cache.
3. fetching.py manual redirect loop streamed each hop and `continue`d without closing. Now `await response.aclose()` runs on both redirect paths (missing-Location and normal hop).
4. Browser-infra exceptions escaped two ways: browser.py's `new_context`/`route`/`new_page` sat outside any try, and fetching.py's escalation call sat in the retry `else` branch where no except applies. Both layers now contain: browser.py returns a non-OK `UNPARSEABLE` diagnostic result; fetching.py wraps `_maybe_render` so a raising renderer becomes a diagnostic non-OK `FetchResult` from `get()`, never an exception.
5. network_policy `_EXTRA_BLOCKED` lacked 6to4 relay + AS112 anycast. Added `192.88.99.0/24`, `192.31.196.0/24`, `192.52.193.0/24`, `192.175.48.0/24` (additive only; public API unchanged).
6. SECURITY.md residual-risk section restated: application-enforced vs best-effort vs infrastructure boundary; no "fully SSRF-proof" phrasing.

## GATES (real commands and results, run in worktree at candidate SHA)

1. `cd backend && ./.venv/bin/python -m pytest tests/test_browser_network.py tests/test_ssrf.py -q` -> `98 passed in 0.58s` (baseline: `12 failed, 86 passed`)
2. `./.venv/bin/python -m pytest tests/test_adapters.py tests/test_security.py tests/test_live_regressions.py tests/test_live_discovery.py tests/test_live_extraction.py tests/test_metrics.py -q` -> `296 passed, 1 warning in 10.57s` (test_fetch.py does not exist in this tree)
3. `./.venv/bin/python -m mypy app tests` -> `Success: no issues found in 155 source files` (clean, no baseline comparison needed)
4. `./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m ruff format --check app tests` -> `All checks passed!` / `155 files already formatted`
5. Combined: `pytest tests/test_browser_network.py tests/test_ssrf.py tests/test_adapters.py tests/test_security.py tests/test_live_regressions.py tests/test_live_discovery.py tests/test_live_extraction.py tests/test_metrics.py` -> `394 passed, 1 warning in 10.90s`

Full-suite pytest --cov not run (dispatcher-owned slot). No network calls to real hosts; all tests offline.

## RED_TO_GREEN

- R1a `test_browser_error_page_is_not_ok`: green — render() maps final-nav 404 to `HTTP_ERROR`, status 404 preserved, empty text.
- R1b `test_render_with_no_response_is_not_ok`: green — `goto()` returning None now yields `UNPARSEABLE` with diagnostic error, `status_code=None`, `ok is False`.
- R2 `test_error_rendering_is_not_escalated_or_cached`: green — `_maybe_render` refuses any rendered result with `status_code >= 400` even if `outcome=OK`, so the error page is neither returned as the fetch of record nor written to the cache (original 200 stands, already cached pre-escalation).
- R3 `test_redirect_hop_response_is_closed`: green — 302 hop's streamed response is `aclose()`d before following the Location (also on the missing-Location path).
- R4a `test_browser_infra_failure_is_a_result_not_a_crash`: green — the `_maybe_render` call in `get()`'s else-branch is wrapped; a raising renderer becomes a non-OK `UNPARSEABLE` `FetchResult` with diagnostic.
- R4b `test_render_infra_exception_does_not_crash_the_fetcher`: green — `new_context`/`route`/`new_page` are inside a try; `BrowserFetcher.render` returns a non-OK diagnostic result instead of raising.
- R5 `test_as112_and_6to4_ranges_are_blocked` (4 addrs) + `test_6to4_relay_and_as112_urls_are_refused` (2 addrs): green — the four ranges added to `_EXTRA_BLOCKED`.
- R6 negative controls + test_ssrf.py TestErrorStatusesAreErrors (3): remained green throughout (no HTTP-tier behavior change).

## DESIGN_NOTES

- Both defensive layers of the contract implemented independently, per QA note: browser.py fixes the produced shape; the fetching.py escalation guard and infra containment hold even against a renderer with the old buggy shape.
- Infra-failure remedy is a diagnostic non-OK result, not fallback to the original thin HTTP 200 — this is what the frozen R4a assertion requires (`result.ok is False`).
- The OK return in browser.py now sits inside the `async with self._lock` block (needed for scope); functionally equivalent, lock still released promptly.
- Optional to_thread DNS change for `is_allowed` NOT taken: it is sync public API (changing to async would not be additive) and remains a documented residual.
- No new FetchOutcome members, no migrations, no conftest/test edits, network_policy API additive-only.

## RESIDUALS (documented in SECURITY.md)

- Chromium resolves DNS and connects itself after the route-gate check — rebinding TOCTOU remains; needs network-level egress enforcement for guarantees.
- Browser-internal redirects are not bounded by MAX_REDIRECTS (application layer bounds only its own manual loop).
- `_BLOCKED_HOSTNAMES` is deliberately short, not exhaustive.
- Sync `socket.getaddrinfo` in `is_allowed` still runs on the event loop (browser tier only).
- Retry-After still ignored (pre-existing documented limitation, out of scope).

## BLOCKERS

None.

## NEXT_ACTION

Hand CANDIDATE_SHA 28d729ca76cdf8d52344517a8316e2e805099d11 to independent QA verification and reviewer; independent QA/review NOT yet performed by me.
