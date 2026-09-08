# T33 A1 — QA TEST_AUTHOR report (campaign c3, SECURITY paywall bypass)

ROLE_PHASE: ashyq-qa / TEST_AUTHOR
STATUS: TESTS_READY (with one escalated surface-scan finding, see §4)
CHECKED_SHA: edf546de9f998c0909337d0abe6f8e1c9c4a0be5 (git rev-parse HEAD, branch ai/c3/t33/qa, tree clean before work)
QA_COMMIT: 2d00f4522004df273a8efac383b3fe70963c190f (parent = baseline; only the two allowed test files; no push)

## 1. Files created/modified (allowed paths only)

- MODIFIED /Users/wpalish/ashyq-worktrees/c3-t33-qa/backend/tests/test_paywall.py (+229, append-only; no existing test edited)
- NEW /Users/wpalish/ashyq-worktrees/c3-t33-qa/backend/tests/test_paywall_surface.py (18 tests: 1 inventory + 17 execution params)
- No conftest.py, app/**, payments/**, config.py, frontend/** edits (git status shows only the two files).

## 2. Commands and exit codes (venv /Users/wpalish/ashyq-worktrees/c3-t33-qa/backend/.venv)

- `./.venv/bin/python -m pytest tests/test_paywall.py` (pre-work baseline sanity): 20 passed, exit 0
- `./.venv/bin/python -m pytest tests/test_paywall.py tests/test_paywall_surface.py` (final): 7 failed, 35 passed, exit 1
- `./.venv/bin/python -m pytest tests/test_frontend_contract.py tests/test_billing_api.py`: 34 passed, exit 0 (unmodified)
- `./.venv/bin/python -m ruff check tests/test_paywall.py tests/test_paywall_surface.py`: passed
- `./.venv/bin/python -m ruff format --check tests/test_paywall.py tests/test_paywall_surface.py`: passed
- Route discovery probe (throwaway script, not committed): enumerated app.routes through the FastAPI 0.141.1 `_IncludedRouter.original_router` + `include_context.prefix`; log retained at /tmp/t33-final.log (pytest) and in-session shell output.

## 3. RED results (all on baseline, before any fix)

- RED-1 test_decision_for_free_org_returns_the_free_view_projection — FAIL at tests/test_paywall.py:302: `assert body['claims'] == []` got the full seeded claim list back (POST /api/runs/{run_id}/results/{result_id}/decision answered 200 with full material). Assertions written in post-fix form: material withheld, user_decision/reason/notes/decided_at reflected, canonical-JSON byte-identity with free_view(ProgramResult.model_validate(stored.payload)).model_dump(mode="json").
- RED-2 test_notes_for_free_org_returns_the_free_view_projection — FAIL at tests/test_paywall.py:302 (same withheld-material helper; PATCH .../notes answered 200 with full material). Post-fix form also pins user_notes reflected, user_decision "undecided", decided_at None, byte-identity.
- RED-3 test_gdpr_export_for_free_org_withholds_paid_material — FAIL at tests/test_paywall.py:393: `assert body['claims'] == []` got the claims table (GET /api/profiles/{profile_id}/export answered 200 with full claims/conflicts/results). Post-fix form: claims [], conflicts [], counts preserved (>=1 each), note no longer promises "every claim and conflict", every result row projected + row-level paid_content_withheld True.

## 4. Surface-scan results (test_paywall_surface.py) — EXACT failing-param list

Contracted expectation (planner.md §4): scan RED on exactly 3 params. OBSERVED: RED on 4 params.

1. `POST /api/runs/{run_id}/results/{result_id}/decision` — hits: response.requirement_checks, response.scholarships, response.costs.source_urls, response.funding_gap, response.admission_deadline_raw, response.career_notes, response.conflicts, response.conflicts[0].source_urls, response.unresolved, response.claims, response.source_urls, response.verification_completeness. [EXPECTED RED — S1]
2. `PATCH /api/runs/{run_id}/results/{result_id}/notes` — same hit set as decision. [EXPECTED RED — S1]
3. `GET /api/profiles/{profile_id}/export` — hits: response.claims, response.conflicts, response.conflicts[*].source_urls, and per results[*]: requirement_checks, scholarships, scholarships[*].eligibility_checks, scholarships[*].source_urls, costs.source_urls, funding_gap, admission_deadline_raw, post_study_work, career_notes, hard_filter_failures (rows[3]), unresolved, claims, source_urls, verification_completeness. [EXPECTED RED — S2]
4. `GET /api/runs/{run_id}/results` — hits: response[0..4].costs.source_urls (every free row). [ESCALATION — NOT in the contracted 3]

Escalation detail for param 4: `free_view` (app/payments/entitlements.py:76-98) clears top-level source_urls but leaves the nested `costs.source_urls` list populated; the cost adapter appends the costs page URL at app/adapters/cost/web_costs.py:99 (demo values are `fixture://<slug>/costs.html` provenance, same evidence trail the paywall withholds at top level). Per contract "лишний параметр = новая утечка → эскалация" I did NOT narrow the frozen material dictionary and did NOT touch entitlements.py (reserved to T34). Dispatcher ruling needed: either route "free_view must also clear costs.source_urls" to T34/developer scope, or amend the frozen dictionary carve-out. The scan implements the frozen dictionary verbatim.

Inventory equality test PASSED: discovered set == frozen 17-route list (discovery walks ^/api/runs/{run_id}/ and ^/api/profiles/{profile_id}/ proper prefixes, GET/POST/PATCH/PUT, declared status not in {202, 204} — the 202 enqueue routes and the id-only GET/PUT roots carry no material and are out per the frozen count of 17).

13 remaining scan params PASSED on baseline: POST cancel, GET claims (402), GET conflicts (402), GET deadlines (402), GET deadlines.ics (402), GET export.{fmt} (402), GET questions (402), POST rerank, GET results/{result_id} (402), POST retry, GET shortlist (402), GET summary, GET profiles/{profile_id}/validation.

## 5. GREEN results on baseline

- test_paying_opens_full_decision_notes_and_export — PASS (guard: after _unlock(), decision/notes return the seeded claims/source_urls/funding_gap; export carries claims+conflicts; paid result rows have no paid_content_withheld key, per PD-4 "paid output unchanged").
- Existing 20 test_paywall.py tests — PASS (unmodified).
- tests/test_frontend_contract.py + tests/test_billing_api.py — 34 passed, unmodified.

## 6. Environment

macOS arm64, Python 3.12 venv (provisioned), fastapi 0.141.1 / starlette 1.6.0 (route discovery must go through `_IncludedRouter.original_router`), SQLite per-test DB via paid_client fixture (unchanged), offline, pgserver not needed by these files. No retries, no timeout increases, no test-tuning to force PASS.

## 7. Seeding note (test data only)

`_seed_paid_material_into_first_row(run_id)` writes schema-valid values through the real pydantic models into the test DB (ProgramResultRow.payload + one ClaimRow + one ConflictRow): source_urls, ClaimOut(id="claim-seed-1", tuition=5000, fixture-style URL), Conflict(claim_type=tuition), Scholarship(id="scholarship-seed-1"), FundingGap(computable=True, gap Money 1200), verification_completeness=1.0, admission_deadline_raw, career_notes. Makes RED deterministic independent of corpus shuffle; no production code touched.

## 8. Untested risks / handoff notes

- The byte-identity assertions intentionally compare against `free_view` of the payload AS STORED AFTER the write — a fix that projects BEFORE applying user fields will still fail RED-1/2 (per contract: fields applied before projection).
- RED-3 asserts row-level `paid_content_withheld: True` (the exact frozen contract shape) and does NOT assert a top-level flag; developer may add one, contract does not require it.
- The escalated 4th scan param means a naive fix of only decision/notes/export will leave test_paywall_surface.py::...[GET-/api/runs/{run_id}/results] red. Decide ownership (entitlements.py is T34's reserve) BEFORE developer starts.
- QA cannot approve merge; verification of the candidate happens in a fresh VERIFY_CANDIDATE run.
