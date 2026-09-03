# Release checklist — ASHYQ Apply 1.0

Thirty gates. A release may be declared only when every one is green. Status is
recorded honestly: `PASS` means verified by a command whose output is shown in
the release report, not "implemented".

**Current verdict: NOT DEPLOYED.** 27 of the 30 original gates pass, one is
partial and one fails; the local container stack is still the unverified gate,
and the release commit/tag waits on it.

**next: Phase 2** of [`docs/FIX_PLAN.md`](docs/FIX_PLAN.md). Phase 0 (baseline)
and Phase 1 (P0 blockers 1.1–1.6) are done; gates 36–42 below record what each
fix is now held to. Phase 1 found that two of the three compose defects the
audit reported do not exist in this tree — see gate 22.

| # | Gate | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Existing 240 + 39 + 42 tests kept or replaced by stricter ones | **PASS** | 541 + 53 + 50 (25 desktop + 25 mobile). Nothing removed; Phase 1 added 14. The backend number is lower than the 547 recorded earlier because 25 PostgreSQL tests now *skip* on a machine without a working `pgserver` instead of erroring — they still run in CI |
| 2 | All new unit / integration / E2E / security tests green | **PARTIAL** | `pytest` 541 passed / 25 skipped (SQLite; the PostgreSQL branch could not be provisioned on this machine — `pgserver`'s `initdb.exe` fails here), `vitest` 53, `playwright` 25 desktop + 25 mobile |
| 3 | ruff, mypy, TypeScript, ESLint, production build clean | **PASS** | all clean; build 74.0 kB JS gzip |
| 4 | PostgreSQL migrations work on fresh and upgraded databases | **PASS** | Alembic. Verified fresh, downgrade to base, re-upgrade, re-apply as a no-op, on PostgreSQL 16.2 and SQLite. `create_all()` removed from the production path; startup refuses a mismatched revision |
| 5 | Worker survives a crash restart | **PASS** | `scripts/crash_test.py` SIGKILLs a real worker after 12 results are written; a second worker recovers the job and finishes with no duplicates. Stable over 3 runs. **PostgreSQL-backed queue, not Redis — see ADR 0001** |
| 6 | No run stuck `running` with no worker | **PASS** | Worker lease + heartbeat; `retryable_failed`; startup reconciliation; API reports `stale`. 7 tests |
| 7 | `candidate_limit` works | **PASS** | Persisted on the run, applied, capped against `verify_limit`, reused on retry. 3 tests |
| 8 | Playwright escalation actually invoked and recorded | **PASS** | Escalation inside `Fetcher`; per-page tier and per-run tier counts. 3 tests |
| 9 | Known live false positives no longer reproducible | **PASS** | 10 documented FPs, ~60 regression tests, live canary shows zero |
| 10 | MSc award never shown to a bachelor applicant without proof | **PASS** | `degree_applicability`; verified on the real van Effen page |
| 11 | Missing deadline never becomes "available" | **PASS** | Availability decomposed into 7 fields, all defaulting to unknown |
| 12 | Every material claim has an official evidence trail | **PASS** | Claim carries URL, verbatim excerpt, specificity, timestamp, status, method. Excerpt-provenance tests on both adapters |
| 13 | No silently inferred YES | **PASS** | Positive claims require positive evidence; audited in the canary |
| 14 | Auth and tenant isolation proven by tests | **PASS** | Opaque server sessions, `scrypt`, organizations and 404 ownership checks across every case/run/result/export endpoint; 17 security tests. Phase 1 closed the last hole: `set_decision` resolved no ownership at all, so any authenticated user could approve or reject rows on another organization's shortlist (gate 38) |
| 15 | No critical/high security findings | **PASS** | `pip-audit` and `npm audit` clean; 81 SSRF cases, DNS pinning, redirect/body limits, CSP/HSTS/origin checks, rate limits and `SECURITY.md` |
| 16 | No secrets or applicant data in git or logs | **PASS** | Secret scan clean; `.gitignore` hardened; audit-log leak test |
| 17 | Full profile editable in the UI and correct after reload | **PASS** | Tests, activities, achievements, evidence, academic record, funding and preference fields are editable; persistence/replacement covered by E2E |
| 18 | Multiple applicant cases | **PASS** | Cases are tenant-scoped profiles with create/switch UI and `/api/cases`; blank cases do not inherit demo identity data |
| 19 | Approve / reject / maybe and document collection work | **PASS** | Covered by E2E |
| 20 | CSV / JSON / XLSX exports carry provenance and data origin | **PASS** | 38 columns incl. source links, last-verified, data origin |
| 21 | Accessibility audit passed | **PASS** | axe WCAG A/AA scans every reachable workflow screen on desktop and mobile; focused keyboard/progress/table/overflow checks also pass |
| 22 | Docker Compose brings up a production-like stack | **FAIL** | One real defect fixed: the read-only `api` had no writable `/app/data`, and `ensure_dirs()` runs at import, so the container would have died with EROFS before serving a request. The audit's other two compose findings did not reproduce — the worker's `worker-cache:/app/data` matches `BACKEND_ROOT` for the image compose builds, and `backend/Dockerfile` already carries a `curl` HEALTHCHECK. `scripts/verify_compose.sh` drives the whole stack to a finished demo run. **WRITTEN, NOT RUN: Docker is not installed on this machine.** Requires a user checkpoint |
| 23 | Backup / restore and crash recovery verified | **PASS** | Real SIGKILL recovery plus a PostgreSQL `pg_dump`/`pg_restore` scratch-database drill: 12 tables and a synthetic probe restored identically |
| 24 | Documentation matches actual behaviour | **PASS** | Three README overstatements corrected; status banner added |
| 25 | No TODO / FIXME in a production path | **PASS** | `grep -rn "TODO\|FIXME" backend/app frontend/src` → none |
| 26 | No disabled or skipped tests without written justification | **PASS** | No xfails. 25 skips, all one justified case: the PostgreSQL fixture skips when `pgserver` cannot start a cluster (its `initdb.exe` fails on Windows). The reason is in the skip message and in `conftest.py`; Linux CI provisions the real server and runs them |
| 27 | Demo data unmistakably synthetic | **PASS** | Fixture banner, `fixture://` scheme, UI badge, export column. Loads only on an explicit confirmed action |
| 28 | Independent live truth audit across five canary universities | **PASS** | Ten official domains audited; 26/30 category pages, 0 zero-tolerance false positives. Programme recall remains honestly limited to 1/10; see `docs/LIVE_DISCOVERY_REPORT.md` |
| 29 | Local release commit/tag after all gates pass | **BLOCKED** | Gates open |
| 30 | Nothing pushed externally without permission | **PASS** | External publication occurs only after the user's explicit GitHub upload request |

### Added since the last review

| # | Gate | Status | Evidence |
|---|---|---|---|
| 31 | Jobs are durable across a restart of every process | **PASS** | Jobs are rows; 26 queue tests on real PostgreSQL |
| 32 | Two workers never claim the same job | **PASS** | `SELECT … FOR UPDATE SKIP LOCKED`; asserted with two concurrent sessions |
| 33 | Idempotency prevents duplicate work | **PASS** | Pre-check plus a unique constraint; both paths tested |
| 34 | A poison job dies rather than retrying forever | **PASS** | Attempts exhausted → `dead`, never re-claimed |
| 35 | Cancellation lands at a consistent point | **PASS** | Observed between units of work; a cancelled job is `cancelled`, not `succeeded` |

### Added by Phase 1 of the audit fix plan

| # | Gate | Status | Evidence |
|---|---|---|---|
| 36 | Retry never loses results or decisions | **PASS** | Retry used to delete every row while resetting only failed stages, so retrying a *successful* run left 0 of 20 results. Rows are now upserted and `_update_result` carries `user_decision`, its reason, notes and `decided_at` across. 4 tests in `TestRetry`, including the audit's exact recipe |
| 37 | Repeating document collection follows the shortlist | **PASS** | Key is a hash of the approved row ids, not their count. `TestDocumentIdempotency`: swapping one approval for another enqueues real work and the new row gets its checklist; an unchanged shortlist stays a no-op |
| 38 | Every result route is tenant-scoped | **PASS** | `owned_run` added to `set_decision`; all nine routes under `/api/runs/{run_id}` audited. `test_another_tenant_cannot_read_or_decide_a_result_row` proves the stranger gets 404 and the row keeps its decision |
| 39 | One research run per applicant per click | **PASS** | `Idempotency-Key` replays its own run (new `research_runs.client_request_key`, unique per profile) and an active run answers 409 naming the run to join; the client joins it instead of erroring. 3 API tests + 2 store tests |
| 40 | Rate limits bind the caller behind a proxy | **PASS** | `--proxy-headers` in every uvicorn command, `UNIMATCH_TRUST_PROXY_HEADERS` gating whether `X-Forwarded-For` is believed, a per-email login budget, and a dummy `scrypt` verify for unknown addresses. 3 tests in `TestAbuseLimits` |
| 41 | The retry buttons say what they do | **PASS** | Two buttons: "Retry from &lt;stage&gt;" passes the stage that stopped, "Re-run everything" confirms first and states decisions are kept. 4 tests in `ProgressScreen.test.tsx`. The single old button was labelled "from the failed stage" while calling the full retry |
| 42 | Playwright E2E re-run after Phase 1 | **PASS** | 25 desktop + 25 mobile, green, against the Phase 1 code. Getting there required two fixes: the launchers hardcoded the Linux venv layout so the `webServer` never started the API, and `playwright.config.ts` now invokes `run.sh` through bash rather than a shebang `cmd.exe` cannot read |

## Summary

- **PASS:** 27 (of 30 original) + 5 + 7 added by Phase 1
- **PARTIAL:** 1 (gate 2 — the PostgreSQL branch was not exercised on this machine)
- **FAIL:** 1 (gate 22 — the container stack has still never been run)
- **BLOCKED:** 1

## Order of work remaining

0. **Phase 2 of `docs/FIX_PLAN.md`** — P1 reliability and security (job-lease
   fencing, `enqueue` rolling back the caller's transaction, `budget_currency`
   ignored in scoring, stale-run UX, citizenship substring matching, ambiguous
   dates, the global `ValueError → 400` handler, header injection in the export
   filename, `/api/health` not touching the database, the missing auth flows)
1. ~~**P1** — PostgreSQL, Alembic, durable queue, crash recovery~~ **done** (gates 4, 5)
2. ~~**P2** — auth, organizations, cases, tenant isolation~~ **done**
3. ~~**P3** — SSRF suite, headers, rate limiting, threat model~~ **done**
4. ~~**P4** — full onboarding forms~~ **done**
5. **P5–P6** — improve programme-page classifier recall and deepen funding/document extraction
6. **P7** — run the container stack and verify a deployment (gate 22)
7. ~~**P8** — canary audit across ten institutions~~ **done**

## Needs the user

* **Running the container stack** requires Docker, which is not installed and
  cannot be installed without your password. The files are written; they have
  never been executed.
* **Any external deployment**, domain or billing.
