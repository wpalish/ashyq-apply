# T34 A1 — QA VERIFY_CANDIDATE report (campaign c3, payments fail-closed)

- ROLE_PHASE: ashyq-qa / VERIFY_CANDIDATE
- STATUS: VERIFIED_PASS
- CHECKED_SHA: `b55a3b083558812079e7a2ff366cc9019e2d7393` (frozen candidate, worktree `/Users/wpalish/ashyq-worktrees/c3-t34-verify`, branch `ai/c3/t34/verify`, tree clean)
- Candidate is immutable during verification: no file in the worktree was modified.

## SCOPE_CHECK — PASS

- `git rev-parse HEAD` → `b55a3b083558812079e7a2ff366cc9019e2d7393`; `git status --porcelain` → empty.
- Ancestry: `git merge-base --is-ancestor` — edf546d → dc04fc3 OK; dc04fc3 → b55a3b0 OK.
- `git diff dc04fc3..HEAD --stat` → exactly `backend/app/config.py +19`, `backend/app/payments/apipay.py +11`, `backend/app/payments/provider.py +6`; 36 insertions, 0 deletions.
- `git diff dc04fc3..HEAD -- backend/tests/` → 0 bytes (QA tests byte-identical to QA commit dc04fc3).
- dc04fc3 verified as the QA RED commit (only the two QA test files; trailer style matches qa-test-author.md).

## ANTI_WEAKENING_CHECK — PASS (diff read literally, not from developer.md)

- C1: payments block inserted at the TOP of `validate_runtime` body (after docstring, before the pre-existing auth check). Order: enum check first → apipay `len(api_key.get_secret_value()) < 20` → `len(webhook_secret.get_secret_value()) < 32` → `is_production and payments_enabled and provider=="fake"`. Raw `get_secret_value()`, no strip semantics anywhere in the added code (strip scan: only pre-existing CORS/email helpers and `base_url.rstrip("/")` remain). No config.py field changes — diff touches only the method body.
- C2: `ValueError` guards are the FIRST statements of `ApiPayProvider.__init__` (before `self._secret = ...` and `httpx.Client`). Exact frozen texts "ApiPayProvider requires a non-empty api_key." / "...non-empty webhook_secret."
- C3: `if not self._secret: return False` sits AFTER the `if not signature` guard and BEFORE `hmac.new`; no other path reaches `hmac.new` in `verify_webhook`.
- C4: `RuntimeError` (not assert) `if settings.payments_provider != "fake"` placed before the `get_shared_fake` fallback, message byte-equal to the C1 enum message, with the explanatory comment about `python -O`.
- Message conformance verified programmatically (AST-adjacent-literal concatenation handled): all four frozen C1 substrings byte-match, including the contract-allowed two-literal wrap of the >=32 message.
- Untouched: fake.py, routes_webhooks.py, worker, entitlements, schemas, frontend, conftest.py. Only ApiPayProvider construction site in app/ is `provider.py:68` (get_provider). No API behavior change beyond fail-closed.

## GATES (real runs, cwd backend/, venv ./.venv, no extra flags)

| Gate | Command | Exit | Result |
|---|---|---|---|
| a | `./.venv/bin/python -m pytest tests/test_apipay_adapter.py tests/test_payments_config.py` | 0 | 28 passed |
| b | `./.venv/bin/python -m pytest tests/test_payment_webhook.py tests/test_payment_service.py tests/test_payment_reconcile.py tests/test_payment_provider.py` | 0 | 51 passed, 1 warning (pre-existing Starlette deprecation) |
| c | `./.venv/bin/python -m pytest tests/test_security.py tests/test_metrics.py tests/test_api.py tests/test_billing_api.py tests/test_paywall.py` | 0 | 132 passed, 1 warning (same pre-existing) |
| d | `./.venv/bin/python -m mypy app tests` | 0 | Success: no issues found in 164 source files (only pre-existing annotation-unchecked notes) |
| e | `./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m ruff format --check app tests` | 0 | All checks passed! / 164 files already formatted |
| f (optional pg) | `./.venv/bin/python -m pytest tests/test_jobs.py` | 0 | 30 passed (pgserver ephemeral; `ps` showed no other postgres before start) |

## ADVERSARIAL_NOTES

1. Bypass hunt — empty-secret webhook: no remaining path verifies with `b""` secret. C3 rejects before `hmac.new`; C2 makes `b""` unreachable at construction; the single production construction site is get_provider → apipay branch. R1 (forced `_secret = b""`, forged signature) is green on the candidate inside gate a. FakeProvider untouched by frozen contract (fallback secret never empty; production+fake+enabled refused at startup; payments_enabled=False → free).
2. Reaching ApiPayProvider with empty secrets post-fix — impossible silently, proven by live diagnostics (mocked get_settings to emulate the worker that skips validate_runtime): typo provider "apipy" → C4 RuntimeError with the exact frozen message; provider "apipay" + empty secrets → C2 ValueError ("non-empty api_key"); direct `ApiPayProvider(api_key="")` and `(webhook_secret="")` → C2 ValueError each.
3. Error precedence (C1-top insertion): live diagnostic — a production config violating BOTH payments (provider "apipy") and auth (auth_enabled=False) reports the payments message FIRST; a production config violating only auth reports `UNIMATCH_AUTH_ENABLED ...` as before, because with default payments config (fake, disabled) the payments block no-ops. Hence test_security/test_metrics still see their own messages for their configs — corroborated by gate c green (132 passed).
4. No lifespan-breaking fixture: grep across tests found payments config only in `tests/conftest.py:256-258` (provider "fake", dev), `tests/test_payment_service.py:24` (fake+enabled, dev), `tests/test_entitlements.py:22,153` (default fake). No fixture uses provider="apipay" with short secrets; developer claim verified. Gate b runs real lifespans (test_payment_webhook TestClient) and is green.
5. Residual (contract-accepted, not a violation): a worker-only deployment with provider="apipay" and a SHORT-but-nonempty secret still constructs (C2 is non-empty by frozen design; length enforcement lives in C1/validate_runtime, which the worker never calls). Worker fail-fast at boot is the frozen follow-up outside this task's reserved paths. Same for whitespace-only credentials — "no strip semantics" is exactly the frozen contract.

## BLOCKERS

None.

## NEXT_ACTION

Candidate `b55a3b0` is accepted from the QA side: hand to ashyq-reviewer (and security reviewer per money-path policy) on the same frozen SHA, then integrator for T34 → T35 → T36 merge order with affected gates re-run. QA does not grant final merge approval.
