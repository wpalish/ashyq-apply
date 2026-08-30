# Release checklist — ASHYQ Apply 1.0

Thirty gates. A release may be declared only when every one is green. Status is
recorded honestly: `PASS` means verified by a command whose output is shown in
the release report, not "implemented".

**Current verdict: NOT READY, NOT DEPLOYED.** Two gates are open, both named
below. The measured values are in `artifacts/release-evidence.json`; this file states status and reasoning, and must not restate numbers that live there.

Gate **22 (the container stack) is NOT RUN for this commit.** It has passed in
CI on earlier commits of this branch, having genuinely failed first at
`a669496` for a real reason. It cannot be measured on this machine — there is no
container runtime — and the artifact says so rather than carrying an older
commit's result forward. It returns to PASS when CI has attested *this* head and
the artifact records that attestation; until then the honest status is that
nobody has watched it here.

The open gate is **28: holdout recall, 3/6 against a bar of 4**. The main live
canary meets every bar it has (median and worst programme pages, category and
scholarship pages, zero zero-tolerance false positives), and the product
threshold for decision-grade extraction is not met either. Completeness rose
this cycle and is still far below its bar; the measured values are in the
artifact.

Extraction now has a **denominator**. `backend/app/corpus/gold/` holds a frozen
gold set: what each institution actually publishes for each of the twenty-five
decision questions, read by hand off their own pages, with the URL, the excerpt
and the date it was read. `scripts/evaluate_extraction.py` scores the extractor
against it per question. Against the programmes audited so far it is precise and
half-deaf — it has never claimed something a page does not say, and it misses
about half of what they do. Coverage is reported on every run and is small; the
selection is frozen by digest so it cannot be curated toward a result.

Two gates changed status *downwards* this cycle, both because they were being
measured against the wrong thing:

* **Gate 28** was PASS on "zero false positives". Zero false positives is a
  precision result and says nothing about recall. The main canary now meets its
  recall bar; the frozen holdout does not, and that is what keeps 28 open. The
  holdout was re-measured this cycle and is unchanged at 3/6.
* **Gate 22** was BLOCKED on "Docker is not installed", which is still true of
  this machine and no longer true of the gate: the `container-runtime` CI job
  runs the smoke test on every push. It failed there first, for a real reason,
  and now passes.

| # | Gate | Status | Evidence / what is missing |
|---|---|---|---|
| 1 | Existing tests kept or replaced by stricter ones | **PASS** | Counts in the release artifact. Every changed expectation states its product reason in the test |
| 2 | All new unit / integration / E2E / security tests green | **PASS** | `pytest` on SQLite *and* PostgreSQL 16.2, `vitest`, `playwright`; counts in the release artifact. A structured 0-skip gate reads the JUnit/JSON reports rather than grepping for decorators |
| 3 | ruff, mypy, TypeScript, ESLint, production build clean | **PASS** | all clean; build 74.5 kB JS gzip, 5.3 kB CSS |
| 4 | PostgreSQL migrations work on fresh and upgraded databases | **PASS** | Alembic. Verified fresh, downgrade to base, re-upgrade, re-apply as a no-op, on PostgreSQL 16.2 and SQLite. `create_all()` removed from the production path; startup refuses a mismatched revision |
| 5 | Worker survives a crash restart | **PASS** | `scripts/crash_test.py` SIGKILLs a real worker after 12 results are written; a second worker recovers the job and finishes with no duplicates. Stable over 3 runs. **PostgreSQL-backed queue, not Redis — see ADR 0001** |
| 6 | No run stuck `running` with no worker | **PASS** | Worker lease + token-fenced heartbeat on a thread ([ADR 0004](docs/adr/0004-lease-fencing.md)); `retryable_failed`; startup reconciliation; API reports `stale`. Store-level fencing on PostgreSQL, worker-level enforcement with the event loop blocked, and `scripts/split_brain_test.py`, which SIGSTOPs a real worker past its lease and gives it every chance to interfere |
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
| 22 | Docker Compose brings up a production-like stack | **NOT RUN** | Not measurable on this machine (no container runtime), and the artifact records `not_run` rather than carrying an older commit's result forward. The `container-runtime` CI job has passed on earlier commits of this branch — it **failed** first, at `a669496`: the API had `read_only: true` with only `/tmp` writable while `get_settings()` created `/app/data/httpcache` at import, so the container never became healthy. That fix stands. This gate returns to PASS when CI has attested this head and the artifact records the attestation. |
| 23 | Backup / restore and crash recovery verified | **PASS** | Real SIGKILL recovery plus a PostgreSQL `pg_dump`/`pg_restore` scratch-database drill: 12 tables and a synthetic probe restored identically |
| 24 | Documentation matches actual behaviour | **PASS** | `CURRENT_STATE.md` retitled as the dated snapshot it is, with each superseded row marked; `LOOP_REPORT.md` carries a corrections table for its stale present-tense claims; `CANARY_AUDIT.md`'s "fee figures are behind JavaScript" corrected — they are in the served HTML and were being misread; `LIVE_DISCOVERY_REPORT.md` rewritten against three measured runs |
| 25 | No TODO / FIXME in a production path | **PASS** | `grep -rn "TODO\|FIXME" backend/app frontend/src` → none |
| 26 | No disabled or skipped tests without written justification | **PASS** | No skips, no xfails |
| 27 | Demo data unmistakably synthetic | **PASS** | Fixture banner, `fixture://` scheme, UI badge, export column. Loads only on an explicit confirmed action |
| 28 | Independent live truth audit, and programme discovery meets its bar | **FAIL** | Main canary **passes** on every bar it has; the measured values, and the sha256 of each run's raw output, are in the artifact. Three runs are three separate executions, kept in `artifacts/canary/` with their digests — the previous artifact recorded only basenames, so three runs and one file counted three times were indistinguishable in the record. All twenty accepted programme pages were opened by hand and every one is a named, specific bachelor's programme. The **holdout fails**: 3 of 6 against a bar of 4, re-measured this cycle and unchanged, with its registry unedited and no seed added. Monterrey is disallowed by `robots.txt`; Tokyo serves no sitemap; Cape Town publishes programme detail in faculty handbook PDFs, and the classifier is handed those PDFs as decoded binary to parse as HTML — a general defect in one call, not fixed here. **The holdout is the gate that keeps the release closed.** |
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

- **FAIL:** 1 — gate 28, holdout recall (3 of 6 against a bar of 4)
- **BLOCKED:** 1 — gate 29, which cannot move while 28 is open
- **NOT RUN:** 1 — gate 22, the container stack, for this commit
- **PASS:** everything else

Product thresholds sit outside this table and are what actually hold the
verdict: decision-grade extraction completeness is far below its bar. A summary
that disagreed with its own table is what this section used to be, and it is
the kind of thing a reader stops checking.

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

* **Running the container stack locally** would require Docker, which is not
  installed here. It is not blocking: the `container-runtime` CI job runs the
  smoke test on every push, and its diagnostics and attestation are uploaded
  with each run.
* **Any external deployment**, domain or billing.
