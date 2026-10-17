# Loop report, finish plan v2 (2026-10-17)

Scored against the **unsigned** drafts `ground_truth.draft10.json` (cohort) and
`heldout.draft1.json`, built from 19 independent expert drafts whose quotes the
production fetcher verified (evidence check 39059316157: 100/128).

## Cycle 1: is the search provider the bottleneck?

Built: Serper as the benchmark's search layer (owner's key, `search_provider=auto`).
Ran: cohort 39058503662 and heldout 39058505075, all rules at their defaults.

| run | provider | known core answered | claim precision | programme page |
|---|---|---|---|---|
| cohort rl1 37545452839 | Exa MCP | 9/27 | 46/46 | 6/10 |
| cohort 39058503662 | Serper | 7/27 | 27/29 | 6/10 |
| heldout 37554279823 | Exa MCP | 0/23 | — | 0/7 readable |
| heldout 39058505075 | Serper | 0/23 | — | 0/7 readable |

Finding: **no**. Swapping the provider moves nothing on unseen sites; the
programme page is lost after search (a Serper smoke query returns TUM's exact
programme page first, the pipeline never confirms it). Root cause under
analysis in `docs/process/DISCOVERY_ANALYSIS_2026-10-17.md`.

Defects found:
- D1 (precision, UBC, Serper run): "Deadline November 15, 2026 … deadline to
  apply and submit an award application if you wish to be considered for the
  … Scholarship" read as the admission deadline. Root cause: a deadline
  conditioned on an award application is claimed as ADMISSION_DEADLINE.
  Queued as rule DL-3.
- D2 (measurement): the expert-draft converter stamped the request's field
  and intake on label evidence; the scorer compares scope literally, so a
  correct NTU claim scored as wrong scope. Fixed (`label_scope`), test added.
- D3 (measurement): the verify script's exact-substring check rejected quotes
  whose table cells the expert joined with " | ". Fixed: words in order,
  separators ignored; a changed figure or a paraphrase still fails.

Decision (delegated): keep the nine heldout universities for the final check
only and build a new development cohort (dev2) for discovery tuning.

## Cycle 2a: DL-3 (award-conditional deadline)

Run 39063173594 (cohort, Serper, off/on/on/off). Wrong claims: off#1 2 (UBC
2026-11-15), on 0 in both repetitions; stable losses 0; known core 7/27 both
arms. The right UBC deadline (2027-01-15) is not a stable gain: Serper's path
does not always reach /dates-deadlines/. **On by default** (precision gain, no
loss; owner delegation).

## Side finding: the golden demo test was a time bomb (product bug)

`WebScholarshipAdapter._derive_availability` judged "deadline passed" on the
server's local `date.today()` while `_stage_assess` uses the run's UTC day.
After 2026-10-15 TUM's Deutschlandstipendium flipped in stored results; CI was
red on main from 2026-10-17. Fixed in 06323a8; full suite 94.87%.

## Cycle 2b: dev2 baseline, HP-1, CU-1

dev2 control 39066742964 (10 no-seed universities, Serper): **0/21** known core
answered — the heldout failure reproduces on a development split, so discovery
and evidence rules can be tuned without touching the heldout nine. (dev2's
programme_page_recall has denominator 1: the converter keeps only programme
URLs whose title quote verified; use "known core answered".)

| rule | cohort run | dev2 run | labels | reads | decision |
|---|---|---|---|---|---|
| HP-1 hop-root deadline | 39067186082 | 39067187799 | no change | no change | off (no effect) |
| CU-1 http/https identity | 39067189351 | 39067190840 | no change, 0 losses | dev2 345/342 → 326/323 | **on** |

New finding (TCD trace): after discovery finds the programme page the verify
stage gets nothing — the host is marked dead after one discovery timeout, the
admissions page used is a postgraduate one, and discovery spends all 6 queries
so topic search cannot run. Analysed in docs/process/EVIDENCE_ANALYSIS_2026-10-17.md.

## Cycle 2c: discovery rules SM-1, SO-1, QA-1

| rule | cohort run | dev2 run | known core | reads | programme pages (dev2, by URL) | decision |
|---|---|---|---|---|---|---|
| SM-1 sitemap child priority | 39067291167 | 39067292756 | 7/27, 0/21 both arms | ≈ | same pages | off (no effect) |
| SO-1 cost-aware search order | 39067294419 | 39067295985 | 7/27, 0/21 both arms | −45 both splits | **lost TCD's correct page** in one pair | off (discovery regression outweighs reads) |
| QA-1 alias queries | 39067297468 | 39067298867 | 7/27, 0/21 both arms | ≈ | same or different junk | off (no effect) |

What the dev2 traces show instead: accepted "programme pages" are often not
programme pages (a staff page at lafhis.dc.uba.ar, a researcher profile at
research.tec.mx, a PDF at pps.kaznu.kz, UCT's Business Science programme) —
PG-1's target — and where the right page is found (ETH, TCD, Uppsala) the
evidence stage still yields nothing (EVIDENCE_ANALYSIS).

## Cycle 2d: PG-1 programme page guard

Runs 39067949720 (cohort) and 39067951214 (dev2). Labels unchanged, 0 losses,
reads −15/−20. What changed is what the pipeline calls "the programme page":
with PG-1 on, a scanned PDF (KazNU), a researcher profile (Tec), an LMS link
(UBA), a college page (Khalifa), an Aalto minor and HKU's department root are
no longer reported; TCD's page is now `unresolved` — the trace shows it was
never read (10 s timeout), so the old arm had reported an unread lead as the
programme. That is DoD target 3's "never a guess". **On by default.**

## Cycle 2e: LI-1 localized identity; PG-1 defect fixed

LI-1 runs 39068981447 (cohort) and 39068982766 (dev2): labels unchanged, 0
losses; Paris-Saclay's `licence-undergraduate-programme/informatique` page
(the English twin of the expert's page) found in both on repetitions and in
no off repetition. **On by default.**

PG-1 defect found by the full suite: `is_host_root` read a single two-letter
path segment as a language root, so `https://uni.edu/cs` (computer science;
also the code for Czech) was demoted. Fixed: a two-letter segment is a root
only when the page's own `<html lang>` says that language, or, without a lang
attribute, when the code is not also a programme abbreviation (cs, it, ai, is,
ml, ee, ce, me). Test added.

## Cycle 3a: parallel paired runs (measurement speed)

A paired run captured its 40 observations one after another (about 45 min for
ten universities). `case_parallelism` captures several universities at once,
each in its own off/on/on/off order; different universities are different
sites, so no site sees more requests.

Check: SO-1 on the cohort, serial run vs run 39076880836 at 5 in parallel,
both scored on ground_truth.draft10.

| | serial | parallel 5 |
|---|---|---|
| wall clock | ~45 min | 12 min |
| known core answered (4 arms) | 5, 7, 7, 7 / 28 | 7, 7, 7, 7 / 28 |
| wrong claims | 0 | 0 |
| stable gains / losses | 0 / 0 | 0 / 0 |
| unstable | hku:programme.exists | hku:programme.exists |
| median / max seconds per capture | 66 / 115 | 57 / 107 |
| wall-clock timeouts | 2 (groningen) | 0 |

Decision: 5 in parallel is the default. The SO-1 decision (off) stands.

## Cycle 3b: HL-1, UC-1, CL-1, EX-2, QB-1 (serial paired runs)

Scored with `scorecard --allow-drafts`: cohort on ground_truth.draft10, dev2 on
dev2.draft1. Columns off#1, off#2, on#1, on#2.

| rule | cohort run | dev2 run | cohort known core | dev2 known core | stable gains | losses / new wrong | reads | decision |
|---|---|---|---|---|---|---|---|---|
| HL-1 hub leads | 39074822464 | 39074824494 | 7,7 → 8,5 | 0 → 0 | none | 0 / 0 | +18 / +12 | **off**: no effect, more reads |
| UC-1 service pages | 39074826071 | 39074827931 | 7,7 → 7,7 | 0 → 0 | none | 0 / 0 | +4 / +8 | **off**: no effect |
| CL-1 catalogue heading scope | 39074829596 | 39074831170 | 7,7 → 8,8 | 0 → 0 | groningen:ielts.overall | 0 / 0 | ±0 | **on** |
| EX-2 deadline window scope | 39074832834 | 39074834122 | 7,7 → 7,7 | 0 → 0 | none | 0 / 0 | ±0 | **off**: no effect |
| QB-1 discovery query reserve | 39075147659 | 39075149269 | 7,7 → 7,8 | 0,0 → 1,1 | uppsala:ielts.overall, uppsala:ielts.subscores (dev2) | 0 / **groningen ielts 6.0 (gold 6.5)** | +45 / +6 | **off for now**: new wrong claim, programme pages 6,6 → 4,5; root cause under analysis |

CL-1 also found the right programme page in both dev2 repetitions for TCD
(`/courses/undergraduate/courses/computer-science`) and Uppsala
(`/study/programme/bachelors-programme-computer-science`); dev2 programme
page recall 1/6 → 3/6. QB-1 produced the first claims ever on dev2 (Uppsala
IELTS, precision 4/4 and 2/2).

### QB-1 root cause (analysis 2026-10-17, scratch QB1_ANALYSIS.md)

- **Groningen IELTS 6.0 is a scope bug independent of QB-1.** Topic search,
  which only has budget under QB-1, read the Faculty of Economics and
  Business "apply for a Bachelor" page; its IELTS 6.0 was attributed to the
  Computing Science bachelor (Faculty of Science and Engineering, 6.5).
  Topic pages are never checked against the programme's faculty. Fix: FS-1
  (topic page faculty scope), in progress. The 6.5 hit in on#2 came from the
  Campus Fryslân block of a multi-faculty page, right by accident.
- **No discovery loss.** Groningen's programme page was confirmed in all four
  runs; the on arm spent the reserve late and hit the 120 s wall clock, and the
  harness's timeout path never fills `programme_urls`. Warsaw on#1 confirmed
  `programmes-first/IN/S1-INF`, an identical twin of the gold
  `programmes-all/IN/S1-INF/`. Fixes: QB-1b (no hop entry points and at most
  3 recovery checks when a page is already confirmed) and the harness timeout
  path, in progress.
- **Reads +45** are the reserve being spent: topic pages and their leads,
  award-search pages, robots.txt and redirect hops on new hosts.

Label proposals for the owner (draft10 is unsigned; not applied):
1. Warsaw: accept `…/programmes-first/IN/S1-INF` beside `…/programmes-all/IN/S1-INF/` (same title and h1).
2. Groningen: accept the programme URL without `?lang=en`.
3. Groningen IELTS evidence: the gold URL is 404 today; the university-wide
   `bachelor-entry-requirements/language-requirements-and-exemptions` page's
   Faculty of Science and Engineering row states the same 6.5.

## Cycle 3c: DI-1 (admissions host from homepage)

| rule | cohort run | dev2 run | cohort known core | dev2 known core | stable gains | losses / new wrong | reads | decision |
|---|---|---|---|---|---|---|---|---|
| DI-1 admissions host | 39076132879 | 39076134490 | 7,7 → 7,7 | 0 → 0 | none | 0 / 0 | +11 / +12 | **off for now** |

DI-1 fires where it should (Tsinghua: `join-tsinghua.edu.cn` accepted in both
on repetitions) but adds no answer: with every discovery query spent, topic
search never runs, so nothing searches the second domain. It is re-measured
together with QB-1, which leaves queries for topic search.

The dev3 QB-1 run 39076378164 was cancelled by the 55-minute job limit
(15 universities serially); it is re-run with five in parallel and QB-1b.
