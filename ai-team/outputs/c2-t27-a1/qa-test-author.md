# T27 A1 — QA TEST_AUTHOR report

- ROLE_PHASE: TEST_AUTHOR (ashyq-qa, campaign c2, attempt A1)
- Worktree: /Users/wpalish/ashyq-worktrees/c2-t27-qa (branch ai/c2/t27/qa)
- BASELINE_SHA verified before work: 28d729ca76cdf8d52344517a8316e2e805099d11 (git rev-parse HEAD), tree clean
- QA_COMMIT_SHA: d8553e19cf7d5d5236c5f74b7ffc55f436d66a00 (parent = baseline; 5 files, 712 insertions, 0 deletions; no push)
- Venv: /Users/wpalish/ashyq-worktrees/c2-t27-qa/backend/.venv; offline only (monkeypatched Fetcher per existing harness). Note: pytest.ini sets addopts=-q; no extra -q passed anywhere.

## FILES_CREATED_OR_MODIFIED

- NEW backend/tests/fixtures/live_shapes/requirements_fee_waiver_negation.html (GENERAL_ADMISSIONS-shaped; verified classify_page -> general_admissions)
- NEW backend/tests/fixtures/live_shapes/costs_application_fee_trap.html (COSTS-shaped; verified classify_page -> costs; empirically tuned so the 120-char tuition window swallows "$50 application fee" — probe showed TUITION = {'amount': 50.0, 'currency': 'USD'} on baseline)
- NEW backend/tests/fixtures/live_shapes/requirements_attacker_spoofed_domain.html (minimal GENERAL_ADMISSIONS page for the spoofed-domain scenario; verified classification)
- MODIFIED backend/tests/test_live_regressions.py (append-only, +223 lines: helpers _verify_page/_fetch_cost_page reusing the existing _serve harness; classes TestFeeWaiverNegation, TestApplicationFeeSwallowedByTuitionWindow, TestSpoofedOfficialDomain)
- NEW backend/tests/test_claim_verifier.py (contract tests against the frozen API; 455 lines)

Production code untouched. No fetching.py/models/migrations files touched (T28 scope). No conftest/test_api/test_pipeline/test_ssrf/test_fetch edits.

## RED_RESULTS (baseline 28d729c, per scenario)

Command: cd backend && ./.venv/bin/python -m pytest tests/test_live_regressions.py --no-header -p no:cacheprovider -rf
Exit: 1 — "7 failed, 64 passed in 1.39s" (log: /tmp/t27probe/red_live_final.log)

| # | Test | Defect (file:line) | Actual failure snippet |
|---|------|--------------------|------------------------|
| R1a | TestFeeWaiverNegation::test_an_explicit_negation_is_never_a_waiver_yes | app/adapters/requirements/web_requirements.py:312-314 (any "fee waiver" line -> True) | `AssertionError: the page says "Fee waivers are not available"; claiming True is the opposite of the page: [True]` |
| R1b | TestFeeWaiverNegation::test_an_indeterminate_waiver_mention_yields_no_claim | web_requirements.py:312-314 | `AssertionError: an indeterminate 'fee waiver' mention must not become a claim at all, let alone True: [True]` |
| R2a | TestApplicationFeeSwallowedByTuitionWindow::test_the_cost_adapter_never_reads_the_fee_as_tuition | app/adapters/extraction.py:475-482 (extract_costs, first money in 120-char label window; _MONEY \d{2,7} at extraction.py:211-216) | `AssertionError: the $50 application fee inside the tuition label's window was read as tuition: [{'amount': 50.0, 'currency': 'USD'}]` |
| R2b | TestApplicationFeeSwallowedByTuitionWindow::test_extract_costs_itself_ignores_the_small_fee | extraction.py:456-491 (extract_costs seam the fix lands on) | `AssertionError: extract_costs attached the application fee to tuition: [{'amount': 50.0, 'currency': 'USD'}]` |
| R3a | TestSpoofedOfficialDomain::test_a_query_parameter_is_not_the_page_host | app/adapters/extraction.py:96-103 (substring over URL string) | `AssertionError: narxoz.kz inside ?u= is a URL substring, not the page's host` / `assert True is False` |
| R3b | TestSpoofedOfficialDomain::test_a_subdomain_of_an_attacker_domain_is_not_the_university | extraction.py:96-103 | `AssertionError: narxoz.kz.attacker.example is a host owned by attacker.example` / `assert True is False` |
| R3c | TestSpoofedOfficialDomain::test_a_page_served_from_an_attacker_url_is_never_verified_current | extraction.py:96-103 feeding the ClaimBuilder gate extraction.py:147-162 | `AssertionError: a page served from attacker.example must not publish VERIFIED_CURRENT claims: [(<ClaimType.IELTS_MIN_OVERALL ... 6.5), (<ClaimType.IELTS_ACCEPTED_TYPES ... ['academic'])]` |

All R1/R2/R3 REDs are assertion failures (defect reproduced through the real adapter path, monkeypatched Fetcher, no network). None is an import or environment error.

test_claim_verifier.py: cd backend && ./.venv/bin/python -m pytest tests/test_claim_verifier.py
Exit: 2 — `ModuleNotFoundError: No module named 'app.domain.claim_verifier'` at tests/test_claim_verifier.py:42 during collection. Import failure is the ONLY reason it is red: the whole file is written against the exact frozen API (verify_claim/VerificationInput/Verdict/RejectReason/normalize_text/is_verbatim_excerpt/value_in_range/url_matches_domains/registrable_domain/page_type_admits). No shim, no fake green. Log: /tmp/t27probe/red_claim_verifier.log

Combined packet command (both files at once) on baseline: exit 2, interrupted at collection of test_claim_verifier.py — expected; per-file runs above are the authoritative per-scenario evidence. Log: /tmp/t27probe/red_final.log

## GREEN_RESULTS (justified, on baseline)

Inside test_live_regressions.py (part of the 64 passed):
- TestFeeWaiverNegation::test_the_application_fee_on_the_same_page_is_still_claimed — pins APPLICATION_FEE {"amount": 50.0, "currency": "USD"} from the fee line; guards against the fix overreaching into the 2-digit application-fee path (contract: APPLICATION_FEE keeps 2-digit).
- TestApplicationFeeSwallowedByTuitionWindow::test_a_genuine_tuition_figure_on_the_same_page_still_reads — TUITION 4500.0 still read after removing the trap sentence; guards against "suppress all tuition" fixes.
- TestSpoofedOfficialDomain::test_the_real_host_and_www_stay_official — narxoz.kz and www.narxoz.kz stay official (is_official_domain pins, consistent with test_adapters.py:75-79).

## EXTRA_RUNS (collateral + gates)

1. cd backend && ./.venv/bin/python -m pytest tests/test_adapters.py tests/test_live_extraction.py --no-header -p no:cacheprovider -q → exit 0, all passed. Log: /tmp/t27probe/collateral.log
2. cd backend && ./.venv/bin/python -m pytest tests/test_adapters.py tests/test_live_extraction.py tests/test_live_regressions.py --no-header -p no:cacheprovider → exit 1 with exactly the same 7 intended REDs, 151 passed — no collateral breakage from the added fixtures/tests. Log: /tmp/t27probe/collateral_final.log
3. Future coverage gate (expected fail on baseline): ./.venv/bin/python -m pytest tests/test_claim_verifier.py --cov=app.domain.claim_verifier --cov-fail-under=100 → exit 2 (module missing). This is the T27 implementation gate; not hacked around. Log: /tmp/t27probe/coverage_gate.log
4. Hygiene: ruff check + ruff format --check clean on both test files; mypy clean ("Success: no issues found in 2 source files").

## ASSERTIONS (defect -> required behavior encoded)

- R1: negation page -> no FEE_WAIVER_AVAILABLE claim with normalized_value True; indeterminate mention -> no claim at all; the published $50 application fee stays claimed.
- R2: no TUITION claim with amount < 100 (adapter and extractor seam); genuine $4,500 tuition still reads.
- R3: is_official_domain False for ?u= query spoof and subdomain spoof, True for real host/www; adapter-level: no VERIFIED_CURRENT claims from a page served from attacker.example with candidate.domain="narxoz.kz".
- test_claim_verifier.py (frozen contract): NFKC/NBSP/whitespace-collapse normalization; case-sensitive verbatim after normalization incl. near-misses; range table per rule kind with injected today (IELTS step 0.5 boundary incl. 6.25/9.5, money > 0, bare-year >= today.year boundary, deadline ISO format-only); url_matches_domains exact/subdomain/query/path/subdomain-spoof/fixture://; registrable_domain; page_type_admits matrix + ACCEPTS-consistency test importing page_classifier.ACCEPTS and PageType (all 14 PageType values x 6 extractor families); verify_claim first-fail order excerpt -> value -> domain -> page_type; absent context never rejects (None page_text, official_domain=False, empty allowed_domains, None page_type).

## FIXTURE CALIBRATION NOTES (for the developer/next QA)

- The trap fixture fires because the first "tuition" occurrence's 120-char window contains "$50" before any period (verified: TUITION 50.0 via both WebCostAdapter and extract_costs directly).
- In the negation fixture the fee h2 is named "Fees and payment": _claim_fees._line_containing takes the FIRST line containing "application fee", so an "Application fee" heading without an amount swallows the fee line and no APPLICATION_FEE claim is produced at all (baseline behavior; avoided so the R2 guard is testable).
- The genuine-tuition guard's replacement sentence is length-tuned: main_content requires >200 chars of main text (else the <title> joins the text and shifts the window), and "$4,500" must sit within the first 127 chars after the h1's "Tuition".

## OBSERVED_ADJACENT_DEFECTS (out of agreed scope — NOT tested, flagging only)

1. extract_costs label patterns have no word boundaries: MEALS pattern alternative "board" matched inside "university board", attaching the $4,500 tuition to MEALS_COST in one probe variant. Same class of bug as the audited window defect (extraction.py:461-474).
2. On baseline, a page whose first "application fee" line is an amount-less heading produces NO application-fee claim even when a later line publishes the amount (first-match semantics of _line_containing, web_requirements.py:349-353).

## UNTESTED_RISKS

- The frozen contract's "bare-year >= today.year" rule is exercised via ClaimType.ADMISSION_DEADLINE bare-year string values ("2026"/"2027"); no current extractor produces bare years (T2/T3 future sources), so the adapter-level path for that rule is untested by construction.
- CLAIM_TYPE_PAGE_TYPES consistency covers the six ACCEPTS families with producing extractors; POST_STUDY_WORK (government) and RANKING_POSITION (fixture ranking) have no ACCEPTS family and are outside the table.
- value_in_range signature is pinned as value_in_range(claim_type, value, *, today) — contract tests define this; if the developer's frozen-API reading differs, this surfaces at implementation time, not silently.

## BLOCKERS

None.

## NEXT_ACTION

Developer (T27 A1) branches from QA commit d8553e19cf7d5d5236c5f74b7ffc55f436d66a00 and implements the frozen contract (claim_verifier.py + extraction.py + web_requirements.py _claim_fees negation branch) until the 7 REDs turn GREEN and test_claim_verifier.py passes with --cov=app.domain.claim_verifier --cov-fail-under=100; then VERIFY_CANDIDATE on the frozen candidate SHA.
