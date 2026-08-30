# ASHYQ Apply

*Internal package, database and module names remain `unimatch`; renaming them
now would be churn without benefit. The product name is ASHYQ Apply.*

University and scholarship shortlisting for international applicants, where every
material value on screen traces back to the page it was read from.

> **Status: release candidate, not publicly deployed.** Authentication, tenant
> isolation, durable PostgreSQL jobs, CI, backups and production images exist
> and are tested. The remaining release blockers are a real container/deploy
> run and low live programme-page recall (1 of 10 canary institutions). See
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
│   ├── models/          SQLAlchemy + Alembic (PostgreSQL production, SQLite local)
│   └── corpus/          The bundled synthetic demo corpus + its generator
└── tests/               the suite (count in the release artifact)
frontend/
├── src/
│   ├── screens/         The nine workflow screens
│   ├── components/      Primitives + the university detail drawer
│   ├── lib/             Store, formatting, immutable helpers
│   ├── api/             Typed client
│   └── styles/          Design tokens + component styles
└── e2e/                 50 Playwright tests (desktop + mobile, including axe)
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

A **live truth audit** against ten official university domains is recorded in
[`docs/LIVE_DISCOVERY_REPORT.md`](docs/LIVE_DISCOVERY_REPORT.md). Sitemap-first
discovery reaches 26 of 30 admissions/cost/scholarship categories and produces
zero audited material false positives, but confirms an individual programme
page on only one institution in ten. That limitation is visible here because
finding a category page is not the same as building a useful shortlist.

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
./.venv/bin/python -m pytest                  # the whole suite
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
npm run e2e            # 50 Playwright tests, desktop + mobile (starts both servers itself)
npm run e2e:report     # open the last Playwright report
```

Or from the repository root: `make setup`, `make dev`, `make test`, `make check`.

---

## Verification

The measured numbers live in
[`artifacts/release-evidence.json`](artifacts/release-evidence.json), generated
by `backend/scripts/release_evidence.py` and rendered into
[`docs/evidence/RELEASE-EVIDENCE-2026-08-29.md`](docs/evidence/RELEASE-EVIDENCE-2026-08-29.md).
They are deliberately not repeated here. This section once carried a test
count and a programme recall that had both been true months earlier and were
false by the time anyone read them, because nothing was checking it.

What is stable enough to state in prose:

| Check | Where |
|---|---|
| Backend tests, coverage, lint, types | the generated gate table |
| Frontend unit, typecheck, lint, build | the generated gate table |
| E2E (Playwright), desktop 1440×900 and Pixel 7 | the generated gate table |
| Accessibility | axe WCAG A/AA on every reachable screen, inside the E2E run |
| Crash recovery | real SIGKILL, job recovered, no duplicate results |
| Migrations | fresh, downgrade, re-upgrade, re-apply, on SQLite and PostgreSQL |
| Container stack | run by the `container-runtime` CI job on every push, not on a developer machine |
| Live discovery | three canary runs plus a frozen holdout, in the generated table |

**The product is NOT READY**, and the reason is not technical: decision-grade
extraction completeness and holdout recall are both below their bars. The
verdict in the artifact is computed from those thresholds, not asserted.

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
| `UNIMATCH_AUTH_ENABLED` | `false` locally | Required in production; enables opaque server sessions |
| `UNIMATCH_AUTH_REGISTRATION_ENABLED` | `true` | Keep false for an invite-only public deployment |
| `UNIMATCH_COOKIE_SECURE` | `false` locally | Required in production behind HTTPS |
| `UNIMATCH_CORS_ORIGINS` | local Vite origins | Explicit HTTPS origins are required in production |

---

## Limitations

These are real, and the UI states them rather than hiding them.

0. **Not deployed production software.** Auth, organization isolation, CI and
   deployment definitions are implemented and tested, but the container stack
   has not been run on this Mac and no public deployment has had an operational
   security review.
1. **No outcome prediction.** ASHYQ Apply reports published criteria. Selection is
   competitive and depends on factors no public page states.
2. **Extraction is rule-based and conservative.** It finds what its patterns
   match and reports nothing where they do not. On live pages it will miss
   values that a human would find — those show as *not found*, never as a guess.
3. **Currency rates come from the European Central Bank's daily reference
   feed**, with the date they describe and their source travelling with every
   converted figure. There is no silent fallback: a rate older than ten days,
   or a currency the ECB does not publish — the tenge among them — is refused,
   the amount stays in its source currency, and the funding gap is reported as
   not computable. The bundled dated table is still there for tests and demo
   mode, and every conversion made from it is labelled an estimate.
4. **Grade conversions are approximations** and are never applied unless the
   user accepts one. US applications generally require a NACES credential
   evaluation, which this tool does not replace.
5. **Live discovery confirms a programme page at 4 institutions in 10.** This
   is the product's largest open problem and the reason it is not ready. It
   uses a curated registry, official seeds and sitemaps rather than sending
   applicant context to a search engine. Three independent runs on 2026-08-29
   gave 4, 4 and 4; category pages reach 27 of 30. Every accepted programme
   page was opened by hand and is real — the gap is recall, not truthfulness.
   `docs/LIVE_DISCOVERY_REPORT.md` names the reason for each of the six
   misses; four are defects and two are honest NOT_FOUND.
6. **Cost figures in a dense fee table are not extracted.** TU Delft's tuition
   page is a real example — and the earlier claim that its numbers sit behind a
   JavaScript calculator was wrong: they are in the served HTML, and were being
   misread. `€ 17.310` parsed as `17.31` until this cycle. Associating a figure
   in a fee table with the right label still needs more than proximity, so the
   result is an honest "no cost figures could be extracted" rather than a
   number attached to the wrong row.
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
- Passwords are stored only as salted `scrypt` hashes. One-time codes, payment
  details, passport scans and medical data are not modelled.
- `backend/data/` is gitignored in full.

---

## Documents

- [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) — the honest baseline, including what is missing
- [`docs/CANARY_AUDIT.md`](docs/CANARY_AUDIT.md) — live truth audit, claim by claim
- [`docs/LIVE_DISCOVERY_REPORT.md`](docs/LIVE_DISCOVERY_REPORT.md) — sitemap discovery canary across ten institutions
- [`SECURITY.md`](SECURITY.md) — threat model, privacy controls and residual risks
- [`docs/BACKUP_RESTORE.md`](docs/BACKUP_RESTORE.md) — backup policy and verified restore drill
- [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) — the gates, and which are open
- [`ASSUMPTIONS.md`](ASSUMPTIONS.md) — every decision taken without asking, and why
- [`LOOP_REPORT.md`](LOOP_REPORT.md) — each build/test/critique cycle, the defects found and how they were fixed
- [`docs/screenshots/`](docs/screenshots/) — every main state, desktop and mobile
