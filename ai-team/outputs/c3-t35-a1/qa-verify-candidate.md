# T35 A1 — QA VERIFY_CANDIDATE report (campaign c3, findings S4+S5)

- ROLE_PHASE: ashyq-qa / VERIFY_CANDIDATE
- STATUS: VERIFIED_PASS
- CHECKED_SHA: 8bf1f5d08fe3d389e4ab6bb9c2d485932fd12e4f (branch ai/c3/t35/verify, tree clean)
- Worktree: /Users/wpalish/ashyq-worktrees/c3-t35-verify (independent verification worktree; venv Python 3.12.13)

## SCOPE_CHECK

- `git rev-parse HEAD` → 8bf1f5d08fe3d389e4ab6bb9c2d485932fd12e4f; `git status --porcelain` → empty (clean).
- Ancestry verified with `git merge-base --is-ancestor`: edf546d → be9f2da → 8bf1f5d, all YES.
- `git diff be9f2da..HEAD --stat` → exactly 3 files, +43/-2:
  - backend/app/api/routes_auth.py | 24 insertions, 1 deletion
  - backend/app/config.py | 10 insertions, 0 deletions
  - backend/app/mail.py | 9 insertions, 1 deletion
- `git diff be9f2da..HEAD -- backend/tests/` → empty (0 lines): QA tests byte-identical to the RED commit be9f2da. No other files changed (`--name-only` lists only the 3 production files). No T33/T34/T37 files touched; diff contains no payment/invoice/subscription keywords (grep exit 1 = no match).

## ANTI_WEAKENING_CHECK (read from the actual diff, not the developer report)

- mail.py: `import ssl` in the stdlib group; SmtpSender.send only: `ctx = ssl.create_default_context()`; `if not self.settings.smtp_tls_verify: ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE`; `smtp.starttls(context=ctx)`. Nothing else in the file changed — ConsoleSender, RecordingSender, get_sender, SMTP/port/timeout logic untouched (diff = 2 hunks only).
- config.py hunk 1: `smtp_tls_verify: bool = True` + docstring comment naming `UNIMATCH_SMTP_TLS_VERIFY`, positioned immediately after `smtp_from` (line 96 → field at :100), before `auth_require_verified_email`. Exactly as contracted.
- config.py hunk 2: in validate_runtime, immediately after the `UNIMATCH_SMTP_HOST is required` check (:205), before the `public_base_url` HTTPS check (:212). Single conjunct `self.is_production and not self.smtp_tls_verify`, no extra disjunct — as contracted.
- FROZEN MESSAGE verified BYTE-EXACT at runtime against the planner text: "UNIMATCH_SMTP_TLS_VERIFY must be true in production; STARTTLS without certificate verification would deliver password-reset mail through anyone on the path." → `message byte-exact vs frozen: True`. `smtp_tls_verify=True` + complete production base validates clean (exit 0). Also confirmed the new guard (:206) fires BEFORE the metrics check (:217).
- routes_auth.py: `AuditEvent` added to the models import (alphabetical, first); `needs_rehash` added after `hash_password` (alphabetical). Rehash block inserted EXACTLY between the membership-403 (`raise HTTPException(403, "This account has no active workspace.")`) and `create_session(...)`. Shape: `if needs_rehash(user.password_hash):` → try `user.password_hash = hash_password(payload.password)` / `except ValueError: pass` (commented) / else `session.add(AuditEvent(organization_id=membership.organization_id, actor="system", action="password_rehashed", entity_type="user", entity_id=user.id, detail={}))` + `session.commit()`. All kwargs per contract.
- Auth semantics otherwise untouched: auth-disabled 403, per-account rate limit 429, unknown-email shield (DUMMY_PASSWORD_HASH), verify_password 401, cookie settings — none in the diff.

## GATES (real runs, cwd /Users/wpalish/ashyq-worktrees/c3-t35-verify/backend, venv ./.venv/bin/python, no extra flags)

- a) `./.venv/bin/python -m pytest tests/test_account_flows.py` → "36 passed, 1 warning in 9.02s", exit 0. All 4 baseline REDs green; both guards green. `--collect-only` confirms all 6 QA tests present in the module (TestStarttlsUsesAVerifiedTlsContext x2, TestLoginRehashesOldCostHashes x3, TestProductionRefusesUnverifiedSmpt x1).
- b) `./.venv/bin/python -m pytest tests/test_security.py tests/test_metrics.py tests/test_logging_and_correlation.py` → "48 passed, 1 warning in 10.47s", exit 0.
- c) `./.venv/bin/python -m pytest tests/test_api.py` → "66 passed, 1 warning in 35.67s", exit 0.
- d) `./.venv/bin/python -m mypy app tests` → "Success: no issues found in 164 source files", exit 0 (pre-existing annotation-unchecked notes only).
- e) `./.venv/bin/python -m ruff check app tests` → "All checks passed!", exit 0; `./.venv/bin/python -m ruff format --check app tests` → "164 files already formatted", exit 0.

No skips/deselects in any gate output. No retries, no timeout increases.

## ADVERSARIAL_NOTES

- SMTP: `grep -rn starttls app/` → exactly ONE site (app/mail.py:72), and it carries `context=ctx`. No `SMTP_SSL`, no `ssl._create_unverified`, no other CERT_NONE/check_hostname writes anywhere in app/. The only unverified-context path is the explicit opt-out branch.
- Rehash bypass: `needs_rehash` referenced only at its definition (security.py:62) and the new login block (routes_auth.py:172). Other password_hash writers all use current-cost `hash_password(...)` (default n = 2**password_scrypt_log2 → needs_rehash False): registration routes_auth.py:98/106; routes_account.py:112 and :232 (password change, reset). No path writes a stale-cost hash that would skip or spuriously re-trigger.
- Dev principal: security.py:108 writes `password_hash="disabled"`; verify_password("...","disabled") fails at split-unpack (ValueError caught → False) → login unreachable for the dev user → no rehash interaction. Additionally needs_rehash("disabled") itself returns False (split-unpack guard).
- No new crash path in needs_rehash: the block is only reachable after verify_password returned True, which requires a well-formed `scrypt$n$...` string, so int(n) there cannot raise.
- ValueError guard: LoginIn.password is min_length=1, max_length=128 (routes_auth.py:45). The >128 hash_password bound is unreachable from login; the short-password guard is the live one and is pinned by test_a_legacy_short_password_login_is_not_broken (GREEN in gate a).
- Audit validity: membership 403 precedes the block, so organization_id is always a real membership's org id; AuditEvent.organization_id NOT NULL FK satisfied. actor="system" fits String(20); "password_rehashed" fits String(60, indexed); detail={} matches JSON default.
- Concurrency: confirmed NO unique constraint or locking was added (diff has none; audit_events has only non-unique indexes ix_audit_entity / ix_audit_organization_created). Sequential exactly-once holds by state (needs_rehash strict `<`); simultaneous double-login may write up to 2 audit rows — contract-accepted, harmless.

## ENVIRONMENT

- macOS darwin 25.6.0 arm64; Python 3.12.13 venv at /Users/wpalish/ashyq-worktrees/c3-t35-verify/backend/.venv; offline; no network calls.
- PG-free sweep classification: gates a/b/c run on SQLite per-test DBs (tests/conftest.py:135 `database_url=f"sqlite:///{tmp_path / 'test.db'}"`); test_api.py requests only the `client` fixture. The `postgres_url`/`pg_engine` fixtures (conftest.py:46/:65) are lazy and were NOT requested by any test in these gates — no PostgreSQL started, no resource slot consumed. Full `--cov` not run (integrator's gate).
- No production code, tests, T33/T34/T37 files, or conftest modified by this verification.

## RESULT

VERIFIED_PASS — candidate 8bf1f5d08fe3d389e4ab6bb9c2d485932fd12e4f implements the frozen contract exactly, no weakening detected, all affected gates green on the frozen SHA. (QA cannot declare final merge approval; handed back to the main agent for reviewer/integration.)

## UNTESTED_RISKS

- Real STARTTLS negotiation with a live/self-signed relay is covered only by the RecordingSMTP double and the CERT_REQUIRED assertion (offline by design).
- Concurrent double-login double-audit accepted but not exercised with independent sessions (contract-accepted; would need a PostgreSQL session-isolation run).
- Full backend suite / PostgreSQL suites / coverage floor left to integration.
- Operator friction risk (developer-noted, by design): upgrading self-hosted deployments with a relay whose certificate no public CA verifies must set UNIMATCH_SMTP_TLS_VERIFY=false in non-production, or production will refuse to start.

## BLOCKERS

None.

## NEXT_ACTION

Main agent may proceed to reviewer/security review of the frozen 8bf1f5d and integration (merge order T34 → T35; config.py hunks anchored to compose).
