# Residue ledger — every remaining development loss on targets 3 and 4, by name and class (finish-algorithm ticket 16)

Date 2026-10-18 · planner, read-only on captures · ticket
[16](wayfinder/finish-algorithm/issues/16-residue-ledger.md) · feeds [17](wayfinder/finish-algorithm/issues/17-clean-baseline-3-development-exit.md)
(exit gate) and pre-fills [18](wayfinder/finish-algorithm/issues/18-escalation-unreachable-targets.md) (Table C).

**Evidence.** The latest cycle's scored captures: five paired runs per set (FP-1, EF-1, PL-1, DI-1, evidence bundle), all
built on pipeline `47e250b8`, 2 repetitions per arm → **20 repetitions per set**; the `off` arms are today's defaults minus
FP-1 / QH-1 / AN-1, each `on` arm adds one flag. Scored by `evaluation.research.scorecard` with the readable denominator
(01-Q2) and per-repetition `unavailable` (01-Q3) against `ground_truth.reviewed11`, `dev2-draft2`, `dev3-draft2`, and
`dev4-draft2` (re-scored here with `--allow-drafts`; **unsigned**, ticket 09). Earlier `base2` / `ap1c` captures are used
only for stability context. Aggregation script and its outputs: `scratchpad/ledger16/{aggregate.py,agg_*.md}` (heldout ids
excluded by name; no heldout file, capture, log or label opened). Classes are the map's stopping-rule classes (01-Q4), with
`CORE_GAP_ANALYSIS_2026-10-18.md` cause codes in brackets.

**Pending while this was written** (their runs are dispatched; their verdicts are *expected* here, not typed as results):
EF-1 (+2 repetitions), DL-6 (Uppsala international round), SC-2 (unsw wrong_scope under diagnosis), PDF map 04 / 06
(PD-1, PD-2). QH-1 + AN-1 are on by default since the cycle (their gain is in the `evb.on` columns and is counted below).

## 0. Headline — what the scorecard rows read on the latest cycle

| set | programme page on readable (range over 20 reps) | wrong programme pages | known core answered (all) | known core answered (readable) | readable rate range |
|---|---|---|---|---|---|
| cohort | 5/8 … 7/8; 5/5–6/6 in reps where hku and ubc are `unavailable` | 0–2 | 10–14/27 | 10/13 … 14/17; 13–14/19 when hku's host answers > half | **0.68–0.82** |
| dev2 | 3/5 … 5/6 | 0–1 | 3–5/21 | 3/14 … 5/14 (uppsala out) ; 3–4/17–18 | **0.17–0.36** |
| dev3 | 7/10 … 9/9 | 0–2 | 5–8/22 | 3/13 … 8/18 | **0.23–0.50** (0.44 typical) |
| dev4 (unsigned) | 2/4 … 4/5 | 0–1 | 2/9 | 2/9 | **0.22** |

Pooled, a typical repetition: **28 of ≈ 63 readable questions (≈ 44 %)**; on the old denominator 28/79 (35 %). Every target-3
and target-4 row is **NO** on every set and arm (cohort target 4 reads YES only in repetitions where hku's host fails ≥ 50 %
and leaves the denominator — 14/17 = 0.82; when hku answers 9/25, the same answers read 14/19 = 0.74).

Targets 1, 2, 5 stay met on every set except: **target 1 on dev2** fails in every repetition that reads Uppsala's programme
page (`deadline` 2027-04-15 against the signed international round 2027-01-15; precision 0.86–0.90) — DL-6's run decides it;
and one `wrong_scope` pair on unsw (SC-2 `on` arm, one repetition) — SC-2 stays off.

## 1. Table A — target 3, the programme page on readable sites

Outcome over the latest 20 repetitions; `excluded` = repetitions where 01-Q3 took the case out as `unavailable`.

| case | set | outcome (n/20) | excluded | class | ticket that tried | verdict |
|---|---|---|---|---|---|---|
| aalto | cohort | miss 20 | 20 | **access** (19/20 failed, robots) | — | `unavailable` by definition |
| toronto | cohort | miss 20 | 20 | **access** (future.utoronto.ca 403 on 21–23/23) | A (11) | `unavailable` by definition; W↔M flip gone (FP-1) |
| hku | cohort | miss 18, hit 2 | 8 | **access** (admissions host; 9–16/25 failed, flips the 50 % line) + **provider rank** (gold at `field_and_degree` 1 vs 3) | A (11); RK-2 rejected; 05/06 "no rule" | residue — stop rule met (two attempts on the same cause) |
| kaist | cohort | miss 20 | 6 | **department host / opaque URLs** (`cs.` host, walker `short_label`; 15/16 failed in 2 reps) | A (11); DI-1 rejected | residue (named class) |
| ubc | cohort | miss 14, hit 6 | 1 | **degree word** — BA page outranks the BSc gold, both from two families | 05/06: "needs a degree-word rule, not a rank rule" | **ours-still** (0 core questions behind it: ubc's four are answered from other pages) |
| tcd | dev2 | hit 14, miss 6 (off 6/10, on 8/10) | 0 | **order / lead slot** (gold rank 1 in three families; the `-jh` sibling confirmed first) | A (11): FP-1 on, EF-1 +2 reps pending | ours, flaky — pending EF-1's verdict; stays in the denominator under 01-Q3 |
| uppsala | dev2 | hit 16, miss 4 | 4 | **host flakiness** (BLOCKED / 14/16 failed in the 4 missed reps) | — | `unavailable` in those reps (01-Q3) — no loss |
| tsinghua | dev2 | miss 20 | 0 | **other registrable domain** (`join-tsinghua.edu.cn`; gold never seen) | B (12); DI-1 rejected | residue (named class) |
| unsw | dev3 | hit 16, miss 4 | 0 | **provider rank** (gold `field_and_degree` 1 vs 3; commerce page confirmed) | 05/06 "no rule"; RK-2 rejected | residue — stop rule met |
| iitd | dev3 | hit 17, miss 3 | 0 | **provider rank** (gold `natural_language` 8 or absent) | B (12); 05/06 | residue — stop rule met |
| kuleuven | dev3 | miss 20 | 16 | **access** (subhost robots time out, 16/20 reps); in the 4 reachable reps the gold is `returned` (`local_language` 2) and never read | B (12) | `unavailable` 16/20; residue (returned-not-read) 4/20 |
| ub | dev3 | miss 20 | 20 | **access** (Cloudflare challenge, 13–15/20 failed) | B (12) | `unavailable` by definition |
| puc, uio | dev3 | miss 1 each | 0 | **stage clock** (55 s discovery deadline; sitemap stage 46–51 s) | fog "stage order on slow hosts" | ours, flaky (1/20) — not worth a rule on its own |
| ctu | dev4 | miss 14, hit 6 | 0 | **returned, not read** (gold only at `local_language` 5; lead slots spent on `bilakniha`/`fel`) | B (12); 05/06 "no rule"; EF-1 pending | residue — stop rule met (RK-2, RA-1) |
| unibo | dev4 | miss 20 | 2 | **returned, not read** (one-family English sibling ranked first; the related CSE page no longer confirms) | 05/06 "no rule" | residue — stop rule met |
| rwth | dev4 | hit 18, miss 2 (on 10/10) | 0 | **order** (single lead, walker eats the clock) | 05; FP-1 on | ours, flaky — stable on the `on` arms |
| tec, kaznu, uct, khalifa, utokyo, ntutw, msu, usp, vut, taltech, boun, itu | dev2–4 | unlabelled 20 | kaznu 20, khalifa 12, utokyo 2 | **no programme label** (ticket 10) | E (15) delivered proposals | enter the denominator only when 10 is signed — see §3 |

**Reading.** On readable sites the page is found stably on 22 of the 26 labelled cases that let us read them at all; the
four stable misses are kaist, tsinghua, ctu, unibo — every one in a named class with the stop rule met (two rank rules
rejected: RK-2 in a run, RA-1 before build) or a class the map declared unreachable (department host, other domain). The
"worst repetition" additionally fails on the flaky ours cases (tcd, unsw, iitd, hku, rwth, ubc): 01-Q3 keeps them in the
denominator on purpose. **No single rule flips target 3 on any set**, because every set has at least one stable residue
miss (cohort kaist, dev2 tsinghua, dev3 kuleuven-when-reachable, dev4 ctu/unibo).

## 2. Table B — target 4, the six core questions on readable pages

Question level (the scorecard's row). "answered n/20" and "in denominator n/20" from the latest cycle. Classes: **access**,
**other registrable domain**, **SPA/PDF-only**, **client-rendered list / not linked**, **department host**, **non-English
evidence** (08: build nothing — `pending_08` closed as residue), **gold identity / prose label**, **returned-not-read**,
**host flakiness**, **ours-still** (names the function).

### cohort — 27 known questions; readable 17–19; answered 14 (10 in one rep)

| case | question | answered | in denominator | class [cause] | tried | verdict |
|---|---|---|---|---|---|---|
| groningen | cost, deadline, english | 20/20 ×3 | 20/20 | hit | — | — |
| groningen | scholarship, schol._international | 0/20 ×2 | 20/20 | **client-rendered list** [A1] — `rug.nl/education/scholarships` static HTML has no link to `nl-scholarship`; sitemap 5 MB cap; award query returns other pages | C (13), SQ-1 | residue (named class) |
| delft | cost, deadline, english | 20/20 ×3 | 20/20 | hit | — | — |
| aalto | cost, deadline | 0/20 ×2 | 0/20 | **access** | — | out of the denominator |
| warsaw | scholarship | 0/20 | 20/20 | **department host never linked** [A1/A6] — `bpm.uw.edu.pl/en/rectors-scholarship/` (English) is linked from no page we read and returned by no query; funding reads `welcome.uw.edu.pl` | C (13) | residue (named class) |
| warsaw | schol._international | 0/20 | 0/20 | **PDF** (Polish regulation on `monitor.uw.edu.pl`) | PDF map | out; re-enters under PDF 01-Q3 when PD-1 is on (`pdf_unreached`, `pdf_non_english`) |
| ubc | english, scholarship, schol._international | 19, 17, 17 /20 | 19/20 | hit (flaky on the BA page's confirmation) | AP-1 | — |
| ubc | deadline | 14/20 | 19/20 | **ours — stage order** [A4]: the dates page is queued behind two english pages and fees; TB-1 refuses it with 20 s to reserve | DL-5 ordering | ours-still, flaky; 1 question; fog "stage order on slow hosts" |
| toronto | deadline, english | 0/20 ×2 | 0/20 | **access** | — | out |
| hku | scholarship (2 labels), schol._international | 2, 0 /20 | 12/20 | **access** (`admissions.hku.hk` robots unreachable) + **provider rank** (the cds page is confirmed 2/20; its award is heading-named in the nav-linked page) | A (11), AP-1, QR-2, AP-1c | residue: the first loss is the programme page (Table A) |
| ntu | deadline, english, scholarship, schol._international | 19/20 ×4 | 20/20 | hit (02-Q1/Q2 aliases; 1/20 flake) | 02 | — |
| kaist | cost, scholarship, schol._international | 0/20 ×3 | 0/20 | **access** (`admission.kaist.ac.kr` every request fails → `host_failed`) | — | out |

### dev2 — 21 known questions; readable 14–18; answered 3–5 (5 with QH-1/AN-1)

| case | question | answered | in denominator | class [cause] | tried | verdict |
|---|---|---|---|---|---|---|
| ethz | scholarship, schol._international | 0/20 ×2 | 20/20 | **client-rendered list / no link** [A1] — `financial/scholarships.html` static HTML links only "Financial" and two logins | C (13) | residue (named class) |
| uppsala | english | 16/20 | 16/20 | hit (host out 4/20) | EN-2b | — |
| uppsala | deadline | 0/20 (**wrong** 16/20) | 16/20 | **gold round / reader** [D3]: the programme page's national 15 April is read; the signed gold is the international 15 January on `/bachelors-studies/application` | 02-Q5; **DL-6 pending** | pending — expected hit + wrong claim 1 → 0 |
| uppsala | scholarship, schol._international | 0/20 ×2 | 16/20 | **not linked, not returned** [A1] — programme page links fees only; SQ-1's query returns a faculty degree-project award | C (13), SQ-1 | residue (same stop class as groningen/ethz: the page is one query away and the provider does not return it in 6) |
| tcd | cost, english | 20/20 ×2 | 20/20 | hit | FE-2b, EN-2b | — |
| tcd | scholarship, schol._international | 2/20 (both `evb.on` reps) | 20/20 | hit with QH-1 + AN-1 (now default) | C (13) | **expected stable hit on every later capture** (+2) |
| tsinghua | deadline, scholarship, schol._international | 0/20 ×3 | 20/20 | **other registrable domain** [A6] | B (12), DI-1 | residue (named class) |
| tec | english | 0/20 | 20/20 | **ours — classifier** [C1]: the English hreflang twin of the Spanish programme page is read 4/4 and rejected "not a programme page"; `72 points on the TOEFL iBT` is on it | 07 | ours-still, 1 question — but only after ticket 10 signs tec's programme page (today no programme label) |
| tec | scholarship | 0/20 | 20/20 | **non-English evidence** (Spanish `becas` page, never fetched) | 07/08 | residue (`non_english_no_route`) |
| tec | schol._international | 0/20 | 0/20 | **PDF** (English regulation PDF, never reached) | PDF map | out; re-enters with PD-1; PD-3 could reach it (+1) |
| uba | scholarship, schol._international | 0/20 ×2 | 20/20 | **non-English evidence** (`extension.uba.ar`, es-AR, never fetched; `.international = false` needs clause polarity) | 07/08 | residue |
| kaznu | scholarship, schol._international | 0/20 ×2 | 0/20 | **access** (certificates; 9/18 failed) | — | out |
| uct | english | 19/20 | 19/20 | hit (SO-1 flake 1/20) | — | — |

### dev3 — 22 known questions; readable 13–18; answered 8 (5 in one rep)

| case | question | answered | in denominator | class [cause] | tried | verdict |
|---|---|---|---|---|---|---|
| imperial | cost, deadline, english, scholarship, schol._international | 19–20/20 | 19/20 | hit (host out 1/20) | EN-2b, FE-2b, AP-1 | — |
| unsw | english | 0/20 (wrong_scope ×2 in SC-2 `on#1`) | 20/20 | **ours — table reader** [B2]: IELTS in the heading above a faculty table; SC-2 read the right value with a two-degree-level scope | EN-2b, **SC-2 pending diagnosis** | pending; 1 question; SC-2 has one failed run (a new wrong claim) — a second failure stops it |
| unsw | scholarship, schol._international | 0/20 ×2 | 20/20 | **other host, never returned** [A1/A6] — `www.scholarships.unsw.edu.au/scholarships/id/1988`; the award query returns a marketing page | D (14) | residue (named class: other host the programme page never links) |
| utokyo | deadline | 0/20 | 0/20 | **PDF** (Japanese guidelines) | PDF map | out |
| utokyo | scholarship, schol._international | 0/20 ×2 | 17/20 | **non-English evidence** (ja page; switcher-only English twin; no programme page in gold) | 07/08 | residue |
| ntutw | deadline | 0/20 | 20/20 | **other host + reader** [A3/C1 + B4]: `admissions.ntu.edu.tw` returned, read once as `unknown`; the window carries "(11AM)" inside the range; no programme page in gold | 10 pending | residue (two causes, one question) |
| um | english | 20/20 | 20/20 | hit | — | — |
| auckland | deadline, english | 20/20 ×2 | 20/20 | hit | DL-5, QR-2 | — |
| auckland | scholarship, schol._international | 0/20 ×2 | 20/20 | **index depth / read budget** [C2]: the award sits two levels below `find-a-scholarship`; 13–15 index reads refused per repetition | AP-1, AP-1c | residue: a deeper index chain adds reads for one case (01-Q5 rejects it) |
| msu | scholarship | 0/20 | 20/20 | **non-English evidence** (ru page `pk.cs.msu.ru/auslander_budget`, a state-funded place, not a named award; no programme page in gold) | 07/08 | residue |
| msu | schol._international | 0/20 | 0/20 | **PDF** (Russian rules) | PDF map | out |
| puc | deadline | 0/20 | 20/20 | **non-English evidence** (es calendar on `admision.uc.cl`, two windows) | 07/08 | residue |
| usp | scholarship, schol._international | 0/20 ×2 | 0/20 | **PDF** (Portuguese edital) | PDF map | out; PD-3 + per-language word could reach `exists` (+1) |
| chula | — | — | — | five ISE labels `not_applicable` (02-Q6) | 02 | out of the denominator by signature |
| um, ucph, msu | gpa | — | — | prose labels `unknown` (02-Q7) | 02 | out by signature |

### dev4 (unsigned, ticket 09) — 9 known questions; readable 9; answered 2

| case | question | answered | in denominator | class [cause] | tried | verdict |
|---|---|---|---|---|---|---|
| boun | english | 20/20 | 20/20 | hit | — | — |
| ktu | english | 20/20 | 20/20 | hit via TOEFL 75; the `ielts.overall` label (IELTS ≥ 5.5) is missed 20/20 — `_IELTS_OVERALL` has no "≥" alternative [B1] | EN-2b | reader gap, **0 questions** (answered by TOEFL) |
| ktu | gpa | 0/20 | 20/20 | **prose label** («60 % minimum average grade (CGPA) in each entry subject») — the 02-Q7 shape | 09 sign-off | corpus: `unknown` or a structured form (ask in 09) |
| ktu | scholarship, schol._international | 0/20 ×2 | 20/20 | **ours — unnamed award on a read index page** [B6]: `admissions.ktu.edu/bachelor/` is read in every repetition; "partial tuition fee waiver … open to all international applicants" has no proper award name, so AP-1's heading rule never fires | AP-1 | ours-still, 2 questions (22 pp of dev4) — a name-less award reader is the precision risk AP-1 was designed to refuse |
| rwth | scholarship | 0/20 | 20/20 | **binding / identity** [D1]: a `Bildungsfonds-Deutschlandstipendium` page is read, the label's evidence URL is the `Kosten-und-Finanzierung` page | 09 sign-off | corpus: add the award page as a second source URL (ask in 09) |
| vut | scholarship | 0/20 | 20/20 | **not linked / no programme page** [A1]: `vut.cz/en/students/scholarships` never reached; the case has no exact CS programme (related only) | 10 | residue |
| taltech | scholarship | 0/20 | 20/20 | **non-English evidence + reach**: the Estonian admissions page `taltech.ee/informaatika` is never read; the faculty twin (no admission facts) is read 6/20 | 07/08 | residue |
| ctu | english | 0/20 | 20/20 | **returned, not read** (Table A: the programme page is missed 14/20; the English admissions page is never fetched) | 05/06, EF-1 pending | residue (follows the page) |

### Totals per class (question level, in the readable denominator of a typical repetition)

| class | cohort | dev2 | dev3 | dev4 | pooled | reachable by a rule? |
|---|---|---|---|---|---|---|
| answered (stable) | 14 | 3 (+2 QH-1/AN-1) | 8 | 2 | **27 → 29** | — |
| pending rule (DL-6 uppsala deadline; SC-2 unsw english) | 0 | 1 | 1 | 0 | 2 | expected +1 (DL-6); SC-2 ±1 |
| client-rendered list / not linked, not returned [A1] | 2 (groningen) | 4 (ethz 2, uppsala 2) | 2 (auckland, index depth) | 1 (vut) | **9** | no (01-Q4 class; SQ-1 and AP-1c tried) |
| department host / other host never linked | 1 (warsaw) | 0 | 3 (unsw 2, ntutw 1) | 0 | **4** | no (01-Q4 class) |
| other registrable domain | 0 | 3 (tsinghua) | 0 | 0 | **3** | no |
| non-English evidence, no route | 0 | 3 (tec exists, uba 2) | 4 (utokyo 2, msu 1, puc 1) | 1 (taltech) | **9** | no (07: 0 reachable on today's captures; 08 → build nothing) |
| returned, not read (page) → question follows | 2 (hku, when readable) | 0 | 0 | 1 (ctu) | **3** | no (stop rule met: RK-2, RA-1) |
| ours-still | 1 (ubc deadline, flaky) | 1 (tec english, after 10) | 0 | 2 (ktu award, unsigned) | **4** | yes in principle; **none flips a target** (see §4) |
| corpus (prose label / binding alias), dev4 unsigned | 0 | 0 | 0 | 2 (ktu gpa, rwth binding) | 2 | corpus line in 09, not code |
| **readable denominator (typical rep)** | 17–19 | 18 | 18 | 9 | **≈ 63** | |
| out of the denominator: access | aalto 2, toronto 2, kaist 3, hku 3 (8/20 reps) | kaznu 2 | ub, kuleuven (no labels) | — | 12 (+3 hku in some reps) | `unavailable` by definition |
| out of the denominator: PDF | warsaw 1 | tec 1 | utokyo 1, msu 1, usp 2 | — | **6** | re-enter under PDF 01-Q3 when PD-1 is on; +0 answered today, PD-3 ≤ +2 |

Pooled rate today ≈ 28/63 = **44 %**; with QH-1/AN-1 counted and DL-6 passing: 31/63 = **49 %**; with every ours-still
item landed as well: 35/63 = **56 %**; with the pending-rule and ours-still items *and* every PDF label re-entered: 35/69 =
**51 %**. On the old denominator the same numerators read 28/79 → 35/79 (35 → 44 %).

## 3. Expected numbers after the pending rules and the owner's round 2

| change | status | expected movement | target rows affected |
|---|---|---|---|
| QH-1 + AN-1 on by default | done (this cycle) | dev2 known core readable 4/18 → **6/18** (tcd e3 ×2) | target 4 dev2 0.22 → 0.33 (still NO) |
| DL-6 `--international-round-deadline` | runs dispatched | uppsala `deadline` wrong → hit: dev2 **7/18**; wrong claims 1 → 0; dev2 precision back to 1.00 | **target 1 dev2 NO → yes**; target 4 dev2 0.39 (NO) |
| EF-1 `--exact-field-lead-first` +2 reps | running | ctu `programme.exists` flaky gain; tcd page 8/10 vs 6/10; 0 core questions | target 3 unchanged (ctu's page needs the gold read, which EF-1 does not do) |
| SC-2 `--coordinated-degree-scope` | diagnosis | if the two-level scope is fixed: unsw english +1 → dev3 **9/18 = 0.50**; if not, rejected (second failure = stop) | target 4 dev3 (NO either way) |
| PD-1 / PD-2 (PDF map 04, 06) + 07 re-entry | worker in progress | PDF labels re-enter the denominator (+6 questions, +0 answered today) → pooled rate **−3 to −4 pp**; PD-3 (05) could add ≤ +2 (tec intl, usp exists) only if PDF 02 finds the PDFs one link away | target 4 every set a little lower; honest |
| ticket 10 signed (12 programme labels) | round 2 | target-3 denominators grow by tec, kaznu (access → out), uct, khalifa (12/20 reps `unavailable`), ntutw, msu, usp, taltech (related), vut/boun/itu (related only, missed). Expected new outcomes on today's captures: tec **missed** (classifier rejects the EN twin), msu **missed** (ru page never returned), uct **wrong** (department hub) on the off arms / related on the on arms, khalifa and usp **hit**, ntutw missed | target 3 NO on dev2/dev3 by more cases; the new misses are residue by class (classifier → ours; other host; no CS programme) |
| ticket 09 signed (dev4 core) | round 2 | 9 known questions, 2 answered → **0.22**; after the corpus lines (ktu gpa `unknown`, rwth binding alias) 2/8 → 3/8 = 0.38 | target 4 dev4 NO; **target 6 proxy: dev4 0.22–0.38 against cohort 0.74–0.82 → 36–60 pp gap ≫ 15 pp** |

## 4. Are targets 3 and 4 reachable by rules at all (01-Q4)?

**Target 3 — no.** Every set has a stable miss in a class the map declared unreachable or on which two rank rules already
failed: cohort kaist (department host / opaque URLs) and hku (access + rank); dev2 tsinghua (other domain); dev3 kuleuven
in its reachable repetitions (returned-not-read) and unsw/iitd (rank); dev4 ctu and unibo (returned-not-read). The one new
rule shape never tried — a degree-word tie-break for ubc (BSc over BA) — would gain one cohort page and still leave kaist
and hku, so the cohort row stays NO. The flaky ours cases (tcd, rwth, uio, puc, uppsala's 55 s clock) belong to the fog item
"stage order on slow hosts"; a rule there would steady the worst repetition but flips no set either.

**Target 4 — no.** Of the ≈ 63 readable questions, **25 sit in named stop classes** (A1 not linked / client-rendered 9, other
host 4, other domain 3, non-English 9) and 3 follow a programme page in the returned-not-read class; the ours-still set is
**4 questions** (ubc deadline flaky, tec english after 10, ktu award ×2 unsigned), plus the two pending rules (≤ 2). The
ceiling with every one of them landed is ≈ 35/63 = 56 % (≈ 51 % once PDFs re-enter) — **24 pp short of 80 %**, on every set
but the cohort. The cohort alone reads 0.74–0.82 and is decided by whether hku's admissions host fails ≥ 50 % of its requests
in that repetition, i.e. by 01-Q3, not by a rule.

The binding loss is **reach, not reading**: 13 of the 16 non-English pages and all 6 PDFs are never fetched in any
repetition; the client-rendered and never-linked award pages are never fetched either. A reader of any kind (keyword table,
PDF text, model extractor) gains 0 on today's captures (07 §2, PDF map Notes). The only lever left that moves reach is a
provider parameter or a second runner — both are ticket 18 (c) options, not rules on this map.

## 5. Table C — pre-filled options for ticket 18 (per target; the owner picks one)

| target | (a) accept and record | (b) redefine the measure (exact DoD wording) | (c) one non-rule change | planner's recommendation |
|---|---|---|---|---|
| **3** programme page on readable sites | "not met; residue: department host / opaque URLs 1 (kaist), other registrable domain 1 (tsinghua), returned-not-read 4 (hku, ctu, unibo, kuleuven-when-reachable), provider rank 2 (unsw, iitd — flaky), degree word 1 (ubc), order/stage clock 3 (tcd, rwth, uio/puc — flaky)". Acceptance pre-registers programme recall on readable sites at the cohort's **5–6 of 7–8 (≈ 0.71–0.75)** and the pooled development **≈ 0.78** | "target 3 is met when the page is found in at least 3 of 4 repetitions on every readable site" — steadies the flaky cases only; **does not** change kaist/tsinghua/ctu/unibo. Not recommended | provider parameter `hl`/`gl` on the local-language family (M5 probe: gold in top 10 rises 4/6 → 5/6) — one paired run, touches `serper.py`/`intent.py`; predicted: ctu/unibo/uba order, not kaist/tsinghua. Or Track E (another runner) for the access class — infrastructure, out of this map | **(a)**; (c) `hl`/`gl` only if the owner wants one more *provider* experiment before 19 — it is not a rule and cannot reach the two named-class misses |
| **4** ≥ 80 % core questions on readable pages | "not met; readable rate ≈ 0.49 pooled (cohort 0.74–0.82, dev2 0.39, dev3 0.44–0.50, dev4 0.22); residue: not linked / client-rendered 9, non-English 9, other host 4, other domain 3, returned-not-read 3, ours-still 4, PDF 6 (out until PD-1)" | exclude from `core_known_readable` "a label whose evidence page the pipeline never fetched and that no page it read links" — removes 25 questions → 31/38 = **0.82 pooled** but turns target 4 into "answered where we happened to look"; the DoD's "publishes the answer and lets us read it" is exactly those pages. Not recommended. Narrower: exclude non-English only (−9) → 31/54 = 0.57: still NO | model extractor under D9 (07 §3: ≈ $0.005–0.01 per university at the smallest tier, ≈ $1 per four-set paired run; privacy row "official page text + question names"): reaches ≤ 7–8 non-English + ≤ 3–4 PDF questions **only once the pages are fetched** — today 0. Needs a reach change first (PD-3 for PDFs; nothing on this map for other-host award pages) | **(a)**, with 18-Q3 = yes (run 19 with the residue pre-registered). Open (c) as its own map only together with a reach rule; alone it buys nothing measurable |
| **6** heldout within 15 pp of cohort (pre-register, not escalate) | the dev4 proxy says core coverage on the nine's countries reads **0.22–0.38 against 0.74–0.82** — pre-register "expected not met; residue classes expected: returned-not-read, non-English, unnamed award, no exact CS programme" | compare the nine with the pooled development rate (≈ 0.49) instead of the cohort's — a dated DoD line the owner must sign; honest, since the cohort is the English-site set | — | pre-register both readings in 19; ask the owner in round 3 whether target 6's reference is the cohort or the pooled development sets |

## 6. PDF residue (hand-off from the PDF map's ticket 10, by class)

| label (set) | class | in denominator today | after PD-1 default-on (PDF 01-Q3) |
|---|---|---|---|
| warsaw `rektora.applicability.international` (cohort) | `pdf_unreached` + `pdf_non_english` (pl) | no | yes, unanswered unless PD-3 reaches it and a model reads the clause |
| tec `beca.applicability.international` (dev2) | `pdf_unreached` (English PDF) | no | yes; PD-3 + AP-1 could answer it (+1) |
| utokyo `deadline` (dev3) | `pdf_unreached` + `pdf_non_english` (ja, two windows) | no | yes, unanswered |
| msu `state_funded.applicability.international` (dev3) | `pdf_unreached` + `pdf_non_english` (ru) | no | yes, unanswered |
| usp `papfe.exists`, `.applicability.international` (dev3) | `pdf_unreached` + `pdf_non_english` (pt) | no | yes; `exists` reachable by PD-3 + one word (+1), `.international` needs clause polarity |

None of the six appears in any capture of this cycle (checked by the scorecard's `pdf` exclusion on every repetition). The
`pdf_reader_gap` class is empty: no English text PDF was reached and misread. Verdict for the PDF map: residue by class;
PD-1/PD-2 are product hygiene (≈ 30 wasted PDF reads per set become classified pages), not target movers.

## 7. Verdict

**Go to 17.** Nothing ours-still remains that can change a target's verdict: the four ours-still questions and the one
ours-still page (ubc) lift no set to 80 % or to "every readable site", and each named-class loss has its class, its ticket and
its stop recorded above. The three rules already dispatched (EF-1 +2 reps, DL-6, SC-2 diagnosis) finish under the cycle-4c
delegation and are read in 17's baseline; **no new rule is started** on this map. If the owner nevertheless wants one more
rule before 17, the single candidate with a measurable gain is the **unnamed-award reader for ktu (+2 dev4 questions, +22 pp on
the target-6 proxy)** — and it waits for ticket 09's signature, so it is an 18 option, not a rule today.

## 8. The shortest path to clean baseline 3 (17) and the acceptance run (19)

1. **Now, no owner needed:** let EF-1's two extra repetitions, DL-6's four runs and SC-2's diagnosis finish; judge each by the
   delegation (no stable loss, no new wrong claim). Expected: DL-6 on (dev2 precision 1.00), EF-1 on or rejected on ctu's flake,
   SC-2 rejected on a second wrong_scope or on after a scope fix. PD-1/PD-2 land when their worker finishes (hygiene; their
   paired runs may run beside 17's baseline, since they move no known question).
2. **Owner round 2 (one sitting, `OWNER_QUESTIONS.md`):** ticket 10's twelve programme labels, ticket 09's dev4 core table,
   ticket 08 (build nothing). Apply the signed lines, re-score the frozen captures (no run), record the new denominators.
3. **17 — clean baseline 3:** one `expert_paired` run per set with both arms = defaults (`extra_args` and `base_args` empty), on
   the commit after DL-6's verdict; four identical repetitions per set, ≈ 25 min wall clock in parallel. Read the six target
   rows on the worst repetition after 01-Q3 exclusions. Expected: targets 1, 2, 5 **met** on all four sets; targets 3 and 4
   **not met** on every set (cohort target 4 borderline on hku's access). Attach this ledger by reference.
4. **18 — one sitting:** Table C above, recommended (a), (a), 18-Q3 yes; plus the target-6 reference question (cohort or pooled).
5. **19 — the heldout look:** pre-register from 17's table (programme recall on readable sites ≈ 0.71–0.78; readable core rate
   cohort ≈ 0.74–0.82, pooled ≈ 0.49, dev4 proxy ≈ 0.22–0.38; expected `unavailable` ≈ 2–3 sites of nine by the development
   access share; residue classes by count only). Dispatch once, `case=heldout`, `extra_args=--through-identity-gate`, 2 reps per
   arm; read aggregates only — the scorecard has no `--summary-only` option today, so ticket 19 step 3 applies: a worker adds
   that one flag (metric and target rows, per-case table suppressed) before the heldout artifact is scored; update the DoD
   status table and the map.

Wall clock from here: round 2 sitting + ≈ 25 min (17) + round 3 sitting + ≈ 25 min (19) + scoring — no rule on the path.
