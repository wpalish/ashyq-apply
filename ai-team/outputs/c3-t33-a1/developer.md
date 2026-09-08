# T33 A1 — Developer report

- STATUS: IMPLEMENTED
- BASELINE_SHA (QA RED, start): 2d00f4522004df273a8efac383b3fe70963c190f (parent = edf546de9f998c0909337d0abe6f8e1c9c4a0be5)
- CANDIDATE_SHA: 540e3567f78e0bbe4be1da3cd3319ae086e3ca8c (branch ai/c3/t33/dev, worktree /Users/wpalish/ashyq-worktrees/c3-t33-dev, tree clean after commit)

## CHANGED_FILES

- backend/app/api/routes_results.py (+9/-4 — bodies of set_decision, set_notes only)
- backend/app/api/routes_profile.py (+59/-13 — imports + body of export_profile only)
- backend/app/payments/entitlements.py (+3/-2 — free_view nested costs.source_urls clearing only)

No QA test files, no config.py, no frontend, no schemas touched. Parallel-task files (payments/apipay.py, payments/provider.py, mail.py, routes_auth.py, runner.py) untouched.

## ROOT_CAUSE_FIXED

- S1: set_decision/set_notes guarded ownership only (owned_run) and returned the full stored ProgramResult; now resolve `_profile_id, allowed = access_for_run(...)` (tenancy preserved — access_for_run calls owned_run internally), persist exactly as before (full payload + decision/notes + audit), apply user fields to the result BEFORE projection, and `return result if allowed else free_view(result)`. 200 both ways; payments_enabled=False → has_full_access=True → byte-identical baseline behavior.
- S2: export_profile guarded ownership only. Now `has_full_access(session, principal.organization_id, profile_id)` (PD-4, one entitlement per profile opens the whole export). allowed → output byte-identical to baseline. Not allowed → per row `{**free_view(ProgramResult.model_validate(result.payload)).model_dump(mode="json"), "paid_content_withheld": True}`; claims/conflicts tables `[]`; counts unchanged (queries kept); note rewritten in free branch only.
- Scan 4th param (dispatcher expansion PD-scan): free_view clears nested `costs.source_urls = []` (CostBreakdown is a single object on ProgramResult, never None; deep copy keeps the projection non-mutating). costs.items/total stay readable per contract — only the source_urls inside are stripped.

## GATES (real runs, backend/, venv)

- a. `./.venv/bin/python -m pytest tests/test_paywall.py tests/test_paywall_surface.py` → **42 passed** (RED-1/2/3 green; surface scan all 4 former-RED params green; inventory test green; GREEN-guard green)
- b. `./.venv/bin/python -m pytest tests/test_billing_api.py tests/test_frontend_contract.py` → **34 passed**
- c. `./.venv/bin/python -m pytest tests/test_api.py tests/test_payment_webhook.py tests/test_payment_service.py` → **99 passed**
- d. `./.venv/bin/python -m mypy app tests` → **Success: no issues found in 165 source files**
- e. `./.venv/bin/python -m ruff check app tests && ruff format --check app tests` → **All checks passed! / 165 files already formatted**
- Extra (not required): `pytest tests/test_entitlements.py` → 10 passed (adjacent unit tests for the changed entitlements.py, incl. non-mutation test).

## RED_TO_GREEN (measured on baseline 2d00f45 before fix)

- RED test_decision_for_free_org_returns_the_free_view_projection → green
- RED test_notes_for_free_org_returns_the_free_view_projection → green
- RED test_gdpr_export_for_free_org_withholds_paid_material → green
- Scan RED GET /api/runs/{run_id}/results (nested costs.source_urls) → green
- Scan RED POST /api/runs/{run_id}/results/{result_id}/decision → green
- Scan RED PATCH /api/runs/{run_id}/results/{result_id}/notes → green
- Scan RED GET /api/profiles/{profile_id}/export → green
- Inventory test + all other scan params: green on baseline, green after.

## DESIGN_NOTES

- Projection happens after persistence and audit; the stored payload remains full for both tiers (a later payment reveals history without re-running).
- Free export note (dev wording): states what IS included, says the research evidence behind the results is withheld because the case has not been unlocked, points at counts and the paid_content_withheld marker, keeps the deletion promise. Contains no "every claim and conflict" promise.
- Deviation from a literal reading of the ruling text: "inside each costs entry" — ProgramResult.costs is a single CostBreakdown object (not a list), so one assignment `trimmed.costs.source_urls = []` covers it; verified against app/schemas/result.py:307,133-138.
- free branch export rows use model_dump only (id/run_id/user fields all present from the model); the explicit column-header dict is kept only on the allowed path so the paid output stays byte-identical.

## MIGRATIONS

None. No schema changes.

## RESIDUALS

- Singular `Money.source_url` inside costs.items and RankingEntry.url are not in the frozen material dictionary and were left as-is (out of scope; existing free shortlist behavior).
- Independent QA/review not yet run on the candidate — not claimed here.

## BLOCKERS

None.

## NEXT_ACTION

Hand candidate 540e3567f78e0bbe4be1da3cd3319ae086e3ca8c to QA verification in a separate worktree; do not amend the candidate during review.
