# ASHYQ Apply

*Internal package, database and module names remain `unimatch`; renaming them
now would be churn without benefit. The product name is ASHYQ Apply.*

University and scholarship shortlisting for international applicants, where every
material value on screen traces back to the page it was read from.

> **Status: NOT READY for production.** This is a working local prototype whose
> live-mode claims are now trustworthy, but it has no authentication, no
> multi-tenancy, no durable job system and no deployment story. See
> [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) for the honest position and
> [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) for what is left.

The product answers one question — *which universities can I get into, and which
of those will actually pay for it?* — and it answers it with a source, an
excerpt, and a date attached to each claim. It never predicts an admission or an
award, and it never converts an unknown into a guess.

---

## Quick start

Two terminals. Nothing else to configure: demo mode runs entirely offline
against a bundled corpus, with no API keys and no network access.

**Backend**

```bash
cd backend && ./setup.sh && ./run.sh
```

`run.sh` migrates the database, then starts the API. Add `--with-worker` to
start a queue worker alongside for local use:

```bash
cd backend && ./run.sh --with-worker
```

In production the two are separate processes — the API only enqueues work and a
worker consumes it — which is what `docker-compose.yml` runs.

**Frontend**

```bash
cd frontend && npm install && npm run dev
```

Open <http://127.0.0.1:5173>. The default profile is a synthetic applicant
already filled in — press **Start research** and the pipeline runs end to end in
about ten seconds.

API docs are at <http://127.0.0.1:8099/docs>.

---

## What it does

1. **Takes a structured applicant profile** — level, citizenship, grades on their
   original scale, every IELTS subscore, activities with hours and outcomes,
   preferences, and a budget.
2. **Finds candidate universities** from catalogues and rankings, which are used
   for discovery only and can never support a requirement or a price.
3. **Reads the official programme page** for each candidate and extracts the
   published requirements, deadline and fees.
4. **Reads the official scholarship pages** and builds a per-cost-category
   coverage table for each award.
5. **Assesses three independent things** and never collapses them into one
   verdict:
   - **Eligibility** — do you meet the published requirements?
   - **Admissions fit** — where does your profile sit against them?
   - **Funding fit** — what does an official page say an award covers?
6. **Computes the remaining annual cost**, or refuses to and says why.
7. **Lets you approve, reject or flag** each row, keeping rejections with their
   reason.
8. **Collects documents and deadlines** for the shortlist you approved.

### The judgements it is careful about

| Situation | What UniMatch does |
|---|---|
| A page says "a full ride" but its table shows tuition and fees only | Classifies **FULL_TUITION**, flags the promotional wording |
| Your IELTS overall clears 6.5 but writing is below a 6.5 per-band rule | **GAP** on IELTS writing, not a pass |
| A scholarship is open only to EEA citizens | **NOT_ELIGIBLE** for a Kazakhstani applicant, with the restriction quoted |
| The award amount is for 2024/25 and the costs for 2026/27 | **Refuses** to show a zero remaining cost, and says the figures are not comparable |
| The programme page says IELTS 6.5, the admissions page says 6.0 | Shows **both**, marks the programme page as more specific, drafts an email to admissions, and enforces the stricter one |
| No scholarship page could be read | **UNKNOWN**, explicitly "not the same as there being none" |
| The site is unreachable | **NEEDS_OFFICIAL_CLARIFICATION**, listed under pages that could not be read |
| Your GPA is on a 5-point scale and the programme publishes 4.0 | Refuses to decide until you accept a documented conversion |
| A programme is test-optional and you have no SAT | Not a barrier — **MET** |

### What it will not do

- Predict admission or funding. There is no "73% chance" anywhere, by design.
- Convert a grade silently. A converted value cannot exist without a stored
  method and source.
- Submit an application, sign anything, pay a fee, or upload a document.
- Put any part of your profile into an outbound URL. A guard raises rather than
  letting it through.
- Bypass a CAPTCHA, a login, or robots.txt.

---

## Architecture

```
backend/
├── app/
│   ├── domain/          Pure business rules — no I/O, no framework
│   │   ├── enums.py         Every controlled vocabulary, incl. an explicit "unknown"
│   │   ├── funding.py       Coverage table -> FULL_RIDE_CONFIRMED / FULL_TUITION / ...
│   │   ├── costs.py         The gap arithmetic, and the cases it refuses
│   │   ├── eligibility.py   Published requirements vs the profile; hard filters
│   │   ├── scoring.py       Explainable weighted score + missing-data penalty
│   │   ├── conflicts.py     Detects contradictions; never resolves them silently
│   │   ├── freshness.py     Per-claim-type staleness windows
│   │   ├── grades.py        Conversions offered with their caveats, never applied
│   │   ├── currency.py      Dated static FX, exposes its rate
│   │   ├── dedupe.py        Stable keys for universities/programmes/awards
│   │   └── validation.py    Profile gaps with their concrete consequence
│   ├── adapters/        Everything that touches the outside world
│   │   ├── fetching.py      robots.txt, rate limiting, disk cache, backoff, PII guard
│   │   ├── browser.py       Playwright tier for JS-rendered pages
│   │   ├── extraction.py    HTML/PDF -> claims, each carrying its excerpt
│   │   ├── discovery/       Catalogue (demo) and live institution-registry crawler
│   │   ├── requirements/    Programme + admissions pages
│   │   ├── scholarship/     Award pages, coverage tables read structurally
│   │   ├── cost/            Fee pages, HTML and PDF
│   │   ├── documents/       Document checklists
│   │   └── government/      Post-study work rules
│   ├── jobs/            Durable queue (store.py) and the worker process
│   ├── pipeline/        State machine, resumable per stage
│   ├── api/             FastAPI routes
│   ├── export/          CSV / JSON / XLSX, provenance included
│   ├── models/          SQLAlchemy (SQLite now, PostgreSQL-ready)
│   └── corpus/          The bundled synthetic demo corpus + its generator
└── tests/               349 tests
frontend/
├── src/
│   ├── screens/         The nine workflow screens
│   ├── components/      Primitives + the university detail drawer
│   ├── lib/             Store, formatting, immutable helpers
│   ├── api/             Typed client
│   └── styles/          Design tokens + component styles
└── e2e/                 42 Playwright tests (desktop + mobile)
```

### The claim is the unit of truth

Nothing reaches the results table unless it traces to a `Claim`:

```python
Claim(
    claim_type=ClaimType.IELTS_MIN_OVERALL,
    normalized_value=6.5,
    original_text_excerpt="...an overall band of 6.5, with no individual component below 6.0...",
    source_url="https://www.tudelft.nl/en/education/.../admission-requirements",
    source_specificity=SourceSpecificity.PROGRAM_INTAKE,
    accessed_at=datetime(2026, 8, 27, ...),
    status=ClaimStatus.VERIFIED_CURRENT,
)
```

Source specificity is ordered, and that order does real work. A programme page
beats a general admissions page; any official page beats an aggregator; and a
*decision-grade* claim (a requirement, a deadline, a price, an award amount)
resting only on an aggregator is automatically demoted to
`NEEDS_OFFICIAL_CLARIFICATION` with a question raised for the user.

### The pipeline

```
profile_validation → candidate_discovery → program_verification
    → funding_discovery → assessment → [awaiting_user_decision]
    → document_collection → completed
```

State lives in the database, not in a running task, and so do the jobs. A
worker claims a job with `SELECT … FOR UPDATE SKIP LOCKED`, holds a lease on it
and refreshes that lease as it works. A lease that stops being refreshed is how
a crashed worker becomes visible: another worker's reaper returns the job to
the queue, and a job that exhausts its attempts goes to `dead` rather than
looping.

**A crashed run resumes.** Stages already marked complete are not repeated, and
persisting a result updates the row a previous attempt wrote rather than
colliding with it. `scripts/crash_test.py` proves this by SIGKILLing a real
worker after twelve results exist and requiring a second worker to finish
without duplicating anything.

Document collection runs *after* the user decides, because it is the expensive
stage and only the shortlist needs it.

---

## Data sources and adapters

| Adapter | Role | Demo | Live |
|---|---|---|---|
| `fixture-catalog` | University/programme discovery | ✅ | — |
| `fixture-rankings` | Ranking snapshot (discovery only) | ✅ | — |
| `live-institution-registry` | Discovery by crawling institution homepages | — | ✅ |
| `web-requirements` | Programme + admissions requirements | ✅ | ✅ |
| `web-costs` | Cost of attendance, HTML and PDF | ✅ | ✅ |
| `web-scholarships` | Awards, coverage, eligibility, deadlines | ✅ | ✅ |
| `web-documents` | Document checklists | ✅ | ✅ |
| `web-government` | Post-study work rules | ✅ | ✅ |

The verification adapters are URL-scheme agnostic. They read a bundled
`fixture://` page and a live `https://` page through the same code, so demo mode
rehearses the real extraction path rather than returning canned objects.

### Fetch strategy

1. Structured data where a site publishes it.
2. Plain HTTP for static pages.
3. **Playwright** for JavaScript-rendered pages. Escalation lives inside
   `Fetcher`, so every adapter goes through it; the tier that produced each
   page is recorded, and per-run tier counts are on the run. It fires only when
   a plain fetch returns a page with under 400 characters of extractable text,
   and it is gated by robots.txt exactly as plain HTTP is. Two tests assert
   that it is genuinely invoked and that it is *not* invoked for a page that
   already has content.
4. **PDF parsing** for handbooks and fee schedules.
5. Otherwise `NOT_FOUND` / `NEEDS_OFFICIAL_CLARIFICATION`, never a guess.

### Politeness and privacy

Every network read goes through one `Fetcher`, which makes the guarantees
checkable in one place:

- robots.txt is fetched once per host and honoured, including for the browser tier
- per-host concurrency capped at 2, requests spaced (honouring `Crawl-delay`)
- responses cached on disk; exponential backoff on 429/5xx
- an identifying User-Agent with a contact address
- **`assert_no_pii` runs on every request** and raises rather than letting an
  email address, a long ID number, or a credential-shaped parameter into a URL

### Demo mode

The bundled corpus is 85 generated pages covering 16 universities in detail plus
24 catalogue-only entries — 40 candidates in total. Every page carries a visible
and machine-readable fixture banner, every source shows as `fixture://` in the
UI with a **demo fixture** badge, and every exported row is stamped
`DEMO FIXTURE (synthetic)` in its data-origin column.

**The demo figures are invented.** Institution names are real so the demo reads
naturally; the numbers, deadlines, scholarships and policies are not. Never
quote them.

Regenerate the corpus with:

```bash
cd backend && ./.venv/bin/python -m app.corpus.build
```

---

## Live mode

Toggle **Demo mode** off on the preferences screen, or set
`UNIMATCH_DEMO_MODE=false`. Live mode crawls the institutions listed in
`backend/app/adapters/discovery/institution_registry.json`, starting from each
homepage rather than a search engine — a search query would carry applicant
context off the machine.

Live mode is slower, and it finds less. That is honest: it reports what it could
read and marks the rest as not found.

A **live truth audit** against `rug.nl` and `tudelft.nl` is recorded in
[`docs/CANARY_AUDIT.md`](docs/CANARY_AUDIT.md): every claim the system made,
checked by hand against the page it came from. It currently shows **zero
false-positive material claims** for those two institutions. Aalto, Vienna and
Warsaw have not yet been audited.

---

## Commands

```bash
# Backend
cd backend
./setup.sh                                    # venv + dependencies + corpus + browser
./run.sh                                      # migrate, then API on :8099
./run.sh --with-worker                        # ... and a queue worker alongside
./worker.sh                                   # a worker on its own (run several)
python scripts/pg.py --print-uri              # a local PostgreSQL, no install needed
python scripts/pg.py .venv/bin/pytest         # run the suite against PostgreSQL
python scripts/pg.py .venv/bin/python scripts/crash_test.py   # SIGKILL recovery proof
./.venv/bin/python -m pytest                  # 349 tests
./.venv/bin/python -m pytest --cov=app        # with coverage (89%)
./.venv/bin/python -m ruff check app tests    # lint
./.venv/bin/python -m mypy app                # type check
./.venv/bin/python seed_demo.py --approve     # run the whole pipeline on the CLI

# Frontend
cd frontend
npm run dev            # Vite on :5173, proxies /api to :8099
npm run build          # production build
npm run typecheck      # tsc --noEmit
npm run lint           # eslint
npm test               # 47 Vitest unit tests
npm run e2e            # 48 Playwright tests, desktop + mobile (starts both servers itself)
npm run e2e:report     # open the last Playwright report
```

Or from the repository root: `make setup`, `make dev`, `make test`, `make check`.

---

## Verification

| Check | Result |
|---|---|
| Backend tests | 349 passed (SQLite **and** PostgreSQL 16.2) |
| Backend coverage | 89% (`app/`); jobs/store 91%, jobs/worker 83%, pipeline/runner 91% |
| Backend lint (ruff) | clean |
| Python dependency audit (pip-audit) | clean (36 advisories found and fixed at baseline) |
| Backend types (mypy) | clean, 67 files |
| Frontend unit tests | 47 passed |
| Frontend typecheck | clean |
| Frontend lint (eslint) | clean |
| E2E (Playwright) | 48 passed — desktop 1440×900 and Pixel 7 |
| Console errors during the full journey | 0 |
| Horizontal overflow at 320/768/1024/1440 | none |
| Production bundle | 68.9 kB JS gzipped, 5.1 kB CSS |

| Crash recovery | verified: real SIGKILL, job recovered, 0 duplicate results |
| Migrations | verified: fresh, downgrade, re-upgrade, re-apply, both backends |
| Container stack | **written, never run** — Docker is not installed here |

Screenshots of every main state are in [`docs/screenshots/`](docs/screenshots/)
(desktop) and `docs/screenshots/mobile/`.

---

## Configuration

Copy `.env.example` to `backend/.env`. No secrets are required to run anything.

| Variable | Default | Purpose |
|---|---|---|
| `UNIMATCH_DEMO_MODE` | `true` | Use the bundled corpus, no network |
| `UNIMATCH_RESPECT_ROBOTS` | `true` | Honour robots.txt — leave this on |
| `UNIMATCH_FETCH_DELAY_SECONDS` | `1.5` | Minimum spacing between requests to one host |
| `UNIMATCH_FETCH_CONTACT` | *(empty)* | Contact address in the User-Agent; set it for live crawling |
| `UNIMATCH_ENABLE_BROWSER_TIER` | `true` | Allow Playwright escalation |
| `UNIMATCH_CANDIDATE_LIMIT` | `40` | Candidates to discover |
| `UNIMATCH_VERIFY_LIMIT` | `20` | Candidates to verify in depth |
| `UNIMATCH_TARGET_CURRENCY` | `USD` | Currency for cost comparison |
| `UNIMATCH_DATABASE_URL` | SQLite file | PostgreSQL in production. The full test suite runs against PostgreSQL 16.2 as well as SQLite. |
| `UNIMATCH_AUTO_MIGRATE` | `false` | Migrating is a deliberate step; two processes migrating together race |
| `UNIMATCH_WORKER_CONCURRENCY` | `2` | Jobs a worker runs at once |
| `UNIMATCH_JOB_LEASE_SECONDS` | `120` | How long a claimed job is held before it can be reaped |

---

## Limitations

These are real, and the UI states them rather than hiding them.

0. **Not production software.** No authentication and no multi-tenancy: anyone
   who can reach the API can read and delete every profile. The containers have
   never been run. There is no CI. Single user, local machine.
1. **No outcome prediction.** ASHYQ Apply reports published criteria. Selection is
   competitive and depends on factors no public page states.
2. **Extraction is rule-based and conservative.** It finds what its patterns
   match and reports nothing where they do not. On live pages it will miss
   values that a human would find — those show as *not found*, never as a guess.
3. **Currency rates are a dated static snapshot** (`app/domain/currency.py`),
   not a live feed. The rate and its date travel with every converted figure.
4. **Grade conversions are approximations** and are never applied unless the
   user accepts one. US applications generally require a NACES credential
   evaluation, which this tool does not replace.
5. **Live discovery works from a curated registry**, not a search engine. Adding
   institutions means editing the registry.
6. **Cost pages behind a fee calculator** yield no figures. TU Delft's tuition
   page is a real example: the page is readable, the numbers are not on it, and
   the result is an honest "no cost figures could be extracted".
7. **The queue is PostgreSQL-backed, not Redis.** A deliberate choice, recorded
   in [ADR 0001](docs/adr/0001-durable-job-queue.md): no broker could be
   installed here without your password, and one transaction covering both the
   job and its output is a real advantage for minutes-long jobs. Very high job
   rates would eventually want a broker; the interface is ready for one.
8. **Demo data is synthetic**, as described above.
9. **No portal automation.** Nothing is uploaded, submitted, signed or paid for.

---

## Privacy

- The applicant profile lives in one JSON document, so *export everything* and
  *delete everything* are single auditable operations.
- Deleting a profile cascades to every run, result, claim, conflict and
  checklist. The cascade is enforced by the ORM, not by a SQLite pragma that
  could be lost on a connection.
- The audit log records ids and action names only. A test asserts that no name,
  citizenship, test name or GPA appears in it.
- No passwords, one-time codes, payment details, passport numbers or medical
  data are modelled anywhere, so no code path can persist one.
- `backend/data/` is gitignored in full.

---

## Documents

- [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) — the honest baseline, including what is missing
- [`docs/CANARY_AUDIT.md`](docs/CANARY_AUDIT.md) — live truth audit, claim by claim
- [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) — the gates, and which are open
- [`ASSUMPTIONS.md`](ASSUMPTIONS.md) — every decision taken without asking, and why
- [`LOOP_REPORT.md`](LOOP_REPORT.md) — each build/test/critique cycle, the defects found and how they were fixed
- [`docs/screenshots/`](docs/screenshots/) — every main state, desktop and mobile
