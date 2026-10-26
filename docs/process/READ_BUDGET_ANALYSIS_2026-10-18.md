# Read budget analysis: why dev3 is over 60 reads, and how to make 60 a hard cap

Read-only analysis, 2026-10-18, branch `claude/greeting-16wj2z` (HEAD d062975). No repo edits.
Captures: `scratchpad/runs/{sb1c,bundle5,lx1,sb1}-{dev3,dev2,cohort}`. Heldout not opened.
Scripts used: `scratchpad/rb/tab.py`, `scratchpad/rb/stages.py` (log + capture + raw-trace parsers).

## 0. Headline

**The "reads" the scorecard counts and the reads the code caps are different things.**

* Scorecard `http_fetches` (non-strict harness, which is what `expert_paired` runs) counts every
  **wire-level HTTP request**: `evaluation/research/live.py:650 counted_request` patches
  `app.adapters.fetching._pinned_request`, which is built once per **redirect hop**, per **retry
  attempt** (`MAX_ATTEMPTS = 3`, 5xx/429), per **address tried** (`MAX_ADDRESSES_TRIED = 3`) and for
  every **robots.txt load** (one per host, `fetching.py:393`).
* Every cap in code counts **`Fetcher.get` calls** that missed the cache: discovery's
  `StageBudget` (`live_discovery.py:1919`), and the harness's own page cap
  (`live.py:701`, `network_reads >= max_pages`, `--max-pages 60` from the workflow).
* In no capture on any split does a case reach 60 `Fetcher.get` network reads (max seen: 51,
  Auckland bundle5 off). Imperial is over budget with **24-39** gets: its 66-74 "reads" are
  **30-49 requests of redirect overhead** (course URLs under `/2027/` answer 301 and take 2-3 hops:
  checked by hand today, e.g. `/study/courses/undergraduate/2027/mathematics-computer-science-beng`
  → 3 redirects). Chula's 61-64 are 37-38 gets + 24-26 overhead (6 hosts' robots.txt, http→https
  and trailing-slash 301s).
* So nothing in code can stop the scorecard's 60: the quantity is not metered anywhere a stage
  can see it.

## 1. Which cases exceed which limit

### Definition (`backend/evaluation/research/scorecard.py`)

* `BUDGET = {"search_calls": 6, "http_fetches": 60, "latency_seconds": 120.0}` (line 41).
* `cost()` (l.218-234): per case and repetition, `over_budget` = number of the three limits with
  value **strictly greater** than the limit (`None` → 0). So 60 reads, 6 queries, 120.0 s pass.
* `targets()` (l.348-361): `cases_over_budget` = **sum over every repetition of the arm of the
  case rows with `over_budget > 0`**. It is a count of (case, repetition) pairs, not of distinct
  cases, and not the worst repetition, although the table column is labelled "worst". Imperial
  over in both repetitions counts 2.
* `http_fetches` = wire requests as above (non-strict mode). In `--strict-expert-budget` mode it
  is instead `budget.fetcher_calls` (Fetcher.get calls, cache forced off) — a third definition.
* Latency blind spot: the harness kills a case at its wall clock (115 s soft, 120 s), so
  `latency_seconds` can never be > 120; Imperial, UNSW, USP, UCT end at 115.0-120.0 "within
  budget" while incomplete. No case in any run is over on queries (max 6) or latency (max 120.0).

### Over-budget rows (all are `http_fetches`; queries/latency never over)

| run (arm config) | arm | rep | case | reads | over by | q | s |
|---|---|---|---|---|---|---|---|
| **sb1c-dev3** (both arms = today's defaults; 9 cases) | off | 0 | imperial | 66 | +6 | 2 | 115 (killed) |
| | off | 1 | chula | 64 | +4 | 6 | 89 |
| | off | 1 | imperial | 69 | +9 | 2 | 115 (killed) |
| | on | 0 | chula | 61 | +1 | 6 | 81 |
| | on | 0 | imperial | 71 | +11 | 2 | 115 (killed) |
| | on | 1 | chula | 63 | +3 | 6 | 88 |
| | on | 1 | imperial | 70 | +10 | 2 | 115 (killed) |
| → `cases_over_budget` | off 3, on 4 | | | | | | |
| **bundle5-dev3** (off = pre-bundle defaults; on = SB-1+QR-1+AR-1+FI-1+CG-1) | off | 0 | auckland | 64 | +4 | 6 | 110 |
| | off | 0 | chula | 72 | +12 | 6 | 111 |
| | off | 0 | imperial | 73 | +13 | 0 | 115 (killed) |
| | off | 1 | chula | 72 | +12 | 6 | 105 |
| | off | 1 | imperial | 74 | +14 | 0 | 115 (killed) |
| | on | 0 | chula | 63 | +3 | 6 | 85 |
| | on | 0 | imperial | 68 | +8 | 1 | 115 (killed) |
| | on | 1 | chula | 63 | +3 | 6 | 80 |
| | on | 1 | imperial | 66 | +6 | 1 | 115 (killed) |
| → `cases_over_budget` | off 5, on 4 | | | | | | |
| lx1-dev3 (older) | off | 0/1 | chula 66/72, imperial 73/72, auckland(rep1) 62 | | | | |
| | on | 0/1 | chula 71/72, imperial(rep1) 62 | → off 5, on 3 | | | |
| sb1-dev3 (older) | off | 0/1 | auckland(rep0) 63, chula 70/63, imperial 73/74 | → off 5 | | | |
| | on (SB-1 alone) | — | none (Imperial 52/52, Chula 46/60) | → on 0 | | | |

Edge values not counted: dev3 USP 120.0 s, UNSW 120.0 s (lx1), dev2 UCT 120.0 s (bundle5 off).

**Cohort and dev2: 0 over budget** in bundle5, lx1 and sb1, both arms. Closest: Groningen 57
(off; 51 on), Warsaw 56-57 (off), TCD 53-54, UCT 50-54, NTU 51 (bundle on). All are ≥ 50 wire
requests with only 27-50 network gets.

## 2. Where the reads go (today's defaults, sb1c-dev3; gets = non-cached Fetcher.get)

| case | wire | net gets | discovery (StageBudget) | verify + costs | funding | wire overhead |
|---|---|---|---|---|---|---|
| Imperial ×4 | 66-71 | 33-39 | 11 = sitemap 4 + confirm 7; **stopped by deadline 55 s** in confirm (no walker, no query) | ~10 (entry-req, English ×2, tuition, fees-and-funding, offer-holders fees, process, UG deadlines, **PGT deadlines**, `entry-requirements/` = trailing-slash duplicate) | **13-18** (societal-engagement "funding" ×4, scholarships-search index, then award pages: PhD studentships, advisory board, ADA Lovelace PhD...) until the 115 s kill | 30-33 |
| Chula ×4 | 58-64 | 37-39 | 25-26 = **sitemap 13** (robots, 2 index + **2 404 probes**, 8 children incl. clipping ×2, gallery, event-calendar, highlight) + navigation 5 + walker 3-4 + search 3 (home pages of math.sc, cbs, www) + recovery 1; reserve 0 | 6 (admissions ×3, about/feedback as "costs", tuition-and-fees **http and https**) | 6 (research funding-ora 11 s, an arts PDF, inter post, scholarships, awards-honours, media fellowship) | 19-26 |
| Auckland ×4 | 45-46 | 36-37 | 12 = sitemap 3 + confirm 8 + recovery 1 | 7 | 17-18 | 9 |

Stage attribution: discovery from the raw trace's `stage_budget.reads`, the rest from the per-read
log in order; funding starts at the first funding-path URL after discovery (approximate).

### Which cap should have stopped them

* `DISCOVERY_READ_CAP = 28` (candidate reads only), `DISCOVERY_SITEMAP_ALLOWANCE =
  MAX_SITEMAP_DOCUMENTS + 1 = 13`, `RECOVERY_RESERVE_READS = PRECONFIRMED_RECOVERY_CHECKS = 3`,
  `DISCOVERY_DEADLINE_SECONDS = 55` (`live_discovery.py:150-180`). Discovery-only, counts gets.
  It worked as designed: Imperial stopped at 55 s with 11 reads, Chula at 25-26.
* Verify/requirements: only per-programme follow caps — `_MAX_LANGUAGE_FOLLOWS = 2`,
  `_MAX_ROUTE_FOLLOWS = 4`, `_MAX_QUESTION_LINKS = 2` per question (QR-1), three topic queries
  (`_TOPIC_QUERIES`), up to `MAX_PAGES_PER_CATEGORY = 3` programmes; costs and government
  uncapped beyond their own lists. Funding: `_MAX_INDEX_PAGES = 3`, `_MAX_AWARD_PAGES = 12`
  (AR-1: 5 / 3, off), award search 3 leads.
* **No case-level read ledger exists in `app/`.** The runner (`runner.py:374`) builds one
  `Fetcher` per run and hands it to every stage; nothing sums reads across stages per institution.
* The only case-level cap is the benchmark's `--max-pages 60` (`live.py:701`), on network gets,
  which raises `BENCHMARK_PAGE_BUDGET_EXHAUSTED` (kills the case, no graceful stop). It never fired.

### Can SB-1b + verify exceed 60 by design? Yes, at both layers.

* Gets: discovery up to 13 + 28 + 3 = **44**, and the reserve can also be spent past the deadline.
  Verify per programme: programme page + admissions pages + 3 topic pages + 2 language + 4 route +
  2×2 question links ≈ 15, ×(1-3 programmes); funding up to 3 + 12 (+3 search leads). Worst case
  well above 60; the 16 left after discovery's 44 is less than one programme's verify plus funding.
* Wire: each get costs 1 + redirect hops (`MAX_REDIRECTS = 5`) × attempts (up to 3) + one robots.txt
  per new host. Imperial pays ~2-3 requests per get; nothing budgets that.

## 3. Did a rule turned on today raise reads? No (against the pre-rule captures).

| case (dev3) | pre-SB-1 defaults (sb1/lx1/bundle5 off) | SB-1 alone (sb1 on) | bundle on (bundle5 on, incl. AR-1) | today's defaults (sb1c, AR-1 off) |
|---|---|---|---|---|
| Imperial wire / gets | 72-74 / 23-25, 0 queries, killed at 115 s | **52 / 21, finished at 81-83 s** | 66-68 / 28-31, killed | 66-71 / 33-39, killed |
| Chula | 63-72 / 40-43 | 46, 60 / 28, 36 | 63 / 38 | 58-64 / 37-39 |
| Auckland | 59-64 / 45-51 | 51-53 / 41-43 | 47 / 37 | 45-46 / 36-37 |
| dev3 total reads (15 cases) | 553, 519, 561, 581, 568 | 435, 446 | 499, 488 | (9 cases only: 331-345) |

* Versus the old defaults every rule set lowered reads (Imperial 73 → 66-71, Chula 72 → 61-64,
  Auckland 64 → 46). SB-1/SB-1b/SB-1c, QR-1/b/c, FI-1, CG-1, FS-1/FS-2 did not push any case above
  where it already was; Auckland was fixed by the bundle (FI-1 found its programme page).
* Versus **SB-1 alone**, Imperial rose 52 → 66-71 and now hits the clock again. Discovery is
  identical (11 reads). The rise is downstream: QR-1's extra question pages (process, deadlines UG +
  PGT, offer-holders fees, the `/` duplicate) and the queries made after discovery (topic query at
  ~63 s, scholarship search at ~90 s; SB-1 alone made 0 queries). The scholarship search then fills
  the rest of the 115 s with PhD award pages. With AR-1 on (bundle5) funding read UG bursary pages
  instead. Imperial's wire count tracks the clock (~0.6 requests/s with redirects), so whatever
  runs until the kill sets the number.
* SB-1b specifically: the 13-read sitemap allowance kept Chula's 13 sitemap reads (7 of them
  wasted: 2 guaranteed 404 probes + 5 news/gallery/event children). SM-1 (`SITEMAP_CHILD_PRIORITY`,
  off) would remove them; it is not on.
* SB-1c (the sb1c check): both arms are the same defaults; 3 vs 4 over is noise (Chula 58-64).

## 4. Minimal fix for a hard per-case 60

### Step 0 (needs the owner, no code risk): one definition of "read"
The DoD says "60 page reads". Today the scorecard measures wire requests, the harness caps
network gets, strict mode counts gets with the cache off. Pick one and make harness, scorecard
and pipeline use it. Recommendation: **network page reads = non-cached `Fetcher.get` calls
plus every extra redirect hop**, robots.txt reported separately (it is policy, not search). If the
owner keeps wire requests as the definition, the cap must meter wire requests (step 2). Either way
this is a DoD measure change: per the DoD file it needs the owner's approval and a dated entry.
Note: under the get definition, every case on every split is already within 60 today (max 51).

### Step 1: cheap read savers that lose no answers (each behind a flag, paired run)
1. **Redirect memo**: remember `url → final_url` in the Fetcher; a later link to a URL known to
   redirect requests the final URL, and the cache is keyed on both. Imperial `/2027/` course and
   fee pages are linked repeatedly. Saves most of Imperial's 30-49 overhead requests and their
   ~1.5 s pacing per hop (also helps the 115 s kill).
2. **URL canonicalization before cache lookup**: trailing slash, `http`→`https` on the same host
   (Imperial `entry-requirements` vs `/`, Chula tuition http + https).
3. **Sitemap**: stop probing conventional locations after the first that parses, and read
   news/gallery/event children last (= SM-1); drop `DISCOVERY_SITEMAP_ALLOWANCE` from 13 to ~6.
4. **Funding**: skip award links that name another level (PhD, studentship, postgraduate, MSc)
   for an undergraduate request before reading them, and skip "funding" pages outside
   study/admissions paths (Imperial societal-engagement); stop the award walk once
   `scholarship exists` + `international` are answered.
5. **QR-1 question links**: apply the `_names_other_level` filter (already used for language
   links) to deadline links (Imperial PGT deadlines page).

### Step 2: the hard cap (backstop)
* **Where**: a per-institution `ReadLedger` in `app/adapters/fetching.py`, charged in
  `Fetcher._request_one_hop` and robots `_load` (the same points `_pinned_request` serves, so the
  ledger and the scorecard count the same thing), keyed by the candidate's registrable domain plus
  its DI-1 admissions domains. The runner (`runner.py` `_stage_discover/_stage_verify/
  _stage_funding`) sets the active institution before each candidate. A get that starts with
  the ledger spent returns `BLOCKED "case read budget spent"`, like `_BudgetedFetcher`. The redirect
  loop stops a chain that would cross the cap (counts as a failed read, recorded in page outcomes).
* **Shares, carry-forward**: discovery gets `min(DISCOVERY_READ_CAP + sitemap, ledger.remaining
  − 24)` (StageBudget reads from the ledger instead of its own counters), verify reserves 16 for the
  six core questions, funding gets what is left (≥ 8). Unused reads carry to the next stage.
* **Drop order when short** (least answer value first): sitemap children past the first
  programme-bearing one → navigation/walker past a confirmed page (SB-1 already does) → funding
  award pages beyond the first matching one → route follows → second and third programme's verify
  → language follows → topic pages for questions already answered. Never dropped: the confirmed
  programme page, the admissions page beside it, one topic page per unanswered core question.
* **Harness**: replace the raise at `live.py:701` with reading the ledger, so a case ends
  gracefully with its claims instead of `BENCHMARK_PAGE_BUDGET_EXHAUSTED`.

### Risks
* **Answer loss**: Imperial's deadline gain (bundle, 2027-01-13) comes from verify pages read after
  65 s; a strict ledger without step 1 would cut those before funding. Do step 1 first and measure.
  Delft's QR-1 deadline gain uses question links that the drop order cuts last, but check it.
* **Production runs share one Fetcher and cache across universities**: the ledger must be per
  institution; shared pages (the government post-study-work page per country) are charged to the
  first institution only; cache hits are free.
* **Counting redirects penalises redirect-heavy sites**; without the redirect memo the cap would
  trade Imperial's answers for overhead.
* **Golden demo**: fixture fetcher has no redirects or robots; keep the cap far above demo reads
  and run `seed_demo.py` (brief §5.7 order).
* **Latency stays unmeasured**: Imperial still runs to the 115 s kill; the reads fix does not change
  that, and the scorecard cannot report latency > 120 because the harness kills first. Consider
  counting a clock-killed case as over budget.
* **Process**: the scorecard measure change and the default-on of each saver need the owner's
  approval (DoD §"How it is measured", loop step 4).
