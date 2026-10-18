# Where the known core answers are lost after the programme page is found — base6 clean baseline (2026-10-18)

Analyst: claude-opus-5, read-only (no repo file changed, nothing committed). Inputs: the four repetitions
(off#1, off#2, on#1, on#2; both arms = today's defaults) of `scratchpad/runs/base6-{cohort,dev2,dev3}/x/`
(`<case>.json` predictions, `.log` fetches, `.raw.json` trace/claims/page diagnostics) and their `sc.json`;
gold `ground_truth.reviewed10.json`, `dev2.draft1.json`, `dev3.draft1.json`; scorer `scorecard.py` /
`metrics.py` / `mapping.py`; identity bindings `identity_bindings.{draft2,dev2-draft1,dev3-draft1}.json`.
No heldout case, label, capture or log was opened (nu, metu, sabanci, charles, masaryk, tum, tartu, polimi,
vilnius excluded by name in every script). dev4 has no known core labels and is not in the denominator.

Seventeen public gold/programme pages were fetched by hand into `scratchpad/core_gap_pages/` (and five
already cached under `scratchpad/{funnel_pages,evpages}/`) and run through the **production extractors
offline** (`scratchpad/core_gap_tools/offline_probe.py`, backend venv, no pipeline, no network); every
"(b) read, not extracted" verdict below is backed by such a probe or by a unit test of the gold sentence.

Tooling (all under `scratchpad/core_gap_tools/`, run with `python3 -I`): `funnel2.py` builds one row per
known core label × repetition (`out/labels.json`, `out/GROUPED.md` one block per label with all 4
repetitions, gold-page fetch status, diagnostics, trace mentions, our predictions and raw claims);
`counts.py` holds the hand-reviewed cause per label and writes `out/COUNTS.md` / `out/NOTES.md`.

## 0. Headline

The clean baseline answers **7-9/28 (cohort), 1-2/21 (dev2), 3/28 (dev3)** known core questions. Of the
86 known core labels, 57 sit on the 16 cases whose programme page is a hit in ≥3 of 4 repetitions
(groningen, delft, warsaw, hku, ntu; ethz, uppsala, tcd, uba; imperial, unsw, um, auckland, ucph, puc,
chula). On those 57 labels (48 questions):

| where the label is lost | labels | questions it holds |
|---|---|---|
| hit | 12 | 11 answered |
| **(a) gold page never read** | 22 | 19 |
| **(b) read, nothing extracted** (extractor/reader gap; incl. 3 free-text gpa labels) | 14 | 10 |
| **(c) extracted-or-readable but withheld** (classifier page type, index budget) | 6 | 6 |
| **(d) claimed, scored miss** (NTU Nanyang: right award, right values, unbound URL alias) | 3 | 2 |

(11 + 19 + 10 + 6 + 2 = 48 questions; a question is held by the cause of its unanswered labels, hku's
scholarship question once.) So on found pages the binding gap is **(a) 22 : (b) 14 : (c) 6 : (d) 3** at
label level — but (a) is dominated by scholarships on pages that no static link or query reaches (8), by
another host / local language (5) and by a gold-identity dispute (chula, 5). The labels that are
*reachable today and lost in our own code* are (b)+(c)+(d) = **23 labels / 18 questions**, of which 3 gpa
questions need a corpus change, not code; add the 3 (a) labels that are one link away (hku cds ×2,
auckland deadline). That is the addressable set: 15 code-addressable questions + 3 one-link-away, which
would lift group F from 11/48 to roughly 26–29/48 if every item below landed.

Three measurement facts hide real answers today: NTU's Nanyang Global Scholarship is read correctly in all
four repetitions (`scholarship_exists`, `citizenship_restriction = all`, `international_eligible = true`)
but filed under `unmapped.*` because the page's live URL is `/admissions/ug/...` and the bindings list
`/admissions/undergraduate/...` (3 labels, 2 questions); `sat_min_total` maps to `sat.minimum` while NTU's
gold key is `english_evidence.sat.minimum`; and all four gpa labels (ntu, um, ucph, msu) are free-text
paraphrases that exact JSON comparison can never match.

## 1. Count tables (cause × question)

Cause codes: **A1** never read, not linked in the static HTML of any page we read and not returned by our
queries · **A2** linked from a page we read, link not followed (navigation-only / not a QR-1 question link) ·
**A3** returned by a query, never read · **A4** refused by budget (TB-1/RL-1) · **A5** access (robots, 403,
timeouts) · **A6** other host / other registrable domain / local language / PDF · **A7** gold identity (labels
of another programme than the one confirmed) · **B1** prose regex (IELTS/SAT) · **B2** table structure ·
**B3** TOEFL reader · **B4** deadline reader · **B5** cost readers · **B6** award described on the index page
itself · **B7** free-text gold value · **C1** classifier page type · **C2** scholarship index budget · **D1**
identity-binding URL alias · **D2** key mapping · **D3** wrong value. Each label gets the cause of the
majority of its 4 repetitions; repetition-level variations are in §2.

### Group F — programme page found (16 cases, 57 labels)

| cause | english | gpa | deadline | cost | scholarship | schol._international | labels |
|---|---|---|---|---|---|---|---|
| HIT | 6 | 0 | 4 | 2 | 0 | 0 | 12 |
| A1 not linked, not returned | 0 | 0 | 0 | 0 | 4 | 4 | 8 |
| A2 linked, not followed | 0 | 0 | 1 | 0 | 1 | 1 | 3 |
| A5 access | 0 | 0 | 0 | 0 | 1 | 0 | 1 |
| A6 other host / language / PDF | 0 | 0 | 1 | 0 | 2 | 2 | 5 |
| A7 gold identity (chula ISE) | 3 | 0 | 0 | 0 | 1 | 1 | 5 |
| B1 prose regex | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| B2 table structure | 4 | 0 | 0 | 0 | 0 | 0 | 4 |
| B3 TOEFL reader | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| B4 deadline reader | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| B5 cost readers | 0 | 0 | 0 | 2 | 0 | 0 | 2 |
| B7 free-text gold (gpa) | 0 | 3 | 0 | 0 | 0 | 0 | 3 |
| C1 classifier page type | 0 | 0 | 0 | 0 | 1 | 1 | 2 |
| C2 index budget | 0 | 0 | 0 | 0 | 2 | 2 | 4 |
| D1 binding alias | 0 | 0 | 0 | 0 | 1 | 2 | 3 |
| **total** | 17 | 3 | 7 | 4 | 13 | 13 | 57 |

Group F question level: **11 of 48** known core questions answered — english 5/10, deadline 4/7, cost 2/4,
gpa 0/3, scholarship 0/12, scholarship_international 0/12 (per-question rows in `out/COUNTS.md`).

### Group R — site readable, programme page `related` (ubc: BA page confirmed) or unknown in gold (tec, kaznu, uct, utokyo, ntutw, msu, usp) — 19 labels

| cause | english | gpa | deadline | cost | scholarship | schol._international | labels |
|---|---|---|---|---|---|---|---|
| HIT (ubc ielts 3/4, uct ielts 2/4) | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| A3 returned, never read (ntutw) | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| A4 TB-1 refused (ubc deadline, 2/4; hit 1/4) | 0 | 0 | 1 | 0 | 0 | 0 | 1 |
| A6 local language / PDF (tec, kaznu, utokyo, msu, usp) | 1 | 1 | 1 | 0 | 5 | 5 | 13 |
| B6 award on the index page (ubc IMES) | 0 | 0 | 0 | 0 | 1 | 1 | 2 |
| **total** | 3 | 1 | 3 | 0 | 6 | 6 | 19 |

### Group X — programme page not found (aalto, toronto, kaist, tsinghua) — 10 labels: A5 access 7, A6 other domain 3. Nothing in the evidence stage can act on these.

## 2. Every known core label on a found page (and the readable group R), with where it is lost

Format: case · key (question) · cause · what the captures and the offline probe show. "4/4" = all four
repetitions agree. Gold sentences are quoted from the signed corpus.

### cohort

- **groningen** `ielts.overall`, `deadline`, `tuition` — **hit 4/4** (language page reached as a QR-1 english link via the `with-non-dutch-diploma` variant; deadline and non-EU/EEA 2027/28 tuition from the programme page).
- **groningen** `scholarships.nl.exists`, `.applicability.international` — **A1 4/4**. Funding stage read `rug.nl/education/scholarships` ("read as a funding index; 0 award links"): the offline probe confirms the static HTML carries no link to `nl-scholarship` (the list is rendered client-side; the only in-content link is `/scholarships/!sso`). The award query (`site:rug.nl scholarship international …`) returned prospect-burma / eric-bleumink / a law-faculty grants page. The sitemap that lists the page was `too_large` (5 MB cap). Gold quote: "Selection criteria | Purposes: Master (MSc/MA/LL.M.), Bachelor (BSc/BA/LL.B) | Programmes: All | Countries of Origin: All".
- **delft** `ielts.overall`, `deadline`, `tuition` — **hit 4/4** (deadline from the "Selection procedure" page reached as a QR-1 deadline link; tuition from the seed costs page, 2027/2028 institutional rate).
- **delft** `english_evidence.toefl_ibt.minimum = 90` — **B3 4/4**. The page is read (as `admission-requirements`, the gold's `1-admission-requirements` twin) and yields IELTS 6.5. `_toefl_total` returns on the first "TOEFL" mention: "TOEFL test reports obtained from January **21**, 2026" → 21 → outside 40–120 → dropped; the caller never tries the next mention, "TOEFL iBT with an overall band score of at least 90". Offline: `_toefl_total` = 21 on the live page.
- **warsaw** `scholarships.rektora.exists`, `.applicability.international` — **A6 4/4**: gold on `bpm.uw.edu.pl` and a Polish PDF on `monitor.uw.edu.pl`; the funding stage read `welcome.uw.edu.pl` indexes (29 s, Belarus award claimed). Not reachable by any link or query shape we send.
- **hku** `scholarships.entrance.exists` — **A5 4/4**: `admissions.hku.hk` robots.txt unreachable → every lead refused.
- **hku** `scholarships.computing_data_science_entrance.exists`, `.applicability.international` — **A2 4/4**. The confirmed cds programme page links `/prospective-students/scholarships/` four times — all in the navigation; `_award_links` runs on `main_content(soup)` and reports "0 award links", so the gold page is never queued. Offline the gold page classifies `scholarship_award` with signals amount/coverage/duration, but its *subject* is the page title "Scholarships - HKU School of Computing and Data Science (HKUCDS)" while the binding's subject is "School of Computing and Data Science Entrance Scholarship" → even when read it would file as `unmapped.scholarship_exists` (D1-type). Two fixes needed (nav link + award name from the h3 "1. School of Computing and Data Science Entrance Scholarship").
- **ntu** `deadline` — **hit 4/4** (catch-all window row).
- **ntu** `scholarships.nanyang_global.exists`, `.applicability.nationality = "all"`, `.applicability.international = true` — **D1 4/4**. The award page is read in every repetition at `https://www.ntu.edu.sg/admissions/ug/scholarships/scholarship-opportunities/detail/nanyang-scholarship` (the path the programme page's "Scholarships" index links; `curl -I` shows `/admissions/undergraduate/scholarships/...` 301 → `/admissions/undergraduate/scholarships-and-awards/...`, and `/admissions/ug/...` serves 200 directly). Claims: `scholarship_exists = "Nanyang Global Scholarship"`, `scholarship_citizenship_restriction = "all"`, `scholarship_international_eligible = true`, all `VERIFIED_CURRENT`. `IdentityMap.resolve` compares `canonical_url(binding.source_url) == canonical_url(source_url)`; the bindings hold the `/undergraduate/scholarships/` and `/undergraduate/scholarships-and-awards/` spellings only → `unmapped.scholarship_exists`, `unmapped.scholarship_citizenship_restriction`, `unmapped.scholarship_international_eligible` → 3 misses, 2 questions. Pure measurement loss.
- **ntu** `english_evidence.sat.minimum = 1250` — **B1 4/4** (page read; IELTS 6.5 and TOEFL 90 are claimed from it). Gold sentence "SAT Total score – 1250": `_SAT_MIN` needs `SAT … (minimum|at least|score of) … \d{3,4}` or "\d{3,4} (for|on|in) … SAT"; "Total score –" has neither. Unit test on the sentence: no SAT claim. If extracted, `sat_min_total → sat.minimum` would still miss the gold key `english_evidence.sat.minimum` (**D2**).
- **ntu** `gpa = "A in all subjects (NIS Grade 12 Certificate exam)"` — **B7 4/4**. The gold page (`…/other-international-qualifications`) is read in every repetition and yields IELTS/TOEFL claims; the gold value is a reviewer paraphrase of the table row "Kazakhstan NIS Grade 12 Certificate | Yes | Score of A in all subjects taken at NIS Grade 12 Certificate exam." No reader produces that string; exact comparison cannot match it.

### dev2

- **ethz** `scholarships.eth.exists`, `.applicability.international` — **A1 4/4**. The funding index `financial/scholarships.html` is read ("0 award links"); offline its static HTML (1 563 chars) links only "Financial" and two login URLs — `cost-of-living*.html` is not in the markup. The award query returned the Excellence Scholarship (master's) page, claimed as an award (unlabelled). Gold quote: "International Bachelor students may apply for financial aid after passing the first year exams (Basisprüfung)."
- **uppsala** `ielts.overall` — **hit 4/4** (entry-requirements page reached for the english question).
- **uppsala** `english_evidence.toefl_ibt.minimum = 90` — **B3 4/4**. Same page, same sentence as the gold: "TOEFL iBT: score of 20 (scale 0-30) in written test, total score of 90" → `_toefl_total` returns 20 (the section score), out of range, dropped. Unit test: toefl = 20.
- **uppsala** `deadline = 2027-04-15` — **B4 3/4, D3 1/4**. The programme page is read and accepted in every repetition (2 claims: `program_exists`, `intake_term fall 2026`). Its text holds two accordions, "Autumn 2026 … Application deadline 15 April 2026" and "Autumn 2027 … Application deadline 15 April 2027". `_deadline_v2` first collects `_application_windows(_DATE_RANGE_V2)`: the two *study periods* ("31 August 2026 – 3 June 2029", "30 August 2027 – 9 June 2030") count as windows with different ends → `return None` (the several-windows guard; `DEADLINE_WINDOW_SCOPE`/EX-2 is off, so the requested intake's section is never isolated). Unit test on the Autumn 2027 section alone: `admission_deadline = 2027-04-15` **and** `tuition = SEK 450,000` (an unlabelled-but-right cost answer that is lost the same way). In on#2 the deadline question's extra page `/bachelors-studies/application` yielded 2027-01-15 ("The next application will open 16 October 2026 and close 15 January 2027" — the international round) → `wrong_value`; this is the owner's open gold dispute.
- **uppsala** `scholarships.anders_wall_studies_at.exists`, `.applicability.international` — **A1 4/4**. The programme page's QR-1 links are fees only (`/en/study/fees`); no scholarships page was selected by seeds/sitemap; the award query returned a faculty "Environmental Scholarships from Sveriges Ingenjörer" degree-project page (claimed as an award with `degree: master`, unlabelled). Offline, the gold index `bachelors-studies/scholarships` classifies `scholarship_index` and `_award_links` lists the gold award page first — it is one query away ("Uppsala University bachelor's scholarships").
- **tcd** `ielts.overall = 6.5`, `english_evidence.toefl_ibt.minimum = 90`, `english_evidence.duolingo.minimum = 120` — **B2 4/4**. The gold page is fetched in every repetition as a QR-1 english link and read for the question ("english page: 1 claims read" — only a postgraduate waiver sentence). Offline IR dump: the table rows are the bands — `row_headers=['Band B (Standard entry)']`, `column_headers=[]`, cell text "6.5 overall 6.0 in each band" — the header row with the test names is not captured, so `extract_table_requirements` (which requires IELTS in the *row* headers) sees no IELTS row; the prose `_IELTS_OVERALL` needs the band within one sentence of "IELTS", which only appears in the header; `_toefl_total` returns 202 from "TOEFL iBT (Before January 2026)"; `_DUOLINGO` needs the number within 90 chars after "Duolingo". Gold quote: "Band B (Standard entry) UG & PG Standard requirements 6.5 overall 6.0 in each band 120 overall 100 in each subscore 90 overall 21 in each section …".
- **tcd** `tuition = EUR 30,450` — **B5 4/4**. The gold fees page is fetched (QR-1 fees link "Fees" → `courses/undergraduate/fees/`) and read: "page was read but no cost figures could be extracted". The page is a per-course table; the gold row "2027/28 School of Computer Science & Statistics Computer Science (Year 5 is postgraduate) UICS-ICSC-2F UF_000031 €4,982.00 €2,350.00 €7,332.00 €30,450.00" has no tuition keyword or population word within 120 chars of the money → `extract_costs` 0 (unit test). Needs a row-by-programme reader with the "Non-EU Student Total Fee" column header.
- **tcd** `scholarships.e3_balanced_solutions_better.exists`, `.applicability.international` — **C2 4/4** (with **B6** underneath). The gold page `e3/education/scholarships` is fetched in every repetition at the end of the funding walk, classified `scholarship_index` and refused "index page beyond the index budget" (`_MAX_INDEX_PAGES = 3` already spent on `study/international/scholarships`, a business-school prizes page and `international/scholarships/undergraduate`). Even inside the budget it would yield nothing: the award's text ("Undergraduate E3 Balanced Solutions for a Better World Scholarship … Who can apply: Applicants who have non-EU status and will pay tuition fees at the non-EU rate …") is **on the page itself**, and `_award_links` returns four links to the central international-scholarship pages, not to the E3 awards. The programme page has no scholarships link; the e3 page comes from the award query.
- **uba** ×2 — **A6**: `extension.uba.ar`, Spanish news post; never seen.
- **tsinghua** ×3 — **A6** (other registrable domain; group X).
- **tec** `toefl` — **A6**: the Spanish programme page is fetched by discovery and refused "reads as unknown, not a programme page"; gold programme unknown, so verify never runs on it. `beca` ×2 — **A6** (Spanish page, PDF).
- **kaznu** ×2 — **A6** (Russian, `welcome.kaznu.kz`).
- **uct** `ielts.overall` — **hit 2/4**; the other two repetitions lose the host to timeouts (the gold page itself "timeout — host stopped responding earlier in this run").

### dev3

- **imperial** `deadline` — **hit 4/4** (programme page, "Application deadlines – Wednesday 13 January 2027").
- **imperial** `ielts.overall = 6.5` — **B1 4/4**. The gold english page is fetched as a QR-1 english link ("English language requirements") in every repetition and read for the question: 3 claims (`duolingo_min 115`, accepted types, waiver). IR dump: no table cell mentions IELTS (the requirement grid is not a `<table>`). Prose: "IELTS – Academic (Test-Centre/UKVI SELT/Online) Standard Higher 6.5 overall (minimum 6.0 in all elements) 7.0 overall …" — alternative 1 of `_IELTS_OVERALL` needs the keyword *before* the band and cannot cross the "." of "6.5"; alternative 3 allows ≤ 20 non-digit chars between IELTS and the band (here ~50); the "score required" and "IELTS (Academic) 5.5 TOEFL" alternatives do not apply. Unit test on the sentence: no IELTS claim. `_toefl_total` = 21 ("TOEFL iBT after 21 January 2026").
- **imperial** `tuition = GBP 47,800` — **B5 4/4**. The programme page is read in every repetition ("4 claims": exists, SAT 1480, deadline, interview). Its text: "Home fee 2027 entry £10,050 per year … Overseas fee 2027 entry £47,800 per year". `extract_costs`: the tuition pattern wants "tuition|tuition fee|programme fee|course fee" within 120 chars before the money, and `_population_amounts` knows only EU/EEA vocabulary — "Overseas"/"Home" (the UK fee-status words) are not population names → 0 claims (unit test). The three fees-topic pages read "no cost figures".
- **imperial** `scholarships.imperial_inspires.exists`, `.applicability.international` — **C1 3/4** (A5 timeout 1/4). The gold award page (`…/scholarships-search/imperial-inspires-scholarships-undergraduate-20272028.php`, linked from the programme page) is fetched at t≈80 s and **classified `scholarship_index`** — `classify_page`'s funding branch returns INDEX whenever `award_links >= 2` before it tests the named-award rule; the page links its own hub (`/imperial-inspires-scholarships/`) and `/fees-and-funding/` → "4 award links" → then refused "beyond the index budget". Offline: `classify_page` → `scholarship_index`, `_lists_awards_below` → False (no child pages), title "Imperial Inspires Scholarships (Undergraduate)". Side note: on this page `_deadline_v2` would answer 2026-10-15 — a reason to keep scholarship pages out of the deadline reader.
- **unsw** `ielts.overall = 6.5` — **B2 4/4**. The gold page is fetched as a QR-1 english link and read for the question (2 claims, none a minimum). IR dump: `row_headers=['Engineering']`, `column_headers=['Undergraduate']`, cell "6.5 overall (min 6.0 in each subtest)"; the test name is the heading above the table, not a header cell → the structural reader never attributes the row to IELTS; the cell phrasing "(min 6.0 in each subtest)" fits neither `_BAND` nor `_BAND_WITH_FLOOR` ("no part/band/section less than"). Gold quote: "Engineering 6.5 overall (min 6.0 in each subtest) …".
- **unsw** `scholarships.scientia_coursework.exists`, `.applicability.international` — **A1 4/4**: the gold page is on `www.scholarships.unsw.edu.au` (id/1988) and never returned; the award query returned `/study/your-future/international-scholarships`, a generic marketing page the pipeline **claimed as an award** ("UNSW scholarships for international students", `scholarship_international_eligible = true`, scope `degree: master`) — unlabelled, so not counted as wrong, but it is a precision defect to keep in mind for Change 2. The later award reads (`/international-student-award`, `/india-scholarships`) were refused by TB-1 with < 1 s left.
- **um** `ielts.overall = 5.5`, `english_evidence.toefl_ibt.minimum = 46` — **hit 4/4** (from the sibling programme page, same text; sibling-evidence rule).
- **um** `gpa = "65% minimum average (SHSC)"` — **B7 4/4** (page read; free text).
- **auckland** `ielts.overall = 6.0` — **hit 4/4**.
- **auckland** `deadline = 2026-12-08` — **A2 4/4** (+ **B4** behind it). The confirmed pages are the major's pages (`bsc-compsci-from-2019.html`, `computer-science/undergraduate.html`) and the plan page; the gold is the **parent degree page** `bachelor-of-science-bsc.html`, linked from the confirmed page as "Bachelor of Science (BSc)" — not a QR-1 question link (QR-1's deadline links went to `important-dates.html` → `unknown`, and an accommodation "how to apply"). It was returned at rank 1 by `natural_language` in one repetition and not read (a page was already confirmed). Offline on the gold page: `_deadline_v2` → None — "Application closing dates Summer School 2027 1 December 2026 Semester One 2027 8 December 2026 Semester Two 2027 4 July 2027" has no `deadline|closes?|apply by|due` keyword ("closing" ≠ "closes") and three intakes.
- **auckland** `scholarships.pong.exists`, `.applicability.international` — **C2 4/4**: 17 scholarship-index reads per repetition, 13–15 refused "beyond the index budget", among them `find-a-scholarship.html`, the parent of the gold award (`find-a-scholarship/pong-tams-ko-scholarship-1037-all.html`). The index budget is spent on `scholarships-and-awards.html`, `scholarship-types.html`, `scholarship-eligibility.html`.
- **ucph** `gpa` — **B7 4/4** (free text; the quota-2 page is linked "Quota 1 and quota 2" from the programme page and never read — A2 behind it).
- **puc** `deadline` — **A6 4/4**: Spanish calendar on `admision.uc.cl`; the department page on `dcc.ing.uc.cl` is what we confirm.
- **chula** `ielts.overall`, `toefl`, `duolingo`, `scholarships.ise_foreign.*` — **A7 4/4**: all five labels are for the ISE/ICE programme on `ise.eng.chula.ac.th`; we confirm the `math.sc.chula.ac.th` BSc page (also listed in the gold's `programme_urls`). The ISE page was returned by `natural_language` at rank 6–9 in every repetition and never read. A gold identity question, not an extractor one.
- **msu**, **usp**, **utokyo** — **A6** (Russian / Portuguese / Japanese pages and PDFs; programme unknown).
- **ntutw** `deadline` — **A3 2/4, C1 1/4, never 1/4**: no programme page (gold unknown), so no deadline routing; the gold admissions page is returned at rank 2 (`natural_language`) and once read in discovery recovery, "classified as unknown; no requirement can be read" — the deadline window "2027 September Entry (1st Round) Open Application Period: September 29 (11AM) – November 5, 2026 (4PM)" would also need a reader that tolerates "(11AM)" inside the range.
- **ubc** (group R) `ielts.overall` **hit 3/4**; `deadline` **A4 2/4** (the dates-deadlines link is a QR-1 deadline link but queued after two english pages and the fees page, and TB-1 refused it with 27.5 s / 23.8 s left and 20 s to reserve; the one repetition that read it answered 2027-01-15 correctly), `missed` 1/4 on host timeout; `scholarships.major_entrance.*` **B6 3/4**: the gold index page is read ("3 award links"), the IMES award is described on the index itself ("For the 2026/2027 academic year, IMES awards will be valued at $10,000 – $25,000/year", "Be an international student who will be studying at UBC on a Canadian study permit"), and the only sub-page followed (`/international-scholars`) is "not an award page".

## 3. Changes ranked by known core answers gained (group F unless noted; conservative / optimistic)

Gains are counted at question level against the four base6 repetitions; "conservative" counts only
labels whose gold page is already read today, "optimistic" adds the one-link-away pages.

### 1. `AWARD_PAGE_EVIDENCE` (flag `--award-page-evidence`, AP-1): read awards from the page in hand — **+6 / +10 questions**

Design (`web_scholarships.find`, `page_classifier.classify_page`):
1. **Classifier order**: in the funding branch, test the named-award rule *before* the link-count rule when the identity (h1/title) names an award and `_lists_awards_below()` is False — Imperial's `imperial-inspires-scholarships-undergraduate-20272028.php` (title "Imperial Inspires Scholarships (Undergraduate)", 4 sibling links) then reads as `scholarship_award`. Pages that link ≥3 children below their own path stay indexes.
2. **Award sections on an index**: when an index (or the page the funding route starts from) contains headings that name an award (`_award_name` on h2/h3/h4 text; UBC "International Major Entrance Scholarship", TCD "Undergraduate E3 Balanced Solutions for a Better World Scholarship", HKU "1. School of Computing and Data Science Entrance Scholarship"), run `_parse_award` on each heading's section with `subject = heading text` — `scholarship_exists` and `applicability.international` from that section's eligibility sentences only (`_eligibility_sentences`, `_route_international`); nothing else from an index.
3. **Depth-0 index budget**: an index whose own sections yielded awards does not count against `_MAX_INDEX_PAGES`.

Cases fixed: ubc major_entrance ×2 (group R; page read 3/4), tcd e3 ×2 (page read 4/4), imperial inspires ×2 (page read 3/4) → **+6 questions**; hku cds ×2 once AP-3 below follows the nav link (**+2**); auckland pong +0–2 only with a deeper index chain.
Precision risk: award sections on an index are where past wrong claims came from (UBC award-conditional deadline, "students from Belarus"). Guards: the subject must be a proper award name containing scholarship|award|bursary|grant; `applicability.international` only from sentences under that heading that name international/overseas/non-EU students or a nationality list (`_DOMESTIC_ONLY` still drops Canadian-only pages); no deadline, amount or coverage from an index section; keep `SCHOLARSHIP_LEVEL_SCOPE` (SL-1). Measure: paired run on cohort/dev2/dev3; required 0 new wrong claims, `wrong_scope_claim_rate ≤ 0.03`, stable gains `ubc:scholarships.major_entrance.exists`, `tcd:scholarships.e3_*.exists`, `imperial:scholarships.imperial_inspires.exists`; watch the unlabelled list for generic pages claimed as awards (the UNSW "UNSW scholarships for international students" claim is the shape to refuse: no capitalised award name).

### 2. `ENGLISH_TABLE_V2` (flag `--english-readers-v2`, EN-2): the three table/prose shapes the readers miss — **+3 questions, +5 labels** (imperial, tcd ×3, unsw)

Design (`structured_extraction.extract_table_requirements`, `extraction._IELTS_OVERALL`):
1. **Test from column headers or the table's heading**: when no row header names a test, attribute a column by its header (TCD: header row has `<td>`s — build headers from the first row when the IR has none) and, failing that, by the nearest preceding heading in `section_path` ("IELTS" h3 above UNSW's table). A column/table so attributed is read like an IELTS row today.
2. **Cell phrasing**: extend `_BAND_WITH_FLOOR` to "N overall (min(imum)? M in each (band|subtest|section|element|component))" and "N overall M in each band" (TCD/UNSW/Imperial cells); keep the `part ≤ overall` check.
3. **Prose**: one more `_IELTS_OVERALL` alternative, `IELTS[^\n]{0,80}?(\d(?:\.\d)?)\s*overall\b`, that may cross decimal points and takes the *first* band followed by "overall" (Imperial: 6.5, not the Higher column's 7.0).
4. **Row selection** when several rows yield different overall bands: TCD "Band B (Standard entry)" vs "Band C (Higher entry)", UNSW faculties — keep the row whose header names the programme's faculty (FS-1's `_faculty_section` logic) or "standard"; otherwise abstain (no claim), never the first row.

Cases fixed: imperial ielts (B1), tcd ielts/toefl/duolingo (B2; TOEFL/Duolingo come from the same attributed columns), unsw ielts (B2) → **+3 questions** (imperial, tcd, unsw english), +5 labels. Precision risk: UNSW's rows differ by faculty (Medicine 7.0) and TCD's by band; without rule 4 the first row would be claimed — so rule 4 is a precondition, and the paired run must show no new `ielts.overall` claim whose value differs across rows of the same table. Prerequisite for TCD: the IR header-row fix is in `document_ir`, test on the saved page.

### 3. `IDENTITY_URL_ALIASES` (scorer-side; owner approval for bindings) — **+2 questions, +3 labels** (ntu), 0 pipeline risk

Design (`evaluation/research/identities.py`, bindings): either add the live `/admissions/ug/scholarships/scholarship-opportunities/detail/nanyang-scholarship` URL as a second binding for `scholarships.nanyang_global`, or let `IdentityMap.resolve` accept a recorded redirect/alias set (the capture already records `programme_url_aliases` for programme pages; awards need the same). Also map `sat_min_total` to the corpus's `english_evidence.sat.minimum` where the corpus uses it (NTU; 0 questions, 1 label once B1 is fixed). Precision risk: none (measurement). Note for the owner: the bindings are signed corpus data; this is a correction of a URL spelling, not a new identity.

### 4. `FEE_POPULATION_V2` (flag `--fee-readers-v2`, FE-2): UK fee-status rows and per-programme fee tables — **+2 questions** (imperial, tcd)

Design (`extraction.extract_costs`, `_population_amounts`, `structured_costs`):
1. Population aliases: "Overseas (fee|students)" → `international`, "Home (fee|students)" → `domestic`, "International fee" → international; a row "Overseas fee 2027 entry £47,800 per year" yields `tuition {47800, GBP}` with `population international`, `academic_year 2027/28` (TY-1 picks "2027 entry" against the request).
2. Per-programme fee table: when a table's rows name programmes and a column header names the population ("Non-EU Student Total Fee"), read the row whose first cells match the programme (`titles_name_same_programme`) and the requested year (TCD "2027/28 … Computer Science … €30,450.00"); abstain when no row matches or two match.

Cases fixed: imperial tuition (programme page already read 4/4), tcd tuition (fees page already read 4/4) → **+2**. Unlabelled gains: Uppsala "Total tuition fee: SEK 450,000" once the intake section is isolated (change 5). Precision risk: the Home row must never be filed as the international fee (population from the row label, never from the request); per-course tables with a "Year 1" vs "Years 2+" split — take the column whose header says Year 1 / first year, else abstain.

### 5. `DEADLINE_INTAKE_SECTION` (flag `--deadline-intake-section`, DL-5; re-measure EX-2 on top of CL-1) — **+1 / +3 questions**

Design (`extraction._deadline_v2`, `_deadline_scope`, `web_requirements` ordering):
1. Before the several-windows guard, cut the page to the requested intake's section (`_intake_section` for "Autumn 2027" / "Semester One 2027" / "2027 entry") and run the readers on that section; study-period ranges (`_study_period_range`) never count as application windows. Uppsala's Autumn 2027 accordion then gives 2027-04-15 (unit-tested).
2. Keyword: add "closing date(s)" to `_DEADLINE_V2`'s label set and read "Semester One 2027 8 December 2026" as the fall-2027 row of a table of intakes (Auckland).
3. Ordering: read one page per question before a second page of any question (today UBC reads two english pages and the fees page before the dates-deadlines link, and TB-1 refuses the deadline read in 2 of 4 repetitions).

Cases fixed: uppsala deadline (**+1**; note the owner's dispute — the national-round date is what the gold says), ubc deadline (**+1**, 2 lost repetitions), auckland deadline (**+1** only with change 6's parent-page link). Precision risk: Uppsala's `/bachelors-studies/application` page states the international round (15 January) — with the section rule the programme page answers first and the topic page must not overwrite it (keep the first programme-page deadline when the two disagree, and record the conflict).

### 6. `PROGRAMME_PAGE_LINKS_V2` (flag `--programme-links-v2`, QR-2): two link classes QR-1 ignores — **+1 / +3 questions**

Design (`web_requirements._question_links`, `web_scholarships._award_links`):
1. **Parent degree page**: a link on the confirmed programme page whose text is the degree title that the programme page's own subject names ("Bachelor of Science (BSc)" for "Bachelor of Science major in Computer Science") is read as a deadline/fees source with the programme's scope (Auckland: closing dates live on the BSc page; UCPH's "Quota 1 and quota 2" is the same shape for gpa).
2. **Navigation scholarship links**: `_award_links` on the programme/admissions page also scans the navigation (not only `main_content`) for links whose path ends in `/scholarships/` on the same host (HKU cds). At most one such link; it is read as the funding index at depth 0.

Cases fixed: auckland deadline (+1 with DL-5), hku cds ×2 (+2 with AP-1's heading-named awards) → **+1 conservative, +3 optimistic**. Precision risk: parent degree pages carry degree-wide fees/deadlines — file them with `programme = None` scope (the scorer's programme-identity rule accepts a page that names no programme); never read english from them when the programme page named a stricter band.

### 7. `TOEFL_READER_V2` (flag `--toefl-reader-v2`, TF-2) — **+0 questions, +2 labels** (delft, uppsala; tcd's TOEFL comes with EN-2)

`_toefl_total` continues to the next "TOEFL" mention when the number is out of range or is followed by a month name / "20\d\d"; prefers "total (score)? of N" / "overall (band|score)? of N" inside the mention over the first number; skips a number followed by "(scale 0-30)". Fixes delft 90, uppsala 90 (and Imperial's unlabelled 92). No question gain (those english questions are answered by IELTS), but it removes two stable misses and the silent "first number wins" defect that also produced TCD's 202 and Imperial's 21.

### 8. One scholarship index query (flag `--scholarship-index-query`, SQ-1) — **+2 / +4 questions**, costs 1 query

`{institution} scholarships for international bachelor's students` sent when the funding route found no award and `candidate.search_queries_used < 6`; the top same-domain result is read as the depth-0 index (Uppsala's `bachelors-studies/scholarships` then lists the gold award; Groningen's `nl-scholarship` page is the one result such a query must return — the index is client-rendered). Risk: budget (Uppsala and TCD already send 5–6 queries; Groningen 3) and another generic page read as an award unless AP-1's name rule is in.

Not ranked: the 23 group-F/R labels behind other hosts, other registrable domains, local language and PDFs (A6: warsaw, uba, puc, tec, kaznu, msu, usp, utokyo, tsinghua), access (A5), and the chula identity question (A7) — nothing in the evidence stage reaches them; and the four gpa labels (B7) until the corpus represents them structurally.

## 4. Gold labels that look wrong, outdated or unmatchable (not changed)

- **uppsala `deadline = 2027-04-15`** — the university's own application page states the international round "open 16 October 2026 and close 15 January 2027"; the programme page states the national round 15 April 2027. Open owner dispute; both are "official"; the label's scope says nothing about the round.
- **gpa labels** — `ntu` "A in all subjects (NIS Grade 12 Certificate exam)", `um` "65% minimum average (SHSC)", `ucph` "Pass the KU quota 2-test, then be selected at interview; no numeric cut-off published", `msu` "Math 60 / Informatics 65 (or Physics 55) / Russian 60 (ЕГЭ minimums, 2026)": reviewer prose, not a value any reader can emit; the exact-JSON scorer makes the gpa question unanswerable (0/4 everywhere). Suggest a structured form (`{qualification, requirement}`) or `status: unknown` for the core count.
- **ntu `english_evidence.sat.minimum = 1250`** — the pipeline's SAT key is `sat.minimum`; the corpus files the SAT under English evidence. One of the two should move; and SAT is an English-proficiency *alternative* at NTU, so the key is defensible only with that note.
- **ntu nanyang bindings** — list `/admissions/undergraduate/scholarships/` and `/scholarships-and-awards/` spellings; the live site serves the award at `/admissions/ug/...` (and 301s the first spelling to the second). Binding alias, not a label error.
- **hku `scholarships.computing_data_science_entrance`** — binding subject "School of Computing and Data Science Entrance Scholarship" vs the page's own title "Scholarships - HKU School of Computing and Data Science (HKUCDS)"; the award is one of several headings on that page, so the binding needs the heading text as subject (it has it) and the reader must emit heading-named awards (AP-1).
- **hku `scholarships.entrance.exists`** on `admissions.hku.hk/node/891` — host unreachable from the runner in every run since 2026-10; cannot be verified from here.
- **imperial inspires** — gold URL is the yearly `...undergraduate-20272028.php` page; the programme page links the hub `/fees-and-funding/imperial-inspires-scholarships/` as well. Bindings hold only the `.php` page; a hub-page read would file as unmapped.
- **chula** english ×3 and scholarship ×2 — labels of the ISE (ICE) programme while `programme_urls` also lists the Faculty of Science BSc page we confirm; the two programmes have different English requirements. The case should say which programme the core labels belong to.
- **unsw** — our funding stage claims "UNSW scholarships for international students" from a marketing page (unlabelled). Not a gold error, but a claim the gold cannot catch; worth an `unknown`-status label or a negative test.
- **delft `english_evidence.toefl_ibt.minimum` evidence URL** `…/bsc-international-diploma/1-admission-requirements/` — the live site serves `…/admission-requirements` (the IELTS label on the same page is a hit through the sibling-evidence rule); harmless, but the two URLs should be declared twins.
- **groningen `ielts.overall` evidence URL** `…/admission/non-dutch-qualification/bachelor/bachelor-entry-requirements/language-requirements-and-exemptions?lang=en` — the pipeline reads the `…/with-non-dutch-diploma/bachelor/…` variant and scores a hit (same domain); fine.

## 5. Measurement notes for the next paired runs

1. `funnel2.py` matches gold pages to log lines by a 120-character prefix; the log truncation makes `…/general-admission-requirements` and `…/general-admission-requirements/international-qualifications/other-international-qualifications` ambiguous — the raw `page_diagnostics` (full URLs) were used wherever they existed. Logging the full URL (or a hash) would remove the ambiguity.
2. Awards: record the award page's final URL *and* the index that linked it, so a binding alias can be checked from a capture (`programme_url_aliases` exists for programme pages only).
3. The scorecard's `core_known` counts a question answered when *any* of its labels hits; the per-label table above is stricter and is what the (b)/(c)/(d) fixes move.

## Appendix A — offline probe results (production code, saved pages, no network)

| page | classify_page | table IELTS | prose claims | costs | `_deadline_v2` | `_toefl_total` | links / awards |
|---|---|---|---|---|---|---|---|
| imperial `/study/apply/english-language/` | country_credential_requirements | 0 | duolingo 115 | 0 | None | 21 | — |
| imperial `/2027/computing-beng` (gold programme page) | intake_specific_program | 0 | sat 1480, deadline 2027-01-13, interview | **0** | 13 January 2027 | None | QR-1: 45 links (english ×2, deadline ×2, fees ×41 incl. the inspires `.php`) |
| imperial inspires `.php` (gold award) | **scholarship_index** ('4 award links') | 0 | deadline 2026-10-15 (!) | 0 | 15 October 2026 | None | `_award_links` 2 (hub, fees-and-funding); `_lists_awards_below` False |
| tcd `/study/english-language-requirements/` | unknown | 0 | 0 | 0 | None | 202 | IR rows: Band A/B/C, no column headers |
| tcd `/courses/undergraduate/fees/` | intake_specific_program ('Undergraduate Fees') | 0 | 0 | **0** | None | None | — |
| tcd `/e3/education/scholarships/` | scholarship_index ('6 award links, listing heading') | — | — | — | — | — | `_award_links` 4, all central pages; awards are on-page sections |
| tcd programme page | program_detail | — | — | — | — | — | QR-1: fees `courses/undergraduate/fees/`, english gold page, deadline ×2 (one wrong: microcredentials); no scholarship link |
| unsw english page | unknown | 0 | 0 | 0 | None | None | IR rows by faculty, test in heading |
| uppsala entry-requirements | program_detail | 0 | ielts 6.5, sub 5.5 | 0 | None | **20** | — |
| uppsala programme page | program_detail | 0 | intake fall 2026 | 0 | None (2 study-period windows) | None | QR-1: fees only |
| delft admission-requirements | program_detail | 0 | ielts 6.5, exam, credential eval | 0 | None | **21** | — |
| ubc intl scholarships (gold index) | scholarship_index | — | — | — | — | — | `_award_links` 4 (canadian-only, loans, international-scholars ×2); IMES is on-page |
| eth scholarships index | scholarship_index | — | — | — | — | — | `_award_links` 0; no `cost-of-living` link in static HTML |
| rug scholarships index | unknown (funding, no award name) | — | — | — | — | — | `_award_links` 0; 133 links, none to `nl-scholarship` (client-rendered list) |
| auckland BSc page (gold deadline) | program_detail | 0 | ielts 6.0, sub 5.5 | 0 | **None** ("closing dates") | None | — |
| auckland compsci undergraduate page (confirmed) | program_detail | — | — | — | — | — | links "Bachelor of Science (BSc)" → gold page; QR-1: deadline → important-dates, accommodation how-to-apply |
| hku cds programme page (confirmed) | unknown | 0 | ielts 7.0 (!), sat 1400, superscore | 0 | None | None | "Scholarships" ×4 in the nav; QR-1 0; `_award_links` 0 |
| hku cds scholarships (gold) | **scholarship_award**, subject = page title | — | — | — | — | — | `_award_links` 0 |
| uppsala bachelors-studies/scholarships (gold index) | scholarship_index | — | — | — | — | — | `_award_links` 3, first = gold award page |
| ntu programme page | program_detail | — | — | — | — | — | links "Scholarships" → `/admissions/undergraduate/scholarships` (classifies scholarship_faq; `_award_links` 5 incl. the opportunities listing) |

Unit tests on the gold sentences (`extract_requirements` / `extract_costs` / `_deadline_v2` / `_toefl_total`):
Imperial IELTS sentence → no IELTS claim; NTU "SAT Total score – 1250" → no SAT claim; Uppsala TOEFL sentence
→ 20; Delft TOEFL sentence → 21; Auckland "Application closing dates …" → None; Imperial "Overseas fee 2027
entry £47,800 per year" → no cost; TCD fee row → no cost; Uppsala Autumn-2027 section → deadline 2027-04-15
**and** tuition SEK 450,000.

## Appendix B — files

- `scratchpad/core_gap_tools/funnel2.py` → `out/labels.json` (344 rows), `out/GROUPED.md`, `out/FUNNEL2.md`
- `scratchpad/core_gap_tools/counts.py` → `out/COUNTS.md`, `out/NOTES.md` (the per-label notes behind §2)
- `scratchpad/core_gap_tools/offline_probe.py` (run from `backend/` with `PYTHONPATH=backend .venv/bin/python -P`)
- `scratchpad/core_gap_pages/*.html` — the 17 pages fetched by hand (untrusted data; never executed)
