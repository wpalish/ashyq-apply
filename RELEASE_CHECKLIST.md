# Release checklist — ASHYQ Apply 1.0

Thirty gates. A release may be declared only when every one is green. Status is
recorded honestly: `PASS` means verified by a command whose output is shown in
the release report, not "implemented".

**Current verdict: NOT READY.** 21 of 30 gates pass, 3 partial, 5 fail, 1 blocked.

| # | Gate | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Existing 240 + 39 + 42 tests kept or replaced by stricter ones | **PASS** | 349 + 47 + 48. Four expectations corrected, each with a written reason in the test |
| 2 | All new unit / integration / E2E / security tests green | **PASS** | `pytest` 349 (on SQLite *and* PostgreSQL), `vitest` 47, `playwright` 48 |
| 3 | ruff, mypy, TypeScript, ESLint, production build clean | **PASS** | all four clean; build 68.9 kB gzip |
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
| 14 | Auth and tenant isolation proven by tests | **FAIL** | No authentication at all |
| 15 | No critical/high security findings | **PARTIAL** | `pip-audit` and `npm audit` clean. No SSRF suite, no security headers, no rate limiting, no threat model |
| 16 | No secrets or applicant data in git or logs | **PASS** | Secret scan clean; `.gitignore` hardened; audit-log leak test |
| 17 | Full profile editable in the UI and correct after reload | **PARTIAL** | Reload bug fixed and tested. The form still covers a subset of the schema (no activities/achievements/preferences editors) |
| 18 | Multiple applicant cases | **FAIL** | Single implicit profile |
| 19 | Approve / reject / maybe and document collection work | **PASS** | Covered by E2E |
| 20 | CSV / JSON / XLSX exports carry provenance and data origin | **PASS** | 38 columns incl. source links, last-verified, data origin |
| 21 | Accessibility audit passed | **PARTIAL** | Hand-written assertions pass; no axe run, no WCAG 2.2 AA audit |
| 22 | Docker Compose brings up a production-like stack | **FAIL** | Dockerfiles, nginx config and a five-service compose file are written and parse, with non-root users, healthchecks, read-only roots, resource limits and a one-shot migration job. **Never run: Docker is not installed on this machine.** Requires a user checkpoint |
| 23 | Backup / restore and crash recovery verified | **PARTIAL** | Crash recovery proven end to end with a real SIGKILL. Backup/restore procedure not written or drilled |
| 24 | Documentation matches actual behaviour | **PASS** | Three README overstatements corrected; status banner added |
| 25 | No TODO / FIXME in a production path | **PASS** | `grep -rn "TODO\|FIXME" backend/app frontend/src` → none |
| 26 | No disabled or skipped tests without written justification | **PASS** | No skips, no xfails |
| 27 | Demo data unmistakably synthetic | **PASS** | Fixture banner, `fixture://` scheme, UI badge, export column. Loads only on an explicit confirmed action |
| 28 | Independent live truth audit across five canary universities | **PARTIAL** | Groningen and TU Delft audited, zero false positives. Aalto, Vienna, Warsaw outstanding |
| 29 | Local release commit/tag after all gates pass | **BLOCKED** | Gates open |
| 30 | Nothing pushed externally without permission | **PASS** | Three local commits, no remote configured, nothing pushed |

### Added since the last review

| # | Gate | Status | Evidence |
|---|---|---|---|
| 31 | Jobs are durable across a restart of every process | **PASS** | Jobs are rows; 26 queue tests on real PostgreSQL |
| 32 | Two workers never claim the same job | **PASS** | `SELECT … FOR UPDATE SKIP LOCKED`; asserted with two concurrent sessions |
| 33 | Idempotency prevents duplicate work | **PASS** | Pre-check plus a unique constraint; both paths tested |
| 34 | A poison job dies rather than retrying forever | **PASS** | Attempts exhausted → `dead`, never re-claimed |
| 35 | Cancellation lands at a consistent point | **PASS** | Observed between units of work; a cancelled job is `cancelled`, not `succeeded` |

## Summary

- **PASS:** 21 (of 30 original) + 5 added
- **PARTIAL:** 3
- **FAIL:** 5
- **BLOCKED:** 1

## Order of work remaining

1. ~~**P1** — PostgreSQL, Alembic, durable queue, crash recovery~~ **done** (gates 4, 5)
2. **P2** — auth, organizations, cases, tenant isolation (gates 14, 18) — *next*
3. **P3** — SSRF suite, headers, rate limiting, threat model (gate 15)
4. **P4** — full onboarding forms (gate 17)
5. **P5–P6** — discovery providers, funding/document depth
6. **P7** — running the containers, observability, CI (gates 21, 22)
7. **P8** — canary audit across all five institutions (gate 28)

## Needs the user

* **Running the container stack** requires Docker, which is not installed and
  cannot be installed without your password. The files are written; they have
  never been executed.
* **Redis + Dramatiq**, if you want a broker rather than the PostgreSQL queue,
  needs Docker or Homebrew for the same reason. ADR 0001 explains the trade.
* **Any external deployment**, domain or billing.
