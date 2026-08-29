# Release checklist — ASHYQ Apply 1.0

Thirty gates. A release may be declared only when every one is green. Status is
recorded honestly: `PASS` means verified by a command whose output is shown in
the release report, not "implemented".

**Current verdict: NOT READY, NOT DEPLOYED.** Two gates are open and one is
new. Verified on 2026-08-29 on `claude/production-completion`.

Two gates changed status *downwards* this cycle, both because they were being
measured against the wrong thing:

* **Gate 28** was PASS on "zero false positives". Zero false positives is a
  precision result and says nothing about recall; live discovery confirms a
  programme page at four institutions in ten, against a bar of eight. It is now
  **FAIL**, and it is the reason the product is not ready.
* **Gate 22** said FAIL on "Docker is not installed". That is still true, and
  the honest status is **BLOCKED** — it needs an admin install, which is a user
  checkpoint, not an engineering task left undone.

| # | Gate | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Existing tests kept or replaced by stricter ones | **PASS** | 768 + 47 + 52, from 240 + 39 + 42 originally. Every changed expectation states its product reason in the test |
| 2 | All new unit / integration / E2E / security tests green | **PASS** | `pytest` 768 (on SQLite *and* PostgreSQL 16.2), `vitest` 47, `playwright` 52 |
| 3 | ruff, mypy, TypeScript, ESLint, production build clean | **PASS** | all clean; build 74.5 kB JS gzip, 5.3 kB CSS |
| 4 | PostgreSQL migrations work on fresh and upgraded databases | **PASS** | Alembic. Verified fresh, downgrade to base, re-upgrade, re-apply as a no-op, on PostgreSQL 16.2 and SQLite. `create_all()` removed from the production path; startup refuses a mismatched revision |
| 5 | Worker survives a crash restart | **PASS** | `scripts/crash_test.py` SIGKILLs a real worker after 12 results are written; a second worker recovers the job and finishes with no duplicates. Stable over 3 runs. **PostgreSQL-backed queue, not Redis — see ADR 0001** |
| 6 | No run stuck `running` with no worker | **PASS** | Worker lease + heartbeat; `retryable_failed`; startup reconciliation; API reports `stale`. 7 tests |
| 7 | `candidate_limit` works | **PASS** | Persisted on the run, applied, capped against `verify_limit`, reused on retry. 3 tests |
| 8 | Playwright escalation actually invoked and recorded | **PASS** | Escalation inside `Fetcher`; per-page tier and per-run tier counts. 3 tests |
| 9 | Known live false positives no longer reproducible | **PASS** | 10 documented FPs, ~60 regression tests. Three independent live canary runs on 2026-08-29: zero zero-tolerance false positives in each |
| 10 | MSc award never shown to a bachelor applicant without proof | **PASS** | `degree_applicability`; verified on the real van Effen page |
| 11 | Missing deadline never becomes "available" | **PASS** | Availability decomposed into 7 fields, all defaulting to unknown |
| 12 | Every material claim has an official evidence trail | **PASS** | Claim carries URL, verbatim excerpt, specificity, timestamp, status, method. Excerpt-provenance tests on both adapters |
| 13 | No silently inferred YES | **PASS** | Positive claims require positive evidence; audited in the canary |
| 14 | Auth and tenant isolation proven by tests | **PASS** | Opaque server sessions, `scrypt`, organizations. All **17** routes carrying a resource id refuse another tenant with 404, and the probe set is derived from the application's own OpenAPI schema, so a route added later fails the suite until it is probed. Logged-out, deleted-user and invented tokens all rejected |
| 15 | No critical/high security findings | **PASS** | `pip-audit` and `npm audit` clean. Three real defects found and fixed this cycle: spreadsheet formula injection in CSV/XLSX exports, an unhandled exception on a malformed crawled link, and production builds publishing source maps. SSRF re-verified live: fourteen probes including octal, hex, integer, IPv4-mapped and dotted-short loopback all refused while curl reached the same service |
| 16 | No secrets or applicant data in git or logs | **PASS** | Secret scan clean; `.gitignore` hardened; audit-log leak test |
| 17 | Full profile editable in the UI and correct after reload | **PASS** | Tests, activities, achievements, evidence, academic record, funding and preference fields are editable; persistence/replacement covered by E2E |
| 18 | Multiple applicant cases | **PASS** | Cases are tenant-scoped profiles with create/switch UI and `/api/cases`; blank cases do not inherit demo identity data |
| 19 | Approve / reject / maybe and document collection work | **PASS** | Covered by E2E |
| 20 | CSV / JSON / XLSX exports carry provenance and data origin | **PASS** | 38 columns incl. source links, last-verified, data origin |
| 21 | Accessibility audit passed | **PASS** | axe WCAG A/AA scans every reachable workflow screen on desktop and mobile; no horizontal overflow at 320, 375, 768, 1024, 1440 or 1920. A manual screen-reader pass with a real assistive technology has still not been done |
| 22 | Docker Compose brings up a production-like stack | **BLOCKED** | The stack is written and CI now has a `container-runtime` job running `scripts/compose_smoke.sh`, which starts it and checks health, the one-shot migration, a real run picked up by the worker, worker-kill recovery with no duplicate results, API restart, tenant isolation, security headers and a pg_dump restore. **It has never been executed:** `docker`, `podman`, `colima`, `nerdctl` and `lima` are all absent from this machine and installing one needs an admin password. Building an image is not running a stack, and this stays BLOCKED until the job has actually run |
| 23 | Backup / restore and crash recovery verified | **PASS** | Real SIGKILL recovery plus a PostgreSQL `pg_dump`/`pg_restore` scratch-database drill: 12 tables and a synthetic probe restored identically |
| 24 | Documentation matches actual behaviour | **PASS** | `CURRENT_STATE.md` retitled as the dated snapshot it is, with each superseded row marked; `LOOP_REPORT.md` carries a corrections table for its stale present-tense claims; `CANARY_AUDIT.md`'s "fee figures are behind JavaScript" corrected — they are in the served HTML and were being misread; `LIVE_DISCOVERY_REPORT.md` rewritten against three measured runs |
| 25 | No TODO / FIXME in a production path | **PASS** | `grep -rn "TODO\|FIXME" backend/app frontend/src` → none |
| 26 | No disabled or skipped tests without written justification | **PASS** | No skips, no xfails |
| 27 | Demo data unmistakably synthetic | **PASS** | Fixture banner, `fixture://` scheme, UI badge, export column. Loads only on an explicit confirmed action |
| 28 | Independent live truth audit, and programme discovery meets its bar | **FAIL** | Three independent runs on 2026-08-29: **4, 4, 4** programme pages of ten, against a bar of median 8 and worst 7. Category pages **27/30**, which does meet its bar. Zero zero-tolerance false positives in every run, and all twelve accepted programme pages were opened by hand and are real. Four of the six misses are genuine recall defects, two are honest NOT_FOUND; each is named in `docs/LIVE_DISCOVERY_REPORT.md`. **This is the gate that keeps the release closed.** |
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
