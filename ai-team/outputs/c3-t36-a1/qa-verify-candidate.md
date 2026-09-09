# T36 / A1 — ashyq-qa VERIFY_CANDIDATE output

- ROLE: ashyq-qa, PHASE: VERIFY_CANDIDATE (campaign c3, attempt A1)
- STATUS: **VERIFIED_FAIL**
- CHECKED_SHA: b7cdc812d39f3a12ac507d590a637e4f2185fd16 (branch ai/c3/t36/verify, worktree /Users/wpalish/ashyq-worktrees/c3-t36-verify)
- BASELINE edf546de9f998c0909337d0abe6f8e1c9c4a0be5 → QA 054331fa50a8069e0ff7d9d9b43ed6096b1169b7 → candidate b7cdc81

## 1. SCOPE_CHECK — PASS

- `git rev-parse HEAD` → b7cdc812d39f3a12ac507d590a637e4f2185fd16; `git status --porcelain` → empty before AND after all runs (worktree untouched by me).
- Ancestry confirmed (`git merge-base --is-ancestor` both steps OK; `git rev-list --count edf546d..HEAD` = 2).
- `git diff 054331f..HEAD --stat` → exactly: `backend/app/main.py` (15), `docker-compose.yml` (13), `scripts/verify_compose.sh` (33). Nothing else.
- `git diff 054331f..HEAD -- backend/tests/` → 0 lines: QA tests byte-identical, no assertion edits. `-- backend/app/config.py` → 0 lines: untouched (no T34/T35 conflict surface).

## 2. ANTI_WEAKENING_CHECK

### main.py client_address — PASS
- `hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]; return hops[-1]` — matches the master card's design snippet verbatim; empty/absent XFF falls through to socket peer ("unknown" if no client). XFF is read only inside `if settings.trust_proxy_headers:` — trust=False ignores XFF entirely (probe-verified below).
- Docstring now truthfully states the single-trusted-proxy append model (was: falsely claimed "first hop ... is the caller").
- Existing `TestAbuseLimits`: every XFF usage in test_security.py outside the new class is a single address (lines 219–444; first == last under both semantics). No pre-existing test relied on first-hop multi-hop keying; the 24 existing tests pass unmodified.

### docker-compose.yml — PASS
- api: `ports` removed, `expose: ["8099"]`; commented `# - "127.0.0.1:8099:8099"` variant present with truthful explanation (incl. that verify_compose.sh refuses it).
- Other services unchanged: web still publishes `"${WEB_PORT:-8080}:8080"`; postgres expose-only 5432; NO service publishes 8099. `UNIMATCH_TRUST_PROXY_HEADERS: "true"` retained in the shared env anchor.

### verify_compose.sh — awk gate PASS, probe rerouting FAIL (the blocker)
- **awk gate validated offline** on 5 `docker compose config`-shaped fixtures using the exact awk program (log: qa_t36_verify_awk_fixtures.log): expose-only → clean; api `published: "8099"` → flagged; **api loopback 8099 → flagged (STRICTER than QA's file test)**; web `published: "8080"` → not flagged (api-block scoping correct); host-remap `published: "9099"` targeting 8099 → **NOT flagged** (residual gap; the QA static test does catch "9099:8099" in the repo file, so the committed state stays guarded — gap only affects uncommitted local overrides).
- **Strictness adjudication: ACCEPTABLE.** The shipped compose has no ports at all, so both gates agree on the releasable state; the loopback variant is documented in-file as ad-hoc debugging, and stricter = fail-closed. No contradiction between the QA contract test and the script.
- **nginx path shape confirmed**: frontend/nginx.conf `location /api/ { proxy_pass http://api:8099; }` — proxy_pass WITHOUT a URI part forwards the original URI unchanged: `$WEB/api/health` → `api:8099/api/health`. Four of five probe URLs were reshaped correctly (`$API/auth/register`, `$API/profiles`, `$API/runs`, `$API/runs/$run`).
- **BLOCKING DEFECT — line 45 was not updated**: `body=$(curl -fsS "$API/api/health" ...)` with `API="$WEB/api"` requests `http://localhost:8080/api/api/health` → nginx passes it unchanged → `api:8099/api/api/health`. Empirically no such route exists: `routes_meta.router` serves exactly `/api/health`, `/api/capabilities`, `/api/vocabulary`, `/api/audit`; grep for `/api/api` across `app/` = 0 hits → FastAPI 404 → `curl -f` yields no body → the 60×2s loop never sees `"status"` → line 49 `[ -n "${body:-}" ] || fail` fires **unconditionally**. The script can NEVER reach PASS — the release gate is broken in the fail-closed direction. Line 49's fail message WAS updated to `$API/health` and therefore does not even match the URL actually requested on line 45 — evidence of a missed edit among the five probe URLs. developer.md disclosed the script was never executed (no docker).

## 3. GATES (real runs, verification worktree venv backend/.venv)

| gate | command | result | exit |
|---|---|---|---|
| a | `./.venv/bin/python -m pytest tests/test_security.py tests/test_compose_publishes_no_api_port.py` | **28 passed** in 24.03s | 0 |
| a-evidence | same, per-test (`-q -rA`) on the new class + compose file | **6 passed**: TestForwardedAddressSemantics::test_the_last_forwarded_hop_is_the_limiting_address / ::test_xff_is_ignored_when_proxy_headers_are_not_trusted / ::test_empty_or_absent_forwarded_for_charges_the_socket_peer; test_the_api_service_does_not_publish_its_port_to_the_host / test_the_api_port_stays_reachable_on_the_compose_network / test_verify_compose_script_is_present_for_release_gating | 0 |
| b | `./.venv/bin/python -m pytest tests/test_api.py tests/test_metrics.py` | **80 passed** in 34.36s | 0 |
| c | `./.venv/bin/python -m mypy app tests` | Success: no issues found in 165 source files | 0 |
| d | `./.venv/bin/python -m ruff check app tests` + `ruff format --check app tests` | All checks passed! / 165 files already formatted | 0 / 0 |
| e | `bash -n scripts/verify_compose.sh` | no output (syntax OK) | 0 |
| f | full verify_compose.sh run | **NOT_RUN** — packet forbids docker; the script also builds and starts the five-service stack. Offline validations substituted (above). Even if run, it would fail at the health probe due to the line-45 defect. | — |

## 4. ADVERSARIAL_NOTES

Function-level probes of `client_address` (synthetic starlette Requests, no network; log: qa_t36_verify_adversarial.log) — **14/14 PASS**:
- `"1.2.3.4, , 5.6.7.8,"` (trailing commas/spaces) → `5.6.7.8` (last non-empty hop); `" , , "` → socket peer.
- Spoofed single hop through nginx: nginx.conf sets `$proxy_add_x_forwarded_for` (APPENDS the real client), so `"9.9.9.9, <real>"` → `<real>` charged — spoofing defeated; multi-spoof prefix behaves the same.
- IPv6: `"1.2.3.4, 2001:db8::1"` → `2001:db8::1`; bare `"::1"` → `::1`; bracket-port form passes through as-is.
- trust=False + XFF present (both multi- and single-hop) → socket peer; absent/empty XFF → peer; no client in scope → `"unknown"`.
- Compose: no other service publishes 8099; web's 8080 publication intact; postgres expose-only.
- Residual (accepted by card): a two-proxy chain would charge the inner proxy (no `trusted_proxy_hops`); awk gate blind to host-port remapping of 8099 (repo file still guarded by the QA static test).

## 5. BLOCKERS

1. scripts/verify_compose.sh line 45: `"$API/api/health"` must become `"$API/health"` — otherwise the health probe hits `/api/api/health` (404) and the gate fails unconditionally. Fail-closed, not a security weakening, but it defeats the script's purpose as the release gate and contradicts its own line-49 message.

## 6. ENVIRONMENT / ARTIFACTS

- macOS darwin 25.6.0 arm64; Python 3.12 venv provisioned in the verification worktree; SQLite per-test; no docker daemon, no PostgreSQL server, no network calls; no files in the worktree modified by QA (tree clean at end, HEAD unchanged).
- Logs: /Users/wpalish/ashyq-apply/ai-team/outputs/c3-t36-a1/logs/qa_t36_verify_adversarial.log, qa_t36_verify_awk_fixtures.log (+ .sh, .py sources).
- main.py and docker-compose.yml portions of the candidate: verified good, no changes requested there.

## 7. NEXT_ACTION

Developer amends scripts/verify_compose.sh line 45 (`curl "$API/health"`), re-freezes a NEW candidate SHA; dispatcher dispatches a fresh VERIFY_CANDIDATE on it (rules: a new candidate requires new verification — this report does not carry over). Optional (non-blocking): tighten the awk gate to also catch host-remap publications targeting 8099. QA does not declare merge approval.
