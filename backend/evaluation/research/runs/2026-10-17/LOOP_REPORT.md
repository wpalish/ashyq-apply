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

## Cycle 3d: QB-1b, FS-1 and the bundle; QB-1 and FS-1 on

All runs five universities in parallel. Cohort on reviewed10 (signed), dev2 on
dev2.draft1, dev3 on dev3.draft1.

| run | set | known core (off#1, off#2, on#1, on#2) | stable gains | losses / new wrong | note |
|---|---|---|---|---|---|
| QB-1b 39080023001 | cohort | 8, 3, 6, 6 / 28 | hku:programme.exists | 0 / 0 | off arm: Groningen ×2 and UBC ×1 over 120 s; UBC's you.ubc.ca answers robots-disallowed in some captures (site, not rule) |
| QB-1b 39080024396 | dev2 | 0, 0, 1, 1 / 21 | uppsala:ielts.overall, uppsala:ielts.subscores | 0 / 0 | programme pages 3/6 in all arms (CL-1) |
| QB-1b 39080161290 | dev3 | 0, 0, 1, 1 / 28 | auckland:ielts.overall | 0 / auckland:ielts.subscores 6.0 | programme pages 0/11 in all arms |
| QB-1 + FS-1 39080847253 | cohort | 6, 6, 6, 6 / 28 | none | 0 / 0 | Groningen IELTS 6.0 gone |
| QB-1 + FS-1 39080850234 | dev2 | 0, 0, 1, 1 / 21 | uppsala:ielts.overall, uppsala:ielts.subscores | 0 / 0 | |
| QB-1 + FS-1 39080851464 | dev3 | 0, 0, 1, 1 / 28 | auckland:ielts.overall | 0 / auckland:ielts.subscores 6.0 | captured before the extraction fix below |

**Auckland subscores 6.0 is an extraction bug, not QB-1.** The page says
"Overall score of 6.0 and no bands below 5.5"; `_IELTS_SUB` matched only the
singular "band", skipped it, and took the "6" of another test's "no section
below 60%". Fixed (plural floors; a band is never followed by a digit or %),
with tests.

**Decision: QB-1 (with QB-1b) and FS-1 on by default.** Three stable gains, no
stable loss on any set, and the one new wrong claim has an independent root
cause that is now fixed. The golden demo is byte-identical with both on.

**Open: dev3 discovery.** 0/11 programme pages in every arm; Imperial, UNSW and
USP sent no query in 115-120 s. Under analysis.

## Cycle 3e: DI-1 on top of QB-1 + FS-1; dev3 analysis

| run | set | known core (off#1, off#2, on#1, on#2) | stable gains | losses / new wrong | decision |
|---|---|---|---|---|---|
| DI-1 39082225120 | cohort | 6, 6, 6, 6 / 28 | none | 0 / 0 | |
| DI-1 39082226594 | dev2 | 1, 1, 1, 1 / 21 | none | 0 / 0 | |
| DI-1 39082228030 | dev3 | 1, 1, 1, 1 / 28 | none | 0 / 0 | **DI-1 off**: no effect even with topic-search budget |

These runs are also the first control on the new defaults (CL-1, QB-1, QB-1b,
FS-1, plural-band fix): **no wrong claim in any arm of any set**; Auckland's
subscores are no longer claimed.

**Cohort 7-8 → 6 is UBC's site, not a regression.** Every lost label is UBC's
(deadline, IELTS overall and subscores, programme). you.ubc.ca answered
normally in the CL-1 run (88 reads ok) and robots-disallowed in later runs
(QB-1 + FS-1: 36 of 36, both arms; DI-1: 12 of 39). The policy fails closed
when robots.txt is unreachable, as it must.

**dev3 analysis (scratch DEV3_DISCOVERY_ANALYSIS.md).** Imperial, UNSW, USP
ran out of the 120 s clock before the first query (slow hosts, a sitemap
parser bug, ranking); KU Leuven drops connections, UB is behind a Cloudflare
challenge (not fixable without bypassing, which we do not do); IIT Delhi's
page was found and refused (no B.Tech degree word; CSE also counts as related,
not equivalent: owner decision); PUC and UiO publish Spanish / Norwegian pages
only; UCPH, UM, Chula and Auckland found a correct page the gold did not list.
dev3.draft1 now accepts those pages (development split, unsigned): programme
pages 0/11 → 4/11 on the same captures. Fixes in progress: sitemap namespace
and relative locs (bug fix), SR-1 field-slug scoring, LX-1 lexicon, HS-1 a
guessed URL never stalls a host.

## Cycle 3f: SR-1, HS-1 (with the sitemap parser fix in both arms)

| rule | cohort | dev2 | dev3 | stable gains | new wrong | decision |
|---|---|---|---|---|---|---|
| SR-1 field slug scoring (39083827723 / 39083829058 / 39083830298) | 6 → 6 | 1 → 1 | 1 → 1 | none | uppsala deadline 2027-01-15 (1 rep); um ielts.overall 6.0 (1 rep) | **off** |
| HS-1 guessed URL never stalls a host (39083832134 / 39083833560 / 39083834894) | 6 → 6 | 1 → 1 | 1 → 1 | none | none | **off**: no effect |

Known core answered, off → on. The sitemap parser fix (https namespace,
relative locs) is in both arms; it changed no label by itself.

Why dev3 still finds nothing new: Imperial and UNSW still hit 120 s before the
first query. UNSW's sitemap now parses, but each document takes ~10 s and the
index lists news and staff sitemaps before `study/undergraduate.sitemap.xml`,
so the clock runs out in the sitemap stage. That is exactly what SM-1
(programme sitemaps first) and SO-1 (search first when the host is slow) were
built for; both were measured before the parser fix and QB-1, and are re-run
now on all three sets (39085143891 … 39085150435).

## Cycle 3g: SM-1, SO-1 re-run on the new defaults; LX-1; FS-2

| rule | cohort | dev2 | dev3 | stable losses / new wrong | decision |
|---|---|---|---|---|---|
| SM-1 programme sitemaps first (39085143891 / 39085145178 / 39085146376) | 6 → 6 | 1 → 0 | 1 → 1 | **uppsala ielts.overall, ielts.subscores** / um ielts 6.0 (1 rep) | **off** |
| SO-1 search first on slow hosts (39085147782 / 39085149041 / 39085150435) | 6 → 6, 8 | 1 → 1 | 1 → 1, 0 | dev3 programme pages 4 → 3, 2 / none new | **off** |

Known core answered, off → on.

**UM IELTS 6.0 is claimed by the current defaults too** (SO-1 run, off arm).
The topic search's English-requirements query returned
`study.um.edu.my/bachelor-of-english-language-and-linguistics`, another
programme's own page, and its conditional-admission "Band 6" was claimed for
Computer Science (UM's CS page states 5.5). FS-1 checks faculties only. New
rule FS-2 (`TOPIC_PROGRAMME_SCOPE`, off): a topic-search page, or a lead from
one, that is a programme page of another field claims nothing.

LX-1 (lexicon: B.Tech, licenciatura and other bachelor words; funding gate on
the page identity; informatikk, datalogi, informàtica, ciencia de la
computación as localized identity aliases; Spanish/Dutch/Norwegian publication
paths and lirias in PG-1) is in, off, and under paired runs. "Enginyeria
informàtica" was left out: it is computer engineering, refused like the
Italian "ingegneria informatica".

| rule | cohort | dev2 | dev3 | stable losses / new wrong | decision |
|---|---|---|---|---|---|
| LX-1 lexicon (39086520685 / 39086522101 / 39086523553) | 6 → 6 | 1 → 1 | 1 → 1 | 0 / **imperial deadline 2026-04-28, 2026-09-28** | **off** |
| FS-2 topic programme scope (39086716573 / 39086718309 / 39086719897) | 6 → 6 | 1 → 1 | 1 → 0 | **auckland ielts.overall, ielts.subscores** / 0 | **off**: too coarse, it also cut Auckland's English requirements page |

**Coverage swings explained.** The full suite reported 90-94 % while files were
being edited during the run (coverage maps its data to the files as they are at
report time; the low modules were exactly the ones edited: live_discovery 59 %,
page_classifier 60 %, web_requirements 67 %). With no edit during the run:
94.94 %, all tests pass. Rule for this loop: never edit while the full suite runs.

**Where the loop stands.** On: CL-1, QB-1 + QB-1b, FS-1, the plural-band fix,
the sitemap parser fix. Known core answered: cohort 6/28 (UBC is robots-closed
at the moment; 7-8 with it), dev2 1/21, dev3 1/28; one recurring wrong claim
(UM IELTS 6.0 via another programme's page). The last eight single rules (DI-1,
SR-1, HS-1, SM-1, SO-1, LX-1, FS-2, and HL-1/UC-1/EX-2 before them) moved
nothing. The remaining blockers are structural: slow hosts spend the 120 s
before the first query (Imperial, UNSW), local-language-only pages (PUC, UiO),
and sites that refuse us (KU Leuven, UB).

## Cycle 4a: structural changes from STRUCTURAL_ANALYSIS_2026-10-18

Merged (flags off): SB-1 `--stage-budgets`, QR-1 `--question-routing`, AR-1
`--award-route`. Merged on by default: extraction fixes (application deadline
before a test window, IELTS "Score required" cell, IELTS in a list of tests),
TOEFL iBT / Duolingo minimums scored under `english_evidence.*`, stage
telemetry, and a confirm-checkpoint trace. Full suite: 94.97 %, all pass.

Known core answered, off → on (the dev3 off arm is 2 because TOEFL now scores):

| run | cohort | dev2 | dev3 | stable gains | new wrong / wrong-scope (on) |
|---|---|---|---|---|---|
| AR-1 (39091458171 / 39091459307 / 39091460461) | 6 → 6 | 1 → 1 | 1 → 1 | none | none |
| SB-1 (39092648825 / 39092650149 / 39092651873) | 6 → 6 | 1 → 1 | 2 → 2 | none | unsw ielts 6.5; dev3 programme pages 4 → 2-3 |
| QR-1 (39092653528 / 39092654922 / 39092656324) | 6 → 7 | 1 → 1 | 2 → 2 | **delft:deadline** | ubc ielts 6.5 + subscores (scope), uct ielts 6.5 (scope) |
| SB-1 + QR-1 + AR-1 (39092657656 / 39092659136 / 39092660804) | 6 → 7 | 1 → 1 | 2 → 2 | **delft:deadline** | uct; unsw; um ielts 5.0/6.0, toefl 41/57; puc deadline 2024-10-01; imperial deadline 2026-04-28 |

Decision: all three stay **off** for now — precision falls below the 0.95 bar
as soon as more pages are read. The TOEFL mapping also exposed that the
current defaults claim UM's TOEFL 57 / IELTS 6.0 from the English Language
and Linguistics programme page. Every wrong claim is under root-cause
analysis; the bundle is re-run with the extraction fixes in (39092657656 ran
before them).

## Cycle 4b: fixes from WRONG_CLAIMS_ANALYSIS; FS-2 on

On by default (bug fixes): TOEFL read from TOEFL's own statement (UM 57 → 78,
FAQ 41 → 60: they were PTE scores); opening/announcement dates are never the
deadline (Imperial's "28 April 2026 – UCAS search tool opens"); ISO deadlines
more than a year past and exchange/mobility pages are not claimed (PUC
2024-10-01). Behind flags: QR-1b (scope from the linking programme page, one
read per institution, every question page read for its question), SB-1b (the
read cap never skips search, search by 33 s, sitemap reads apart). Full suite
95.01 %, all pass.

| run | cohort | dev2 | dev3 | stable gains | new wrong (on) | decision |
|---|---|---|---|---|---|---|
| FS-2 narrowed (39096181406 / 39096182669 / 39096183785) | 6 → 6 | 1 → 1 | 1-2 → 2 | warsaw programme.exists, programme.language | uppsala deadline 2027-01-15 (1 rep) — a gold dispute, see below | **on** |
| SB-1 + QR-1 + AR-1 with b-fixes (39096177621 / 39096178894 / 39096180155) | 6 → 7 | 1 → 1 | 2 → 2 | delft:deadline | uct ielts 6.5 scope (1 rep); unsw ielts 6.5 (Bengaluru campus) | **off**: two left |

FS-2 removes the claims today's defaults made from UM's Linguistics page
(IELTS 6.0, TOEFL 78). Uppsala's 2027-01-15 is read from the official
`/study/bachelors-studies` page ("15 January 2027 - Application closes" for
autumn 2027, the international round); the draft gold holds 2027-04-15 (the
second round). Both are official; raised in SIGN_DEV2 for the owner.

Left for the bundle: UNSW confirms the Bengaluru campus page because its real
programme page is refused by the funding gate (LX-1 part 2 fixes it); one UCT
repetition still claims the degree-silent English page without the inherited
scope.

## Cycle 4c: the bundle on by default

Added behind flags, then measured together with SB-1 + QR-1 + AR-1: FI-1
`--funding-identity-scope` (the funding gate reads the page identity only —
the part of LX-1 that fixes UNSW's and Auckland's programme pages), CG-1
`--campus-guard` (a branch campus abroad is never the programme page: UNSW
Bengaluru), QR-1c (a degree-silent page linked from the admissions page beside
a confirmed programme takes the programme's degree: UCT).

Bundle run 39098957286 / 39098958087 / 39098958849 (known core answered, off → on):

| set | off | on | stable gains | flagged on claims |
|---|---|---|---|---|
| cohort | 6, 6 | 7, 7 | delft:deadline | none |
| dev2 | 1, 1 | 2, 2 | uct:ielts.overall | uppsala deadline 2027-01-15 (gold dispute: official international round) |
| dev3 | 2, 2 | 3, 3 | imperial:deadline | imperial deadline 2027-01-13 also read from the MEng page (right value, other programme) |

Pooled on-arm precision 51/54 = 0.944 as scored; 52/54 = 0.963 if the
Uppsala round is accepted. Decision (owner delegation): **SB-1, QR-1, FI-1,
CG-1 on by default.** AR-1 stays off: it alone changes the golden demo, and it
never gained a label. Follow-ups landed: integrated master's (MEng, MSci,
MMath, MPhys, MChem) read as master level for a bachelor request
(`INTEGRATED_MASTERS_LEVEL`, on); 37 tests that assumed the old defaults
aligned (all stale assertions, no product bug; each rule is now tested both
on and off). Full suite 4208 passed, 95.04 %. Golden demo byte-identical.

Final check: the heldout nine on the current defaults, run 39103386295,
scored on heldout.reviewed1 (signed).

## Final check: the heldout nine on the current defaults (run 39103386295)

Scored strictly on heldout.reviewed1 (signed). Both arms are today's defaults,
so the four columns are four repetitions. Only the aggregate is read; no
heldout label is used to design a rule.

| metric | rep 1 | rep 2 | rep 3 | rep 4 |
|---|---|---|---|---|
| programme page recall | 0/9 | 1/9 | 0/9 | 0/9 |
| known core answered | 0/23 | 0/23 | 0/23 | 0/23 |
| claims (all wrong scope) | 3 | 3 | 3 | 3 |

Every site was reached and every case stayed within 6 queries / 60 reads /
120 s (first query at 12-34 s). The search did not generalise: the gains on
the development sets (cohort 6 → 7/28, dev2 1 → 2/21, dev3 1 → 3/28) came from
finding requirement pages once the programme page is known, and on the
heldout nine the programme page itself is not found.

**DoD status (docs/process/SEARCH_DEFINITION_OF_DONE.md):**

| criterion | target | development sets | heldout | met |
|---|---|---|---|---|
| claim precision | ≥ 0.95 | 0.944 scored / 0.963 with the Uppsala round | 0/3 | no |
| wrong scope | ≤ 3 % | ~4 % | 100 % (3 claims) | no |
| programme page found on readable sites | always, never a guess | cohort 5/10, dev2 3/6, dev3 4/11 | 0-1/9 | no |
| known core answered | ≥ 80 % | 25 %, 10 %, 11 % | 0 % | no |
| budget 6 / 60 / 120 s | all cases | **no**: dev3 has 4-5 cases over budget (Imperial 68-71 reads, Chula 61-63; see correction below) | yes | no |
| heldout within 15 pp | ≤ 15 pp | — | 25 pp below cohort | no |

The algorithm is not done. The search stays inside its budget and almost
never invents a value on the development sets, but it finds a minority of
answers, and the heldout result says programme discovery for unseen
universities is the binding gap.

### Correction (2026-10-18): the budget criterion is not met on dev3

The DoD table above first marked "budget 6 / 60 / 120 s" as met on the
development sets. That was wrong: I checked the heldout run only. The
scorecard's own `cases_over_budget` row is 4-5 on dev3 in bundle run
39098958849 and in the SB-1c check 39106597318 (Imperial 68-71 reads at
115 s, Chula 61-63 reads). The table row is corrected.

SB-1c check (run 39106597318, nine dev3 cases on current defaults, both arms
defaults): UiO now sends 5 discovery queries (0 before the fix); no new wrong
claim; precision 3/3 on every repetition.

## v3 M3: the production identity gate, first measurement (runs 39110771082 / 39110772358)

On arm = `--through-identity-gate` (entry built from the seed row; production's
`CatalogueDiscoveryAdapter._identify_site` decides the site). Off arm = today's
benchmark path with verified domains.

| set | identity established (on, rep 1 / 2) | not established | known core off → on | stable losses |
|---|---|---|---|---|
| dev2 | 6/10, 5/10 | kaznu, tcd, tsinghua, uppsala (+ khalifa once) | 2 → 1 | uppsala ielts overall + subscores |
| dev3 | 6/15, 6/15 | auckland, chula, iitd, ntutw, ub, ucph, uio, utokyo (+ msu / kuleuven once) | 3 → 2 | auckland ielts overall + subscores |

The product never starts searching on 40-60 % of these universities: every
number the loop has published so far measures a path production does not
take for them. This is plan rule R6 (ticket 05: redirect to `official_site` →
native name by `<html lang>` → English alternate → today's rule).

## v3 R6 `SITE_IDENTITY_V2` through the production gate (runs 39113842507 / 39113844090)

On arm = `--through-identity-gate --site-identity-v2`; off arm = the benchmark's
verified entry. Savers and the request ledger are on in both arms.

| set | identity established (on) | before R6 (M3 run) | not established | stable losses vs verified path | new wrong |
|---|---|---|---|---|---|
| dev2 | 8/10, 8/10 | 6/10, 5/10 | kaznu, khalifa (sites refuse the runner: certificates) | none | none (Uppsala 2027-01-15 is the open gold dispute) |
| dev3 | 12/15, 12/15 | 6/15, 6/15 | iitd, kuleuven, ub (refuse the runner) | none | none |

The gate now matches the verified path on every site that lets us read it.
One defect found: rows with no domain (auckland, ntutw, utokyo) spend the
identity fallback query outside the 6-query budget (7 sent); fix in progress.
R6 stays off until that fix lands.

## v3 rules R1, R2, R3 and probe M5 (2026-10-18)

Programme pages found (`programme_page_recall`, two repetitions per arm; dev4
counts the five cases with an exact gold page, owner decision on related ones):

| rule | runs | cohort off → on | dev2 | dev3 | dev4 | stable gains / losses | decision |
|---|---|---|---|---|---|---|---|
| R1 localized page identity | 39119685301 / …6849 / …8512 / …0148 | 5 → 5 | 4 → 4 | 3-4 → 4 | 1 → 2 | +rwth / none | **on** |
| R2 subject title shapes (with the 19-Q4 amendment) | 39126143581 / …6244 / …8051 / …9746 | 5 → 5 | 4 → 4 | 4-5 → 4-5 | 1-2 → 2 | none / **imperial:deadline**; new wrong-scope uct ielts | off, fix R2b in progress |
| R3 sitemap keep by subject+level | 39126683224 / …4628 / …6134 / …7881 | 5 → 5 | 4 → 3 | 3-4 → 3 | 1 → 1 | none / **psaclay programme page** (gold never seen on the on arm) | **rejected, stays off** |

R3's predicted gains did not happen: UM was already confirmed on the off arm,
UBA's gold page is never seen by any stage. It also displaces Paris-Saclay's
page (seen and confirmed off, never seen on).

M5 Serper probe (run 39126325681, 30 credits): gold in top 10 of six local
development cases — today's English family 1/6, local alias + local bachelor
word 4/6, the same with `hl`/`gl` **5/6**. R5 builds that family into the
first pass (runs dispatched).

## v3 rules R5, R4 and TB-1 (2026-10-18)

| rule | runs | programme pages, off → on (cohort / dev2 / dev3 / dev4) | stable gains / losses | budget | decision |
|---|---|---|---|---|---|
| R5 local-language query family | 39127583646 / …5479 / …7124 / …8639 | 5→5 / 3-4→**5** / 3-4→4 / 1→1 | **uba, iitd** programme pages in both reps / none | unchanged | **on** |
| R4 local catalogue entry | 39128108020 / …9727 / …1315 / …2914 | 5→5 / 3-4→3 / 4-5→4 / 1→1-2 | none / none | cohort 0 → 2 cases over | **rejected, stays off** |
| TB-1 per-case time budget | 39127473231 (cohort) / 39127474664 (dev3); dev2/dev4 pending | 5→5 / — / 3-4→4 / — | none / none | **cohort 1 → 0, dev3 2 → 0** | on once dev2/dev4 show no loss |

R4 adds reads without finding a page: as its builder predicted, the
navigation step it hooks into rarely runs under SB-1's order on the target
cases (puc, uio), and where it runs it only costs requests.

## Clean baseline on today's defaults (runs 39134382040 / 39134383452 / 39134384807 / 39134386353)

Both arms are the defaults (R1, R2+R2b, R5, R6, SB-1, QR-1, FI-1, CG-1, savers,
request ledger, TB-1; R3/R4 rejected), scored on the gold updated with the
owner's second-page and related labels. Four repetitions per set:

| set | programme pages found | wrong programme pages | claim precision | wrong scope | cases over budget | known core answered |
|---|---|---|---|---|---|---|
| cohort | 5-6 / 10 | 0-1 | 1.00 (81/81) | 0 | 0 | 7-9 / 28 |
| dev2 | 5 / 6 | 0 | 0.91 (10/11) | 0 | 0 | 1-2 / 21 |
| dev3 | 8-9 / 11 | 0-1 | 1.00 (20/20) | 0 | 0 | 3 / 28 |
| dev4 | 2-3 / 5 | 0 | 1.00 | 0 | 0 | — |

This morning (final heldout check time): programme pages cohort 5/10, dev2 3/6,
dev3 4/11, dev4 1/9 (before relabelling); cases over budget 4-5 on dev3.
The one wrong dev2 claim is Uppsala's 15 January deadline, the open gold
dispute (official international round).

DoD status: budget (target 5) **met on all four sets**; precision ≥ 0.95 and
wrong scope ≤ 3 % met except the Uppsala dispute; programme page on every
readable site (target 3) — remaining misses are mostly access (aalto, toronto,
hku, ubc flaky, kuleuven, ub) plus ordering (rwth, ctu, unibo — RK-2 in
measurement); core answers (target 4) remain far from 80 %: the binding gap
is now evidence on a found page, not discovery.

## RK-2, the read-saving trio, and a scope fix (2026-10-18)

| change | runs | result | decision |
|---|---|---|---|
| RK-2 retrieval rank v2 | 39135098804 / …100422 / …102075 / …103778 | loses **uba** (dev2) and **unsw** (dev3) programme pages in both reps; hku once | **rejected, off** |
| FEE_SUBPAGE_EXCLUSION + LOCAL_TWIN_ON_IDENTITY_REFUSAL + ALIAS_AWARE_PROGRAM_MATCH | 39134950075 / …951928 / …954132 / …956132 | no programme page gained or lost; rwth `programme.exists` stable gain; fewer reads | **on** |
| programme name without a file extension (bug fix) | same | KIT `programme.exists` now claimed | on |
| scorer: `.htm` variant; a university named with its acronym beside it | rescored | KIT's claim was scored wrong_scope on "KIT, Karlsruhe Institute of Technology"; dev4 precision 1.00 | in |

## Evidence on found pages: DL-5, EN-2, FE-2, AP-1 (runs 391458553…–391460993…)

From docs/process/CORE_GAP_ANALYSIS_2026-10-18.md. Stable label gains / losses (off → on, 2 reps each):

| rule | stable gains | stable losses | new wrong | decision |
|---|---|---|---|---|
| DL-5 + QP-1 + QR-2 + SQ-1 | uppsala deadline, auckland deadline | none | none | on after DL-5b (no whole-programme tuition) |
| EN-2 english readers | delft toefl; tcd ielts overall+subscores, toefl, duolingo; uppsala toefl; imperial ielts overall+subscores | **auckland ielts overall+subscores** | none | fix EN-2b first |
| FE-2 fee readers + SAT fix | tcd tuition, imperial tuition | **ubc deadline** | imperial Home £10,050 (gold has no population) | fix FE-2b first |
| AP-1 award page evidence | imperial_inspires exists + international | none | ubc major_entrance ×2 (wrong scope: degree missing, related BA programme inherited) | fix AP-1b first |

ID-1 scorer aliases (NTU SAT key, award URL alias) are off until the owner
signs them: the SAT alias scored NTU's correct 1250 as wrong scope against a
descriptive gold population.

## EN-2b and FE-2b reruns (2026-10-18)

Paired runs with 2 reps per arm. Stable means the change appears in both reps. No set was over budget in either arm, and precision was 1.00 in both arms.

| Rule | Set | Stable gains | Stable losses | Wrong claims |
|---|---|---|---|---|
| EN-2b (39150325173/326857/328178) | cohort | delft toefl | none | 0 |
| | dev2 | tcd duolingo, toefl, ielts overall, ielts subscores; uppsala toefl | none | 0 |
| | dev3 | imperial ielts overall, ielts subscores | none | 0 |
| FE-2b (39150329872/331765/333407) | cohort | none | none | 0 |
| | dev2 | tcd tuition | none | 0 |
| | dev3 | imperial tuition (international, £47,800) | none | 0 |

- Auckland IELTS is no longer lost.
- The UBC deadline is not lost, and no Imperial Home-fee row is claimed for an international applicant.
- Both rules are now on by default: `ENGLISH_READERS_V2` and `FEE_READERS_V2`.
- Test alignment for the DL-5 bundle and AP-1 is merged. It includes two product fixes:
  - QP-1 now reads the programme and admissions pages first even when QR-1 is off.
  - SQ-1 no longer re-asks a provider whose index query failed.
- Full suite: 5460 passed.

## Clean baseline 2 (2026-10-18, every rule on; runs 39152953156/954966/956828/958881)

Four reps per set. Neither arm adds a rule, so each set gets four identical captures.

| Set | Programme page found | Wrong page | Known core answered | Over budget | Precision | Wrong scope |
|---|---|---|---|---|---|---|
| cohort | 5–6/10 | 0–2 | 11–12/28 | 0 | 1.00 | 0 |
| dev2 | 2–5/6 adjudicated | 0–1 | 4–5/21 | 0 | 1.00 | 0 |
| dev3 | 7–9/11 adjudicated | 0–1 | 8/28 | 0 | 1.00 | 0 |
| dev4 | 3–4/5 adjudicated | 0 | — (no core labels) | 0 | 1.00 | 0 |

DoD status:
- Met: precision, wrong scope and budget.
- Not met: programme page on every readable site, and ≥80% core answers.

Remaining gaps:
- Wrong page in some reps: toronto, hku, tcd.
- Page missed: toronto, kaist, tsinghua, kuleuven, ub, uba/uio (1 rep).
- Page found but core questions unanswered: groningen 3/5, ntu 1/5, ethz 0/2, uppsala 2/4, tcd 2/4, warsaw 0/2, unsw 0/3, chula 0/3, auckland 2/4, um 1/2, puc 0/1, ucph 0/1.

AP-1c (`--nav-link-level-guard`; runs 39153129640/131153/132653/134257):
- No stable gains, no stable losses, 0 wrong claims.
- On by default.

## Corpus corrections round (finish-algorithm ticket 02, owner «Все да», 2026-10-18)

The eight signed lines are applied: reviewed11 (cohort), dev2-draft2, dev3-draft2 (`VERSIONS.md`), the
ID-1 award URL alias and SAT key alias on by default, and fee period in the scorer (02-Q4; the pipeline is
unchanged and still abstains on a semester fee). No run: the frozen `base2-*` and `ap1c-*` captures are
re-scored. Their raw claims are re-mapped under the URL alias (a raw claim's predictions are replaced only
where the alias changes them; with the alias off every stored prediction is found again, no mismatch), then
scored with `python -m evaluation.research.scorecard … --allow-drafts` against the new corpora (dev4 against
dev4-draft1, unchanged). Four repetitions per arm; both arms are the same rule set.

| set | known core answered (before → after) | claim recall | precision | wrong claims |
|---|---|---|---|---|
| base2 cohort | 11, 12, 12, 11 / 28 → **14, 15, 15, 14 / 27** | 20–22/84 → 28–30/83 | 1.00 → 1.00 | 0 → 0 |
| base2 dev2 | 5, 5, 5, 4 / 21 → **4, 4, 4, 4 / 21** | 9–10/27 → 9/28 | 1.00 → 0.90 (9/10 in 3 reps) | 0 → **1** (uppsala `deadline` 2027-04-15: wrong value, wrong scope) |
| base2 dev3 | 8 / 28 → **8 / 22** | 11/34 → 11/26 | 1.00 → 1.00 | 0 → 0 |
| base2 dev4 | — (no core labels) | 4–5/9 unchanged | 1.00 | 0 → 0 |
| ap1c cohort | 11, 11, 12, 11 / 28 → **14, 14, 15, 14 / 27** | 20–22/84 → 28–30/83 | 1.00 → 1.00 | 0 → 0 |
| ap1c dev2 | 4, 5, 5, 5 / 21 → **3, 4, 4, 4 / 21** | 9–10/27 → 8–9/28 | 1.00 → 0.89–0.90 | 0 → **1** (same) |
| ap1c dev3 | 8 / 28 → **8 / 22** | 11/34 → 11/26 | 1.00 → 1.00 | 0 → 0 |
| ap1c dev4 | — | 3–5/9 unchanged | 1.00 | 0 → 0 |

Per item, from the label outcomes (every repetition alike):

- **Q1** NTU Nanyang Global Scholarship: `exists`, `applicability.international`, `.nationality`, `bond`,
  `coverage.living`, `duration`, `renewal` missed → hit; `application_mode` and `degree` → partial (coarser
  readings, D4). Cohort +2 core questions (scholarship, scholarship_international), as the ticket expected.
- **Q2** NTU `english_evidence.sat.minimum` 1250 missed → hit (+1 core question, english) — not wrong scope:
  the label's population is now `international`, which the claim records.
- **Q3** Imperial £47,800: still a hit (the claim records `international`); a Home row can no longer match.
- **Q4** no semester fee in these captures or labels; nothing moved.
- **Q5** **not the movement the ticket expected.** The ticket assumed the pipeline reads 15 January; base2 and
  ap1c read **2027-04-15** from the programme page (3–4 of 4 reps), so the signed gold turns uppsala `deadline`
  hit → wrong value in every repetition that reads it: dev2 known core −1, one wrong claim, precision below
  0.95. The new `deadline.eu_national` label is missed (no claim key reaches it; not critical, outside the
  core questions). A 15 January claim that names no population would be wrong scope too (D1: silence is
  judged), so the deadline reader has to record the round's population, or read the international
  application page first, for this label to be answered. Planner/owner decision; nothing changed here.
- **Q6** Chula's five ISE/ICE labels leave the dev3 denominator (−3 core questions).
- **Q7** ntu, um, ucph, msu prose `gpa` leave the denominators (cohort −1, dev3 −3).
- **Q8** Delft TOEFL stays a hit (its twin URL is now in the label beside the sibling rule).

`scholarship-audit` on Q1 (the labels, read against the NTU award page): Nanyang Global Scholarship — open to
all nationalities (international eligibility stated); bachelor's, full-time; separate application after the
admission application, with a 250-word essay and a teacher's online appraisal; covers subsidised tuition fees
(after the MOE Tuition Grant, whose three-year bond applies to Singapore PRs and international students), a
living allowance of S$6,500 a year, housing up to S$2,000 a year only in NTU hostel residence, travel up to
S$8,000 only for an eligible overseas programme; normal programme duration, renewed at CGPA ≥ 3.5/5.0 each
semester; awarded competitively. Class `FULL_TUITION` (subsidised-tuition basis), not a full ride: meals,
mandatory fees and insurance are not stated as covered. Funding gap not computable from the corpus (no cost of
attendance for the same year). The alias changes only which URL spelling the binding accepts; every value
the claims land on is stated on the page.

## Cycle: FP-1, EF-1, PL-1, DI-1, evidence bundle (SC-2 + QH-1 + AN-1) — 2026-10-18

Runs:
- 39164210866…241246, 20 paired runs: 4 sets, 2 reps per arm.
- Scored on reviewed11/draft2 with the readable denominator.

| Rule | Stable gains | Stable losses | New wrong | Decision |
|---|---|---|---|---|
| FP-1 `--front-page-not-programme` | — | — | 0 | **on**: a precision guard that adds no reads |
| EF-1 `--exact-field-lead-first` | dev4 ctu programme.exists | — | 0 (cohort wrong pages 2/1 on vs 1/1 off) | ctu is on the flaky list (ticket 04), so +2 reps per arm before deciding |
| PL-1 `--provider-lead-floor` | — | — | 0 | **rejected**: no gain, adds reads (01-Q5) |
| DI-1 `--admissions-host-from-homepage` | — | — | 0 | **rejected**: tsinghua not recovered |
| QH-1 + AN-1 | dev2 tcd e3 award exists + international | — | 0 | **on** |
| SC-2 `--coordinated-degree-scope` | — | — | unsw ielts ×2 wrong_scope in 1 rep (value right) | off; sent to a worker to diagnose |

- Uppsala's deadline of 2027-04-15 remains the one dev2 wrong claim in every arm until DL-6 is judged. DL-6 runs were dispatched at 21:33.
- dev4 evidence check (run 39164242896): every quote checked.

## DL-6, EF-1 (+2 reps), scorer acronym fix — 2026-10-18

- **DL-6** `--international-round-deadline`, runs 39168347411…352273.
  - dev2: the uppsala deadline is a stable gain (2027-01-15, population international), and the dev2 wrong claim goes 1 → 0.
  - cohort: a stable loss on ubc:deadline. One on-rep is degraded (4 URLs), and ubc:deadline also shows as a "gain" under EF-1, so it is flaky.
  - No change on dev3 or dev4. 0 over budget.
  - Decision: 2 more reps on cohort (claude-dl6b-cohort) before deciding.
- **EF-1**: combined 4 reps per arm (ef1 + ef1b).
  - cohort: wrong programme pages 2,2 on vs 0,1 off, plus a stable loss on the hku CDS award.
  - dev4: the ctu gain does not repeat.
  - Decision: **rejected**.
- **Scorer**: the university dimension now matches a name that carries the other name's ≥3-letter initials (UNSW Sydney ↔ The University of New South Wales). Re-scoring every saved capture changes only evb-dev3 on#1 (wrong_scope 2 → 0).
  - SC-2's unsw IELTS gain shows in 1 of 2 reps, so it is being re-run (claude-sc2b-dev3).
- **PD-1** `--pdf-evidence-readers` and **PD-2** `--cache-buster-canonical` merged off. Paired runs were dispatched at 21:58.
- **DL-6 on by default.** With 4 reps per arm on cohort (dl6 + dl6b), there is no stable loss: the ubc:deadline loss was noise from a degraded rep. On dev2, uppsala's deadline goes from wrong to a hit, and dev2 precision returns to 1.00.
- **Scorecard `--summary-only`.** Reports aggregates only, for ticket 19.

## PD-1, PD-2, SC-2 (+2 reps); AN-1 regression — 2026-10-18

- **SC-2 on.** Over 4 reps on dev3 (evb + sc2b): unsw ielts.overall and subscores are stable gains, with 0 wrong claims once the scorer acronym fix is in.
- **AN-1 off again.** dev2 shows a new wrong_scope in both arms of the PD runs: uppsala Anders Wall `exists` is scoped **master**. The value is right, but the award section says "Bachelor's or Master's", and the scope reader took the second level.
  - A worker will apply coordinated-degree scope to award sections (AN-1b). AN-1 goes back on after a paired run.
- **PD-1** `--pdf-evidence-readers`: no gain (gold PDFs unreached, as predicted). One stable loss, dev4 boun ielts.subscores, which is suspicious for a PDF-only rule.
  - Left off. This counts as failure 1 of 2 under the PDF map's stopping rule. Diagnosis is cheap and is folded into the next PDF ticket.
- **PD-2** `--cache-buster-canonical`: neutral, 0 gain, 0 wrong. Left off; it is a prerequisite for PD-3 only.
- These runs predate DL-6 being on, which is why uppsala's 2027-04-15 still shows as wrong in both arms.

## Clean baseline 3 (ticket 17), 2026-10-18 22:30

- Runs 39172483236/484697/486984/488858.
- 4 identical reps of today's defaults per set. DL-6, SC-2, FP-1 and QH-1 are on; AN-1 is off.
- Scored with the readable denominator against reviewed11 / dev2.draft2 / dev3.draft2 / dev4.draft2. dev4 is unsigned and scored with --allow-drafts.

| DoD target | cohort | dev2 | dev3 | dev4 | Status |
|---|---|---|---|---|---|
| 1. Precision ≥0.95 | 1.00 | 1.00 | 1.00 | 1.00 | **met** |
| 2. Wrong scope ≤3% | 0 | 0 | 0 | 0 | **met** |
| 3. Programme page on readable sites | 5/8 (0.63) | 4–5/6 | 8/9–10 | 3–4/4–5 | not met; wrong pages 0–2 per rep |
| 4. Readable core ≥80% | 13–14/19 (0.68–0.74) | 6–7/18 (0.35–0.39) | 8–9/18 (0.44–0.50) | 2/9 (0.22) | not met; pooled ≈ 30–32/64 ≈ 48% |
| 5. Budget | 0 over | 0 over | 0 over | 0 over | **met** |
| 6. Heldout within 15 pp | — | — | — | proxy 0.22 | measured only by ticket 19 |

- This matches the ticket 16 forecast: targets 1, 2 and 5 are met; targets 3 and 4 are not met on any set.
- Every remaining loss falls in a class named in RESIDUE_LEDGER_2026-10-18.md.
- Round 3 (ticket 18) is open with the owner.
- **AN-1 + AN-1b on by default** (runs 39173608793…613552).
  - dev2: uppsala Anders Wall `exists` is a stable gain, scoped bachelor.
  - No stable loss and 0 wrong claims on any set.
  - Expected effect on baseline 3: dev2 readable core moves from 7/18 to 8/18.

## Round 3 recorded; heldout acceptance pre-registered (ticket 19, step 1) — 2026-10-18

- Owner (round 3, ticket 18, «все как рекомендовано»): targets 3 and 4 recorded **not met** in the DoD change log with the residue by class (ledger Tables A/B); no measure change; model extractor only as a separate map paired with a reach rule; the acceptance run proceeds; target 6 reads the nine against the **pooled development sets** (primary) and the cohort (secondary).
- Pre-registration, written before any dispatch: `docs/process/HELDOUT_PREREGISTRATION_2026-10-18.md`. Development reference recomputed from the baseline-3 scorecards (`scratchpad/runs/base3-*/sc.json`, pooled over the four sets and sixteen columns): precision 307/307, wrong scope 0/307, over budget 0, programme page on readable 85/112 = 0.759 (0.69–0.79 per column), wrong pages 0–3 per column, core readable 124/255 = 0.486 (0.47–0.50 per column; 128/255 = 0.502 with AN-1 + AN-1b, which are on for the nine), unavailable 4–6 of 44 per column.
- Pre-registered bars on the nine (worst column): precision ≥ 0.95; wrong scope ≤ 0.03; budget 0 over; wrong programme pages 0; programme page on readable expected ≈ 0.71–0.78 (DoD row 1.0 expected not met); core readable expected not met vs 0.80; **target 6 primary: ≥ 0.352** (pooled 0.502 − 0.15); secondary vs cohort: ≥ 0.534 (13/19 − 0.15); dev4 proxy 0.22–0.38; unavailable ≈ 2–3 of 9, 0 pages confirmed on them.
- Dispatch: `benchmark-capture.yml`, `mode=expert_paired`, `case=nu metu sabanci charles masaryk tum tartu polimi vilnius` (the ids, space-separated — `heldout` is not a `--case` value), `extra_args=--through-identity-gate`, `base_args` empty, defaults otherwise (120 s / 60 / parallelism 5), `run_tag=heldout-acceptance-19`. Note: the gate arm acts only on seed-only cases, so on the nine both arms are today's defaults and `identity established` reads 0/0 — recorded in the pre-registration as *not measured*, not changed.
- Scoring: `scorecard <artifact> --dataset evaluation/research/data/heldout.reviewed1.json --summary-only --out summary.json`; the summary is the only thing read. No rule, default, scorer line or corpus line changes in response to the result; a second look only via programme-discovery 21-Q1.
## Signed labels: tickets 09 and 10 (owner «Раунд 2 и 3: все как рекомендовано», 2026-10-18)

- New versions (draft2 files stay frozen): `dev2.draft3.json` (`2026-10-18.dev2-draft3`), `dev3.draft3.json`
  (`2026-10-18.dev3-draft3`), `dev4.draft3.json` (`2026-10-18.dev4-draft3`, every case `human_verified`, reviewer
  Диас) and `identity_bindings.dev4-draft3.json` (the measurement workflow's dev4 extra bindings now point to it).
- Ticket 10, programme pages (13/13 proposal quotes verified by the CI `verify_evidence` run):
  - known: tec, kaznu, uct (related: BA Informatics, BBusSc CS), khalifa (related: ZMU), ntutw, msu, usp (IME and ICMC);
  - taltech: the IT faculty IAIB page added to related;
  - utokyo stays unknown; vut, boun and itu are unchanged.
- Ticket 09, dev4 core (25/25 quotes verified):
  - every drafted label accepted;
  - ktu `gpa` → `unknown`. It is prose, as 02-Q7, and the text is kept in the note;
  - the RWTH Deutschlandstipendium award page (`…/Bildungsfonds-Deutschlandstipendium/~goap/…`) is bound as a
    second source URL of `scholarships.deutschlandstipendium`.
- How the captures were scored: base3 and an1b frozen captures, re-scored read-only with the same scorer and the
  readable denominator. Before = reviewed11 / draft2; after = reviewed11 / draft3. The output files are
  `scratchpad/runs/{base3,an1b}-*/t0910-{before,after}.{md,json}`; `sc.md` and `sc.json` are untouched.
- Award claims were not re-mapped under the new bindings. The captures hold no claim from the RWTH award page:
  it is classifier-rejected, "not an award page".

Results per set, reps off#1 / off#2 / on#1 / on#2:

| run | set | row | before | after |
|---|---|---|---|---|
| base3 | cohort | every row | — | identical (no cohort label changed) |
| base3 | dev2 | programme page on readable | 4/6, 5/6, 5/6, 5/6 | 5/9, 6/9, 6/9, 6/9 |
| base3 | dev2 | wrong programme pages | 1, 0, 0, 0 | 2, 0, 1, 1 |
| base3 | dev2 | hit/wrong/related/missed | 4/1/0/1, 5/0/0/1 ×3 | 6/2/0/2, 7/0/1/2, 7/1/0/2, 7/1/0/2 |
| base3 | dev3 | programme page on readable | 8/10, 8/9, 8/9, 8/9 | 9/13, 9/12, 9/12, 9/12 |
| base3 | dev3 | wrong programme pages | 1, 0, 0, 0 | 1, 0, 0, 1 |
| base3 | dev4 | known core answered (readable) | 2/9 (0.22) ×4 | 2/8 (0.25) ×4 |
| base3 | dev4 | hit/wrong/related/missed | 3/0/1/4, 3/0/0/5, 4/0/1/3, 4/0/1/3 | 3/0/2/4, 3/0/1/5, 4/0/2/3, 4/0/2/3 |
| an1b | cohort | every row | — | identical |
| an1b | dev2 | programme page on readable | 5/6, 4/6, 4/6, 4/6 | 6/9, 5/9, 5/9, 5/9 |
| an1b | dev2 | wrong programme pages | 0, 1, 1, 1 | 1, 2, 1, 1 |
| an1b | dev3 | programme page on readable | 8/10, 9/9, 7/9, 8/9 | 9/13, 10/12, 8/12, 9/12 |
| an1b | dev3 | wrong programme pages | 1, 0, 0, 0 | 1, 0, 0, 1 |
| an1b | dev4 | known core answered (readable) | 2/9 ×4 | 2/8 ×4 |

What did not move:
- Claim precision, wrong claims and readable core on dev2 and dev3: no core label changed there.
- Cohort: no file changed.

New target-3 denominators (readable sites with a known programme page):
- dev2: 6 → 9;
- dev3: 9–10 → 12–13;
- dev4: 4–5, unchanged. Its four unknown cases are adjudicated as related or missed.

Per case, after:
- dev2:
  - kaznu and khalifa are hits in 8/8 reps;
  - tec is missed in 8/8 (the EN twin is read and rejected by the classifier);
  - uct reads `wrong` in 5/8: a page outside the labelled set (in base2 it was the department hub, which is neither programme nor related). In the other 3 it reads related.
- dev3:
  - usp is a hit in 8/8 (ICMC);
  - msu is missed in 8/8 (never returned);
  - ntutw is missed in 6/8 and reads `wrong` in on#2 of both runs (a page that is not the CSIE admissions page);
  - utokyo stays unadjudicated.
- dev4: taltech is related in 8/8 (the faculty page); vut, boun and itu are missed.

| DoD target (base3, worst rep) | dev2 before → after | dev3 before → after | dev4 before → after |
|---|---|---|---|
| 3. Programme page on readable | 0.667 → 0.556 (off), wrong 1 → 2 | 0.800 → 0.692 (off), on wrong 0 → 1 | unchanged |
| 4. Readable core | unchanged | unchanged | 0.222 → 0.250 |

Residue: the new wrong pages go to ticket 16 by name. They are uct (5/8 reps) and ntutw (on#2 of both runs).

## Ticket 19: heldout acceptance run (run 39177612475, 2026-10-18 23:42 UTC; summary only)

- Precision is 0/3. Wrong scope is 3/3.
- Programme page on readable sites: 1/9 (hit/wrong/related/missed = 1/4/0/4).
- Readable known core: 0/23. Any-answer core: 10–11/54.
- 0 over budget. 0 unavailable, 8 REACHED and 1 PARTIALLY_BLOCKED. All four columns are identical.
- Against the pre-registration:
  - targets 1, 2, 3, 4 and 6 are **not met**, and 1, 2 and 3 fall far outside the expected ranges;
  - target 5 is met.
- Per §6, nothing is changed in response. Details are in docs/process/HELDOUT_PREREGISTRATION_2026-10-18.md §8.
- The development-to-heldout gap is the headline finding of this map. Its cause cannot be named without per-case data, and opening that data is the owner's call (21-Q4).

## dev5 blind baseline (run 39203214600, 2026-10-19 05:11; aggregates only, design-blind)

- Programme page 0/7 on readable sites, with 0 wrong confirms. Known core 0/21 readable. Claims 0/2 precise, both wrong scope.
- 2 cases unavailable: kbtu and satbayev (TLS/robots). 0 over budget.
- **The run is invalid as a measurement.** stage_summary shows **discovery_queries = 0** in every column, against about 36 on dev4. No identity-recovery lead was checked, and mean seconds per case were about 28 against about 60. Discovery never searched for dev5 cases, so this looks like a harness wiring defect. It has been handed to a worker, who will debug from code only.
- Rerun after the fix. Ticket 10's pre-registered ceiling still stands: 3/8 confirmable, 0 wrong from related-only cases.
- Dispatched at 05:32: gold-knockout (ticket 07) on cohort, dev2, dev3 and dev4, and the ticket 06 path arms (`--no-registry-seeds`, `--through-identity-gate`) on cohort.

## Search provider outage (2026-10-19, between 23:42 and 05:11 UTC)

- Every Serper call returns `SearchUnavailable (no reason, http 400)`: dev5 baseline 260/260, knockout dev4 180/180.
- The heldout run at 23:42 still had 210–270 search results, so the outage began after it.
- **Every run dispatched from 05:11 is invalid as a measurement:** claude-base-dev5, claude-ko-{cohort,dev2,dev3,dev4}, g06-no-seed and g06-gate.
- The ticket-02 worker's harness-defect hunt correctly found no wiring defect. Its test now guards that dev5 reaches discovery search.
- **Action:** the owner checks the Serper account (credits/key). No further runs are dispatched until search answers again. Recommended harness change: a stage_summary row `search_failures`, plus an abort or flag when more than 50% of discovery queries fail, so an outage never again reads as a pipeline result.

## 2026-10-19 10:40 — recorded-search replay A/A (no provider called, $0)

Owner decision: no scraping; algorithm work after search continues on replayed Serper lists
(`recorded_search.base3.json`, base3 runs of 2026-10-18 22:30). Four `expert_paired` runs with
`search_provider=recorded`, `extra_args` empty (off vs off), dev datasets cohort draft10, dev2/dev3/dev4 draft3.

| set | run | page recall off#1/off#2/on#1/on#2 | wrong pages | unanswered requests per column | stable gains/losses |
|---|---|---|---|---|---|
| cohort | 39236948934 | 4/4/4/4 of 10 | 2/2/2/2 | 9 | 0/0 |
| dev2 | 39236953817 | 6/6/5/6 of 10 | 1/1/1/1 | 22–23 | 0/0 |
| dev3 | 39236958339 | 8/8/8/8 of 14 | 1/0/1/0 | 23–26 | 0/0 |
| dev4 | 39236924796 | 4/4/4/4 of 5 | 0/0/0/1 | 19 | 0/0 |

- Noise floor: replay is close to deterministic. Any difference is one case at most, and no metric is a stable gain or loss in A/A. So a replay paired run can attribute a stable change to the flag.
- Limits:
  - Only discovery queries were recorded. Topic, scholarship and identity searches always miss, so absolute claim and recall numbers are below live; compare arms, not absolutes.
  - A flag whose on arm raises `recorded_search_misses` above the off arm changed the queries and is not measurable on replay. The scorecard target fails in that case.
- Not counted as a paid run: zero Serper credits.

**Correction (10:40 A/A entry):** the cohort A/A above was scored on `ground_truth.draft10`. On the signed
`ground_truth.reviewed11` (the scorecard default) the same artifact reads claim precision 28/28, wrong scope 0/28,
and wrong pages 1 (toronto) in all four columns. Score cohort replays on reviewed11. Plan:
`docs/process/wayfinder/free-search/REPLAY_PLAN_2026-10-19.md`.

## 2026-10-19 11:20 — G-07 gold knockout on replay ($0)

`expert_paired`, `search_provider=recorded`, on arm = `--knockout-gold <dataset>` (the gold page is
unreachable). Cohort scored on reviewed11; dev2/3/4 on draft3.

| set | run | page recall off → on | wrong pages off → on (guesses with gold hidden) | claim precision on |
|---|---|---|---|---|
| cohort | 39241545248 | 4/10 → 0/10 | 1 → 2 | 18/18, 21/21 |
| dev2 | 39241550005 | 6/10 → 0/10 | 1 → 4 | 6/6 |
| dev3 | 39241555623 | 8/14 → 0/14 | 0–1 → 1–2 | 0/0 |
| dev4 | 39241559928 | 4/5 → 0/5 | 0 → 2 | 4/4 |

- The knockout is clean: no gold hit leaked in any on column.
- With the gold hidden, the system confirms a wrong page on 2/10, 4/10, 1–2/14 and 2/5 cases. That is the guess
  rate CH-1 and UA-1 must bring down. dev2 is the worst set.
- Claims stay precise under knockout: the wrong pages yield few claims, and those are scored as correct
  or as other scope.
- Next: CH-1 (`--confirm-head-identity`) and UA-1 (`--abstain-on-unreadable-entry`) replays on all four sets,
  normal and knockout, are running (12 runs).

## 2026-10-19 11:50 — CH-1 and UA-1 on replay (12 runs, $0)

| rule | set | normal: wrong pages off → on | hits lost | knockout: wrong pages off → on | verdict |
|---|---|---|---|---|---|
| UA-1 | cohort | 1,1 → 0,0 (toronto) | 0 | — | gain |
| UA-1 | dev2/dev3/dev4 | unchanged (noise only) | 0 | — | no move |
| CH-1 | cohort | 1 → 1 | 0 | 2 → 2 | no move |
| CH-1 | dev2 | 0,1 → 0,0 (uct now related) | 0 | 4 → 2 (both reps) | gain |
| CH-1 | dev3 | 1,0 → 1,0 | 0 | 2,1 → 2,1 | no move |
| CH-1 | dev4 | 0 → 0 | 0 | 2 → 2 | no move |

- No stable loss and no new wrong claim for either rule. The discovery-miss target was met everywhere.
- **UA-1** meets its plan bar (toronto 1 → 0, nothing else moved). It is now **on by default**, with `--no-abstain-on-unreadable-entry` as the off form.
- **CH-1** has no losses, but its gains (normal and knockout) are only on dev2, the set that motivated it. It misses the plan bar of "knockout guesses down on ≥ 2 sets". It stays **off** and is recorded as seen_site for now. It will be re-tested in a bundle with CQ-1 (combination heads) and SP-1 (sub-page heads), which target the knockout guesses on cohort/dev2/dev4 (docs/process/GOLD_KNOCKOUT_2026-10-19.md).

## 2026-10-19 12:30 — CQ-1, SP-1 and the CH-1+CQ-1+SP-1 bundle on replay (16 runs, $0)

UA-1 is on in every arm, so the knockout off baselines now read cohort 1, dev2 4, dev3 1, dev4 2.
Cells give wrong programme pages per repetition, off#1,off#2 → on#1,on#2.

| arm | cohort | dev2 | dev3 | dev4 |
|---|---|---|---|---|
| bundle, knockout | 1,1 → 0,0 | 4,4 → 1,1 | 1,1 → 0,0 | 2,2 → 1,1 |
| CQ-1, knockout | 1,1 → 0,0 | 4,4 → 4,4 | 2,1 → 1,0 | 2,2 → 2,2 |
| SP-1, knockout | 1,1 → 1,1 | 4,3 → 3,3 | 2,1 → 1,1 | 2,2 → 1,1 |
| bundle, normal: hits | 4,4 → 4,4 | 6,6 → 6,6 | **8,8 → 7,6** | 4,4 → 4,4 |
| bundle, normal: wrong | 0,0 → 1,0 | 1,1 → 0,0 | 1,0 → 1,1 | 0 → 0 |

- With the gold hidden, the bundle cuts guesses on all four sets, from 8 to 2 in total. This is the first change that generalises past the set that motivated it.
- **Blocker:** in normal mode the bundle loses 1–2 gold hits on dev3 (they become related), and cohort on#1 gains one wrong page together with a "queries changed" warning.
- The stable claim "losses" in the knockout arms (ntu programme.exists, tcd English, rwth programme.exists) are claims read from the guessed pages. They are not a regression in normal mode.
- Decision: nothing is flipped yet. A worker is diagnosing the dev3 hit loss and the cohort wrong page per rule, with a generic fix. After that, re-run the bundle on normal + knockout.

## 2026-10-19 13:07 — bundle re-run after the CQ-1 clause fix (8 runs, $0)

Cells are hit/wrong/related/missed per repetition, off#1 | off#2 | on#1 | on#2.

| set | normal | knockout |
|---|---|---|
| cohort | 4/0/1/5 ×4 (no change) | wrong 1,1 → 0,0 |
| dev2 | 5/1 → 5/0 (wrong 1 → 0, hits equal) | wrong 3,3 → 1,1 |
| dev3 | 8/1,8/0 → 8/1,8/0 (uio back to a hit) | 2,1 → 2,1 (uio's specialisation guess returns) |
| dev4 | 4/0 ×4 | wrong 2,2 → 1,1 |

- No gold hit was lost on any set, and there was no stable loss in normal mode.
- Knockout guesses fell on 3 of 4 sets, from 8 to 3 in total.
- Decision: CH-1, CQ-1 and SP-1 go on by default, with `--no-` forms. A worker is doing the flip and checking 11 legacy tests that relied on headless synthetic pages; any real regression stops the flip.

## 2026-10-19 13:52 — new-defaults baseline on replay (UA-1, CH-1, CQ-1, SP-1 on; 8 runs, $0)

| set | normal hit/wrong/related/missed (×4) | knockout wrong | claim recall |
|---|---|---|---|
| cohort | 4/0/1/5 | 0 | 19/83 (same as A/A) |
| dev2 | 6/0/1/3 | 1 | — |
| dev3 | 8/0–1/1/4–5 (one rep 7) | 1–2 | — |
| dev4 | 4/0/1/4 | 1 | — |

- This matches the rp-bundle2 on arm. Normal mode now has 0 wrong programme pages on cohort, dev2 and dev4.
- Cohort claim precision is 20/20 (was 28/28), but recall is unchanged at 19/83. The 8 claims that dropped came from the ntu second-major pages and were never gold keys.
- Remaining gaps:
  - The largest gap is programme pages missed: cohort 5, dev2 3, dev3 4–5, dev4 4.
  - Knockout guesses left: khalifa partner campus, uio specialisation, ctu admissions page.
- Next: CL-2 (unibo gold read as unknown), plus a planner loss-stage analysis of the remaining misses on the new baseline.

## 2026-10-19 14:50 — CL-2, D1 `--skip-refused-hosts` and D2 `--no-stage-budgets` on replay ($0)

Cells show programme pages hit/wrong per repetition, off#1, off#2 → on#1, on#2.

| arm | cohort | dev2 | dev3 | dev4 | knockout wrong | verdict |
|---|---|---|---|---|---|---|
| CL-2 | 4/0 → 4/0, 4/1 | **6/0 → 5/1, 5/1 (new wrong page)** | noise | **4 → 5 (unibo)** | dev2 1→2, dev4 1→2 | **rejected for now**: it adds a wrong page on dev2 and more knockout guesses, and the gain is on dev4 only (seen_site). A worker is diagnosing the dev2 wrong page. |
| D1 skip-refused-hosts | unchanged (one noise column, ubc) | unchanged | noise | unchanged | — | neutral; stays off |
| D2 no-stage-budgets | **4 → 5, 5** | unchanged | wrong 1,0 → 1,0; related 1 → 0 | **4 → 3, 3 (ctu lost)** | — | mixed; stage budgets stay on |

## 2026-10-19 15:00 — QT-1 and CC-1 on replay (16 runs, $0)

Cells show programme pages hit/wrong/related per repetition, off#1, off#2 → on#1, on#2. Columns not listed are unchanged.

| rule | dev3 normal | knockout | verdict |
|---|---|---|---|
| QT-1 `--read-qualifier-twin` | 8/1/1, 8/0/1 → **9/0/0, 9/0/0** (unsw related → hit) | no new guess; cohort stable claim loss `ubc:deadline` | **ubc did not move**, so the plan bar is half met. Kept off pending a diagnosis. |
| CC-1 `--course-lead-guard` | 8/1, 8/0 → **9/1, 9/1** (iitd → hit) | no new guess | It hits the target; the on#2 wrong page still has to be identified (kuleuven flake or CC-1). Kept off pending that check. |

- No hit was lost on any set by either rule.
- A worker is diagnosing why QT-1 did not fire for ubc, the ubc:deadline loss, and the CC-1 wrong page.
- The CL-2 re-run, with the stricter preconditions (d) and (e), is in flight.

**15:20 — CC-1 is on by default.** iitd went from missed to hit in 2/2 runs, no hit was lost, and reads fell on dev3. The only wrong page is kuleuven's known flake, which also appears with the flag off. QT-1b fix: the twin may spend one SB-1b reserve read past the deadline, because ubc's twin was queued but never fetched once the deadline had passed. QT-1 is being replayed again.

## 2026-10-19 15:35 — QT-1b and CL-2b on replay ($0)

- **QT-1b:** ubc moved from related to **hit** in both on reps (cohort hits 4 → 5), with no new wrong page in normal or knockout runs. **However,** `ubc:deadline` is a stable claim loss (recall 19 → 18): the extra twin read on ubc's slow host takes time that TB-1 later needs for the deadline page. The rule stays off. A worker is gating the twin read on TB-1's core reserve. dev3 is still running.
- **CL-2b** (preconditions d+e): no new wrong page on cohort, dev2, dev4 or any knockout set. dev4 unibo is a hit in 1/2 reps, which depends on whether the host answers. The dev3 batch was noisy on the **off** arm too (hits 6, 7 against a usual 8), so it is inconclusive and dev3 has been re-dispatched (rp-cl2c). The rule stays off until then.

## 2026-10-19 16:30 — QT-1c and CL-2c pass on replay ($0)

| rule | normal | knockout | claims |
|---|---|---|---|
| QT-1c (twin read gated by TB-1) | cohort 4 → **5,5** (ubc), dev3 9 → **10,9** (unsw); dev2/dev4 unchanged; 0 new wrong pages | unchanged on all four sets | recall unchanged (ubc:deadline kept) |
| CL-2c (preconditions d+e) | dev4 4 → **5,5** (unibo); cohort/dev2/dev3 unchanged; 0 new wrong pages | unchanged | no stable loss |

Both meet their bars. A worker is flipping them on by default and checking 13 legacy tests that assumed the rules were off. A real regression stops the flip.

Running total since the replay baseline (A/A 10:40), with no paid search:

| set | page hits (A/A → now) | wrong pages, normal | wrong pages, knockout |
|---|---|---|---|
| cohort | 4 → 5 | 1 → 0 | 1 → 0 |
| dev2 | 6 → 6 | 1 → 0 | 4 → 1 |
| dev3 | 8 → 10 | 0–1 → 0–1 | 1–2 → 1–2 |
| dev4 | 4 → 5 | 0 → 0 | 2 → 1 |

The dev3 wrong page is the kuleuven flake.

## 2026-10-19 17:55 — day-end baseline on replay (all seven rules on: UA-1, CH-1, CQ-1, SP-1, CC-1, QT-1, CL-2; $0)

| set | A/A 10:40 hits (wrong) | now hits/wrong/related/missed | knockout wrong, A/A-era → now | claim precision now |
|---|---|---|---|---|
| cohort | 4 (1) | **5**/0/0/5 | 1 → **0** | 19–20/19–20 |
| dev2 | 6 (1) | 6/**0**/1/3 | 4 → **1** | 6/7 |
| dev3 | 8 (0–1) | **10**/0–1/0/3–4 (kuleuven flake) | 1–2 → 1–2 | 11/11 |
| dev4 | 4 (0) | **5**/0/1/3 | 2 → **1** | 5/6 |

- **Total gold programme-page hits went from 22 to 26 out of 39.**
- Wrong pages in normal mode fell from 2–3 to 0–1. The remaining one is the known kuleuven flake.
- Knockout guesses fell from 8 to 3–4.
- Claim recall is unchanged (cohort 19/83). All runs were on the recorded-search replay; no paid query was sent.

### 2026-10-19 SP-2 replay (recorded search v1, 4 sets, ABBA)

`--subpage-requirements-lead` (needs SP-1, on). Cohort, dev2, dev3, dev4: stable gains 0, stable losses 0,
wrong values identical off/on (dev2 uppsala deadline, dev4 unibo programme, both pre-existing). The one
off-column dip on dev3 (5/5 claims) is the A/A noise already recorded (≤1 case). **Verdict: SP-2 stays
off** — no gain on any set; as recorded in HANDOFF §8, ctu's FIT page is not refused by SP-1, so the
lead never reaches it.

## 2026-10-20 01:15 — cycle 14 dispatches (NEXT_CYCLES_2026-10-20 D-F, D-A, D-B; recorded replay, $0)

| item | result | verdict |
|---|---|---|
| D-F no-search floor (`search_provider=none`, columns 1) | hits/wrong/related/missed: cohort 4/0/0/6, dev2 2/0/1/7, dev3 3/0/0/11, dev4 0/0/0/9 → **9/39, 0 wrong** (index-ceiling bar 3/1/6/1 = 11/39; replay with search 26/39) | recorded: the live path beyond the KB finds about a third of the gold pages with no search provider, and never a wrong one |
| D-A LL-1 `--listing-follows-local-aliases` normal | stable gains 0, losses 0 on all four sets; wrong pages unchanged (dev3 off-arm 1 = the kuleuven flake) | **stays off** (as expected; msu unchanged) |
| D-A LL-1 knockout | knockout wrong pages unchanged (cohort 0, dev2 1, dev3 1–2, dev4 1); no stable change | stays off |
| D-B cohort `--no-registry-seeds` normal + knockout | page hits unchanged (4–5/10); **3 stable claim losses** (delft:tuition, ubc major-entrance scholarship + its international applicability) in both modes | H-B partial: registry seeds carry claims (fees/scholarship pages), not programme-page hits, on cohort |

ntu:deadline / SAT / programme.exists stay unstable across arms (known replay noise).

## 2026-10-20 02:20 — cycle 15 (LV-1 replay, first ablations, identity-gate probe; $0)

| item | result | verdict |
|---|---|---|
| LV-1 `--lexicon-language-coverage` normal, 4 sets | stable gains 0, losses 0; on-arm wrong pages 0 (cohort off-arm 1 and dev3 off-arm 1 = known flakes) | **on by default** (bar met: no stable loss, no new wrong page); it fixes the Estonian integrated-study level read |
| LV-1 knockout, 4 sets | knockout wrong pages unchanged (0 / 1 / 1–2 / 1); no stable change | as above |
| D-D ablation `--no-alias-aware-program-match` | stable loss rwth:programme.exists (dev4); others identical | load-bearing, keep |
| D-D ablation `--no-integrated-masters-level` | stable loss uct:ielts.overall (dev2); others identical | load-bearing, keep |
| IG-2 identity-gate probe (CI, no fallback query) | base: cohort 7/10, dev2 8/10, dev3 12/15, dev4 8/9, dev5 7/13 (counts only). Fold + proposed native names: cohort 7/10, dev2 8/10, dev3 12/15, dev4 8/9, **dev5 9/13** | +2 on dev5, no set down; pre-registered 9/9 and 11/11 not met (taltech's homepage title lacks its native name). Native names need the owner's signature on the overlay before the gate can read them |
| LOCO-1 (ticket 08) | H-C confirmed: removing a language's own rows loses 25 % of local-language gold on the store, 28 % on pages; strictly case-made rows explain only uio (+ puc on pages) | the concrete defect is one alias per language in the local query (LQ-2, needs a search key to test); held-out provenance audit of de/it/cs/tr rows started |

Next ablations running: english-readers-v2, fee-readers-v2.

### 2026-10-20 02:55 — D-D ablations, evidence readers ($0 replay)

| ablation | stable losses with the rule off | verdict |
|---|---|---|
| `--no-english-readers-v2` | 8 claims: tcd ielts/toefl/duolingo (4), imperial ielts overall + subscores (2), delft toefl (1); dev4 identical | load-bearing on three sets, keep |
| `--no-fee-readers-v2` | 3 claims: imperial tuition, tcd tuition, ubc deadline; dev4 identical | load-bearing on three sets, keep |

No stable gain on any off arm: neither reader costs development hits or claims. Next: intake-section-deadline, parent-degree-link (dispatched).
| `--no-intake-section-deadline` | 1 claim: auckland deadline (dev3); other sets identical | load-bearing, keep |
| `--no-parent-degree-link` | 6 claims: ubc deadline + ielts overall/subscores (cohort), auckland deadline + ielts overall/subscores (dev3) | load-bearing on two sets, keep |
