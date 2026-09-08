# T27 A1 — Planner contract (frozen)

- Invocation ref: agent_9ed8a437-0b1e-451e-a333-be7a353a486b
- Baseline: 28d729ca76cdf8d52344517a8316e2e805099d11 (ai/c2/integration head; T16 merged)
- STATUS: PLANNED
- Note: planner verified findings against /Users/wpalish/ashyq-worktrees/c2-integration (main checkout was still at 4d2125c; cited regions byte-identical since T16 did not touch extraction files).

## Facts (baseline state)

- No claim_verifier.py exists (domain/ has 20 modules, none named claim_verifier).
- Ranges inline in code: IELTS 4.0-9.0 extraction.py:327,344; TOEFL 40-120 :356; Duolingo 60-160 :366; GPA <=scale<=100 :379; SAT 400-1600 :395. No data table.
- _MONEY (extraction.py:211-216) accepts \d{2,7}; extract_costs (:456-491) takes first money in 120-char label window → "$50 application fee" inside tuition window becomes TUITION. Fix NOT in parse_money/_MONEY (test_adapters.py:516-522 pins USD 100 application fee; philosophy pinned test_live_extraction.py:446-455).
- FEE_WAIVER negation FP: web_requirements.py:306-314 _claim_fees — any "fee waiver" line yields True (:312-314). No existing FEE_WAIVER test.
- Domain FP: is_official_domain (extraction.py:96-103) substring-over-URL: ?u=narxoz.kz spoof yields True → VERIFIED_CURRENT via ClaimBuilder.add gate (extraction.py:147-162). Pins to keep: test_adapters.py:75-79. fixture:// short-circuits upstream; netloc parse keeps behavior.
- ACCEPTS matrix is extractor-family-keyed (page_classifier.py:44-75, accepts() :90-91); no ClaimType→PageType table; domain/ cannot import adapters (AGENTS.md §6) → ClaimType-level DATA table in claim_verifier.py + consistency test.
- T1 corpus already satisfies excerpt/range/domain/page_type by construction; the 3 audit FPs are extraction bugs → verifier enforces range + domain-consistency at builder seam now; verbatim/page_type wired but dormant until adapters/T31 pass context. Nothing in fixture corpus may change outcome.
- Harness precedent: _verify_against/_serve test_live_regressions.py:441-529 (monkeypatched Fetcher, offline).

## Frozen contract

- NEW backend/app/domain/claim_verifier.py: pure, no I/O, imports only domain+stdlib. Frozen API: RejectReason(StrEnum: EXCERPT_NOT_VERBATIM/VALUE_OUT_OF_RANGE/DOMAIN_NOT_OFFICIAL/PAGE_TYPE_REJECTED); VerificationInput(claim_type, value, excerpt, page_text, source_url, page_type, official_domain, allowed_domains, today: date); Verdict(accepted, reason); verify_claim (first-fail order: excerpt→value→domain→page_type); normalize_text (NFKC + Unicode-whitespace-run collapse + strip); is_verbatim_excerpt (case-sensitive after normalization); value_in_range (DATA table: IELTS 0-9 step 0.5, TOEFL 0-120, Duolingo 0-160, SAT 0-1600, money amount>0, admission_deadline FORMAT-ONLY ISO, bare-year >= today.year for T2/T3); url_matches_domains (host suffix-match on registrable domain; query/path occurrences NEVER match; narxoz.kz.attacker.example does NOT match); registrable_domain; page_type_admits (CLAIM_TYPE_PAGE_TYPES table mirroring ACCEPTS families, consistency-guarded by test importing both sides).
- DATA tables live INSIDE claim_verifier.py as module-level frozen structures (JSON would need I/O — forbidden; second module out of card scope).
- Builder wiring (all in extraction.py, no adapter call-site edits): ClaimBuilder.__init__ optional kwargs page_text/page_type/allowed_domains; add() runs checks with present context only (absent context = NOT evaluated, NEVER rejects); at T27 activates range check (today from accessed_at) + domain-consistency guard (official_domain=True AND allowed_domains non-empty AND not url_matches_domains → reject DOMAIN_NOT_OFFICIAL); on reject: claim not appended, recorded in builder.rejected [(claim_type, excerpt, reason)], add() returns Claim | None; extract_requirements/extract_costs skip None. Rejects NOT surfaced to PageOutcome (T29 consumer).
- T1 fixes: is_official_domain reimplemented on registrable_domain/url_matches_domains; extract_costs tuition floor >= 100 named DATA constant (TUITION required; TOTAL_COST_OF_ATTENDANCE recommended-optional; APPLICATION_FEE keeps 2-digit); web_requirements.py _claim_fees negation branch ONLY: explicit negation → normalized_value=False; indeterminate → no claim (unknown stays unknown).
- allowed_paths: claim_verifier.py (new), extraction.py, web_requirements.py (_claim_fees only), test_claim_verifier.py (new), test_live_regressions.py, fixtures/live_shapes/** (3 new). No expansion needed.
- Non-goals: no fetching/models/migrations (T28), no LLM, no live requests, no Claim/enum/ACCEPTS/page_classifier/schemas changes, no PageOutcome surfacing, no global _MONEY retightening, no coverage lowering.
- Product decisions (frozen defaults, owner may override): negation→False vs no-claim (chose False = positive evidence of absence); year-rule scope (bare-year only, deadline format-only); tuition floor scope (TUITION required, TOTAL optional).
- Migration impact: none. Consumers: T31 (verify_claim for candidates + rejects feed), T29 (builder.rejected), all web adapters via seam transparently.

## QA TEST_AUTHOR instructions (verbatim from planner)

Work in /Users/wpalish/ashyq-worktrees/c2-t27-qa (ai/c2/t27/qa, venv backend/.venv), baseline 28d729c:
1. Fixtures in backend/tests/fixtures/live_shapes/: requirements_fee_waiver_negation.html, costs_application_fee_trap.html, + minimal requirements-shaped page for spoofed-domain scenario.
2. test_live_regressions.py: R1 adapter-level no FEE_WAIVER_AVAILABLE=True from negation page; R2 no TUITION amount<100 + APPLICATION_FEE preserved; R3 is_official_domain unit cases + adapter-level no VERIFIED_CURRENT from attacker URL. Assertion-RED on baseline.
3. test_claim_verifier.py against frozen API: ImportError-RED acceptable and expected on baseline (new-module pattern; do not fake GREEN). Coverage: --cov=app.domain.claim_verifier --cov-fail-under=100; global 92 untouched.
4. No production edits; commit with Agent trailer.
