# Two confirmed synthetic DNS seams — helper-only proposal

**PREPARED_NOT_EXECUTED.** This new packet copies the exact helper executed in the retained tracing receipt, then adds two exact native case tuples to its synthetic resolver map. It does not edit application source, native tests, assertions, dependencies, the original helpers or completed evidence.

## Retained result and diagnosis

`evidence/remaining-dns-trace/20261009T031157841755Z/result.json` reports **509 native tests, 0 failures/errors/skips**, with exactly two denied `socket.getaddrinfo` calls. The helper correctly returned **FOCUSED_DIAGNOSTIC_FAIL_NOT_FULL**. Source hashes were unchanged, child startup failures were empty, and shutdown/runtime removal were confirmed. PostgreSQL full phase remains **NOT_RUN**. Metadata and hashes are retained in `retained-trace-receipt-metadata.json`; no historical payload or assertion failure body was opened.

The two events are ordinary positive synthetic seams, rather than tests requesting a DNS failure:

| Exact native case | Source and injected seam | Contract retained |
| --- | --- | --- |
| `tests.test_live_regressions / TestBrowserTierIsReallyUsed / test_a_page_with_real_content_is_not_escalated` | `backend/tests/test_live_regressions.py:658–679`: fixed HTML at `https://uni.edu/static` through `_StubClient` (`:691`). Its `send` returns an in-memory response; `RecordingRenderer` raises if invoked. | The renderer must remain unused, and the result must have `fetch_tier == "http"`. The real URL policy currently reaches DNS before the stub response. |
| `tests.test_live_discovery / TestCatalogWalkerContract / test_r7_js_silent_shell_is_recorded_not_fatal` | `backend/tests/test_live_discovery.py:1665–1692`: `_js_catalog_renderer` (`:1320`) uses `WalkerFakeBrowser`/`WalkerFakePage`; `StubSite` replaces Fetcher transport. The fake browser only emits fixed responses. | Discovery completes with no programs, `js_no_program_list` recorded, and exactly one catalogue walked. URL policy currently reaches DNS before fake rendering. |

These are unchanged native tests. The prior two denial receipts are preserved and are not deleted or reclassified.

## Exact repair and unchanged floors

Only these two `(module, class, original function)` keys are added to `BROWSER_CASES`, with `uni.edu` as their sole host. The existing function-scoped fixture still requires port **443**, IPv4/unspecified family and TCP stream transport. Its fixed public answer is `93.184.216.34`; it performs no real DNS, request, browser navigation or socket operation. The original five API module mappings and four exact browser mappings remain unchanged.

The fixture ends through native pytest `monkeypatch` teardown. Other cases, hosts, ports and transports receive no new allowance. `unrelated.example` remains unlisted. Production SSRF/resolver code is unchanged. Global real DNS refusal, durable denial metadata, IP socket guards, inherited OS sandbox, child guards, shared non-truncating flock, strict private Unix PG endpoint checks and owned cleanup remain byte-identical.

`static-seam-proof.json` records stdlib AST comparison only: every plugin/launcher function is exact, the API map is exact, the four previous browser tuples are exact, and the other five Python helpers are byte-identical. All seven Python helper files parse. No test, import of a helper/application/driver, probe, server or gate was executed here.

## Root-reviewed diagnostic first

The fixed `--diagnostic` list in `bounded-diagnostic-targets.json` contains **21 selectors**:

- all 18 selectors of the prior clean focus, including the five API mock modules, synthetic child workflow, private PG migration/source controls, the four previous browser seams and `test_subject_phrase_guard.py`;
- both newly identified positive cases;
- `tests/test_browser_network.py::TestRouteGateNegativeControl::test_route_gate_blocks_metadata`, which is explicitly **absent** from `BROWSER_CASES` and keeps the cloud-metadata abort assertions.

This list is bounded at 300 seconds and retains all isolation, source and cleanup checks. It can only yield **FOCUSED_DIAGNOSTIC_PASS_NOT_FULL** or a failure. It has no coverage claim. Actual case count is pending execution.

Root may adopt `proposed/` into a fresh helper directory, verify its manifest and the unchanged `expected-native-source-pins.json`, and execute against the frozen external v3 source:

```text
<existing v3 backend Python> <new helper>/run_full_backend.py
  --source-root <v3>/source --output-root <v3>/evidence/remaining-dns-seam-fix
  --execute --diagnostic --phase-timeout 300
```

If that diagnostic is clean, the required **full mode remains unchanged**: all native `tests`, `--cov=app --cov-fail-under=92`, first SQLite then owned private Unix PostgreSQL. Both phases must satisfy zero failures/errors/skips, zero outside attempts/startup failures, unchanged source hashes and confirmed cleanup. No thresholds, exclusions or native assertions are weakened.

The earlier full SQLite receipt (4,515 passing tests, 95.4398894518655% coverage) remains **FAIL_OR_INCOMPLETE** because of those two denials; it is not promoted by this proposal. Both repaired full phases are **NOT_RUN**. Primary is unapplied/unreleased. Current search quality remains **NOT_MEASURED**; the closed `GLOBAL_PROVIDER_STOP` / `UNSCORED` pilot remains untouched.
