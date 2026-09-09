# Release checklist — ASHYQ Apply 1.0

Ninety-six gates, grown from the original thirty. A release may be declared
only when every one is green. Status is
recorded honestly: `PASS` means verified by a command whose output is shown in
the release report, not "implemented".

**Current verdict: NOT DEPLOYED externally.** The local container stack was
verified against real Docker on 2026-09-06, so gate 22 now passes. What is left
needs a person, not another phase: an external deployment, a lawyer for the
privacy policy and terms (gate 87), and a live ApiPay account before payments
can be switched on (gate 94).

**CI on `main` is green, and has been since 2026-09-07.** Verified green runs:
main run 34115345524 (2026-09-07), PR runs 34188244906 and 34188286259, and the
post-merge main run 34189211422 (all 2026-09-08, the campaign-c2 merge). The
end-to-end suite that had been red since 2026-09-04
(`e2e/profile-persistence.spec.ts:26`, two elements matching 'Saved') was fixed
before that merge; gate 2 records the history. Standing rule: this CI status is
refreshed at every merge to `main`, and a red `main` is a hotfix that outranks
every feature.

**`docs/FIX_PLAN.md` is finished.** Phases 0–6 are done, including the optional
sixth; gates 36–92 below record what each fix is held to. Two audit findings
did not reproduce against this tree and are recorded as such rather than
"fixed" — see gates 22 and 47. What remains open needs a person, not another
phase: a lawyer for the privacy policy and terms (gate 87), and a live ApiPay
account (gate 94). Ranking v2, the community module and payments landed after
Phase 6; gates 93-96 record what they are held to.

| # | Gate | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Existing 240 + 39 + 42 tests kept or replaced by stricter ones | **PASS** | 1110 + 164 + 74 (desktop and mobile) + 6 auth E2E, measured on `2be6b55`. Nothing removed; Phase 1 added 14, Phase 2 added 65, Phase 3 added 50, and Phase 5 added 21 backend (metrics, dead jobs) and 8 frontend (the needs-attention line, the legal page); the c2/c3 counts superseding them are recorded in gate 2 (1358 on the c2 merge, 1402 at `810bb00`) |
| 2 | All new unit / integration / E2E / security tests green | **PASS** | `pytest` 1358 passed on the c2 merge — CI on both databases (coverage 93.81%, floor 92); at the c3 integration head `810bb00`: 1402 passed / 0 skipped, coverage 94.04% (local, 2026-09-08). `vitest` 182 passed. Playwright: ordinary 75 passed + 1 intentional skip, `e2e:auth` 6/6 (local, 2026-09-08). History: red on `main` 2026-09-04 → 2026-09-07 (`e2e/profile-persistence.spec.ts:26`, which also blocked `e2e:auth`); green runs since: 34115345524, 34188244906, 34188286259, 34189211422. |
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
| 22 | Docker Compose brings up a production-like stack | **PASS** | Run for real on 2026-09-06 against Docker Desktop 4.89.0 / Engine 29.7.2 under WSL2: images built, migrations exited 0, postgres/api/web healthy, and registration plus a demo research run through nginx on :8080 returned 20 results at `awaiting_user_decision`. Two defects the run itself found are fixed in `docker-compose.yml`: the `/app/data` tmpfs was root-owned so the API died creating its cache directory, and the worker inherited an HTTP healthcheck for a port it does not serve. Evidence: `docs/DOCKER_VERIFICATION.md`. CI additionally runs `docker compose build` on every push. Earlier finding, kept: one real defect fixed: the read-only `api` had no writable `/app/data`, and `ensure_dirs()` runs at import, so the container would have died with EROFS before serving a request. The audit's other two compose findings did not reproduce — the worker's `worker-cache:/app/data` matches `BACKEND_ROOT` for the image compose builds, and `backend/Dockerfile` already carries a `curl` HEALTHCHECK. `scripts/verify_compose.sh` drives the whole stack to a finished demo run. Requires a user checkpoint |
| 23 | Backup / restore and crash recovery verified | **PASS** | Real SIGKILL recovery plus a PostgreSQL `pg_dump`/`pg_restore` scratch-database drill: 12 tables and a synthetic probe restored identically |
| 24 | Documentation matches actual behaviour | **PASS** | Three README overstatements corrected; status banner added |
| 25 | No TODO / FIXME in a production path | **PASS** | `grep -rn "TODO\|FIXME" backend/app frontend/src` → none |
| 26 | No disabled or skipped tests without written justification | **PASS** | No xfails. 25 skips, all one justified case: the PostgreSQL fixture skips when `pgserver` cannot start a cluster (its `initdb.exe` fails on Windows). The reason is in the skip message and in `conftest.py`; Linux CI provisions the real server and runs them |
| 27 | Demo data unmistakably synthetic | **PASS** | Fixture banner, `fixture://` scheme, UI badge, export column. Loads only on an explicit confirmed action |
| 28 | Independent live truth audit across five canary universities | **PASS** | Ten official domains audited; 26/30 category pages, 0 zero-tolerance false positives. Programme recall 7/10, category recall 26/30, 0 material false positives (T30 canary, 2026-09-08); see `docs/LIVE_DISCOVERY_REPORT.md` |
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
| 74 | No dead code left behind | **PASS** | `queue.py`, `can_transition`, `RETRYABLE`, `tenacity` and `python-multipart` deleted; the `arg-type` mypy exclusions for `app.api` and `app.corpus` turned out to be dead too, and removing them surfaced one shadowed loop variable rather than a class of errors. `mypy app tests` clean on 99 files with no escape hatch but the Playwright lazy-init one |
| 75 | Formatting is a gate, not a habit | **PASS** | `ruff format --check app tests` runs in CI; `ruff format` applied once as its own commit. 99 files already formatted |
| 76 | The repository can be contributed to | **PASS** | LICENSE (MIT), CONTRIBUTING.md, bug and feature issue templates; `LOOP_REPORT.md` moved under `docs/process/` |
| 77 | Half an answer is never rounded up to a whole one | **PASS** | `hours_per_week` without `weeks_per_year` is named in `missing_fields` and in the explanation instead of being silently discarded; the score is unchanged, so answering cannot cost the applicant anything. The 40-weeks assumption was rejected and the reasoning is recorded in `docs/PROFILE_FIELDS.md`. 4 tests |
| 78 | A conversion method is only offered where it applies | **PASS** | `uk_class_to_us4` is no longer offered for non-UK percentage scales; matched on word boundaries, so "Ukrainian" is not read as "UK". 3 tests |
| 79 | Live mode says how far it reaches | **PASS** | PreferencesScreen shows the registry's own recall note and country list when demo mode is switched off — the registry's institutions (ten then, nineteen since gate 89), not the open web. A contract test pins the API shape to the TypeScript type and was verified to fail on a renamed key. 3 unit tests + 1 contract test |
| 80 | The authenticated path is exercised end to end | **PASS** | `npm run e2e:auth` — a second Playwright config with `UNIMATCH_AUTH_ENABLED=true` and `reuseExistingServer: false`, covering register → profile → run → sign out → sign in → data still there. 6 tests |
| 81 | An expired session returns to sign-in | **PASS** | Found by writing gate 80: every 401 was rendered as a topbar banner on a screen the user could not leave. Guarded in the store's shared `fail`. Both the E2E case and the unit test were confirmed to fail with the guard removed. 2 tests |
| 82 | The coverage floor means something | **PASS** | Raised from 80 to 92, the level actually measured on a green run (6010 statements, 504 uncovered) |


### Added by Phase 5 of the audit fix plan

| # | Gate | Status | Evidence |
|---|---|---|---|
| 83 | The service can be watched from outside its logs | **PASS** | `/metrics` in Prometheus text: requests by route and status, a latency histogram, limiter refusals, and jobs and runs by state read from the database at scrape time. Verified against a running API, not only in tests: a 404 on `/api/runs/nope` was counted as `route="/api/runs/{run_id}"`, and a queued demo run appeared as `ashyq_jobs{status="queued"} 1`. 14 tests |
| 84 | The scrape endpoint is not a second way to read applicant data | **PASS** | Aggregates only, and a canary display name is asserted never to appear. Bearer token when one is configured, 404 when disabled, and production refuses to start with the endpoint open and no token. `fly.toml` ships with it off because that app is published on the open internet; nginx refuses `/metrics` explicitly |
| 85 | Work the queue gave up on is visible to the people it affects | **PASS** | `GET /api/admin/jobs?status=dead`, scoped to the caller's own organization and to owners, with the count in `X-Total-Count`; the progress screen says "N jobs need attention" and stays silent for anyone who may not read the queue. 7 backend tests + 4 vitest |
| 86 | A backup happens on a schedule, and a restore has been proven | **PASS** | `scripts/backup.sh` — one dump, verified by listing its contents, then pruning older than `RETENTION_DAYS`, and only after the new one verifies; the cron line and the Fly equivalent are in `docs/BACKUP_RESTORE.md`. `backup_drill.py` restored 18 tables with identical row counts against the bundled PostgreSQL — the first restore this repository has actually performed rather than described |
| 87 | The product says what it does with personal data | **PARTIAL** | A privacy policy and terms exist, have an address (`#/legal`), and every factual claim in them is true of the code. They are **drafts and say so**: no lawyer has read them, and the product asks no age although it is built for applicants who will include minors. Legal review is outstanding and is a release blocker for real applicants, not a formality. 4 vitest |
| 88 | Every log line can be tied to the request that produced it | **PASS** | Request-id middleware honouring a safe inbound `X-Request-ID` and echoing it back, JSON log format behind `UNIMATCH_LOG_FORMAT`, correlation id carried per context and through the worker on the job id. 12 tests (Phase 5.1–5.2) |

### Added by Phase 6 of the audit fix plan

| # | Gate | Status | Evidence |
|---|---|---|---|
| 89 | Live mode reaches beyond ten Western universities | **PASS** | Nineteen institutions, the nine new ones chosen for where Kazakh applicants apply, including Nazarbayev University. Every seed fetched and classified by the product's own classifier before being written down; a category with no verifiable page has no seed. All 52 seeds resolve. Nine canaried the day they were added: nine reached, zero blocked, **zero false positives**, programme pages 2 of 9; superseded by the 2026-09-08 T30 canary: programme pages 7/10 (gate 28) |
| 90 | The canary can actually run, and its verdict can be trusted | **PASS** | Three defects in the tool, none in the product: it died on a NOT NULL constraint from the `dev-org` default Phase 4 removed; `--only` narrowed the report but not the run; and the false-positive gate read a requirement's provenance from attributes a string does not have, so it could never pass and accused Charles University of a false positive it had not made. 4 tests now hold the gate to its own contract |
| 91 | A transcript can be read instead of retyped | **PASS** | Grade average with its scale, and the graduation date, each quoted back with the line it came from and applied only per field on request. Refuses an average with no scale, an ambiguous numeric date, and a value above its own scale. PDFs only, 10 MB, authenticated, held in memory and discarded. 17 backend tests + 4 vitest |
| 92 | Russian and Kazakh have a foundation that does not invent terms | **PARTIAL** | The shell reads from dictionaries with English as the visible fallback, and a language selector persists the choice. Deliberately incomplete: claim, shortlist, funding gap, conditional offer and the status vocabulary are listed in `docs/i18n/GLOSSARY.md` with the question each poses, and the strings containing them stay in English until a person who advises applicants in those languages decides. 7 vitest, including one that fails if a reserved term is quietly translated |

### Added after Phase 6 — ranking v2, community and payments

These three landed on `main` after the fix plan closed. They are recorded here
because a release gate document that does not mention a merged module is not a
release gate document.

| # | Gate | Status | Evidence |
|---|---|---|---|
| 93 | The shortlist ranks non-compensatively, and never as a probability | **PASS** | Ranking v2 (PR #2): a geometric mean over six axes, so an unaffordable place cannot buy its way to the top with the other five, plus portfolio buckets and re-ranking a finished run against new priorities without fetching a page. `backend/tests/test_ranking_v2.py`; the reasoning is `docs/adr/0003-noncompensatory-ranking.md`. The preferences screen says in plain words that the order is not a probability |
| 94 | A real payment has been taken end to end | **BLOCKED — needs the owner** | The whole path exists and is tested — orders, a signed webhook that grants exactly once, a reconciler for the webhook that never arrives, the paywall, school subscriptions with quotas — across `test_billing_api.py`, `test_payment_webhook.py`, `test_payment_reconcile.py`, `test_paywall.py`, `test_subscription_*.py`. But **the adapter has never spoken to ApiPay**: every claim rests on contract tests written against their published OpenAPI document. Needs a merchant account with Kaspi Pay connected, the keys in the deployment, the public webhook URL registered, a confirmed price (4990 ₸ is a placeholder), and one real transaction reconciled in both dashboards |
| 95 | Payments off changes nothing | **PASS** | `UNIMATCH_PAYMENTS_ENABLED=false` is the default, and `test_with_payments_disabled_everything_is_visible` in `test_entitlements.py` asserts every case stays fully open. `test_payments_config.py` pins the defaults and that secrets never render in a settings dump |
| 96 | Community content can be moderated, and a person can leave | **PASS** | Feed, threads, private conversations with a setting that guards the first message, blocking, a report queue someone can work, and avatars stripped of their metadata. `test_social_api.py`, `test_social_messages.py`, `test_social_moderation.py`, `test_social_avatars.py`, `test_social_models.py`. Account deletion has a test for the seam with the community. **Not gated:** community rules and a moderation SLA are not written, and no gate covers what a moderator is supposed to do |
| 97 | The paywall is whole: no route hands out paid material to a free organization | **PASS** | Campaign c3 (T33): `set_decision`/`set_notes` answer with the `free_view` projection; `export_profile` gates claims/conflicts/full payloads behind `has_full_access` and marks withheld rows; `free_view` also clears nested cost source URLs. A surface-scan test (`test_paywall_surface.py`) walks all 17 material routes for a free org and an inventory test fails on any new ungated route. Evidence: `ai-team/outputs/c3-t33-a1/` |
| 98 | Payments fail closed: bad provider config or empty secrets cannot run | **PASS** | Campaign c3 (T34): `validate_runtime` refuses unknown providers, ApiPay without ≥20/≥32-char credentials, and production billing through the fake provider; `ApiPayProvider.__init__` raises on empty secrets; `verify_webhook` returns False on an empty secret before computing HMAC. The forged-`b""`-signature exploit test was RED on the baseline. Evidence: `ai-team/outputs/c3-t34-a1/` |
| 99 | Password mail goes over verified TLS, and old hashes are upgraded at login | **PASS** | Campaign c3 (T35): STARTTLS always runs with `ssl.create_default_context()` (`UNIMATCH_SMTP_TLS_VERIFY=false` is the explicit non-production opt-out; production refuses to start with it); a stdlib read proves a stripped STARTTLS capability fails the send with no plaintext path. A successful login with a legacy-cost scrypt hash rehashes it exactly once with a `password_rehashed` audit event. Evidence: `ai-team/outputs/c3-t35-a1/` |
| 100 | The rate limiter cannot be spoofed through the proxy chain | **PASS** | Campaign c3 (T36): with `trust_proxy_headers` the limiter keys on the **last** X-Forwarded-For hop (nginx appends the real client); compose no longer publishes the API port (expose-only), and `scripts/verify_compose.sh` fails on any api host publication. The live docker run of that script remains an owner release-gate step (NOT_RUN in c3). Evidence: `ai-team/outputs/c3-t36-a1/` |
| 101 | Re-entering the funding stage never duplicates claims | **PASS** | Campaign c3 (T37): `_update_result` replaces the scholarship-family claims/conflicts (keeping SUPERSEDED history) before storing on stage re-entry. The RED test doubled claims on 14/20 results on the baseline; T32 reextract and TestRetry stay green. Evidence: `ai-team/outputs/c3-t37-a1/` |
| 102 | The documents state measured facts, not hopes | **PASS** | Campaign c3 (T38): README/RELEASE_CHECKLIST/CURRENT_STATE carry only sourced numbers — recall 7/10 (T30 canary), CI green since 2026-09-07 with run ids, c3 local gates labelled LOCAL+SHA+date. QA cross-checked 60+ numbers against artifacts and re-counted registry/i18n/e2e itself. Evidence: `ai-team/outputs/c3-t38-a1/` |

## Summary

Counted on `2be6b55`; re-counted 2026-09-08 after the c2 merge moved gate 2 to
PASS, and again after campaign c3 added gates 97-102. Gates 1-102.

- **PASS:** 98
- **PARTIAL:** 2 — gate 87 (the privacy policy and terms are drafts no lawyer
  has read), gate 92 (the product vocabulary is deliberately untranslated
  pending human review)
- **FAIL:** 0
- **BLOCKED:** 2 — gate 29 (the release tag waits on the rest) and gate 94 (a
  real payment needs a merchant account)

Gate 22 moved from FAIL to PASS on work: the stack was actually run, and running
it found two defects that no amount of reading the file would have shown. Gate 2
moved the other way, from PASS to PARTIAL, on evidence: the end-to-end suite has
been red on `main` since 2026-09-04 and the summary said nothing about it. Gate
2 moved back to PASS at the c2 merge (2026-09-08): the failing spec was fixed
and CI on `main` has been green since 2026-09-07.

## Order of work remaining

0. ~~**Phase 4 of `docs/FIX_PLAN.md`** — P3 hygiene~~ **done** (gates 74-82)
0a. ~~**Phase 5** — ops and observability: request-id middleware, JSON logs,
   `/metrics`, a scheduled backup, admin visibility of dead jobs, and Privacy
   Policy / Terms stubs~~ **done** (gates 83-88)
0b. ~~**Phase 6** — optional: i18n groundwork (ru/kk), transcript import, and
   more live-registry institutions~~ **done** (gates 89-92). Nine institutions
   were added rather than ten: six candidates were evaluated and rejected, one
   of them because its robots.txt disallows the site, and padding the number
   with an unverifiable seed would have made "verified" mean nothing.
1. ~~**P1** — PostgreSQL, Alembic, durable queue, crash recovery~~ **done** (gates 4, 5)
2. ~~**P2** — auth, organizations, cases, tenant isolation~~ **done**
3. ~~**P3** — SSRF suite, headers, rate limiting, threat model~~ **done**
4. ~~**P4** — full onboarding forms~~ **done**
5. ~~**Fix the red end-to-end test**~~ **done** — fixed before the c2 merge;
   `main` green since 2026-09-07 and `e2e:auth` 6/6 (gate 2)
6. **P5–P6** — improve programme-page classifier recall and deepen funding/document extraction
7. ~~**P7** — run the container stack~~ **done** (gate 22). An external
   deployment is still outstanding and needs the owner
8. ~~**P8** — canary audit across ten institutions~~ **done**
9. **Finish ru/kk** — 183 of 194 dictionary keys are translated into Russian
   and Kazakh, and only the shell and the community screens read from the
   dictionary, so the interface is effectively English for an audience that is
   not (gate 92)

## Needs the user

* ~~Running the container stack.~~ Done on 2026-09-06; see
  `docs/DOCKER_VERIFICATION.md`. No external deployment was performed.
* **Any external deployment**, domain or billing.
* **Payments cannot go live without you.** Specifically:
  1. an ApiPay account with Kaspi Pay connected;
  2. `UNIMATCH_APIPAY_API_KEY` and `UNIMATCH_APIPAY_WEBHOOK_SECRET` in the
     deployment environment, then `UNIMATCH_PAYMENTS_ENABLED=true` and
     `UNIMATCH_PAYMENTS_PROVIDER=apipay`;
  3. the public HTTPS URL of `POST /webhooks/apipay` registered in the ApiPay
     dashboard — which depends on the deployment above;
  4. confirmation of the price; `4990 ₸` is a placeholder default;
  5. one end-to-end payment of the real price, verified in both the ApiPay
     dashboard and our `payment_events` table. Until that has happened, the
     payment path is proven only by contract tests.
* **School subscriptions need two things from you:**
  1. the price list and standard term — the product records what was sold and
     never quotes anyone;
  2. whoever sells must be able to reach a shell with database access, because
     recording a paid subscription is `scripts/grant_subscription.py` and
     deliberately not a network endpoint.
* **A lawyer to read the privacy policy and terms** (gate 87). They are honest
  drafts, and the product will be used by applicants under 18 while asking
  nobody's age — that is a decision for a person, not for this repository.
