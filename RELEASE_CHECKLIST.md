# Release checklist — ASHYQ Apply 1.0

Thirty gates. A release may be declared only when every one is green. Status is
recorded honestly: `PASS` means verified by a command whose output is shown in
the release report, not "implemented".

**Current verdict: NOT DEPLOYED.** 28 of 30 gates pass; the local container
stack is the one unverified gate, and the release commit/tag waits on it.

| # | Gate | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Existing 240 + 39 + 42 tests kept or replaced by stricter ones | **PASS** | 547 + 47 + 50. Changed expectations document their product reason in the test |
| 2 | All new unit / integration / E2E / security tests green | **PASS** | `pytest` 547 (on SQLite *and* PostgreSQL), `vitest` 47, `playwright` 50 |
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
| 14 | Auth and tenant isolation proven by tests | **PASS** | Opaque server sessions, `scrypt`, organizations and 404 ownership checks across every case/run/result/export endpoint; 13 security tests |
| 15 | No critical/high security findings | **PASS** | `pip-audit` and `npm audit` clean; 81 SSRF cases, DNS pinning, redirect/body limits, CSP/HSTS/origin checks, rate limits and `SECURITY.md` |
| 16 | No secrets or applicant data in git or logs | **PASS** | Secret scan clean; `.gitignore` hardened; audit-log leak test |
| 17 | Full profile editable in the UI and correct after reload | **PASS** | Tests, activities, achievements, evidence, academic record, funding and preference fields are editable; persistence/replacement covered by E2E |
| 18 | Multiple applicant cases | **PASS** | Cases are tenant-scoped profiles with create/switch UI and `/api/cases`; blank cases do not inherit demo identity data |
| 19 | Approve / reject / maybe and document collection work | **PASS** | Covered by E2E |
| 20 | CSV / JSON / XLSX exports carry provenance and data origin | **PASS** | 38 columns incl. source links, last-verified, data origin |
| 21 | Accessibility audit passed | **PASS** | axe WCAG A/AA scans every reachable workflow screen on desktop and mobile; focused keyboard/progress/table/overflow checks also pass |
| 22 | Docker Compose brings up a production-like stack | **FAIL** | Dockerfiles, nginx config and a five-service compose file are written and parse, with non-root users, healthchecks, read-only roots, resource limits and a one-shot migration job. **Never run: Docker is not installed on this machine.** Requires a user checkpoint |
| 23 | Backup / restore and crash recovery verified | **PASS** | Real SIGKILL recovery plus a PostgreSQL `pg_dump`/`pg_restore` scratch-database drill: 12 tables and a synthetic probe restored identically |
| 24 | Documentation matches actual behaviour | **PASS** | Three README overstatements corrected; status banner added |
| 25 | No TODO / FIXME in a production path | **PASS** | `grep -rn "TODO\|FIXME" backend/app frontend/src` → none |
| 26 | No disabled or skipped tests without written justification | **PASS** | No skips, no xfails |
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

## Summary

- **PASS:** 28 (of 30 original) + 5 added
- **PARTIAL:** 0
- **FAIL:** 1
- **BLOCKED:** 1

## Order of work remaining

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
