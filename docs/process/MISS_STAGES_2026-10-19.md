# Loss stages of every missed or related gold programme page on the new-defaults replay (2026-10-19)

Planner, 2026-10-19, after the new-defaults baseline (loop report 13:52: UA-1, CH-1, CQ-1, SP-1 on; runs
`rp-base2-{cohort,dev2,dev3,dev4}`, pipeline `573d9362`, `search_provider=recorded`, store
`recorded_search.base3.json`, four repetitions per set; cohort scored on `ground_truth.reviewed11`, dev2/3/4 on
`draft3`). Development cases only: **no heldout file, capture, log or label was opened; dev5 is not in the store and
was not touched; no search provider was called.**

Sources: `scorecard` and `stage_summary` on the four artifacts; per case, `capture.json` (observations, telemetry) and
`<case>.raw.json` (`discovery_trace`: `search_results`, `pages_read`, `unresolved`, `rejected_sample`, `errors`,
`stage_budget`, `walker`, `lead_found_by`); and an **offline re-ranking** of the recorded lists through the production
`discover_candidates` (same `DiscoveryIntent`, same store, `top_k=10`), which gives identity recovery's read order and
the gold's position in it. The scripts are in the session scratchpad (`ms/analyze2.py`, `ms/rerank.py`); nothing from
them is committed.

## 0. Headline

| set | hit/wrong/related/missed (×4 reps) | `programme_found_on_readable` (per rep) | readable-denominator losses (worst rep) |
|---|---|---|---|
| cohort | 4/0/1/5 | 4/7 ×4 (aalto, toronto, hku out: access) | **kaist, warsaw, ubc** |
| dev2 | 6/0/1/3 | 6/9 ×4 (kaznu out: access) | **tsinghua, tec, uct** |
| dev3 | 8/1/1/4 · 8/0/1/5 · 8/1/1/4 · 7/0/2/5 | 8/13 · 8/12 · 8/13 · 7/12 (ub out; kuleuven out in 2 reps) | **unsw, iitd, msu, ntutw** + kuleuven (wrong, 2/4) or usp (related, 1/4) |
| dev4 | 4/0/1/4 | 4/5 · 4/5 · 4/4 · 4/4 (unibo out in 2 reps) | **unibo** (2/4) |

Twelve cases lose the page inside the readable denominator. By the stage where the gold was lost:

| stage | readable-denominator cases | excluded or related-only cases | fixable on replay? |
|---|---|---|---|
| returned, not read | ubc, uct, unsw, iitd (4) | boun (related-only; stage clock) | **yes** for ubc, unsw (QT-1) and iitd (CC-1); uct is a label question |
| read but refused | tec (irrelevant), unibo (unknown, 2/4 reachable), kaist (unknown, via the walker) (3) | — | tec, unibo: **CL-2** (worker in progress); kaist: identity question |
| never returned by the recorded search | tsinghua, msu, ntutw (3) | kaznu (also unreadable); vut, itu (related-only) | **no** — new queries (msu, ntutw, vut, itu) or structural (tsinghua) |
| unreadable (403 / robots / timeout) | — | aalto, toronto, hku, ub, kaznu; kuleuven 2/4, unibo 2/4 | no (vantage point); one 0-hour dispatch for hku |
| replay limitation | warsaw (1) | pass 2 unrecorded on warsaw, ubc, uct, unsw, unibo, boun, kaznu | not a pipeline loss (§1.1) |
| label or twin question | uct, kuleuven, kaist (counted above) | — | owner round |

**Ceiling of post-search work measurable on replay: 12 → 7 losses** (QT-1 +2, CL-2 +2 where the host answers, CC-1
+1): cohort 4/7 → 5/7, dev2 6/9 → 7/9, dev3 8/13 → 10/13, dev4 4/5 → 5/5. The other five need new queries (msu,
ntutw), a domain decision (tsinghua) or an owner answer (uct, kaist).

### 0.1 A measurement fact that changes how "returned, not read" reads

The store holds **URLs only** (`recorded.py`: "Results carry no title or snippet"). `rank_candidates` scores
`title + snippet + url`, so on replay `strong_alias_in_title` and `degree_in_title` fire from URL words alone, and
`registry_seed_host` (+3) and a `bachelor` slug (+2) decide the order. Two consequences, both verified by the offline
re-ranking:

- **warsaw** is a replay-only miss. Its gold (`irk.uw.edu.pl/pl/offer/PELNE2026/programme/S1-INF/`, local-language
  rank 2; `informatorects.uw.edu.pl/en/programmes-all/IN/S1-INF/`, rank 9) scores 0 on URL words and is **outside the
  top 10**; ten `en.uw.edu.pl` news and admissions pages (seed host, `bachelor` in one slug) fill the eight checks.
  Live base3 read the gold first and hit 4/4 (its title carries "Informatyka"). Pass 2 (`programmes`, `courses`,
  `undergraduate`) is unrecorded for this domain (3 misses per column).
- **kuleuven**'s gold (`onderwijsaanbod.kuleuven.be/opleidingen/n/SC_51016742`, local-language rank 2) scores 0 for
  the same reason and is outside the top 10; live it was returned and never read (host flaky).

Every "returned, not read" verdict below is therefore cross-checked against the live base2/base3 outcome of the same
case. ubc (BA confirmed 4/4 live), uct (department page live, `ba-informatics` now) and unsw (commerce page in the
replay's list order; live 3/4 hit when the gold was rank 1) stand as pipeline losses; warsaw does not.

**Recommendation for free-search ticket 03:** when the free-tier probe records result lists, record the provider's
**title** beside each URL (public page text, no query text, as WF-17 already redacts). A store with titles replays
the live read order; this one cannot, and no replay rank rule should be fitted to it.

## 1. Per-case stage table

Outcomes are the four columns off#1 · off#2 · on#1 · on#2 (identical defaults in both arms). "Order #n" is the gold's
place in identity recovery's ranked list on the recorded URLs (offline re-ranking, pass 1 unless stated). Ranks in
brackets are the provider's rank per family. Cases that hit in all four columns are left out.

### cohort

| case | outcome | denominator | stage | what the trace shows | post-search fix | needs search |
|---|---|---|---|---|---|---|
| aalto | missed ×4 | out (BLOCKED 19/19) | unreadable (robots) | `www.aalto.fi/robots.txt` ReadTimeout → RFC 9309 disallow for the site; gold returned (`field_and_degree` 1, `programmes` 4, `undergraduate` 4), queued, `search lead unresolved (robots_disallowed)`; 8 unresolved leads, 0 pages read | none (vantage point, free-search 08) | no |
| toronto | missed ×4 | out (21/22 failed) | unreadable (403) | `future.utoronto.ca` and `www.utoronto.ca` HTTP 403 on robots, sitemaps, navigation; gold `programmes` 3 unresolved; UA-1 holds the UTM page as `unresolved_access` (no wrong page) | none | no |
| hku | missed ×4 | out (13/24 failed) | unreadable (robots), returned | gold `admissions.hku.hk/…/computing-and-data-science` returned by five families (`natural_language` 1) → `robots.txt unreachable (ConnectError)`; **7 of 8 recovery checks spent on that host** (7 `admissions.hku.hk` leads unresolved; the eighth check read a prospectus PDF); second gold form on `www.cds.hku.hk` never returned; `www.cds.hku.hk/` itself returned (`natural_language` 8), never reached | dispatch `--skip-refused-hosts` (D1, §3) | the cds form: 6 queries |
| kaist | missed ×4 | **in** | read but refused (unknown) | gold `cs.kaist.ac.kr/content?menu=188` is the manual `program_catalog` seed: walked as a catalogue, its own link dropped `short_label`; the department's `content?menu=318` read as `unknown`; search returned no gold; the page has no programme title, no level in head or slug (`?menu=188`) | none: identity/label question (programme-discovery analysis 2026-10-18 said the same); CL-2 cannot accept it | no |
| warsaw | missed ×4 | **in** | **replay limitation** | §0.1: gold `local_language` 2 and 9, order > 10 on URL words; 8 checks on `en.uw.edu.pl` pages (`degree_programmes… bachelor-and-master`, admissions news); pass 2 unrecorded; live base3 hit 4/4 | none (record titles in the next store) | no |
| ubc | related ×4 | **in** | returned, not read (stop at first confirmation) | BA page (`field_and_degree` 1, `programmes` 4) is order #1 and confirmed; SB-1 stops recovery after one check; gold BSc (`programmes` 1, `field_and_degree` 8) is **order #3**, behind `computer-science-okanagan-bsc` (#2, unlabelled); live: BA 4/4 | **QT-1** (degree-token twin `-ba` → `-bsc`) | no |

### dev2

| case | outcome | denominator | stage | what the trace shows | post-search fix | needs search |
|---|---|---|---|---|---|---|
| tsinghua | missed ×4 | **in** | never returned (other registrable domain) | gold `international.join-tsinghua.edu.cn/Divisions1.htm`; `site:tsinghua.edu.cn` cannot return it; the homepage links to `join-tsinghua.edu.cn` were dropped `off_domain` by the walker; no sitemap (4 × 404); 8 recovery reads on `cs.tsinghua.edu.cn` news, lab and PhD pages | none (DI-1 rejected; residue class) | no — a domain decision, not a query |
| tec | missed ×4 | **in** | read but refused (irrelevant) | the gold's English twin `tec.mx/en/engineering-and-sciences/bs-in-computer-science-and-technology?srsltid=…` (`field_and_degree` 1, order #1) read → `reads as irrelevant, not a programme page`; the Spanish gold never returned itself; pass 2 returns the same English page three times under `?srsltid=` variants | **CL-2** (in progress; page check first) | no |
| kaznu | missed ×4 | out (13/19 failed) | unreadable + never returned | `www.kaznu.kz/robots.txt` ConnectError (UA-1 fired, nothing held); gold never returned; the listing parent `welcome.kaznu.kz/ru/education_programs/bachelor` was read, refused `program_catalog`, and its links (Russian labels) were not followed; sibling `speciality/2546` refused on subject | LL-1 shape (§3, low) | 6 queries, optional (excluded anyway) |
| uct | related ×4 | **in** | returned, not read (stop at first confirmation) + label question | recovery: BBusSc (R2 related), BCom (R2 related), department (CH-1 unit), `ba-informatics` (labelled related) confirmed → stop; gold `bsc-degrees` (`field_and_degree` 2, `programmes` 3) is **order #5**; its head is a BSc listing ("… degrees"), so CH-1 would refuse it even if read | owner question: is `bsc-degrees` the programme page, or `ba-informatics` / BBusSc? | no |

### dev3

| case | outcome | denominator | stage | what the trace shows | post-search fix | needs search |
|---|---|---|---|---|---|---|
| unsw | related ×4 | **in** | returned, not read (stop at first confirmation) | Bengaluru page (order #1) refused by CG-1; `bachelor-of-commerce-computer-science` (`natural_language` 1; a double degree whose head "Bachelor of Commerce / Computer Science" CQ-1 does not read as a combination) confirmed → stop; gold (`field_and_degree` 3, `programmes` 2) is **order #3**, behind `bachelor-of-science-computer-science` (#2, unlabelled); live (base2 3/4, ledger 16/20): hit when the gold was `field_and_degree` rank 1 | **QT-1** (token-removal twin: slug minus `commerce`); CQ-1 slash joiner is one case, deferred | no |
| iitd | missed ×4 | **in** | returned, not read (read cap spent on course pages) | gold `homecse.iitd.ac.in/b-tech-program` order #5 (`natural_language` 8) and #8 in pass 2 (`undergraduate` 4); check 1 `abudhabi…/undergraduate-programs` robots-refused, 2–3 library/paper pages, 4 `all-courses` (`program_catalog`) whose follow-up links `col100-…`, `/`, `col703-…`, `col863-…` took checks 5–8 (no `lead_found_by`: catalogue follow-ups, not results); live (ledger, 20 repetitions): hit 17/20 | **CC-1** (course-code guard on follow-up links) | no |
| kuleuven | wrong 2, missed 2 | out in 2 reps | wrong when readable; twin question | host answers 2/4: `www.kuleuven.be/programmes/opleidingen/bachelor-informatica` (order #3) confirmed → scored wrong; gold `onderwijsaanbod…/SC_51016742` scores 0 on URL words (order > 10); live: returned, never read; replay plan §2: possibly an undeclared twin | owner question after a worker hand-check (redirect / hreflang between the two) | no |
| msu | missed ×4 | **in** | never returned | gold `pk.cs.msu.ru/bak_educational_programs` in no family; two bachelor listings read and refused on subject (`cs.msu.ru/education/bachelors` 'Бакалавриат', `international.msu.ru/bak`); asvk course pages read | LL-1 shape (if the listing links the gold; unverified) | **6 queries** |
| ntutw | missed ×4 | **in** | never returned | gold `csie.ntu.edu.tw/zh_tw/Admission/Announcement12` in no family; department front page read as `unknown`, PhD admission page refused on level | none | **6 queries** (zh shape) |
| ub | missed ×4 | out (14–15/16 failed) | unreadable (timeout / robots) | gold `web.ub.edu/en/web/estudis/w/bachelordegree-g1148` returned rank 1, 1, 2 by three families, 8 leads unresolved; `www.ub.edu` timeout, then robots ConnectTimeout | none | no |
| usp | hit 3, related 1 | **in** | stage clock (1/4) | on#2: navigation 14 s + walker 11 s + search 18 s left one recovery check (applied mathematics, related) before the 55 s stage deadline; gold `field_and_degree` 1 unread | stage-clock class (§3, low) | no |
| utokyo | unadjudicated ×4 | — | no gold, no related label | — | — | — |

### dev4

| case | outcome | denominator | stage | what the trace shows | post-search fix | needs search |
|---|---|---|---|---|---|---|
| unibo | missed ×4 | out in 2 reps | read but refused (unknown); unreadable in 2 reps | off reps: gold `corsi.unibo.it/laurea/informatica` (order #1) read → `reads as unknown`; on reps: `search lead unresolved (timeout)`, host 9/18 failed; second gold form `1cycle/ComputerScience` (`natural_language` 2) unread; pass 2 unrecorded | **CL-2** (in progress) | no |
| vut | missed ×4 (related-only labels) | n/a | never returned | related `vut.cz/en/students/programmes/programme/10326` in no family; `…/programmes/branch/11814/6090` read as `program_catalog`, its links not followed | LL-1 shape | 6 queries |
| boun | missed ×4 (related-only) | n/a | returned, not read (stage clock) | related `cmpe.bogazici.edu.tr/tr/undergraduate/overview` (`local_language` 2) is order #5; the sitemap stage read 7–8 HTML "site" pages (18–22 s) and navigation took 18–26 s, leaving 2–4 checks before the deadline | stage-clock class | no |
| itu | missed ×4 (related-only) | n/a | never returned | related `bm.itu.edu.tr/…/bilgisayar-muhendisligi/genel-bilgiler` in no family; reads were graduate programme pages; Turkish names the field "bilgisayar mühendisliği" (engineering), not the ontology alias | none | 6 queries + alias question |
| taltech | related ×4 (related-only) | n/a | best possible | the labelled related page is confirmed in every rep | — | — |

## 2. Fixable after search (measurable on replay) versus needs search

**Fixable after search, measurable on replay (regime A: no query changes).** ubc and unsw (QT-1: the gold is the
confirmed page's qualifier twin, order #3 in both lists); tec and unibo (CL-2, in progress); iitd (CC-1: four catalogue
follow-up reads on course pages consumed the cap ahead of the gold at order #5). hku's wasted checks (D1 dispatch).
Expected: +5 hits on the readable denominator, +0–1 for hku.

**Needs new search queries (not measurable on replay).** msu, ntutw (gold in no recorded family; readable hosts);
the cds form of hku's gold; vut and itu (related-only); kaznu (excluded by access anyway). Also every unrecorded
second pass (warsaw, ubc, uct, unsw, unibo, boun, kaznu: 3 families each), which the replay answers with nothing.

**Neither.** tsinghua (other registrable domain: a query under `site:` cannot return it; DI-1 rejected); aalto,
toronto, ub, kaznu (access from this vantage point); kaist, uct, kuleuven (label or twin questions for the owner);
warsaw (replay artefact).

On development, "never returned" is 3 of 39 gold cases (4 with kaznu). The approved heldout aggregates put that
class first on the nine; the development sets under-represent it, so nothing here says the query shape is fine —
only that replay cannot measure it.

## 3. Ranked rule candidates

Ranking = hits recovered on the readable denominator per worker-hour; dispatches cost no worker time. CL-2 is being
built now and is listed for its share only.

| # | candidate | motivating cases (sets) | expected hits | worker h | hits / h | kind |
|---|---|---|---|---|---|---|
| 1 | **QT-1 — read the confirmed page's qualifier twin before stopping** | ubc (cohort), unsw (dev3); knockout tcd, ntu, psaclay share the shape | **+2** (both deterministic on replay) | ≈ 2.5 | 0.8 | recall (one extra read) |
| 2 | **CL-2** — head + slug identity is not `unknown`/`irrelevant` (in progress) | tec (dev2), unibo (dev4) | **+2** (unibo only in reps where `corsi.unibo.it` answers: 2/4) | ≈ 3 | 0.5–0.7 | recall (classifier) |
| 3 | **CC-1 — a course is never a programme lead** | iitd (dev3); frees reads on warsaw's `courses/view?prz_kod=` results, vut's `/study/course/<id>/`, kaist's course lists | **+1** (iitd; live precedent: the ledger's 17/20) | ≈ 2 | 0.5 | guard (refuses leads) |
| 4 | **D1 dispatch `--skip-refused-hosts`** (ER-04's flag, exists) | hku (cohort): 7/8 checks on a robots-refused host; aalto 8/8, ub 8/8, kaznu 3 | +0–1 (hku may enter the denominator and reach `www.cds.hku.hk`) | 0 (+0.5 reading) | — | guard |
| 5 | **D2 dispatch `--no-stage-budgets`** | ubc, unsw, uct: the cost of "stop at the first confirmation" | 0 directly; measures QT-1's control (§3.1) | 0 | — | measurement |
| 6 | LL-1 — listing follow-up links matched through R1's localized aliases, and a listing refused on a level-word head (`Бакалавриат`) treated as a catalogue | kaznu (dev2, excluded), msu (dev3), vut (dev4, related-only) | +0–1 (msu, only if its listing links `pk.cs.msu.ru`; unverified) | ≈ 3 | ≤ 0.3 | recall |
| 7 | Stage-clock trim — cap HTML "sitemap" documents and the navigation stage when nothing confirmed by 33 s | boun (dev4, related-only), usp (dev3, 1/4), kuleuven on#2 (sitemap 47 s) | +0 stable (usp is flaky) | ≈ 2 | ≈ 0 | guard (saver) |
| 8 | CQ-1 slash joiner ("A / B" as a combination) | unsw (dev3) only | +0 beyond QT-1; alone it risks confirming `bachelor-of-science-computer-science` (order #2, unlabelled) | ≈ 1 | — | deferred: one case |

Not ticketed: kaist (identity), uct (label), kuleuven (twin) → owner round, §5. Access cases → free-search 08.

### 3.1 Why "read the next candidate after a confirmation" is not the rule

The offline order shows what one more read would confirm: on ubc the next unread candidate is
`computer-science-okanagan-bsc` (a second campus, not abroad, so CG-1 passes; unlabelled → **wrong page**), and only
then the gold; on unsw it is `bachelor-of-science-computer-science` (unlabelled → wrong page), then the gold. A rule
that reads on by rank buys both hits with two new wrong pages and fails the default-on bar. The twin relation reads
exactly the gold on both cases and nothing else. D2 (`--no-stage-budgets`, which removes the stop and lets recovery
read up to 8 checks / 3 pages) is the free measurement of that cost and is dispatched as QT-1's control, not as a
candidate.

### 3.2 QT-1 — qualifier twin read after a confirmation (`CONFIRM_READS_QUALIFIER_TWIN`, `--read-qualifier-twin`)

**Shape.** In `_recover_search_pages`, when a candidate is confirmed and SB-1 would stop, look once through the
remaining unread queue for a *qualifier twin* of the confirmed URL: same host, same path up to the last segment, and
the twin's slug tokens are the confirmed slug's tokens **minus exactly one token** (unsw:
`bachelor-of-commerce-computer-science` → `bachelor-of-computer-science`), **or** with exactly one token swapped between
two entries of `_DEGREE_SLUGS[requested level]` (ubc: `computer-science-vancouver-ba` → `computer-science-vancouver-bsc`).
Read it (one check, metered like any recovery read), judge it with the same `profile_rejects`, keep it as a second
programme page when it passes, then stop as today. A twin that is unreachable (knockout 404, robots) or refused adds
nothing. Nothing else changes: no new query, no reorder, no change to the first confirmation.

**Evidence.** ubc: gold is order #3, the twin of order #1 by a degree-token swap; unsw: gold is order #3, the twin of
the confirmed page by one token removed. Both 4/4 on replay, both the same live. Under knockout the shape recurs on
tcd (`computer-science-jh` → `computer-science`), ntu (second-major pages → the plain page) and psaclay
(`l2-informatique` under `informatique`), where CQ-1/SP-1 now refuse the qualified page first.

**Overfitting guard.** No word table: slug tokens and the existing degree-slug table only. One read at most. The twin
passes the full predicate (CH-1, CQ-1, SP-1, CG-1). LOCO: without ubc the rule still fires on unsw (removal); without
unsw it still fires on ubc (swap). A twin candidate that differs by two tokens (`okanagan` + `bsc`) is not a twin by
construction.

**Replay acceptance** (4 normal + 4 knockout runs, `--read-qualifier-twin`): cohort ubc `related → hit` and dev3 unsw
`related → hit` in both on repetitions; **0 new wrong page on any set**, normal and knockout; `knockout_guess_cases_wrong`
not up; `reads_total` up by ≤ 1 on ubc and unsw and unchanged elsewhere; `cases_over_budget` 0;
`recorded_search_misses_discovery` equal to the off arm (regime A). Reject on the first new wrong page.

### 3.3 CC-1 — a course is never a programme lead (`COURSE_LEAD_GUARD`, `--course-lead-guard`)

**Shape.** In `catalog_walker.score_link` (shared by the walker and recovery's listing follow-up) a link is a hard
reject (`None`) when its label or its last slug token **starts with a course code** — one token of 2–4 letters
followed directly by 3–4 digits (`COL100`, `CSL102`, `COMP1511`) — or when its path has a `course`/`courses` segment
followed by a numeric or code-like segment or `view` (`/study/course/294207/`, `/courses/view?prz_kod=`). A programme
path such as `/courses/undergraduate/courses/computer-science/` (tcd's gold) has neither and is untouched; programme
codes with one digit (`S1-INF`) or digits only (`6999-…`, `3778 - …`) do not match.

**Evidence.** iitd: the `all-courses` listing queued `col100-…`, `col703-…`, `col863-…` ahead of the ranked results and
took three of the four checks that separated the gold (order #5) from the cap, in all four repetitions. Course pages
also took reads on msu (asvk courses) and ntutw, and fill warsaw's `field_and_degree` list (five `courses/view` rows)
and vut's lists — no hit moves there (gold never returned), but the reads are freed for whatever is next.

**Overfitting guard.** A pattern, not a word list; no university's code is named; the path rule needs an identifier
segment, so a `/courses/<programme-slug>/` path is never excluded. Guard by construction (refuses leads only); it must
lose no hit: tcd, imperial (`/study/courses/undergraduate/computing-beng`), auckland stay confirmed.

**Replay acceptance** (4 normal + 4 knockout): dev3 iitd `missed → hit` in both on repetitions (if the read gold is
refused instead, record the verdict: that is a CL-2/R1 fact, not CC-1's); no hit lost on any set; `reads_total` not up;
knockout rows unchanged; 0 new wrong page.

### 3.4 CL-2's share (in progress; not duplicated here)

tec and unibo are the only "read but refused" golds whose head plausibly carries the alias and the level (the English
twin "BS in Computer Science and Technology" with a `bs-in-…` slug; `laurea/informatica`). kaist's gold has neither and
is outside CL-2 by the ticket's own precondition. Share: **2 of the 12 readable-denominator losses**, on two sets, with
unibo counted only in the two repetitions where its host answers. Its replay acceptance stays as written in the replay
plan §5.3 (0 new wrong page; knockout guesses not above the CH-1 arm).

## 4. Misses only new queries could test, and the minimal free-tier budget

The owner has created no keys yet. Order: Exa (free credit, no card) and Tavily (1 000 credits a month) first, under
ticket 02's per-run cap; Serper only if the owner tops up. Queries are the six public families `queries_for` builds
(institution, domain, "computer science", bachelor, country), as ticket 03 specifies; no applicant word.

| case | set | the list must return | queries |
|---|---|---|---|
| msu | dev3 | `pk.cs.msu.ru/bak_educational_programs` | 6 (the Russian family included) |
| ntutw | dev3 | `www.csie.ntu.edu.tw/zh_tw/Admission/Announcement12` | 6 (the Chinese family included) |
| hku | cohort | `www.cds.hku.hk/prospective-students/undergraduate-old-2026/6999-computing-and-data-science` (the readable form) | 6 |
| itu | dev4 | `bm.itu.edu.tr/…/bilgisayar-muhendisligi/genel-bilgiler` or its English twin (related-only) | 6 |
| vut | dev4 | `www.vut.cz/en/students/programmes/programme/10326` (related-only) | 6 |
| warsaw, ubc, uct, unsw, unibo, boun, kaznu | all | the unrecorded second pass (`programmes`, `courses`, `undergraduate` or `admissions`) | 3 each = 21 |
| kaznu | dev2 | `welcome.kaznu.kz/…/speciality/1730` (optional: the site is unreadable from the runner) | 6, optional |
| tsinghua | dev2 | nothing under `site:tsinghua.edu.cn` can return `join-tsinghua.edu.cn`; one probe documents it | 0 (6 optional) |

**Minimal budget: 51 queries per provider** (30 for the five never-returned readable cases + 21 for the second
passes), **102 across Exa and Tavily, $0** (Exa 2 500 instant searches a month, Tavily 1 000 credits). One repetition
is enough for a keyword index; a second Exa repetition for variance adds 51 (≤ 153 in all). The full ticket-03
comparison (44 cases × 6 = 264 per provider) remains the honest Serper comparison; this is the subset that tests the
misses named here. Record **titles** with the URLs (§0.1) so the lists also extend the replay store faithfully.

## 5. Owner questions (batched; work continues on everything else)

| # | question | recommendation | why |
|---|---|---|---|
| Q1 | uct: the signed gold `sit.uct.ac.za/bsc-degrees` is the School's BSc listing; discovery now confirms `ba-informatics` and labels BBusSc / BCom as related. Keep `bsc-degrees` as gold, or add the BSc listing's own CS entry and let `ba-informatics` stay related? | a 20-minute worker check of what `bsc-degrees` lists, then your call | even when read, CH-1 refuses a head that names no subject; no generic rule reads it as the programme page |
| Q2 | kuleuven: is `www.kuleuven.be/programmes/opleidingen/bachelor-informatica` a twin of the `onderwijsaanbod` entry (redirect or hreflang)? | worker hand-check (dev case; production User-Agent after robots.txt), then sign the twin or keep the wrong | replay plan §2 asked the same; the page is confirmed in both readable repetitions |
| Q3 | kaist: the gold is a department page without a programme title; search never returns it and the classifier cannot name it | keep as residue (department host / opaque URL), as the 18-Q1 record says | a rule that accepts it would accept every department page |
| Q4 | keys for Exa and Tavily (01-Q3) so the 51-query probe of §4 can run | yes | the only way to test msu, ntutw, hku-cds and the second passes |

## 6. Worker tickets (top three; CL-2 is already dispatched)

Common to all: design on the four development sets and code only; no dev5 or heldout page, label, capture or row;
flag off by default, `store_true` harness flag plus a `NEGATABLE_RULES` entry; HANDOFF §8 line; golden demo
byte-identical (`UNIMATCH_DEMO_MODE=true UNIMATCH_ENABLE_BROWSER_TIER=false python seed_demo.py`, brief §5.7 order);
gates green; commit locally in the worktree; the main session cherry-picks and dispatches the replay runs.

### T1 — QT-1 qualifier twin (worker, effort medium, ≈ 2.5 h)

- **Files:** `backend/app/adapters/discovery/live_discovery.py` (`_recover_search_pages`: the confirmation branch and
  SB-1's stop; a pure helper `qualifier_twin(confirmed_url, candidates, level) -> str | None` beside
  `_read_subpage_parent_next`; flag `CONFIRM_READS_QUALIFIER_TWIN = False`), `backend/evaluation/research/live.py`
  (`--read-qualifier-twin`, `NEGATABLE_RULES`), new `backend/tests/test_qualifier_twin.py`, HANDOFF §8.
- **Tests:** helper — `/programs/x-vancouver-ba` with candidates `/programs/x-vancouver-bsc` (twin: degree swap) and
  `/programs/x-okanagan-bsc` (two differences: none); `/study/ug/bachelor-of-commerce-computer-science` with
  `/study/ug/bachelor-of-computer-science` (twin: removal) and `/study/ug/bachelor-of-science-computer-science` (none);
  a twin on another host (none); recovery — fake fetcher: twin confirmed → two pages, one extra read; twin refused by
  `profile_rejects` → one page, one extra read; twin 404 → one page; flag off → byte-identical trace; the demo order.
- **Acceptance:** §3.2. Runs: `expert_paired`, `search_provider=recorded`, `extra_args=--read-qualifier-twin`, four
  sets; then the same with `--knockout-gold <set file>` in `base_args`.

### T2 — CC-1 course lead guard (worker, effort medium, ≈ 2 h)

- **Files:** `backend/app/adapters/discovery/catalog_walker.py` (`score_link`: the two patterns, behind
  `COURSE_LEAD_GUARD = False` in `live_discovery.py` so the flag table stays in one module), `live.py` flag
  `--course-lead-guard`, tests in `backend/tests/test_catalog_walker.py` (labels `COL100 Introduction to …`,
  `CSL102`, `COMP1511 …` → `None`; `Computer Science`, `S1-INF`, `6999 Computing and Data Science`, `3778 - Bachelor
  Computer Science` → scored; paths `/study/course/294207/`, `/courses/view` → `None`; `/courses/undergraduate/courses/
  computer-science/`, `/study/courses/undergraduate/computing-beng` → scored), HANDOFF §8.
- **Acceptance:** §3.3. Same run plan as T1.

### T3 — dispatches, no worker (main session, ≈ 0.5 h reading)

- **D1** `extra_args=--skip-refused-hosts` on the four sets (regime A). Read: hku's `access` cell and whether it enters
  the readable denominator; `programme_found_on_readable`; `reads_total`; no hit lost. The flag's rule was recorded
  neutral on 2026-09-27 (ER-04, before UA-1 and the recovery read cap); the new evidence is the per-case check counts
  above (hku 7/8, aalto 8/8, ub 8/8 on refused hosts). Default-on only on a stable gain; otherwise record the replay
  table in `hypotheses.json` and leave ER-04 rejected.
- **D2** `extra_args=--no-stage-budgets` on the four sets (regime B: `recorded_search_misses_discovery` may rise where
  pass 2 is unrecorded). Read as QT-1's control only: how many pages recovery confirms when it reads on by rank, and
  how many of them are wrong (ubc's `okanagan-bsc`, unsw's `bachelor-of-science-computer-science` are the predictions).
  No default changes from this run.

## 7. What this does not change

The DoD targets and denominators are unchanged. Targets 3 and 4 stay "not met" on development; the replay baseline's
absolute claim numbers are below live (regime C, replay plan §1.3) and are not compared here. No rule is attempted on
the access class, the other-registrable-domain class or the department-host class (01-Q4 stopping rule), and no rank
rule is fitted to the URL-only order (§0.1).
