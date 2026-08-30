# Release checklist — ASHYQ Apply 1.0

Thirty gates. A release may be declared only when every one is green. Status is
recorded honestly: `PASS` means verified by a command whose output is shown in
the release report, not "implemented".

**Current verdict: NOT READY, NOT DEPLOYED.** Two gates are open, both named
below. Verified on 2026-08-29 on `claude/production-completion` at `0af7daa`.

Gate **22 (the container stack) now passes** — measured by CI at `ba15bbb`,
having genuinely failed first at `a669496`.

The open gate is **28: holdout recall, 3/6 against a bar of 4**. The main live
canary meets every bar it has (median 8, worst 8, category 28/30, scholarship
10/10, zero false positives), and the product thresholds for decision-grade
extraction — 5.6% mean completeness against 25 questions — are not met either.

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
| 22 | Docker Compose brings up a production-like stack | **PASS** | Measured by the `container-runtime` CI job, not by reading the config. It **failed** first, at `a669496`: the API had `read_only: true` with only `/tmp` writable while `get_settings()` created `/app/data/httpcache` at import, so the container never became healthy. Fixed, and green at `ba15bbb` — health, the one-shot migration, a real run picked up by the worker, worker-kill recovery with no duplicates, two worker replicas each answering for itself, API restart, tenant isolation, security headers and a restore drill comparing all 12 tables. Every run uploads per-container health output, service logs and an attestation keyed by the tested SHA |
| 23 | Backup / restore and crash recovery verified | **PASS** | Real SIGKILL recovery plus a PostgreSQL `pg_dump`/`pg_restore` scratch-database drill: 12 tables and a synthetic probe restored identically |
| 24 | Documentation matches actual behaviour | **PASS** | `CURRENT_STATE.md` retitled as the dated snapshot it is, with each superseded row marked; `LOOP_REPORT.md` carries a corrections table for its stale present-tense claims; `CANARY_AUDIT.md`'s "fee figures are behind JavaScript" corrected — they are in the served HTML and were being misread; `LIVE_DISCOVERY_REPORT.md` rewritten against three measured runs |
| 25 | No TODO / FIXME in a production path | **PASS** | `grep -rn "TODO\|FIXME" backend/app frontend/src` → none |
| 26 | No disabled or skipped tests without written justification | **PASS** | No skips, no xfails |
| 27 | Demo data unmistakably synthetic | **PASS** | Fixture banner, `fixture://` scheme, UI badge, export column. Loads only on an explicit confirmed action |
| 28 | Independent live truth audit, and programme discovery meets its bar | **FAIL** | Main canary **passes**: three independent runs at `0af7daa` gave **8, 8, 8** programme pages of ten — median 8 against a bar of 8, worst 8 against a bar of 7. Category pages **28/30** against 27, scholarship pages **10/10** against 9, and **zero** zero-tolerance false positives in every run. All twenty accepted programme pages were opened by hand and every one is a named, specific bachelor's programme. The **holdout fails**: 3 of 6 against a bar of 4, with its registry unedited and no seed added. Monterrey is disallowed by `robots.txt`; Tokyo serves no sitemap; Cape Town publishes programme detail in faculty handbook PDFs. **The holdout is the gate that keeps the release closed.** |
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
- **FAIL:** 1 — gate 28, programme discovery recall
- **BLOCKED:** 2 — gate 22 (no container runtime on this machine) and gate 29,
  which waits on the other two

The count said one BLOCKED while two were listed. Gate 29 cannot be anything
else while 22 and 28 are open, and a summary that disagrees with its own table
is the kind of thing a reader stops checking.

## Order of work remaining

1. ~~**P1** — PostgreSQL, Alembic, durable queue, crash recovery~~ **done** (gates 4, 5)
2. ~~**P2** — auth, organizations, cases, tenant isolation~~ **done**
3. ~~**P3** — SSRF suite, headers, rate limiting, threat model~~ **done**
4. ~~**P4** — full onboarding forms~~ **done**
5. **P5–P6** — programme-page classifier recall and funding/document extraction.
   Substantially advanced: see `docs/LIVE_DISCOVERY_REPORT.md` for the measured
   result and the reason each remaining miss fails.
6. **P7** — run the container stack and verify a deployment (gate 22)
7. ~~**P8** — canary audit across ten institutions~~ **done**

## Needs the user

* **Running the container stack** requires Docker, which is not installed and
  cannot be installed without your password. The files are written; they have
  never been executed.
* **Any external deployment**, domain or billing.
