# Baseline snapshot — taken before production hardening

> **This file is a dated snapshot, not the current state.** It records what was
> true when the `production-hardening` branch started, and it is kept because
> the before/after is the evidence that the work happened. Several rows below
> were true then and are false now; each is marked. For what is true today see
> `RELEASE_CHECKLIST.md`, and for discovery specifically
> `docs/LIVE_DISCOVERY_REPORT.md`.
>
> The verdict has not changed: the product is **NOT READY** for production.

## What exists

A working local prototype: a research pipeline that reads official pages,
records every value as a sourced claim, assesses eligibility / admissions fit /
funding fit independently, and produces a shortlist with exports.

| Component | Size |
|---|---|
| Backend | 60 Python files, ~8,900 lines |
| Frontend | 20 TypeScript files, ~3,650 lines |
| Demo corpus | 85 generated pages, 40 candidates |
| API | 24 endpoints |

## Baseline verification (all re-run today)

| Check | Result |
|---|---|
| Backend tests | 240 passed |
| Backend coverage | 88% |
| ruff | clean |
| mypy | clean, 60 files |
| Frontend unit tests | 39 passed |
| TypeScript | clean |
| ESLint | clean |
| Production build | 68.9 kB JS gzip, 5.1 kB CSS |
| E2E (Playwright) | 42 passed, desktop + mobile |
| npm audit | 0 vulnerabilities |
| pip-audit | **36 advisories across 4 packages — fixed during baseline** |

### Dependency vulnerabilities found and fixed at baseline

`pip-audit` had never been run. It found:

| Package | Was | Now | Advisories | Why it mattered here |
|---|---|---|---|---|
| `pypdf` | 6.9.2 | ≥6.15.0 | 20 | Directly in the PDF parsing path; malformed-PDF handling |
| `starlette` | 0.46.2 | ≥1.3.1 | 9 | Request handling under FastAPI |
| `python-multipart` | 0.0.20 | ≥0.0.31 | 6 | Form parsing |
| `pytest` | 8.4.2 | ≥9.0.3 | 1 | Test tooling only |

Post-upgrade: `pip-audit` reports no known vulnerabilities, and all 240 tests
still pass. `requirements.txt` now carries floors with the advisory ids.

## Known false positives in live mode

These were observed in a real run against `rug.nl`, `tudelft.nl`, `aalto.fi`,
`univie.ac.at` and `uw.edu.pl`. **They are the P0 work.** Each is a claim the
system made that an official source does not support.

| # | The system claimed | Reality |
|---|---|---|
| FP-1 | `PROGRAM_EXISTS: computer science (bachelor)` at Groningen and Vienna | Read from a general admissions page and a careers page. Neither confirms that programme exists at that degree level. |
| FP-2 | `INTAKE_OPEN: true` for every programme | Inferred from the *absence* of the phrase "applications are closed". No cycle, window or deadline was confirmed. |
| FP-3 | Excerpt `"Page describes entry for the fall 2027 intake."` | A synthetic sentence the extractor wrote, presented in the evidence panel as if quoted from the page. |
| FP-4 | `SCHOLARSHIP_EXISTS: "Scholarships"`, `"Practical matters"`, `"Prizes and awards"` | Index pages, navigation and research-prize pages, counted as individual awards. |
| FP-5 | `SCHOLARSHIP_INTERNATIONAL_ELIGIBLE: true` | Fired on any page containing the phrase "international students", including "few external scholarships are offered to international students". |
| FP-6 | TU Delft's Justus & Louise van Effen Scholarship shown to a **bachelor** applicant | The award is for MSc students. Degree applicability was never checked. |
| FP-7 | `available_this_intake: yes` with no deadline found | Absence of a deadline was read as availability. |
| FP-8 | `candidate_limit` accepted by the API | Never applied — the pipeline used the server-wide setting. |
| FP-9 | Playwright tier reported as a capability | `BrowserFetcher` is constructed but `fetch_with_escalation` is never called by any adapter. Dead code presented as a feature. |
| FP-10 | Profile draft after reload | A saved profile is restored into `savedProfile` but the form keeps the synthetic `DEFAULT_PROFILE`; saving then overwrites real data with demo data. |

## Architecture gaps for production

Updated after P1.

| Area | Current | Required |
|---|---|---|
| Database | **PostgreSQL + Alembic ✅** — suite passes on PostgreSQL 16.2 and SQLite | — |
| Jobs | **Durable PostgreSQL queue ✅** — leases, reaping, backoff, dead-letter, idempotency; crash recovery proven with a real SIGKILL | A broker if job rates ever justify one |
| Auth | ~~**None**~~ → **done**: opaque server sessions, scrypt, organizations | — |
| Multi-tenancy | ~~**Single implicit user**~~ → **done**: organizations and applicant cases; every id-bearing route refuses another tenant with 404 | — |
| Security headers | ~~CORS only~~ → **done**: CSP, HSTS, SSRF defence, rate limiting | — |
| Discovery | ~~5 hand-listed institutions~~ → **sitemap-first** across ten, with a frozen six-country holdout set. Programme-page recall remains the open product problem | Recall; see the live report |
| Deployment | Containers and compose written; CI now has a runtime smoke job. **Still never run** — no container runtime on this machine | Run the job; observability |
| CI | ~~None~~ → **done**: frontend, backend on SQLite and PostgreSQL, security and containers | — |

## Documentation accuracy

`README.md` currently overstates three things. They are marked here and will be
corrected as each is actually proven:

- ~~*"a run survives a restart"*~~ — `scripts/crash_test.py` now SIGKILLs a
  real worker and proves recovery without duplicates.
- ~~*"PostgreSQL-ready"*~~ — the whole suite runs on PostgreSQL 16.2.
- ~~*"Playwright for JavaScript-rendered pages"*~~ — the tier is invoked, both
  automatically when a page carries no text and on request when a catalogue's
  programme list is built client-side.

## Verdict

**NOT READY.**

Closed since this was written: all ten live false positives (plus five more the
live canary found), the durable job system, PostgreSQL with real migrations,
and crash recovery.

Still open **as of this snapshot** — since closed except where noted: no
authentication and no tenant isolation (closed); the container stack has never
been run (**still true**: no container runtime is installed here); there is no
CI (closed); the profile form covers a subset of the schema (closed).

The open problem this snapshot did not know about is programme-page recall in
live discovery, which is measured in `docs/LIVE_DISCOVERY_REPORT.md`.

See `RELEASE_CHECKLIST.md` for all thirty gates.
