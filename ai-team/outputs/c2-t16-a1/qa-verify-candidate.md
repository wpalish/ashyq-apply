# T16 A1 — QA VERIFY_CANDIDATE report (ashyq-qa)

- ROLE_PHASE: VERIFY_CANDIDATE
- STATUS: VERIFIED_PASS
- CHECKED_SHA: `28d729ca76cdf8d52344517a8316e2e805099d11` (`git rev-parse HEAD` on branch `ai/c2/t16/verify`; `git status --porcelain` empty before and after verification)
- Worktree: `/Users/wpalish/ashyq-worktrees/c2-t16-verify` (read-only; only pytest caches written)
- Ancestry verified: `4d2125c` (baseline) → `65e63ec` (QA RED) → `28d729c` (candidate), single commit on top of the QA commit (`fix: T16 H02 browser/egress hardening — error pages fail closed, hop streams closed, AS112/6to4 blocked`).

## SCOPE_CHECK — CLEAN

`git diff 65e63ec..HEAD --stat` → exactly 4 files:
```
 SECURITY.md                            | 29 +++++++++---
 backend/app/adapters/browser.py        | 80 ++++++++++++++++++++++++----------
 backend/app/adapters/fetching.py       | 31 ++++++++++++-
 backend/app/adapters/network_policy.py |  4 ++
```
`git diff 65e63ec..HEAD -- backend/tests/` → EMPTY (QA tests byte-identical to the QA commit; combined with clean status this also means the working-tree test files are byte-identical). `--name-only` confirms no other files touched. No conftest/test_api/test_pipeline edits, no migrations, no new FetchOutcome members (`app/domain/enums.py` FetchOutcome identical between 65e63ec and HEAD — compared byte-for-byte).

## ANTI_WEAKENING_CHECK — CLEAN

Production code read directly at the candidate, not trusted from reports:

1. browser.py: pre-nav `check_url` BLOCKED path intact; `_gate_request` unchanged (T29 hook); robots gate intact; `assert_no_pii(url)` intact; `new_context` hardening flags unchanged (no downloads, service_workers blocked). New: context-setup exceptions → non-OK UNPARSEABLE diagnostic; `resp is None` → UNPARSEABLE w/ diagnostic; `resp.status >= 400` → HTTP_ERROR with `status_code` preserved and empty text/content (FetchResult defaults `text=""`, `content=b""` verified); only a successful final nav returns OK.
2. fetching.py: escalation guard `if rendered.status_code is not None and rendered.status_code >= 400: return result` — refuses regardless of rendered outcome, error page can be neither the fetch of record nor `cache.put`; `_maybe_render` has exactly one call site (fetching.py:636) and it is the newly wrapped one (`except Exception` → UNPARSEABLE diagnostic, stats counted, never raises out of `get()`); redirect loop closes the streamed hop via `await response.aclose()` on BOTH paths (missing-Location before return, normal hop before continue) — the MAX_REDIRECTS-exhaustion path also closes its last hop (aclose runs before `continue`, before the loop falls out). Loop shape otherwise preserved for T28; `find_pii`, robots.allowed, `_space_requests` untouched by the diff.
3. network_policy.py: additive-only — 4 entries appended to private `_EXTRA_BLOCKED` (192.88.99.0/24 6to4 relay RFC 7526, 192.31.196.0/24, 192.52.193.0/24, 192.175.48.0/24 AS112); public API (check_url/is_allowed/is_blocked_address/BlockedRequest) untouched (T30).
4. SECURITY.md: no "fully SSRF-proof"/"immune"/"eliminates" phrasing (grep over the file: no hits); explicitly states "Guarantees therefore stop at the application boundary"; residuals documented match the code (rebinding window, unbounded browser-internal redirects, short hostname blocklist, firewall recommendation).

## GATES — all re-run by QA at the candidate SHA, real exit codes

1. `./.venv/bin/python -m pytest tests/test_browser_network.py tests/test_ssrf.py -q` → **exit 0**, 98 passed (14 + 84 items; 12 former REDs verified green individually by node id with `-o addopts="" -v`, incl. R1a, R1b, R2, R3, R4a, R4b, R5 ×6, plus 2 negative controls; test_ssrf.py 84 = 81 baseline + 3 TestErrorStatusesAreErrors, all green). Note: repo pytest.ini has `addopts = -q`; stacking a second `-q` suppresses the summary line (exit code + verbose runs used as evidence).
2. `./.venv/bin/python -m pytest tests/test_adapters.py tests/test_security.py tests/test_live_regressions.py tests/test_live_discovery.py tests/test_live_extraction.py tests/test_metrics.py -q` → **exit 0**, `296 passed, 1 warning in 11.93s`.
3. `./.venv/bin/python -m mypy app tests` → **exit 0**, `Success: no issues found in 155 source files`.
4. `./.venv/bin/python -m ruff check app tests` → **exit 0**, `All checks passed!`; `./.venv/bin/python -m ruff format --check app tests` → **exit 0**, `155 files already formatted`.

## BROADER PG-FREE SWEEP (within slot; no PostgreSQL suites started)

- `./.venv/bin/python -m pytest tests/ --co` → **exit 0**, `1170 tests collected in 0.40s`, 0 collection errors.
- Additional pg-free files chosen for relevance to the changed boundary: `tests/test_claims_and_conflicts.py` (ClaimBuilder consumes fetch outcomes), `tests/test_logging_and_correlation.py` (new log lines), `tests/test_apipay_adapter.py`, `tests/test_frontend_contract.py`, `tests/test_pipeline.py` (pg-free by grep; exercises runner.py:294 `attach_renderer` path) → **exit 0**, `97 passed in 14.49s`.
- Verified none of the executed files request `pg_engine`/`pg_session`/`postgres_url` (grep = 0 hits in every executed file; the `alembic_version` string in test_live_regressions.py:756 runs against a non-pg engine — the 11.9s run started no PostgreSQL).

## DEFERRED (and why)

- 11 pg-dependent files NOT run: test_billing_models.py, test_grant_subscription_cli.py, test_entitlements.py, test_jobs.py, test_payment_service.py, test_payment_reconcile.py, test_subscription_reads.py, test_social_models.py, test_worker.py, test_subscription_models.py, test_subscription_consume.py (all request pg fixtures; dispatcher owns the heavy slot). None import the changed adapter modules' changed behavior directly; the fetch-boundary suites above cover the changed code.
- Full-suite `pytest --cov` and E2E not run (dispatcher slot / ports), per instructions.

## ADVERSARIAL_NOTES (non-blocking)

1. The fetching-layer escalation guard keys on `rendered.status_code`; a hypothetical future renderer regressing to the R1b shape (OK + `status_code=None` + error-page text) would NOT be refused at the fetching layer — resp-None defense lives only in browser.py. This matches the frozen contract (R2 pinned at fetching, R1b pinned at browser), but it is single-layer defense for that one shape.
2. browser.py `page.on("dialog", ...)` sits outside any try; if registration ever raised, the context would leak (exception still contained at get()-level). Unchanged exposure vs baseline; negligible.
3. If `context.close()` in the `finally` raises (dead browser), it propagates out of `render()` (chained) but is caught by the new get()-level wrapper — containment holds at the fetcher boundary, not inside `render()` for that edge. R4b pins only new_context/route/new_page failures.
4. A final navigation landing on 3xx would be treated as OK; unreachable in practice via goto's internal redirect-following. Not a defect.
5. Documented residuals stand (not fixed, not claimed): S1 rebinding TOCTOU, browser-internal redirects unbounded by MAX_REDIRECTS, `final_url` still records the requested URL not the landing URL, sync DNS on the event loop, Retry-After ignored. SECURITY.md documents all of these honestly.
6. Unresolved independence caveat per TEAM_RULES: this QA verification is a separate invocation, but reviewer/security review of this candidate is not part of what I can attest; QA cannot grant final merge approval.

## VERDICT

**VERIFIED_PASS** — all four gates green at `28d729ca76cdf8d52344517a8316e2e805099d11`; production scope exactly the 4 agreed files; QA tests byte-identical to `65e63ec` (zero weakening); frozen semantics verified in source (nav >=400 → HTTP_ERROR w/ status + empty text; goto None → non-OK UNPARSEABLE w/ diagnostic; escalation guard refuses >=400 regardless of outcome; hop streams closed on all redirect paths incl. exhaustion; browser-infra failures contained at both layers; 4 new ranges in `_EXTRA_BLOCKED`; no new FetchOutcome members; robots/rate-limit/PII paths untouched); SECURITY.md residual documentation honest and consistent with the diff.
