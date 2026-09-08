# qa-verify-candidate.md — T29 A1 (+A2 amendment), campaign c2, phase VERIFY_CANDIDATE

- ROLE_PHASE: ashyq-qa / VERIFY_CANDIDATE
- STATUS: VERIFIED_PASS
- DATE: 2026-09-08
- Worktree: /Users/wpalish/ashyq-worktrees/c2-t29-verify (branch ai/c2/t29/verify), read-only — no file modified; tree clean before and after all gates.

## CHECKED_SHA

- HEAD: ff6a90e3330c6040bfce02c63c6f8c163398d914 == frozen candidate (verified `git rev-parse HEAD`)
- Branch: ai/c2/t29/verify; `git status --porcelain` empty (verified again after all gates)
- Chain: 2ed4f51 (baseline) -> 7585b57 (QA RED) -> 6ae2799 (dev impl) -> ff6a90e (QA amendment).
  `git rev-list --parents -3 HEAD`: every commit single-parent; `rev-list --count 2ed4f51..HEAD` = 3. Linear, exactly 3 commits.

## SCOPE_CHECK (per commit)

- 2ed4f51..7585b57 (QA RED): A tests/fixtures/live_shapes/js_catalog_payload.json, js_catalog_shell.html, js_catalog_unrelated.json; M backend/tests/test_live_discovery.py PURELY ADDITIVE — 703 insertions, the only `-` line in the diff is the `--- a/` header. No pre-existing test modified or deleted.
- 7585b57..6ae2799 (dev impl): exactly M backend/app/adapters/browser.py, A backend/app/adapters/discovery/catalog_walker.py, M backend/app/adapters/discovery/live_discovery.py. Nothing else.
- 6ae2799..ff6a90e (amendment): exactly M backend/tests/test_live_discovery.py, +1/−1 (the `*anchors: tuple[str, str]` annotation).
- `git diff 7585b57..HEAD -- backend/tests/test_live_discovery.py` = ONLY the 1-line signature hunk. Zero assertion/test-logic changes.
- Whole-chain guard `git diff --name-only 2ed4f51..HEAD | grep -E "runner\.py|models/|migrations|config\.py|fetching\.py|domain/|page_classifier"` → NONE. page_classifier legitimately untouched (justified-GREEN pin intact).

## ANTI_WEAKENING_CHECK

- browser.py vs baseline: exactly TWO non-additive lines, both R1-approved: (1) `render` gains keyword-only `response_listener=None`; (2) settle block `try wait_for_load_state("networkidle", 8000) except (AttributeError, PlaywrightError) -> wait_for_timeout(1200)`. Everything else pure addition. Robots gate, route gate, PII assert, status mapping (>=400 -> HTTP_ERROR, None -> UNPARSEABLE), dialog dismissal, context hardening: byte-identical (absent from diff). Listener handler caps at MAX_LISTENED_RESPONSES=20 / 1MB, reads bodies inside try while the context is open, swallows read and listener failures with log.info.
- catalog_walker.py (NEW, read in full): WALKER_TOP_N=20, WALKER_MAX_CATALOGS=2, MIN_LABEL_CHARS=10, REPEATING_LIST_MIN_SIBLINGS=5; weights +5 DEGREE_MARKER / +4 SUBJECT_DEGREE / +8 FIELD_TEXT (dominates) / +2 REPEATING; DEGREE_MARKERS derived from live_discovery._DEGREE_SLUGS (bachelor/master/phd/foundation). same_institution enforced in extract_links AND for JSON entries. parse_catalog_json: json.loads wrapped, depth<=4, entries<=200, bad payload -> [] (HTML fallback). score_link None = hard reject (excluded_url / short_label / names_other_degree_level). CatalogRenderer subclasses BrowserFetcher, overrides render via response_listener, stash cleared in place; no playwright import in walker; `from app.adapters.browser import BrowserFetcher` is the contract-accepted import. Outcome vocabulary matches the frozen set (note: `field_mismatch` never emitted — walker calls profile_rejects with fields=[] per developer DESIGN_NOTE 2; tests authoritative).
- live_discovery.py: profile_rejects factors the former :802-816 block with byte-identical reject strings and identical check order (page_type -> degree_level -> fields); _confirm_programs behavior-preserving. Walker triggered ONLY when `len(selected[PROGRAM_PAGE]) >= MAX_PAGES_PER_CATEGORY (=3, unchanged)` returns early; top WALKER_MAX_CATALOGS catalogues; homepage-as-last-root only when fallback ran and no catalogue found. trace.walker additive (TypedDict, zeros when inactive), as_dict gains "walker"; caps 200/200. walker_outcomes (PageOutcome category="catalog-walker") reset beside self.traces. page_recorder keyword-only default None; walker failures swallowed to trace.errors.
- Demo byte-identity: fixture_discovery.py and runner.py untouched; runner.py:377/859 construct `LiveDiscoveryAdapter(fetcher)` with NO page_recorder; CatalogRenderer constructed nowhere in app/ (tests only); CatalogWalker constructed only inside _walk_catalogs. Recording fully dormant.

## GATES (all re-run by me, cwd /Users/wpalish/ashyq-worktrees/c2-t29-verify/backend, ./.venv/bin/python, no extra flags)

| Gate | Command | Result | Exit |
|---|---|---|---|
| a | `python -m pytest tests/test_live_discovery.py` | 124 passed in 4.86s | 0 |
| b | `python -m pytest tests/test_browser_network.py tests/test_ssrf.py` | 98 passed in 0.66s | 0 |
| c | `python -m pytest tests/test_adapters.py tests/test_live_extraction.py tests/test_live_regressions.py tests/test_source_pages.py tests/test_pipeline.py` | 194 passed in 21.76s | 0 |
| d | `python -m mypy app tests` | Success: no issues found in 161 source files (pre-existing annotation-unchecked notes only) | 0 |
| e1 | `python -m ruff check app tests` | All checks passed! | 0 |
| e2 | `python -m ruff format --check app tests` | 161 files already formatted | 0 |

Cross-checks: QA RED log (qa-test-live-discovery-baseline.log) ends "10 failed, 114 passed" — RED genuine, count arithmetic consistent (112 pre-existing + 2 baseline-green new = 114; 112 + 12 new = 124 now). Amendment's before/after mypy claim (3 errors -> 0) consistent with gate d at HEAD.

## ADVERSARIAL_NOTES

1. Double-fetch: _read_catalogue uses render XOR get for the catalogue page; a second fetch happens only when render raises or returns not-ok (already-failing case). Walker leads re-fetch URLs the fallback may have fetched — cache hits (fetcher caches). Worst case per institution: 2 renders + 20 fetches.
2. Scoring gaming: link farms bounded by MAX_LINKS_SCANNED=400 scan cap, hard rejects (short_label/excluded_url), TOP_N=20 fetch cap, sort (-score, len(url)) puts zero-score farms last; repeating bonus only +2 vs +8 field-text. Acceptable.
3. Memory: <=20 responses x 1MB per render; `collected` is local to render; catalog_payloads stash cleared in place at each render start. Bounded.
4. Recording dormancy: no production path constructs a recorder or CatalogRenderer; _record gates on `page_recorder is None or result.status_code is None` (robots/PII/timeout refusals produce no row); recorder exceptions swallowed with log.warning.
5. networkidle fallback on real Chromium NOT exercised (offline doubles only; no live browser/network in this environment). The AttributeError arm exists for test doubles; on a real page only PlaywrightError should fire. Residual risk for the wiring attempt.
6. `field_mismatch` frozen-vocabulary string is currently unreachable (walker passes fields=[]); vocabulary kept intact for T30 — documented deviation, tests authoritative.
7. parse_catalog_json is not fuzzed against hostile canonical_url/urljoin inputs (low risk, pure and bounded); no security exposure (same-domain gate applies before any fetch).

## BLOCKERS

None.

## NEXT_ACTION

Candidate ff6a90e3330c6040bfce02c63c6f8c163398d914 verified; hand to reviewer/integrator. R2 wiring attempt (runner.py page_recorder pass + CatalogRenderer construction) remains dispatcher-tracked for after T32; T30 must not run before wiring lands.
