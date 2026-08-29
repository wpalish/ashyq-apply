# Release evidence — 2026-08-29

Every row is a command that was run on `claude/production-completion`, with the
result it produced. A gate is PASS only when its command was executed here.

## Environment

| | |
|---|---|
| Machine | macOS (darwin 25.5.0), Apple Silicon |
| Python | 3.12.13 in `backend/.venv` |
| Node | 22 |
| PostgreSQL | 16.2, provisioned in-process by `pgserver` via `scripts/pg.py` |
| Container runtime | **none installed** — `docker`, `podman`, `colima`, `nerdctl`, `lima` all absent |
| Left untouched | port 8199 and the `cloudflared` tunnel serving the public demo |

## Commands and results

| Gate | Command | Result |
|---|---|---|
| Lint (backend) | `.venv/bin/ruff check app tests scripts` | **PASS** — All checks passed |
| Types (backend) | `.venv/bin/mypy app tests scripts/canary_discovery.py` | **PASS** — no issues, 102 source files |
| Backend, SQLite | `UNIMATCH_DATABASE_URL=sqlite:///… pytest` | **PASS** — 772 passed |
| Backend coverage | `pytest --cov=app --cov-fail-under=80` | **PASS** — 89.93% |
| Backend, PostgreSQL | `.venv/bin/python scripts/pg.py .venv/bin/pytest` | **PASS** — 772 passed |
| Frontend types | `npm run typecheck` | **PASS** — clean |
| Frontend lint | `npm run lint` | **PASS** — clean |
| Frontend unit | `npm test -- --run` | **PASS** — 47 passed, 4 files |
| Frontend build | `npm run build` | **PASS** — 74.46 kB JS gzip, 5.32 kB CSS; no source map emitted |
| E2E | `npm run e2e` | **PASS** — 52 passed, desktop + mobile |
| Accessibility | axe WCAG 2.0/2.1 A+AA, inside the E2E run | **PASS** — no serious or critical violations on any reachable screen, both projects |
| Responsive | 320 / 375 / 768 / 1024 / 1440 / 1920 | **PASS** — no horizontal overflow |
| Python deps | `pip-audit -r backend/requirements.txt` | **PASS** — no known vulnerabilities |
| Node deps | `npm audit --audit-level=high` | **PASS** — 0 vulnerabilities |
| Migrations | `alembic upgrade head` → `downgrade base` → `upgrade head` → `upgrade head` | **PASS** — fresh, downgrade, re-upgrade, and a re-apply that is a no-op |
| Crash recovery | `.venv/bin/python scripts/crash_test.py` | **PASS** — real SIGKILL after 12 results; recovered on attempt 2, 12 unique, 0 duplicates. Reports INCONCLUSIVE (exit 2) when the kill lands after the job finished, which is a race in the harness |
| Backup / restore | `scripts/pg.py … scripts/backup_drill.py` | **PASS** — 12 tables restored with identical row counts, 109,038-byte dump, scratch database |
| Registry seeds | `scripts/canary_discovery.py --check-seeds` | **PASS** — 0 of 33 no longer resolve |
| Live canary ×3 | `scripts/canary_discovery.py --out …` | **FAIL against its bar** — 4, 4, 4 programme pages of ten (bar: median 8, worst 7). 27/30 category pages, which meets its bar. **0 false positives in every run** |
| Holdout canary | `scripts/canary_discovery.py --registry …/holdout_registry.json` | **FAIL against its bar** — 1 of 6 (bar: 4 of 5). 0 false positives |
| SSRF | ad-hoc probe of 14 loopback / private / metadata forms | **PASS** — all refused, while `curl` reached the same loopback service, proving the target was up |
| Tenant isolation | `pytest tests/test_tenant_isolation_exhaustive.py` | **PASS** — all 17 id-bearing routes refuse another tenant with 404; the probe set derives from the app's OpenAPI schema |
| Secrets | tracked files, full git history, `.env*`, built bundle | **PASS** — none found |
| TODO / FIXME | `grep -rn "TODO\|FIXME" backend/app frontend/src` | **PASS** — none |
| Skipped tests | `grep -rn "skip\|xfail\|.only("` | **PASS** — none |
| Container runtime | `scripts/compose_smoke.sh` (CI job `container-runtime`) | **BLOCKED** — written, never executed; no container runtime on this machine and installing one needs an admin password |

## What the numbers were at baseline

| | Baseline (`ea7948c`) | Now |
|---|---|---|
| Backend tests | 553 | **772** |
| Frontend unit | 47 | 47 |
| E2E | 50 | **52** |
| Coverage | 90.02% | 89.93% |
| Programme pages (live) | 1/10 | **4/10** |
| Category pages (live) | 26/30 | **27/30** |
| Live false positives | 0 | **0** |
| `runner.py` | 967 lines | **708** |

Coverage moved down by 0.09 points while 219 tests were added, because the new
code — the FX provider's error paths, the browser-render branch — includes
paths that only a live failure exercises.
