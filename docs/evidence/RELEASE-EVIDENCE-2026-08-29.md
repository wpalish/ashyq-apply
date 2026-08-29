# Release evidence — 2026-08-29

Every row below is a command that was run on `claude/production-completion`,
with the result it produced. A gate is PASS only when its command was executed
here and its output read. Rows that were not run say so.

Measured at `1527e2d`, except the live-discovery rows, which were measured at
`0af7daa` — the last commit before the series started. Nothing affecting
discovery changed between the two; the only later change is how the canary
*reports* a failed institution.

The live-discovery rows are three consecutive runs of the ten-institution
canary plus one run of the frozen six-institution holdout, all at that one
commit, with no code change between them.

## Environment

| | |
|---|---|
| Machine | macOS (darwin 25.5.0), Apple Silicon |
| Python | 3.12.13 in `backend/.venv` |
| Node | 22 |
| PostgreSQL | 16.2, provisioned in-process by `pgserver` via `scripts/pg.py` |
| Container runtime | **none installed** — `docker`, `podman`, `colima`, `nerdctl`, `finch` and `lima` are all absent, and `docker info` finds no daemon |

## Commands and results

| Gate | Command | Result |
|---|---|---|
| Lint (backend) | `.venv/bin/python -m ruff check .` | **PASS** — All checks passed |
| Types (backend) | `.venv/bin/python -m mypy app` | **PASS** — no issues in 78 source files |
| Backend, SQLite | `.venv/bin/python -m pytest` | **PASS** — 977 passed |
| Backend coverage | `pytest --cov=app --cov-fail-under=80` | **PASS** — 90.65%, 6083 statements, 569 missed |
| Backend, PostgreSQL | `scripts/pg.py .venv/bin/python -m pytest` | **PASS** — 977 passed |
| Frontend types | `npx tsc --noEmit` | **PASS** — clean |
| Frontend lint | `npx eslint src e2e` | **PASS** — clean |
| Frontend unit | `npx vitest run` | **PASS** — 56 passed, 6 files |
| Frontend build | `npm run build` | **PASS** — 253.10 kB JS (74.98 kB gzip), 25.55 kB CSS (5.49 kB gzip); no source map emitted |
| E2E | `npx playwright test` | **PASS** — 52 passed, desktop-chromium and mobile |
| Accessibility | axe WCAG 2.0/2.1 A + AA, inside the E2E run | **PASS** — no serious or critical violations on any reachable screen, both viewports |
| Python deps | `pip_audit` | **PASS** — no known vulnerabilities |
| Node deps | `npm audit` | **PASS** — 0 vulnerabilities |
| Migrations | `alembic upgrade head` → `downgrade base` → `upgrade head` → `upgrade head` | **PASS** — all four exit 0; the final re-apply is a no-op |
| Crash recovery | `.venv/bin/python scripts/crash_test.py` | **PASS** — real SIGKILL mid-run; recovered, re-attempted, finished, no duplicates |
| Backup / restore | `scripts/pg.py … scripts/backup_drill.py` | **PASS** — 12 tables restored with identical row counts, 109,126-byte dump, scratch database |
| Registry seeds | `scripts/canary_discovery.py --check-seeds` | **PASS** — 0 of 33 seeds fail to resolve |
| SSRF | `pytest -k ssrf` | **PASS** — 90 passed |
| Tenant isolation | `pytest tests/test_tenant_isolation_exhaustive.py` | **PASS** — 8 passed; the probe set derives from the app's own OpenAPI schema |
| Secrets | tracked files, `.env*`, built bundle | **PASS** — none found; `.env.example` holds placeholders only |
| TODO / FIXME | `grep -rn "TODO\|FIXME" backend/app frontend/src` | **PASS** — 0 |
| Skipped tests | `grep -rnE "@pytest.mark.skip\|xfail\|\.only\(\|\.skip\("` | **PASS** — 0 |
| **Live canary ×3** | `scripts/canary_discovery.py --out …` | **PASS** — 8, 8, 8 programme pages of ten. Median 8 against a bar of 8; worst 8 against a bar of 7. Category pages 28/30 against a bar of 27. Scholarship pages 10/10 against a bar of 9. **0 false positives in every run** |
| **Holdout canary** | `scripts/canary_discovery.py --registry …/holdout_registry.json` | **FAIL against its bar** — 3 of 6 against a bar of 4. 0 false positives. The registry was not edited and no seed was added |
| Container runtime | `scripts/compose_smoke.sh` | **BLOCKED — not run.** No container runtime exists on this machine and installing one needs an admin password. The script is written and reviewed; it has never been executed |

## Live discovery in detail

Identical across all three runs, which is itself worth recording: discovery is
deterministic on this registry.

| | Result | Bar | |
|---|---|---|---|
| Programme pages, median of 3 runs | **8/10** | ≥ 8 | met |
| Programme pages, worst run | **8/10** | ≥ 7 | met |
| Category pages (admissions + costs + scholarships) | **28/30** | ≥ 27 | met |
| Scholarship pages | **10/10** | ≥ 9 | met |
| Zero-tolerance false positives | **0** | 0 | met |
| Holdout programme pages | **3/6** | ≥ 4 | **not met** |
| Material claims per run | 51 | — | 30 at the start of this session |

All 20 accepted programme pages were read by hand. Every one is a named,
specific programme at bachelor level — Groningen's Computing Science, Delft's
Computer Science and Engineering, Aalto's Computer Engineering, Vienna's
Computer Science, UBC's three Computer Science degrees, Toronto's Computer
Science, Applied Data Science and Data Science, HKU's Cambridge joint scheme,
and NTU's three computing degrees. No catalogue, hub, faculty or department
page is among them.

### The three institutions still missed

| Institution | Why |
|---|---|
| University of Warsaw | Its catalogue renders 64 links and lists no programme for this subject. The chain continues one hop further into a page that is itself a listing. Honest NOT_FOUND |
| KAIST | Publishes no programme catalogue. Its programmes sit behind a "College & Department" link whose URL and wording name no subject. Following it would be fitting to one site |
| Tecnológico de Monterrey (holdout) | `robots.txt` disallows the paths involved. Permanent and correct — the crawler obeys it |

Cape Town and Tokyo are also missed on the holdout. Tokyo serves no sitemap and
only seven pages were reachable. Cape Town publishes its undergraduate
programme detail in faculty handbook PDFs and on faculty subdomains rather than
as per-programme pages.

## What changed in this session

33 commits on top of `2ebcbc6`. The three P1 defects named at the start were
fixed first, before any discovery or extraction work:

| Defect | Commit | Evidence it is fixed |
|---|---|---|
| Two concurrent runs could swap exchange rates | `36c5590` | The process-global provider is gone; the provider is constructed per run and passed explicitly. `tests/test_fx_isolation.py` |
| Evidence and Open questions sheets could execute formulas | `94f211b` | Every sheet writes through one `safe_cells` boundary, headers and disclaimers included, enforced by an AST test rather than by convention |
| A German citizen was refused an EU-only scholarship | `2763b50` | Country and bloc membership is modelled with a stated as-of date; restrictions carry their own `any`/`all` logic and per-restriction evidence |

## Size

| | |
|---|---|
| Backend | 78 Python files, 15,536 lines |
| Frontend | 27 TypeScript files, 5,051 lines |
| Tests | 977 backend, 56 frontend unit, 52 E2E |
| Page fixtures | 22 real pages, saved as served |
| `runner.py` | 712 lines |
| `page_classifier.py` | 957 lines |
| `live_discovery.py` | 904 lines |

## A note on one earlier commit

`626f9b1` ("docs: correct three numbers…") accidentally included 35 screenshot
binaries, swept in by a `git add -A docs`. Every delta was under 2% and
consistent with render noise rather than a change in the interface. The history
has been built on since, so it is reported here rather than rewritten.

Screenshots committed later in this session are deliberate: the interface
genuinely changed, and screenshots showing "Yes / Maybe / No" would document a
product that no longer exists.
