# T34 A1 — Developer report (campaign c3, payments fail-closed)

- ROLE: ashyq-developer, attempt A1, single writer of production code for T34 in this worktree.
- STATUS: IMPLEMENTED
- BASELINE: edf546de9f998c0909337d0abe6f8e1c9c4a0be5; checked out at QA RED commit dc04fc387c4ab605dbed4cacde915105384db1e8 (branch ai/c3/t34/dev, clean tree, verified before start).
- CANDIDATE_SHA: b55a3b083558812079e7a2ff366cc9019e2d7393 (immutable from here; parent = dc04fc3).

## Changed files (production paths only, 36 insertions / 0 deletions, no test edits)

- backend/app/config.py (+19) — C1: payments block inserted at the TOP of validate_runtime body (after docstring, before the auth check). Provider enum check; apipay requires key >=20 chars and webhook secret >=32 chars (raw SecretStr values, no strip semantics); production+enabled+fake refused. No field changes anywhere.
- backend/app/payments/apipay.py (+11) — C2: ValueError guards as first statements of __init__ body ("ApiPayProvider requires a non-empty api_key." / "...non-empty webhook_secret."); C3: `if not self._secret: return False` in verify_webhook immediately after the empty-signature guard (401 at the route, never hmac.new over b"").
- backend/app/payments/provider.py (+6) — C4: pre-fake guard `if settings.payments_provider != "fake": raise RuntimeError(...)` with the same C1 message and an explanatory comment (RuntimeError, not assert — asserts vanish under -O).

Out of scope, untouched: fake.py, conftest.py, routes_webhooks.py, service/entitlements/worker, schemas, frontend, all QA test files, config.py smtp hunks (T35's), entitlements.py (T33's).

## Gates (real runs, from backend/, venv ./.venv)

Baseline RED first (pre-implementation, on dc04fc3):

```
./.venv/bin/python -m pytest tests/test_apipay_adapter.py tests/test_payments_config.py
→ 7 failed, 21 passed   (R1, R2, R3, R4, R5[x2], R6 red; 19 pre-existing + 2 guards green)
```

a. `./.venv/bin/python -m pytest tests/test_apipay_adapter.py tests/test_payments_config.py` → 28 passed
b. `./.venv/bin/python -m pytest tests/test_payment_webhook.py tests/test_payment_service.py tests/test_payment_reconcile.py tests/test_payment_provider.py` → 51 passed, 1 warning (pre-existing Starlette deprecation)
c. `./.venv/bin/python -m pytest tests/test_security.py tests/test_metrics.py tests/test_api.py` → 102 passed, 1 warning (same pre-existing)
d. `./.venv/bin/python -m mypy app tests` → Success: no issues found in 164 source files
e. `./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m ruff format --check app tests` → All checks passed! / 164 files already formatted

Extra regression beyond required gates:

```
./.venv/bin/python -m pytest tests/test_billing_api.py tests/test_billing_models.py tests/test_entitlements.py tests/test_paywall.py → 46 passed
./.venv/bin/python -m pytest --cov=app --cov-fail-under=92 → 1367 passed, Total coverage: 93.80% (gate 92)
```

## RED → GREEN per scenario

- R1 (empty-secret webhook forge): RED on baseline (forged b""-key signature verified True) → GREEN: verify_webhook returns False for every signature when _secret is empty.
- R2 (empty api_key at construction): RED (silent construction) → GREEN: ValueError "ApiPayProvider requires a non-empty api_key."
- R3 (empty webhook_secret at construction): RED → GREEN: ValueError "ApiPayProvider requires a non-empty webhook_secret."
- R4 (provider typo "apipy"): RED (validate_runtime did not raise) → GREEN: RuntimeError matching UNIMATCH_PAYMENTS_PROVIDER.
- R5 (apipay short key 19 / short secret 31, parametrized): RED → GREEN: RuntimeError matching UNIMATCH_APIPAY_API_KEY / UNIMATCH_APIPAY_WEBHOOK_SECRET respectively.
- R6 (production + enabled + fake): RED → GREEN: RuntimeError matching "fake provider".
- Guards (valid production apipay config; dev + fake + enabled): green before, green after.

## Design notes / deviations

- None semantic. All four error messages are byte-for-byte the frozen contract text; the >=32-chars message is wrapped across two adjacent string literals in source (contract explicitly allows line wrapping). No strip semantics added. C1 runs before the pre-existing production checks so a misconfigured payment stack is reported even when something else is also wrong — matches the "top insertion" instruction.

## Residuals

- Coverage arithmetic: full-suite coverage is 93.80% (baseline ~93.81%). The only new statement not executed by the suite is the C4 raise in get_provider (provider.py:80) — unreachable via the API because validate_runtime refuses that configuration at startup; it exists precisely for worker processes that skip validate_runtime, and the frozen QA suite deliberately has no test for it. No test was added by me (tests are QA's scope); coverage gate passes with margin.
- Worker startup does not call validate_runtime (baseline fact, planner.md S3(b)): a typo'd provider in a worker-only deployment now fails at first get_provider call (C4) and empty apipay credentials fail at first construction (C2) — loud, but not at worker boot. Fail-fast at worker startup remains a follow-up outside this task's reserved paths.
- Operational consequence (release note material, per contract): the API now refuses to start on a typo'd provider, apipay without real credentials, or production billing through the fake. This is the fix, not a regression.

## Not claimed

- Independent QA re-verification, reviewer sign-off and integration have NOT happened; this candidate is submitted for them. No push, no deploy.

## Blockers

- None.

## Next action

- Hand CANDIDATE_SHA b55a3b083558812079e7a2ff366cc9019e2d7393 to independent QA for verification in a separate worktree; integration order T34 → T35 → T36 (config.py hunks are disjoint and anchor-clean for the recorded merge order).
