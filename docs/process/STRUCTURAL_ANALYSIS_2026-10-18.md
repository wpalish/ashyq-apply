# Structural analysis of the search pipeline — funnel over the current-default captures (2026-10-18)

Analyst: claude-opus-5, read-only (no repo file changed, nothing committed). Inputs: the off arms of
`runs/lx1-cohort/x`, `runs/lx1-dev2/x`, `runs/lx1-dev3/x` (two repetitions per case, 35 cases, 70
captures; off = today's defaults: CL-1, QB-1+QB-1b, FS-1, PG-1, LI-1, DL-3, CU-1, plural-band and sitemap
parser fixes), their `sc.json`, and the gold corpora `ground_truth.reviewed10.json` (cohort, signed),
`dev2.draft1.json`, `dev3.draft1.json`. No heldout file, label or capture was opened. Thirteen public
programme pages were read by hand (eight fetched now into `scratchpad/funnel_pages/`, five already in
`scratchpad/{evpages,fetched,qb1pages}`) for link and offline-extractor checks only; nothing went through
the pipeline. Code at `d3caaf0` (the captures' `pipeline_sha`).

Tooling: `scratchpad/funnel_tools/funnel.py` (run with `python3 -I`) builds the funnel from the captures;
its full output is `scratchpad/funnel_out/FUNNEL.md` (+ `funnel_rows.json`, `funnel_cases.json`) and is
reproduced in the appendices.

**Limits of the evidence.** (1) The trace does not record the provider's result lists, so "seen" means
"read, queued, rejected, listed by the walker, or named as a lead" — a URL the provider returned but
identity recovery never reached is invisible. (2) The log truncates URLs at 120 characters; matching
treats a 120-character logged URL as a prefix. (3) Stage attribution of each read is by position and URL
set (robots/sitemap/confirm queue/walker outcomes/search lines/verify targets), checked by hand against
Groningen, KAIST, TCD, Chula, NTU, Uppsala, Auckland; seconds between reads (parsing, extraction) are
not attributed, so stage seconds sum to 2 261 of the 2 501 s of clock (rep 1).

## 0. Headline

| | cohort | dev2 | dev3 | all |
|---|---|---|---|---|
| known core labels (label level) | 31 | 24 | 31 | **86** |
| hit (rep 1) | 6 | 1 | 1 | 8 |
| lost: **gold page never seen** | 20 | 14 | 30 | **64 (74 %)** |
| lost: seen, not fetched | 2 | 1 | 0 | 3 |
| lost: fetched, **rejected by classifier/scope** | 1 | 6 | 0 | 7 |
| lost: accepted, nothing extracted | 1 | 1 | 0 | 2 |
| lost: value extracted but another value | 1 | 1 | 0 | 2 |
| known core *questions* answered (scorecard) | 6/28 | 1/21 | 1/28 | **8/77** |

By question (rep 1, 86 labels): english 21 known → 4 hit, 11 never seen, 4 rejected, 2 other value;
gpa 4 → 0 hit; deadline 13 → 2 hit, 8 never seen; cost 6 → 2 hit; scholarship 21 → 0 hit (20 never
seen, 1 rejected); scholarship_international 21 → 0 hit (same).

Where the clock goes (rep 1, 35 cases, 2 501 s, 879 network reads at log level):

| stage | seconds | share | reads | queries | what it bought |
|---|---|---|---|---|---|
| robots + sitemaps | 451 | 18 % | 195 | – | programme candidates on 6 sites; 0 kept on 14 sites |
| confirm + navigation + walker | 663 | 27 % | 257 | – | 7 programme pages confirmed by the walker (delft, groningen, vienna, psaclay, tcd×3) |
| discovery search (queries, 3 hop roots, identity recovery) | 785 | 31 % | 264 | 140 | **18 pages confirmed from 318 recovery reads** (5.7 %); 80 hop-root reads bought nothing |
| requirements (topic queries, programme/admissions/topic pages, leads) | 157 | 6 % | 66 | 34 | all 8 hits |
| costs adapter | 23 | 1 % | 16 | – | delft tuition (seed) |
| scholarships (award query, indexes, award pages) | 182 | 7 % | 81 | 11 | **0 known scholarship labels in 42** |
| unattributed (parsing, extraction, waits) | 240 | 10 % | – | – | |

- **51 % of all wall clock is spent before the first query** (1 266 of 2 501 s; median per case 44 %;
  cohort 46 %, dev2 45 %, dev3 56 %). Imperial and UNSW never reach a query at all.
- **Discovery takes 85 % of the clock and 83 % of the reads; the three evidence stages together get
  15 % of the clock.** 10 of 35 cases never reach the verify stage (ubc, uba, kaznu, imperial, unsw,
  ntutw, kuleuven, msu, usp, ub); 19 more reach it with fewer than 25 s left. The budget is 6/60/120 per
  university, but no stage has a budget, so the first stages consume whatever they can.

## 1. Per case: programme page, timing, where the clock went

Full per-case stage table (seconds/reads/queries per stage, both repetitions) in Appendix A; stage
timelines in Appendix C. Condensed view (rep 1; "t_q1" first query, "t_v" verify start):

| set | case | gold prog page hit | our programme page | core known | t_q1 | t_v | clock | what decided it |
|---|---|---|---|---|---|---|---|---|
| cohort | groningen | Y | rug.nl/bachelors/computing-science | 3/5 | 60 | 70 | 100 | walker 10 reads/31 s + nav 17 reads; 2 scholarship labels never seen (index read, "0 award links") |
| cohort | delft | Y | tudelft.nl/…/bachelor-of-computer-science-and-engineering | 2/3 | 18 | 26 | 45 | seeds; deadline is on "Selection procedure" sub-page, linked from the programme page, never followed |
| cohort | aalto | – | – | 0/2 | 12 | 22 | 22 | robots.txt unreachable → every read refused |
| cohort | vienna | Y | aufnahmeverfahren.univie.ac.at/en/computer-science | 0/0 | 25 | 33 | 56 | no known core label |
| cohort | warsaw | Y | informatorects.uw.edu.pl/…/S1-INF | 0/2 | 25 | 52 | 91 | scholarship gold on bpm./monitor.uw.edu.pl (never touched); 7 award reads on welcome.uw.edu.pl (29 s) |
| cohort | ubc | – (killed) | – | 0/4 | 87 | – | 115 | you.ubc.ca 5–15 s/read: 15 nav/walker reads = 78 s before the first query; programme page read at t=99 inside recovery, killed at 115 before `_apply` |
| cohort | toronto | – | – | 0/2 | 9 | 26 | 29 | HTTP 403 on every future.utoronto.ca page |
| cohort | hku | – | cs.hku.hk | 0/3 | 16 | 58 | 68 | admissions.hku.hk robots unreachable; 8 sitemap docs (13 s), hop roots 16 s |
| cohort | ntu | Y | ntu.edu.sg/…/bachelor-of-computing-in-computer-science | 1/5 | 23 | 23 | 65 | slots full → 3 topic queries; gpa page fetched+accepted, value not extractable; nanyang award 2 hops under the linked scholarships index, never reached |
| cohort | kaist | – | – | 0/3 | 21 | 57 | 59 | admission.kaist.ac.kr robots-refused from the runner; 16 recovery reads on lab pages |
| dev2 | ethz | Y | ethz.ch/…/computer-science.html | 0/2 | 13 | 29 | 45 | programme page has no admission/funding link; award query → excellence scholarship (not gold) |
| dev2 | psaclay | – (twin) | …/licence-undergraduate-programme/informatique | 0/0 | 40 | 52 | 70 | no known core label |
| dev2 | uppsala | Y | uu.se/en/study/programme/bachelors-programme-computer-science | 1/5 | 14 | 35 | 50 | deadline (15 April 2027) and SEK 450 000 are on the accepted programme page, not extracted (two-window guard, EX-2 off) |
| dev2 | tcd | Y | tcd.ie/courses/undergraduate/courses/computer-science | 0/6 | 52 | 52 | 101 | gold English page fetched by topic search → `unknown` → rejected; gold fee page linked from programme page, never followed; e3 scholarships page fetched → "beyond the index budget" |
| dev2 | tsinghua | – | – | 0/3 | 12 | 36 | 37 | answers on international.join-tsinghua.edu.cn (other registrable domain) |
| dev2 | tec | – | – | 0/3 | 24 | 64 | 65 | Spanish SPA; walker 13 reads/14 s + 16 recovery reads |
| dev2 | uba | – | – | 0/2 | 41 | – | 74 | walker 9 reads/23 s, 16 recovery reads; answers on extension.uba.ar |
| dev2 | kaznu | – | – | 0/2 | 6 | – | 59 | 16 recovery reads (53 s incl. 22 s hop roots); gold on welcome.kaznu.kz/ru |
| dev2 | uct | – | sit.uct.ac.za/… | 0/1 | 58 | 78 | 108 | 12 sitemap docs (21 s), walker 15 reads/30 s; gold English page fetched by topic search → `unknown` → rejected |
| dev2 | khalifa | – | – | 0/0 | 30 | 38 | 38 | robots.txt timeout → refused |
| dev3 | imperial | – (killed) | – | 0/5 | – | – | 115 | 4 confirm reads on fee tables/wrong pages (23 s), 15 nav/walker reads (73 s) at 4–6 s each; **no query ever sent**; its programme page links to all 5 gold answers |
| dev3 | unsw | – (killed) | – | 0/3 | – | – | 115 | 5 sitemap docs 49 s + 7 confirm reads 62 s at 10 s/read; no query |
| dev3 | utokyo | – | – | 0/3 | 47 | 77 | 81 | Japanese pages/PDF; 16 recovery reads |
| dev3 | ntutw | – | – | 0/1 | 18 | – | 54 | admissions.ntu.edu.tw reachable (2 ok reads) but no programme page → verify never runs (topic search needs `program.url`) |
| dev3 | um | Y | study.um.edu.my/…-computer-system-and-network | 0/2 | 16 | 39 | 61 | page states "IELTS (Academic) 5.5 TOEFL iBT 46": TOEFL extracted (46, correct, scored as miss — unmapped key), IELTS not extracted |
| dev3 | kuleuven | – | – | 0/0 | 15 | – | 42 | connection drops |
| dev3 | auckland | Y (rep1) | study.auckland.ac.nz/…/plan?p7_code=COMP-BSc | 1/4 | 49 | 70 | 112 | 18 nav/walker reads 30 s; English hit via topic page; 17 scholarship reads (29 s) → 13 "index beyond budget", 0 awards |
| dev3 | ucph | Y | ku.dk/… | 0/1 | 56 | 64 | 79 | 12 sitemap docs (19 s), 18 nav reads (26 s); **IELTS 6.5/TOEFL 83 claimed from the master's language page** (scope says degree=master) |
| dev3 | msu | – | – | 0/3 | 12 | – | 45 | Russian PDFs on cpk.msu.ru |
| dev3 | iitd | – | – | 0/0 | 16 | 47 | 51 | no known core label |
| dev3 | puc | – (false positive) | ing.uc.cl/publicaciones/… | 0/1 | 29 | 87 | 108 | 11 recovery reads 40 s; Spanish-only admission calendar |
| dev3 | uio | – | – | 0/0 | 61 | 80 | 83 | 6 sitemap docs 14 s + 8 confirm reads 11 s; no known core label |
| dev3 | usp | – (killed) | – | 0/2 | 52 | – | 99 | 12 nav/walker reads 32 s + 13 recovery reads 45 s; `CAPTURE_IN_PROGRESS` |
| dev3 | ub | – | – | 0/0 | 28 | – | 47 | Cloudflare challenge |
| dev3 | chula | Y (math.sc BSc) | math.sc.chula.ac.th/program/undergraduate/computer-science | 0/5 | 51 | 85 | 114 | 13 sitemap docs (26 s), walker 17 reads 18 s; gold is another programme (ISE) on another host |

## 2. Per core question: the funnel (Appendix B has all 86 labels, both repetitions)

Grouping the 78 missed labels by the *earliest* lost stage and by what would have been needed:

| class | labels | cases (labels) | nature |
|---|---|---|---|
| A. gold page on a reachable host, never seen; **linked from the confirmed or gold programme page** | 15 | ubc 4, imperial 5, tcd cost 1, delft deadline 1, auckland english-link-only(hit), ntu scholarships via index 3 (2 hops), ucph gpa 1 (variant URL) | reachable by one or two official links; the programme page must be confirmed early enough (ubc, imperial) or its links followed (tcd, delft, ntu, ucph) |
| B. gold page on a reachable host, never seen, **not linked from the programme page** | 15 | groningen scholarships 2, uppsala scholarships 2, ethz 2, tec 3 (Spanish page), kaznu 2 (Russian), utokyo 3 (Japanese), um 3 (sibling page; values also on ours), auckland deadline 1 (gold BSc page) | needs a query per question or a local-language identity; um needs only extraction |
| C. **fetched, rejected** by page type or budget | 7 | tcd english 3 (`unknown`), uct english 1 (`unknown`), tcd scholarships 2 ("index beyond the index budget"), delft deadline 1 (rejected as a programme candidate; verify never followed it) | routing: the page was in hand |
| D. fetched and accepted, **value not extracted** / other value | 4 | uppsala deadline (two windows), ntu gpa (prose), ntu sat (other value; key unmapped), uppsala toefl (key unmapped) | extraction + measurement |
| E. seen, **not fetched** | 3 | aalto 2 (robots), tcd cost 1 (walker lead "short_label") | access / lead scoring |
| F. host or programme **unreachable or disputed** | 34 | toronto 2 (403), aalto (robots), kaist 3 (admission host robots), hku 3 (admissions robots; cds host reachable), tsinghua 3 (other domain), uba 2, msu 3, usp 2, puc 1, ntutw 1, chula 5 (other programme), warsaw 2 (bpm/monitor hosts), unsw 3 (killed; scholarships host) | site access (12), local language (9), DI-1-type host (3), gold identity (5), killed before search (3), other host (2) |

Three mechanism findings that are new relative to the earlier analyses:

**F1 — the evidence stage routes a page by its *type*, not by the *question* it was fetched for.**
`web_requirements.verify` queues topic pages as `_Target(url, UNIVERSITY_ADMISSIONS, topic=…)` with
`language_follow=False` and `fee_follow=False`; the loop then hits `if not page.accepts("requirements")`
and `continue`s for every page the classifier does not call a requirements page. Consequences in these
captures (Appendix D lists the verify reads of all 16 cases that reached topic search):
- The **fees query returned a plausible fee page in 12 of 16 cases** (rug.nl financial-matters, Delft
  tuition-fee-finances, Vienna tuition-fee, Warsaw application-and-tuition-fees, ETH tuition-fees, Uppsala
  tuition-fees, Paris-Saclay tuition-fees, UCPH application-deposit-fee-and-tuition-fees, Chula
  tuition-and-fees, UM faq, Auckland international-student-fees, TCD fee-finances) and **every one was
  rejected "classified as costs; no requirement can be read from this kind of page"**; `extract_costs`
  never ran on them, and `WebCostAdapter.fetch` reads only `candidate.costs_url` (a seed/sitemap URL —
  Chula's was `about/feedback`). Zero tuition claims come from topic search today; Delft's tuition hit is
  the seed.
- The **English query returned the right page in 7 of 16** (Groningen via a language lead, Delft, NTU,
  Uppsala, TCD, UCT, Auckland) and the pipeline converted 5; **TCD's and UCT's gold English pages were
  fetched in both repetitions and rejected as `unknown`** ("no decisive signals"). The structural IELTS
  table reader that runs "whatever type it reads as" exists, but only for `language_follow` leads.
- The *deadline* topic query is never sent: the reserve of 3 leaves 2 topic queries + 1 award query.

**F2 — the confirmed programme page already links to most of the missing answers, and nothing follows
those links unless their text matches two regexes.** Hand check of the pages (Appendix E): Imperial's
`2027/computing-beng` links "English language requirements" (gold), "Imperial Inspires scholarships" (gold
award) and states "Application deadlines – Wednesday 13 January 2027" and "Overseas fee 2027 entry
£47,800 per year" (both gold values) in its own text; UBC's programme page links "English language
competency", "Dates and deadlines" and "Scholarships and awards for international students" (all three
gold pages); Auckland's BSc page links the gold English page and the scholarships index and states
"Semester One 2027 8 December 2026"; TCD's course page links "Fees" (gold tuition page) and "English
language requirements … here." (gold); Delft's links "Selection procedure" (gold deadline page); NTU's
links the undergraduate scholarships index (gold award is one hop below) and "Tuition Fees"; UCPH's links
"Quota 1 and quota 2" (gold gpa page variant) — and "Language requirements" pointing at the **master's**
page, which the current defaults followed and claimed from (`ielts.overall 6.5`, `toefl 83`, scope
`degree: master`, for a bachelor request; unlabelled so not counted as wrong). ETH's and KAIST's pages
link nothing useful; Uppsala's and UM's state the values in their own text.
`_route_links`/`_language_links` fire only on "dates & deadlines / application deadline / key dates",
"international diploma / non-Dutch / foreign diploma", and "English/IELTS/language" link text; "Selection
procedure", "Fees", "Scholarships and awards" are not followed (HL-1, off, adds fees/scholarships).

**F3 — discovery has no stop condition and no stage budget.** After the walker confirms a page
(Groningen t=35, TCD t=36) the run still spends: Groningen 6 more nav/walker reads (14 s), 3 queries,
3 recovery reads (6 s); TCD 11 more nav/walker reads (29 s). Hop entry roots cost 80 reads/160 s for
nothing confirmable (roots are rejected). On slow hosts the order (sitemaps → nav → confirm → walker →
search) is fatal: UBC spends 78 s on 15 navigation reads before its first query and reads its programme
page at t=99 inside recovery; Imperial spends 96 s on 19 confirm/walker reads of fee tables and chemistry
department pages and never queries; UNSW spends 111 s on 12 reads. These three cases hold 12 known core
labels. SO-1 (search first on slow hosts) was measured "off: no effect" because, with the walker and
sitemap still unbounded, the saved seconds were spent elsewhere, and because Imperial's programme page
is then lost at the classifier (F4).

**F4 — precision defects that any structural change will expose, found offline on the gold pages:**
- Imperial's programme page classifies as `scholarship_index` under the defaults (funding gate on every
  heading; LX-1 scopes it to h1/title: `page_classifier.py` L648–654). With the gate fixed, the deadline
  reader (`extraction.py` L393, `_deadline_v2` L888) takes the **TMUA test window** ("Test window 2:
  8 January 2027 Booking windows…") → `2026-09-28`, exactly the LX-1 wrong claim; the real sentence is
  "Application deadlines – Wednesday 13 January 2027 at 18.00". LX-1 was rejected for a deadline-reader
  defect, not a lexicon one.
- Auckland's BSc page yields `ielts_min_subscore 5.5` but not `ielts.overall 6.0` from "Score required
  6.0 No bands less than 5.5" (table framing); its deadline table (Summer School / Semester One / Semester
  Two) trips the several-windows guard.
- Uppsala's accepted programme page yields only `intake_term`: the deadline sits in two accordions
  (15 April 2026 / 15 April 2027) and the tuition in "Total tuition fee: SEK 450,000"; EX-2 was measured
  before CL-1 made the page acceptable and should be re-measured.
- UCPH: a lead to a master's page is followed for a bachelor request (no degree guard without HL-1) and
  its claims are filed although `read_scope` records `degree: master`.

**F5 — measurement gaps that hide real answers.** `evaluation/research/mapping.py` maps
`ielts_min_overall`, `ielts_min_subscore`, `sat_*` only; `toefl_min_total`, `duolingo_min` become
`unmapped.*` and can never hit `english_evidence.toefl_ibt.minimum` / `.duolingo.minimum` (9 known labels:
delft, uppsala, tcd×2, tec, um, chula×2; NTU's `english_evidence.sat.minimum` vs mapped `sat.minimum`).
UM's **correct TOEFL 46** is scored as a miss today. A killed capture has no `.raw.json` (access
`unknown`), no `programme_urls` (UBC read its programme page), and the per-stage clock is not in telemetry.

## 3. Three structural changes, ranked by expected known core answers

The ceiling matters: of the 69 unanswered known core questions, roughly 22 sit behind site access from
the measurement network (toronto, aalto, kaist, hku, khalifa, kuleuven, ub, tsinghua's host), 12 behind
local-language-only pages (puc, kaznu, msu, utokyo, uba, tec), 5 behind gold identity disputes (chula,
auckland deadline), and a handful behind extraction of prose values (ntu gpa, ucph gpa). The three
changes below address the ~30 that are on reachable English pages the run can name; together they are
expected to move known core answered from 8/77 to roughly 20–30/77 on this network, not to 80 %.

### Change 1 — Stage budgets and a stop condition for discovery (flag `--stage-budgets`, `STAGE_BUDGETS`)

Design (`live_discovery._discover_one`, `runner._stage_discover`, `fetching.Fetcher` for the per-host read
clock; constants in one `StageBudget` dataclass passed down, recorded in the trace as `stage_order` and
`stage_seconds`):
1. **Discovery deadline and read cap**: `DISCOVERY_DEADLINE_SECONDS = 55`, `DISCOVERY_READ_CAP = 28`
   (of 60); every stage checks `budget.remaining()` before each read and the stage order is cut, never a
   read interrupted. The evidence stages therefore always keep ≥ 60 s and ≥ 30 reads.
2. **Stop when confirmed**: once `selected[PROGRAM_PAGE]` holds a confirmed page (walker, confirm or
   pass-1 recovery), skip the walker's remaining descents, send no second pass, open no hop roots, and
   cap recovery at the existing `PRECONFIRMED_RECOVERY_CHECKS = 3` (already the QB-1b rule — extend it to
   the walker).
3. **Cost-aware order** (SO-1's `HostCost`, already built): when the first three reads average ≥ 5 s or
   robots asks a crawl delay, run search (0 reads, ~1 s/query) immediately after the first sitemap
   document, cap sitemap documents at 3, skip navigation and the walker; otherwise today's order.
4. **Hop entry roots off** when any programme candidate exists (`hop_entry_points=0`); roots were 80
   reads/160 s for 0 confirmations in rep 1.
5. **Per-host read clock**: a host whose median read exceeds 8 s gets at most 6 discovery reads.

Expected gains (funnel evidence): UBC — programme page confirmed by ≈ t=45 instead of read at t=99 and
lost; verify then follows its "English language competency" and "Dates and deadlines" links (the gold
pages; UBC IELTS 6.5/6.0 and 2027-01-15 were hits in the CL-1 run when you.ubc.ca answered) → **+2
questions** (english, deadline), +2 more with Change 3. UNSW — gold programme page is the first confirm
read once the sitemap stage is capped (DEV3 analysis: score 28, sorts first) → topic/link English page →
**+1**. Imperial — a query at ≈ t=20 s instead of never; conditional on the LX-1 funding-gate scope and
the deadline-reader fix (F4) → english via link +1, deadline +1, cost +0–1 → **+1 to +3**. ntutw — with
Change 2's confirmation-independent evidence stage, the reachable admissions.ntu.edu.tw deadline page can
be queried → +0–1. Chula, Auckland, UCT, Puc, TCD gain 30–50 s of evidence window (no label changes by
themselves). Total: **+3 conservative, +7 optimistic**; reads −60 to −100 per set.

Precision risks: none from ordering alone (same confirm predicate); the risk is *fewer* programme pages
where the walker found what search cannot (SO-1 lost TCD's page in one pair before CL-1) — the stop
condition only fires after a confirmation, and the slow-host branch keeps the sitemap's first document
and the confirm stage, so TCD's walker route still runs on fast hosts. Measure: paired run on all three
sets; required: programme_page_recall no stable loss, `cases_over_budget` 0, `verify_reached` 35/35 for
reachable hosts (add it to the scorecard from `stage_seconds`), stable gains ubc:ielts.overall,
ubc:deadline, unsw:ielts.overall.

### Change 2 — A question-driven evidence stage: official links first, one query per question, routing by question, independent of programme confirmation (flag `--question-routing`, `QUESTION_ROUTED_EVIDENCE`)

Design (`web_requirements.verify` → a new `evidence_plan(candidate, program)` + `route(page, target)`;
`web_costs`/`web_scholarships` take targets from the same plan):
1. **Targets per question**, built in this order and capped at 2 reads per question: (a) links on the
   confirmed programme page (and on `admissions_url`) whose text or last path segment names the question —
   English/IELTS/language; fees/tuition (not application fee/waiver); deadline/dates/apply/selection
   procedure/how to apply; scholarships/financial aid/funding — each passed through
   `names_other_degree_level(url)` **and** a link-text level guard (`_OTHER_LEVEL_TEXT`), so UCPH's
   "Language requirements → /masters/" is dropped; (b) one topic query per unanswered question — english,
   fees, **deadline** (today never sent) — which means the award query moves into this plan and the
   reserve stays at 3+3; (c) sitemap/navigation service URLs already in `selected`.
2. **Route by question, not page type**: a target fetched for *english* goes to the structural IELTS
   table reader + `extract_requirements` whatever `classify_page` says (the `language_follow` exemption,
   generalised), still under verbatim, official-domain, FS-1 faculty scope and the FS-2 other-programme
   guard; a *fees* target goes to `extract_structured_costs`/`extract_costs` with TY-1 year selection and
   becomes `candidate.costs_url` when none is set; a *deadline* target goes to the deadline reader; a
   *scholarships* target becomes `candidate.scholarships_url`. A page still yields nothing when its own
   degree level (classifier or `read_scope`) names another level — **withhold any claim whose read scope
   says `degree != request`** (UCPH).
3. **Independent of programme confirmation**: when no programme page is confirmed but the institution's
   site identity is established (homepage read, same registrable domain), the plan still runs its (b) and
   (c) generators at `UNIVERSITY_ADMISSIONS` specificity, so university-wide English/deadline/fee pages are
   read (ntutw, kaist-type cases on reachable hosts). Programme-specific claims stay unavailable; the
   university-level ones are what the gold holds for english in 11 of 21 labels.

Expected gains (funnel rows): TCD english (gold page fetched twice, rejected `unknown`) **+1**; UCT
english (same) **+1**; TCD cost (gold "Fees" link on the programme page; expert read the 2027/28 row;
TY-1 picks the year) **+1**; Uppsala deadline (page accepted; needs EX-2's window-year rule in the deadline
reader) **+1**; UM english (IELTS "(Academic) 5.5" on the accepted page: extractor gap; or the TOEFL 46
already extracted, once mapped) **+1**; Delft deadline ("Selection procedure" link; date format unknown)
+0–1; ntutw deadline (+0–1, with 3.); Imperial english +1 and UNSW english +1 when Change 1 reaches their
pages (counted there); UBC english/deadline (counted in Change 1). Fee pages: 12 cases would yield tuition
claims for the "core questions answered" line, but only Imperial's and TCD's are *known* labels. Total:
**+5 conservative, +8 optimistic**, overlapping Change 1 on ubc/imperial/unsw.

Precision risks and guards: (i) university-wide pages speaking for another faculty — FS-1 stays;
(ii) another programme's own page — FS-2 but scoped (it cut Auckland's English page: apply it only to
`program_detail` pages whose subject names a *different field*, not to requirement pages); (iii) wrong
level — URL and link-text level guards plus the read-scope degree check; (iv) deadline reader taking
test/booking windows (Imperial) — add a negative context for "test window / booking / register for the
test / results released" and prefer the sentence that names "application deadline(s)" (DL-2's
`_DATE_FIRST_DEADLINE` already prefers "Applications due"); (v) fee pages with several populations —
TY-1 and `_tuition_by_population` already keep the highest row and the range. Measure: paired run, all
three sets; required: 0 new wrong claims, stable gains tcd:ielts.overall, uct:ielts.overall, tcd:tuition,
uppsala:deadline; watch `other_scope_claim_rate` (faculty pages) and the unlabelled list for master's-page
claims (ucph). Prerequisite measurement fix: map `toefl_min_total`→`english_evidence.toefl_ibt.minimum`,
`duolingo_min`→`english_evidence.duolingo.minimum`, `sat_min_total`→ also `english_evidence.sat.minimum`
where the corpus uses that key, so the scorer can see them (UM +1 immediately).

### Change 3 — Scholarship discovery as its own route: programme page → scholarships index → named award (flag `--award-route`, `AWARD_ROUTE`)

Today 0 of 42 known scholarship labels; 40 gold award pages never seen; the funding stage spent 81 reads
and 182 s (rep 1) on indexes "beyond the index budget", news, PDFs, `massmailer.univie.ac.at` tracking
links and `study/country/lesotho`. Design (`web_scholarships.find`, `_award_links`, `_search_awards`):
1. **Index from the programme page or admissions hub first** (Change 2's scholarships link: UBC, Imperial,
   Auckland, NTU, TCD-international all link one), then `selected[SCHOLARSHIPS]`, then the programme page
   as today.
2. **Index budget by shape, not by count**: `_MAX_INDEX_PAGES = 3` is spent on the first three indexes
   in link order; instead rank sub-indexes by the request — `international`, `undergraduate|bachelor`,
   `entrance|first-year` in text or path first — and allow up to 5 index reads when each read yields new
   award links (Auckland: `scholarships-for-international-students` and `undergraduate-scholarships` were
   both "beyond the index budget"; NTU: `nanyang-scholarship` is one hop under the linked index; TCD's
   `e3/education/scholarships` was reached and refused for the same reason).
3. **Award query rewritten and filtered**: `site:{domain} scholarship international (bachelor OR
   undergraduate) eligibility benefits` returned tracking links, PDFs, posts; send instead
   `{institution} scholarships international undergraduate students` plus the ontology's "award page"
   shape filter (PG-1 style: no `/news/`, `/posts/`, `.pdf` unless no HTML candidate, no third-party
   redirectors), and read at most 3 results as *indexes or awards*, not as leads of leads.
4. **Exists + international applicability from the award page's own eligibility sentences** (the two
   core keys), with `_DOMESTIC_ONLY`, population restrictions ("students from Belarus") and faculty scope
   as today; an award for another faculty or level (arts.ubc.ca funding; postgraduate indexes) claims
   nothing.

Expected gains: UBC (the linked `scholarships-awards-international-students` page *is* the gold evidence
for both labels) **+2** with Change 1; Imperial (`imperial-inspires-scholarships` linked from the programme
page; gold page is the scholarships-search entry for the same award) **+2** with Change 1 and the gate fix;
NTU (index linked from the programme page → `nanyang-scholarship` one hop down; the Exa-era runs did hit
NTU's award labels) **+1 to +2**; TCD e3 (page reached today) **+0 to +2**; Auckland (pong-tams-ko sits
under `find-a-scholarship`, 2–3 hops) +0–1; Groningen (`/education/scholarships` was read as an index with
"0 award links" — `_award_links` kept nothing; nl-scholarship is directly below it) +0–2; Uppsala, ETH
(query-only) +0–2 each; HKU `cds.hku.hk/prospective-students/scholarships/` (host reachable) +0–2. Total:
**+4 conservative, +12 optimistic** (the pairs count two questions each).

Precision risks: award pages are where past wrong claims came from (UBC award-conditional deadline → DL-3;
"students from Belarus"; HKU SPACE continuing education). Guards: applicability only from eligibility
sentences; no award whose page names another degree level or faculty; the index budget never reads a
third-party host; keep `allow_search` tied to a confirmed `PROGRAM_EXISTS`. Measure: paired run on all
three sets (bindings for dev2/dev3 awards are already loaded per `config.txt`); required: 0 new wrong
claims, `wrong_scope_claim_rate` ≤ 0.03, stable gains ubc:scholarships.major_entrance.*,
ntu:scholarships.nanyang_global.exists, tcd:scholarships.e3_*.exists; reads in the funding stage not above
today's 81.

### Not in the top three, and why

- **Local-language query/identity** (puc, uio, kaznu, msu, utokyo, uba, tec: 12 known core questions):
  every one of these needs a Spanish/Russian/Japanese/Portuguese *extractor* (deadline tables, scholarship
  rules, PDFs) after the page is found; LI-1/LX-1 made the identity side cheap but no core value has ever
  been read from a non-English page. Expected gain with queries alone: 0; it is the right fourth project,
  after Change 2 gives it a question-routed extractor to plug into.
- **DI-1 (second admissions host)**: Tsinghua's 3 answers; measured twice with no effect because topic
  search never ran there — it should be re-measured only on top of Change 2's confirmation-independent
  plan.
- **Site access** (toronto, aalto, kaist, hku admissions, khalifa, kuleuven, ub): 10 known questions;
  Track E (Fly runner) is the only lever and is outside the pipeline.

## 4. Measurement changes the loop needs before the next paired runs

1. `telemetry.stage_seconds`/`stage_reads` (robots+sitemap, confirm, walker, search, requirements, costs,
   scholarships) and `t_first_query`, written by the harness at each stage transition; the scorecard then
   prints "verify reached" and "seconds before first query" per case. `funnel.py` is the prototype.
2. Persist the discovery trace and `programme_urls` at the confirm checkpoint, so a kill at 115 s still
   reports what was confirmed (UBC read its programme page; Imperial/UNSW report `unknown (0/0 failed)`).
3. Record the provider's top-10 URLs per query family (public URLs only) so "never seen" can be split
   into "not returned" and "returned, not read".
4. Map TOEFL/Duolingo/SAT claim keys (F5).

## Appendices

Appendix A — per-case stage costs (both repetitions); Appendix B — per-label funnel (86 labels);
Appendix C — stage timelines; Appendix D — verify-stage reads with their diagnostics for the 16 cases
that reached topic search; Appendix E — programme-page link checks. Generated by
`scratchpad/funnel_tools/funnel.py` and the inline scripts of this session.

## Appendix A — per-case stage costs (seconds/reads[/queries] per stage; rep 1 and rep 2)

Columns: s = clock, reads/q = telemetry; t_1st_query / t_verify in seconds; stage cells are seconds/net reads (search and scholarship cells add /queries); nav+walker shows navigation reads + walker reads.

| set | case | access | err | s | reads | q | t_1st_query | t_verify | robots+sitemap s/r | confirm s/r | nav+walker s/r | search s/r/q | req s/r/q | costs s/r | schol s/r/q | killed_in |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cohort | groningen#1 | PARTIALLY_BLOCKED |  | 100.2 | 57 | 6 | 60 | 70 | 8/3 | 0/0 | 31/10+17/7 | 10/3/3 | 12/5/2 | 3/1 | 10/5/1 |  |
| cohort | groningen#2 | PARTIALLY_BLOCKED |  | 102.8 | 57 | 6 | 60 | 72 | 8/3 | 0/0 | 31/10+17/7 | 11/3/3 | 14/5/2 | 3/1 | 12/5/1 |  |
| cohort | delft#1 | REACHED |  | 44.8 | 26 | 5 | 18 | 26 | 5/2 | 0/0 | 2/1+9/7 | 8/3/3 | 9/7/2 | 1/1 | 5/4/0 |  |
| cohort | delft#2 | REACHED |  | 50.0 | 26 | 5 | 19 | 29 | 7/2 | 0/0 | 2/1+9/7 | 7/3/3 | 14/7/2 | 1/1 | 5/4/0 |  |
| cohort | aalto#1 | PARTIALLY_BLOCKED |  | 22.3 | 4 | 6 | 12 | 22 | 10/5 | 0/0 | 0/1+0/2 | 11/10/6 | 0/1/0 | 0/0 | 0/2/0 |  |
| cohort | aalto#2 | PARTIALLY_BLOCKED |  | 23.2 | 4 | 6 | 12 | 23 | 10/5 | 0/0 | 0/1+0/2 | 13/10/6 | 0/1/0 | 0/0 | 0/2/0 |  |
| cohort | vienna#1 | REACHED |  | 56.1 | 40 | 6 | 25 | 33 | 8/5 | 1/1 | 3/3+10/5 | 8/3/3 | 9/4/2 | 6/2 | 8/4/1 |  |
| cohort | vienna#2 | REACHED |  | 55.0 | 41 | 6 | 24 | 32 | 8/5 | 2/1 | 3/3+9/5 | 7/3/3 | 8/4/2 | 6/2 | 8/5/1 |  |
| cohort | warsaw#1 | PARTIALLY_BLOCKED |  | 91.0 | 53 | 6 | 25 | 52 | 6/4 | 0/0 | 0/0+16/7 | 25/8/3 | 10/3/2 | 0/0 | 29/7/1 |  |
| cohort | warsaw#2 | PARTIALLY_BLOCKED |  | 91.6 | 53 | 6 | 25 | 53 | 7/4 | 0/0 | 0/0+17/7 | 25/8/3 | 9/3/2 | 0/0 | 29/7/1 |  |
| cohort | ubc#1 | unknown | BENCHMARK_WALL | 115.0 | 25 | 3 | 87 | None | 6/5 | 0/0 | 78/15+0/0 | 29/5/3 | 0/0/0 | 0/0 | 0/0/0 | search |
| cohort | ubc#2 | unknown | BENCHMARK_WALL | 115.0 | 28 | 3 | 80 | None | 6/5 | 0/0 | 71/15+0/0 | 36/5/3 | 0/0/0 | 0/0 | 0/0/0 | search |
| cohort | toronto#1 | REACHED |  | 29.1 | 29 | 6 | 9 | 26 | 6/5 | 0/0 | 2/1+0/2 | 18/11/6 | 0/1/0 | 2/1 | 2/1/0 |  |
| cohort | toronto#2 | REACHED |  | 24.8 | 29 | 6 | 10 | 22 | 6/5 | 0/0 | 2/1+0/2 | 14/11/6 | 0/1/0 | 2/1 | 2/1/0 |  |
| cohort | hku#1 | PARTIALLY_BLOCKED |  | 67.7 | 28 | 5 | 16 | 58 | 13/9 | 0/0 | 0/1+1/2 | 40/10/3 | 4/2/2 | 0/2 | 6/4/0 |  |
| cohort | hku#2 | PARTIALLY_BLOCKED |  | 53.2 | 29 | 6 | 18 | 49 | 12/9 | 0/0 | 1/1+0/2 | 31/11/3 | 2/2/2 | 0/2 | 3/3/1 |  |
| cohort | ntu#1 | REACHED |  | 65.3 | 27 | 3 | 23 | 23 | 10/5 | 4/4 | 3/2+0/0 | 0/0/0 | 13/6/3 | 2/1 | 4/6/0 |  |
| cohort | ntu#2 | REACHED |  | 60.4 | 27 | 3 | 19 | 19 | 8/5 | 4/4 | 3/2+0/0 | 0/0/0 | 10/6/3 | 2/1 | 5/6/0 |  |
| cohort | kaist#1 | PARTIALLY_BLOCKED |  | 59.0 | 33 | 6 | 21 | 57 | 9/5 | 0/0 | 0/0+10/5 | 36/11/6 | 1/1/0 | 0/0 | 1/1/0 |  |
| cohort | kaist#2 | PARTIALLY_BLOCKED |  | 55.4 | 33 | 6 | 19 | 53 | 8/5 | 0/0 | 0/0+9/5 | 34/11/6 | 1/1/0 | 0/0 | 2/1/0 |  |
| dev2 | ethz#1 | REACHED |  | 44.6 | 24 | 6 | 13 | 29 | 7/5 | 0/0 | 0/0+3/1 | 15/9/3 | 10/3/2 | 0/0 | 5/3/1 |  |
| dev2 | ethz#2 | REACHED |  | 44.5 | 27 | 6 | 12 | 32 | 7/5 | 0/0 | 0/0+3/1 | 19/10/3 | 6/3/2 | 0/0 | 6/3/1 |  |
| dev2 | psaclay#1 | REACHED |  | 69.9 | 38 | 5 | 40 | 52 | 16/8 | 0/0 | 12/8+6/5 | 10/2/3 | 7/2/2 | 4/2 | 5/3/0 |  |
| dev2 | psaclay#2 | REACHED |  | 70.4 | 38 | 5 | 41 | 52 | 15/8 | 0/0 | 11/8+6/5 | 12/2/3 | 8/2/2 | 4/2 | 5/3/0 |  |
| dev2 | uppsala#1 | REACHED |  | 49.6 | 22 | 6 | 14 | 35 | 10/3 | 0/0 | 0/0+1/1 | 20/9/3 | 6/2/2 | 0/0 | 4/2/1 |  |
| dev2 | uppsala#2 | REACHED |  | 47.9 | 21 | 6 | 14 | 34 | 11/3 | 0/0 | 0/0+1/1 | 19/9/3 | 5/2/2 | 0/0 | 3/1/1 |  |
| dev2 | tcd#1 | REACHED |  | 101.0 | 53 | 4 | 52 | 52 | 8/5 | 6/2 | 29/10+5/2 | 0/0/0 | 17/4/3 | 0/0 | 27/8/1 |  |
| dev2 | tcd#2 | REACHED |  | 90.6 | 53 | 4 | 50 | 50 | 8/5 | 6/2 | 29/10+5/2 | 0/0/0 | 10/4/3 | 0/0 | 25/8/1 |  |
| dev2 | tsinghua#1 | REACHED |  | 36.9 | 24 | 6 | 12 | 36 | 8/5 | 0/0 | 0/0+2/1 | 24/10/6 | 1/1/0 | 0/0 | 0/0/0 |  |
| dev2 | tsinghua#2 | REACHED |  | 38.0 | 24 | 6 | 12 | 37 | 7/5 | 0/0 | 0/0+2/1 | 26/10/6 | 1/1/0 | 0/0 | 0/0/0 |  |
| dev2 | tec#1 | REACHED |  | 64.6 | 39 | 6 | 24 | 64 | 6/2 | 0/0 | 0/0+14/9 | 39/11/6 | 0/0/0 | 0/1 | 0/0/0 |  |
| dev2 | tec#2 | REACHED |  | 62.0 | 40 | 6 | 22 | 61 | 5/2 | 0/0 | 0/0+13/9 | 38/11/6 | 0/0/0 | 0/1 | 0/0/0 |  |
| dev2 | uba#1 | PARTIALLY_BLOCKED |  | 73.6 | 35 | 6 | 41 | None | 15/5 | 0/0 | 0/0+23/6 | 32/10/6 | 0/0/0 | 0/0 | 0/0/0 |  |
| dev2 | uba#2 | PARTIALLY_BLOCKED |  | 76.4 | 36 | 6 | 43 | None | 15/5 | 0/0 | 0/0+25/6 | 34/11/6 | 0/0/0 | 0/0 | 0/0/0 |  |
| dev2 | kaznu#1 | PARTIALLY_BLOCKED |  | 58.5 | 29 | 6 | 6 | None | 3/5 | 0/0 | 0/0+1/2 | 53/11/6 | 0/0/0 | 0/0 | 0/0/0 |  |
| dev2 | kaznu#2 | PARTIALLY_BLOCKED |  | 57.5 | 29 | 6 | 2 | None | 0/5 | 0/0 | 0/0+0/2 | 55/11/6 | 0/0/0 | 0/0 | 0/0/0 |  |
| dev2 | uct#1 | REACHED |  | 107.9 | 49 | 6 | 58 | 78 | 21/13 | 2/2 | 1/1+30/15 | 20/6/3 | 6/2/2 | 1/1 | 10/3/1 |  |
| dev2 | uct#2 | REACHED |  | 94.3 | 49 | 6 | 50 | 73 | 19/13 | 3/2 | 2/1+24/15 | 22/6/3 | 6/3/2 | 1/1 | 4/3/1 |  |
| dev2 | khalifa#1 | REACHED |  | 37.6 | 4 | 6 | 30 | 38 | 27/5 | 0/3 | 0/0+0/2 | 9/9/6 | 0/1/0 | 0/1 | 0/1/0 |  |
| dev2 | khalifa#2 | REACHED |  | 37.4 | 4 | 6 | 29 | 37 | 26/5 | 0/3 | 0/0+0/2 | 10/9/6 | 0/1/0 | 0/1 | 0/1/0 |  |
| dev3 | imperial#1 | unknown | BENCHMARK_WALL | 115.0 | 73 | 0 | None | None | 8/4 | 23/4 | 73/16+0/0 | 0/0/0 | 0/0/0 | 0/0 | 0/0/0 | nav_walker |
| dev3 | imperial#2 | unknown | BENCHMARK_WALL | 115.0 | 72 | 0 | None | None | 10/4 | 23/4 | 70/15+0/0 | 0/0/0 | 0/0/0 | 0/0 | 0/0/0 | nav_walker |
| dev3 | unsw#1 | unknown | BENCHMARK_WALL | 115.0 | 13 | 0 | None | None | 49/6 | 62/7 | 0/0+0/0 | 0/0/0 | 0/0/0 | 0/0 | 0/0/0 | confirm |
| dev3 | unsw#2 | unknown | BENCHMARK_WALL | 115.0 | 13 | 0 | None | None | 48/6 | 62/7 | 0/0+0/0 | 0/0/0 | 0/0/0 | 0/0 | 0/0/0 | confirm |
| dev3 | utokyo#1 | REACHED |  | 81.0 | 23 | 6 | 47 | 77 | 16/5 | 0/0 | 0/0+29/3 | 29/10/6 | 4/1/0 | 0/0 | 0/0/0 |  |
| dev3 | utokyo#2 | REACHED |  | 74.3 | 23 | 6 | 41 | 70 | 29/5 | 0/0 | 0/0+10/3 | 28/10/6 | 4/1/0 | 0/0 | 0/0/0 |  |
| dev3 | ntutw#1 | REACHED |  | 53.7 | 25 | 6 | 18 | None | 10/5 | 0/0 | 3/1+4/1 | 36/10/6 | 0/0/0 | 0/0 | 0/0/0 |  |
| dev3 | ntutw#2 | REACHED |  | 34.5 | 25 | 6 | 15 | None | 8/5 | 0/0 | 2/1+3/1 | 20/10/6 | 0/0/0 | 0/0 | 0/0/0 |  |
| dev3 | um#1 | REACHED |  | 61.0 | 19 | 6 | 16 | 39 | 9/5 | 0/0 | 0/0+5/2 | 22/10/3 | 7/3/2 | 0/0 | 14/2/1 |  |
| dev3 | um#2 | REACHED |  | 59.1 | 25 | 6 | 15 | 38 | 9/5 | 0/0 | 0/0+4/2 | 22/11/3 | 6/4/2 | 0/0 | 10/2/1 |  |
| dev3 | kuleuven#1 | REACHED |  | 41.7 | 24 | 6 | 15 | None | 7/5 | 0/0 | 0/0+3/1 | 29/11/6 | 0/0/0 | 0/0 | 0/0/0 |  |
| dev3 | kuleuven#2 | BLOCKED |  | 74.1 | 6 | 6 | 13 | None | 10/5 | 0/0 | 0/0+0/2 | 63/11/6 | 0/0/0 | 0/0 | 0/0/0 |  |
| dev3 | auckland#1 | REACHED |  | 112.2 | 59 | 6 | 49 | 70 | 8/3 | 0/0 | 30/14+0/0 | 19/7/3 | 8/4/2 | 1/1 | 29/17/1 |  |
| dev3 | auckland#2 | REACHED |  | 104.2 | 62 | 6 | 47 | 79 | 7/3 | 0/0 | 30/14+0/0 | 31/11/6 | 1/1/0 | 1/1 | 19/15/0 |  |
| dev3 | ucph#1 | REACHED |  | 79.4 | 50 | 6 | 56 | 64 | 19/13 | 3/2 | 26/18+3/2 | 6/4/3 | 7/5/2 | 0/0 | 3/2/1 |  |
| dev3 | ucph#2 | REACHED |  | 79.1 | 51 | 6 | 54 | 65 | 18/13 | 3/2 | 26/18+3/2 | 9/6/3 | 7/5/2 | 0/0 | 3/2/1 |  |
| dev3 | msu#1 | REACHED |  | 44.9 | 33 | 6 | 12 | None | 9/5 | 0/0 | 0/0+2/1 | 33/11/6 | 0/0/0 | 0/0 | 0/0/0 |  |
| dev3 | msu#2 | REACHED |  | 40.9 | 33 | 6 | 11 | None | 8/5 | 0/0 | 0/0+2/1 | 29/11/6 | 0/0/0 | 0/0 | 0/0/0 |  |
| dev3 | iitd#1 | PARTIALLY_BLOCKED |  | 51.1 | 35 | 6 | 16 | 47 | 9/5 | 0/0 | 2/1+2/1 | 32/9/6 | 1/1/0 | 0/0 | 2/1/0 |  |
| dev3 | iitd#2 | PARTIALLY_BLOCKED |  | 53.5 | 38 | 6 | 16 | 50 | 9/5 | 0/0 | 2/1+2/1 | 35/10/6 | 1/1/0 | 0/0 | 2/1/0 |  |
| dev3 | puc#1 | REACHED |  | 108.2 | 36 | 5 | 29 | 87 | 22/3 | 0/0 | 2/1+3/3 | 56/11/3 | 21/3/2 | 0/0 | 0/0/0 |  |
| dev3 | puc#2 | REACHED |  | 79.6 | 28 | 5 | 24 | 77 | 22/2 | 0/0 | 0/0+0/2 | 52/11/3 | 3/2/2 | 0/0 | 0/0/0 |  |
| dev3 | uio#1 | REACHED |  | 82.8 | 40 | 6 | 61 | 80 | 14/7 | 11/8 | 0/0+7/3 | 20/10/6 | 0/1/0 | 2/1 | 0/1/0 |  |
| dev3 | uio#2 | REACHED |  | 90.1 | 45 | 6 | 60 | 88 | 14/7 | 11/8 | 0/0+7/3 | 28/11/6 | 0/1/0 | 1/1 | 0/1/0 |  |
| dev3 | usp#1 | unknown | CAPTURE_IN_PRO | 98.8 | 49 | 5 | 52 | None | 16/5 | 0/0 | 32/11+0/0 | 45/10/5 | 0/0/0 | 0/0 | 0/0/0 | search |
| dev3 | usp#2 | unknown | CAPTURE_IN_PRO | 95.1 | 49 | 5 | 45 | None | 12/5 | 0/0 | 30/11+0/0 | 48/11/5 | 0/0/0 | 0/0 | 0/0/0 | search |
| dev3 | ub#1 | REACHED |  | 47.4 | 16 | 6 | 28 | None | 26/7 | 0/0 | 0/0+0/2 | 20/9/6 | 0/0/0 | 0/0 | 0/0/0 |  |
| dev3 | ub#2 | REACHED |  | 53.9 | 19 | 6 | 28 | None | 26/7 | 0/0 | 0/0+0/2 | 26/10/6 | 0/0/0 | 0/0 | 0/0/0 |  |
| dev3 | chula#1 | REACHED |  | 114.4 | 66 | 6 | 51 | 85 | 26/13 | 0/0 | 0/0+18/9 | 32/11/3 | 4/3/2 | 2/1 | 19/4/1 |  |
| dev3 | chula#2 | REACHED |  | 107.4 | 72 | 6 | 35 | 75 | 13/13 | 0/0 | 0/0+16/9 | 39/11/3 | 4/3/2 | 2/1 | 21/6/1 |  |


## Appendix B — per known core label: funnel (rep 1 / rep 2)

Stages: S1 seen anywhere (search queue, sitemap, walker, link, confirm queue, rejected list), S2 fetched ok, S3 accepted by classifier/scope, S4 a value for the question extracted (any page), S5 scorecard outcome.

| set | case | question | key | S1 | S2 | S3 | S4(any/gold) | S5 | lost_at | gold url | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| cohort | groningen | english | ielts.overall | Y/Y | Y/Y | Y/Y | YY/YY | hit/hit | hit/hit | www.rug.nl/education/application-enrolment-tuition-fees/admission/non- | fetched-ok:intake_specific_program |
| cohort | groningen | deadline | deadline | Y/Y | Y/Y | Y/Y | YY/YY | hit/hit | hit/hit | www.rug.nl/bachelors/computing-science/ | fetched-ok:intake_specific_program |
| cohort | groningen | cost | tuition | Y/Y | Y/Y | Y/Y | YY/YY | hit/hit | hit/hit | www.rug.nl/bachelors/computing-science/ | fetched-ok:intake_specific_program |
| cohort | groningen | scholarship | scholarships.nl.exists | -/- | -/- | -/- | Y-/-- | missed/missed | 1_never_seen/1_never_seen | www.rug.nl/education/scholarships/nl-scholarship | seen: |
| cohort | groningen | scholarship_international | scholarships.nl.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.rug.nl/education/scholarships/nl-scholarship | seen: |
| cohort | delft | english | ielts.overall | -/- | -/- | -/- | Y-/Y- | hit/hit | hit/hit | www.tudelft.nl/en/education/admission-and-application/bsc-international-di | seen: |
| cohort | delft | deadline | deadline | Y/Y | Y/Y | -/- | --/-- | missed/missed | 3_rejected/3_rejected | www.tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-eng | seen: |
| cohort | delft | cost | tuition | Y/Y | Y/Y | Y/Y | YY/YY | hit/hit | hit/hit | www.tudelft.nl/en/education/study-programme-orientation/practical-matters/ | classifier-rejected:costs; fetched-ok:costs |
| cohort | delft | english | english_evidence.toefl_ibt.minimum | -/- | -/- | -/- | Y-/Y- | missed/missed | 1_never_seen/1_never_seen | www.tudelft.nl/en/education/admission-and-application/bsc-international-di | seen: |
| cohort | aalto | deadline | deadline | Y/Y | -/- | -/- | --/-- | missed/missed | 2_not_fetched/2_not_fetched | www.aalto.fi/en/study-options/computer-engineering-bachelor-of-science-a |  | disc-rejected: search lead unresolved (robots_disallowed) |
| cohort | aalto | cost | tuition | Y/Y | -/- | -/- | --/-- | missed/missed | 2_not_fetched/2_not_fetched | www.aalto.fi/en/study-options/computer-engineering-bachelor-of-science-a |  | disc-rejected: search lead unresolved (robots_disallowed) |
| cohort | warsaw | scholarship | scholarships.rektora.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | bpm.uw.edu.pl/en/rectors-scholarship/ | seen: |
| cohort | warsaw | scholarship_international | scholarships.rektora.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | monitor.uw.edu.pl/Lists/Uchway/Attachments/5978/M.2021.215.Obw.18.pdf | seen: |
| cohort | ubc | english | ielts.overall | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | you.ubc.ca/applying-ubc/requirements/english-language-competency/ | seen: |
| cohort | ubc | deadline | deadline | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | you.ubc.ca/applying-ubc/dates-deadlines/ | seen: |
| cohort | ubc | scholarship | scholarships.major_entrance.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | you.ubc.ca/financial-planning/scholarships-awards-international-studen | seen: |
| cohort | ubc | scholarship_international | scholarships.major_entrance.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | you.ubc.ca/financial-planning/scholarships-awards-international-studen | seen: |
| cohort | toronto | english | ielts.overall | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | future.utoronto.ca/english-language-requirements | seen: |
| cohort | toronto | deadline | deadline | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | future.utoronto.ca/deadlines | seen: |
| cohort | hku | scholarship | scholarships.entrance.exists | -/- | -/- | -/- | Y-/-- | missed/missed | 1_never_seen/1_never_seen | www.admissions.hku.hk/node/891 | seen: |
| cohort | hku | scholarship | scholarships.computing_data_science_entrance.exists | -/- | -/- | -/- | Y-/-- | missed/missed | 1_never_seen/1_never_seen | www.cds.hku.hk/prospective-students/scholarships/ | seen: |
| cohort | hku | scholarship_international | scholarships.computing_data_science_entrance.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.cds.hku.hk/prospective-students/scholarships/ | seen: |
| cohort | ntu | deadline | deadline | Y/Y | Y/Y | Y/Y | YY/YY | hit/hit | hit/hit | www.ntu.edu.sg/admissions/undergraduate/admissions/general-admission-requi | fetched-ok:intake_specific_program |
| cohort | ntu | scholarship | scholarships.nanyang_global.exists | -/- | -/- | -/- | Y-/Y- | missed/missed | 1_never_seen/1_never_seen | www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportuni | seen: |
| cohort | ntu | scholarship_international | scholarships.nanyang_global.applicability.nationality | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportuni | seen: |
| cohort | ntu | english | english_evidence.sat.minimum | Y/Y | Y/Y | Y/Y | YY/YY | missed/missed | 5_extracted_other_value/5_extracted_other_value | www.ntu.edu.sg/admissions/undergraduate/admissions/general-admission-requi | fetched-ok:intake_specific_program |
| cohort | ntu | gpa | gpa | Y/Y | Y/Y | Y/Y | --/-- | missed/missed | 4_not_extracted/4_not_extracted | www.ntu.edu.sg/admissions/undergraduate/admissions/general-admission-requi | fetched-ok:general_admissions |
| cohort | ntu | scholarship_international | scholarships.nanyang_global.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.ntu.edu.sg/admissions/undergraduate/scholarships-and-awards/scholarshi | seen: |
| cohort | kaist | cost | tuition | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | admission.kaist.ac.kr/intl-undergraduate/support/coa | seen: |
| cohort | kaist | scholarship | scholarships.kaist.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/ | seen: |
| cohort | kaist | scholarship_international | scholarships.kaist.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/ | seen: |
| dev2 | ethz | scholarship | scholarships.eth.exists | -/- | -/- | -/- | Y-/Y- | missed/missed | 1_never_seen/1_never_seen | ethz.ch/students/en/studies/financial/scholarships/cost-of-living/i | seen: |
| dev2 | ethz | scholarship_international | scholarships.eth.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | ethz.ch/students/en/studies/financial/scholarships/cost-of-living.h | seen: |
| dev2 | uppsala | english | ielts.overall | Y/Y | Y/Y | Y/Y | YY/YY | hit/hit | hit/hit | www.uu.se/en/study/bachelors-studies/application/entry-requirements | fetched-ok:intake_specific_program |
| dev2 | uppsala | english | english_evidence.toefl_ibt.minimum | Y/Y | Y/Y | Y/Y | YY/YY | missed/missed | 5_extracted_other_value/5_extracted_other_value | www.uu.se/en/study/bachelors-studies/application/entry-requirements | fetched-ok:intake_specific_program |
| dev2 | uppsala | deadline | deadline | Y/Y | Y/Y | Y/Y | --/-- | missed/missed | 4_not_extracted/4_not_extracted | www.uu.se/en/study/programme/bachelors-programme-computer-science | fetched-ok:program_detail |
| dev2 | uppsala | scholarship | scholarships.anders_wall_studies_at.exists | -/- | -/- | -/- | Y-/Y- | missed/missed | 1_never_seen/1_never_seen | www.uu.se/en/study/bachelors-studies/scholarships/uppsala-university- | seen: |
| dev2 | uppsala | scholarship_international | scholarships.anders_wall_studies_at.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.uu.se/en/study/bachelors-studies/scholarships | seen: |
| dev2 | tcd | english | ielts.overall | Y/Y | Y/Y | -/- | --/-- | missed/missed | 3_rejected/3_rejected | www.tcd.ie/study/english-language-requirements/ | classifier-rejected:unknown |
| dev2 | tcd | english | english_evidence.toefl_ibt.minimum | Y/Y | Y/Y | -/- | --/-- | missed/missed | 3_rejected/3_rejected | www.tcd.ie/study/english-language-requirements/ | classifier-rejected:unknown |
| dev2 | tcd | english | english_evidence.duolingo.minimum | Y/Y | Y/Y | -/- | --/-- | missed/missed | 3_rejected/3_rejected | www.tcd.ie/study/english-language-requirements/ | classifier-rejected:unknown |
| dev2 | tcd | cost | tuition | Y/Y | -/- | -/- | --/-- | missed/missed | 2_not_fetched/2_not_fetched | www.tcd.ie/courses/undergraduate/fees/ |  | disc-rejected: navigation lead names none of the applicant's subjects | walker: short_label |
| dev2 | tcd | scholarship | scholarships.e3_balanced_solutions_better.exists | Y/Y | Y/Y | -/- | --/-- | missed/missed | 3_rejected/3_rejected | www.tcd.ie/e3/education/scholarships/ | classifier-rejected:scholarship_index |
| dev2 | tcd | scholarship_international | scholarships.e3_balanced_solutions_better.applicability.international | Y/Y | Y/Y | -/- | --/-- | missed/missed | 3_rejected/3_rejected | www.tcd.ie/e3/education/scholarships/ | classifier-rejected:scholarship_index |
| dev2 | tsinghua | deadline | deadline | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | international.join-tsinghua.edu.cn/Admission1/Schedule.htm | seen: |
| dev2 | tsinghua | scholarship | scholarships.tsinghua_freshmen.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | international.join-tsinghua.edu.cn/Admission1/Freshmen_Scholarships1.htm | seen: |
| dev2 | tsinghua | scholarship_international | scholarships.tsinghua_freshmen.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | international.join-tsinghua.edu.cn/Admission1/Freshmen_Scholarships1.htm | seen: |
| dev2 | tec | english | english_evidence.toefl_ibt.minimum | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | tec.mx/es/ingenieria-y-ciencias/ingenieria-en-tecnologias-computac | seen: |
| dev2 | tec | scholarship | scholarships.beca_al_talento_academico.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | tec.mx/es/profesional/becas | seen: |
| dev2 | tec | scholarship_international | scholarships.beca_al_talento_academico.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | tec.mx/sites/default/files/repositorio/conocenos/sacscoc/catalogos | seen: |
| dev2 | uba | scholarship | scholarships.beca_de_ayuda_economica.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | extension.uba.ar/noticias/beca-de-ayuda-economica-sarmiento/ | seen: |
| dev2 | uba | scholarship_international | scholarships.beca_de_ayuda_economica.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | extension.uba.ar/noticias/beca-de-ayuda-economica-sarmiento/ | seen: |
| dev2 | kaznu | scholarship | scholarships.award.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | welcome.kaznu.kz/ru/admissions/foreign/foreign_rules/ | seen: |
| dev2 | kaznu | scholarship_international | scholarships.award.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | welcome.kaznu.kz/ru/19388/page | seen: |
| dev2 | uct | english | ielts.overall | Y/Y | Y/Y | -/- | --/-- | missed/missed | 3_rejected/3_rejected | uct.ac.za/students/applications-admission-requirements/language-requi | classifier-rejected:unknown |
| dev3 | imperial | english | ielts.overall | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.imperial.ac.uk/study/apply/english-language/ | seen: |
| dev3 | imperial | deadline | deadline | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.imperial.ac.uk/study/courses/undergraduate/computing-beng/ | seen: |
| dev3 | imperial | cost | tuition | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.imperial.ac.uk/study/courses/undergraduate/computing-beng/ | seen: |
| dev3 | imperial | scholarship | scholarships.imperial_inspires.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.imperial.ac.uk/study/fees-and-funding/scholarships-search/imperial-inspire | seen: |
| dev3 | imperial | scholarship_international | scholarships.imperial_inspires.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.imperial.ac.uk/study/fees-and-funding/scholarships-search/imperial-inspire | seen: |
| dev3 | unsw | english | ielts.overall | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.unsw.edu.au/study/how-to-apply/english-language-requirements | seen: |
| dev3 | unsw | scholarship | scholarships.scientia_coursework.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.scholarships.unsw.edu.au/scholarships/id/1988 | seen: |
| dev3 | unsw | scholarship_international | scholarships.scientia_coursework.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.scholarships.unsw.edu.au/scholarships/id/1988 | seen: |
| dev3 | utokyo | deadline | deadline | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.u-tokyo.ac.jp/content/400291798.pdf | seen: |
| dev3 | utokyo | scholarship | scholarships.award.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.u-tokyo.ac.jp/ja/admissions/tuition-fees/h01_02_03.html | seen: |
| dev3 | utokyo | scholarship_international | scholarships.award.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.u-tokyo.ac.jp/ja/admissions/tuition-fees/h01_02_03.html | seen: |
| dev3 | ntutw | deadline | deadline | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | admissions.ntu.edu.tw/apply/degree-students/international-students/ | seen: |
| dev3 | um | english | ielts.overall | -/- | -/- | -/- | Y-/Y- | missed/missed | 1_never_seen/1_never_seen | study.um.edu.my/bachelor-of-computer-science-software-engineering | seen: |
| dev3 | um | english | english_evidence.toefl_ibt.minimum | -/- | -/- | -/- | Y-/Y- | missed/missed | 1_never_seen/1_never_seen | study.um.edu.my/bachelor-of-computer-science-software-engineering | seen: |
| dev3 | um | gpa | gpa | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | study.um.edu.my/bachelor-of-computer-science-software-engineering | seen: |
| dev3 | auckland | english | ielts.overall | Y/- | Y/- | Y/- | YY/-- | hit/missed | hit/1_never_seen | www.auckland.ac.nz/en/study/applications-and-admissions/entry-requirements/und | fetched-ok:program_detail |
| dev3 | auckland | deadline | deadline | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.auckland.ac.nz/en/study/study-options/find-a-study-option/bachelor-of-scie | seen: |
| dev3 | auckland | scholarship | scholarships.pong.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.auckland.ac.nz/en/study/scholarships-and-awards/find-a-scholarship/pong-ta | seen: |
| dev3 | auckland | scholarship_international | scholarships.pong.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.auckland.ac.nz/en/study/scholarships-and-awards/find-a-scholarship/pong-ta | seen: |
| dev3 | ucph | gpa | gpa | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.ku.dk/studies/admission/bachelor/quota-2 | seen: |
| dev3 | msu | gpa | gpa | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | cpk.msu.ru/files/2026/minimum.pdf | seen: |
| dev3 | msu | scholarship | scholarships.state_funded.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | pk.cs.msu.ru/auslander_budget | seen: |
| dev3 | msu | scholarship_international | scholarships.state_funded.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | cpk.msu.ru/files/2026/rules.pdf | seen: |
| dev3 | puc | deadline | deadline | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | admision.uc.cl/vias-de-admision/admision-especial-y-complementaria/calenda | seen: |
| dev3 | usp | scholarship | scholarships.papfe.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | prip.usp.br/wp-content/uploads/sites/1632/2025/12/PAPFE2026_EDITAL.pdf | seen: |
| dev3 | usp | scholarship_international | scholarships.papfe.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | prip.usp.br/wp-content/uploads/sites/1632/2025/12/PAPFE2026_EDITAL.pdf | seen: |
| dev3 | chula | english | ielts.overall | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.ise.eng.chula.ac.th/prospective-student/international | seen: |
| dev3 | chula | english | english_evidence.toefl_ibt.minimum | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.ise.eng.chula.ac.th/prospective-student/international | seen: |
| dev3 | chula | english | english_evidence.duolingo.minimum | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.ise.eng.chula.ac.th/prospective-student/international | seen: |
| dev3 | chula | scholarship | scholarships.ise_foreign.exists | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.ise.eng.chula.ac.th/news/ise-international-admission-2026-foreign-students | seen: |
| dev3 | chula | scholarship_international | scholarships.ise_foreign.applicability.international | -/- | -/- | -/- | --/-- | missed/missed | 1_never_seen/1_never_seen | www.ise.eng.chula.ac.th/news/ise-international-admission-2026-foreign-students | seen: |

## Appendix C — stage timelines (rep 1): stage[t_start-t_end s, events]

- cohort/groningen: robots[1-1,1] > sitemap[2-5,2] > walker[9-26,10] > nav_walker[26-27,2] > walker[29-29,1] > nav_walker[29-29,1] > walker[29-29,2] > nav_walker[29-29,1] > walker[29-29,1] > nav_walker[29-33,3] > walker[35-35,2] > nav_walker[35-49,6] > search[60-67,6] > topic_search[70-71,2] > requirements[71-82,6] > costs[84-84,1] > scholarships[88-99,7]
- cohort/delft: robots[1-1,1] > sitemap[1-1,1] > walker[6-6,2] > nav_walker[8-8,1] > walker[9-11,2] > nav_walker[11-11,1] > walker[11-15,7] > search[18-24,6] > topic_search[26-27,2] > requirements[27-28,3] > costs[30-30,1] > requirements[31-37,5] > costs[38-38,1] > scholarships[39-43,4]
- cohort/aalto: robots[1-1,1] > sitemap[11-11,4] > walker[11-11,1] > nav_walker[11-11,1] > walker[11-11,1] > search[12-22,16] > requirements[22-22,1] > scholarships[22-22,2]
- cohort/vienna: robots[1-1,1] > sitemap[1-7,4] > walker[8-12,3] > confirm[14-14,1] > walker[15-20,5] > confirm[20-20,1] > nav_walker[20-22,3] > walker[24-24,1] > search[25-31,6] > topic_search[33-34,2] > requirements[34-37,3] > costs[40-40,1] > requirements[43-44,2] > costs[45-45,1] > scholarships[48-55,6]
- cohort/warsaw: robots[1-1,1] > sitemap[3-6,3] > walker[7-24,13] > search[25-47,13] > topic_search[52-53,2] > requirements[53-58,4] > scholarships[60-87,9]
- cohort/ubc: robots[1-1,1] > sitemap[1-5,4] > nav_walker[7-85,22] > search[87-108,9]
- cohort/toronto: robots[0-0,1] > sitemap[0-5,4] > walker[6-6,1] > nav_walker[7-7,1] > walker[8-8,1] > search[9-26,17] > requirements[26-26,1] > costs[26-26,1] > scholarships[28-28,1]
- cohort/hku: robots[0-0,1] > sitemap[1-12,8] > walker[14-14,1] > nav_walker[15-15,1] > walker[15-15,1] > search[16-51,14] > topic_search[58-59,2] > requirements[59-60,3] > costs[60-60,2] > scholarships[60-66,5]
- cohort/ntu: robots[0-0,1] > sitemap[3-8,4] > confirm[12-14,3] > nav_walker[16-16,1] > confirm[17-17,1] > nav_walker[19-19,1] > topic_search[23-27,3] > requirements[27-36,7] > costs[37-37,1] > requirements[40-44,7] > costs[44-44,1] > requirements[44-48,7] > costs[48-48,1] > scholarships[49-55,6]
- cohort/kaist: robots[0-0,1] > sitemap[3-8,4] > walker[9-17,5] > search[21-57,17] > requirements[57-57,1] > scholarships[58-58,1]
- dev2/ethz: robots[1-1,1] > sitemap[2-7,4] > walker[8-11,2] > search[13-26,13] > topic_search[29-33,2] > requirements[33-38,4] > scholarships[39-43,5]
- dev2/psaclay: robots[1-1,1] > sitemap[3-18,7] > walker[20-20,1] > nav_walker[21-21,1] > walker[23-23,1] > nav_walker[24-26,2] > walker[27-32,6] > nav_walker[32-38,5] > search[40-50,6] > topic_search[52-54,2] > requirements[54-55,3] > costs[59-61,2] > scholarships[62-69,3]
- dev2/uppsala: robots[1-1,1] > sitemap[3-6,2] > walker[11-13,2] > search[14-32,13] > topic_search[35-36,2] > requirements[36-42,6] > scholarships[42-48,5]
- dev2/tcd: robots[1-1,1] > sitemap[3-7,4] > walker[9-10,2] > confirm[14-17,2] > nav_walker[20-20,1] > walker[23-23,1] > nav_walker[23-23,1] > confirm[26-26,1] > nav_walker[26-26,1] > confirm[29-29,1] > nav_walker[29-32,3] > confirm[35-35,1] > nav_walker[36-47,5] > topic_search[52-54,3] > requirements[54-72,15] > scholarships[72-100,12]
- dev2/tsinghua: robots[1-1,1] > sitemap[3-7,4] > walker[9-11,2] > search[12-36,17] > requirements[36-36,1]
- dev2/tec: robots[1-1,1] > sitemap[3-3,1] > walker[7-21,13] > search[24-64,17] > costs[64-64,1]
- dev2/uba: robots[1-1,1] > sitemap[2-7,4] > walker[16-35,9] > search[41-74,17]
- dev2/kaznu: robots[1-1,1] > sitemap[2-3,4] > walker[4-5,2] > search[6-58,17]
- dev2/uct: robots[1-1,1] > sitemap[4-21,12] > walker[22-27,3] > confirm[29-31,2] > walker[32-37,3] > nav_walker[39-41,2] > walker[41-57,11] > search[58-72,9] > topic_search[78-80,2] > requirements[80-82,3] > costs[84-84,1] > requirements[85-86,3] > costs[86-86,1] > requirements[87-87,3] > costs[87-87,1] > scholarships[87-105,8]
- dev2/khalifa: robots[1-1,1] > sitemap[4-29,4] > confirm[29-29,3] > walker[29-29,2] > search[30-38,15] > requirements[38-38,1] > costs[38-38,1] > scholarships[38-38,1]
- dev3/imperial: robots[1-1,1] > sitemap[2-12,3] > nav_walker[17-22,2] > confirm[28-46,4] > nav_walker[52-113,15]
- dev3/unsw: robots[1-1,1] > sitemap[2-43,5] > confirm[53-113,7]
- dev3/utokyo: robots[1-1,1] > sitemap[7-15,4] > walker[17-32,4] > search[47-77,17] > requirements[77-77,1]
- dev3/ntutw: robots[1-1,1] > sitemap[4-9,4] > nav_walker[11-11,1] > walker[13-17,2] > search[18-54,17]
- dev3/um: robots[1-1,1] > sitemap[4-8,4] > walker[10-12,3] > search[16-36,13] > topic_search[39-40,2] > requirements[40-46,4] > scholarships[47-60,5]
- dev3/kuleuven: robots[1-1,1] > sitemap[1-6,4] > walker[8-11,2] > search[15-42,17]
- dev3/auckland: robots[1-1,1] > sitemap[3-4,2] > nav_walker[15-47,18] > search[49-65,10] > topic_search[70-71,2] > requirements[71-77,5] > costs[79-79,1] > scholarships[81-109,18]
- dev3/ucph: robots[1-1,1] > sitemap[2-18,12] > walker[20-20,1] > confirm[21-23,2] > walker[24-24,1] > confirm[25-25,2] > nav_walker[25-50,18] > walker[51-51,1] > confirm[53-53,2] > nav_walker[53-54,18] > search[56-61,8] > topic_search[64-65,2] > requirements[65-74,12] > scholarships[74-78,6]
- dev3/msu: robots[1-1,1] > sitemap[3-8,4] > walker[9-11,2] > search[12-45,17]
- dev3/iitd: robots[1-1,1] > sitemap[4-8,4] > nav_walker[10-10,1] > walker[12-14,2] > search[16-47,17] > requirements[47-47,1] > scholarships[48-48,1]
- dev3/puc: robots[1-1,1] > sitemap[1-1,1] > walker[21-21,2] > nav_walker[22-22,1] > walker[24-24,1] > sitemap[24-24,1] > walker[26-27,3] > sitemap[27-27,1] > walker[27-27,2] > search[29-84,14] > topic_search[87-89,2] > requirements[89-94,4] > scholarships[108-108,1]
- dev3/uio: robots[1-1,1] > sitemap[1-40,6] > confirm[41-51,8] > walker[53-59,4] > search[61-80,16] > requirements[80-80,1] > costs[81-81,1] > scholarships[82-82,1]
- dev3/usp: robots[1-1,1] > sitemap[7-14,4] > nav_walker[17-47,12] > search[52-95,18]
- dev3/ub: robots[1-1,1] > sitemap[1-27,6] > walker[27-27,2] > search[28-47,15]
- dev3/chula: robots[1-1,1] > sitemap[2-15,12] > walker[28-50,17] > search[51-82,14] > topic_search[85-87,2] > requirements[87-91,4] > costs[91-91,1] > scholarships[94-113,6]
## Appendix D — verify-stage reads and their diagnostics (rep 1, cases that reached verify)

Each line: time, URL, diagnostic category:page type:detail. `[query]` marks topic/award queries. `?` = read in verify but no diagnostic recorded (lead rejected before classification, or a programme page re-read).

### cohort/groningen — verify from t=70 s, programme page ['rug.nl/bachelors/computing-science']

- [query t=70]
- [query t=71]
- t=71 `https://www.rug.nl/bachelors/computing-science` → fetched-ok:intake_specific_program:5 claims read from this page
- t=72 `https://www.rug.nl/education/bachelor/international-students` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=76 `https://www.rug.nl/education/application-enrolment-tuition-fees/admission/non-dutch-qualification/bachelor/bac` → ?
- t=78 `https://www.rug.nl/education/bachelor/international-students/financial-matters/?lang=en` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='T
- t=78 `https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/non-dutch-qualification/b` → ?
- t=82 `https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/non-dutch-qualification/` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=84 `https://www.rug.nl/education/application-enrolment-tuition-fees` → no-pattern-match:costs:page was read but no cost figures could be extracted
- t=88 `https://www.rug.nl/education/scholarships` → fetched-ok:unknown:read as a funding index; 0 award links, 0 queued within the award budget
- t=92 `https://www.rug.nl/bachelors/computing-science` → fetched-ok:intake_specific_program:5 claims read from this page
- [query t=94]
- t=94 `https://www.rug.nl/education/scholarships/prospect-burma-scholarships?lang=en` → fetched-ok:scholarship_award:award page; 2 claims read
- t=95 `https://www.rug.nl/education/scholarships/eric-bleumink-fellowship?lang=en` → fetched-ok:scholarship_index:read as a funding index; 1 award links, 1 queued within the award budget
- t=96 `https://www.rug.nl/alumni/support-research-and-education/scholarships-and-awards/eric-bleumink-fund/applying-f` → classifier-rejected:unknown:not an award page; no scholarship recorded (1 award links, 0 below it: /alumni/s
- t=99 `https://www.rug.nl/rechten/education/law-exchange-programme/grands-and-insurance/grants-for-study-or-placement` → ?

### cohort/delft — verify from t=26 s, programme page ['tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/bachelor-of-computer-science-and-engineering']

- [query t=26]
- [query t=27]
- t=27 `https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/bachelor-of-compute` → ?
- t=27 `https://www.tudelft.nl/en/education/admission-and-application` → no-pattern-match:general_admissions:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=28 `https://www.tudelft.nl/en/education/admission-and-application/bsc-international-diploma/admission-requirements` → ?
- t=30 `https://www.tudelft.nl/en/education/study-programme-orientation/practical-matters/tuition-fee-finances` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='T
- t=31 `https://www.tudelft.nl/en/education/admission-and-application/bsc-international-diploma` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=32 `https://www.tudelft.nl/onderwijs/toelating-en-aanmelding/bsc-international-diploma/admission-requirements` → fetched-ok:program_detail:4 claims read from this page
- t=34 `https://www.tudelft.nl/en/education/admission-and-application/bsc-international-diploma/admission-requirements` → fetched-ok:program_detail:4 claims read from this page
- t=36 `https://www.tudelft.nl/en/education/admission-and-application/bsc-international-diploma/dates-deadlines` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=37 `https://www.tudelft.nl/onderwijs/toelating-en-aanmelding/bsc-international-diploma/dates-deadlines` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=38 `https://www.tudelft.nl/en/education/study-programme-orientation/practical-matters/tuition-fee-finances` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='T
- t=39 `https://www.tudelft.nl/en/education/study-programme-orientation/practical-matters/scholarships` → fetched-ok:scholarship_index:read as a funding index; 2 award links, 2 queued within the award budget
- t=40 `https://www.tudelft.nl/en/education/study-programme-orientation/practical-matters/scholarships/faq` → classifier-rejected:scholarship_faq:not an award page; no scholarship recorded (1 award links, 0 below it: /en/educa
- t=42 `https://www.tudelft.nl/en/education/study-programme-orientation/practical-matters/scholarships/scholarships-fr` → ?
- t=43 `https://www.tudelft.nl/en/delft-university-fund/we-support/support-innovative-education/clip-scholarship` → fetched-ok:scholarship_award:award page; 2 claims read

### cohort/aalto — verify from t=22 s, programme page []



### cohort/vienna — verify from t=33 s, programme page ['aufnahmeverfahren.univie.ac.at/en/computer-science']

- [query t=33]
- [query t=34]
- t=34 `https://aufnahmeverfahren.univie.ac.at/en/computer-science` → fetched-ok:program_detail:2 claims read from this page
- t=35 `https://studieren.univie.ac.at/en/admission-procedure` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=37 `https://studieren.univie.ac.at/en/admission/info-third-country-students/` → no-pattern-match:general_admissions:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=40 `https://studieren.univie.ac.at/en/tuition-fee/` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title="T
- t=43 `https://aufnahmeverfahren.univie.ac.at/en/german-language-proficiency` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=44 `https://studieren.univie.ac.at/en/admission/german-language-proficiency/` → fetch-failed:unclassified:http_error — HTTP 404
- t=45 `https://studieren.univie.ac.at/en/tuition-fee` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title="T
- t=48 `https://studieren.univie.ac.at/en/studying-and-learning/financial-matters/grants-and-scholarships` → fetched-ok:scholarship_index:read as a funding index; 0 award links, 0 queued within the award budget
- t=49 `https://aufnahmeverfahren.univie.ac.at/en/computer-science` → fetched-ok:program_detail:2 claims read from this page
- [query t=52]
- t=52 `https://massmailer.univie.ac.at/action/mlr/lk?cid=17167&cks=170a4556&idx=434198&uid=0&url=nUE0pUZ6Yl9yMTy0nJ5a` → ?
- t=53 `https://massmailer.univie.ac.at/action/mlr/lk?cid=5347&cks=e5200bec&idx=330272&uid=0&url=nUE0pUZ6Yl9apzShqUZhL` → ?
- t=55 `https://massmailer.univie.ac.at/action/mlr/lk?cid=6545&cks=bfb46239&idx=866284&uid=0&url=nUE0pUZ6Yl9up3NhoJIlL` → ?

### cohort/warsaw — verify from t=52 s, programme page ['informatorects.uw.edu.pl/en/programmes-all/in/s1-inf']

- [query t=52]
- [query t=53]
- t=53 `https://informatorects.uw.edu.pl/en/programmes-all/IN/S1-INF` → fetched-ok:intake_specific_program:1 claims read from this page
- t=54 `https://en.uw.edu.pl/studies/admission` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=56 `https://rekrutacja.uw.edu.pl/en/language-competence/` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=58 `https://rekrutacja.uw.edu.pl/en/application-and-tuition-fees/` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='A
- t=60 `https://en01.uw.edu.pl/badania/granty-i-subsydia` → fetch-failed:unclassified:robots_disallowed — robots.txt unreachable (ConnectTimeout); RFC 9309 treats the
- t=70 `https://informatorects.uw.edu.pl/en/programmes-all/IN/S1-INF` → fetched-ok:intake_specific_program:1 claims read from this page
- [query t=72]
- t=72 `https://welcome.uw.edu.pl/wp/before-you-arrive/scholarship-for-foreigners/scholarship-for-international-studen` → ?
- t=75 `https://welcome.uw.edu.pl/wp/before-you-arrive/scholarship-for-foreigners` → fetched-ok:scholarship_index:read as a funding index; 3 award links, 3 queued within the award budget
- t=78 `https://welcome.uw.edu.pl/scholarship-for-international-students-of-the-university-of-warsaw` → classifier-rejected:scholarship_index:index page beyond the index budget; not followed
- t=81 `https://welcome.uw.edu.pl/scholarships-delivered-by-nawa` → classifier-rejected:scholarship_index:index page beyond the index budget; not followed
- t=84 `https://welcome.uw.edu.pl/visegrad-scholarship-program` → classifier-rejected:unknown:not an award page; no scholarship recorded (0 award links, 0 below it: )
- t=87 `https://welcome.uw.edu.pl/wp/scholarships-and-support-for-students-and-researchers-from-belarus` → fetched-ok:scholarship_award:award page; 1 claims read

### cohort/toronto — verify from t=26 s, programme page []



### cohort/hku — verify from t=58 s, programme page ['cs.hku.hk']

- [query t=58]
- [query t=59]
- t=59 `https://www.cs.hku.hk/` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=60 `https://admissions.hku.hk/` → fetch-failed:unclassified:robots_disallowed — robots.txt unreachable (ConnectError); RFC 9309 treats the w
- t=60 `https://admissions.hku.hk/apply/international-qualifications/english-language-requirement` → fetch-failed:unclassified:robots_disallowed — robots.txt unreachable (ConnectError); RFC 9309 treats the w
- t=60 `https://admissions.hku.hk/fees-and-scholarships/fees` → fetch-failed:unclassified:robots_disallowed — robots.txt unreachable (ConnectError); RFC 9309 treats the w
- t=60 `https://admissions.hku.hk/fees-and-scholarships/fees` → fetch-failed:unclassified:robots_disallowed — robots.txt unreachable (ConnectError); RFC 9309 treats the w
- t=60 `https://admissions.hku.hk/fees-and-scholarships/scholarships` → fetch-failed:unclassified:robots_disallowed — robots.txt unreachable (ConnectError); RFC 9309 treats the w
- t=61 `https://www.cs.hku.hk/` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=61 `https://www.cs.hku.hk/news-events/news-and-announcements/cds-announces-entrance-scholarships-for-top-students-` → ?
- t=64 `https://www.cs.hku.hk/news-events/news-and-announcements/cds-prof-qi-zhao-honoured-as-highly-commended-in-the-` → ?
- t=66 `https://www.cs.hku.hk/news-events/news-and-announcements/hku-cds-receives-three-awards-at-the-51st-internation` → ?

### cohort/ntu — verify from t=23 s, programme page ['ntu.edu.sg/education/undergraduate-programme/bachelor-of-computing-in-computer-science']

- [query t=23]
- [query t=24]
- [query t=27]
- t=27 `https://www.ntu.edu.sg/education/undergraduate-programme/bachelor-of-computing-in-computer-science` → fetched-ok:program_detail:1 claims read from this page
- t=27 `https://www.ntu.edu.sg/admissions/undergraduate` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=28 `https://www.ntu.edu.sg/admissions/undergraduate/admissions/general-admission-requirements` → fetched-ok:intake_specific_program:5 claims read from this page
- t=30 `https://www.ntu.edu.sg/admissions/undergraduate/fees-and-funding/tuition-fees` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='T
- t=31 `https://www.ntu.edu.sg/admissions/undergraduate/admissions` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=33 `https://www.ntu.edu.sg/admissions/undergraduate/admissions/general-admission-requirements/international-qualif` → fetched-ok:intake_specific_program:5 claims read from this page
- t=36 `https://www.ntu.edu.sg/admissions/undergraduate/admissions/general-admission-requirements/international-qualif` → ?
- t=37 `https://www.ntu.edu.sg/admissions/undergraduate/financial-matters` → no-pattern-match:costs:page was read but no cost figures could be extracted
- t=40 `https://www.ntu.edu.sg/education/undergraduate-programme/bachelor-of-science-in-mathematical-and-computer-scie` → fetched-ok:program_detail:1 claims read from this page
- t=40 `https://www.ntu.edu.sg/admissions/undergraduate` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=41 `https://www.ntu.edu.sg/admissions/undergraduate/admissions/general-admission-requirements` → fetched-ok:intake_specific_program:5 claims read from this page
- t=42 `https://www.ntu.edu.sg/admissions/undergraduate/fees-and-funding/tuition-fees` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='T
- t=42 `https://www.ntu.edu.sg/admissions/undergraduate/admissions` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is

### cohort/kaist — verify from t=57 s, programme page []



### dev2/ethz — verify from t=29 s, programme page ['ethz.ch/en/studies/bachelor/bachelors-degree-programmes/engineering-sciences/computer-science.html']

- [query t=29]
- [query t=33]
- t=33 `https://ethz.ch/en/studies/bachelor/bachelors-degree-programmes/engineering-sciences/computer-science.html` → fetched-ok:program_detail:1 claims read from this page
- t=34 `https://ethz.ch/en/studies/bachelor/application/non-swiss-matriculation-certificate/admission-prerequisites.ht` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=34 `https://ethz.ch/students/en/studies/financial/tuition-fees.html` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='T
- t=38 `https://ethz.ch/en/studies/bachelor/application/non-swiss-matriculation-certificate/language-requirements.html` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=39 `https://ethz.ch/en/studies/bachelor/bachelors-degree-programmes/engineering-sciences/computer-science.html` → fetched-ok:program_detail:1 claims read from this page
- [query t=40]
- t=40 `https://ethz.ch/students/en/studies/financial/scholarships.html` → fetched-ok:scholarship_index:read as a funding index; 0 award links, 0 queued within the award budget
- t=40 `https://ethz.ch/students/en/studies/financial/scholarships/excellencescholarship.html` → fetched-ok:scholarship_award:award page; 2 claims read
- t=43 `https://ethz.ch/content/dam/ethz/main/education/finanzielles/files-en/guidelines-scholarships.pdf` → classifier-rejected:unknown:not an award page; no scholarship recorded (0 award links, 0 below it: )

### dev2/psaclay — verify from t=52 s, programme page ['universite-paris-saclay.fr/en/education/licence-undergraduate-programme/informatique']

- [query t=52]
- [query t=54]
- t=54 `https://www.universite-paris-saclay.fr/en/education/licence-undergraduate-programme/informatique` → fetched-ok:program_detail:1 claims read from this page
- t=54 `https://www.universite-paris-saclay.fr/en/admission/international-students` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='I
- t=55 `http://www.universite-paris-saclay.fr/en/admissions/applying-undergraduate-programmes` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=59 `http://www.universite-paris-saclay.fr/en/admission/tuition-fees` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='T
- t=61 `https://www.universite-paris-saclay.fr/en/admission/tuition-fees` → no-pattern-match:costs:page was read but no cost figures could be extracted
- t=62 `https://www.universite-paris-saclay.fr/en/recherche/doctorat-et-hdr/funding` → fetched-ok:scholarship_index:read as a funding index; 2 award links, 2 queued within the award budget
- t=64 `https://www.universite-paris-saclay.fr/en/csc-joint-doctoral-program-universite-paris-saclay-and-china-scholar` → ?
- t=69 `https://www.universite-paris-saclay.fr/en/french-government-doctoral-scholarship-programme-mopga-china` → fetch-failed:unclassified:http_error — HTTP 404

### dev2/uppsala — verify from t=35 s, programme page ['uu.se/en/study/outline']

- [query t=35]
- [query t=36]
- t=36 `https://www.uu.se/en/study/programme/bachelors-programme-computer-science` → fetched-ok:program_detail:2 claims read from this page
- t=37 `https://www.uu.se/en/study/bachelors-studies/application/entry-requirements` → fetched-ok:intake_specific_program:3 claims read from this page
- t=38 `https://www.uu.se/en/students/student-life/student-finance/tuition-fees` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='T
- t=40 `https://www.uu.se/en/study/outline?query=166` → fetched-ok:program_detail:1 claims read from this page
- t=42 `https://www.uu.se/en/study/bachelors-studies/application/entry-requirements` → fetched-ok:intake_specific_program:3 claims read from this page
- t=42 `https://www.uu.se/en/students/student-life/student-finance/tuition-fees` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='T
- t=42 `https://www.uu.se/en/study/programme/bachelors-programme-computer-science` → fetched-ok:program_detail:2 claims read from this page
- [query t=44]
- t=44 `https://www.uu.se/en/study/syllabus?query=22894` → classifier-rejected:general_admissions:not an award page; no scholarship recorded (0 award links, 0 below it: )
- t=45 `https://www.uu.se/en/students/faculty/science-and-technology/degree-project/environmental-scholarships-from-sv` → ?
- t=48 `https://www.uu.se/en/study/outline?query=166` → fetched-ok:program_detail:1 claims read from this page

### dev2/tcd — verify from t=52 s, programme page ['tcd.ie/courses/undergraduate/courses/computer-science']

- [query t=52]
- [query t=53]
- [query t=54]
- t=54 `https://www.tcd.ie/courses/undergraduate/courses/computer-science` → fetched-ok:program_detail:1 claims read from this page
- t=55 `https://www.tcd.ie/courses/postgraduate/how-to-apply` → classifier-rejected:program_catalog:classified as program_catalog; no requirement can be read from this kind of page
- t=58 `https://www.tcd.ie/study/english-language-requirements/` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=61 `https://www.tcd.ie/study/undergraduate/fee-finances/` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=64 `https://www.tcd.ie/study/international/` → classifier-rejected:program_catalog:classified as program_catalog; no requirement can be read from this kind of page
- t=69 `https://www.tcd.ie/courses/undergraduate/courses/computer-science-jh` → fetched-ok:program_detail:1 claims read from this page
- t=70 `https://www.tcd.ie/courses/postgraduate/how-to-apply` → classifier-rejected:program_catalog:classified as program_catalog; no requirement can be read from this kind of page
- t=70 `https://www.tcd.ie/study/english-language-requirements/` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=70 `https://www.tcd.ie/study/undergraduate/fee-finances/` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=70 `https://www.tcd.ie/study/international/` → classifier-rejected:program_catalog:classified as program_catalog; no requirement can be read from this kind of page
- t=71 `https://www.tcd.ie/courses/undergraduate/courses/computer-science-linguistics-and-a-language` → fetched-ok:program_detail:1 claims read from this page
- t=71 `https://www.tcd.ie/courses/postgraduate/how-to-apply` → classifier-rejected:program_catalog:classified as program_catalog; no requirement can be read from this kind of page
- t=71 `https://www.tcd.ie/study/english-language-requirements/` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=

### dev2/tsinghua — verify from t=36 s, programme page []



### dev2/tec — verify from t=64 s, programme page []



### dev2/uct — verify from t=78 s, programme page ['sit.uct.ac.za/ba-informatics']

- [query t=78]
- [query t=80]
- t=80 `https://sit.uct.ac.za/bachelor-business-science-specialising-computer-science` → fetched-ok:program_detail:1 claims read from this page
- t=81 `https://uct.ac.za/students/applications/international-applicants` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=82 `https://uct.ac.za/students/applications-admission-requirements/language-requirements` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=84 `https://uct.ac.za/eresearch/costs` → no-pattern-match:unknown:page was read but no cost figures could be extracted
- t=85 `https://sit.uct.ac.za/ba-informatics` → fetched-ok:program_detail:1 claims read from this page
- t=86 `https://uct.ac.za/students/applications/international-applicants` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=86 `https://uct.ac.za/students/applications-admission-requirements/language-requirements` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=86 `https://uct.ac.za/eresearch/costs` → no-pattern-match:unknown:page was read but no cost figures could be extracted
- t=87 `https://sit.uct.ac.za/department-computer-science` → fetched-ok:unknown:listing page: only the programme's existence was read
- t=87 `https://uct.ac.za/students/applications/international-applicants` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=87 `https://uct.ac.za/students/applications-admission-requirements/language-requirements` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=87 `https://uct.ac.za/eresearch/costs` → no-pattern-match:unknown:page was read but no cost figures could be extracted
- t=87 `https://uct.ac.za/mastercardfdn/scholarship-overview` → fetched-ok:unknown:read as a funding index; 0 award links, 0 queued within the award budget
- t=89 `https://sit.uct.ac.za/bachelor-business-science-specialising-computer-science` → fetched-ok:program_detail:1 claims read from this page

### dev2/khalifa — verify from t=38 s, programme page []



### dev3/utokyo — verify from t=77 s, programme page []



### dev3/um — verify from t=39 s, programme page ['study.um.edu.my/bachelor-of-computer-science-computer-system-and-network']

- [query t=39]
- [query t=40]
- t=40 `https://study.um.edu.my/bachelor-of-computer-science-computer-system-and-network` → fetched-ok:program_detail:3 claims read from this page
- t=41 `https://study.um.edu.my/how-to-apply` → no-pattern-match:general_admissions:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=44 `https://aasd.um.edu.my/faq-ug-international-admission` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='A
- t=46 `https://study.um.edu.my/doc/tution-fee/Fee%20Structure%2C%20UG%2C%20International%20-%20Updated%2022%20Oct%202` → ?
- t=47 `https://aasd.um.edu.my/financial-aid-for-undergraduate` → fetched-ok:scholarship_index:read as a funding index; 0 award links, 0 queued within the award budget
- t=47 `https://study.um.edu.my/bachelor-of-computer-science-computer-system-and-network` → fetched-ok:program_detail:3 claims read from this page
- [query t=50]
- t=50 `https://aasd.um.edu.my/website_doc/DEP_UBT/scholarships/19.01.2026%20-%20MGSP2026.pdf` → classifier-rejected:unknown:not an award page; no scholarship recorded (0 award links, 0 below it: )
- t=60 `https://www.um.edu.my/scholarships-and-financial-assistancers` → fetched-ok:scholarship_index:read as a funding index; 0 award links, 0 queued within the award budget

### dev3/auckland — verify from t=70 s, programme page ['study.auckland.ac.nz/ords/r/uoa/catalogue/plan']

- [query t=70]
- [query t=71]
- t=71 `https://study.auckland.ac.nz/ords/r/uoa/catalogue/plan?p7_code=COMP-BSc` → fetched-ok:intake_specific_program:1 claims read from this page
- t=72 `https://www.auckland.ac.nz/en/study/applications-and-admissions/how-to-apply.html` → classifier-rejected:scholarship_index:classified as scholarship_index; no requirement can be read from this kind of pa
- t=73 `https://www.auckland.ac.nz/en/study/applications-and-admissions/entry-requirements/undergraduate-entry-require` → ?
- t=76 `https://www.auckland.ac.nz/en/study/fees-and-money-matters/tuition-fees/international-student-fees/undergradua` → ?
- t=77 `https://www.auckland.ac.nz/en/students/academic-information/important-dates.html` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=79 `https://www.auckland.ac.nz/en/study/fees-and-money-matters/tuition-fees.html` → no-pattern-match:costs:page was read but no cost figures could be extracted
- t=81 `https://www.auckland.ac.nz/en/study/scholarships-and-awards.html` → fetched-ok:scholarship_index:read as a funding index; 11 award links, 11 queued within the award budget
- t=82 `https://www.auckland.ac.nz/en/study/scholarships-and-awards/scholarship-types.html` → fetched-ok:scholarship_index:read as a funding index; 12 award links, 7 queued within the award budget
- t=84 `https://www.auckland.ac.nz/en/study/scholarships-and-awards/scholarship-eligibility.html` → fetched-ok:scholarship_index:read as a funding index; 10 award links, 6 queued within the award budget
- t=84 `https://www.auckland.ac.nz/en/study/scholarships-and-awards/how-to-apply.html` → classifier-rejected:scholarship_index:index page beyond the index budget; not followed
- t=86 `https://www.auckland.ac.nz/en/study/scholarships-and-awards/scholarship-types/undergraduate-scholarships.html` → classifier-rejected:scholarship_index:index page beyond the index budget; not followed
- t=87 `https://www.auckland.ac.nz/en/study/scholarships-and-awards/scholarship-types/scholarships-for-international-s` → ?
- t=89 `https://www.auckland.ac.nz/en/study/scholarships-and-awards/scholarship-types/scholarships-for-students-with-d` → ?
- t=91 `https://www.auckland.ac.nz/en/study/scholarships-and-awards/applications-open-now.html` → classifier-rejected:scholarship_index:index page beyond the index budget; not followed

### dev3/ucph — verify from t=64 s, programme page ['ku.dk/education/curriculum/computer-science']

- [query t=64]
- [query t=65]
- t=65 `https://www.ku.dk/studies/bachelor/computer-science` → fetched-ok:program_detail:1 claims read from this page
- t=66 `https://www.ku.dk/studies/admission/bachelor` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=66 `https://www.ku.dk/studies/admission/application-deposit-fee-and-tuition-fees` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='H
- t=68 `https://www.ku.dk/studies/masters` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=69 `https://www.ku.dk/studies/admission/masters/language-requirements` → fetched-ok:program_detail:3 claims read from this page
- t=72 `https://www.ku.dk/studies/admission/important-dates-and-deadlines` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=72 `https://www.ku.dk/studies/bachelor/computer-science-and-economics` → fetched-ok:program_detail:1 claims read from this page
- t=73 `https://www.ku.dk/studies/admission/bachelor` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=73 `https://www.ku.dk/studies/admission/application-deposit-fee-and-tuition-fees` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='H
- t=73 `https://www.ku.dk/studies/masters` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=73 `https://www.ku.dk/studies/admission/masters/language-requirements` → fetched-ok:program_detail:3 claims read from this page
- t=74 `https://www.ku.dk/studies/admission/important-dates-and-deadlines` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=74 `https://www.ku.dk/studies/bachelor/computer-science` → fetched-ok:program_detail:1 claims read from this page
- [query t=76]

### dev3/iitd — verify from t=47 s, programme page []



### dev3/puc — verify from t=87 s, programme page ['ing.uc.cl/publicaciones/a-mobile-robotics-course-for-undergraduate-students-in-computer-science']

- [query t=87]
- [query t=89]
- t=89 `https://www.ing.uc.cl/publicaciones/a-mobile-robotics-course-for-undergraduate-students-in-computer-science` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=90 `https://www.uc.cl/en/keywords/admission` → no-pattern-match:general_admissions:page was read and accepted, but no requirement pattern matched; nothing on it is
- t=92 `https://www.ing.uc.cl/en/programas-de-estudio/postgrado/doctorado-ciencias-la-ingenieria/requisitos-y-postulac` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=94 `https://doctorados.uc.cl/en/admissions/tuition-fees/` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='T
- t=108 `https://www.ing.uc.cl/publicaciones/a-mobile-robotics-course-for-undergraduate-students-in-computer-science` → no-pattern-match:program_detail:page was read and accepted, but no requirement pattern matched; nothing on it is

### dev3/uio — verify from t=80 s, programme page []



### dev3/chula — verify from t=85 s, programme page ['math.sc.chula.ac.th/program/undergraduate/computer-science']

- [query t=85]
- [query t=87]
- t=87 `https://www.math.sc.chula.ac.th/program/undergraduate/computer-science` → fetched-ok:unknown:listing page: only the programme's existence was read
- t=87 `https://www.chula.ac.th/academics/admissions` → classifier-rejected:unknown:classified as unknown; no requirement can be read from this kind of page. title=
- t=88 `https://www.chula.ac.th/en/academics/admissions/undergraduate-admission/` → fetched-ok:program_detail:1 claims read from this page
- t=91 `https://www.chula.ac.th/en/academics/admissions/tuition-and-fees/` → classifier-rejected:costs:classified as costs; no requirement can be read from this kind of page. title='T
- t=91 `https://www.chula.ac.th/about/feedback` → no-pattern-match:unknown:page was read but no cost figures could be extracted
- t=94 `https://www.research.chula.ac.th/funding-ora` → fetched-ok:unknown:read as a funding index; 0 award links, 0 queued within the award budget
- t=104 `https://www.math.sc.chula.ac.th/program/undergraduate/computer-science` → fetched-ok:unknown:listing page: only the programme's existence was read
- [query t=105]
- t=105 `https://www.arts.chula.ac.th/balac/wp-content/uploads/2020/07/ETcVKLnAo5Fri110644.pdf` → classifier-rejected:unknown:not an award page; no scholarship recorded (0 award links, 0 below it: )
- t=112 `https://www.inter.chula.ac.th/posts/39176` → classifier-rejected:unknown:not an award page; no scholarship recorded (0 award links, 0 below it: )
- t=113 `https://www.inter.chula.ac.th/posts/29376` → classifier-rejected:unknown:not an award page; no scholarship recorded (0 award links, 0 below it: )


## Appendix E — do the programme pages link to the gold evidence pages? (hand fetch, offline)

Needle = a path fragment of a gold evidence URL (or the question's page kind); each hit shows the link and its anchor text. Text probes show the gold value in the page's own text.

### ntu (confirmed programme page) — 358 links

- `nanyang-scholarship`: 0
- `other-international-qualifications`: 0
- `general-admission-requirements`: 0
- `/scholarships`: 2 → `https://www.ntu.edu.sg/admissions/graduate/financialmatters/scholarships` [Scholarships]; `https://www.ntu.edu.sg/admissions/undergraduate/scholarships` [Scholarships]
- `tuition-fees`: 1 → `https://www.ntu.edu.sg/admissions/undergraduate/financial-matters/tuition-fees` [Tuition Fees]

### imperial (gold programme page, 2027) — 426 links

- `/study/apply/english-language`: 2 → `https://www.imperial.ac.uk/study/apply/english-language/` [English language requirements]; `https://www.imperial.ac.uk/study/apply/english-language/english-language-exemption/` [English language exemption]
- `imperial-inspires`: 5 → `https://www.imperial.ac.uk/study/fees-and-funding/imperial-inspires-scholarships/` [Imperial Inspires scholarships]; `https://www.imperial.ac.uk/study/fees-and-funding/imperial-inspires-scholarships/faqs/` [Imperial Inspires FAQs]; `https://www.imperial.ac.uk/study/fees-and-funding/imperial-inspires-scholarships/terms-and-condition` [Terms and Conditions - 2027 Entry]
- `scholarships-search`: 2 → `https://www.imperial.ac.uk/study/fees-and-funding/scholarships-search/` [Search our scholarships]; `https://www.imperial.ac.uk/study/fees-and-funding/scholarships-search/imperial-inspires-scholarships` [Imperial Inspires Scholarships (Undergraduate)]
- text `13 January 2027`: …S | G400 UCAS institution code: I50 Application deadlines – Wednesday 13 January 2027 at 18.00 (UK time) Admissions test – the TMUA Admissions test (T…
- text `47,800`: …arn more about additional costs Overseas fee Overseas fee 2027 entry £47,800 per year Which fee you pay Whether you pay the Home or Overseas fee depen…
- text `Application deadline`: …n. Submit your application via UCAS | G400 UCAS institution code: I50 Application deadlines – Wednesday 13 January 2027 at 18.00 (UK time) Admissions …

### auckland (confirmed plan page) — 54 links

- `bachelor-of-science-bsc`: 0
- `english-language-requirements`: 0
- `scholarship`: 0

### auckland (gold BSc page) — 398 links

- `undergraduate-english-language-requirements`: 1 → `https://www.auckland.ac.nz/en/study/applications-and-admissions/entry-requirements/undergraduate-ent` [See alternative English language requirements]
- `pong-tams-ko`: 0
- `scholarships-and-awards`: 1 → `https://www.auckland.ac.nz/en/study/scholarships-and-awards.html` [Scholarships and awards]
- `fees`: 3 → `https://www.auckland.ac.nz/en/study/fees-and-money-matters.html` [Fees and money matters]; `https://www.auckland.ac.nz/en/study/fees-and-money-matters/tuition-fees/fees-by-faculty.html` [See course fees for each faculty]; `https://www.auckland.ac.nz/en/study/fees-and-money-matters/student-loans-and-allowances.html` [Student loans and allowances]
- text `IELTS`: …International Baccalaureate Diploma Score required 26 + Qualification IELTS Academic International English Language Testing System Score required 6.0 …
- text `8 December 2026`: …on closing dates Summer School 2027 1 December 2026 Semester One 2027 8 December 2026 Semester Two 2027 4 July 2027 Start dates Here are the start dat…

### um (confirmed CSN page) — 27 links

- `software-engineering`: 0
- `fee`: 0
- `scholarship`: 0
- `how-to-apply`: 1 → `https://study.um.edu.my/how-to-apply` [HOW TO APPLY]
- text `IELTS`: …age Competency in any ONE (1) of the following requirements: MUET 4.0 IELTS (Academic) 5.5 TOEFL iBT (Centre-based) 46 TOEFL Essentials (Online) 8.0 P…
- text `IELTS (Academic) 5.5`: …age Competency in any ONE (1) of the following requirements: MUET 4.0 IELTS (Academic) 5.5 TOEFL iBT (Centre-based) 46 TOEFL Essentials (Online) 8.0 P…

### ubc (gold programme page) — 167 links

- `english-language-competency`: 3 → `https://you.ubc.ca/applying-ubc/requirements/english-language-competency/` [English language competency]; `https://you.ubc.ca/applying-ubc/requirements/english-language-competency/development-programs/` [Academic English development programs for admission]; `https://you.ubc.ca/applying-ubc/requirements/english-language-competency/conditional-admission-progr` [UBC Conditional Admission Program]
- `dates-deadlines`: 1 → `https://you.ubc.ca/applying-ubc/dates-deadlines/` [Dates and deadlines]
- `scholarships-awards-international-students`: 2 → `https://you.ubc.ca/financial-planning/scholarships-awards-international-students/` [Scholarships and awards for international students]; `https://you.ubc.ca/financial-planning/scholarships-awards-international-students/international-schol` [International Scholars]
- `tuition`: 1 → `https://you.ubc.ca/financial-planning/tuition-fees/` [How UBC determines your tuition fees]

### delft (confirmed programme page) — 98 links

- `selection-procedure`: 1 → `https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/bachelor-` [Selection procedure]
- `admission-requirements`: 1 → `https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/bachelor-` [Admission requirements]
- `tuition-fee`: 0
- `scholarships`: 0
- `dates-deadlines`: 0

### kaist (gold programme page menu=188) — 342 links

- `admission.kaist.ac.kr`: 0
- `scholarships`: 0
- `menu=40`: 1 → `https://cs.kaist.ac.kr/content?menu=40` [입학 > 학부 입학">학부 입학]

### groningen (confirmed programme page) — 213 links

- `nl-scholarship`: 0
- `language-requirements-and-exemptions`: 0
- `/education/scholarships`: 0
- `apply-bsc/language`: 1 → `https://www.rug.nl/fse/education/admission-application/apply-bsc/language` [https://www.rug.nl/fse/education/admission-application/apply]
- `tuition`: 7 → `https://www.rug.nl/education/application-enrolment-tuition-fees/` [Application, registration and tuition fees]; `https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/dutch-qualifica` [Dutch diploma]; `https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/non-dutch-quali` [International diploma]
- text `IELTS`: …gineering. Please find our English language requirements (exemptions, IELTS, TOEFL, Cambridge and more) on this page: https://www.rug.nl/fse/education…
- text `Application deadline`: … Bachelor programmes. Please go to this website for more information. Application deadlines Type of student Deadline Start course Dutch students 01 Ma…

### ethz (confirmed programme page) — 58 links

- `cost-of-living`: 0
- `scholarships`: 0
- `financial`: 0
- `admission`: 0

### uppsala (confirmed programme page) — 117 links

- `entry-requirements`: 0
- `uppsala-university-scholarships`: 0
- `bachelors-studies/scholarships`: 0
- `/fees`: 1 → `https://www.uu.se/en/study/fees` [Read more about fees.]
- text `SEK 450`: …ion fees. First tuition fee instalment: SEK 75,000 Total tuition fee: SEK 450,000 Read more about fees. Application deadline 15 April 2026 Application…
- text `15 April 2027`: …l tuition fee: SEK 450,000 Read more about fees. Application deadline 15 April 2027 Application code UU-P1100 Apply now AppRegistry.registerBootstrapD…
- text `Application deadline`: …ment: SEK 75,000 Total tuition fee: SEK 450,000 Read more about fees. Application deadline 15 April 2026 Application code UU-P1100 Apply now Expand th…

### ucph (confirmed programme page) — 235 links

- `quota-2`: 1 → `https://www.ku.dk/studies/bachelor/quota-1-and-quota-2` [Quota 1 and quota 2]
- `admission/bachelor`: 4 → `https://www.ku.dk/studies/admission/bachelor` [Bachelor: Apply for admission]; `https://www.ku.dk/studies/admission/bachelor/non-eu-eea-and-non-nordic-countries` [Non-EU EEA and Non-Nordic Countries]; `https://www.ku.dk/studies/admission/bachelor/ib-and-other-international-diplomas` [IB and other international diplomas]
- `language-requirements`: 1 → `https://www.ku.dk/studies/admission/masters/language-requirements` [Language requirements]
- `deadlines`: 2 → `https://www.ku.dk/studies/admission/important-dates-and-deadlines` [Important dates and deadlines]; `https://www.ku.dk/studies/admission/masters-important-dates-and-deadlines` [Master's: Important dates and deadlines]

### tcd (confirmed programme page) — 297 links

- `/courses/undergraduate/fees`: 1 → `https://www.tcd.ie/courses/undergraduate/fees/` [Fees]
- `english-language-requirements`: 1 → `https://www.tcd.ie/study/english-language-requirements/` [here.]
- `/e3/education/scholarships`: 0
- `scholarships`: 0

