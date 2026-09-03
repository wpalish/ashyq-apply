# Current state — baseline before production hardening

Recorded at the start of the `production-hardening` branch. This is a factual
snapshot, not a claim of readiness. The product is **NOT READY** for production.

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
| Auth | **None** | OIDC, roles, tenant isolation |
| Multi-tenancy | **Single implicit user** | Organizations, cases, counselor assignment |
| Security headers | CORS only | CSP, HSTS, SSRF defence, rate limiting |
| Discovery | 5 hand-listed institutions | Provider architecture with sitemap discovery |
| Deployment | Containers and compose **written but never run** | Run them; observability |
| CI | None | Full gates on every commit |

## Documentation accuracy

`README.md` currently overstates three things. They are marked here and will be
corrected as each is actually proven:

- *"a run survives a restart"* — no crash-recovery test exists.
- *"PostgreSQL-ready"* — never run against PostgreSQL.
- *"Playwright for JavaScript-rendered pages"* — the tier is never invoked.

## Verdict

**NOT READY.**

Closed since this was written: all ten live false positives (plus five more the
live canary found), the durable job system, PostgreSQL with real migrations,
and crash recovery.

Still open: **no authentication and no tenant isolation** — anyone who can
reach the API can read and delete every profile. The container stack has never
been run. There is no CI. The profile form covers a subset of the schema.

See `RELEASE_CHECKLIST.md` for all thirty gates.

## Update — Phase 1 of the audit fix plan

An external audit produced [`FIX_PLAN.md`](FIX_PLAN.md). Phase 0 re-established
the baseline and Phase 1 closed its six P0 blockers, each with a regression
test written before the fix:

- **Retry destroyed the shortlist.** It deleted every result row while
  resetting only failed stages, so retrying a finished run left 0 of 20
  results and discarded the applicant's decisions. Rows are upserted now and
  decisions travel with them.
- **Repeating document collection was a silent no-op** whenever the shortlist
  changed without changing size.
- **`set_decision` had no tenant check**: an authenticated user of another
  organization could approve or reject rows on someone else's shortlist.
- **Two clicks on Start produced two runs**; the idempotency key was derived
  from the run the request had just created.
- **Rate limits were global behind a proxy**, and an unknown email answered
  faster than a known one.
- **The read-only API container** could not create the directories it makes at
  import time.

Still open and unchanged by Phase 1: the container stack has still never been
run (no Docker here), live programme recall is still 1 of 10 canary
institutions, and Phases 2–6 of the plan — job-lease fencing, the currency bug
in scoring, the stale-run dead end in the UI, the missing auth flows and the
~20 collected-but-unused profile fields — are untouched.

## Update — Phase 2 of the audit fix plan

Seventeen P1 defects, each with a test written before the fix. The ones worth
knowing about if you are reading the code:

- **A worker that lost its lease kept working** and could mark a job succeeded
  that another worker had already taken over, double-counting the run's
  counters. Terminal updates are fenced on the owner now, and the runner stops
  at its next checkpoint.
- **A KZT budget was compared with a USD cost as bare numbers**, so every
  option scored as affordable. The ceiling is converted, with the rate and its
  date in the explanation.
- **Citizenship was matched by substring**: "Korea" satisfied "North Korea
  only", and "Kazakhstan" failed "Central Asian nationals". Both directions
  cost the applicant money. Vague groups are now PENDING rather than a refusal.
- **03/04/2027 was silently read as 3 April.** An ambiguous date is refused.
- **A cached post-study-work right appeared with no source** on every row after
  the first in a country.
- **A global `ValueError → 400` handler** masked 500s as client errors and
  leaked internal text; **the export filter** landed unchecked in a response
  header.
- **`/api/health` never touched the database**, so the probe stayed green with
  PostgreSQL down.
- **POSSIBLY_STALE claims were never re-read.** A finished run now queues a
  recheck for the date its evidence ages out.
- **The account flows did not exist**: no password change, no reset, no
  deletion, no way to reach a second workspace. All four exist, with the
  negative cases tested.
- **The production CSP blocked the fonts the app asked for**, and a render
  error produced a white page with no way back.

Still open and unchanged: the container stack has never been run (no Docker
here), live programme recall is still 1 of 10 canary institutions, and Phases
3-6 of the plan — the ~20 collected-but-unused profile fields, URL routing,
polling behaviour, pagination, the deadline calendar, observability and i18n —
are untouched.
