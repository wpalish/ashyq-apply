# Next cycles plan, 2026-10-19 evening: cycles 11–13

Planner, after the day-end replay baseline (loop report 17:55; artifacts `rp-base3-{cohort,dev2,dev3,dev4}` and
`rp-base3-ko-*`, `search_provider=recorded`, store `recorded_search.base3.json`, seven rules on by default: UA-1,
CH-1, CQ-1, SP-1, CC-1, QT-1, CL-2). Scored here with `scorecard` and `stage_summary` on the signed corpora (cohort
`ground_truth.reviewed11`, dev2/3/4 `draft3`), with the per-case traces (`<case>.raw.json`, `<case>.log`) and the
live base3 captures (`scratchpad/runs/base3-*`) read beside them. **Development cases only: no heldout file,
capture, log or label was opened; dev5 was not opened for design; no provider was called; no paid credit was
spent.** The scripts are in the session scratchpad (`plan19/claimstages.py`, `plan19/diag.py`); nothing from them
is committed.

Constraints this plan is written under: paid search frozen; Exa and Tavily keys not yet created (free-search
01-Q3); every provider run needs `--max-search-queries` (free-search 02); a live capture now logs every request with
titles and snippets (`search-log/1`) and the recorded store loads `recorded-search/2`; the product answers from the
KB (98 universities, 322 facts).

## 0. Where we stand

| set | gold cases | hit / wrong / related / missed (×2 on reps) | `programme_found_on_readable` | known core readable | knockout wrong (on) |
|---|---:|---|---|---|---|
| cohort | 10 | 5 / 0 / 0 / 5 | 5/7 (aalto, toronto, hku out: access) | 12/17 | 0 |
| dev2 | 10 | 6 / 0 / 1 / 3 | 6/9 (kaznu out) | 3/18 | 1 (tcd) |
| dev3 | 14 | 10 / 1 / 0 / 3 | 10/13 (ub out) | 8/18 | 2 (uio; kuleuven flake) |
| dev4 | 5 (+4 related-only) | 5 / 0 / 1 / 3 | 5/5 | 0/8 | 1 (ctu) |
| **all** | **39** | **26 hits**, 0–1 wrong | 26/34 | **23/61 ≈ 0.38** (live base3 ≈ 0.49) | **3–4** |

Claim precision is 1.0 on every set; wrong scope 0; cases over budget 0. The pooled known-core rate is below live
because topic, scholarship and identity searches miss on replay (regime C, replay plan §1.3). §1.3 says exactly which
labels that costs.

## 1. Search algorithm

### 1.1 The 13 remaining misses: loss stage and what could move each

Twelve of 39 gold cases are missed and one is `related` (uct). The stage is read from the trace of the on arm; both on
repetitions agree on every case.

| # | set | case | denominator | stage | what the trace shows | fixable on replay? | needs search? | owner? |
|---|---|---|---|---|---|---|---|---|
| 1 | cohort | aalto | out (BLOCKED 19/19) | unreadable: robots.txt times out → RFC 9309 disallow for the site | gold returned by three families, every lead `robots_disallowed`; 1 read | no | no | no: vantage point (free-search 08) |
| 2 | cohort | toronto | out (21/22 failed) | unreadable: HTTP 403 on both hosts | gold returned by `programmes`, unresolved; UA-1 holds the satellite page as `unresolved_access` | no | no | no |
| 3 | cohort | hku | out (13/24 failed) | unreadable: `admissions.hku.hk` robots unreachable | 7 of 8 recovery checks spent on the refused host; the readable `www.cds.hku.hk` form never returned | no (D1 `--skip-refused-hosts` read neutral on 2026-10-19) | **yes**: the cds form, 6 queries | no |
| 4 | cohort | kaist | **in** | read but refused (`unknown`) | the department's `content?menu=318` and 8 other `cs.kaist.ac.kr` pages all read `unknown`; the gold has no programme title, no level in head or slug | no | no | **Q4**: keep as residue (department host / opaque URL, 18-Q1 class) |
| 5 | cohort | warsaw | **in** | **replay artefact** (MISS_STAGES §0.1) | gold is `local_language` rank 2 and 9 but scores 0 on URL words, so order > 10 on a URL-only store; live base3 read it first and hit 4/4 | **yes, by a v2 store** (titles), not by a rule | no | no |
| 6 | dev2 | kaznu | out (13/19 failed) | unreadable + never returned | `www.kaznu.kz/robots.txt` ConnectError; listing parent refused as `program_catalog`, its Russian cards not followed | no (LL-1 is built, flag off; the case is excluded anyway) | 6 queries, optional | no |
| 7 | dev2 | tec | **in** | read but refused (`irrelevant`), **CL-2 did not move it** | the English twin `bs-in-computer-science-and-technology` reads no level: "B.S." and the slug `bs` are not in the degree tables (DA-2 verdict: one set only, do not add); the Spanish gold never returned; pass 2 returns the same page under `?srsltid=` variants | no | **yes**: the Spanish gold, 6 queries | **Q5**: accept as residue until a second set shows "B.S." |
| 8 | dev2 | tsinghua | **in** | never returned: other registrable domain | `international.join-tsinghua.edu.cn` cannot come back under `site:tsinghua.edu.cn`; the homepage links to it were dropped `off_domain`; DI-1 rejected | no | no (a domain decision) | no (residue class, 18-Q1) |
| 9 | dev2 | uct | **in** (related) | returned, not read + label question | recovery read BBusSc and BCom (R2 related, correct), refused the department page (CH-1), confirmed `ba-informatics` (labelled related) → stop; gold `bsc-degrees` is `field_and_degree` 2 / `programmes` 3, order #5, never read; its head is a BSc listing, which CH-1 would refuse | no rule should accept a listing head | no | **Q1**: is `bsc-degrees` the programme page, or `ba-informatics`? |
| 10 | dev3 | kuleuven | out in 2 of 4 reps; **wrong** when readable | twin question | `www.kuleuven.be/programmes/opleidingen/bachelor-informatica` confirmed (head "Bachelor in de informatica", level and subject present); gold is the `onderwijsaanbod` catalogue entry, order > 10 on URL words | no | no | **Q2**: redirect / hreflang check, sign the twin or keep the wrong |
| 11 | dev3 | msu | **in** | never returned | `pk.cs.msu.ru/bak_educational_programs` in no family; two bachelor listings read and refused on subject | LL-1 replay may follow the listing's cards (+0–1, unverified) | **yes**: 6 queries, Russian family | no |
| 12 | dev3 | ntutw | **in** | never returned | `csie.ntu.edu.tw/zh_tw/Admission/Announcement12` in no family; the admissions page read in recovery reads `unknown` | no | **yes**: 6 queries, Chinese family | no |
| 13 | dev3 | ub | out (14–15/16 failed) | unreadable: timeout, then robots ConnectTimeout | gold returned rank 1–2 by three families, 8 leads unresolved | no | no | no |

Summary. **Fixable on replay by a rule: none of the 13.** The replay has done what it can after search: of the five
post-search losses MISS_STAGES §2 called fixable (ubc, unsw, iitd by QT-1 and CC-1; tec, unibo by CL-2), four are hits
now and tec is not (row 7). What is left splits into: access from
this vantage point 5 (aalto, toronto, hku, kaznu, ub — unavailable by definition, outside the denominator); never
returned by the recorded lists 3 (msu, ntutw; tsinghua is a domain, not a query); label / twin / identity questions 3
(uct, kuleuven, kaist); a classifier residue with one-set evidence 1 (tec); a replay artefact 1 (warsaw). The
readable-denominator ceiling of a v2 store plus owner answers is 26/34 → 27/34 (warsaw) → up to 30/34 if the owner
signs uct's and kuleuven's twins and accepts kaist as residue; only msu, ntutw and tec need new queries.

### 1.2 Knockout guesses left (gold hidden, on arm): 3 cases + 1 flake

| set | case | page confirmed with the gold hidden | head | why no on-by-default rule refuses it | what would |
|---|---|---|---|---|---|
| dev2 | tcd | `tcd.ie/scss/courses/undergraduate/computer-science` | the School's page for the **same degree** | it is not a guess: the School of Computer Science and Statistics publishes its own page of the gold programme | **Q3**: sign it as a twin of the gold (`programme_url_aliases`) — then the knockout count falls to 2 + flake with no rule |
| dev3 | uio | `uio.no/studier/program/informatikk-ledelse` | "Informatikk: digital økonomi og ledelse (bachelor)" | R2 tests the subject head before `:` only; the related-field subtitle is not read | GOLD_KNOCKOUT candidate 3 (related-field subtitle = specialisation); one case, needs a second set before build — none has appeared |
| dev4 | ctu | `fit.cvut.cz/en/applicants/admissions-procedure/bachelor-study-program` | "Bachelor's degree programme Informatics" (h1), title "Bachelor study program" | SP-1's process nouns look at the head; this h1 names the programme itself, the process is in the URL and title only | SP-1b: process noun in the title's first part or the URL path (`admissions-procedure`, `application`) when the h1 carries no qualifier; still one set (dev4: ctu, and rwth's "Application for the B.Sc." in the same set) — below the two-set bar |
| dev3 | kuleuven | as §1.1 row 10 | — | host-flaky; same page off | Q2 |

The guard rules have taken the knockout from 8 guesses to 3 (one of which is a twin). No further guard is attempted
without a second set; §1.4 ranks nothing against uio or ctu.

### 1.3 Claim recall: where the known core labels are lost after the programme page

Every known core label of the four signed corpora (`ielts.overall`, `english_evidence.*.minimum`, `gpa`, `deadline`,
`tuition`, `scholarships.*.exists`, `scholarships.*.applicability.international`; 86 labels), per label, on the replay
on#1 repetition, with the live base3 fetch of the same evidence URL beside it. "Reached" means the label's evidence URL
was fetched `ok` in the capture.

| loss class | labels | sets (cases) | measurable on replay? |
|---|---:|---|---|
| **hit** | 27 | cohort 13, dev2 5, dev3 9, dev4 0 | — |
| no programme page (upstream, §1.1) | 21 | cohort 9 (toronto 2, hku 3, kaist 3, warsaw 1), dev2 7 (tsinghua 3, tec 2, kaznu 2), dev3 3 (utokyo 2, msu 1), dev4 2 (vut, boun) | not here |
| **reached live, not on replay (regime C: topic / scholarship query dead)** | 10 | dev2 6 (uppsala ielts, toefl, deadline, anders_wall exists; tcd e3 ×2), dev4 4 (ktu ielts, toefl, partial_tuition ×2) — plus ntu's nanyang ×2 below, reached live through the index link | **no**: a v2 store makes them measurable (§2.2) |
| **not reached, live or replay, on a found page** | 18 | cohort 4 (groningen nl ×2: client-rendered list; ntu nanyang ×2), dev2 5 (ethz cost-of-living ×2, uba news host ×2, uppsala anders_wall intl), dev3 5 (unsw scientia ×2: other host; auckland pong ×2: **index budget**; puc deadline: Spanish calendar host), dev4 4 (ctu english ×2: the FIT admissions page; rwth Kosten page; taltech award on the programme page itself) | yes (link following, index budget, on-page sections) |
| PDF evidence | 6 | warsaw, tec, utokyo, msu, usp ×2 | PD-1 map |
| evidence host failed | 2 | aalto | no |
| **read, nothing extracted** | 2 | unsw `ielts.overall` (table whose test name is the heading above it; EN-2 rule 1 did not fire), ntutw deadline (read in recovery as `unknown`, no programme page) | yes |

What the table says:

- **The read caps are not the loss.** `budget_refused:*` on the cohort replay is 0–3 per column (`funding:award` 2/0/1/2,
  `verify:question_extra` 3/0/0/0); TB-1 refused no core read that a label needed. ubc's deadline, the one label TB-1
  cost live, is a hit on replay in both reps (QT-1c's gating holds).
- **Extraction is nearly not the loss either**: 2 of 59 missed labels are on a page the run read. The B1/B2/B5 shapes
  of CORE_GAP_ANALYSIS (imperial ielts/tuition, tcd english ×3, tcd tuition) are hits now.
- **Scope** costs nothing on these corpora: wrong scope 0, other-scope 3 on the cohort (the statutory EU fee beside the
  international label, honest).
- **Reach is the loss**: 28 of 59 missed labels are on a found page whose evidence URL the run never fetched, and
  **21 of those 28 are scholarship labels**. Ten are reached live only by a topic or award query (uppsala, tcd, ktu),
  so the replay cannot measure a rule for them until the store holds those requests. The other 18 are reachable by
  link, by an index child or by reading a section of a page in hand — and today's route misses them live too.

### 1.4 Ranked generic rule candidates (claim recall and discovery), with tickets and overfitting guards

Ranking = known core questions or gold pages recovered on the readable denominator per worker-hour, counting only
what the replay can measure today or after the v2 store. Every candidate: flag off by default, a `store_true` harness
flag plus a `NEGATABLE_RULES` entry, HANDOFF §8 line, golden demo byte-identical, gates green; default-on needs the
13-Q2 bar (a stable gain outside the motivating set, or a guard by construction; dev5 aggregate not worse once it
exists).

| # | candidate | motivating labels (sets) | expected | worker h | guard against overfitting | measurable |
|---|---|---|---|---|---|---|
| 1 | **SR-1 — scholarship-route loss stage, then one rule** (diagnosis first) | groningen nl, ntu nanyang (C); ethz, uba (D2); auckland pong, unsw scientia (D3); rwth, taltech (D4): 13 labels, 4 sets | +2 to +4 questions if one shape covers ≥ 2 sets; the diagnosis names the shape (index child beyond the budget — auckland's `find-a-scholarship` "beyond the index budget; not followed"; award section on the page in hand — taltech "read as a funding index; 0 award links"; a cost-of-living page under `/scholarships/` — ethz) | 2 (diagnosis) + 3 (rule) | the diagnosis is written before the rule and names the shape per case; the rule takes dictionary-grade words only (`find a scholarship`, `scholarship search`, their `languages.json` equivalents), no word from a page; any rule that adds a read must show reads_total not up elsewhere | yes (regime A) |
| 2 | **SP-2 — a sub-page SP-1 refuses for its process noun becomes a requirements lead** | ctu `ielts.overall`, toefl (D4: the FIT "admissions procedure" page carries the English minima); uppsala `/bachelors-studies/application` (D2, deadline — reached live by a topic query) | +1 question now (ctu), +1 after the v2 store (uppsala) | 3 | reuses SP-1's own process-noun table, adds no word; one extra read at most, queued behind QR-1's question links; the lead carries the programme scope only when the page's h1 names the programme (ctu's does) | ctu yes; uppsala after v2 |
| 3 | **LL-1 dispatch** — built, flag off (`--listing-follows-local-aliases`): recovery follows a listing's cards by their own heading, a level-headed page as a listing | msu (D3), kaznu (D2, excluded), vut (D4, related-only) | +0–1 page (msu only if its listing links the gold) | 0 (+0.5 reading) | already built to the plan's spec; default-on only on a stable gain outside dev3 — expected none, so the honest outcome is "recorded, stays off" | yes (link following) |
| 4 | **EN-3 — table attributed by the heading above it** | unsw `ielts.overall` (D3) | +1 question | 1.5 | one case, one set: **below the bar; not built**. Recorded here so the next B2 shape on another set re-opens it with two motivating cases | yes |
| 5 | SP-1b (process noun in title or path when the h1 carries none) | ctu, rwth under knockout (D4) | knockout 1 → 0 on dev4 | 1.5 | one set: **not built** until a second set shows the shape | yes (knockout) |
| 6 | Related-field subtitle = specialisation (GOLD_KNOCKOUT candidate 3) | uio (D3) | knockout dev3 1 → 0 | 2 | one set: **not built** | yes (knockout) |

Not candidates: tsinghua (domain), kaist (identity), the access five, tec (DA-2's bar stands), the PDF six (PD-1 map),
groningen's client-rendered list (no static link exists; only a query reaches it — SQ-1's shape, regime C). No rank
rule is fitted to the URL-only order (MISS_STAGES §0.1).

## 2. A minimal capped live run, once the keys exist

### 2.1 The exact query budget (ledger arithmetic)

The cap plans 6 queries per case per capture (the shared per-case budget holds discovery, topic and scholarship
queries inside the six); the measured mean is 4.66 per case per column (ledger §2). Every line below is dispatched with
`max_search_queries` set to the ceiling, which the harness refuses to exceed; the Serper pre-flight (+1) applies to
Serper only.

| run | mode and cases | ceiling (cap) | expected (measured mean) | what it buys |
|---|---|---:|---:|---|
| **R1 record run** | one capture per case, the 44 development cases, `search_provider=exa`; **needs W4 first**: today `benchmark` and `expert_baseline` take a single `--case` id and only `expert_paired` iterates a list, at four columns (1 056); per set under W4: cohort 60, dev2 60, dev3 90, dev4 54 | **264** | ≈ 205 | (a) the **v2 store** (§2.2); (b) ticket 03's row `gold_returned_by_search` per family against Serper's base3 lists, from the same `search.json` files — no separate probe tool is needed; (c) MISS_STAGES §4's 51-query miss probe is a subset of it (msu, ntutw, hku-cds and every unrecorded second pass are sent) |
| R1′ comparison | the same on Tavily (its own 1 000 credits) | 264 | ≈ 205 | ticket 03's second row; needs WF-03a (§4) first: the workflow's `search_provider` choice lists exa / exa_mcp / none / recorded only |
| **R2 dev5 baseline** | `expert_paired`, empty `extra_args` (four identical repetitions, generalisation ticket 14), 13 cases | **312** | ≈ 245 | the first valid design-blind dev5 aggregate (the 05:11 run fell in the outage); 13's LOCO input; the "dev5 not worse" reading the seven default-on rules were flipped without |
| R3 H-B arms | `expert_paired` cohort, `--no-registry-seeds` (regime B, needs live) | 240 | ≈ 160–190 | generalisation 06's verdict (its 2026-10-19 runs fell in the outage) |
| R4 one live confirmation | `expert_paired` dev4 + dev5 with one replay-passing rule as `extra_args` | 528 | ≈ 410 | the default-on step a replay cannot give (replay plan §1.4 point 4) |
| reserve | heldout second look, 9 × 6 × 4 | 216 | ≈ 170 | **not dispatched in these cycles** (§2.4) |

Month total if every line runs: **1 344 on Exa's ≈ 2 500** (R1 + R2 + R3 + R4) plus 264 on Tavily, with 216 reserved.
No Serper top-up is needed for this plan. Order: R1 first (it is three deliverables in one), R2 second, R3 and R4 after
their preconditions. Two cautions from the ledger: Exa bills `highlights` as contents, so the real per-query cost is
read off the dashboard after R1 before R2 is sized; and a free allowance resets on the 1st — R1 and R2 run before
2026-10-31, each cap set from what the dashboard shows that day (§8 trap).

### 2.2 What a v2 store is worth

A capture made since `live.SearchLog` landed keeps `<case>.search.json`: every request's text and parameters and each
result's URL, title, snippet and rank, for discovery, topic, scholarship and identity searches alike.
`recorded_search` builds `recorded-search/2` from it, and the `recorded` provider serves the titles and snippets. The
chain exists end to end; nothing is built for it. After R1:

1. `python -m evaluation.research.recorded_search --source <set> <run_id> <created_at> <head_sha> <dir> … --out
   evaluation/research/data/recorded_search.r1.json` (development sets only; the builder refuses heldout and dev5 ids).
2. Re-baseline the replay on the v2 store: four `expert_paired` runs, empty `extra_args`, `--recorded-store` in
   `base_args` ($0). Expected against the day-end baseline: warsaw `missed → hit` (27/39); `recorded_search_misses_topic`
   and `_scholarship` → 0; the ten regime-C labels of §1.3 become measurable, of which eight are live hits (uppsala
   english + deadline, tcd e3 ×2, ktu toefl, ntu nanyang ×2) — pooled known-core readable ≈ 23/61 → ≈ 29/61, the live
   base3 level; uppsala's `deadline` wrong value (a replay artefact, replay plan §1.3) disappears.
3. Every evidence-stage rule (SR-1, SP-2 and the ten seen-site rules the ledger marks) then has a replay regime A/B
   reading, and the loop returns to $0 per rule.

One live column of 264 queries therefore buys a replay that can measure the whole pipeline, not discovery alone.

### 2.3 The dev5 design-blind aggregate (R2)

Preconditions, all before dispatch: generalisation 13-Q1…Q5 answered (the blindness line dated in the ticket), ticket
14's pre-registration table filled from the offline audits (10's ceiling, 11's gate count), the Exa key in the repository
secrets, cap 312. Reading: `scorecard --summary-only` and `stage_summary` only; the main session opens no per-case file of
the dev5 artifact. kbtu and satbayev are expected `unavailable` (TLS refusal to the runner on 2026-10-18); 11 readable
cases remain. The seven rules flipped on today were flipped without 13-Q2 (b); R2 is the first time that reading exists,
and a rule the dev5 aggregate reads worse under goes back to flag-off pending a diagnosis (13-Q4's per-rule dev5 runs,
≤ 12 × 312, are **not** affordable on a free tier in one month — the owner chooses which two or three rules, if any,
get one).

### 2.4 The heldout second look: not in these cycles

Programme-discovery 21-Q1 allows two looks; one is spent. Ticket 15 writes the pre-registration only when every
hypothesis has a verdict, dev5 is signed and baselined (R2), the LOCO fold range is computed, and at least one rule has
passed the paired bar on all five sets **and** 13's guard. None of that is true tonight; the 216-query reserve is held,
nothing is dispatched, and no number about the nine is computed by this plan.

## 3. Product (KB mode)

### 3.1 The unassigned KB_E2E_SMOKE gaps, ordered by applicant value per worker-hour

| rank | gap | entries it touches today | fix (minimal) | worker h | value |
|---|---|---|---|---|---|
| 1 | **B1** the "no institutional scholarship" outcome is unreachable: 0 of 98 entries have a `not_applicable` scholarship row; the expert's "none" (KTH, FU Berlin, Delft, Lund) is filed `unknown` | ≥ 4 | `core_drafts.propose_scholarship` emits a `not_applicable` record with the expert's URL and quote when present; CI `verify_evidence` checks the quote like any fact; `kb_build` v6 | 2 (+ one CI job) | "Funding: Unknown" → an explicit, sourced outcome on every university that publishes "none"; the runtime path (`none_offered_rows → kb_funding_outcome`) is already tested |
| 2 | **B4** "Needs clarification" with 0 open questions: english `not_applicable` rows (ETH "no English test required", FU Berlin "German, DSH 2") are never shown | 24 entries have english n/a rows | `answer()` turns an english `not_applicable` row into a non-blocking note claim or open question quoting it; and a non-blocking question whenever eligibility is `NEEDS_OFFICIAL_CLARIFICATION` and no question exists | 1.5 | a quarter of the KB explains itself instead of showing an unexplained chip |
| 3 | **B2** the Costs tab hides the stale fee ("No official cost of attendance was found") | **48** entries have a stale tuition fact | kb mode: when the cost table is empty and the row has a `POSSIBLY_STALE` tuition claim, the gap reason reads "Official tuition found for <year> only (stale for the <intake> intake): <amount>; not used"; the tab lists stale tuition claims under the notice | 1.5 | half the KB's cost tabs stop saying "not found" about a figure the KB holds |
| 4 | **B8** the stale chip says "Ageing" and the Sources copy "re-checked more often"; a KB fact can be stale on its first day | 58 stale facts | `STATUS_LABEL.POSSIBLY_STALE` → "Not current" when `capabilities.knowledge_mode === "kb"`; Sources copy keyed the same way | 0.5 | copy that matches what F1 already shows |
| 5 | **B3** Funding tab copy assumes live mode ("No official scholarship page could be read") | 34 entries with scholarship `unknown` | `kb_scholarships` (or the funding stage in kb mode) adds the explicit unresolved question "The verified knowledge base names no award for …; funding unknown, not confirmed absent"; the panel keys its copy on `knowledge_mode` | 1 | the honest sentence instead of a false one |
| 6 | **B5** programme names are long quotes | every KB row | carry the draft's programme `title` into the built entry; `KnowledgeDiscovery` prefers it, the quote stays evidence | 1.5 | readable rows; needs a rebuild |
| 7 | **B6** results are English only (ru, kk offered) | all | UI labels first (`ResultDetail`, `ShortlistScreen`, chips) ≈ 3 h; backend questions need stable codes (`topic` + code) the UI localises ≈ 4 h | 6–8 | the owner's audience; two tickets, after 1–5 |
| — | **G9** `demo_mode` defaults to `true`; "default kb mode" needs `UNIMATCH_DEMO_MODE=false` | — | one line in `KNOWLEDGE_BASE.md` "Setting" now; flipping the default is the owner's (Q9) | 0.2 | — |
| — | **B7** brand "Unimatch" vs "ASHYQ Apply" | — | owner's call (Q9) | — | — |

Bundle 1 + 2 + 4 into one worker ticket (P1, ≈ 4 h, one rebuild); 3 + 5 into P2 (≈ 2.5 h); 6 into P3; 7 later.

### 3.2 KB coverage growth: what each gap costs and buys

Counts from `kb_cs_bachelor.json` v5 (98 entries) with `kb_imported_dev.json` (21 entries, 15 unsigned drafts) merged
at runtime.

| gap | today | option | worker h | value |
|---|---|---|---|---|
| **deadlines** | known 32 (10 of them stale: 2026 dates passed); **unknown 66** (US 20, AU 7, UK 6, CA 4, CH/HK/JP/DE/SE 3 each, …) | **K1** expert pass in batches of 20 by catalogue rank (`university-admissions-research`; the 2027-entry dates are published now for most northern-hemisphere universities); drafts → CI quote check → rebuild | ≈ 0.25 per university: **5 per batch, ≈ 19 for all 76** | the core question applicants act on first; coverage 32 → up to ≈ 90 of 98. The highest value per hour in this plan |
| **tuition** | known 67, **stale 48**: 31 "2026/27 before the 2027/28 intake", 13 "academic year not stated" (a standing fee policy: ETH, EPFL, FU Berlin, Heidelberg, UZH, KTH, Lund, IP Paris, Osaka, Nanjing, UCLA, Kyoto, ISCT), 4 past (Toronto 25/26, UM, Paris-Saclay, ISCT 2019) | the 31 wait for publication (US/CA/AU 2027/28 fees appear Feb–Jul 2027); UK and IE 2027-entry fees are mostly published → re-draft that subset now (≈ 8); the 4 past now; the 13 standing policies are **Q7**: shown "current policy, year not stated" with a caveat, or stale as today | 2.5 (UK/IE + past); 1 (policy code + tests, if Q7 = yes); 0 expert hours for the 13 | the 13 + 12 re-drafts fill the cost table for a quarter of the KB without waiting for spring |
| **programme page** | 67 known in the built file; 20 more come from the import; **11 without** (UCL, Melbourne, Sydney, PSL, UTokyo, IP Paris, Michigan, LSE, Lund, KTH, Alberta) | expert pass on the 11 (LSE likely "not offered" → an honest `not_applicable` programme) | 3.5 | removes the F5 blocking question on 11 rows |
| **GPA** | known **6**, n/a 23, unknown 69 | do not chase a number: a numeric GPA minimum for international bachelors is rarely published. Fold into K1: the expert records `not_applicable` ("no numeric minimum published; qualification-specific") where confirmed, and B4's note surfaces it | 0 dedicated | the honest answer shown instead of an empty cell |
| scholarships | unknown 34 | folded into K1 (the same admissions pages); B1 makes "none" expressible | +0.1 per university | — |
| refresh queue (ticket 07) | 1 re-draft (NTU deadline quote gone), 25 blocked from this vantage point (SNU, KAIST, HKU, KU Leuven, ANU, NTU Taiwan, UTokyo, Chicago, Zhejiang) | re-draft NTU now; the 25 run once on `runner: self-hosted` (01-Q4 answered yes) | 0.3 + one home run | the stale-by-vantage facts stop ageing |

## 4. The cycles

| cycle | dispatches (0 worker h) | worker tickets | gate |
|---|---|---|---|
| **11 (now, $0)** | LL-1 replay on the four sets (`--listing-follows-local-aliases`, normal + knockout); SR-1's diagnosis reads the day-end artifacts | **W1 K1 batch 1** (deadlines, 20 universities); **W2 P1** (B1 + B4 + B8); **W3 SR-1 diagnosis** (→ rule ticket); **W4 WF-03a** (workflow `search_provider` gains tavily and brave; `expert_baseline` takes the four case lists under one cap; a scorecard target row that reads 0 topic/scholarship misses on a v2 store) | owner round: Q1–Q5 |
| **12 (keys exist, W4 landed)** | **R1** (cap 264, Exa), R1′ (Tavily); build `recorded_search.r1.json`; re-baseline the replay on v2 (4 runs, $0); SR-1 rule replay if W3 named a two-set shape | **W5 SP-2** (ctu now, uppsala on v2); **P2** (B2 + B5); K1 batch 2; the UK/IE + past tuition re-drafts | ticket 03's table filled; 13-Q1…Q5 answered |
| **13** | **R2** dev5 baseline (cap 312) once 14's pre-registration is written; R3 (H-B arms, cap 240) | **P3** (B6 UI labels); K1 batch 3; the 11 programme pages; the self-hosted refresh run | 14's "predicted vs read" table; 15's inputs begin |

Worker tickets, top four (details for dispatch):

**W1 — K1 deadline pass, batch 1** (expert worker, ≈ 5 h). Twenty universities: the stale ten (Fudan, Korea, NUS,
Peking, SNU, UNSW, TCD, UM, Cambridge, Zhejiang) plus the ten highest-ranked `unknown` entries. Per university: the
official 2027-entry (fall 2027) international bachelor deadline with URL and verbatim quote, in the drafts format
`kb_build` reads; `scholarship_exists` and `gpa` recorded on the same pass where the page states them (`not_applicable`
with a quote when the site says there is no numeric minimum / no award). Then CI `verify_evidence` on the batch, `kb_build`
v6, `KB_REFRESH` queue line. Guard: no value without a quote; no page read outside `Fetcher`'s rules; nothing from a
heldout university. Done when the CI check passes on ≥ 18 of 20 and v6 is built.

**W2 — P1: B1 + B4 + B8** (worker, ≈ 4 h). Files: `backend/evaluation/research/expert/core_drafts.py`
(`propose_scholarship`: emit a `not_applicable` record with URL + quote), `backend/app/knowledge/claims.py` (`answer()`:
english `not_applicable` → note claim / non-blocking question), `backend/app/pipeline/runner.py` (kb branch only: a
non-blocking question when eligibility is `NEEDS_OFFICIAL_CLARIFICATION` and no question exists),
`frontend/src/lib/format.ts` (`POSSIBLY_STALE` label by `knowledge_mode`), tests beside each; rebuild after the data
change. Guard: demo and live output byte-identical (`seed_demo.py`, brief §5.7 order); the `not_applicable` outcome
fires only on a verified, current quote. Done when KTH and FU Berlin read "No institutional scholarship: …" in the smoke
profile and ETH's row carries its "no English test required" note.

**W3 — SR-1 scholarship-route loss stage** (analysis worker, ≈ 2 h, then a rule ticket). For groningen, ntu (cohort),
ethz, uba (dev2), auckland, unsw (dev3), rwth, taltech (dev4): from the day-end replay traces and the live base3
captures, where the labelled award page sits relative to the pages read (linked from a read page and not followed;
index child beyond `_MAX_INDEX_PAGES`; described in a section of a page in hand; another host never linked), with the
page-diagnostics line that refused it. Output: a table case → shape → the single generic rule that would reach it, and
which sets each shape covers. A shape with ≥ 2 sets becomes the rule ticket (flag off, one extra read at most,
dictionary-grade words only); a one-set shape is recorded, not built. No page is fetched by the worker; replay and base3
captures only.

**W4 — WF-03a harness readiness for the record run** (worker, ≈ 2 h). `.github/workflows/benchmark-capture.yml`
and `backend/evaluation/research/live.py`: a **single-column list mode** — the smaller of (a) `expert_paired` with a
`columns` input of `1` (one `on` capture per case through the existing per-case loop, cap plan 6 × cases × 1) or (b)
`expert_baseline` iterating a space-separated case list — because `--case` is a single choice today and only
`expert_paired` iterates a list; `search_provider` choice gains `tavily` and `brave` (the adapters and secrets already
exist); `backend/evaluation/research/scorecard.py`: on a `recorded-search/2` store the replay target also requires
`recorded_search_misses_topic` and `_scholarship` = 0, so a v2 replay that still misses is flagged. Tests for the
list mode's cap plan and the target row. No product code. Done when a dry `--search-provider none` dispatch on the 44
ids plans 264 and a cap of 263 is refused before any capture starts.

## 5. Owner questions (batched; everything else proceeds)

| # | question | recommendation | why |
|---|---|---|---|
| Q1 | uct: keep `sit.uct.ac.za/bsc-degrees` as the gold, or add the BSc listing's CS entry and let `ba-informatics` stay related? (MISS_STAGES Q1) | a 20-minute worker check of what `bsc-degrees` lists, then your call | CH-1 refuses a listing head by design; no generic rule will read it as the programme page |
| Q2 | kuleuven: is `www.kuleuven.be/programmes/opleidingen/bachelor-informatica` a twin of the `onderwijsaanbod` entry? (MISS_STAGES Q2) | worker hand-check (redirect / hreflang), sign the twin or keep the wrong | it is the only wrong page left in normal mode |
| **Q3** | tcd: under knockout the run confirms `tcd.ie/scss/courses/undergraduate/computer-science`, the School's page of the same degree. Sign it as a twin of the gold? | **yes** (worker hand-check first) | it is the same programme on the department host, not a guess; the knockout count becomes 2 + flake with no rule |
| Q4 | kaist: keep as residue (department host / opaque URL)? | yes, as 18-Q1 recorded | a rule that accepts it accepts every department page |
| Q5 | tec: accept as residue, or re-open DA-2 on its one-set evidence ("B.S." dotted token before "in"/"of")? | residue; re-open on a second set | DA-2's bar was set before the audit |
| Q6 | Exa and Tavily keys (free-search 01-Q3) → cycle 12 | yes, both; Brave only without a card | R1 is three deliverables for 264 queries |
| Q7 | tuition "academic year not stated" (13 standing fee policies): show as "current policy, year not stated" with a caveat, or stale as today? | current with caveat, re-checked by the monthly cron | a standing policy is not last year's figure; the caveat keeps it honest |
| Q8 | the 15 unsigned expert drafts imported from dev2/dev3/dev5 labels are served under "Verified knowledge base". Sign them in the next review, or label the rows "expert draft" until then? | label until signed | the chip promises verification |
| Q9 | G9: flip `demo_mode` to `false` for the product? B7: "ASHYQ Apply" or "Unimatch" in the UI? | your call; G9 documented either way | — |
| Q10 | generalisation 13-Q1…Q5 (dev5 blindness protocol, default-on bar, LOCO, per-rule dev5 runs) are still open | answer before R2 is dispatched | R2's reading depends on them |

## 6. What this plan does not change

The DoD targets and denominators; targets 3 and 4 stay "not met" on development. No rule is attempted on the access
class, the other-registrable-domain class or the department-host class (01-Q4 stopping rule), no rank rule is fitted to
the URL-only store, and no one-set shape is built (13-Q2 (a)). No heldout look is dispatched; the 216-query reserve is
held for ticket 15. Model-based extraction stays outside every map here (18-Q2 (c)).
