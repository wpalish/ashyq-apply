# Release checklist — ASHYQ Apply 1.0

Thirty gates. A release may be declared only when every one is green. Status is
recorded honestly: `PASS` means verified by a command whose output is shown in
the release report, not "implemented".

**Current verdict: NOT READY.** 8 of 30 gates pass.

| # | Gate | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Existing 240 + 39 + 42 tests kept or replaced by stricter ones | **PASS** | 301 + 47 + 48. Two expectations corrected, each with a written reason in the test |
| 2 | All new unit / integration / E2E / security tests green | **PASS** | `pytest` 301, `vitest` 47, `playwright` 48 |
| 3 | ruff, mypy, TypeScript, ESLint, production build clean | **PASS** | all four clean; build 68.9 kB gzip |
| 4 | PostgreSQL migrations work on fresh and upgraded databases | **FAIL** | No Alembic migrations. SQLite only. `create_all()` cannot alter a table; a fail-fast check names missing columns as a stopgap |
| 5 | Redis worker survives a crash restart | **FAIL** | No Redis, no external broker. In-process asyncio queue |
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
| 22 | Docker Compose brings up a production-like stack | **FAIL** | No Dockerfiles, no compose |
| 23 | Backup / restore and crash recovery verified | **FAIL** | Crash *detection* verified; recovery is manual retry. No backup procedure |
| 24 | Documentation matches actual behaviour | **PASS** | Three README overstatements corrected; status banner added |
| 25 | No TODO / FIXME in a production path | **PASS** | `grep -rn "TODO\|FIXME" backend/app frontend/src` → none |
| 26 | No disabled or skipped tests without written justification | **PASS** | No skips, no xfails |
| 27 | Demo data unmistakably synthetic | **PASS** | Fixture banner, `fixture://` scheme, UI badge, export column. Loads only on an explicit confirmed action |
| 28 | Independent live truth audit across five canary universities | **PARTIAL** | Groningen and TU Delft audited, zero false positives. Aalto, Vienna, Warsaw outstanding |
| 29 | Local release commit/tag after all gates pass | **BLOCKED** | Gates open |
| 30 | Nothing pushed externally without permission | **PASS** | Three local commits, no remote configured, nothing pushed |

## Summary

- **PASS:** 17
- **PARTIAL:** 4
- **FAIL:** 8
- **BLOCKED:** 1

## Order of work remaining

1. **P1** — PostgreSQL, Alembic, durable queue, real crash recovery (gates 4, 5, 23)
2. **P2** — auth, organizations, cases, tenant isolation (gates 14, 18)
3. **P3** — SSRF suite, headers, rate limiting, threat model (gate 15)
4. **P4** — full onboarding forms (gate 17)
5. **P5–P6** — discovery providers, funding/document depth
6. **P7** — Docker, observability, CI (gates 21, 22)
7. **P8** — canary audit across all five institutions (gate 28)
