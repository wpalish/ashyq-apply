# T35 A1 — QA TEST_AUTHOR report (campaign c3, findings S4+S5)

- ROLE_PHASE: ashyq-qa / TEST_AUTHOR
- STATUS: TESTS_READY
- CHECKED_SHA (baseline, verified before work): edf546de9f998c0909337d0abe6f8e1c9c4a0be5 (branch ai/c3/t35/qa, tree clean)
- COMMIT_SHA (QA commit): be9f2daf2eb4077632bb4db99e9293655c464cb7 (parent edf546d; only backend/tests/test_account_flows.py, 248 insertions, 0 deletions — pure append; tree clean after commit)
- Worktree: /Users/wpalish/ashyq-worktrees/c3-t35-qa

## TEST_FILES

- /Users/wpalish/ashyq-worktrees/c3-t35-qa/backend/tests/test_account_flows.py (appended; no existing test edits; test_logging_and_correlation.py NOT needed, untouched)

New tests (all in test_account_flows.py):
1. TestStarttlsUsesAVerifiedTlsContext::test_starttls_gets_a_verifying_ssl_context — RED-1 (S4)
2. TestStarttlsUsesAVerifiedTlsContext::test_starttls_verification_can_be_disabled_for_a_self_hosted_relay — RED-2 (S4, smtp_tls_verify=False → check_hostname False + CERT_NONE)
3. TestLoginRehashesOldCostHashes::test_login_upgrades_an_old_cost_hash_and_audits_it_once — RED-3 (S5; legacy hash_password(PASSWORD, n=2**12); prefix f"scrypt${2**settings.password_scrypt_log2}$"; needs_rehash False; exactly 1 AuditEvent action="password_rehashed" entity_id=user_id; second login byte-identical hash, still 1)
4. TestLoginRehashesOldCostHashes::test_a_wrong_password_on_a_legacy_account_rehashes_nothing — negative sibling (401, hash unchanged, 0 events)
5. TestLoginRehashesOldCostHashes::test_a_legacy_short_password_login_is_not_broken — GREEN-guard (hand-built "scrypt$4096$8$1$salt$digest" for a 10-char password via hashlib.scrypt matching security.py verify_password format; login 200, 0 audit rows)
6. TestProductionRefusesUnverifiedSmtp::test_production_refuses_to_start_without_smtp_tls_verification — GREEN-scenario (production base dict from test_metrics.py:250-259 + metrics_token set; smtp_tls_verify=False → pytest.raises(RuntimeError, match="UNIMATCH_SMTP_TLS_VERIFY"); True → validates clean)

Harness: module-level `_send_through_recording_smtp(monkeypatch, settings)` — RecordingSMTP double with smtplib.SMTP-compatible constructor (host, port positional; timeout kwarg), context manager, starttls(**kwargs) recorder; patched via `monkeypatch.setattr(mail_module.smtplib, "SMTP", RecordingSMTP)` exactly per contract.

## COMMANDS (all run in /Users/wpalish/ashyq-worktrees/c3-t35-qa/backend, venv ./.venv/bin/python)

- `git rev-parse HEAD` → edf546de9f998c0909337d0abe6f8e1c9c4a0be5; `git status --porcelain` → clean
- Probe (baseline honesty check): python -c Settings(demo_mode=True, email_sender="smtp", ..., smtp_tls_verify=False) → constructor ACCEPTED SILENTLY (extra="ignore"), hasattr False. Contract packet guessed TypeError; reality is silent ignore — RED classification below reflects the observed behavior.
- `./.venv/bin/python -m pytest tests/test_account_flows.py` (full module, no extra flags)
- `./.venv/bin/python -m pytest tests/test_account_flows.py -k "starttls or rehash or legacy_short_password or refuses_to_start_without_smtp_tls"`
- `./.venv/bin/python -m ruff format tests/test_account_flows.py` then `--check` (exit 0)
- `./.venv/bin/python -m ruff check tests/test_account_flows.py` (exit 0)
- `./.venv/bin/python -m mypy tests/test_account_flows.py` → "Success: no issues found in 1 source file"
- `./.venv/bin/python -m pytest tests/test_metrics.py tests/test_security.py` (baseline sanity, related modules)

## EXIT_CODES

- pytest tests/test_account_flows.py → 1 (4 failed, 32 passed) — expected RED on baseline
- targeted -k run → 1 (4 failed, 2 passed)
- pytest tests/test_metrics.py tests/test_security.py → 0 (36 passed)
- ruff format --check → 0; ruff check → 0; mypy (test file) → 0
- git commit → 0

## RED_RESULTS (baseline, real output)

1. test_starttls_gets_a_verifying_ssl_context:
   `assert context is not None, "STARTTLS was called without a context"` → `AssertionError: STARTTLS was called without a context` / `assert None is not None` (baseline starttls() carries no kwargs).
2. test_starttls_verification_can_be_disabled_for_a_self_hosted_relay:
   Same assertion failure (`context is None`). HONEST CLASSIFICATION: the RED is the missing context, not a constructor error — Settings(extra="ignore") silently drops the unknown `smtp_tls_verify` kwarg on baseline (verified by probe above); no TypeError/ValidationError occurs.
3. test_login_upgrades_an_old_cost_hash_and_audits_it_once:
   `AssertionError: a successful login must rewrite a weak-cost hash` — `assert stored != legacy` with stored == legacy == `scrypt$4096$8$1$a3700e6c...74b3629a...` (login 200, hash untouched, 0 audit rows — rehash path absent).
4. test_production_refuses_to_start_without_smtp_tls_verification:
   `Failed: DID NOT RAISE RuntimeError` at the pytest.raises(match="UNIMATCH_SMTP_TLS_VERIFY") block. HONEST CLASSIFICATION: unknown kwarg silently ignored (extra="ignore"), validate_runtime() passes clean on baseline; the production guard does not exist.

## GREEN_RESULTS (passing on baseline, as contracted)

- test_a_wrong_password_on_a_legacy_account_rehashes_nothing → PASS (401, hash unchanged, 0 events; expected to pass pre-fix).
- test_a_legacy_short_password_login_is_not_broken → PASS (hand-built scrypt$4096$ hash of "just-short" verifies; login 200; 0 audit rows). Pins the ValueError-guard semantics: must also pass post-fix via the except ValueError: pass path.
- All 30 pre-existing tests in test_account_flows.py → PASS (32 passed = 30 pre-existing + 2 guards above).
- test_metrics.py + test_security.py sanity → 36 passed.

## ASSERTIONS (binding, not relaxed anywhere)

- starttls called exactly once; kwargs["context"] is not None; context.check_hostname is True; context.verify_mode == ssl.CERT_REQUIRED (default path); check_hostname False + CERT_NONE only with explicit smtp_tls_verify=False.
- Login upgrade: stored != legacy; startswith(f"scrypt${2**settings.password_scrypt_log2}$") (= scrypt$16384$ under auth_client log2=14); verify_password True; needs_rehash False; AuditEvent(action="password_rehashed", entity_id=user_id) count == 1; second login: hash byte-identical, count still 1.
- Negative: wrong password → 401, hash unchanged, 0 events.
- Guard: short legacy password → 200, 0 events.
- Production: RuntimeError matching "UNIMATCH_SMTP_TLS_VERIFY" when smtp_tls_verify=False; clean validate_runtime() when True.

## ENVIRONMENT

- macOS darwin 25.6.0 arm64; Python 3.12 venv at /Users/wpalish/ashyq-worktrees/c3-t35-qa/backend/.venv (provisioned); SQLite per-test DB via auth_client fixture (tmp_path); offline; no network calls; no PostgreSQL run (suite under test is SQLite-based; parallel-task conflict avoided); no retries, no timeout bumps; no conftest.py edits; no production files touched (mail.py / config.py / routes_auth.py / payments / runner.py untouched).

## ARTIFACT_REFS

- Full module run log: /tmp/t35_module_run.txt
- QA commit: be9f2daf2eb4077632bb4db99e9293655c464cb7 (branch ai/c3/t35/qa, NOT pushed)
- This report: /Users/wpalish/ashyq-apply/ai-team/outputs/c3-t35-a1/qa-test-author.md

## REPRODUCED_BUGS

- S4 REPRODUCED: SmtpSender.starttls() on baseline receives no context kwarg (assert shows None) → unverified STARTTLS (mail.py:64).
- S5 REPRODUCED: successful login on a scrypt$4096$ account leaves the hash byte-identical and writes zero password_rehashed audit rows (routes_auth.py login never consults needs_rehash).

## UNTESTED_RISKS

- Concurrenct double-login double-rehash row (contract: accepted, up to 2 rows — not tested here; needs independent sessions at VERIFY phase).
- Real SMTP server protocol behavior beyond the RecordingSMTP double (no live STARTTLS negotiation tested — by design, offline).
- Full backend suite not run on baseline (not required by contract; PostgreSQL suites left to integration to avoid parallel-task resource conflicts).
- smtp_tls_verify=True default under real certificate failure paths is covered only implicitly by the CERT_REQUIRED assertion.

## BLOCKERS

None.

## NEXT_ACTION

Hand QA commit be9f2da to the main agent; Developer branches from it and implements the frozen fix (mail.py context, config.py smtp_tls_verify + validate_runtime hunk, routes_auth.py needs_rehash+audit insertion). Expect all 4 REDs to flip GREEN; both guards must stay GREEN.
