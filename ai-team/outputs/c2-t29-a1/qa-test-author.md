# qa-test-author.md — T29 A1 (campaign c2), role ashyq-qa, phase TEST_AUTHOR

- ROLE_PHASE: TEST_AUTHOR
- STATUS: TESTS_READY
- Worktree: /Users/wpalish/ashyq-worktrees/c2-t29-qa (branch ai/c2/t29/qa)
- Baseline verified: `git rev-parse HEAD` == 2ed4f51e1d5c1fae3f4cb36ad64982eb67184a2d before any edit; tree was clean.
- QA commit: 7585b575e76e9887b3294d8a03ad0506131d4b86 (parent == baseline, verified). No push. No production edits.
- Contract: /Users/wpalish/ashyq-apply/ai-team/outputs/c2-t29-a1/planner.md (read in full). AGENTS.md and ai-team/TEAM_RULES.md read.

## FILES_CREATED_OR_MODIFIED (all in the QA worktree)

- backend/tests/test_live_discovery.py — appended class `TestCatalogWalkerContract` (R1-R10 + 2 justified-GREEN pins) + file-local browser doubles (WalkerFakePage/WalkerFakeBrowser/FakeJsResponse, pattern copied from test_browser_network.py, not imported). Existing tests untouched (diff = 703 insertions, 0 deletions/modifications).
- backend/tests/fixtures/live_shapes/js_catalog_payload.json — NEW ({name,url} array, pattern-free /p/N urls)
- backend/tests/fixtures/live_shapes/js_catalog_shell.html — NEW (plural-catalogue-titled JS shell)
- backend/tests/fixtures/live_shapes/js_catalog_unrelated.json — NEW (JSON with no {name,url} arrays)

Not touched: conftest.py, test_source_pages.py, test_browser_network.py, any app/** file, anything in T32 scope.

## COMMANDS (real, run in /Users/wpalish/ashyq-worktrees/c2-t29-qa/backend)

1. `./.venv/bin/python -m ruff format tests/test_live_discovery.py && ./.venv/bin/python -m ruff check tests/test_live_discovery.py` — 1 file reformatted, then I001 fixed via `ruff check --fix`; final `ruff format --check` clean.
2. `./.venv/bin/python -m pytest tests/test_live_discovery.py` → EXIT_CODE=1 — **10 failed, 114 passed** (all 10 failures are the new R-scenarios; all pre-existing tests green).
3. `./.venv/bin/python -m pytest tests/test_browser_network.py` → EXIT_CODE=0 — 14 passed (T16 negative controls unharmed).
4. `./.venv/bin/python -m pytest tests/test_source_pages.py` → EXIT_CODE=0 — 8 passed (incl. PG scenarios via pgserver).

Logs: qa-test-live-discovery-baseline.log, qa-test-browser-network-collateral.log, qa-test-source-pages-collateral.log (this directory).

## RED_RESULTS (per scenario, observed modes from the real run)

| Scenario | Test | Observed RED mode (baseline) |
|---|---|---|
| R1 walker_extracts_scored_links | test_r1_walker_extracts_scored_links | ImportError: `ModuleNotFoundError: No module named 'app.adapters.discovery.catalog_walker'` (accepted new-module pattern) |
| R2 each_link_fetched_with_outcome | test_r2_each_link_fetched_with_outcome | AttributeError: `'DiscoveryTrace' object has no attribute 'walker'` (new trace key) |
| R3 profile_predicate_reused | test_r3_profile_predicate_reused | AttributeError: no attribute 'walker' (new trace key); the confirm-stage "degree level master" rejection and the label-text confirmation already pass and are pinned as justified-GREEN sub-assertions |
| R4 off_domain_never_fetched | test_r4_off_domain_never_fetched | AttributeError: no attribute 'walker'; the never-fetched/never-offered sub-assertions pass on baseline (justified-GREEN pin of the same-domain boundary) |
| R5 js_json_payload_yields_programs | test_r5_js_json_payload_yields_programs | ImportError: catalog_walker absent (`_js_catalog_renderer`, test file line 1254) |
| R6 js_unrelated_json_falls_through | test_r6_js_unrelated_json_falls_through | ImportError: catalog_walker absent; the HTML-fallback programme confirmation passes on baseline (justified-GREEN sub-pin) |
| R7 js_silent_shell_is_recorded_not_fatal | test_r7_js_silent_shell_is_recorded_not_fatal | ImportError: catalog_walker absent |
| R8 source_pages_rows_recorded | test_r8_source_pages_rows_recorded | TypeError: `LiveDiscoveryAdapter.__init__() got an unexpected keyword argument 'page_recorder'` |
| R9 top_n_budget | test_r9_top_n_budget | ImportError: catalog_walker (WALKER_TOP_N import) |
| R10 no_catalog_byte_identical | test_r10_no_catalog_byte_identical | KeyError: 'walker' on `as_dict()` |

## GREEN_RESULTS (justified, marked per T27 pattern)

- test_justified_green_titled_js_shell_is_a_catalogue — GREEN on baseline by design: js_catalog_shell.html (title "Bachelor's programmes | University") classifies PROGRAM_CATALOG via page_classifier.py:341-348 + title fallback :471-477. Pinned so the JS tier starts from a catalogue the classifier already recognises.
- test_r10_demo_invariant — GREEN on baseline (trivially: no walker exists); pins that the demo FixtureDiscoveryAdapter never requests a university URL and carries no walker_outcomes surface, so wiring cannot silently change demo.
- In-test justified-GREEN sub-pins: R3 (confirm-stage degree-level rejection reason), R4 (off-domain never fetched/offered), R6 (plain HTML links already confirm through the navigation fallback), R10a (walker-inactive request set + all pre-existing trace keys keep baseline values).

## DIVERGENCE NOTE (honest, for the dispatcher/developer)

The contract predicted R5-R7 to RED as "no interception happened (empty program list)". Observed mode is ImportError instead: constructing the contract's CatalogRenderer is a precondition of those scenarios, so on a baseline without catalog_walker the lazy import fails before any assertion can run. The predicted mode becomes observable only after the module exists. The "nothing invented / no crash / shell explained" halves of R5-R7 are fully asserted and will exercise the JS tier post-fix; R5/R6/R7 additionally pin their baseline-still-true halves. R8's observed mode is TypeError (new keyword), the analogue of the predicted new-kwarg bucket.

Signature assumptions (minimal, from the contract surface; adjustable via a test-contract change if the walker needs more): `extract_links(html, base_url, domain)`, `score_link(url, label, degree, fields)` (repeating-list bonus assumed to be applied by walk_catalog, not by this pure call), `CatalogRenderer(fetcher)` mirroring `BrowserFetcher(fetcher)`, walker renderer discovered via the existing `Fetcher.attach_renderer` seam (`fetcher._renderer`), "no renderer → HTTP HTML only".

## UNTESTED_RISKS / NOT_RUN

- runner.py wiring (both seams), browser.py render(response_listener=...) live behaviour, networkidle settle, response caps (20/1MB), robots/PII gates on the JS tier: deferred by contract (R1 approval is for the developer branch; A1 has no browser.py change on the QA baseline) — these need VERIFY_CANDIDATE once the candidate exists.
- walker_outcomes PageOutcome field mapping (which of page_type/detail carries the frozen outcome string) is asserted loosely (value appears in page_type or detail) because the contract does not pin it.
- trace.walker["candidates"] item shape asserted only via list length/keys at container level (not pinned by the contract).
- Full pytest suite (coverage gate) and frontend gates NOT_RUN here: out of A1 scope; the affected suites were run per contract.

## NEXT_ACTION

Dispatcher hands the QA commit 7585b575e76e9887b3294d8a03ad0506131d4b86 to the developer as the base for the T29 implementation branch (catalog_walker.py + live_discovery seam + profile_rejects factor + browser.py response_listener per the approved R1). STATUS for the task ledger: TESTS_READY.
