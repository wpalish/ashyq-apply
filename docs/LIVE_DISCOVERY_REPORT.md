# Live discovery (P1.8) — what it finds, and what it does not

**Branch:** `claude/live-discovery` (from `0fecc95`)
**Access date for every live figure below:** 2026-08-28
**Scope:** discovery only. Nothing in auth, tenancy, routing, jobs, migrations,
fetching, the browser tier or the frontend was touched.

## What changed

Discovery used to walk a university's global navigation from the homepage.
The live canary shows what that was worth: across ten official university
domains it reached **0 programme pages** and **12 of 30** category pages
(admissions / costs / scholarships).

Discovery is now **sitemap-first**, in three tiers:

1. **Manual seeds** from the registry, where a human has verified which page is
   the catalogue, the admissions page, the fee page. A seed says *where to
   look*. It is never itself evidence: the page is fetched and classified like
   any other, and a seed that turns out to be a landing page yields nothing.
2. **Sitemaps** — robots.txt `Sitemap:` directives, then the conventional
   locations, following sitemap indexes and gzipped sitemaps, confined to the
   institution's own registrable domain.
3. **Navigation**, only when the first two did not reach a programme page,
   starting from the catalogue rather than the global menu.

A fourth step then **reads** every programme candidate and keeps only the ones
the existing page classifier calls a programme. URL shape alone cannot tell a
degree from an open day.

## Reproducing

```bash
cd backend
./.venv/bin/python -m pytest tests/test_live_discovery.py -q     # offline, deterministic
./.venv/bin/python scripts/canary_discovery.py --check-seeds      # are the seeds still live?
./.venv/bin/python scripts/canary_discovery.py --out ../artifacts # the full live canary
```

The canary drives the real `ResearchRunner` against a throwaway SQLite database
in a temporary directory. It never touches `backend/data/`.

## The ten sites, 2026-08-28

| Institution | Country | Access | Programme page | Scholarship page | Pages ok/fail | Claims | Completeness | False positives |
|---|---|---|---|---|---|---|---|---|
| University of Groningen | Netherlands | REACHED | no | yes | 9/0 | 0 | 0% | 0 |
| Delft University of Technology | Netherlands | REACHED | no | yes | 14/0 | 5 | 33% | 0 |
| Aalto University | Finland | PARTIALLY_BLOCKED | no | yes | 26/1 | 0 | 0% | 0 |
| University of Vienna | Austria | REACHED | no | no | 5/4 | 0 | 0% | 0 |
| University of Warsaw | Poland | REACHED | no | yes | 8/1 | 0 | 0% | 0 |
| University of British Columbia | Canada | REACHED | no | yes | 21/4 | 0 | 0% | 0 |
| University of Toronto | Canada | REACHED | no | yes | 12/5 | 5 | 0% | 0 |
| The University of Hong Kong | Hong Kong | REACHED | no | yes | 12/5 | 0 | 0% | 0 |
| Nanyang Technological University | Singapore | REACHED | **yes** | yes | 40/3 | 5 | 17% | 0 |
| KAIST | South Korea | REACHED | no | no | 4/3 | 0 | 0% | 0 |

**Access.** Nine of ten were reachable. Aalto is recorded `PARTIALLY_BLOCKED`:
its robots.txt disallows `/en/node/*`, one candidate fell under that rule, and
the request was refused and logged. Nothing retried it under another agent,
ignored the directive, or substituted a cached copy. Toronto returns HTTP 403
for `www.utoronto.ca/robots.txt` and for every sitemap path; discovery recorded
that and worked from `future.utoronto.ca`, which serves normally.

**Before and after**, same ten institutions, discovery in isolation:

| | category pages | programme URLs |
|---|---|---|
| base `0fecc95` (`live-institution-registry`) | 12/30 | 0 |
| this branch (`live-sitemap-discovery`) | **26/30** | **3** |

The three programme URLs are all NTU's, and all three are correct:
`bachelor-of-computing-in-computer-science`,
`bachelor-of-science-in-mathematical-and-computer-sciences`, and
`bachelor-of-computing-in-computer-science-with-second-major-in-business`.
For a computer science applicant that is the right answer.

## What the canary found

Every defect below was invisible to the offline suite and is now covered by a
deterministic regression test.

| # | Defect | Where it showed |
|---|---|---|
| 1 | The 20,000-URL sitemap bound was applied *before* relevance filtering, so rug.nl filled the budget with news articles from one research institute and the walk stopped before any programme. Relevance is now decided per URL as it is read. | Groningen, Aalto, Warsaw |
| 2 | The navigation fallback ran only when *nothing at all* was found, so a single seeded admissions page suppressed it and the run ended with no programme. It now depends on the programme page specifically. | six of ten |
| 3 | `utm_source=x` survived canonicalisation — the tracking filter matched `key=value` pairs against a key-only pattern — so one page was discovered under two URLs. | all |
| 4 | Catalogue URL patterns required a bare `/programmes/` segment. Universities write `degree-programmes` and `degrees-programs`, so the walk stopped on the intermediate page. | Vienna, Warsaw, UBC |
| 5 | A programme page found only by the catalogue's **link text** was unreachable by any URL rule. Toronto's lead is `/data-computer-science` behind the text "Data & Computer Science". | Toronto |
| 6 | Events and newsletters sitting *inside* programme paths were returned as programme pages: `bachelor-open-day`, `onlinebachelorweek`, `student-for-a-day`, `campus-tour`, `webklassen`, and two Aalto student newsletters. | Groningen, Aalto |
| 7 | A scholarship page was returned as the applicant's programme page — "undergraduate" in the path outscored "scholarships" beside it. | NTU |
| 8 | A research group's "BSc and MSc projects" page was returned as a programme. A degree marker in a slug says nothing about whether the page is a degree. | Groningen |
| 9 | The subject bonus was too weak to separate structurally identical programme URLs, so a computer science applicant was answered with aerospace engineering, applied mathematics and applied physics. | Delft |
| 10 | Six of 31 manual seeds no longer resolved. A dead seed is worse than no seed: it spends the fetch budget and contributes nothing. All are replaced and verified; `--check-seeds` now reports 0 of 33 broken. | Aalto, Vienna, UBC, HKU, NTU |

Defects 6–9 were caught by reading the canary's own output, not by its
automated checks. That is the point of a manual audit: the automated column
said "programme page found: yes" for seven institutions, and only one of those
seven was actually a programme page.

### A finding about the canary itself

The first live run reported **14 false positives**, all of the form "claim
without excerpt". Every one was wrong: the canary looked for a payload key
named `excerpt` when the field is `original_text_excerpt`. The claims had their
excerpts all along. A checker that reports defects it cannot substantiate is
worse than no checker, so it is recorded here rather than quietly fixed.

## Zero-tolerance categories

The canary checks four things it will not accept, and reports **0** of each
across all ten institutions:

- a **full-ride** classification with no claim behind it, with no quoted
  excerpt, or with international eligibility not confirmed
- a **degree applicability** verdict with no stated reason
- a **deadline** taken from a page too general to carry it, or without an excerpt
- an **admission requirement** decided without a claim behind it

Plus a blanket check that every claim has a URL, a verbatim excerpt and a
timestamp. All 15 claims from the run pass.

Nothing here bypasses robots.txt, a login, a CAPTCHA, a rate limit or a
paywall, and no page is fetched off the institution's own registrable domain.

## Honest limitations

**Discovery reaches an individual programme page on one site in ten.** Category
pages are reliable (26/30); programme pages are not. Where the recall goes:

1. **The page classifier reads a real programme page as a catalogue when the
   page carries a programme-list sidebar.** Delft's `bsc-aerospace-engineering`
   and Toronto's `data-computer-science` are genuine programme pages, rejected
   because the classifier counts 18 and 1 programme links respectively and
   reports `program_catalog`. This is the single largest source of lost recall.
   The fix belongs in `app/adapters/page_classifier.py` — stripping the
   navigation sidebar the way `main_content()` already strips site chrome —
   **and that file is outside this branch's permitted scope, so it was not
   touched.** It is the highest-value next change.
2. **Three sites keep their programme list behind a catalogue chain the walk
   does not finish**: Vienna nests it three levels deep, Warsaw and UBC put it
   behind an intermediate page. Raising the walk budget from 5 pages to 8 was
   measured against all ten sites: it gained nothing and cost every site extra
   requests, so it was reverted rather than kept.
3. **KAIST publishes no English undergraduate programme catalogue** at any
   entry point tried. Its programme pages live on departmental subdomains
   (`cs.kaist.ac.kr`), which are on the same registrable domain but are not
   linked from any catalogue discovery reaches. Seeding a departmental page
   would tie the registry to one subject, so nothing was seeded.
4. **Results vary between runs.** Sites time out, WAFs return 403, and a page
   that resolved an hour ago 404s. Across eight canary runs the confirmed
   programme count ranged 1–3. The table above is one run, not a guarantee.
5. **Verification completeness is 0–33%.** Discovery finding a page is
   necessary, not sufficient; extraction and classification are what turn a
   page into claims, and they are outside this branch.
6. **The registry is ten institutions.** Nothing here establishes how discovery
   behaves on a site unlike these ten.
7. **`registrable_domain` uses a hand-built suffix list**, not the public
   suffix list. Adding `tldextract` would mean editing `requirements.txt`,
   which is outside scope. The list covers the academic suffixes in the
   registry; an institution under an uncovered multi-part suffix would be
   treated as a different domain and its own pages skipped.
8. **The canary rebinds `LiveDiscoveryAdapter` in `app.pipeline.runner`** to
   capture discovery traces, because the runner does not expose its adapter and
   `runner.py` is out of scope. Behaviour is inherited unchanged, but it is a
   test-harness seam, not a supported API.

## Pre-existing, untouched

`mypy app tests` reports 3 errors that predate this branch, in
`tests/conftest.py:36` and `tests/test_live_regressions.py:396,410`. Both files
are outside the permitted scope, so they were left alone. `mypy app` is clean.
`ruff check app tests` is clean; `scripts/` is outside the project's documented
lint scope and `scripts/crash_test.py` carries one pre-existing F841.
