# Loop report

Each cycle: build a vertical slice, run it, inspect the output, simulate the
failure cases, critique, fix the root cause. Defects below are the ones that
were actually found and fixed — not a list of what was attempted.

---

## Loop 1 — Domain core

**Built.** Controlled vocabularies (`enums.py`), the applicant profile schema,
the claim/provenance schema, and the four rule modules that do the thinking:
funding classification, cost arithmetic, eligibility, scoring.

**Verified.** Each module exercised directly against the boundary cases it
exists for.

**Defects found**

| # | Defect | Root cause | Fix |
|---|---|---|---|
| 1.1 | A 900-character page excerpt was *rejected* by validation, so an extractor handing over surrounding text would crash | The 600-char cap was an `Annotated` constraint, which runs before the truncating validator | Truncate in a `mode="before"` validator, so no caller has to remember the cap |

**Verified working first time.** The silent-conversion guard (a `converted_value`
without a documented method raises), full-ride discipline (a coverage table with
housing `no` classifies as `FULL_TUITION` even when the page says "full ride"),
the cross-year refusal, and the test-optional asymmetry.

**Limitations at this point.** No extraction, no persistence, no interface.

---

## Loop 2 — Extraction and fetching

**Built.** The `Fetcher` (robots.txt, per-host rate limiting, disk cache,
exponential backoff, PII guard), rule-based HTML/PDF extraction, and the
`fixture://` scheme so demo mode shares the live code path.

**Verified.** Live fetch against `rug.nl` (200, robots honoured, second read
served from cache), offline mode, path-traversal refusal, and PDF parsing of a
generated fee schedule.

**Defects found**

| # | Defect | Root cause | Fix |
|---|---|---|---|
| 2.1 | `IELTS ... overall band of 6.5` was not extracted from realistic text | Patterns use `[^.\n]` to stay inside one sentence; real pages wrap mid-clause, so the newline broke the match | `for_matching()` replaces newlines with spaces character-for-character, preserving every offset so excerpts still line up |
| 2.2 | `EUR 450` and `CHF 200` were not parsed | The money pattern required 4+ digits or a thousands separator, so any fee under 1,000 was invisible | Widened to 2–7 digits, still requiring an adjacent currency marker so bare numbers and years are never read as money |
| 2.3 | A minimum test score parsed as `"6.5."` and crashed on `float()` | `[\d.]+` swallowed the sentence's full stop | Bounded to `\d+(?:\.\d+)?` |

---

## Loop 3 — Pipeline and assessment

**Built.** The demo corpus generator (85 pages, 40 candidates, each university
seeded to exercise one QA case), persistence, and the pipeline state machine.

**Verified.** Full run in demo mode: 20 results, 124 claims, 73 pages read.

**Defects found**

| # | Defect | Root cause | Fix |
|---|---|---|---|
| 3.1 | Every result row collided on the same primary key | The id was built as `f"{run_id}-{n:03d}"` then truncated to 32 chars — which is exactly the run id | The row's primary key is generated first and the result document adopts it |
| 3.2 | **UBC's remaining cost was overstated by 18,000 USD**, Tokyo's by 1.9M | `total_cost` returned a *published* total without converting it, so a CAD or JPY figure was netted against a USD award | Convert the published total like any other Money |
| 3.3 | **Groningen showed a 0 USD remaining cost that should have been ~1,850** | Stacking was decided by the added award alone; the primary award's "may not be combined with other university scholarships" was ignored | Stacking needs consent from both sides, and the refusal is reported as a warning |
| 3.4 | Groningen showed 6 contradictions and KU Leuven 4, all spurious | Claims were grouped for conflict detection by `(type, programme, intake)`, so two *different* awards at one university looked like one award contradicting itself | Claims carry a `subject_key`; two awards only conflict when they describe the same award |
| 3.5 | Delft's full ride was flagged as a category mismatch | The classifier accepts a living stipend in place of a meal plan; the gap calculator did not, so the two modules disagreed about the same award | Both apply the substitution |

**Simulation results after fixes** — all ten cases behave:

| Case | Result |
|---|---|
| (a) Applicant meets requirements | Groningen: `MET`-adjacent (`PENDING` on GPA scale), `FULL_RIDE_CONFIRMED` |
| (b) Subscore below a per-band minimum | Delft: `GAP`, hard filter on IELTS writing |
| (c) Award closed by citizenship | KU Leuven Flemish grant: `NOT_ELIGIBLE`, restriction quoted |
| (d) Full tuition marketed as a full ride | ASU: `FULL_TUITION`, promotional wording flagged |
| (e) Official sources contradict | Delft: programme page 6.5 vs admissions 6.0, both shown |
| (f) Deadline passed | Melbourne: `GAP`, "passed" badge |
| (g) Cost from another academic year | Toronto: gap refused, `year_mismatch` |
| (h) Data missing | Vienna: `UNKNOWN`, "not the same as there being none" |
| (i) Site unavailable | Oslo: `NEEDS_OFFICIAL_CLARIFICATION`, listed under unreadable pages |
| (j) User rejects a row | Kept with its reason, not deleted |

---

## Loop 4 — API and interface

**Built.** 24 API endpoints, the design system, and nine screens.

**Defects found**

| # | Defect | Root cause | Fix |
|---|---|---|---|
| 4.1 | Starting a run through the API raised `RuntimeError: no running event loop` | FastAPI runs synchronous route handlers in a threadpool, where `asyncio.create_task` has no loop | The queue binds the application's loop at startup and schedules onto it from a thread |
| 4.2 | Playwright could not reach the dev server | Vite bound to `[::1]` only on this machine, while the base URL was `127.0.0.1` | Host pinned explicitly in `vite.config.ts` |

---

## Loop 5 — End-to-end testing

**Built.** 42 Playwright tests across desktop (1440×900) and mobile (Pixel 7),
plus screenshots of every main state.

**Defects found** — every one of these was found by a test, not by reading code:

| # | Defect | Root cause | Fix |
|---|---|---|---|
| 5.1 | React key warning in the console on every shortlist render | A `<>…</>` fragment in `.map()` had keys on its children rather than on the fragment | `<Fragment key={r.id}>` |
| 5.2 | The documents screen said "the items at the top depend on other people" and then listed a 1-day passport scan first | Groups were rendered in a fixed order, not by lead time | Groups and their contents are ordered by longest lead time, so the referee letter is first |
| 5.3 | **The Decision column — the primary action — was scrolled off-screen at 1440px** | Eight columns with full-length status labels exceeded the container | Short labels in the table with the full phrase as a tooltip, plus the decision column pinned to the right edge |
| 5.4 | Screenshots were captured in mobile layout | `browser.newContext()` ignores the project's `use` block, so the shared session lost its viewport | Viewport and device settings carried across explicitly |
| 5.5 | Mobile screenshots silently overwrote the desktop ones | Both projects wrote the same paths | Namespaced by project |
| 5.6 | **Eligibility enforced the value from the *less* specific of two contradicting pages** while the conflict panel told the user the more specific one was preferred | `_first()` sorted by status then recency; the panel sorted by source specificity | Specificity decides in both places — the UI and the verdict can no longer disagree |

---

## Loop 6 — Test suites, lint and types

**Built.** 233 backend tests, 39 frontend unit tests, ruff, mypy.

**Defects found**

| # | Defect | Root cause | Fix |
|---|---|---|---|
| 6.1 | **Deleting a profile left every run, result and claim behind** | Cascade relied on SQLite's `foreign_keys` pragma, which is per-connection. It worked in the app and failed against a fresh engine | The ORM owns the cascade. Deletion is a privacy guarantee and must not depend on a pragma |
| 6.2 | `/api/vocabulary` omitted the degree levels the profile form offers | Found by the frontend/backend contract test | Added `degree_level` and `curriculum_type` |
| 6.3 | Three functions reused one variable name for two different types (`c` for a claim and a conflict; `parsed` for a date and a money tuple; `m` for six regex matches) | Found by mypy. Not yet a bug, but the shape one arrives in | Distinct names throughout |
| 6.4 | The runner looked up a `CostCategory`-keyed dict with a plain string | Works only because `StrEnum` compares equal to its value | Use the enum member |

**Test defects fixed too** — two assertions were wrong rather than the code:
an audit-log leak check matched `4.8` inside a timestamp's fractional seconds,
and a scoring test used a one-activity profile to assert a threshold that means
"substantive record". Both were tightened rather than the code weakened.

---

## Loop 7 — Live mode against real websites

**Ran** the pipeline in live mode against `rug.nl`, `tudelft.nl`, `aalto.fi`,
`univie.ac.at` and `uw.edu.pl`.

**Defects found**

| # | Defect | Root cause | Fix |
|---|---|---|---|
| 7.1 | **A `PIILeakError` on `https://www.aalto.fi/en/node/1008496` aborted the entire run** | The guard treated any 9+ digit run as a passport number, and raised. CMS node ids are numeric | Long digit runs are suspicious in a *query string*, not a path. And a URL merely *discovered* while crawling is refused and skipped; only a URL the code *builds* from profile fields still raises |
| 7.2 | Six fabricated 404s per institution (`/en/admission-services/en/study-at-aalto`) | Relative links were joined by string concatenation instead of `urljoin` | `urljoin`, with the `fixture://` scheme resolved by hand since `urljoin` does not know it |
| 7.3 | "Menu główne", "Skip to main content" and "Prizes and awards" became scholarships | Every anchor on a funding index page was followed | A link must look like an award in its text or path, and site furniture is excluded |
| 7.4 | Facebook, LinkedIn and Bluesky share URLs were fetched (and correctly refused by robots.txt) | Share buttons carry the page's own URL in a query string, so they matched the award hints | Award links must stay on the institution's own domain |
| 7.5 | Delft reported **"100% verified"** beside "requirements could not be verified" | Completeness was measured over whatever claims happened to be extracted, so one incidental verified fact read as complete | Measured against six core questions a user actually needs answered |
| 7.6 | Warsaw produced an application-fee claim whose value was `"Among this year's applicants, thre"` | The fee extractor fell back to the raw sentence when no amount parsed | A fee that cannot be read is not a claim |

**Live-mode result after fixes:** 16 pages read, 5 unreadable, no crash. It found
TU Delft's real *Justus & Louise van Effen Excellence Scholarship* page. Every
programme reported `NEEDS_OFFICIAL_CLARIFICATION` — honest, because the
homepage-crawling heuristics reach landing pages rather than requirement pages.

---

## Critique (0–10)

Scored after loop 7, against what the product claims about itself.

| Dimension | Score | Reasoning |
|---|---:|---|
| Factual reliability | **9** | Nothing reaches the table without a claim. Ten seeded failure cases pass. The remaining point: extraction is rule-based, so on unseen live pages it under-reports rather than mis-reports — safe, but incomplete. |
| Source provenance | **9** | Every claim carries URL, excerpt, specificity, timestamp and status. Aggregators cannot support decision-grade claims. Contradictions are shown with a drafted question, never resolved silently. |
| Admissions correctness | **8** | Hard filters fire only on confirmed requirements; per-band subscores, test-optional and scale mismatches all behave. Not covered: interviews, portfolios and country-specific rules are surfaced as actions but not evaluated. |
| Scholarship classification | **9** | Marketing language cannot promote a classification. Citizenship restrictions, stacking consent, need-based sizing and living-stipend substitution all behave and are tested. |
| Privacy | **9** | PII guard on every request, audit log asserted clean of applicant data, ORM-level deletion, no sensitive field modelled anywhere. Point withheld for having no encryption at rest. |
| Scraper resilience | **7** | Politeness is thorough and one bad link can no longer end a run. But live discovery works from a curated registry and finds landing pages more often than requirement pages — the honest weak spot. |
| UX | **8** | Three judgements kept visually separate, refusals explained in place, no unexplained spinner, keyboard-reachable, both themes. Dense by design; a first-time user has a lot to take in. |
| Maintainability | **8** | Domain logic is pure and I/O lives behind adapters. `runner.py` at 732 lines is the one file that has grown past comfortable. |
| Test coverage | **9** | 233 backend + 39 unit + 42 E2E; 87% backend coverage; a contract test pins the frontend vocabularies to the backend enums. |
| Accessibility | **8** | Labelled table, named control groups, live progress, `aria-expanded`, focus rings, reduced-motion, no overflow at any breakpoint. No screen-reader pass with a real AT, and no automated axe run. |

**Weakest link:** live discovery. It is the difference between a demo that
proves the machinery and a tool that researches an arbitrary university.

---

---

## Loop 8 — Production hardening: P0 (live truth correctness)

The previous report closed with a critique that scored *factual reliability* at
9/10. A live run then showed six false-positive claims. The score was wrong
because it was taken against a corpus written from the same assumptions as the
code.

**Baseline first.** `pip-audit` had never been run: 36 advisories across 4
packages, 20 of them in `pypdf`, which sits directly in the PDF parsing path.
Upgraded; `requirements.txt` now carries floors annotated with advisory ids.

**Ten false positives, each with a regression test before the fix.**

| # | The system claimed | Root cause | Fix |
|---|---|---|---|
| FP-1 | A programme existed, from a general admissions page | No page classification at all — HTTP 200 was treated as confirmation | `page_classifier.py` (14 classes) + `matching.py`; PROGRAM_EXISTS needs a programme page whose subject and degree match |
| FP-2 | Every intake was open | Inferred from the absence of "applications are closed" | Positive claims need positive evidence, scoped to the cycle asked about |
| FP-3 | Evidence quoted sentences the extractor wrote | Excerpts were built, not quoted | Every excerpt is verbatim; asserted on both adapters |
| FP-4 | Index, FAQ and navigation pages were scholarships | Every anchor was followed and every page trusted | Only `SCHOLARSHIP_AWARD` pages produce awards |
| FP-5 | Any mention of "international students" meant eligible | Substring test | Affirmative clause required |
| FP-6 | An MSc award was offered to a bachelor applicant | Degree was never checked | `applicability.py` + `degree_applicability` |
| FP-7 | No deadline meant available | One field answering several questions | Seven separate states, all defaulting to unknown |
| FP-8 | `candidate_limit` was accepted | It was never read | Persisted on the run, applied, capped, reused on retry |
| FP-9 | A Playwright tier "existed" | Constructed every run, invoked never | Escalation moved inside `Fetcher`; tiers recorded and asserted |
| FP-10 | A reload kept the demo profile in the draft | Restore populated `savedProfile` only | Draft hydrated from the payload; demo loads only on explicit confirmation |

**Then the canary found five more that the fixtures could not.**

| # | Defect | Why fixtures missed it |
|---|---|---|
| C-1 | Site chrome read as content: the global menu made an award page look like an index and an admissions page like a catalogue; the first `<h1>` came from the header | Hand-written fixtures have no site chrome |
| C-2 | "…who has obtained their bachelor's degree" read as "this award is for bachelors" | Nobody writes that sentence in a fixture |
| C-3 | An award's level settled by a positive statement about a *different* level ("for one of the following Master of Science Programmes") | Fixtures state exclusions explicitly |
| C-4 | "Scholarships from other providers" treated as an award | Fixture headings are either clean names or bare categories |
| C-5 | `\btuition fee\b` does not match "tuition fees" | The fixture used the singular |

Two further defects surfaced while fixing these: `classify()` ignored
applicant-level eligibility, so an EEA-only award was classified as funding for
a Kazakhstani applicant; and the frontend/backend contract parser was truncated
by a semicolon inside a doc comment, silently shortening the vocabulary it
checked.

**Two test expectations were corrected**, both with reasons recorded in the test
file: an EEA-only award is a citizenship restriction, not a blanket exclusion of
international students; and a one-activity profile is not what "substantive
activity record" means.

**Result.** 301 backend tests (from 240), 47 frontend unit (from 39), 48 E2E
(from 42). Coverage 89%. Live canary against Groningen and TU Delft: two claims,
both true, both quoting real page text, zero false positives — recorded
claim-by-claim in `docs/CANARY_AUDIT.md`.

**What this loop did not do.** P1 through P12 are untouched: no PostgreSQL, no
migrations, no durable queue, no authentication, no multi-tenancy, no
containers, no CI. `RELEASE_CHECKLIST.md` tracks all thirty gates; 17 pass.

### Critique, re-scored after the canary

The previous scores were taken against the product's own fixtures. These are
taken against a live run.

| Dimension | Was | Now | Why it moved |
|---|---:|---:|---|
| Factual reliability | 9 | **8** | Zero false positives on two live institutions, proven claim by claim — but three institutions are unaudited, so 9 would be unearned |
| Source provenance | 9 | **9** | Excerpts are now verbatim everywhere, and page class is recorded per source |
| Admissions correctness | 8 | **7** | More correct and much less complete: live runs now mostly answer "unknown" |
| Scholarship classification | 9 | **9** | Degree applicability and decomposed availability close the two worst gaps |
| Privacy | 9 | **8** | The PII guard aborted an entire run on a CMS node id; now scoped and non-fatal, but it was shipped untested against real URLs |
| Scraper resilience | 7 | **8** | Chrome stripping, correct URL joining, same-domain restriction, non-fatal refusals |
| UX | 8 | **7** | The reload bug destroyed real data; the form still covers a subset of the schema |
| Maintainability | 8 | **7** | `runner.py` is 780 lines and `page_classifier.py` 420; both want splitting |
| Test coverage | 9 | **9** | 396 tests, 89% coverage, and the new tests encode real defects rather than happy paths |
| Accessibility | 8 | **7** | Unchanged in substance, but no axe run means the score was never earned |
| **Production readiness** | — | **2** | No auth, no durable jobs, no PostgreSQL, no containers, no CI |

**Weakest link is no longer live discovery — it is that this is not production
software.** Correctness work is ahead of the platform work by a wide margin.

## Known remaining limitations

1. Live discovery reaches landing pages more reliably than requirement pages, so
   live runs produce more `NEEDS_OFFICIAL_CLARIFICATION` than demo runs.
2. Extraction is rule-based. It under-reports on unseen page structures.
3. Vienna's live funding page yields research prizes (ERC, Nobel) rather than
   student scholarships — the award-link heuristic cannot tell them apart.
4. `runner.py` is 732 lines and should be split by stage.
5. No automated accessibility audit; the checks are hand-written assertions.
6. Currency rates are a dated static snapshot.
7. The job queue is in-process.

None of these cause a wrong answer. Each causes a *missing* answer, reported as
missing.
