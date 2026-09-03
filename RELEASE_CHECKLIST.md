# Release checklist — ASHYQ Apply 1.0

Thirty gates. A release may be declared only when every one is green. Status is
recorded honestly: `PASS` means verified by a command whose output is shown in
the release report, not "implemented".

**Current verdict: NOT DEPLOYED.** 27 of the 30 original gates pass, one is
partial and one fails; the local container stack is still the unverified gate,
and the release commit/tag waits on it.

**next: Phase 4** of [`docs/FIX_PLAN.md`](docs/FIX_PLAN.md). Phase 0
(baseline), Phase 1 (P0 blockers), Phase 2 (P1 reliability and security) and
Phase 3 (P2 UX, 3.1–3.14) are done; gates 36–73 below record what each fix is
now held to. Two audit findings did not reproduce against this tree and are
recorded as such rather than "fixed" — see gates 22 and 47.

| # | Gate | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Existing 240 + 39 + 42 tests kept or replaced by stricter ones | **PASS** | 656 + 93 + 54 (27 desktop + 27 mobile). Nothing removed; Phase 1 added 14, Phase 2 added 65, Phase 3 added 50. The backend number is lower than the 547 recorded earlier because 25 PostgreSQL tests now *skip* on a machine without a working `pgserver` instead of erroring — they still run in CI |
| 2 | All new unit / integration / E2E / security tests green | **PARTIAL** | `pytest` 656 passed / 25 skipped (SQLite; the PostgreSQL branch could not be provisioned on this machine — `pgserver`'s `initdb.exe` fails here), `vitest` 93, `playwright` 27 desktop + 27 mobile |
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

### Added by Phase 2 of the audit fix plan

| # | Gate | Status | Evidence |
|---|---|---|---|
| 43 | A worker that lost its lease stops and records nothing | **PASS** | Every terminal job update is fenced on (running, worker_id); the runner's checkpoint raises LeaseLost when the job is no longer ours, so the abandoned attempt stops between units of work. 4 tests in `TestLeaseFencing` |
| 44 | `enqueue` never rolls back the caller's transaction | **PASS** | The insert runs in a SAVEPOINT. Test forces the unique-key race and asserts the caller's own pending change survives |
| 45 | Budget and cost are compared in the same currency | **PASS** | The ceiling is converted through the bundled snapshot with the rate and date in the explanation; an unsupported currency is honestly absent. A 2,880,000 KZT ceiling used to read as infinite against a 6,000 USD gap. 3 tests |
| 46 | One lease definition, and a heartbeat that keeps up with it | **PASS** | `is_lease_expired` resolves `UNIMATCH_JOB_LEASE_SECONDS`; verification saves progress, counters and heartbeat after every candidate rather than every fourth. 3 tests |
| 47 | A dead run is visible and escapable in the UI | **PASS** | ProgressScreen renders `stale`, `job_error` and `recovery_count` with Resume-from-stage and Cancel. 3 vitest cases. (The related audit claim that `/api/runs` reported no job at all did not reproduce; what did was the opposite — see gate 54) |
| 48 | Rejections keep their reason | **PASS** | Inline prompt with four one-click chips and free text; the reason shows on the row, on the approved screen, and after a reload. 6 vitest + 1 E2E |
| 49 | A failed grade conversion cannot damage the profile | **PASS** | Typed client call, draft written only on success, error surfaced. A 400 used to overwrite the applicant's GPA with `{detail: …}`. 3 vitest |
| 50 | Every value on screen carries its own source | **PASS** | Government post-study-work claims are cached with their evidence and attached to every row of that country, not only the first. Regression test asserts the claim and its source URL on each row |
| 51 | Citizenship and dates are matched, never guessed | **PASS** | Phrase matching with demonyms and published blocs; vague groups are PENDING, never a refusal. Ambiguous d/m vs m/d dates return None with the reason. 18 tests |
| 52 | Errors say what they are | **PASS** | The global `ValueError → 400` handler is gone: an internal ValueError is a 500 with no internal text, while a bad email is still a readable 400. Export filters are validated against the enum and the filename stem is rebuilt from a safe alphabet. 3 tests |
| 53 | `/api/health` fails when the database does | **PASS** | `SELECT 1`, 503 and `status: degraded`. Both the container HEALTHCHECK and the Fly check already treat that as a failure. 2 tests |
| 54 | Stale evidence is re-read, and a queued recheck is not mistaken for work | **PASS** | A finished run records `next_recheck_at` and queues a `recheck` job for that date; the UI names the date and offers "Re-verify now". The E2E suite then caught the consequence — a job queued months ahead read as work in flight and froze the collect button — so the run view now reports only jobs available to run. 5 tests |
| 55 | The account flows exist | **PASS** | Password change (revoking other sessions), single-use hour-long reset tokens stored as digests with identical answers for unknown addresses, password-confirmed account deletion that erases sole-owner workspaces and their cases, workspace listing and switching. 20 tests in `test_account_flows.py`; SECURITY.md updated |
| 56 | Session and password hygiene | **PASS** | scrypt 2**17 for new hashes with 2**14 still verifying, 20 sessions per user with the oldest revoked, expired rows cleaned on sign-in, SameSite=Lax with the Origin/Fetch-Metadata checks unchanged |
| 57 | Typography does not depend on a third party | **PASS** | Fonts self-hosted through @fontsource; `grep` over `dist` finds no external URL. The production CSP had been blocking Google Fonts outright |
| 58 | A render error is not a white page | **PASS** | Root and per-screen ErrorBoundary with a fallback that says the server data is safe, plus Reload. 3 vitest |
| 59 | The rate snapshot admits its age | **PASS** | Past 90 days `/api/capabilities` carries `stale_warning` and the funding screen shows it; `scripts/update_rates.py` prints the drift and a ready block for a human to paste. 4 tests |


### Added by Phase 3 of the audit fix plan

| # | Gate | Status | Evidence |
|---|---|---|---|
| 60 | Unsaved edits are never discarded silently | **PASS** | The draft is autosaved under its own key and restored after a reload with a banner and a Discard button; switching case or starting a new one asks first. A restored draft is layered on the server copy, never written into it — the shape of the old demo-data-overwrites-real-profile defect. 4 vitest |
| 61 | Every screen has an address | **PASS** | `#/shortlist` and friends; back, forward and reload work, and a deep link to a screen that is not reachable yet redirects with the reason. Gates apply to addresses, not to in-app navigation, so the redirect cannot fight the workflow. 2 E2E |
| 62 | One polling loop, paused when nobody is looking | **PASS** | Timeout chain keyed on the run id, in-flight guard, pause while `document.hidden` with an immediate poll on return, backoff to 15s, and a banner only after four consecutive failures. 5 vitest with fake timers |
| 63 | Every profile field changes something, or is not asked | **PASS** | ~20 dead fields resolved: scored where the registry holds comparable data, context where it does not, and three removed from the form outright. `docs/PROFILE_FIELDS.md` records each one with its test. 19 tests |
| 64 | Filters read as English | **PASS** | `STATUS_LABEL` in the options, enum still the value. 2 vitest |
| 65 | Money and dates share one locale | **PASS** | `DISPLAY_LOCALE` from the browser, en-GB fallback; money was en-US beside en-GB dates on the same screen |
| 66 | The product is called ASHYQ Apply everywhere a person reads | **PASS** | Sidebar, disclaimers, export header, the bot's User-Agent, and browser storage keys migrated from `unimatch.*` with a test. Internal names stay, and the README says why |
| 67 | The data export is complete | **PASS** | Profile, runs, results with decisions and notes, claims, conflicts and the audit trail, with counts and a Download button. It previously carried a count of results and called itself the complete record. 3 tests |
| 68 | An unknown is not reported as a failure | **PASS** | `run.unknowns` beside `run.errors`, split where the diagnostic is recorded; a clean demo run reports zero failures where it used to list 47. Two panels in the UI, and an older run still renders. 16 tests |
| 69 | Saving a note is not deciding the row | **PASS** | `PATCH …/notes`, tenant-scoped; the note no longer stamps `decided_at` on an undecided row. 3 tests |
| 70 | Lists are paged and say how much there is | **PASS** | limit/offset and `X-Total-Count` on profiles, cases, runs and claims; the silent 2000-claim cap is gone. A test fails if the per-run N+1 in `list_runs` returns. 5 tests |
| 71 | Deadlines can be put in a calendar | **PASS** | Valid VCALENDAR with stable UIDs, all-day events, and only confirmed dates; a JSON list marks passed deadlines rather than hiding them. 4 tests |
| 72 | An unmatched row is never skipped silently | **PASS** | Matching by `university_key`; a row that still cannot be matched is named in the run's diagnostics and carries its own open question. 1 test |
| 73 | Progress counts one thing | **PASS** | Programmes on both sides of the ratio, committed with the heartbeat. 2 tests |


## Summary

- **PASS:** 27 (of 30 original) + 5 + 7 added by Phase 1 + 17 added by Phase 2 + 14 added by Phase 3
- **PARTIAL:** 1 (gate 2 — the PostgreSQL branch was not exercised on this machine)
- **FAIL:** 1 (gate 22 — the container stack has still never been run)
- **BLOCKED:** 1

## Order of work remaining

0. **Phase 4 of `docs/FIX_PLAN.md`** — P3 hygiene (dead code, `ruff format` in
   CI, LICENSE and CONTRIBUTING, JSON→JSONB on PostgreSQL, small API bounds,
   honest live-coverage in the UI, an authenticated E2E path, coverage floor)
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
