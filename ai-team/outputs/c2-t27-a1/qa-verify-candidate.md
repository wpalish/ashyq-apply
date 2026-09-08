# T27 A1 — QA VERIFY_CANDIDATE report

- ROLE_PHASE: VERIFY_CANDIDATE (ashyq-qa, campaign c2, attempt A1; independent new invocation, separate from TEST_AUTHOR)
- Worktree: /Users/wpalish/ashyq-worktrees/c2-t27-verify (branch ai/c2/t27/verify; read-only except pytest caches — nothing tracked modified, tree clean before and after)
- Venv: /Users/wpalish/ashyq-worktrees/c2-t27-verify/backend/.venv; pytest.ini addopts=-q respected (no extra -q passed)
- Artifact: offline adversarial probe /tmp/t27verify/probe_adversarial.py (15/15 checks pass, exit 0)

## STATUS: VERIFIED_PASS

## CHECKED_SHA

- HEAD: 51f211d9d1159f0e255f307dc707872ddd3a1f30 (`git rev-parse HEAD`) — equals frozen CANDIDATE_SHA
- `git status --porcelain` empty (clean); branch ai/c2/t27/verify
- Ancestry verified: 28d729ca76cdf8d52344517a8316e2e805099d11 → d8553e19cf7d5d5236c5f74b7ffc55f436d66a00 → 51f211d (merge-base --is-ancestor both edges; HEAD~1=d8553e1, HEAD~2=28d729c)
- QA commit d8553e1 = exactly 5 test files, 712 insertions (3 fixtures live_shapes + test_claim_verifier.py 455 + test_live_regressions.py 223) — matches TEST_AUTHOR report

## SCOPE_CHECK: PASS

`git diff d8553e1..HEAD --stat` = exactly 3 files:
- backend/app/domain/claim_verifier.py — NEW +375/-0
- backend/app/adapters/extraction.py — +118/-29
- backend/app/adapters/requirements/web_requirements.py — +21/-3

`git diff d8553e1..HEAD -- backend/tests/` is EMPTY — QA tests byte-identical. No fetching/models/migrations/schemas/page_classifier/enums files touched. web_costs/web_scholarships/web_documents/web_government untouched (confirmed via diff --name-only; only extraction.py and requirements/web_requirements.py appear).

## ANTI_WEAKENING_CHECK: PASS (1 adjudicated deviation — ACCEPTED)

Contract conformance, verified by reading the code (not the reports):
- claim_verifier.py imports: stdlib only + app.domain.enums. No app.adapters import, no I/O. Contract API present: RejectReason (4 values, exact), VerificationInput (field order per contract, today last), Verdict(accepted, reason), verify_claim first-fail order excerpt→value→domain→page_type, normalize_text (NFKC + \s+ collapse + strip), is_verbatim_excerpt case-sensitive after both-side normalization, url_matches_domains host-only via registrable_domain (query/path never decide; narxoz.kz.attacker.example → attacker.example), VALUE_RANGE_RULES DATA table per contract (IELTS 0-9 step 0.5, TOEFL 0-120, Duolingo 0-160, SAT 0-1600, money amount>0, ADMISSION_DEADLINE ISO format-only + bare-year >= today.year), CLAIM_TYPE_PAGE_TYPES mirroring ACCEPTS (guarded by the frozen two-sided consistency test, green).
- extraction.py: ClaimBuilder optional kwargs page_text/page_type/allowed_domains (context stored OUTSIDE meta — persisted Claim fields unchanged); add() → Claim | None; reject recorded in builder.rejected as (claim_type, excerpt, reason); extract_requirements/extract_costs skip None via _keep; range check active with today=accessed_at.date(); domain-consistency guard exactly official_domain AND allowed_domains AND source_url AND mismatch (dormant for legacy call sites — allowed_domains defaults to ()). is_official_domain reimplemented on registrable_domain/url_matches_domains — host-only. TUITION_FLOOR_AMOUNT=100.0 named Final constant, applied to {TUITION, TOTAL_COST_OF_ATTENDANCE} before builder.add. parse_money/_MONEY untouched (not in diff).
- web_requirements.py: diff confined to _claim_fees waiver branch + _WAIVER_NEGATION/_WAIVER_OFFERED constants. No waiver line → no claim; negation → False; explicit affirmation → True; indeterminate → no claim. APPLICATION_FEE branch untouched.

### Adjudication of the casefold deviation (verify_claim excerpt step): ACCEPT

The tension is real and provable in the frozen, byte-identical tests: test_claim_verifier.py:102-103 (test_matching_is_case_sensitive) pins is_verbatim_excerpt as case-sensitive, while :414-423 (test_a_zero_money_amount_is_rejected) pairs excerpt "tuition is $0 per year" with page "Tuition is $0 per year…" and demands VALUE_OUT_OF_RANGE. With a strictly case-sensitive excerpt step at the seam, first-fail order returns EXCERPT_NOT_VERBATIM and that frozen test fails. NO implementation satisfies both frozen tests without seam-level case forgiveness; the developer could not edit the tests (diff empty, verified) and did not.

Why acceptance is not a weakening of the anti-hallucination guarantee:
1. The exported is_verbatim_excerpt remains strictly case-sensitive (pinned, verified) — the contract's verbatim predicate is intact; only verify_claim's excerpt step forgives letter case, scoped, and documented in the module docstring.
2. Casefold folds letter identity only. Numbers, punctuation, word boundaries, and negations must still match exactly — probe: "tuition is 4,5000 per year" (matching case, changed content) → EXCERPT_NOT_VERBATIM; "an overall band of 6.50" → rejected. A hallucinated excerpt cannot pass by changing case; it must still reproduce the page's exact words and figures.
3. This is the same spirit as the contract's own normalization (NFKC folds NBSP→space, ﬁ→fi; whitespace runs collapse), which likewise alters bytes without altering content. Letter case on English university pages carries no truth value.
4. The developer flagged it proactively (DESIGN_NOTES #1) instead of hiding it.

Condition: record this as a contract clarification in HANDOFF §8 (verify_claim's excerpt step is case-insensitive at the seam; is_verbatim_excerpt stays strict). If the team later wants a strictly case-sensitive seam, that is a test-contract change (fix the zero-money test's excerpt casing) requiring a new QA cycle + new candidate — not doable silently.

Minor, non-weakening API notes (both flagged by developer, both verified harmless): VerificationInput.today typed `date | None = None` with date.today() fallback (contract says "today: date"; all frozen tests inject today; adapter paths always inject accessed_at.date()); the domain guard additionally requires source_url presence (consistent with "absent context never rejects").

## GATES (re-run by QA on 51f211d, cwd backend/, real outputs)

- a. `./.venv/bin/python -m pytest tests/test_claim_verifier.py tests/test_live_regressions.py` → `157 passed in 5.26s`, exit 0. Includes all 10 tests of the three regression classes (7 former REDs + 3 GREEN guards); also run with `-k "TestFeeWaiverNegation or TestApplicationFeeSwallowedByTuitionWindow or TestSpoofedOfficialDomain" -v` → `10 passed`, exit 0.
- b. `./.venv/bin/python -m pytest tests/test_claim_verifier.py --cov=app.domain.claim_verifier --cov-fail-under=100` → `app/domain/claim_verifier.py 93 0 100%`, `Required test coverage of 100% reached. Total coverage: 100.00%`, `86 passed`, exit 0.
- c. `./.venv/bin/python -m pytest tests/test_adapters.py tests/test_live_extraction.py tests/test_security.py` → `109 passed, 1 warning in 8.88s`, exit 0.
- d. `./.venv/bin/python -m mypy app tests` → `Success: no issues found in 157 source files`, exit 0 (pre-existing annotation-unchecked notes in unrelated test files only).
- e. `./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m ruff format --check app tests` → `All checks passed!` / `157 files already formatted`, exit 0.
- Sweep (pg-free, verified by grep before running: test_metrics.py's psycopg strings are config values, no pg fixtures; test_pipeline.py uses SQLite via the settings fixture): `./.venv/bin/python -m pytest tests/test_live_discovery.py tests/test_metrics.py tests/test_pipeline.py` → `154 passed, 1 warning in 15.67s`, exit 0.
- Full `--cov=app` heavy suite NOT run — reserved to dispatcher per packet.

## PASS-THROUGH SPOT CHECKS (offline, real adapter path, fixture corpus)

- WebRequirementsAdapter on fixture://u-groningen/admissions.html + program-0.html (domain rug.nl): 14/14 claims VERIFIED_CURRENT (ielts_min_overall 6.0/6.5, application_fee, fee_waiver_available, deadlines, gpa, sat_policy, toefl 90 ...).
- WebCostAdapter.fetch on fixture://epfl/costs.html (domain epfl.ch): 6/6 claims VERIFIED_CURRENT, tuition 1,580 CHF intact.
- QA GREEN guards inside the frozen tests (application fee 50 USD preserved, genuine 4,500 tuition reads, narxoz.kz/www official) all green in gate a.

## ADVERSARIAL_NOTES

1. CONFIRMED residual defect class, out of frozen scope: the tuition floor only kills amounts < 100. Probe `extract_costs` on "Tuition and fees $150 application fee is due at submission..." → TUITION = 150.0 USD survives. The audited $50 FP is fixed; a 100-999 application/housing fee inside the 120-char window still misreads as tuition. Root cause is the label-window/no-word-boundary design (also TEST_AUTHOR's "board"-in-"university board" note). Needs its own task; do not widen inside T27.
2. Domain-consistency guard dormant in production: none of the 5 ClaimBuilder call sites (web_government.py:36, web_scholarships.py:172, web_costs.py:83, web_requirements.py:157, web_documents.py:186) passes allowed_domains/page_text/page_type (the page_type= hits are PageOutcome report objects). By contract (no adapter call-site edits at T27). So adapter-level anti-spoof protection currently rests solely on is_official_domain — which is now genuinely host-only: probe confirms False for ?u=narxoz.kz, /narxoz.kz path, narxoz.kz.attacker.example, AND userinfo spoofs narxoz.kz@attacker.example / narxoz.kz:secret@attacker.example (the old substring code accepted the userinfo variants). Fixture:// short-circuit and www/subdomain/port shapes behave as pinned.
3. SCHOLARSHIP_AMOUNT has no range rule. Developer's rationale verified factual: web_scholarships.py produces {"percent_of_tuition": x}, {"amount":..., "academic_year":...}, or None for it — an amount-only rule would KeyError on two of three shapes. Residual: "the award is worth $0" would be claimed and accepted (no rule). Frozen table never ranged it → conformance OK; flag for the future task that unifies scholarship value shapes.
4. Coverage nuance: registrable_domain's keep=3 (multi-part suffix) branch is not discriminated in isolation — line coverage passes because the ternary is one line and branch coverage is not enforced. Behaviorally the ox.ac.uk official pin holds under either computation, and the discriminating case (narxoz.kz.attacker.example → attacker.example, keep=2) is pinned. No action needed for T27.
5. No retries, no timeout increases, no skips used anywhere; every gate ran once against the frozen tree.

## BLOCKERS

None.

## NEXT_ACTION

Candidate 51f211d9d1159f0e255f307dc707872ddd3a1f30 is VERIFIED_PASS from QA VERIFY_CANDIDATE. Hand to ashyq-reviewer (dispatcher may add ashyq-security given the domain-spoof surface). Dispatcher actions: log the casefold adjudication in HANDOFF §8; the heavy `--cov=app` gate remains dispatcher-owned; consider follow-up tasks for the 100-999 tuition-window class and scholarship value-shape unification (both outside T27/T28 files).
