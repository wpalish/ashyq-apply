# T35 A1 — DEVELOPER report (campaign c3, findings S4+S5)

- ROLE_PHASE: ashyq-developer / IMPLEMENT
- STATUS: IMPLEMENTED
- CHECKED_SHA (QA RED commit, verified base): be9f2daf2eb4077632bb4db99e9293655c464cb7 (branch ai/c3/t35/dev, tree clean at start; parent edf546de9f998c0909337d0abe6f8e1c9c4a0be5 = baseline)
- CANDIDATE_SHA (frozen, handed to review): 8bf1f5d08fe3d389e4ab6bb9c2d485932fd12e4f
- Worktree: /Users/wpalish/ashyq-worktrees/c3-t35-dev (branch ai/c3/t35/dev, tree clean after commit; NOT pushed)
- Contract: /Users/wpalish/ashyq-apply/ai-team/outputs/c3-t35-a1/planner.md (frozen hunks §1–§4)
- QA tests: untouched (backend/tests/test_account_flows.py byte-identical to be9f2da; git diff confirms only the 3 allowed production files changed)

## CHANGED_FILES (exact, +/-)

1. /Users/wpalish/ashyq-worktrees/c3-t35-dev/backend/app/mail.py (+9/-1)
   - import ssl (stdlib group)
   - SmtpSender.send: ctx = ssl.create_default_context(); if not settings.smtp_tls_verify → check_hostname=False, verify_mode=ssl.CERT_NONE; smtp.starttls(context=ctx). No other protocol change (no SMTP_SSL/port/timeout logic; ConsoleSender/RecordingSender/get_sender untouched).
2. /Users/wpalish/ashyq-worktrees/c3-t35-dev/backend/app/config.py (+10/-0)
   - Hunk 1 (after smtp_from, the contracted anchor :96): `smtp_tls_verify: bool = True` with docstring comment naming env UNIMATCH_SMTP_TLS_VERIFY.
   - Hunk 2 (validate_runtime, immediately after the UNIMATCH_SMTP_HOST check, before the public_base_url check — the contracted :201/:202 gap): `if self.is_production and not self.smtp_tls_verify: raise RuntimeError("UNIMATCH_SMTP_TLS_VERIFY must be true in production; STARTTLS without certificate verification would deliver password-reset mail through anyone on the path.")` — frozen message, single conjunct as contracted (email_sender check fires earlier in production).
3. /Users/wpalish/ashyq-worktrees/c3-t35-dev/backend/app/api/routes_auth.py (+24/-1)
   - Imports: AuditEvent added to app.models import; needs_rehash added to app.security imports (after hash_password, alphabetical).
   - login(): rehash block inserted exactly between the membership-403 and create_session: `if needs_rehash(user.password_hash):` → try `user.password_hash = hash_password(payload.password)` except ValueError: pass (comment) else: session.add(AuditEvent(organization_id=membership.organization_id, actor="system", action="password_rehashed", entity_type="user", entity_id=user.id, detail={})) + session.commit().

Total: 3 files, +43/-2. No migrations. No new dependencies. security.py untouched (helpers were correct). No test files touched; all QA assertions intact.

## GATES (real runs, cwd /Users/wpalish/ashyq-worktrees/c3-t35-dev/backend, venv ./.venv)

- a) `./.venv/bin/python -m pytest tests/test_account_flows.py` → 36 passed, exit 0 (QA baseline: 4 failed / 32 passed → all 4 RED flipped GREEN; 2 guards and 30 pre-existing stay GREEN)
- b) `./.venv/bin/python -m pytest tests/test_security.py tests/test_metrics.py tests/test_logging_and_correlation.py` → 48 passed, exit 0 (validate_runtime + logging neighbors)
- c) `./.venv/bin/python -m pytest tests/test_api.py` → 66 passed, exit 0 (auth routes regression)
- d) `./.venv/bin/python -m mypy app tests` → "Success: no issues found in 164 source files", exit 0 (only pre-existing informational annotation-unchecked notes)
- e) `./.venv/bin/python -m ruff check app tests` → "All checks passed!"; `./.venv/bin/python -m ruff format --check app tests` → "164 files already formatted", exit 0

## RED_TO_GREEN

- RED-1 test_starttls_gets_a_verifying_ssl_context: GREEN — starttls now receives context=ctx with check_hostname True, verify_mode CERT_REQUIRED by default.
- RED-2 test_starttls_verification_can_be_disabled_for_a_self_hosted_relay: GREEN — explicit smtp_tls_verify=False yields check_hostname False + CERT_NONE.
- RED-3 test_login_upgrades_an_old_cost_hash_and_audits_it_once: GREEN — legacy scrypt$4096$ hash rewritten to scrypt$16384$ at first login, verify ok, needs_rehash False, exactly 1 password_rehashed AuditEvent; second login byte-identical, still 1.
- GREEN-guard wrong-password: still GREEN — 401, hash unchanged, 0 events.
- GREEN-guard legacy short password: still GREEN — hand-built scrypt$4096$ hash of a 10-char password logs in 200 via the except ValueError: pass path, 0 events.
- GREEN-scenario production refusal: GREEN — RuntimeError matching "UNIMATCH_SMTP_TLS_VERIFY" when False; validate_runtime() clean when True.

## DESIGN_NOTES

- Implemented byte-for-byte within frozen contract §1–§4; no deviations in shape, message text, audit kwargs, or insertion anchors. T34's config.py territory (validate_runtime TOP insertion) untouched — my two hunks are anchored as agreed; integration merge order T34 → T35 holds.
- The frozen except ValueError: pass shape vs ruff: B110 (try-except-pass) does not fire because the except body carries a comment — verified empirically against the project's ruff 0.9.6 with the exact shape before writing (isolated --select B probe, exit 0). No suppress/alternative needed; contract shape kept verbatim.
- needs_rehash + membership ordering: the block sits after the membership 403, so organization_id for the AuditEvent is always valid, per contract.
- Exactly-once semantics by state: the rewritten hash no longer satisfies needs_rehash (strict <), so subsequent logins are no-ops; concurrent double-login may write up to 2 audit rows — accepted by contract, no lock added.

## RESIDUALS

- Concurrency: two simultaneous logins on one legacy account can rehash twice / write up to 2 audit rows (contract-accepted; flagged by QA as untested at VERIFY — needs independent sessions).
- Real STARTTLS negotiation is only covered by the RecordingSMTP double (offline by design); a genuinely self-signed relay failure path is covered implicitly by CERT_REQUIRED.
- smtp_tls_verify defaults to True for every existing self-hosted deployment that upgrades: a relay whose certificate no public CA verifies will now fail to send until the operator sets UNIMATCH_SMTP_TLS_VERIFY=false (production additionally refuses to start with it false — intended friction; release notes should call this out).
- Full backend suite / PostgreSQL-based suites not run here (parallel-task resource coordination; left to integration per contract).

## BLOCKERS

None.

## NEXT_ACTION

Freeze candidate 8bf1f5d08fe3d389e4ab6bb9c2d485932fd12e4f for independent QA verification and reviewer read on that SHA; integration merges T34 → T35 (config.py anchored hunks designed to compose).
