# Core answers after the programme page — evidence analysis (2026-10-17)

Author: claude-opus-5 (analysis only; no `app/` change, no commit). Companion to
`DISCOVERY_ANALYSIS_2026-10-17.md` (which asked *where the programme page is lost*); this one asks
*why, once a programme page is found, no core answer comes out on a university without curated seeds*.

Inputs. Code on `claude/greeting-16wj2z` (captures ran at `3bca749`; PG-1 was switched on afterwards in
`2149c1d`). Unpacked artifacts: dev2 control 39066742964 (`scratchpad/dev2ctl/x`), dev2 HP-1/CU-1 runs
(`scratchpad/runs/{hp1,cu1}-dev2/x`), cohort Serper control 39058503662 (`scratchpad/sctl/x`), cohort Exa rl1
(`scratchpad/rl1run/x`). Labels: `backend/evaluation/research/data/dev2.draft1.json` (21 known core
questions) and the dev2 expert drafts `expert/data/core_drafts_dev2.2026-10-17/*.json` (where each answer
lives and how the expert reached it). **Protocol:** no heldout label, draft or scorecard was opened. Eight
public pages were fetched by hand (curl) and run through the *offline* classifier/extractors for mechanism
checks only (`scratchpad/evpages/`); nothing went through the pipeline.

## 0. Summary — why 0 of 21

| # | Root cause (one line) | Known core questions it decides (of 21) | Evidence |
|---|---|---|---|
| 1 | **BL-1 starves every later search.** Discovery always sends all 6 query families (`retrieval.py` L393–431: the loop stops only on a 429). With `SHARED_QUERY_BUDGET` (`intent.py` L40) topic search gets `6 − 6 − 1 < 0` → never runs (`web_requirements.py` L579–586), and the scholarship search is refused the same way (`web_scholarships.py` L215–222). On no-seed sites there is then **no generator at all** for admissions, fee and scholarship pages except URL-shape guesses from sitemaps/menus. | 13: all 12 scholarship questions (6 cases × exists + international) + Uppsala English | every dev2 case: `telemetry.search_calls == 6`, no `costs`/`scholarships` category selected in 7 of 10 traces; NTU (cohort) is the proof of the opposite: 3 programme slots were full before search, so discovery sent 0 queries and the verify stage ran 3 topic queries at t=18–21 s and read `general-admission-requirements` (16 claims) — `sctl/x/ntu-on/*/ntu.log` L26–28 |
| 2 | **The classifier demotes real programme pages to `program_catalog`** because `_CATALOG` is matched against the *concatenation of the title and every heading* (`page_classifier.py` L481–484, L600–607): TCD's "Computer Science – Courses \| TCD" + h2 "Overview" → `courses … overview`; Uppsala's h1 "Bachelor's Programme in Computer Science" + h4 "Admitted or on the waiting **list**" → `programme … list`. The walker read TCD's real page at t=33 s and Uppsala's at t=31 s and rejected both. | 4: TCD English (3 keys), TCD cost, UCT English (hub rejected as `unknown`), Uppsala deadline | offline run on the hand-fetched pages reproduces both verdicts and signals verbatim (§1.2); traces: `uppsala` rejected "reads as program_catalog"; `tcd` walker `programs_confirmed: 0` |
| 3 | **Leads are followed only from pages the classifier accepts.** `verify()` `continue`s out of every rejected-page branch (`web_requirements.py` L397–475) *before* the `_language_links`/`_route_links` block (L497–545). TCD's course page carries the exact English-requirements link the expert used; UCT's admissions hub carries the exact `language-requirements`, `key-dates` and `eligibility-admission` links. Neither was ever followed. Leads also cover only English and deadlines — never fees or scholarships — and `web_costs`/`web_scholarships` take no lead at all (`web_costs.py` L50–52; `web_scholarships.py` L266–280). | overlaps #2 (TCD, UCT); would also have reached Khalifa's `/undergraduate-admissions` (GPA + tuition table) from its `/admissions` hub | offline `_language_links`/`_route_links` on the fetched pages (§1.2) |
| 4 | **URL categorisation files undergraduate service pages as programme leads and keeps postgraduate ones as admissions.** `/(bachelors?\|masters?\|undergraduate)/<slug>` scores 5 for PROGRAM_PAGE (`live_discovery.py` L327) and beats `/fees` (4) and `/how-to-apply` (5 → tie broken by +4 degree bonus): TCD `/courses/undergraduate/fees` → `program_page 9` → rejected "names none of the applicant's subjects"; `/courses/postgraduate/how-to-apply` → `admissions 5` → **selected** as the bachelor applicant's admissions page. No degree-level guard exists for ADMISSIONS/COSTS/SCHOLARSHIPS (`keep()` L1587–1593, navigation L2510–2535 guard only programme categories). | 1 (TCD cost) + the wrong admissions page on TCD in 12/12 repetitions | `categorise_url` offline (§2.3); trace `selected.admissions` = three `/postgraduate/` URLs |
| 5 | **Institution identity is one registrable domain.** Tsinghua publishes every core answer on `international.join-tsinghua.edu.cn`; `same_institution`/`registrable_domain` reject it (walker outcome `off_domain` for `join-tsinghua.edu.cn`), so neither discovery nor topic search could ever return it. | 3 (Tsinghua deadline, scholarship ×2) | `dev2ctl/x/tsinghua-on/*/tsinghua.raw.json` walker outcomes; `_find_topic_pages` L612 `same_institution` |
| 6 | **Measurement ceiling: scholarship labels cannot be credited.** 14 of the 21 known core labels are `scholarships.<award>.*`; the live capture maps claims with `identity_bindings.reviewed.json` only (`live.py` L258, L358; `benchmark-capture.yml` L223). `identity_bindings.dev2-draft1.json` holds the 8 dev2 awards but nothing loads it, so a correct claim lands on `unmapped.scholarship_exists`, which `core_known` cannot match by key (`metrics.py` L320–327). | 12 of 21 can never score until the bindings are wired | §5 |

Not a cause: the host-stall circuit breaker (§3). It fired on one case (TCD), on DNS, deterministically in
12/12 repetitions, and the page it "protected" was a wrong lead anyway.

## 1. Cases × questions — the earliest stage each known answer is lost

Stage codes: **P0** programme page never found · **P1** programme page selected but never read · **P2**
page (programme or hub) read but classifier rejected · **P3** page read and accepted, extractor found nothing ·
**S0** admissions/cost/scholarship page never located (no seed; topic/award search had no query budget) ·
**S1** wrong page located (wrong degree level / category competition) · **D** official answer lives on a host
outside the registrable domain · **A** access (robots.txt unreachable, DNS) · **M** measurement (labels or
bindings). Dev2 control run, arm `on`, first repetition; identical in the other 3 repetitions unless noted.

| case | known core | english | gpa | deadline | cost | scholarship exists | scholarship international | what the run actually did |
|---|---|---|---|---|---|---|---|---|
| ethz | 2 | n/a (German) | n/a | unk | unk | **S0** → M | **S0** → M | programme page found and read (`program_detail`, 1 claim). No admissions/costs/scholarships URL selected. Funding stage read the programme page "as a funding index; 0 award links". `_search_awards` refused: 6/6 queries spent. Expert's answers: `ethz.ch/students/en/studies/financial/…` (never fetched). The EN programme page has 0 admission/fee links (offline check) |
| uppsala | 4 | **S0** | n/a | **P2** then P3 | unk | **S0** → M | **S0** → M | real programme page `…/programme/bachelors-programme-computer-science` fetched at t=31 s (log #11) and rejected "reads as program_catalog" (§1.2); kept page = syllabus `outline?query=166` (1 claim: exists). Deadline and SEK 450,000 fee are on the rejected page; offline, the extractor also drops the deadline because the page states two *study-period* date ranges (the several-windows guard, `extraction.py` L985–997) and takes the 2026 accordion first. English page `…/bachelors-studies/application/entry-requirements` never fetched: no admissions URL, no topic search |
| tcd | 4 | **P2** (hub) | n/a | unk | **S1** + P2 (hub) | **S0** → M | **S0** → M | walker read the real course page at t=33 s (log #20, 2.9 s ok) → `program_catalog` (`courses … overview`) → not confirmed. Kept "programme pages" = unread `scss.tcd.ie` search leads (DNS 10 s each, L1029) promoted by `_recover_search_pages` (L2370–2372; PG-1 now stops this). Verify: both leads → breaker (0.0 s); admissions page = `/courses/postgraduate/how-to-apply` → `program_catalog`, rejected. The course page links `Fees → /courses/undergraduate/fees/` (expert's tuition row) and the English page `/study/english-language-requirements/` (a `_language_links` hit) — never followed |
| tsinghua | 3 | unk | n/a | **D** | unk | **D** → M | **D** → M | programme page not found; `www.tsinghua.edu.cn/en/Admissions.htm` read, "no requirement pattern matched". Every expert URL is on `international.join-tsinghua.edu.cn` = different registrable domain → `off_domain` |
| tec | 3 | **P0** | n/a | unk | unk | **S0** → M | **S0** → M | kept programme pages = `research.tec.mx/vivo-tec/…` (VIVO research records; `programme.exists` ×2 claimed from them). Real page `tec.mx/es/ingenieria-y-ciencias/ingenieria-en-tecnologias-computacionales` (TOEFL 72 is there) never fetched. `tec.mx/es/profesional` was fetched by navigation but classifies `unknown` (Spanish, JS-heavy); costs page read, 0 figures (Imperva/JS) |
| uba | 2 | n/a (Spanish) | unk | unk | unk | **S0** → M | **S0** → M | kept programme pages redirect off-site (Moodle → YouTube, personal page → LinkedIn) → `blocked`. Real page `ingresantes.exactas.uba.ar/…` never fetched. Answers live on `cbc.uba.ar` (Vue SPA) and `extension.uba.ar/noticias/…` |
| kaznu | 2 | n/a | n/a | unk | unk | **S0** → M | **S0** → M | kept programme page `pps.kaznu.kz/…/FileShow/…` → "more than 5 redirects". `www.kaznu.kz` robots.txt unreachable (A). `welcome.kaznu.kz` bachelor pages were read (log #14–17) but the subject is "Bachelor — Admissions 2026"; expert's answers are Russian pages/PDFs under `welcome.kaznu.kz/ru/admissions/…`, never fetched |
| uct | 1 | **P2** (hub) | n/a | unk | unk | n/a | n/a | three `sit.uct.ac.za` pages kept (Business Science / Commerce / department) → 3 `exists` claims. Admissions URL `uct.ac.za/students/applications/international-applicants` read 3× → `unknown` → rejected, so its `Language requirements` link (the expert's IELTS page) and `key-dates`/`eligibility-admission` route links were never followed (offline: `_language_links` and `_route_links` both find them) |
| psaclay | 0 | — | — | — | — | — | — | admissions URL `/en/admission/international-students` classifies `costs` → rejected; `/en/admission/tuition-fees` read, "no cost figures" (offline: €178/€254/€397 sit in table cells, structured reader yields nothing); scholarships URLs are doctoral funding pages. 1 of 4 repetitions ended `BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED` at 58–60 reads |
| khalifa | 0 (6 expert answers demoted to `unknown`, §5) | — | — | — | — | — | — | control: `www.ku.ac.ae` robots.txt ReadTimeout → RFC 9309 full disallow → 6 fetch-failed (A, host-time dependent: HP-1/CU-1 runs 30–60 min later reached it). When reached: admissions URL `/apply` → `unknown`; the `/admissions` hub (2nd of 3 selected, never used because `_apply` keeps `_first`, L2393) links `Undergraduate Admissions → /undergraduate-admissions` = the expert's GPA + tuition page, which `categorise_url` cannot file (no leading `/admission`) |

Totals by earliest stage: **S0 13** · **P2 4** · **D 3** · **P0 1** (= 21). Twelve of the 13 S0 losses are the
scholarship pair, and all 12 are additionally **M**-blocked.

### 1.1 Dev2 vs cohort: why the cohort gets 7–9 of 27

Every cohort answer in `serper-control.scorecard.md` comes through a curated seed or from a page one RL-1 hop
below one: Delft — seed admissions hub accepted (`no-pattern-match` is still *accepted*) → route lead
`bsc-international-diploma/admission-requirements` → 4 IELTS claims; seed costs page → tuition. Groningen —
seed costs/programme pages. UBC — seeds. NTU — the only case where BL-1 left budget (q=3), and its three
topic pages produced 16 claims. Cohort discovery also spends 6 queries on 8 of 10 cases (`q=6` in `sctl`), so
ER-08 is effectively dead there too; the cohort simply does not need it because the seeds are the topic pages.

### 1.2 Mechanism checks on the hand-fetched pages (offline classifier/extractors, same code as production)

| page | `classify_page` | signal | `_language_links` / `_route_links` found | note |
|---|---|---|---|---|
| TCD `/courses/undergraduate/courses/computer-science/` | `program_catalog` | `5 programme links; plural catalogue heading` — `_CATALOG` matched `courses \| trinity college dublin computer science overview` across title + h2 | `/study/english-language-requirements/` (expert's IELTS page) | identity = "Computer Science"; `_program_name` → None (no degree word) |
| Uppsala `/en/study/programme/bachelors-programme-computer-science` | `program_catalog` | `0 programme links; plural catalogue heading` — `_CATALOG` matched `programme … waiting list` across h1 + h4 | — ; page links `Read more about fees → /en/study/fees` | identity = "Bachelor's Programme in Computer Science"; `_program_name` → the programme. Extractor on the full text: only `intake_term fall 2026`; on the deadline sentence alone: `2026-04-15`; on `"Total tuition fee: SEK 450,000"` alone: tuition SEK 450,000 — the page is lost first to the classifier, then to the several-windows guard |
| UCT `/students/applications/international-applicants` | `unknown` | `no decisive signals` | language: `…/language-requirements` (expert's page); route: `key-dates`, `eligibility-admission` | the run read this page three times and followed nothing |
| ETH programme page | `program_detail` | single programme at bachelor level | none; 0 admission/fee links in the HTML ("For detailed information go to the pages in German") | ETH is a pure S0 case: only a query can reach `ethz.ch/students/en/studies/financial/…` |
| Khalifa `/admissions` | `general_admissions` | admissions phrasing | — ; links `Undergraduate Admissions → /undergraduate-admissions`, `Fee & Payment` | second selected admissions URL, never read (`_first`) |
| Paris-Saclay `/en/admission/tuition-fees` | `costs` | cost vocabulary | — | €178 / €254 / €397 are bare table cells; `extract_costs` and the structured reader return nothing |
| Tec `/es/profesional` | `unknown` | — | — | Spanish deadline table ("Fechas de admisión continua … 5 de noviembre 2026") — no Spanish patterns |

## 2. How production finds admissions, costs and scholarship pages with no seeds

Path for a seed-less university (`CatalogueDiscoveryAdapter._identify_site` → `_discover_one`, entry with
`seeds == {}`; `trace.manual_seeds == {}` in every dev2 trace):

1. `_discover_one` (`live_discovery.py` L1544–1677): `selected` has six categories; without seeds only
   **sitemaps** (`keep()` L1581–1600, URL shape via `categorise_url` L582–609), the **navigation fallback**
   (L2454–2570, only when no programme page yet) and the **walker** (programme pages only) can fill
   ADMISSIONS/COSTS/SCHOLARSHIPS. Search (`_add_search_results` L1913–2058) adds **programme pages only**.
2. `_apply` (L2384–2395): `candidate.admissions_url = _first(selected[ADMISSIONS])`, same for costs and
   scholarships — one URL each, no degree-level check, no page ever read before selection.
3. Verify (`runner.py` L508–693 → `web_requirements.verify` L240–549): targets = programme page +
   `candidate.admissions_url` (L246–252) + topic pages **only if** `remaining = 6 − search_queries_used − 1 > 0`
   (L579–586). Route/language leads (L497–545) only from accepted pages, only for deadline and English.
4. Costs (`web_costs.fetch` L47–66): `if not candidate.costs_url: "No official cost page is known"` — no
   search, no lead, no programme-page fallback (only `extract_costs` on an accepted programme/fee page in
   verify, L478–487).
5. Funding (`runner.py` L695–760 → `web_scholarships.find` L261–300): `primary = scholarships_url or
   program.url`; the programme page is "read as a funding index" (0 award links on every dev2 page);
   `_search_awards` (L188–259) refused when `search_queries_used >= 6` (L215–222).

Every place a seed is assumed (explicitly or by having no other generator):

| where | assumption |
|---|---|
| `live_discovery.py` L1560–1575, L2393–2395 | a human-verified URL per category exists; one URL per category is enough (`_first`) |
| `live_discovery.py` L735–778 `is_seed_host` → `retrieval.py` L248 | search ranking trusts hosts the registry seeds name |
| `live_discovery.py` L1587–1593, L2510–2535 | degree level is checked only for programme categories; a seed is assumed to be the right level |
| `web_requirements.py` L246–252 | the admissions hub is `candidate.admissions_url` (one page) |
| `web_requirements.py` L579–586 + `intent.py` L40–42 | topic search is a *supplement* to seeds; on seed-less sites it never runs |
| `web_costs.py` L50–52 | a cost page is known or costs are unknown |
| `web_scholarships.py` L266–280, L215–222 | a scholarship page is known or the programme page is the index; the award query is budget-gated |
| `runner.py` L1140 `registry_campuses` | campus withholding is registry data (no-seed sites: none) |
| `base.py` L47–50 `Candidate.verifiable` | "an official page is known" means admissions_url/costs_url/programme url |

## 3. The host-stall circuit breaker

Where: `fetching.py`. `Fetcher._stalled_hosts` (L526–529) is checked at the top of `get()` (L1019–1024,
error "host stopped responding earlier in this run; not waited on again") and before each redirect hop
(L696–702). A hostname is added on (a) **DNS** resolution exceeding `DNS_DEADLINE_SECONDS = 10` (L70, L77–79,
L1026–1035 — error "name resolution took longer than 10s"), (b) a whole exchange exceeding the network
deadline (L1047–1058 "no complete response within the deadline"). Robots stalls are a parallel breaker:
`RobotsPolicy.stalled`/`_unreachable` (L319–345) make the whole origin *disallowed* (RFC 9309), also checked
at L1019. Scope: exact hostname, for the Fetcher's life (one canary run = discovery + verify + funding).
One timeout trips it; `MAX_ATTEMPTS = 3` (L62) never applies to a timeout.

How often it fired:

| run | cases with breaker hits | hits (all reps) | what tripped it | cost |
|---|---|---|---|---|
| dev2 control | tcd only | 6 (verify + funding) | DNS: `scss.tcd.ie` at t=48 s, `teaching.scss.tcd.ie` t=70 s, `www.scss.tcd.ie` t=81 s — three hostnames, 10 s each, in **discovery** (walker confirm + search recovery) | 30 s of TCD's clock; verify began at t≈92–94 s |
| dev2 HP-1 / CU-1 | tcd only | 10 / 8 | same | same |
| cohort Serper / Exa | none | 0 | — | robots unreachable instead: aalto, groningen, hku, kaist/ubc, warsaw (76–77 disallowed requests per run) |

Does one slow read during discovery poison verify for the programme host? Yes by design, and in TCD that is
exactly what happened (`page_outcomes`: 4 × "fetch-failed … not waited on again"). But: (i) the trip was DNS,
not a slow page, and `scss.tcd.ie` never resolved in 12/12 repetitions, so a retry with a longer timeout
would have cost another 10 s each and found nothing; (ii) the pages behind it were unread search leads
promoted by `_recover_search_pages` L2370–2372 — PG-1 (`2149c1d`, on since these captures) now keeps them
as `unresolved`; (iii) the page that *should* have been the programme page is on `www.tcd.ie`, read fine at
t=33 s. **Candidate (c) is rejected as a core-answer lever.** The one defensible tweak is cost-only: remember
a DNS failure per *parent zone* so `www.scss`/`teaching.scss` do not each pay 10 s after `scss` failed
(−20 s on TCD, no label can change).

## 4. Rules, ranked (one flag, one paired run each; cohort must show no stable loss)

| rank | rule / flag | cause (§0) | mechanism | precision guard | files | offline test | expected to move (dev2 known core) |
|---|---|---|---|---|---|---|---|
| 1 | **QB-1 `DISCOVERY_QUERY_RESERVE = 3`** (candidates a + d) | #1 | `_add_search_results` calls `discover_candidates(query_budget=3)`; identity recovery runs; only if **no** programme page is confirmed does a second call send the remaining families (3). A confirmed page therefore leaves ≥3 queries: topic search gets `3 − 1 = 2` (English, fees) and `_search_awards` gets 1. Record `discovery_query_passes` in the trace | none new: topic results already must be same-institution, non-excluded, right degree level (L606–616), and every page is classified and extracted under the existing verbatim/domain rules | `live_discovery.py` L1990–2000, `retrieval.py` L393–394, `intent.py` | fake provider counting calls: a confirmed first pass sends 3; an empty first pass sends 6; `verify` then runs 2 topic queries with `search_queries_used == 3` | **tcd English, tcd cost, uppsala English, uct English** (4); plus `_search_awards` on ethz/uppsala/tcd/tec (scholarship pair, needs #6 to score). Cohort risk: a page found only by families 4–6 — not measurable from traces (families not persisted); the paired run decides |
| 2 | **HL-1 `HUB_LEADS`** (candidate b) | #3 | In `verify`, run the lead scan (`_language_links`, `_route_links`) on **every** official HTML page read, including ones the classifier rejected as `program_catalog`/`unknown`/`costs`; add two lead kinds — *fees/tuition* (→ queued with `topic="fees"` so `extract_costs` runs, and `candidate.costs_url` set when None) and *scholarships/financial aid* (→ `candidate.scholarships_url` when None). Also take the first `selected[ADMISSIONS]` whose URL/text names the requested level, not `_first` | existing `_GRADUATE_LEAD` text guard + `names_other_degree_level(url)`; `_MAX_ROUTE_FOLLOWS = 4` shared; a lead is followed only while the matching core claim is missing; followed pages are classified and extracted as today, so a hub's rejection still stands for *its own* text | `web_requirements.py` L397–475 (move the lead scan before the `continue`s), L171–227 (lead patterns), `live_discovery.py` L2393 | fixtures: a hub classified `unknown` with "Language requirements" and "Fees" links → both followed, IELTS read from the language page, no claim from the hub; a hub with "Postgraduate fees" → not followed | **tcd English + cost, uct English** (3; overlaps rank 1 — the two together cover the case where the provider does not return the page); khalifa GPA/tuition (no label yet) |
| 3 | **CL-1 `CATALOG_HEADING_SCOPE`** | #2 | `_CATALOG` is tested against the identity heading and the title **separately**, never against the joined `low_head`; `_PLURAL_PROGRAM_HEADING` and the ≥5-links/no-identity rule stay | a page whose own title or H1 is catalogue-shaped ("A-Z of UG courses", "Browse programmes") still classifies as a catalogue; the subject/level confirm predicate (`profile_rejects`) is unchanged | `page_classifier.py` L600–607 | fixtures from the two fetched pages: TCD → `program_detail`, subject "Computer Science"; Uppsala → `program_detail`; `/courses/undergraduate/a-z-of-ug-courses` → still `program_catalog` | **tcd English** (walker confirms the real page at t=33 s, before the DNS stalls; verify then follows its language link); uppsala deadline needs rank 6 too. Watch: Uppsala's "First tuition fee instalment: SEK 75,000" would be read as tuition (offline check) — a wrong-value risk the paired run must show |
| 4 | **UC-1 `SERVICE_PAGE_PRIORITY`** | #4 | In `categorise_url`: when a URL matches a service category by its **last** segment (`fees`, `how-to-apply`, `entry-requirements`, `scholarships`…) and PROGRAM_PAGE only through the `/(bachelors?\|masters?\|undergraduate)/<slug>` rule, file it under the service category and add the degree bonus; apply `names_other_degree_level` to ADMISSIONS/COSTS/SCHOLARSHIPS in `keep()` and navigation | discovery only picks entry pages; `web_costs`/`verify` still classify them | `live_discovery.py` L325–333, L582–609, L1587–1593, L2510–2535 | unit: `/courses/undergraduate/fees` → costs; `/courses/postgraduate/how-to-apply` rejected for a bachelor request; `/courses/undergraduate/how-to-apply` → admissions | **tcd cost** (expert found the 2027/28 row in that fee table) and TCD's admissions page becomes the undergraduate one; ethz `…/application/…/dates.html` (deadline label unknown) |
| 5 | **DI-1 `ADMISSIONS_HOST_FROM_HOMEPAGE`** | #5 | During the navigation fallback, a link from the homepage's main navigation whose text is admissions/apply-shaped and whose host is a different registrable domain is recorded as `candidate.extra_domains` (max 1); `same_institution`, `is_official_domain` and `verification_domains` accept it for this candidate | only from the official homepage, only admissions/apply text, a social/third-party blocklist, never a shortener; pages on it are classified as usual | `live_discovery.py` L485–510, L2454–2500; `extraction.py` L128–136 | fixture homepage linking "Admissions → international.join-example.edu.cn" → topic result on that host accepted; a "Facebook" link not | **tsinghua deadline + scholarship pair** (3, pair needs #6) — static HTML, English pages (`Admission1/Schedule.htm`, `Fees.htm`, `Freshmen_Scholarships1.htm`) |
| 6 | **EX-2 `DEADLINE_WINDOW_SCOPE`** | #2 (Uppsala), extractor | The several-windows guard (`extraction.py` L985–997) counts only date ranges within one sentence of application/deadline words (not "Study period 31 August 2026–3 June 2029"); when a page has two intake sections, the deadline is read from the section whose intake matches the requested year (as TY-1 does for fee rows) | still "no claim" when two *application* windows differ; year selection only narrows | `extraction.py` L955–997 | fixture with two study-period ranges + two "Application deadline" accordions → `2027-04-15` for fall 2027 | **uppsala deadline** (with rank 3). Without rank 3 the page never reaches the extractor |

Rejected or folded: **(c) breaker scoping** — rejected, §3. **(d) topic search without seeds** — it already
has no seed dependency; its only blocker is the budget, so it is rank 1. **Bindings for dev2 awards** (§5)
is a measurement change, not a rule, but it is a prerequisite for 12 of the 21 labels to ever score.

The single change expected to move the most dev2 answers: **QB-1**, because it restores the only generator
that can reach a university-level admissions, fee or scholarship page on a site nobody has curated, and the
NTU cohort trace shows that generator producing 16 claims from 3 queries when it is allowed to run.

## 5. What is misleading in the measurement

1. **`programme_page_recall` denominator = 1 on dev2.** `core_drafts.programme_item` (L840–860) marks the
   expert's programme URL `known` only when the *title quote* verified; `evidence_check.39065042793.json`
   has `quote_found: false` for 9 of 10 programme items (titles are expert paraphrases, e.g. "Computer
   Science — B.A. (Moderatorship) …"), so `build_heldout` (L1078–1081) drops them and only UBA keeps one.
   Use "known core answered"; or verify the programme item by URL reachability + H1 words.
2. **Scholarship questions cannot score on dev2** — 14 of the 21 known core labels (12 questions) are
   `scholarships.<award>.*`. `live.py` L258/L358 and `benchmark-capture.yml` L223 load only
   `identity_bindings.reviewed.json` (8 bindings, none for dev2 hosts); `identity_bindings.dev2-draft1.json`
   (8 dev2 awards) is referenced by nothing. Until the capture takes `--bindings` per split, the dev2
   ceiling is **7/21**, and a run that *does* find the ETH or Uppsala award would still show 0.
3. **Khalifa's denominator is 0 by accident.** The verify script's fetch hit `www.ku.ac.ae` while its
   robots.txt timed out (RFC 9309 disallow), so all six expert answers — including the only GPA and one of
   two tuition answers in dev2 — were demoted to `unknown`. HP-1/CU-1 runs reached the host 30–60 min later.
   Re-run the evidence check for Khalifa before signing.
4. **`programme_urls` / `program_page_found` overstated.** TCD reports two programme pages it never read
   (pending leads promoted, L2370–2372). PG-1 is on since `2149c1d` (after these captures), so the next dev2
   control will show TCD `prog=0`; do not read that as a regression.
5. **Budget starvation is invisible in the artifacts.** "Topic search not run: discovery used the 6-query
   budget" and "Official scholarship search not run" go to `run.errors` via `_record_diagnostics`, which the
   canary report does not export; `<case>.json` only shows `search_calls == 6`. Export `run.errors` into
   `.raw.json` so the scorecard can count S0 directly.
6. **Host-time variance.** Khalifa control (robots stall, 0 reads) vs HP-1 (reached, 5 claims) differ by
   time of day, not by flag; the paired off/on/on/off order is what protects against this — keep it.
7. **Cohort 7–9/27 is seeds + RL-1, not ER-08.** `q=6` on 8 of 10 cohort cases means topic search never ran
   there either; the one exception (NTU, `q=3`) is also the cohort's best no-seed-like performer.

## 6. Evidence index

- Runs: `scratchpad/dev2ctl/x/<case>-{on,off}/<ts>/<case>.{json,log,raw.json}` (control 39066742964);
  `scratchpad/runs/{hp1,cu1}-dev2/x`; `scratchpad/sctl/x`; `scratchpad/rl1run/x`.
- TCD timeline (`dev2ctl/x/tcd-on/20261017T203432Z/tcd.log`): #20 t=33 s real course page 2.9 s ok; #26 t=48 s
  `scss.tcd.ie` 10.0 s timeout; search #1–6 t=65–70 s; #44 t=70 s `teaching.scss` 10.0 s; #46 t=81 s
  `www.scss` 10.0 s; #49 t=92 s `scss` 0.0 s (breaker); #54 t=94 s `/courses/postgraduate/how-to-apply` 2.5 s ok.
  `tcd.raw.json` failures: "timeout: name resolution took longer than 10s" ×3.
- Code: `app/adapters/fetching.py` L62, L70, L77–79, L319–345, L488–496, L526–529, L696–702, L1019–1058;
  `app/adapters/discovery/live_discovery.py` L325–333, L352–357, L582–609, L735–778, L1544–1677, L1913–2058,
  L2233–2382, L2384–2395, L2454–2570; `app/adapters/search/retrieval.py` L393–431; `app/adapters/search/intent.py`
  L33–42; `app/adapters/requirements/web_requirements.py` L120–130, L171–227, L240–260, L397–475, L497–545,
  L551–625; `app/adapters/cost/web_costs.py` L47–66; `app/adapters/scholarship/web_scholarships.py` L188–300;
  `app/pipeline/runner.py` L508–693, L695–760, L1661–1668; `app/adapters/page_classifier.py` L178–190,
  L481–484, L600–632; `app/adapters/extraction.py` L128–136, L955–997; `app/adapters/base.py` L28–50.
- Measurement: `evaluation/research/live.py` L258, L358, L570–574, L639–643, L669; `evaluation/research/scorecard.py`
  L46–69, L200–215; `evaluation/research/metrics.py` L303–327; `evaluation/research/expert/core_drafts.py`
  L840–860, L1078–1081; `.github/workflows/benchmark-capture.yml` L223; `scripts/canary_discovery.py` L548–549;
  `evaluation/research/runs/2026-10-17/{hp1-dev2,serper-control}.scorecard.md`, `LOOP_REPORT.md`.
- Hand-fetched pages for the offline checks: `scratchpad/evpages/*.html` (TCD course page, Uppsala programme
  page, UCT international applicants, ETH programme page, Paris-Saclay tuition fees, Khalifa admissions,
  Tec profesional).
