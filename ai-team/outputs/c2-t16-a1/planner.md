# T16 A1 — Planner contract (frozen)

- Invocation ref: agent_355f9f0a-100f-4732-aa1a-b590c01b885b
- Baseline checked: 4d2125c00e2a320d6f6c31a79600bf97237ce218
- STATUS: PLANNED

## Findings vs code on 4d2125c (per H02 sub-finding)

- **S1 STILL OPEN** — browser.py:51,62,129-131: Chromium does its own DNS resolution + connection after `is_allowed` gate (network_policy.py:144-153 resolving via blocking `socket.getaddrinfo` in async handler); HTTP tier pinned (fetching.py:63-81, test_ssrf.py:239-263) but nothing transfers to Chromium → rebinding TOCTOU. SECURITY.md:120-123 documents residual honestly, no mitigation.
- **S2 MOSTLY FIXED, gaps open** — network_policy.py:27-141 (ranges, hostname blocklist, IPv4-mapped unwrap, per-address validation), fetching.py:339-380 per-hop redirect revalidation, 472-476 no auto-follow. Open: browser redirects gated only per-request (same TOCTOU), MAX_REDIRECTS not applied in browser, browser.py:149 reports final_url=url (landing URL never recorded); 6to4 192.88.99.0/24 + AS112 192.31.196.0/24, 192.52.193.0/24, 192.175.48.0/24 absent from _EXTRA_BLOCKED.
- **S3 PARTIALLY FIXED** — pre-nav BLOCKED (browser.py:83-87), per-request abort (63-66). Open: (a) browser.py:141-150 returns OK regardless of HTTP status; :134 resp is None → OK with status_code=None (fail-open on status); (b) browser-infra exceptions (browser.py:107-125 outside inner try) escape via fetching.py:619 else-branch not covered by :604-613 excepts → crash instead of diagnostic FetchResult.
- **S4 MOSTLY FIXED, stream-leak open** — >=400 → HTTP_ERROR + body closed (fetching.py:384-392), content-type allowlist, length caps, aclose on terminal paths, 429/5xx bounded retry, MAX_REDIRECTS=5. Open: redirect-hop responses never closed (fetching.py:358-371 `continue` without aclose → one leaked stream per hop); Retry-After ignored (documented limitation); no explicit 403/404/429 unit tests (justified-GREEN additions).
- **S5 OPEN in browser tier** — error pages become VERIFIED claims: browser.py:141-150 rendered 404/403/429/5xx → OK; fetching.py:459 escalation accepts on rendered.ok; :463 cached as OK; ClaimBuilder (extraction.py:147-162) grants VERIFIED_CURRENT with no fetch-status check. Strongest still-reproducing defect. HTTP tier fixed (ok=False on errors; guards web_requirements.py:92, live_discovery.py:602).
- **Scope-adjacent (NOT T16):** find_pii only at fetching.py:548, not on hops → T28.

## Frozen contract (abridged — full text in invocation)

- Acceptance: (1) controlled forbidden destinations BLOCKED/abort offline-proven; (2) 404/403/429/redirect/body limits correct — HTTP tier keeps behavior + explicit tests, browser tier maps non-2xx nav to non-OK, hop streams closed; (3) SECURITY.md honest residual/infrastructure-boundary documentation, no "fully SSRF-proof".
- Frozen semantics: FetchOutcome members unchanged; network_policy public API frozen additive-only; FetchResult fields unchanged; nav >=400 → HTTP_ERROR w/ status preserved + empty text; resp None → non-OK UNPARSEABLE w/ diagnostic; browser-infra failure → non-OK FetchResult, never raises; gate stays as T29 hook; pinning improvements allowed if offline-testable and documented best-effort.
- allowed_paths confirmed: browser.py, fetching.py, network_policy.py, test_ssrf.py, new test_fetch*/test_browser* files (QA target test_browser_network.py), SECURITY.md. test_live_regressions.py NOT in scope.
- No conftest.py edits; local fixtures, monkeypatched fake Playwright; tests run without Chromium.
- QA RED scenarios: R1 browser_error_page_is_not_ok (browser.py:141-150); R2 error_rendering_is_not_escalated_or_cached (fetching.py:459-464); R3 redirect_hop_response_is_closed (fetching.py:360-371); R4 browser_infra_failure_is_a_result_not_a_crash (fetching.py:619); R5 as112_and_6to4_ranges_are_blocked (network_policy.py:27-37); R6 route-gate negative control (justified GREEN). Plus justified-GREEN: HTTP 403/404/429 explicit tests in test_ssrf.py.
- Non-goals: no find_pii on hops (T28, leave loop shape), no search/LLM, no live external requests, no infra changes, no weakening robots/rate-limit/PII/coverage, no conftest/test_api/test_pipeline edits, no new FetchOutcome members, no migrations.
- Migration impact: none. Consumers: T28 (redirect loop shape preserved), T29 (route gate hook), T30 (network_policy API frozen).
- Residual risks for security review: TOCTOU remains without network-level egress enforcement (documented, not deployed); sync DNS in event loop (optional to_thread fix); hostname blocklist not exhaustive; browser-internal redirects unbounded by MAX_REDIRECTS; all "not reached" claims are offline-test claims.
