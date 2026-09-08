# T33 A1 — QA VERIFY_CANDIDATE report (campaign c3, findings S1+S2)

ROLE_PHASE: ashyq-qa / VERIFY_CANDIDATE
STATUS: VERIFIED_PASS
CHECKED_SHA: 540e3567f78e0bbe4be1da3cd3319ae086e3ca8c (worktree /Users/wpalish/ashyq-worktrees/c3-t33-verify, branch ai/c3/t33/verify, tree clean: `git status --porcelain` empty)

## SCOPE_CHECK

- Ancestry: `git merge-base --is-ancestor` edf546de→2d00f45 OK; 2d00f45→540e356 OK. `git log 2d00f45~1..HEAD` = exactly [2d00f45 QA RED, 540e356 candidate].
- `git diff 2d00f45..HEAD --numstat`: 64/27 routes_profile.py, 11/4 routes_results.py, 4/1 entitlements.py — exactly the three contracted files, nothing else.
- `git diff 2d00f45..HEAD -- backend/tests/` = 0 bytes (QA tests byte-identical). `-- backend/app/schemas backend/app/config.py frontend` = 0 bytes. No migrations.
- Note: developer.md numstat claims (+59/-13, +9/-4, +3/-2) undercount the real diff; scope itself is correct. Reporting inaccuracy only.

## ANTI_WEAKENING_CHECK

- set_decision/set_notes: `owned_run` replaced by `_profile_id, allowed = access_for_run(...)` (app/api/paywall.py:18-25 — access_for_run calls owned_run internally, tenancy preserved). Persistence order unchanged: row.payload = full model_dump + decision/notes fields + AuditEvent + commit BEFORE `return result if allowed else free_view(result)`; user fields applied to `result` before projection (routes_results.py:280-303, 332-347). payments_enabled=False: has_full_access returns True unconditionally (entitlements.py:23-24) → `result if allowed` = baseline path; probe P4 confirms full material returns.
- export_profile: `owned_profile` retained; `allowed = has_full_access(session, principal.organization_id, profile_id)` (PD-4). Allowed-branch byte-identity verified mechanically: results-row dict, claims dict, conflicts dict and note string extracted from baseline vs candidate and compared — all textually identical. Free branch exactly the frozen shape `{**free_view(ProgramResult.model_validate(payload)).model_dump(mode="json"), "paid_content_withheld": True}`; claims/conflicts [] (queries still executed, so counts.claims/conflicts kept); free note states what is included, says evidence withheld because case not unlocked, keeps the deletion promise, no "every claim and conflict" promise.
- free_view hardening adjudication (dispatcher expansion ACCEPTED as implemented): diff adds ONLY `trimmed.costs.source_urls = []` (+docstring). ProgramResult.costs is a single non-optional CostBreakdown (app/schemas/result.py:307 `costs: CostBreakdown = Field(default_factory=CostBreakdown)`; class at :133, source_urls at :137) — the developer's "single object" claim is correct. Money.source_url (singular, :260) inside costs.items and RankingEntry.url (:43) are not keys in the frozen material dictionary and are untouched. No other free_view behavior changed; deep-copy (model_copy(deep=True)) preserved.
- Payload-aliasing check (runtime, /tmp/t33_verify_probe.py, 34/34 PASS): after a FREE decision and a FREE notes call, a fresh session reads the stored row.payload — claims (1), source_urls, funding_gap, verification_completeness=1.0, admission_deadline_raw, career_notes AND costs.source_urls all still present in storage while the HTTP responses were trimmed; costs.items survives; user_decision/user_notes persisted. free_view trims a deep copy; the stored dict is never aliased or written back.
- No other routes touched; get_result still 402 and summary open (existing tests green in gate a); no schema/types/config changes.

## GATES (real runs, backend/, venv .venv, no extra flags, no retries, no timeout changes)

- a. `./.venv/bin/python -m pytest tests/test_paywall.py tests/test_paywall_surface.py` → **42 passed**, exit 0 (RED-1/2/3 green, all 4 former-RED scan params green, 17-route inventory equality green, GREEN-guard green)
- b. `./.venv/bin/python -m pytest tests/test_billing_api.py tests/test_frontend_contract.py tests/test_entitlements.py` → **44 passed**, exit 0
- c. `./.venv/bin/python -m pytest tests/test_api.py tests/test_payment_webhook.py tests/test_payment_service.py` → **99 passed**, exit 0
- d. `./.venv/bin/python -m mypy app tests` → **Success: no issues found in 165 source files**, exit 0
- e. `./.venv/bin/python -m ruff check app tests` → All checks passed!, exit 0; `./.venv/bin/python -m ruff format --check app tests` → 165 files already formatted, exit 0
- Sweep (pg-free, classified by grep first): tests/test_security.py uses its own sqlite auth_client (its single "postgres" hit is a config-string literal in a Settings validation test); tests/test_pipeline.py has zero pg/pgserver/psycopg references. `pytest tests/test_security.py tests/test_pipeline.py` → **53 passed**, exit 0.

## ADVERSARIAL_NOTES

- 17-route surface: the executed scan (inventory + all params) is green on the candidate; against the diff, no route gained a material path — decision/notes are now projected, export branched, free_view strictly removes more. No new routes (inventory equality enforces this).
- Mixed runs: probe P2/P3 — profile with two sequential runs, no entitlement: every row of BOTH runs withheld + paid_content_withheld, claims/conflicts [], counts kept, honest note; after one CASE_FULL entitlement the whole-profile export opens (PD-4), paid note restored, no withheld markers.
- The byte-identity tests alone would not distinguish a trimmed persisted payload; probe P1 closes that gap empirically.
- Untouched residuals (accepted, per frozen dictionary): Money.source_url inside costs.items and RankingEntry.url remain visible in free output — not material keys under the frozen contract; if the dictionary is ever amended, that is a new contracted decision, not this candidate's defect.

## BLOCKERS

None.

## NEXT_ACTION

Candidate 540e3567f78e0bbe4be1da3cd3319ae086e3ca8c is verified from QA side (VERIFIED_PASS). Hand to reviewer/integrator; full --cov sweep remains the integrator's gate. No push/deploy performed. QA does not grant final merge approval.

Environment: macOS arm64, backend/.venv (Python 3.12), offline SQLite fixtures, no PostgreSQL needed by any executed suite. Artifacts: this report; probe script /tmp/t33_verify_probe.py; logs /tmp/t33_gate_c.log, /tmp/t33_sweep.log.
