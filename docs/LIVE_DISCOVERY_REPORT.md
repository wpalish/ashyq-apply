# Live discovery — what it finds, and what it does not

**Branch:** `claude/production-completion` (from `ea7948c`)
**Access date for every live figure:** 2026-08-29
**Applicant used:** a Kazakhstani school-leaver applying for a computer science
bachelor's for Fall 2027, needing nearly full funding. Synthetic; no real
applicant data is ever used against live sites.

## Headline

| | Before this cycle | After |
|---|---|---|
| Programme pages confirmed | **1/10** | **4/10** |
| Category pages (admissions / costs / scholarships) | 26/30 | **27/30** |
| Scholarship pages | 8/10 | **9/10** |
| Material claims | 15 | **27** |
| Zero-tolerance false positives | 0 | **0** |

Three independent runs, all on 2026-08-29, produced **4, 4 and 4**. Median 4,
worst 4. The acceptance bar this cycle aimed at was a median of 8 and a worst
of 7. **It is not met**, and that is the reason the release verdict is NOT
READY rather than "ready with limitations".

## Reproducing

```bash
cd backend
./.venv/bin/python -m pytest tests/test_live_discovery.py tests/test_page_classifier_real_pages.py -q
./.venv/bin/python scripts/canary_discovery.py --check-seeds
./.venv/bin/python scripts/canary_discovery.py --out ../artifacts
./.venv/bin/python scripts/canary_discovery.py \
  --registry app/adapters/discovery/holdout_registry.json --out ../artifacts/holdout
```

The canary drives the real `ResearchRunner` against a throwaway SQLite database
in a temporary directory. It never touches `backend/data/`. A run takes about
twenty minutes, most of it browser rendering.

## The ten canary sites, 2026-08-29

| Institution | Country | Access | Programme | Scholarship | pages ok/fail | Claims | Completeness | False positives |
|---|---|---|---|---|---|---|---|---|
| University of Groningen | Netherlands | REACHED | no | yes | 15/0 | 0 | 0% | 0 |
| Delft University of Technology | Netherlands | REACHED | **yes** | yes | 26/0 | 9 | 33% | 0 |
| Aalto University | Finland | PARTIALLY_BLOCKED | no | yes | 35/1 | 0 | 0% | 0 |
| University of Vienna | Austria | REACHED | **yes** | yes | 29/4 | 1 | 0% | 0 |
| University of Warsaw | Poland | REACHED | no | yes | 8/1 | 0 | 0% | 0 |
| University of British Columbia | Canada | REACHED | **yes** | yes | 21/4 | 1 | 0% | 0 |
| University of Toronto | Canada | REACHED | no | yes | 12/5 | 8 | 0% | 0 |
| The University of Hong Kong | Hong Kong | REACHED | no | yes | 12/5 | 0 | 0% | 0 |
| Nanyang Technological University | Singapore | REACHED | **yes** | yes | 40/3 | 8 | 33% | 0 |
| KAIST | South Korea | REACHED | no | no | 4/3 | 0 | 0% | 0 |

**Access.** Aalto is `PARTIALLY_BLOCKED`: its robots.txt disallows `/en/node/*`,
one candidate fell under that rule, and the request was refused and logged.
Nothing retried it under another agent, ignored the directive, or substituted a
cached copy. Toronto returns 403 for `www.utoronto.ca/robots.txt` and every
sitemap path; that is recorded, and discovery works from `future.utoronto.ca`,
which serves normally.

### Every programme page the run accepted

All twelve were opened by hand. Every one is a real programme page, and the
applicant's own subject is present at all four institutions.

| Institution | Programme the classifier named |
|---|---|
| TU Delft | Bachelor of Computer Science and Engineering |
| TU Delft | BSc Molecular Science and Technology |
| TU Delft | BSc Life Science and Technology |
| Vienna | Computer Science (bachelor's programme) |
| Vienna | Sport and Human Movement Science (Bachelor) |
| Vienna | Mathematical Foundations of Data Science |
| UBC | Computer Science (BSc), Vancouver |
| UBC | Computer Science (BA), Vancouver |
| UBC | Computer Science (BSc), Okanagan |
| NTU | Bachelor of Computing (Hons) in Computer Science |
| NTU | Bachelor of Science in Mathematical and Computer Sciences |
| NTU | Bachelor of Computing in Computer Science with a second major |

Precision on accepted programme pages is 12/12. The problem is recall, not
truthfulness.

## Why the other six fail, one at a time

Averaging these into "60% failure" would hide that two of them are not
discovery defects at all.

| Institution | Why | Is it a defect? |
|---|---|---|
| **Groningen** | The bachelor catalogue serves 103 links and not one programme; the list is built client-side, and the rendered copy does not add programmes either. | **Yes** — unreached. |
| **Aalto** | The only computing link on the study-options page is the *Department* of Computer Science, which is a department, not a programme. Its programme finder is a separate application. | **Yes** — unreached. |
| **Warsaw** | The English catalogue links onward to `irk.uw.edu.pl`, a separate admissions system on the same registrable domain. Rendering added one link and no programmes. | **Yes** — unreached. |
| **HKU** | Its programme index renders 35 links; the ones under `/programmes/` are collaborative schemes rather than the single-subject degrees. | **Yes** — unreached. |
| **Toronto** | `future.utoronto.ca/data-computer-science` is a *subject-area hub* spanning three campuses, which links out to programmes. The classifier calls it `unknown` and declines it. | **No** — the page genuinely is not a programme. An earlier version of this report called it "a genuine programme page"; that was wrong. |
| **KAIST** | No English undergraduate programme catalogue exists at any entry point tried. Programmes live on departmental sites such as `cs.kaist.ac.kr`, which are on the same registrable domain but are not linked from any catalogue discovery reaches. | **No** — nothing to find at the level we look. Seeding a departmental page would tie the registry to one subject. |

So four of ten are real recall defects and two are honest `NOT_FOUND`.

## What changed this cycle

Each was found by reading what a real page contains, and each is pinned by a
deterministic test over saved real HTML.

| # | Defect | Where it showed |
|---|---|---|
| 1 | A programme page that links to its own sub-pages counted as a catalogue. Delft's BSc Aerospace Engineering carries eighteen hrefs containing "/bachelors/" — "About the programme", "After your studies", fifteen student stories — every one under its own URL. Counting them made the programme page a catalogue of eighteen. | Delft, and any site with a section menu |
| 2 | Discovery stopped at the first programme it confirmed. Delft's sitemap yields aerospace, mathematics and physics, so the catalogue listing computer science was never walked. | Delft |
| 3 | Catalogue entries filled three slots in the order they appeared, so Vienna returned "African Studies" — first alphabetically. | Vienna |
| 4 | A catalogue whose programme list is built client-side was never re-read through the browser. UBC serves 127 links and no programmes; rendered, 308. | UBC, Warsaw, HKU |
| 5 | `_CATALOG` was matched against every heading joined into one string, so its `.*` bridged unrelated headings and invented a catalogue match. | Toronto |
| 6 | The catalogue branch reported "plural catalogue heading" whatever rule fired, including on pages headed "BSc Aerospace Engineering". | all |
| 7 | "Bachelors" passed as a programme name, so Delft's catalogue could name itself as a programme. | Delft |
| 8 | "MSc and BSc projects" — a research group's project list — passed as a programme on two degree words. | Groningen |
| 9 | "Recruitment" was read as staff hiring, so HKU's "Undergraduate Recruitment Scheme" was discarded as irrelevant. | HKU |
| 10 | The hand-built public-suffix table was necessarily incomplete; an institution under an unlisted suffix was treated as a foreign domain and its own pages skipped. Replaced with the Public Suffix List, bundled offline. | any |

## Zero-tolerance categories

The canary checks four things it will not accept, and reports **0** of each
across all ten institutions in all three runs:

- a **full-ride** classification with no claim behind it, without a quoted
  excerpt, or with international eligibility unconfirmed
- a **degree applicability** verdict with no stated reason
- a **deadline** taken from a page too general to carry it, or without an excerpt
- an **admission requirement** decided without a claim behind it

Plus a blanket check that every claim has a URL, a verbatim excerpt and a
timestamp. All 27 claims pass.

Nothing bypasses robots.txt, a login, a CAPTCHA, a rate limit or a paywall, and
no page off the institution's own registrable domain is fetched.

## Honest limitations

1. **Programme recall is 4/10, against a bar of 8/10.** Four of the six misses
   are real defects and are described above by name.
2. **Verification completeness is 0–33%.** Finding a page is necessary, not
   sufficient. Cost extraction in particular reads nothing from Delft's or
   Groningen's fee tables — see the note in `docs/CANARY_AUDIT.md`, which this
   cycle corrected: the figures are in the served HTML and were being
   *misread*, not hidden behind JavaScript.
3. **A run takes about twenty minutes**, most of it browser rendering. That is
   acceptable for a background job and would not be for an interactive one.
4. **Ten institutions is not the world.** Nothing here establishes behaviour on
   a site unlike these ten; that is what the holdout set exists to probe.
5. **The canary rebinds `LiveDiscoveryAdapter`** in `app.pipeline.runner` to
   capture discovery traces, because the runner does not expose its adapter.
   Behaviour is inherited unchanged, but it is a harness seam, not an API.
6. **Results depend on sites staying still.** Six of thirty-one registry seeds
   had already moved when this cycle started; `--check-seeds` now reports that
   in one command, and all thirty-three currently resolve.
