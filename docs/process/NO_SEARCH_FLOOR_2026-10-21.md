# No-search floor against the own-index ceiling, per case and stage (NS-1a, 2026-10-21)

Ticket NS-1a of `NEXT_CYCLES_2026-10-21.md` §3. It decides whether NS-1b opens. Research only, no pipeline change.

**Verdict: a shared cause on dev3 and dev4, so NS-1b opens.** The stage is the navigation fallback at hop 1, and the
mechanism is "never followed". The homepage links the gold page through a page in its top five study links. On
puc and iitd (dev3) and kit (dev4) that page sits on another host of the institution's own domain. The
fallback queues a homepage link only when `categorise_url` recognises its URL, and none of those pages has
such a URL. So it reads 1–3 pages and stops. Each run ends 9–34 s into the case with 46–53 of its 60 reads
unused. The same shape is behind cohort's kaist, but there a registry seed hides it (see below). The NS-1b
rule is in §4.

## 1. Inputs and method

- **Runs**: `benchmark-capture.yml`, mode `expert_paired`, `search_provider=none`, `columns=1` (one capture per case),
  2026-10-20 00:55 UTC, pipeline `f0d1830e`:
  - `ns-floor-cohort` 39350475181;
  - `ns-floor-dev2` 39350477901;
  - `ns-floor-dev3` 39350480488;
  - `ns-floor-dev4` 39350483178.

  The artifacts `expert-recovery-<run id>` were read from the session scratchpad. No search provider was configured
  (`search_calls` 0 on every case).
- **Scoring**: `metrics.adjudicate_programme_pages` against `ground_truth.reviewed11` (cohort) and `dev2/dev3/dev4.draft3`.
  The outcomes reproduce LOOP_REPORT cycle 14: hits 4 / 2 / 3 / 0, 0 wrong outcomes, 9/39 in all.
- **What each case did**: read from the raw trace and the per-case log. The trace fields used are:
  - `stage_order`, `stage_budget` (stage seconds, stage reads, `stopped_by`);
  - `read_ledger`, `case_time`;
  - `sitemaps_read`, `sitemap_urls_seen` / `kept`;
  - `selected`, `manual_seeds`;
  - `pages_read` (the confirm verdicts), `rejected_sample`;
  - `walker.candidates` / `outcomes`, `page_diagnostics`.

  The ticket also names `navigation_candidates`, `hop_entry_points` and `profile_rejects`. These captures carry none of
  them; the confirm verdicts in `pages_read` are what `profile_rejects` returned.
- **Reachability**: the per-case table of `INDEX_CEILING_2026-10-19.md`.
  - "bounded" means the gold is listed in `SitemapReader.collect`'s bounded read of the homepage host.
  - "hop 2" means the gold is linked from a page that the homepage links through a study, programme or admissions
    anchor.

  The ceiling report JSON is not committed, and it records no parent page. So, for the hop-2 cases, a scratch probe
  re-ran `index_ceiling.crawl_two_hops` from the agent sandbox on 2026-10-20 at about 05:30 UTC. It used the production
  `Fetcher` and no search, and it recorded which hop-1 page links the gold. It also recorded the rank of that hop-1
  page among the homepage's links under the product's own scorer:
  - `navigation._score`;
  - plus 3 for a `study_section_label`;
  - plus 2 for a `_SECTION_WORDS` / `_ADMISSION_WORDS` label.

  The probe ran from another vantage point and some hours later than the runs, so a homepage may have changed in
  between. That is the main caveat on the "rank" column.
- **Not opened**: any heldout file, capture, log or label; dev5; any other scratchpad.

## 2. The stage table — every case the ceiling marks reachable

Reads are network reads out of the 60-read budget. "Ended" is the case's elapsed time out of its 110 s limit.

| set | case | reachable by | no-search outcome | what the run did | stage named |
|---|---|---|---|---|---|
| dev3 | imperial | bounded | **hit** | 3 sitemaps, 28 050 URLs seen, 370 kept; confirm read 8, accepting `…/2027/computing-beng` beside the related maths-and-CS page (R2b) | — (sitemap + confirm worked) |
| dev3 | unsw | bounded | **hit** | crawl-delay 10 host (slow); 4 sitemap reads, 31 s; confirm read 3 and returned the gold plus the diploma and the CS-and-law pages | — (sitemap + confirm worked; the two extra pages do not change the case outcome) |
| dev3 | ucph | bounded, hop 2 | **hit** | 12 sitemap documents; confirm read 8 (hreflang twins), accepting `/studies/bachelor/computer-science` | — |
| dev3 | auckland | bounded, hop 2 | missed | Sitemap: 20 908 URLs seen, 261 kept. Confirm spent its 8 reads on `computer-science.html` (read as unknown), the `/doctoral` and `/postgraduate` siblings and three conjoint BSc/LLB pages. The walker spent its read cap on undergraduate-options, foundation and summer-start pages (88 `walker_budget_exhausted`). Ended 82 s, 47 reads. The gold was never read. The trace does not record whether `keep()` kept it among the 261. | **ranked out**: confirm-queue order. The hop-1 page "Find a study option" ranks 17th, outside any small hop budget. |
| dev3 | iitd | hop 2 | missed | The navigation fallback queued `alumni.iitd.ac.in/transcripts-degrees` because its URL says "degrees" (read, `not_program_catalog`). It then read the homepage. Nothing else on the homepage categorises by URL, so the queue emptied. `academics.iitd.ac.in` was read later and classified unknown. Ended **18.7 s, 14 reads**. | **never followed**: hop 1 is `www.cse.iitd.ac.in` ("Computer Science and Engineering", rank 3, another host on the institution's domain), which links the gold as "B.Tech" |
| dev3 | puc | hop 2 | missed | The single 21 s `sitemap.xml` read made the host "slow" (median 10.9 s), so the walker was skipped. Navigation read two `/keywords/` pages and the homepage. "Carreras de pregrado" → `admision.uc.cl/carreras` was never queued: its URL does not categorise, and R4 is off. Ended **33.7 s, 13 reads**. | **never followed**: hop 1 `admision.uc.cl/carreras` (rank 4, other host on the institution's domain); gold anchor names the field |
| dev4 | kit | hop 2 | missed | Four guessed sitemap paths returned 404 (7.5 s). Navigation read the homepage only: no link categorises by URL, so the queue was empty. The walker then walked the homepage as a catalogue (`walker_no_signal` / `short_label` / `off_domain`, 0 candidates). Ended **9.4 s, 7 reads**. | **never followed**: hop 1 `www.sle.kit.edu/vorstudium/studiengaenge.php` ("Studiengänge", rank 5, other host on the institution's domain) links the gold as "Informatik". `bewerbung.php` (rank 7) links it too. |
| cohort | ntu | bounded, hop 2 | **hit** | The registry seed catalogue `education/degree-programmes` led to the gold, confirmed in 3 reads | — (the seed is the hop-1 page; the probe ranks it 17th without the seed) |
| cohort | vienna | hop 2 | **hit** | The registry seed catalogue `studieren.univie.ac.at/en/degree-programmes/` was read. Its link "Computer Science" was kept by link text and accepted. | — (the seed is the hop-1 page, rank 1–2) |
| cohort | kaist | hop 2 | missed | The registry seed puts the gold `cs.kaist.ac.kr/content?menu=188` in `program_catalog` and `menu=318` in `program_page`. Confirm refused `menu=318` (reads as unknown), and the walker walked the gold as a catalogue (`short_label` ×128). Because a seed filled the programme slot, the navigation fallback never ran. Ended 14.2 s, 12 reads. | **read and refused**: read in the catalogue role, never judged as a programme page. Hop 1 is `cs.kaist.ac.kr` (rank 2, other host). |
| dev2 | khalifa | bounded (hop 0) | related | Confirm read 3 sitemap candidates: a news item and two minors. The walker reached `ku.ac.ae/zmu` ("BSc in Computer Science program", labelled related) and returned it. `/program/bsc-in-computer-science` was never read. Ended 46 s, 15 reads. | **ranked out**: confirm-queue order |

What the hits did right, in one line each:
- **dev3**: every hit came from the homepage host's bounded sitemap and the confirm stage. None needed navigation.
- **cohort**: every hit started from a curated registry seed catalogue, which stands in for the hop-1 page.
  - groningen: the walker, 11 reads.
  - delft: confirm, 5 reads.
  - vienna: a field-named link on the catalogue.
  - ntu: confirm.
- **dev2**: psaclay and tcd were found by navigation and the walker going deeper than the ceiling's two hops. The
  ceiling marks both unreachable.

## 3. The cases the ceiling marks unreachable, for completeness

| set | case | ended / reads | what stopped it |
|---|---|---|---|
| dev3 | chula | 41 s / 37 | 12 sitemap documents, 46 kept, walker 5; gold on faculty hosts the run never touched |
| dev3 | kuleuven | 10.7 s / 8 | homepage sitemaps 401/404; navigation read the homepage only; gold host robots-refused (ceiling) |
| dev3 | msu | 10.4 s / 14 | no sitemap; navigation 1 page; gold on `pk.cs.msu.ru` |
| dev3 | ntutw | 14.9 s / 11 | robots and sitemaps missing; navigation 2 pages; gold on `csie.ntu.edu.tw` |
| dev3 | ub | 26.8 s / 6 | a timeout on `sitemap_443.xml` and on the homepage (access) |
| dev3 | uio | 59.2 s / 27 | `sitemap-www.mn.uio.no` `too_large`; SB-1 deadline in the walker at 55 s (**clock**) |
| dev3 | um | 18.5 s / 11 | no sitemap; navigation 1 page; gold on `study.um.edu.my` |
| dev3 | usp | 30.1 s / 19 | navigation lead `prpg.usp.br … list-of-courses` `http_error`; gold on department hosts |
| dev4 | ctu | 63.3 s / 8 | crawl-delay 10: three guessed sitemap 404s cost 30 s; SB-1 deadline in navigation at 63 s (**clock**) |
| dev4 | ktu | 26.4 s / 17 | 12 sitemap documents, 2 873 URLs, 1 kept; gold on `stojantiesiems.` / `admissions.` hosts |
| dev4 | rwth | 83.8 s / 53 | junk catalogue picks (Ambassador programme, master's programmes); the walker's faculty lead not reached |
| dev4 | unibo | 10.7 s / 7 | `sitemap.xml.gz` `unparseable`; navigation 1 page; gold on `corsi.unibo.it` |
| cohort | aalto | 10.4 s / 1 | robots.txt timed out, so the whole site counts as disallowed (access) |
| cohort | warsaw | 38.8 s / 20 | gold on `informatorects.` / `irk.` hosts |
| cohort | ubc | 109 s / 25 | navigation 47.5 s; SB-1 deadline in the walker (**clock**) |
| cohort | toronto, hku | 12–13 s | 403 / robots on the catalogue host (access) |
| dev2 | uppsala | 62 s / 20 | SB-1 deadline in the sitemap stage at 56 s (**clock**) |
| dev2 | kaznu | 4.2 s / 1 | robots.txt unreachable (access) |
| dev2 | ethz, tsinghua | 10.6–12.5 s / 8 | no sitemap; navigation 1 page; gold deeper / on another domain |
| dev2 | tec, uba, uct | 29–63 s | catalogue picks without the programme; gold on faculty hosts (uba, uct) |

## 4. Causes across sets, and the verdict

| cause (stage, mechanism) | dev3 | dev4 | cohort | dev2 | shared on dev3 **and** dev4 |
|---|---|---|---|---|---|
| **navigation fallback never reads the top-ranked hop-1 page** (no URL category, so not queued; run ends with ≥ 46 reads unused) | iitd, puc | kit | (kaist, behind a seed) | — | **yes** |
| confirm-queue order: a bounded-sitemap gold ranked out of the 8 confirm reads | auckland | — | — | khalifa | no (dev2 + dev3) |
| read and refused in a catalogue role | — | — | kaist | — | no |
| clock (SB-1 deadline, crawl-delay) on a reachable gold | — | — | — | — | no (only on unreachable cases: uio, ctu, ubc, uppsala) |
| trimmed (12-document bound, `too_large`, `unparseable`) on a reachable gold | — | — | — | — | no (the ceiling found the trim cost only aalto) |

**Shared cause on dev3 and dev4: the navigation fallback, hop 1, "never followed".** `_navigation_fallback` queues a
homepage link only when `categorise_url` gives it a category, or (with R4 off) never by its label. The homepage's best
study links lead to another host on the institution's registrable domain: `sle.kit.edu`, `admision.uc.cl` and
`cse.iitd.ac.in`. Those links carry no such URL, so the walk ends after 1–3 pages. Search used to cover this gap. With
`search_provider=none` nothing does, and 46–53 of the 60 reads go unspent. The cohort escapes this cause through its
registry seeds: vienna's and ntu's seeds *are* the hop-1 page. This is also why the cohort's hits do not need
the rule.

R4 (`--local-catalogue-entry`, rejected on 2026-10-18 with search on) reaches into the same loop by vocabulary. On
kit ("Studiengänge") and puc ("Carreras de pregrado") the probe finds that `study_section_label` names the hop-1
anchor, but it names nothing on iitd (India has no language row). The 2026-10-18 rejection said that navigation
"rarely runs under SB-1's order" when search is present. With no search it runs on most cases. A dispatch of R4 on
`search_provider=none` costs no worker hours and gives the comparison arm below.

## 5. NS-1b — worker-ready spec

**Rule NS-1 "homepage hop reads".** When the navigation fallback has read the homepage, its queue is empty and no
programme page is selected, read the homepage's best-scored study links, ranked by the product's own link score
and regardless of their URL's category, as section pages. "Section pages" means their field-named links become
programme leads under today's rules, and their catalogue-shaped links queue as today. This is structural: a link
class (any host on the institution's own registrable domain), an order (the existing score) and a read budget. It
adds no word.

- **Flag.** `HOMEPAGE_HOP_READS = False` in `backend/app/adapters/discovery/live_discovery.py` (beside
  `LOCAL_CATALOGUE_ENTRY`), plus `HOMEPAGE_HOP_READ_CAP = 5`.
  - Harness: `--homepage-hop-reads` in `backend/evaluation/research/live.py`, where it sets the constant.
  - Off-form: `--no-homepage-hop-reads`, an entry in `NEGATABLE_RULES` / `DEFAULT_OFF_NEGATABLE`, so the off arm can
    be named ahead of any default change.
  - HANDOFF §8: one contract line.
- **Where.** `LiveDiscovery._navigation_fallback`, only. Nothing in `intent.py`, the classifier, `profile_rejects` or
  the evidence stages.
  1. When the homepage is read (`start == entry["homepage"]`), the flag is on and no programme page is selected:
     score every harvested link that is not already walked or queued.
  2. The score: `navigation._score(NavigationLink(url, label), intent)`, + 3 when `study_section_label(label,
     country_languages(trace.country), degree)` is not None, + 2 when the label contains a
     `navigation._SECTION_WORDS` / `_ADMISSION_WORDS` entry.
     - The intent is built from the institution's domain, the requested degree and the *public* requested fields
       (`_public_requested_fields`), never from applicant attributes.
     - This is `index_ceiling.programmeish` without its evaluation-only `_PATH_WORD` regex.
  3. Keep the links with a score above 0 that:
     - pass `on_institution_site` (any host of the registrable domain);
     - fail `_url_excluded`;
     - fail `names_other_degree_level` and `label_names_other_level`.
  4. Append the best `HOMEPAGE_HOP_READ_CAP` of them, ties broken by URL, to the *end* of the queue, so every lead
     today's rules queue is walked first. Mark them as `section_pages` with hop 1.
  5. Their reads do not count against `MAX_FALLBACK_PAGES` (cap 5 of their own). They stay inside `_spent()`, the SB-1
     deadline and read cap, the 60-read ledger and the 120 s case clock.
  6. A refused or failed read is recorded as today (`navigation fallback: … unreachable`) and never retried.
  7. A hop-1 page reads as news, admissions or fees: `_section_page_kept` drops it as for R4.
- **Trace.** `homepage_hop_reads: list[(url, score)]` on `DiscoveryTrace`, written by `as_dict`, so the next floor
  run can be read without a probe.
- **Tests** (new `backend/tests/test_homepage_hop_reads.py`, synthetic hosts `www.example-uni.edu` /
  `admit.example-uni.edu`, with no word from a development page):
  1. The homepage's only study link has a URL that does not categorise and points to the sibling host. That page links
     the programme page with a field-named anchor. On: the programme page is selected and confirmed. Off: the sibling
     page is never fetched (assert the fake fetcher's calls), and the result is byte-identical to the flag-less trace.
  2. Six scored links: only the best five are read (cap), in score order.
  3. A link to another registrable domain is never read. A link naming another degree level is never read.
  4. A URL-categorised catalogue lead on the homepage is walked before any hop read (order unchanged).
  5. A refused hop page (robots, 403) uses one ledger read and is not retried.
  6. A programme page already selected (a seed or the sitemap) means no hop reads at all.
  7. The budget tests pass unchanged, with the flag both off and on. These are `test_case_read_ledger.py`,
     `test_stage_budgets.py` and `test_case_time_budget.py` (the plan's `test_read_budget*`; no file has that name).
  8. `seed_demo.py` output byte-identical.
- **Dispatch** (`NEXT_CYCLES_2026-10-21` §4):
  - `search_provider=none`, `columns=4`, `extra_args=--homepage-hop-reads`, four sets normal (`ns1-<set>`) and
    knockout (`ns1-ko-<set>`).
  - The guard: `search_provider=recorded`, same flag, dev3 and dev4 (`rp-ns1-<set>`).
  - The comparison arm, free and parallel: `search_provider=none`, `extra_args=--local-catalogue-entry`
    (`ns-r4-<set>`). If R4 alone gains kit and puc stably, the cheaper verdict is "R4 on when no search provider is
    configured". NS-1 still owns iitd-shaped (English) cases.
- **Pre-registered expectation (no-search arms).**
  - **dev3**: puc missed → **hit** (hop 1 rank 4; the gold's anchor and URL name the field, `matches_field` 24).
    - iitd **stays missed**: hop 1 is read, but its link to the gold is "B.Tech" with a URL that names no field, so
      `NAVIGATION_FIELD_LEADS` refuses it. A hit there is a bonus, not the bar.
    - auckland stays missed (hop 1 is rank 17; its cause is the confirm order).
    - imperial, unsw and ucph are unchanged: navigation never runs there.
  - **dev4**: kit missed → **hit** (hop 1 rank 5; anchor "Informatik", `matches_field` 8). ctu stays a clock case,
    and unibo, ktu and rwth are unchanged. On vut, taltech, boun and itu (gold unknown) a newly returned page reads
    "unadjudicated", and every one is listed in the verdict.
  - **cohort**: no change. kaist's navigation does not run (the seed fills the slot). Groningen, delft, vienna and ntu
    are found before navigation.
  - **dev2**: no change. psaclay and tcd must stay hits (their walk queues URL-categorised leads first).
  - Expected total **9/39 → 11/39**, 0 wrong.
- **Bar** (as §3 NS-1b):
  - No-search: no hit lost on any set; 0 wrong pages; knockout `wrong_programme_pages` not up (today 0 / 1 / 1–2 / 1).
  - A stable gain on **both** dev3 (puc) and dev4 (kit) across the four columns.
  - Recorded guard: identical or better, `recorded_search_misses` equal to the off arm.
  - Then default-on. Otherwise `hypotheses.json` gets the cause with the per-case trace rows.

## 6. Side observations (no action taken)

- unsw returned two pages beside the gold: the diploma and the CS-and-law double degree. The case scores a hit, so the
  "0 wrong" row counts outcomes, not pages.
- When robots.txt names no sitemap, the sitemap step guesses up to four paths (`SITEMAP_FALLBACK_PATHS`). On most
  such hosts (kit, itu, msu, um, ethz, utokyo and others) all four return 404, which costs 6–8 s on a normal host. On
  ctu's crawl-delay-10 host, three guesses cost 30 s, and that case ended on the SB-1 deadline. This is a clock cause
  on one set only; it is recorded here for a later ticket.
- The confirm-queue order cause (auckland, khalifa) is shared by dev2 and dev3, not dev4. It is the next candidate if
  NS-1 fails its bar. **Corrected in §7**: only auckland is a confirm-queue order case. khalifa's gold is not in its
  sitemap.

## 7. CO-1 step 1: the confirm-queue order on auckland and khalifa (2026-10-20)

Ticket CO-1 step 1 of `NEXT_CYCLES_2026-10-22.md` §3. Research only: no file under `app/` changed.

**Verdict: not shared.** The confirm-queue order loses auckland's gold (dev3), and a generic order change puts it at
read 4 of 8. It does not lose khalifa's gold (dev2). khalifa's gold is **not in `sitemap_urls_seen`** at all, so no
order or budget split in `keep()` / `_confirm_programs` can reach it. khalifa is lost in the catalogue walker, which
reads two hub pages that link the gold, refuses them as programme pages, and never follows their links. §2 and §4
called khalifa "bounded (hop 0)" and "ranked out: confirm-queue order". That came from the `INDEX_CEILING` row, which
cannot be reproduced (§7.2). Under the §3 CO-1 bar ("a stable gain on **both** dev2 and dev3"), **step 2 as written
cannot pass.** §7.4 gives the rule anyway, worker-ready, with its one-set expectation, so the planner can decide in
one line. §7.5 names the two-set shape that does exist (a refused hub's links are never followed) as a separate
candidate.

### 7.1 Inputs and method

- **Captures**: the artifacts `expert-recovery-<run>`, downloaded into this session's own scratchpad. Six captures
  per case:
  - `ns-floor-dev2` 39350477901 and `ns-floor-dev3` 39350480488 (pipeline `f0d1830e`);
  - `ns1-dev2` 39379523420 and `ns1-dev3` 39379525547 (pipeline `0bc7d6c0`), two on and two off columns each.

  For the simulation over all four sets: `ns-floor-cohort` 39350475181 and `ns-floor-dev4` 39350483178. Their
  confirm reads are stable on both cases: all 5 khalifa captures read the same 3 pages, and all 5 auckland captures
  read the same 8.
- **The seen list**: the captures record `sitemap_urls_seen` as a **count**, not a list, and no capture names the
  gold. So the list was rebuilt. A probe re-read, through the production `Fetcher` (robots, crawl delay, our user
  agent, from the sandbox proxy), exactly the documents in each case's captured `sitemaps_read`, in order. It
  replayed `SitemapReader.collect`'s inner loop: `_resolve_loc`, `canonical_url`, dedup, `same_institution`. Checks
  against the captures:

  | case | URLs seen, probe vs capture | matched exactly? |
  |---|---|---|
  | khalifa | 3 569 / 3 569 | yes |
  | auckland | 20 906 / 20 908 (the ns1 columns say 20 906) | near |
  | delft, kaist, rwth, psaclay, unsw, warsaw, hku, taltech, ucph, uct, ktu | — | yes, or within 5 URLs |
  | imperial, uio, uppsala | 28 093 / 28 050, 76 591 / 76 584, 133 760 / 133 729 | drift ≤ 0.2 % |
  | chula | 649 / 1 527 | no |
  | boun | 1 768 / 2 471 (four documents `robots_disallowed` from this vantage point) | no |
  | tec | 0 / 1 150 (`http_error`) | no |
- **keep() and the queue, offline**: the production functions are imported read-only: `categorise_url`,
  `matches_field`, `matches_degree`, `names_other_degree_level`, `_prefer_exact_field`,
  `MAX_CANDIDATES_PER_CATEGORY` = 40, `MAX_PAGES_PER_CATEGORY` = 3 and `MAX_PROGRAM_CANDIDATES_CHECKED` = 8, at
  `HEAD` `7d55695f`. Defaults apply: `SITEMAP_KEEP_EVIDENCE_SUM` and `SERVICE_PAGE_PRIORITY` are off, as the captures
  ran them. Two closures are replicated line for line:
  - the `keep()` closure in `_discover_institution`;
  - the queue build at the top of `_confirm_programs`. That build takes `selected` (the selection loop's top 3 by
    `(-score, len(url))`, then `_prefer_exact_field`), then `sorted(ranked, reverse=True)`, then
    `_prefer_exact_field`.

  The fields are `["computer science"]` and the degree is `bachelor`.
- **Validation**: the simulated first 8 reads match the captured confirm reads, in order:
  - auckland: 6/6 successful reads, plus the two `http_error` reads at positions 6 and 8 in the log;
  - khalifa 3/3, taltech 8/8, uct 8/8, uio 8/8, unsw 3/3;
  - imperial 7/8: the 8th read is R2b's inserted `computing-beng`;
  - ucph 5/8: the other three are R1 local hreflang twins inserted at read time. The trace logs four such
    insertions.
- **Pages read beyond the sitemaps**, all through `Fetcher`, each once, to name the cause and to predict verdicts
  with `classify_page` + `profile_rejects`:
  - khalifa: the gold, `/academics/undergraduate-programs` and `/college-of-computing-and-mathematical-sciences`
    (the first attempt was `robots_disallowed`, because robots.txt was unreachable from this vantage point; the
    retry read them);
  - auckland: `find-a-study-option/computer-science.html`, the gold `…/computer-science/undergraduate.html`, and the
    five pages a variant newly queues;
  - imperial: the two pages a variant newly queues.

  There were no search provider calls.
- **Not opened**: any heldout file, capture, log or label, `scratchpad/HELDOUT_QUARANTINE_DO_NOT_OPEN`,
  `scratchpad/DEV5_BLIND`, `DISCOVERY_ANALYSIS_2026-10-17.md`, dev5, or any other scratchpad.

### 7.2 The per-case rank table

| case | gold form (draft3 `programme_urls`) | in `sitemap_urls_seen`? | `keep()` | score (structure + field + level) | queue rank / length | read? |
|---|---|---|---|---|---|---|
| auckland | `…/find-a-study-option/computer-science/undergraduate.html` | yes | kept | 19 = 3 + 16 + **0** | **26 / 40** | no: reads 1–8 are ranks 1–8 |
| auckland | `…/find-a-study-option/bachelor-of-science-bsc.html` | yes | kept, then **evicted** from the 40 by `…/BSc-degree-planners.html` (17) | 15 = 3 + 8 + 4 | — | no |
| auckland | `…/computer-science/undergraduate/bsc-compsci-from-2019.html` | no | — | — | — | — |
| auckland | `study.auckland.ac.nz/ords/…?p7_code=COMP-BSc` | no (another host) | — | — | — | — |
| khalifa | `www.ku.ac.ae/program/bsc-in-computer-science` (and its `/ar/` twin) | **no**: `sitemap.xml` has 3 569 URLs and no `/program/` path; `sitemap_index.xml` (3 743 URLs, never read: SM-1 drops the other guesses once `/sitemap.xml` answers) has none either | — | it would score 29 = 9 + 16 + 4, the top of the queue | **not queued** | no |

**auckland, what outranks the gold, and why.**
1. Every computer-science page under `find-a-study-option/` scores 19: structure 3 + field 16. The level bonus is 0
   for all of them. `degree_level_named` reads a level only as a slug word bounded by `([/-]|$)`, so a trailing
   `.html` hides it:
   - `…/computer-science/doctoral.html` reads no level (`…/doctoral` without the extension reads `phd`);
   - so does `…/postgraduate.html` (`…/postgraduate-study-options.html` reads `master`);
   - so does the gold `…/undergraduate.html`.
   So the doctoral and postgraduate siblings are neither refused by `names_other_degree_level` nor penalised.
   The gold earns no +4.
2. 26 candidates tie at 19:
   - the hub `computer-science.html`, its doctoral, postgraduate and undergraduate children;
   - 21 conjoint pages under `undergraduate-study-options/conjoint-programmes/`, each 7 + 8 + 4. "science" scores
     8 in `bachelor-science-bachelor-laws`, and "bachelor" scores 4;
   - `professional-development-and-short-courses/science-computing-and-mathematics.html`.
3. The two sorts disagree on ties:
   - The selection loop (`scored.sort(key=(-score, len(url)))`) puts the shortest URLs first. That fills
     `selected` with the hub, `doctoral.html` and `postgraduate.html`, which are queue ranks 1–3.
   - `_confirm_programs` then appends the rest by `sorted(ranked, reverse=True)`, which breaks a tie on the **URL
     string, descending**. So `undergraduate-study-options/…` (u) comes before `professional-development…` (p),
     which comes before `find-a-study-option/…` (f).
   - The gold, the next-shortest URL of the tie, drops from rank 4 to rank 26, behind the 21 conjoint pages.
4. Reads 4–8 went to conjoint pages: three were refused on subject, two were `http_error`.

None of the three sources the ticket asked about inserted these pages:
- `_queue_english_alternate`: the site is English, so there is no twin;
- `_queue_field_sibling`: no read was a related verdict;
- `_queue_subpage_parent`: no read was a sub-page refusal.

`keep()` queued all eight.

The hub `computer-science.html` itself links the gold ("Undergraduate study"). Confirm read it at rank 1 and refused
it as `unknown`.

**khalifa, what was read instead.** The program-page category kept only three URLs, so the confirm stage read all
three. The 8-read budget was not binding.

| rank | page | score (structure + field + level) | captured verdict |
|---:|---|---|---|
| 1 | `/bsc-math-alumni-participate-in-women-in-data-science-2021` (news) | 17 = 5 + 8 + 4 | "reads as irrelevant" |
| 2 | `/academics/undergraduate-programs/minor-in-nuclear-engineering` | 8 = 4 + 0 + 4 | "reads as unknown" |
| 3 | `/academics/undergraduate-programs/minor-in-unmanned-aerial-vehicles` | 8 = 4 + 0 + 4 | "reads as unknown" |

The walker then walked the sitemap's first catalogue pick, `/bachelor/accelerated-master-of-science-program`. It read
its candidates as programme pages:
- `college-of-computing-and-mathematical-sciences` (16): `reads_as_unknown`;
- `academics/undergraduate-programs` (15): `reads_as_program_detail`;
- `undergraduate-admissions` (13);
- `zmu` (12, "BSc in Computer Science program"): accepted, so `walker_stopped`. The draft3 labels mark it related.

The two hub pages both link the gold as "Bachelor of Science in Computer Science" (read on 2026-10-20). The walker
does not harvest a refused candidate's links, so the gold was one hop away and never read.

The `INDEX_CEILING_2026-10-19` row "khalifa bounded yes, hop 0" does not reproduce. `read_bounded` runs the same
`SitemapReader.collect`, and neither sitemap document lists the gold today. The capture's seen count is identical to
today's, so the row was most likely matched on something other than the draft3 gold. IC-2 should re-measure it.

### 7.3 Candidate changes, simulated over the four sets

Which cases a confirm-queue order can touch: only those where the queue is longer than the 8 reads (`confirm` = 8 in
the capture). That is auckland, imperial, ucph and uio on dev3, uct on dev2, and taltech on dev4. No cohort case
qualifies. Every other case reads its whole queue, so an order change cannot change which pages it reads. All six
were probed and simulated.

Variants:
- **V1, order**: the queue continues in the selection loop's own order, `(-score, len(url))`, then
  `_prefer_exact_field`, instead of `sorted(ranked, reverse=True)`.
- **V2, exclusion**: `keep()` reads the level on the URL with its trailing file extension removed (`.html`, `.htm`,
  `.php`, `.asp(x)`, `.jsp`). That is the existing `names_other_degree_level` / `matches_degree`, applied before
  ranking.
- **V3**: V1 and V2 together.
- **V4, budget split**: at most 2 of the 8 reads per URL directory.

| case (set) | base: gold rank / queue | V1 | V2 | V3 | V4 | new non-gold page in the first 8 (V1) and its offline verdict |
|---|---|---|---|---|---|---|
| auckland (dev3) | 26 / 40 (missed) | **4** | **1** | **1** | 28 | after the gold: `science-computing-and-mathematics.html` (unknown), conjoint BA/BSc and BMus/BSc (subject refused). V3 adds BN/BSc (unknown) and BCom/BSc (subject). **0 would be confirmed** |
| imperial (dev3) | 13 / 40 (hit via R2b after read 1) | 12 | 13 | 12 | 13 | R2b still fires on read 1, so the hit is unchanged. `apply-to-study-materials-science` (general_admissions) and `materials-science-career-prospects` (subject refused): **0 confirmed** |
| ucph (dev3) | 1 / 40 (hit) | 1 | 1 | 1 | 1 | none |
| uio (dev3) | not queued (clock case) | — | — | — | — | none; the first 8 are identical |
| uct (dev2) | not queued | — | — | — | — | none; the first 8 are identical |
| taltech (dev4) | related not queued | — | — | — | — | none; the first 8 are identical |
| khalifa (dev2) | **not seen** | — | — | — | — | none (3-URL queue) |
| unsw (dev3, queue not binding) | 2 / 40 (hit) | 2 | 2 | 2 | 2 | none |

**Gold in the confirm budget** across the 39 development cases:
- statically, base 2 (ucph, unsw) plus imperial through R2b, so 3;
- with V1, V2 or V3, 3 + auckland, so **4**;
- with V4, 3.

New non-gold pages that would be confirmed: **0** under every variant. No change reaches khalifa.

### 7.4 CO-1 step 2: worker-ready spec (the rule; the planner decides whether it is built under a one-set bar)

**Rule CO-1 "confirm queue in selection order".** `_confirm_programs` continues its queue in the order the selection
loop already uses: score descending, then shorter URL, then `_prefer_exact_field`. It no longer re-sorts by
`(score, url)` descending, which breaks ties alphabetically.
- **Structural**: one sort key. No word, no read added, no budget changed.
- **Off**: byte-identical.
- **What it repairs**: a self-inconsistency between two sorts of the same list. The selection loop's tie rule is the
  shorter, hub-closer URL. The queue's tie rule is reverse alphabetical, which carries no information.
- **V2 stays out of this ticket.** It is a second flag (`LEVEL_SLUG_IGNORES_EXTENSION` in `keep()` only), to open
  only if V1 fails its bar. It changes which URLs `keep()` refuses, so it needs its own knockout look.

- **Flag.**
  - `CONFIRM_QUEUE_SELECTION_ORDER = False` in `backend/app/adapters/discovery/live_discovery.py`, beside
    `CONFIRM_REJECTS_SUBPAGE_HEAD`, with a comment citing this §7.
  - Harness: `--confirm-queue-selection-order` in `backend/evaluation/research/live.py`, where it sets the constant
    as `--homepage-hop-reads` does.
  - `NEGATABLE_RULES["confirm-queue-selection-order"]`, plus the stem in `DEFAULT_OFF_NEGATABLE`.
  - One HANDOFF §8 line.
- **Where.** `LiveDiscoveryAdapter._confirm_programs`, the `for _score, url in _prefer_exact_field(sorted(ranked[…],
  reverse=True), …)` line only. When the flag is on, it uses
  `sorted(ranked[PageCategory.PROGRAM_PAGE], key=lambda p: (-p[0], len(p[1]), p[1]))`. The final URL key makes a
  full tie deterministic.
  - `selected` (the first 3) is unchanged.
  - The reads cap, the R2b / SP-1 / LI-1 insertions, `_spent()` and the ledger are unchanged.
  - **Not touched**: `keep()`, the selection loop, navigation, the walker, `profile_rejects`.
  - Concurrency note: `live_discovery.py` is held in sequence (PC-1, then TR-1, then CO-1 step 2). Rebase on TR-1's
    `confirm_queue` rows, and record the rank under both orders there when the flag is on.
- **Tests**: new `backend/tests/test_confirm_queue_order.py`, with synthetic host `www.example-uni.edu`, a fake
  fetcher and no development page's words.
  1. A sitemap lists `/find/field-x.html` (hub, reads unknown), `/find/field-x/doctoral.html`,
     `/find/field-x/postgraduate.html` and `/find/field-x/undergraduate.html` (a programme page at the requested
     level). It also lists six longer tied URLs under `/zz-options/combined/…` that sort after `/find/` in reverse
     and read as other-subject programmes. Every score must tie. Assert the ties through `categorise_url` and
     `matches_field` in the test, not by hand.
     - On: the undergraduate page is read within the 8 and confirmed.
     - Off: it is never fetched (assert the fake fetcher's calls), and the trace is byte-identical to the
       flag-less run.
  2. A queue of 8 or fewer: the same set of reads with the flag on and off (order only).
  3. `selected` (the first 3) is identical on and off.
  4. R2b still inserts the field sibling right after a related verdict with the flag on (an imperial-shaped synthetic
     case).
  5. The budget tests pass unchanged with the flag off and on: `test_case_read_ledger.py`, `test_stage_budgets.py`
     and `test_case_time_budget.py`.
  6. `seed_demo.py` output byte-identical.
- **Dispatch** (`NEXT_CYCLES_2026-10-22` §4, the CO-1 row):
  - `search_provider=none`, `columns=4`, `extra_args=--confirm-queue-selection-order`: four sets normal
    (`co1-<set>`) and knockout (`co1-ko-<set>`);
  - the recorded guard on dev2 and dev3 (`rp-co1-<set>`).
- **Pre-registered expectation** (no-search arms):
  - **dev3**: auckland missed → **hit** in 4/4 columns (gold at read 4, accepted offline as `program_detail`,
    bachelor, "Undergraduate study in Computer Science"). Reads 5–8 are refused, which is 0 new confirmed pages.
    imperial stays a hit (R2b on read 1). ucph and unsw are unchanged. uio is unchanged.
  - **dev2**: **no change**. khalifa stays related, because its gold is never queued. uct's first 8 are identical.
  - **dev4**: no change (taltech's first 8 are identical).
  - **cohort**: no change (no case is cap-bound).
  - Expected total, no-search: **+1** (auckland). Knockout: unchanged, since an order cannot add a page that is not
    already queued, and on the knockout arms the gold is hidden anyway. Recorded guard: identical.
- **Bar.** The §3 bar's "stable gain on both dev2 and dev3" **cannot be met by this rule, by measurement.** The
  planner chooses one of two paths:
  - (a) build it under a one-set bar. The 13-Q2 (a) answer: the mechanism is two sorts of one list disagreeing, so
    it is dev-wide by construction. It changes the reads of every cap-bound queue with ties, which is 2 of the 6 on
    the development sets. Then "no hit lost; 0 wrong; knockout not up; auckland hit in 4/4; recorded guard
    identical" means default-on.
  - (b) do not build it and record it in `hypotheses.json` with this table.

### 7.5 The two-set shape that does exist (a candidate, not built)

Both cases lose a gold that sits **one link below a page the pipeline read and refused**:
- **auckland**: the hub `computer-science.html` was read in confirm and refused as unknown. It links the gold as
  "Undergraduate study".
- **khalifa**: `college-of-computing-and-mathematical-sciences` and `academics/undergraduate-programs` were read in
  the walker and refused. Both link the gold as "Bachelor of Science in Computer Science".

The two cases differ in where the hub was read:

| case | stage that read the hub | what is missing |
|---|---|---|
| auckland | confirm | that stage has no link follow |
| khalifa | walker | the walker harvests only its catalogue's links, not a refused candidate's |

A rule of the shape "a read page refused as unknown, or as a programme of another subject, whose URL or head names
the requested field, is read once as a catalogue: its links that name the field, and no other level, are queued
within the existing caps" would cover both. It would cost at most one extra harvest per refused hub and no extra
read beyond the queued links.

It is not simulated here, because simulating it needs the hub pages' links on every development case, which means
reads. If the planner opens it, its step 1 is to:
- list every refused-hub read on the four sets' floor captures;
- count how many link a gold or a related page;
- check the knockout arms for a page it would newly confirm.

On khalifa the related `zmu` would still be read first unless the hub links are queued ahead of the walker's
lower-scored candidates, so the order inside that rule matters too.

## 8. FRH step 1: does following a refused hub's field-named link reach the gold? (2026-10-20)

Research only: no file under `app/` changed, `live_discovery.py` untouched (another worker holds it). Question from
§7.5: auckland and khalifa lose a gold that sits one link below a page the run read and refused, because neither
the confirm stage nor the walker follows a refused page's links. Bar: the shape reaches the gold on **≥ 2 sets**
with **0 predicted new wrong confirmations**.

**Verdict: the bar is met, but only by a structural refinement of the plain shape.** "Follow the best field-named
link of a refused hub" as written reaches only khalifa (dev2). On auckland (dev3) the gold's anchor is
"Undergraduate study": the label names no field, and by link score the gold ranks 2nd of 3 behind "School of
Computer Science". The label-only variant also confirms a wrong page there. The shape passes when:
- the hub's own children come first (links under the hub's path, extension stripped);
- the hub's URL or head names the field;
- the rule stops once the case has a confirmed programme page;
- at most 3 follows run per case.

It then reaches the gold on **dev2 (khalifa) and dev3 (auckland), 5/5 no-search captures each**, with 0 non-gold
pages confirmed on any arm. Cohort and dev4 have no reachable case: kaist's refused pages link the gold only as
"교육" (Education), which names no field, and no dev4 refused page links a gold or labelled related page. The step-2
spec is in §8.5.

### 8.1 Inputs and method

- **Captures** (artifacts `expert-recovery-<run>`, this session's own scratchpad), every case of the four
  development sets, 569 captures in all:
  - no-search: `ns-floor-<set>` (39350475181 / 477901 / 480488 / 483178, one column) and `ns1-<set>` (39379521311
    / 523420 / 525547 / 527478, two on and two off columns), 217 captures;
  - knockout: `ns1-ko-<set>` (39379529849 / 532195 / 534372 / 536854), 176 captures;
  - guard, recorded search, default config: `aw2-<set>` (39371051329 / 053780 / 056063 / 058290), 176 captures.

  Scored with `metrics.adjudicate_programme_pages` against `ground_truth.reviewed11` and `dev2/dev3/dev4.draft3`.
- **Refused pages**: every discovery-phase read was recovered from the case log. That is the first
  `read_ledger.by_phase.discovery` uncached `get` lines, because the walker's trace outcomes are capped at 200 and
  drop reads on large catalogues. Each read was tagged with its stage:
  - **confirm**: `pages_read` with a non-empty verdict;
  - **walker**: a `walker.candidates` URL that is not a walked catalogue, with its `reads_as_*` /
    `degree_level_mismatch` outcome. When the capped trace lost the outcome, the read is judged offline: groningen's
    gold, for one, was accepted in the walker but has no outcome in the trace.

  The result is 313 distinct refused pages on 38 cases.
- **Re-reads**: 1 082 URLs, through the production `Fetcher`: robots honoured, our user agent, its own rate limit,
  one read each. They were the refused pages, every rule-candidate link the simulation follows, the top 3 candidate
  links on each missed case's refused pages, and every gold and labelled-related URL.
  - From this sandbox a direct read finds robots.txt unreachable, so every page is `robots_disallowed`. All reads
    therefore ran with `trust_env_proxy=True`, as in §7.
  - 920 were read; the failures were mostly 404s and robots refusals on pages the runs had also failed on.
  - 10 timeouts (uct `/oic/…`) were retried once, and 9 of them were then read.
  - No refused page on a reached case failed. No search provider was called.
- **Simulation**, offline, at `HEAD` `c7028b01`, using production functions only:
  - `catalog_walker.extract_links` and `score_link`, `label_names_other_level`, `matches_field_text`,
    `matches_field`;
  - verdicts from `classify_page` + `profile_rejects` (field `computer science`, level `bachelor`).

  The simulation walks each capture's refused reads in their captured order. For each refused page that passes the
  variant's trigger, it follows the variant's chosen link if that link has not been read yet. It records the
  followed page's class and verdict:
  - **GOLD**: the URL, or an hreflang twin a gold page declares, is a canonical variant of a draft3 / reviewed11
    `programme_urls` entry;
  - **related**: a labelled `related_programme_urls` page;
  - **other**: any other page.

  On a knockout capture a followed gold is refused, as the arm refuses it. A followed page is never itself a hub
  (one hop).
- **Not opened**: any heldout file, capture, log or label, `scratchpad/HELDOUT_QUARANTINE_DO_NOT_OPEN`,
  `scratchpad/DEV5_BLIND`, `DISCOVERY_ANALYSIS_2026-10-17.md`, dev5, or any other scratchpad.

### 8.2 The per-case table: refused pages that link the gold, on captures that missed it

"Link #" is the anchor's position among the page's same-site links, which is `extract_links` order and within
`MAX_LINKS_SCANNED`. "Rank" is the gold's rank among the rule's candidate links, best first, by the rule's order:
- **label**: label names the field;
- **label/URL**: label or URL names the field, by `score_link`;
- **child-first**: label/URL, with the hub's children first.

| set | case (captures missed) | refused page (stage, verdict) | anchor to gold, link # | rank: label / label/URL / child-first | does a one-hop follow reach the gold? |
|---|---|---|---|---|---|
| dev2 | khalifa (related 5/5 no-search, 4/4 ko) | `/college-of-computing-and-mathematical-sciences` (walker lead 1, `reads_as_unknown`) | "Bachelor of Science in Computer Science", #110 | **1/2 / 1/7 / 1/7** | **yes**, every variant. The gold reads as `program_detail`, bachelor, accepted. The walker then stops before `zmu`. |
| dev2 | khalifa | `/academics/undergraduate-programs` (walker lead 2, `reads_as_program_detail`, refused on subject) | same label, #105 | not a listing page | Only an any-refusal trigger fires here, and lead 1 has reached the gold already. |
| dev3 | auckland (missed 5/5 no-search, 4/4 ko) | `find-a-study-option/computer-science.html` (confirm read 1, "reads as unknown") | "Undergraduate study", #203; the URL `…/computer-science/undergraduate.html` names the field, the label does not | **— / 2/3 / 1/3** | **Only child-first.** By score, "School of Computer Science" (24, reads unknown) comes first. The gold (`programme_urls` entry 4) is accepted as `program_detail`, bachelor. |
| cohort | kaist (missed 5/5) | 4 pages on no-search, `content?menu=318`, `aiiscs/undergraduate`, `aiiscs/infoservice`, `bbs/ainews` (confirm / walker, unknown), and 5 more on aw2 | "교육" (Education), #59–60; URL `content?menu=188` | no candidate | **No**: neither the label nor the URL names the field. No word-free field rule reaches it. |
| dev2 | uct (aw2 only, related 4/4) | `department-computer-science` (head names a unit), and two other-subject programme pages | "BSc degrees", #50–51 | not field-named | **No**. The rule reads `ba-informatics`, which is labelled related, and the outcome stays related. |
| dev3 | ntutw (aw2 only, missed 4/4) | `www.csie.ntu.edu.tw/` (confirm, unknown) | "大學部招生", #49 | not field-named | **No**. The rule reads a news item, which is refused. |
| dev3 | usp (aw2 only, 1/4 related) | `icmc…/applied-mathematics-and-scientific-computing` (confirm, refused on subject, `program_detail`) | "Computer Science", #27 | 1/1, but the page is not a listing | Only an any-refusal trigger fires, and that trigger adds wrong pages elsewhere (§8.3). |
| dev4 | — | no refused page on any missed capture links a gold or a labelled related page | | | — |

The pages were re-read on 2026-10-20, a few hours after the runs, from another vantage point.

### 8.3 Variants simulated, and the bar

Gains and wrong confirmations are counted over captures: 217 no-search, 176 ko, 176 aw2. A "wrong" is a newly
confirmed page classed **other**: on a missed case it turns the outcome to wrong, and on a hit case it adds a wrong
page.

| variant (trigger → link chosen, 1 per hub) | no-search gold reached | new wrong confirmations | bar |
|---|---|---|---|
| refused **listing** page (unknown / catalogue) → best **label**-named link | khalifa 5/5 (dev2) | **auckland 5 ns + 4 ko + 4 aw2**: `postgraduate.html` → "Computer Science" → `study.auckland.ac.nz/…p7_code=COMP-BSc(Hons)` | fails |
| listing → best **label- or URL**-named link | khalifa 5/5 | 0 | fails: one set |
| listing → best 2 label/URL links | khalifa, auckland | the same BSc(Hons) page on auckland | fails |
| **any** refusal → best label link / label-or-URL link | khalifa 5/5. usp gains 1 aw2 capture. | label link: the auckland BSc(Hons) page (5 ns + 4 ko + 4 aw2). Label-or-URL link: vienna, a hit case, 4/4 aw2, where the refused "recommended path of study" pages lead to `…/bachelor-computer-science-specialisations` and its German twin, which are accepted. | fails |
| listing → label/URL, **hub's children first**, ≤ 3 per case | khalifa 5/5, auckland 5/5 | 0. Labelled related confirmed: `zmu` ×5 ns, ×4 ko, ×4 aw2 (khalifa still hits), `ba-informatics` ×4 aw2 (uct stays related). | passes; khalifa's gold is its 3rd follow (cap 2 loses it) |
| **FRH**: as above, and the hub's URL or head names the field, and no follow once the case has a confirmed programme page | **khalifa 5/5, auckland 5/5** | **0**. The only non-gold page confirmed on any arm is `ba-informatics` ×4 aw2, a labelled related page; uct stays related. | **passes** |

**Risk of FRH, reads and confirmations by capture group:**

| arm | group | captures | follows | of which gold | non-gold reads | non-gold confirmed |
|---|---|---:|---:|---:|---:|---:|
| no-search | baseline hit | 46 | 10 | 0 | 10 | 0 |
| no-search | gained (khalifa, auckland) | 10 | 10 | 10 | **0** | 0 |
| no-search | still not hit | 161 | 24 | 0 | 24 | 0 |
| knockout | all | 176 | 70 | 8 (refused by the arm) | 62 | 0 |
| aw2 guard | baseline hit | 102 | 28 | 12 | 16 | 0 |
| aw2 guard | not hit | 74 | 44 | 0 | 44 | 4 (`ba-informatics`, labelled related) |

- At most 3 follows run in a capture; 449 of 569 captures follow nothing.
- The 34 no-search non-gold reads are all refused offline. By case:
  - taltech: 15 department pages;
  - tcd: 10 micro-credential pages (a hit case, two per capture);
  - vut: 5 and unibo: 3 "open science" pages, which match because the URL-field test reads "science";
  - rwth: 1 footer page.
- The four clock cases (uio, ctu, ubc, uppsala) follow nothing.

### 8.4 Caveats

- The child-first order was found by looking at auckland, so one case drives it. The knockout and recorded arms in
  §8.5 are the guard against overfit.
- The BSc(Hons) plan link stays on auckland's `postgraduate.html` at candidate rank ≥ 2. A variant that follows
  more than one link per hub, or orders by score alone, confirms it as a wrong page.
- The simulation keeps the captured read order. It does not model the clock: every follow is one network read,
  inside `_spent()`, the 28-read discovery cap and the case clock.
- If CO-1 step 2 (§7.4) lands first, auckland's gold is read at confirm read 4 anyway. FRH's evidence then shrinks
  to one set (khalifa). The planner orders the two tickets with that in mind; FRH alone owns khalifa.

### 8.5 FRH step 2: worker-ready spec

*Amended by §8.6 (2026-10-25): the URL half of the hub test is SR-1's whole-phrase test, and a hub is followed once.*

**Rule FRH "follow a refused hub's field link".** A page the confirm stage or the walker reads as a programme
candidate is a **hub** when all of these hold:
- `profile_rejects` refuses it;
- it reads as a listing (`page_type` in `{PROGRAM_CATALOG, UNKNOWN}`, identity recovery's `_LISTING_PAGE_TYPES`);
- its final URL names a requested field (`matches_field(url, fields) > 0`), or its classified head does
  (`matches_field_text(page.subject, fields)`).

For a hub, its single best field link is read next, one hop, and judged by `profile_rejects` like any candidate.
The rule is structural: a page class, an order and a read cap. It adds no word.

- **Flag.** `FOLLOW_REFUSED_HUB_LINK = False` and `FOLLOW_REFUSED_HUB_LINK_CAP = 3` in
  `backend/app/adapters/discovery/live_discovery.py`, beside `CONFIRM_QUEUE_SELECTION_ORDER`, with a comment citing
  this §8.
  - Harness: `--follow-refused-hub-link` in `backend/evaluation/research/live.py`, setting the constant as
    `--homepage-hop-reads` does.
  - `NEGATABLE_RULES["follow-refused-hub-link"]`, plus the stem in `DEFAULT_OFF_NEGATABLE`.
  - One HANDOFF §8 line.
  - Concurrency: `live_discovery.py` is held in sequence (PC-1, TR-1, CO-1 step 2). This ticket goes after them;
    rebase on their trace rows.
- **The link** comes from a new pure helper `refused_hub_lead(html, page_url, hub_url, domain, extra_domains,
  degree, fields, skip) -> WalkerLink | None` in `backend/app/adapters/discovery/catalog_walker.py`. It sits next to
  `score_link`, which both stages already import.
  1. Take `extract_links(html, page_url, domain, extra_domains=extra_domains)`.
  2. Keep a link only if all of these hold:
     - `score_link(url, label, degree, fields)` is not `None`. That already drops excluded URLs, labels under 10
       characters, URLs naming another level, and course links;
     - `label_names_other_level(label, degree)` is false;
     - `matches_field_text(label, fields)` or `matches_field(url, fields) > 0`;
     - the URL is not in `skip` (read, queued for the current stage's reads, or followed already).
  3. Order the kept links by `(not child, -score, url)`. A child is a link on the hub's host whose path starts with
     the hub's path, minus a trailing `.html/.htm/.php/.aspx/.jsp/.cfm`, plus `/`.
  4. Return the first. Exactly one link is read per hub.
- **Where.**
  - (a) `LiveDiscoveryAdapter._confirm_programs`, in the `reason is not None` branch, after the R2b / SP-1 / LI-1
    insertions:
    - The hub must not have been reached by a follow.
    - When the flag is on, the case's follow count is under the cap, nothing is confirmed yet (`confirmed`,
      `self._confirmed` and `selected[PROGRAM_PAGE]` are all empty) and `not self._spent()`, read the helper's link
      at once.
    - It is **outside** `MAX_PROGRAM_CANDIDATES_CHECKED`, so no queued read is displaced.
    - Accepted, it is appended to `confirmed` and `self._confirmed`, exactly like a queued candidate.
  - (b) `CatalogWalker._read_lead`, after a refusal recorded as `reads_as_<type>`. It takes a new optional
    constructor argument `follow: Callable[[str, str, PageClassification], Awaitable[str | None]] | None`. The
    adapter passes it only when the flag is on; it owns the cap and the stop condition.
    - An accepted page goes to `walk.confirmed`, so `stop_when_confirmed` ends the walk.
    - Its outcome is recorded as `hub_link_<page_type>` or `hub_link_<fetch outcome>`, never `reads_as_*`, so
      `_descent_lead` is unchanged.
  - **Not touched**: navigation fallback, identity recovery (it has its own listing follow), `keep()`, the queue
    order, the classifier, `profile_rejects`.
  - **Budget**: one network read per follow, through the budgeted fetcher. It counts in SB-1's read cap and deadline,
    the 60-read ledger and the case clock. A refused fetch (robots, 403, timeout) uses its read and is not retried.
    A followed page never triggers a follow.
- **Trace.** `refused_hub_links: list[tuple[str, str, str]]` (hub, link, verdict or `"confirmed"`) on
  `DiscoveryTrace`. `as_dict` writes it only when it is non-empty, so a flag-off trace is byte-identical.
- **Tests**: new `backend/tests/test_follow_refused_hub_link.py`, synthetic hosts `www.example-uni.edu` /
  `study.example-uni.edu`, a fake fetcher, and no development page's words.
  1. Confirm shape (auckland), with the flag off and on:
     - The kept queue holds `/find/field-x.html` (reads unknown). That page links `/find/field-x/undergraduate.html`,
       labelled "Undergraduate study", a programme page at the requested level. It also links
       `/about/school-of-field-x.html`, labelled "School of Field X", which has the higher `score_link` and reads
       unknown.
     - On: the child is read next and confirmed. The school page is never fetched.
     - Off: neither is fetched (assert the fetch calls), and the trace is byte-identical to the flag-less run.
  2. Walker shape (khalifa):
     - The catalogue's first lead `/college-of-field-x` reads unknown and links `/program/bsc-in-field-x`, labelled
       "Bachelor of Science in Field X".
     - The second lead is a programme page of a related subject that `profile_rejects` accepts.
     - On: the linked programme page is confirmed and the second lead is never fetched (`walker_stopped`).
     - Off: unchanged.
  3. Trigger:
     - A refused listing page whose URL and head name no requested field is not a hub, so it causes no fetch.
     - A page refused on subject or on degree level (not a listing) is not a hub.
     - A page reached by a follow is never a hub.
  4. Link filters:
     - none of these is read: a link to another registrable domain, a label naming another level ("Master of
       Field X"), a URL naming another level, an excluded URL, a link whose label and URL name no field;
     - a link already read or queued is never read twice.
  5. Order and cap:
     - a child outranks a higher-scored non-child;
     - four hubs make 3 follows;
     - no follow happens once any programme page is confirmed (by a queued read, the sitemap, a seed or a follow).
  6. A refused follow (robots, 403) costs one ledger read and is not retried. A spent stage budget means no follow.
  7. The budget tests pass unchanged with the flag off and on: `test_case_read_ledger.py`, `test_stage_budgets.py`
     and `test_case_time_budget.py`. The R2b / SP-1 tests also pass unchanged with the flag on.
  8. `seed_demo.py` output is byte-identical.
- **Dispatch** (`benchmark-capture.yml`, `expert_paired`, `columns=4`, `extra_args=--follow-refused-hub-link`):
  - `search_provider=none`, four sets: normal `frh-<set>` and knockout `frh-ko-<set>`;
  - the recorded guard on all four sets, `search_provider=recorded` (`rp-frh-<set>`). On aw2 the simulation fires
    the rule on dev2, dev3 and dev4, including the hit captures of khalifa, tcd, auckland, puc, rwth and unibo (28
    follows). It fires on no cohort case.
- **Pre-registered expectation.**
  - **dev2**: khalifa related → **hit** in 4/4 columns. In the walker, lead 1 → the gold; `zmu` is no longer read.
    Every other case is unchanged.
  - **dev3**: auckland missed → **hit** in 4/4: confirm read 1 → `…/computer-science/undergraduate.html`. Every
    other case is unchanged; imperial and ucph keep their hits.
  - **cohort, dev4, and every other case**: no outcome change. Follows outside the two gains are refused reads,
    at most 3 per case: tcd (dev2); taltech, vut, unibo and rwth (dev4). None run on cohort.
  - **Knockout**: no outcome change. khalifa stays related and auckland stays missed (their followed gold is
    refused by the arm). `wrong_programme_pages` is unchanged.
  - **Recorded guard**: identical outcomes. uct stays related (it may now also return `ba-informatics`, labelled
    related). `recorded_search_misses` equal to the off arm.
  - Expected no-search total: **+2** (one on dev2, one on dev3), 0 wrong.
- **Bar.**
  - No-search: no hit lost; 0 wrong pages; knockout `wrong_programme_pages` not up.
  - A stable gain on **both** dev2 (khalifa) and dev3 (auckland), in ≥ 3 of 4 columns each.
  - Recorded guard: identical or better, with `recorded_search_misses` equal.
  - Then default-on. Otherwise record it in `hypotheses.json` with the §8.2 / §8.3 rows. If a run shows a page
    confirmed through a follow that is not gold or labelled related, that is a stop: diagnose it before any default
    change.

### 8.6 FRH step 2 replay: why groningen and unibo were lost, and the amended trigger (2026-10-25)

The 12 arms of §8.5 ran (columns off#1, on#1, on#2, off#2). The predicted gains came, with the follow confirming the
gold in both on columns on no-search and recorded:
- dev2 khalifa related → hit;
- dev3 auckland missed → hit.

There were 0 wrong pages and the knockout was identical. The bar still fails, because two hits were lost:
- **cohort no-search** (`frh-cohort`, run 40215236690): groningen was a hit in both off columns and missed in
  both on columns. The stable claim losses were groningen deadline, ielts.overall, programme.exists and tuition.
- **recorded guard dev4** (`rp-frh-dev4`, run 40215253209): unibo was a hit off and missed on.

**Verdict.**
- **groningen is caused by the follow.** Three follows from two non-hubs spent 9.9 s. The walker hit its 55 s
  stage deadline one read before the gold lead.
  - Both hubs passed the trigger only because their URL contains "science", one word of "computer science".
  - One of the two was then followed a second time, which breaks §8.5's "exactly one link is read per hub".
- **unibo is network noise.** The follow did not cause it:
  - on#2 made no follow at all and lost the same way;
  - on#1's one follow was a 0.9 s read on another host, 20 s before the stall.
- **The change: two narrowings of the trigger, behind the same flag.**
  - (A) A hub's URL names the field as whole consecutive slug words: SR-1's phrase test, the conjunction R3
    already uses.
  - (B) A hub is followed once.

  Replayed with the production functions over every follow in the 12 arms:
  - khalifa and auckland keep their gold follow, unchanged;
  - groningen and unibo make no follow, so groningen's reads are the off arm's;
  - on no-search, follows fall from 27 to 4, and all 4 confirm a gold.

#### 8.6.1 Inputs and method

- **Captures**: this session's scratchpad, development sets only, every case of the 12 arms:
  - `frh-<set>` and `frh-ko-<set>` (no-search);
  - `rp-frh-<set>` (recorded).

  Each capture holds `<case>.json`, `<case>.log` (every `get` with its start time, duration and outcome) and
  `<case>.raw.json`. The last carries the discovery trace: `refused_hub_links`, `confirm_queue`, `pages_read`,
  `walker`, `stage_budget` (`stage_stopped_by`), `host_cost.samples` (one row per read, with stage and seconds)
  and `case_time`.
- **Hub re-reads.** All 20 distinct hub URLs in any arm's `refused_hub_links` were re-read once each, on
  2026-10-25 a few hours after the runs.
  - The reads went through the production `Fetcher` (robots honoured, our user agent, its rate limit), with
    `trust_env_proxy=True` as in §7 and §8.1.
  - All 20 were read. Each was classified with `classify_page` and judged with `is_refused_hub`, at `HEAD`
    before the change and after it.
- **Replay.** The `refused_hub_links` rows of every on capture were walked in capture order:
  - a row is kept when its hub passes the amended `is_refused_hub` and was not followed from already;
  - a dropped row is a read the arm no longer makes.

  The replay used production functions only: `matches_field`, `_field_slug_bonus`, `is_refused_hub` and
  `classify_page`.
- **Can the narrower trigger add a follow?** Only if an unfollowed refused listing page passes it. Every on
  capture was scanned for refused listing reads whose URL passes the phrase test and that started no follow:
  - walker `reads_as_unknown` / `reads_as_program_catalog` outcomes;
  - `pages_read` "reads as unknown" / "program_catalog" verdicts.
- **No search provider was called.** Not opened: any heldout file, capture, log or label,
  `scratchpad/HELDOUT_QUARANTINE_DO_NOT_OPEN`, `scratchpad/DEV5_BLIND`, `DISCOVERY_ANALYSIS_2026-10-17.md`, or any
  scratchpad path outside `runs/frh-*` and `runs/rp-frh-*`.

#### 8.6.2 groningen (cohort, no-search): the follows spend the walker's deadline

Both on columns are read-for-read identical. Both off columns are identical too.

| | off#1 / off#2 | on#1 / on#2 |
|---|---|---|
| `refused_hub_links` | — | 1. `/research/openscience` → `/research/openscience/onderzoekspraktijken-en-ondersteuning`, reads unknown (1.1 s)<br>2. `/society-business/schools-for-science-society` → the same page's `?lang=nl` twin, reads unknown (4.4 s)<br>3. `/research/openscience` **again** (a cached re-read from a second catalogue's walk) → `/research/openscience/open-research-award`, reads irrelevant (4.4 s) |
| follow seconds (`host_cost.samples`) | 0 | 9.9 / 10.0, all in the walker stage |
| walker reads / seconds | 7 / 16.7 | 9 / 24.2 |
| discovery seconds; `stage_stopped_by` | 49.8 / 49.7; none | 57.1 / 57.15; **`walker: deadline`** (SB-1 deadline 55 s) |
| `/bachelors/alphabet` and `/bachelors/in-english` read at | t = 43 s, 44–45 s | t = 49 s, 50 s |
| gold `/bachelors/computing-science` | get #36 at t = 47–48 s, `program_detail`, accepted | **never requested** |
| `confirm_queue` | 5 reads, the same | 5 reads, the same (no follow ran in the confirm stage) |
| outcome; latency | hit; 78 / 77 s | missed; 71 / 71 s |

**Mechanism.**
1. Follows 1 and 2 cost 5.5 s and moved the rest of the walk about 6 s later.
2. After `in-english`, a later catalogue walk re-reads its leads from cache: `by-subject`, `/research/openscience`,
   `schools-for-science-society`, `alphabet`, then the gold. The off arm reads them at get #32–#36 and the gold at
   t ≈ 48 s. On the on arm, the cached re-read of `/research/openscience` is refused again, and the adapter follows
   it a second time, at t = 53 → 58 s.
   - `_hub_lead` skips a hub only when a follow *reached* it (`hub in self._hub_followed`), not when a follow
     already *started* from it.
3. The walker's `stop()` sees the spent deadline before the next lead. The gold, three leads later, is never
   requested.
4. No programme page means no programme, deadline, IELTS or tuition claims: the four stable claim losses.

The on arm's lower latency is a result of the miss: there was nothing to verify.

**Neither hub names the field.** `matches_field` counts 8 for every requested-field *word* longer than three
letters that appears anywhere in the path. "science" in `openscience` and in `schools-for-science-society` is half
of "computer science". The pages' heads name nothing: `classify_page` gives `subject = None` on both re-reads.
Follow 2 also shows that a hub whose URL names the field passes the link filter with its own language twin, since
the twin's URL is the hub's URL. That is noted in §8.6.5.

#### 8.6.3 unibo (dev4, recorded): a stalled host in the on window, not the follow

| column (start, UTC) | follow | slow reads on `www.unibo.it` | `corsi.unibo.it/` | gold `corsi.unibo.it/laurea/informatica` | discovery | outcome |
|---|---|---|---|---|---|---|
| off#1 (17:11:59) | none | none (robots 2.1 s) | 5.7 s ok | 0.9 s ok | 36.5 s | hit |
| on#1 (17:12:41) | 1: `/it/ricerca/open-science` → its working-group page, 0.9 s at t = 20 s, reads unknown | `/it/ho-un-diploma` **20.0 s** (off#1: 1.4 s) | **23.1 s timeout** | **0.0 s timeout** (the host already stalled once) | 65.5 s; `walker: search_due`, `search: deadline` | missed |
| on#2 (17:13:50) | **none**: navigation and walker skipped, so no hub was read | robots **20.2 s**, `sitemap.xml.gz` **19.6 s** | **22.6 s timeout** | **0.0 s timeout** | 64.3 s; `search: deadline` | missed |
| off#2 (17:15:17) | none | robots 11.1 s (unreadable, so disallowed) | 1.8 s | 0.8 s ok | 19.5 s | hit |

Why this is network and not the follow:
- The ABBA order put both on columns back-to-back, from 17:12:41 to 17:15:15. Both saw `corsi.unibo.it` time out
  on its root after 22–23 s, and the fetcher's stalled-host rule then failed the gold on that host at once.
- The off columns ran just before and just after that window.
- on#2 lost the gold with **no follow**. on#1's single 0.9 s follow read another host (`www.unibo.it`) 20 s before
  the stall.
- Under the amended trigger, `/it/ricerca/open-science` is not a hub either ("science" alone).

The miss itself is not attributable to FRH.

#### 8.6.4 The amended rule, and the offline check

**(A) The URL half of the hub test.** The URL must name the field as whole consecutive slug words:
`matches_field(url, fields) > 0 and _field_slug_bonus(path, fields) > 0`.
- This is SR-1's phrase test of the field or one of its strong or localized aliases, applied whatever SR-1's flag.
  R3's `evidence_only_score` uses the same conjunction for the same reason.
- The head half (`matches_field_text(page.subject)`) is unchanged.
- This narrows §8.5's trigger: every new hub was an old hub.

**(B) One follow per hub.** `LiveDiscoveryAdapter._hubs_followed_from` is reset per institution. A hub read
again, from a second catalogue or by both stages, is not followed again.
- This is §8.5's own "exactly one link is read per hub".
- The step-2 build enforced it only within one read of the hub.

Nothing else changes:
- `refused_hub_lead`, the cap, the stop conditions and the budget;
- the flag (`FOLLOW_REFUSED_HUB_LINK`, still default off), so flag-off is byte-identical.

**The 20 hubs**, re-read and judged with the production trigger:

| hub (case) | `matches_field` | `_field_slug_bonus` | hub before → after |
|---|---:|---:|---|
| ku `/college-of-computing-and-mathematical-sciences` (khalifa) | 16 | 16 | yes → **yes** |
| auckland `…/find-a-study-option/computer-science.html` (auckland) | 16 | 16 | yes → **yes** |
| auckland `…/computer-science/postgraduate.html`, `…/research-ai-software-computing.html` (auckland, ko only) | 16, 8 | 16, 16 | yes → yes |
| rwth `informatik…/~mxz/informatik` (rwth, ko only) | 8 | 16 | yes → yes |
| rug `/research/openscience`, `/society-business/schools-for-science-society` (**groningen**) | 8 | 0 | yes → **no** |
| unibo `/it/ricerca/open-science` (**unibo**) | 8 | 0 | yes → **no** |
| vut `/en/rad/openscience`; psaclay `/en/research/open-science`; tudelft `/en/tu-delft-science-centre` | 8 | 0 | yes → no |
| tcd ×2 short-course pages ("…-science-…"); taltech `…/computer-systems/studies/thesis-topics`, `…/software-science/cooperation` | 8 | 0 | yes → no |
| ntu ×2 bachelor-of-(social-)science(s) pages; imperial `earth-science/…`, `…/neuroscience-…`; puc `bachillerato-…-ciencias-sociales` | 8 | 0 | yes → no |

Every hub page's classified head is `None`, so the head half fires for none of them.

**Replay of every follow in the 12 arms** (old → new follows per on capture; both on columns agree everywhere):

| arm | case | old | new | what the new rule reads | predicted outcome |
|---|---|---:|---:|---|---|
| no-search | **groningen** | 3 + 3 | **0 + 0** | nothing: the walk reads what off reads; the gold at t ≈ 48 s, before the 55 s deadline | **hit (restored)** |
| no-search | **khalifa** | 1 + 1 | 1 + 1 | the gold (`confirmed`) | **related → hit (kept)** |
| no-search | **auckland** | 1 + 1 | 1 + 1 | the gold (`confirmed`) | **missed → hit (kept)** |
| no-search | tcd, psaclay (dev2); taltech, vut, unibo (dev4) | 2+2, 1+1; 2+2, 3+3, 1 | 0 | nothing | unchanged (were refused reads) |
| knockout | khalifa / auckland | 1+1 / 3+3 | 1+1 / 3+3 | the same reads; the gold is refused by the arm | unchanged |
| knockout | rwth | 2 | **1** | the first footer page only; the second follow from the same hub is gone (B) | unchanged |
| knockout | groningen, delft, ntu, tcd, psaclay, imperial, puc, taltech, unibo, vut | 34 | 0 | nothing | unchanged |
| recorded | khalifa / auckland | 1+1 / 1+1 | 1+1 / 1+1 | the gold | unchanged (hit) |
| recorded | tcd, psaclay, taltech, unibo, vut | 13 | 0 | nothing | unchanged; unibo's on-window stall is not ours (§8.6.3) |

Totals: no-search follows fall 27 → 4 (4 gold), knockout 45 → 9, recorded 17 → 4 (4 gold).

**Could the narrower trigger add a follow?** Not on these captures.
- A case where the old rule made no follow runs identically under the new one, because every new hub was an old
  hub. Examples on recorded are tec, msu, itu and kuleuven: unfollowed phrase-passing listings, no follows before
  or after.
- A follow can appear only where a dropped follow freed the cap, the clock or the skip set, and a refused
  phrase-passing listing then finds the follows open. The cap was reached only on groningen, vut and auckland-ko:
  - groningen and vut now have no hub at all;
  - auckland-ko keeps its three hubs, so `school-of-computer-science.html` stays beyond the cap.
- Among the cases with dropped follows, the scan found one refused listing that passes the phrase test and started
  no follow: taltech's `…/informaatika-bakalaureus`, in all three arms.
  - Its re-read now redirects to `/en/please-search-again`, which names nothing. If it redirected at run time too,
    it is no hub under either rule, which explains why the old rule passed it by with its follows open.
  - If it did not, the worst case is one more refused read on taltech, a missed case. No §8.2 page links a gold
    from it.
- The other unfollowed phrase-passing listings found by the scan are in two groups:
  - auckland's `postgraduate.html`, refused after the gold follow had confirmed, so closed under both rules;
  - delft, uba and imperial on recorded, cases where the old rule made no follow at all.

**Tests** (`tests/test_follow_refused_hub_link.py`, synthetic: the subjects "geology" and "marine biology",
`example-uni.edu`):
- the predicate: one word of a two-word field in the URL (`/research/biology-labs`, `/events/biology-week`,
  `/research/marine-research`) is no hub, and the phrase (`/find/marine-biology.html`,
  `/faculty/school-of-marine-biology/study`) is;
- end to end, a refused listing naming one word of the field causes no fetch of its programme-page link;
- a hub the confirm stage refused and followed, then read again by the walker, is not followed again: one follow,
  the second link never fetched.

All three fail at the step-2 code and pass now. The 30 step-2 tests pass unchanged, including the flag-off
byte-identity and the budget tests with the flag on.

#### 8.6.5 Caveats

- The hub pages were re-read hours after the runs. A head that named the field at run time and does not now would
  keep a hub that the replay drops. None of the 20 has a head today, and none of the dropped hubs' URLs names the
  field.
- (A) narrows what FRH can ever reach. A refused listing whose URL names only one word of the field and whose head
  is empty is no longer followed. On these four sets no such follow ever reached a gold or a labelled related page
  (§8.3 and the table above). A field whose name is one word is unaffected: its word is the whole phrase.
- **Not built:** a hub whose URL *does* name the field passes the link filter with its own language twin (the same
  path with `?lang=…`). The twin's URL is the hub's own, as groningen's follow 2 shows. No kept hub on these
  captures chose its twin, because a child or a field-named label always ranked first. If a run shows one, the
  fix is to skip a link equal to the hub up to its query (`_without_query`).
- Network variance on unibo's hosts stays. A recorded-guard loss on unibo in a re-run should be judged against
  `host_cost.samples` and the `corsi.unibo.it` timeouts before it counts against FRH.

#### 8.6.6 Re-run: dispatch inputs

`benchmark-capture.yml` on the branch carrying this commit. Shared inputs: `mode=expert_paired`, `columns=4`,
`case_parallelism=5`, `extra_args=--follow-refused-hub-link`, `base_args` empty, `seconds_per_case=120`,
`max_pages=60`, `runner=ubuntu-latest`, `search_first=false`, `max_search_queries` empty.

| run_tag | case | search_provider |
|---|---|---|
| `frh2-cohort` | *(blank: the ten cohort cases)* | `none` |
| `frh2-dev4` | `dev4` | `none` |
| `rp-frh2-cohort` | *(blank)* | `recorded` |
| `rp-frh2-dev4` | `dev4` | `recorded` |
| `frh2-dev2` | `dev2` | `none` |
| `frh2-dev3` | `dev3` | `none` |

**Pre-registered expectation:**
- groningen hit in 4/4 columns, with no `refused_hub_links` on any cohort case;
- khalifa related → hit and auckland missed → hit in both on columns;
- on dev4, no follow on any case;
- on recorded cohort and dev4, outcomes identical and `recorded_search_misses` equal.

**The bar** is §8.5's, unchanged. Knockout was identical on step 2, and (A) and (B) only remove knockout reads, so
it is not re-run. Dispatch `frh2-ko-<set>` if the planner wants it anyway.
