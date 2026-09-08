# developer.md — T29 A1 (campaign c2), role ashyq-developer

- ROLE_PHASE: IMPLEMENT
- STATUS: IMPLEMENTED
- Worktree: /Users/wpalish/ashyq-worktrees/c2-t29-dev (branch ai/c2/t29/dev) — single writer, tree clean
- BASELINE_SHA (QA RED commit, base): 7585b575e76e9887b3294d8a03ad0506131d4b86 (parent == baseline 2ed4f51e1d5c1fae3f4cb36ad64982eb67184a2d, verified)
- CANDIDATE_SHA (frozen, handed to review): 6ae2799b77a7a0fb6a863249d3a79bee013ef83b
- Contract: planner.md (read in full; R1 APPROVED applied, R2 DEFERRED respected — runner.py untouched)
- QA report: qa-test-author.md (signatures implemented to match: extract_links(html,base_url,domain); score_link(url,label,degree,fields); CatalogRenderer(fetcher); renderer via fetcher._renderer)

## FILES_CREATED_OR_MODIFIED (all in the dev worktree, verified numstat vs QA commit)

- backend/app/adapters/discovery/catalog_walker.py — NEW, +531 (WALKER_TOP_N=20, WALKER_MAX_CATALOGS=2, WalkerLink, extract_links, parse_catalog_json, score_link, CatalogWalker.walk/walk_catalog, CatalogRenderer(BrowserFetcher), outcome vocabulary per contract)
- backend/app/adapters/discovery/live_discovery.py — +155 / -21 (profile_rejects factored from :802-816, _confirm_programs now calls it with byte-identical reject strings; DiscoveryTrace.walker TypedDict field + as_dict "walker" key; adapter page_recorder keyword-only default None + walker_outcomes reset beside traces; _walk_catalogs stage after _confirm_programs)
- backend/app/adapters/browser.py — +76 / -2 (R1 APPROVED: render(*, response_listener=None) additive; JSON response collection capped 20 x 1MB, bodies read in-handler before context.close(), listener failures swallowed; networkidle settle attempt (8s) with fallback to the existing wait_for_timeout(1200); all T16 gates byte-identical)

Not touched: runner.py (R2 deferred), models, migrations, jobs, schemas, config, fetching.py, domain, fixture_discovery.py, page_classifier.py (justified-GREEN pin verified: the JS shell already classifies PROGRAM_CATALOG), any test file, any fixture.

## GATES (real runs in /Users/wpalish/ashyq-worktrees/c2-t29-dev/backend)

a. `./.venv/bin/python -m pytest tests/test_live_discovery.py` → **124 passed** (10 former REDs green; 114 pre-existing untouched-green)
b. `./.venv/bin/python -m pytest tests/test_browser_network.py tests/test_ssrf.py` → **98 passed** (T16 negative controls green)
c. `./.venv/bin/python -m pytest tests/test_adapters.py tests/test_live_extraction.py tests/test_live_regressions.py` → **158 passed**
d. `./.venv/bin/python -m mypy app tests` → **3 errors, all pre-existing at the QA commit, all in the frozen test helper `_catalogue_html` (tests/test_live_discovery.py:1264, `*anchors: str` unpacked as pairs)** — proven by running mypy on the pristine QA commit in a throwaway worktree (same 3 errors); 0 errors from this candidate's app code. QA-side fix when convenient: annotate `*anchors: tuple[str, str]`.
e. `./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m ruff format --check app tests` → **clean**

Collateral (beyond the required gates): `pytest tests/test_source_pages.py tests/test_pipeline.py` → 36 passed; full non-API suite `pytest tests --ignore=tests/{test_social_api,test_api,test_worker,test_security,test_citizenship_and_dates}.py` → **1107 passed, 0 failed** (demo pipeline path included).

## RED_TO_GREEN (per QA scenario)

- R1 walker_extracts_scored_links — GREEN (extract_links off-domain drop + WalkerLink.source; score_link +5/+4/+8/URL bonuses; news→excluded_url and "Ask us"→short_label hard-rejects as None)
- R2 each_link_fetched_with_outcome — GREEN (404→http_error, news→reads_as_news, BSc→program_detail; trace.walker + walker_outcomes category="catalog-walker"; programs == [bsc])
- R3 profile_predicate_reused — GREEN (MSc page → degree_level_mismatch via shared profile_rejects; label-named BSc confirmed; confirm-stage "degree level master" pin intact)
- R4 off_domain_never_fetched — GREEN (partner URL dropped in extract_links, outcome off_domain, never requested, never offered)
- R5 js_json_payload_yields_programs — GREEN (CatalogRenderer stash over FakeBrowser seam; {name,url} array parsed; /p/42 + /p/77 fetched and confirmed; catalogs_walked=1, programs_confirmed=2)
- R6 js_unrelated_json_falls_through — GREEN (array-less JSON invents nothing; HTML links drive; nothing fabricated)
- R7 js_silent_shell_is_recorded_not_fatal — GREEN (js_no_program_list outcome; discovery completes; programs == [])
- R8 source_pages_rows_recorded — GREEN (recorder receives exactly the 9 frozen kwargs; institution_key None; 404 row page_type "unknown"; short-label link never fetched/recorded)
- R9 top_n_budget — GREEN (30 candidates → exactly the top-20 fetched, student-support never requested)
- R10 no_catalog_byte_identical — GREEN (walker inactive: no extra fetches, walker zeros, all pre-existing trace keys baseline-equal); demo_invariant GREEN (FixtureDiscoveryAdapter branch untouched, no walker_outcomes surface)

## DESIGN_NOTES (deviations and rationale)

1. Homepage-as-last-root: R5-R7 have no catalogue URL anywhere (no sitemap, unreachable homepage over HTTP), so the walker walks entry["homepage"] when selected[PROGRAM_CATALOG] is empty AND used_navigation_fallback is True (the fallback already had its chance). The gate is required by R10 and by existing test_navigation_is_not_used_when_a_programme_page_was_found ("https://uni.edu/" must not be requested when a programme was found via sitemap). Verified against the pristine-QA baseline flow before implementing.
2. Walker confirm predicate = profile_rejects(page, degree, []) — page-type + degree-level only. The subject refinement is deliberately NOT re-applied: R5 requires the JSON payload's "BSc Mathematics" confirmed for a computer-science applicant (the payload is the university's own statement of its programmes; subject fit is judged downstream). Consequence: the frozen string "field_mismatch" is currently never emitted by the walker (same for "field_mismatch"-producing behavior; vocabulary kept intact for T30/reporting). This is the one place the frozen tests overrode a literal reading of the contract ("used by walker" with fields) — tests are authoritative, noted for reviewer.
3. catalog_walker imports app.adapters.browser (required to subclass BrowserFetcher per the contract's own CatalogRenderer(BrowserFetcher) surface). The contract's "NO browser import" is read as "no playwright/browser launch": the pure functions never touch it, and playwright itself is only imported lazily inside BrowserFetcher._ensure. live_discovery imports catalog_walker lazily (inside _walk_catalogs) so the import dependency stays one-way at module load.
4. extract_links mirrors _harvest_links semantics line-for-line (scan bound, scheme/domain gates, canonicalisation, label cleanup) rather than delegating, plus an optional `drops` keyword (frozen 3-arg calls unaffected) so R4's off_domain outcome can be reported. _harvest_links itself is byte-identical.
5. Not_program_catalog is emitted only for decisive non-catalogue classifications (NEWS, IRRELEVANT, admissions/costs/funding/documents families); UNKNOWN/NAVIGATION are ambiguous and stay silent. No test pins it.
6. Walker re-fetches already-confirmed leads rather than skipping (R9 counts on them in site.requested); real-world cost is nil because the fetcher caches.
7. Demo byte-identity: FixtureDiscoveryAdapter and runner.py untouched; CatalogWalker/CatalogRenderer are constructed only inside LiveDiscoveryAdapter._walk_catalogs (live adapter only); page_recorder defaults to None so recording is dormant until the R2 wiring attempt. Verified by test_pipeline + test_r10_demo_invariant.
8. Bug found and fixed during implementation: CatalogRenderer.render initially rebound catalog_payloads to a new list, so a walker holding the pre-render reference saw nothing (R5 failure); fixed to clear in place.
9. browser.py networkidle: except (AttributeError, PlaywrightError) — the AttributeError arm exists because both QA page doubles (test_browser_network.FakePage, WalkerFakePage) lack wait_for_load_state; on a real page only PlaywrightError fires.

## RESIDUALS

- The 3 pre-existing mypy errors in the frozen QA test helper (see gate d) — QA-owned fix, no behavior impact.
- runner.py wiring (both seams) remains deferred (R2): page_recorder dormant, CatalogRenderer constructed only in tests until wiring; T30 must not run before wiring lands (dispatcher-tracked).
- Live-Playwright behavior of the response listener (real Chromium event timing, caps under load) is offline-tested via doubles only; VERIFY_CANDIDATE may exercise it.
- walker trace "candidates" item shape is dict {url,label,score,source} — contract leaves the shape unpinned; T30 consumes it.

## NEXT_ACTION

Dispatcher: freeze CANDIDATE_SHA 6ae2799b77a7a0fb6a863249d3a79bee013ef83b and hand to independent QA VERIFY_CANDIDATE + reviewer. After T32 lands, run the dispatcher-tracked micro-wiring attempt for the two runner.py seams (page_recorder pass; CatalogRenderer construction) — acceptance items 4-5 are implemented+tested at adapter level only.
