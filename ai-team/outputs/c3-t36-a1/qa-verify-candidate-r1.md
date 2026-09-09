# T36 / A1 repair R1 — ashyq-qa VERIFY_CANDIDATE output

- ROLE: ashyq-qa, PHASE: VERIFY_CANDIDATE (campaign c3, attempt A1, repair re-verify R1)
- STATUS: **VERIFIED_PASS**
- CHECKED_SHA: f9c90bf90f057d35c6ef72fcf70bdd14afc8bd80 (branch ai/c3/t36/verify, worktree /Users/wpalish/ashyq-worktrees/c3-t36-verify)
- BASELINE edf546de9f998c0909337d0abe6f8e1c9c4a0be5 → QA 054331fa50a8069e0ff7d9d9b43ed6096b1169b7 → prev candidate b7cdc812 (VERIFIED_FAIL) → repair f9c90bf

## 1. SCOPE_CHECK — PASS

- `git rev-parse HEAD` → f9c90bf90f057d35c6ef72fcf70bdd14afc8bd80; `git status --porcelain` → empty before AND after all runs (0 lines; fixtures ran in /tmp, logs written outside the worktree).
- Ancestry confirmed with `git merge-base --is-ancestor` (edf546d→054331f→b7cdc81→f9c90bf, all OK); `git rev-list --count edf546d..HEAD` = 3; `git log --oneline -4` shows the exact three expected commits.
- `git diff b7cdc81..HEAD --stat` → exactly `scripts/verify_compose.sh | 2 +-` (1 insertion, 1 deletion). The hunk is line 45 only: `"$API/api/health"` → `"$API/health"`. Nothing else changed in the repair.
- `git diff 054331f..HEAD --stat` → `backend/app/main.py` (15), `docker-compose.yml` (13), `scripts/verify_compose.sh` (35). `--name-only` confirms exactly these 3 files.
- `git diff 054331f..HEAD -- backend/tests/` → 0 lines: QA tests byte-identical, no assertion edits. `-- backend/app/config.py` → 0 lines (also 0 vs b7cdc81): untouched, no T34/T35 conflict surface.
- Commit carries trailer `Agent: ashyq-developer` and names T36.

## 2. URL_INVENTORY_VERDICT — all probes resolve to real routes; the previous blocker is gone

Base construction: `WEB="http://localhost:${WEB_PORT:-8080}"` (L14), `API="$WEB/api"` (L17) → base `http://localhost:8080/api`.
Proxy semantics: frontend/nginx.conf `location /api/ { proxy_pass http://api:8099; ... }` — proxy_pass WITHOUT a URI part, so nginx forwards the original request URI unchanged. Every probe below therefore reaches the API container with its full `/api/...` path.

| script line | constructed URL | upstream path (api:8099) | real route | verdict |
|---|---|---|---|---|
| L45 probe | `$API/health` | `/api/health` | routes_meta `APIRouter(prefix="/api")` + `@router.get("/health")` | **OK — the R1 fix** |
| L49 fail msg | `$API/health` | message only | — | OK, now matches the L45 URL |
| L58 probe | POST `$API/auth/register` | `/api/auth/register` | routes_auth `prefix="/api/auth"` + `@router.post("/register")` | OK |
| L68 probe | POST `$API/profiles` | `/api/profiles` | routes_profile `prefix="/api/profiles"` + `@router.post("")` | OK |
| L73 probe | POST `$API/runs` | `/api/runs` | routes_research `prefix="/api/runs"` + `@router.post("")` | OK |
| L78 probe | GET `$API/runs/$run` | `/api/runs/{run_id}` | routes_research `@router.get("/{run_id}")` | OK |
| L86 probe | GET `$WEB` | `/` (nginx static, no API) | nginx `location /` try_files → index.html | OK |

Independent corroboration:
- `grep -rn "api/api" backend/app/` → 0 hits: no route exists that could serve a doubled `/api/api/...` prefix, so the previous failure mode is structurally eliminated, not just re-pointed.
- routes_meta `/api/health` returns `{"status": "ok", ...}` — the L46 pattern `*'"status"'*` matches on success; on DB failure the route returns 503 + `"status": "degraded"`, `curl -fsS` yields no body via `-f`, the loop exhausts and L49 fails — correct fail-closed behavior retained.
- L86 `grep -qi "<title"` is served by the web container's static index.html — no API dependence.
- All five API probes traverse the same nginx proxy and the same security-middleware rate-limit paths (`/api/auth/register`, `/api/runs` are literal limiter keys in main.py) as real users — the gate exercises the user path, no probe bypasses abuse limits.

## 3. GATES (real runs; verification worktree venv backend/.venv, Python 3.12.13; no extra -q)

| gate | command | result | exit |
|---|---|---|---|
| a | `./.venv/bin/python -m pytest tests/test_security.py tests/test_compose_publishes_no_api_port.py` | **28 passed** in 20.51s (1 pre-existing deprecation warning) | 0 |
| b | `./.venv/bin/python -m pytest tests/test_api.py tests/test_metrics.py` | **80 passed** in 36.29s | 0 |
| c | `./.venv/bin/python -m mypy app tests` | Success: no issues found in 165 source files (2 pre-existing `[annotation-unchecked]` notes) | 0 |
| d | `./.venv/bin/python -m ruff check app tests` + `ruff format --check app tests` | All checks passed! / 165 files already formatted | 0 / 0 |
| e | `bash -n scripts/verify_compose.sh` | no output (syntax OK) | 0 |
| f | full verify_compose.sh run | **NOT_RUN** — packet forbids docker; the script builds and starts the five-service stack. Offline validations substituted (§2, §4). | — |

## 4. ADVERSARIAL_NOTES

- **awk no-8099-publication gate untouched and re-validated on the current text.** The b7cdc81..f9c90bf diff proves the entire repair is one line (L45), so the awk program bytes are identical to the 5-fixture-validated version from the previous verification. I additionally extracted the program verbatim from the f9c90bf script and re-ran it on fresh `docker compose config`-shaped fixtures (log qa_t36_r1_awk_spot.log): expose-only api → CLEAN; api `published: "8099"` → FLAGGED; api loopback (`host_ip: 127.0.0.1`, `published: "8099"`) → FLAGGED (still stricter than the QA file test); web `published: "8099"` → CLEAN (api-block scoping correct).
- **Env interpolation cannot reintroduce publication:** `grep -rn "API_PORT" docker-compose.yml scripts/verify_compose.sh backend/app/config.py` → 0 hits. `${API_PORT}` no longer exists anywhere; the only env-interpolated port mapping is web's `${WEB_PORT:-8080}:8080` (allowed, different service and port). Also, the gate scans `docker compose config` output, which interpolates env vars, so an interpolated publication would still be flagged post-interpolation.
- **Commented loopback mapping is inert and guarded:** docker-compose.yml L82–83 (`# ports:` / `# - "127.0.0.1:8099:8099"`) are YAML comments — they are stripped before the config stage and can never appear in `docker compose config` output, so they cannot activate the awk gate; if uncommented, the loopback fixture above shows the gate flags it.
- **docker-compose.yml state (unchanged from prev verification):** api has no `ports:` at all, `expose: ["8099"]`; postgres expose-only 5432; only web publishes (`${WEB_PORT:-8080}:8080`); `UNIMATCH_TRUST_PROXY_HEADERS: "true"` retained in the shared env anchor — consistent with expose-only.
- **Residual (unchanged, non-blocking, accepted by card):** awk gate blind to host-port remapping of 8099 (e.g. `9099:8099`) — repo file guarded by the QA static test, gap only for uncommitted local overrides; a two-proxy chain would charge the inner proxy; full-script end-to-end run still requires docker and remains NOT_RUN by QA.

## 5. BLOCKERS

None. The single R0 blocker (L45 double `/api`) is fixed and is the whole repair delta.

## 6. ENVIRONMENT / ARTIFACTS

- macOS darwin 25.6.0 arm64; verification worktree /Users/wpalish/ashyq-worktrees/c3-t36-verify, branch ai/c3/t36/verify at f9c90bf; venv backend/.venv Python 3.12.13 (provisioned, not modified); SQLite per-test; no docker, no PostgreSQL, no network, no E2E; worktree left clean, HEAD unchanged.
- Logs: /Users/wpalish/ashyq-apply/ai-team/outputs/c3-t36-a1/logs/qa_t36_r1_gate_a.log, qa_t36_r1_gate_b.log, qa_t36_r1_gate_c.log, qa_t36_r1_gate_d.log, qa_t36_r1_awk_spot.log.
- docker run NOT_RUN (packet prohibition); no push, no deploy, no production data.

## 7. NEXT_ACTION

Dispatch ashyq-reviewer and ashyq-security (mandatory roles for T36) on the SAME frozen SHA f9c90bf90f057d35c6ef72fcf70bdd14afc8bd80; then integrator (T34 → T35 → T36 order). A first real docker run of scripts/verify_compose.sh by the release-gate owner remains advisable before release (QA could not execute it). QA does not declare merge approval.
