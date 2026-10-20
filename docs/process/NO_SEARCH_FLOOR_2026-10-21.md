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
  NS-1 fails its bar.
