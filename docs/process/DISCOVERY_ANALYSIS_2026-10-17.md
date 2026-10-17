# Discovery on unseen universities — root-cause analysis (2026-10-17)

Author: claude-opus-5 (analysis only; no `app/` change, no commit). Inputs: code on
`claude/greeting-16wj2z` (HEAD `06323a8`) and the unpacked run artifacts of 2026-10-06/07
(Exa MCP, runs 37545452839 cohort / 37554279823 heldout) and 2026-10-17 (Serper, runs
39058503662 cohort / 39058505075 heldout). Per case: `<case>.json`, `<case>.log` (one line per
`Fetcher.get` and per provider query), `<case>.raw.json` (discovery trace).

**Protocol.** Heldout traces were read only to locate the *stage* at which a page is lost; no
expert draft, no `heldout.draft1.json` and no scorecard built on them was opened. Every rule
below is justified by a cohort case or by code, and merely *expected* to move a heldout case.
Three public pages were fetched by hand for mechanism checks (TUM's `studycourse` sitemap and
one German/English programme pair, Masaryk's programme pages, NU's sitemap index, METU's and
NU's `robots.txt`); nothing was fetched through the pipeline.

## 0. Summary

| # | Root cause (one line) | Kind | Cases it decides |
|---|---|---|---|
| 1 | The sitemap stage reads index children in file order under a 12-document cap and probes all four fallback paths even after one succeeds; news/post sitemaps eat the cap and the clock | (a) mechanism | NU (75 s, programme sitemap never reached), METU (30 s on three 404s), TUM (7 of 11 documents were news/events) |
| 2 | Search is appended after sitemaps + seeds + navigation + confirm + walker; on a slow host it is never reached and the clock ends with `search_calls=0` | (a) | METU 4/4 (Crawl-delay 10 s, 0 queries), NU 1/4 |
| 3 | Queries carry only the applicant's own words, quoted (`"computer science"`), tuned for a neural index; a keyword engine cannot return a page titled "Informatics" that never says "computer science" | (a) | TUM/Serper 4/4 miss vs TUM/Exa 4/4 hit |
| 4 | URL-shape scoring and field matching are English/cohort-lexicon only (`opleidingen` yes, `studienangebot`/`laurea`/`UKEN-n` no); localized aliases exist in the ontology but discovery never uses them; no language-alternate (hreflang) follow | (a) | TUM (German twin scored 0; `Informatik` subject rejected), Polimi (`laurea-magistrale` not a degree slug), Charles (opaque URLs → 719 seen / 0 kept) |
| 5 | The 8-read identity-recovery cap is spent on lexical junk (publications, news, course archives) because ranking has no programme-ness signal and `_URL_EXCLUSIONS` miss `/publications/`, `/article/`, `news-single-view`; the classifier then accepts some of that junk as `program_detail` | (a) | TUM/Serper (publication "fingerprints" page reported as the programme), KAIST, Vilnius, Polimi (8 reads, 0 confirmed), HKU (`cs.hku.hk/` root), Tartu (blog archive) |
| 6 | `extract_requirements` → `_named_bands` is quadratic on long sentences (`_IELTS_SENTENCE` regex): 15 s per 31k-char page, synchronous, uncancellable; the child is killed and its output stays at the pre-confirm checkpoint | (a) + measurement | Masaryk 8/8 `CAPTURE_IN_PROGRESS` although its Informatics page was read |
| 7 | Hop entry points open the root of every distinct host in the results; a dead host costs the fetcher's full 30 s | (a) | Charles/Exa 3/4 (explorer.cuni.cz 33.8 s + nomos.is.cuni.cz 30.3 s) |
| 8 | Curated seeds decide the walker's roots and the `registry_seed_host` ranking bonus; the benchmark harness can only run registry entries at all | (b) registry | every non-registry university; TUM's `program_catalog` seed is an application-info page, so the walker read "ScienceManagement@TUM" |
| 9 | Crawl-delay 10 s, robots.txt unreachable from GitHub runners, 5 MB sitemaps, JS-rendered catalogues | (c) site access | METU, Aalto/HKU/KAIST admission hosts, Tartu (`ut.ee/sitemap.xml` too_large), Polimi |

The headline "0 of 7 readable sites with either provider" is a Serper fact. Under Exa MCP, TUM's
exact programme page was confirmed in 4/4 repetitions (held1 `tum-*/tum.json`), and Charles
confirmed `mff.cuni.cz/en/students/bachelor-of-computer-science` in 4/4 Serper and 1/4 Exa
repetitions (whether that page is the labelled one is for the expert set to say). The provider
swap did not move the *count* because it swapped one failure mode (Exa MCP slowness, dead-host
hops) for another (keyword queries that cannot name the page, junk that fills the read cap).

## 1. Discovery path and where each case loses the page

The path (same for production and the benchmark): `evaluation/research/live.py:capture_one`
→ `scripts/canary_discovery.py:run_canary` (registry entry by homepage substring, L373–380)
→ `ResearchRunner.run_to_decision` → `LiveDiscoveryAdapter._discover_one`
(`app/adapters/discovery/live_discovery.py` L1105–1220), stages in this order:

1. manual seeds (L1121–1133) → 2. sitemaps with `keep()` URL scoring (L1135–1175; `SitemapReader.collect` L923–1001) →
3. navigation fallback if no programme candidate (L1186–1188) → 4. `_confirm_programs` reads ≤ 8 candidates (L1222–1268) →
5. `_walk_catalogs` (L1330–1415) → 6. `_add_search_results` → `retrieval.discover_candidates` (6 queries, prefilter, BM25, hop roots) →
`_recover_search_pages` reads ≤ 8 (L1737–1875) → 7. `_apply` (L1877). Then the verify stage
(`web_requirements.verify`) reads programme + admissions pages and extracts.

### 1.1 Delft (cohort success, Serper on, `sctl/x/delft-on/20261017T183655Z`)

| t | stage | evidence |
|---|---|---|
| 1–5 s | robots + one sitemap document (`get #2 took 3.8s`) | `sitemap.xml` is a flat list |
| 5–8 s | confirm reads `#4–#6`; `#5` = `/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/bachelor-of-computer-science-…` → accepted | URL scores `/bachelors/` +5, `opleidingen` +3, field words +16, degree +4 (offline check with `categorise_url`/`matches_field`) |
| 10–14 s | walker on the seed catalogue reads 5 leads (nanobiology, aerospace …) — unnecessary, programme already confirmed | log `#11–#15` |
| 17–23 s | 6 Serper queries (slots not full) | `search #1..#6` |
| 23–38 s | hop roots + 8 recovery reads add the Dutch twin | `programme_urls` = 2 |
| 39 s → | verify reads admissions/fees/scholarships seeds | 32 network reads, 54 s |

Delft succeeds because its sitemap lists an English URL that *names the field and the level*. No
seed is needed for the programme page; seeds only supplied admissions/costs pages to extraction.

### 1.2 TUM (heldout; Serper 4/4 wrong page, Exa 4/4 right page)

Serper on, `shel/x/tum-on/20261017T190456Z` (`tum.log`, `tum.raw.json`):

| t | stage | what happened | loss point |
|---|---|---|---|
| 1–19 s | sitemaps: index + `pages` + `studycourse` + `news` ×5 + `events` ×2 = 11 documents, 6 295 URLs seen, 44 kept | `studycourse` lists only German URLs: `/studium/studienangebot/detail/informatik-bachelor-of-science-bsc` (checked by hand, 182 locations, zero `/en/`); the English twin is in no sitemap | **URL scored zero** — `_URL_SIGNALS[PROGRAM_PAGE]` (L221–231) has no `studienangebot` and `matches_field` (L463–481) knows `informatics` but not `informatik`; offline: `categorise_url(...) = (None, 0)`. Rejected "scored zero for every category" (L1152) |
| 19–41 s | confirm reads the 3 sitemap picks (`bewerbung-bachelor`, `infografik-bachelor`, `tie2-asian-venture-programm`) → all rejected on subject; walker reads 5 "catalogues" incl. `/en/lifelong-learning/.../science-management` (seed `program_catalog` is an application-info page, walker scored its links) | 23 reads, 18 of them cache hits | (b) seed misleads; walker confirms 0 |
| 44–49 s | 6 Serper queries: `site:tum.de "computer science" "bachelor" site:tum.de` … (intent.py L232–249; `serper._with_domains` L38–44 appends a second `site:`) | prefilter rejected 8 wrong level, 5 excluded paths, 7 duplicates | The English page's HTML contains **0 occurrences of "computer science"** (title "Informatics - Bachelor of Science (B.Sc.) - TUM", checked by hand). A quoted keyword query cannot return it; the owner's smoke query used the word *informatics* and got it at #1 |
| 49–73 s | hop roots `cs.cit.tum.de/`, `tum.de/`, `ed.tum.de/`; recovery reads 8: information-engineering (subject ≠), ed.tum.de `news-single-view-start/article/…` (unknown), **`portal.fis.tum.de/en/publications/…/fingerprints` → accepted as `program_detail`**, aerospace, application-bachelor, `cs.cit.tum.de/en/camp/teaching/previous-courses`, chemical, mechanical | "search identity recovery: checked 8, confirmed 1" | **read cap exhausted on junk; false positive confirmed**. `classify_url` says IRRELEVANT for `/publications/` (page_classifier.py L364–377) but `classify_page` only rejects when the body also has ≥ 2 research words (L449–458); a Pure "fingerprints" page has none, so title words "Undergraduate … Computer Science" make it a bachelor programme (L583–607). `_URL_EXCLUSIONS` (L283–292) do not list `/publications/`, `/article/`, `news-single-view` |
| 73–79 s | verify: `programme.exists = True` claimed from the publication page | `page_outcomes[0]`: `program_detail`, 1 236 chars, "1 claims read" | wrong claim |

Exa MCP on, `held1/x/tum-on/20261007T011349Z`: same first 23 s, then 6 Exa queries at t=24–34 s,
hop roots `cs.tum.de/`, `cs.cit.tum.de/`, `tum.de/`, recovery read #6 =
`/en/studies/degree-programs/detail/informatics-bachelor-of-science-bsc` → confirmed (t=45 s).
Exa's neural index returned the page without the phrase; Google did not. The same run also shows
rule 4 at work: `cit.tum.de/en/cit/studium/studiengaenge/bachelor-informatik` was read and
rejected "page subject 'Informatik' does not match requested fields ['computer science']"
(`matches_field_text`, L591–615, uses `with_strong_aliases` L493–506 — strong aliases only;
the ontology's `localized_aliases` `{"de": "informatik"}` is never consulted by discovery).

Checked by hand: TUM's German detail page carries
`<link rel="alternate" hreflang="en-US" href="…/en/studies/degree-programs/detail/informatics-bachelor-of-science-bsc…">`.
A one-read "follow the English alternate of a local-language programme page" would have reached
the page from the sitemap in every run, with no search.

Separation: (a) rules 3, 4, 5 of the summary; (b) the `program_catalog` seed sent the walker to
the wrong pages (5 catalogue reads, 0 confirmed); (c) none — tum.de answered every read in ≤ 3 s.

### 1.3 Charles (heldout; Serper 4/4 found `mff.cuni.cz/en/students/bachelor-of-computer-science`, Exa 1/4)

Serper on, `shel/x/charles-on/20261017T184405Z`:

| stage | what happened | loss point / cost |
|---|---|---|
| sitemaps | `cuni.cz/sitemap.xml` ok (5.1 s) then **three fallback paths probed anyway** → 3 × 404; 719 URLs seen, **0 kept** | `SITEMAP_FALLBACK_PATHS` are all queued when robots.txt names none (L939–941) and the loop never stops after a success. cuni.cz URLs are opaque (`UKEN-556.html`): URL-shape scoring has nothing to score |
| seeds | `admissions`, `costs` only — no `program_catalog` | (b): navigation fallback and walker start from the homepage; homepage links are `UKEN-n.html` with short labels → walker `short_label`/`walker_no_signal`, 0 confirmed |
| search | 6 queries; recovery read 8: homepage PDFs (unknown), `degree-plans-general-computer-science` (rejected: variant "degree plans"), **`bachelor-of-computer-science` (confirmed)**, `state-final-examination…` (variant), `admissions/study-programmes-and-branches-of-bachelor-studies` (classified `program_detail` with subject "Study Programmes and Branches…" → rejected on subject, so its links were **not** followed — the listing-follow in `_recover_search_pages` L1828–1851 only fires for `_LISTING_PAGE_TYPES` = {PROGRAM_CATALOG, UNKNOWN}), `is.cuni.cz/…detail_obor&id_obor=34738` (rejected "reads as general_admissions") | a catalogue misclassified as one programme blocks the catalogue hop; the admission-system detail page is a different page type than the classifier expects |

Exa on, `held1/x/charles-on/20261007T010620Z` (budget exhausted at 115 s): identical to t=22 s;
then hop roots `explorer.cuni.cz/` **33.8 s network_unavailable** and `nomos.is.cuni.cz/`
**30.3 s network_unavailable** (`_entry_points` opens the root of every distinct result host,
retrieval.py L334–354, L460–469; `Fetcher` timeout 20 s × attempts) — 64 of 115 s — then the same
mff pages at t=89–98 s and the kill before `_apply`. Separation: (a) rules 1, 5, 7; (b) no
catalogue seed and opaque URLs make the walker useless; (c) two cuni.cz hosts refuse connections
from the runner.

### 1.4 METU (heldout; 8/8 budget exhausted, 0 queries)

`shel/x/metu-on/20261017T183814Z/metu.log` — every read takes ~10 s:
`robots.txt` 1.0 s, `sitemap.xml` 10.2 s, then `sitemap_index.xml` 9.7 s (404), `sitemap-index.xml`
10.0 s (404), `sitemap/sitemap.xml` 10.0 s (404), seed catalogue 10.2 s, navigation leads
`http://…/admissions/undergraduate-programs` 11.4 s **and** `https://…/admissions/undergraduate-programs`
10.1 s (scheme-only duplicate: `canonical_url` keeps the scheme, L386–416), `node/899` 19.8 s,
`node/1099` — killed at 115 s. `search_calls = 0`.

Cause: `https://www.metu.edu.tr/robots.txt` says `Crawl-delay: 10` (checked by hand); the fetcher
honours delays up to `MAX_CRAWL_DELAY_SECONDS = 10.0` (fetching.py L58, `_space_requests`
L879–886). With 10 s per read the 120 s clock holds ~11 reads, and the stage order spends them on
three guaranteed 404s, one duplicate and navigation before search (which costs no read) is ever
reached. Separation: (c) the host's policy; (a) the three wasted probes, the duplicate, and a
stage order blind to the per-read cost; (b) the single `program_catalog` seed was read but the
walker never ran before the kill.

### 1.5 NU and Masaryk (budget exhaustion the task asked about)

**NU** (`shel/x/nu-on/20261017T183421Z`): robots names `sitemap_index.xml`, whose children are
`post-sitemap1..24.xml`, then `page-sitemap1..3.xml`, `sprogram-sitemap1..2.xml` (checked by
hand). `collect` reads children FIFO under `MAX_SITEMAP_DOCUMENTS = 12` (L67, L948): index + 11
post sitemaps, **75 s**, programme sitemap never read. Navigation then found
`scai.nu.edu.kz/bsc-cs` and confirm read it at t=91 s (`get #16`), search ran t=104–110 s, and the
kill at 115 s came before `_apply`, so `programme_urls` is empty although the page had been read
and (per the log order) accepted. The failure is time, not discovery.

**Masaryk** (`shel/x/masaryk-on/20261017T184701Z`, all 8 repetitions `CAPTURE_IN_PROGRESS`):
reads stop at t=40 s, resume at 57 s, stop again at 59 s and nothing is logged until the parent
kills the child at 120 s. Reproduced offline on the pages the run read: `extract_requirements`
takes 4.7 s on `22955-informatics` (18k chars) and 14.8 s on `24410-english-language-and-literature`
(31k chars); cProfile puts 15.03 of 15.09 s in `_named_bands` (extraction.py L673), i.e. in
`_IELTS_SENTENCE = (?:[^.\n]|\.(?=\d))*\bIELTS\b(?:[^.\n]|\.(?=\d))*` (L327–330), whose unanchored
leading repetition is quadratic on long period-free lines. Three programme pages per case ×
5–15 s of synchronous regex block the event loop, so the child's own `asyncio.wait_for` cannot
fire (live.py L579–602), the parent's `subprocess.run(timeout=…)` kills it (L1028–1038), and the
observation keeps the checkpoint from before confirm (`ranked_urls` = the CESP page,
`programme_urls = []`). Masaryk read its Informatics bachelor page in every repetition
(`22955-informatics`, `28473-theoretical-computer-science`) and reported nothing.

## 2. Production for a top-500 university that is not in the registry

Path: `ResearchRunner._make_discovery_adapter` → `CatalogueDiscoveryAdapter`
(`app/catalogue/discovery.py`), not `LiveDiscoveryAdapter.discover`.

| step | what a non-registry university gets | source |
|---|---|---|
| import | a `University` row with `domain = seed_domain(row)` (`official_domain`, or `None` when it conflicts with `official_site`), `domain_status` `seed`/`unknown`; **no seeds, attributes, rankings or campuses**; 353 of 500 seed rows carry a domain, 147 carry none (e.g. Melbourne, Seoul National, Tokyo, Sorbonne) | `importer.py` L144–149, L158–244 |
| retrieval order | `retrieve()` sorts by (named in query, preferred country, **registry entry first**, name); only the first `live_limit = verify_limit` (default 20) rows are live-enriched (`discovery.py` L43–79) | the 19 registry rows always precede the 481 others, so an unseen university is enriched only when the applicant names it (`university_ids`) or prefers its country |
| site identity | `_identify_site`: probe `https://{domain}/` and `official_site`; the homepage's `<title>`/`<h1>` must contain the normalized English name (≥ 8 chars) or an acronym that is also the host label plus the word university/college/institute; else one provider query `"name" "country" official university website` (outside the 6-query budget) and probe the top-3 hosts | `discovery.py` L101–193 |
| discovery | on success the entry is `{"name","country","city","homepage"}` — the same `_discover_one` as the benchmark with **empty seeds**: sitemaps → navigation → confirm → walker rooted at the homepage → search → recovery | L96 |
| budget | `asyncio.wait_for(_enrich, 300)` per university — not the benchmark's 120 s; browser tier per settings; warm cache (TTL 86 400 s) | L65–76 |

Consequences for the 481: (1) the identity gate fails on sites whose homepage title is not the
English name — Chinese/Japanese/Korean/Cyrillic titles, "TUM - Technische Universität München",
"LMU München" — and then **no live discovery runs at all** ("Official website identity not
established"); (2) a stale seed domain (Khalifa `kustar.ac.ae`, UCLouvain `ucl.ac.be`, CUHK listed
as `cuhk.edu.cn`) redirects off-site, fails `same_source_site`, and falls to the search path;
(3) without seeds the walker only has the homepage, so the programme page comes from the sitemap
(English, field-naming URLs) or from search — exactly the two paths that fail in §1; (4) no
admissions/costs/scholarship seeds, so core coverage will be lower than the cohort even when the
programme page is found. Rules 1–5 below are seed-independent for this reason.

What `live.py` lacks for such a university: `--case` is `choices=[*COHORT, *HELDOUT]` (L629) and
`run_canary({**COHORT, **HELDOUT}[case_id], False)` (L580) selects a **registry** entry by homepage
substring (`canary_discovery.py` L333–348, L378–380). A seed-only university cannot be captured.
Rule 0 fixes this.

## 3. Development cohort dev2

Ten seed universities, none in the registry or the heldout nine, chosen for country, site
language, site technology and programme language; machine-readable copy at
`scratchpad/dev2_cohort.json` (fields: case, name, domain, country, seed_id, programme_hint, why).

| case | official name | domain | country | site / programme language | tech | why |
|---|---|---|---|---|---|---|
| ethz | ETH Zurich | ethz.ch | Switzerland | de + en twins / German | AEM, SSR | dev case for localized aliases + hreflang twins (TUM tests it later) |
| psaclay | Université Paris-Saclay | universite-paris-saclay.fr | France | fr + en / French (Licence Informatique) | Drupal | `licence` slug known; many near-duplicate licence pages test identity precision |
| uppsala | Uppsala University | uu.se | Sweden | en page, Swedish-taught (datavetenskap) | SSR | local-language programme on an English page; off-site national admissions portal |
| tcd | Trinity College Dublin | tcd.ie | Ireland | en / English (B.A. Mod. Computer Science) | SSR, `course.php?id=` | opaque URLs on an English site (English counterpart of KAIST) |
| tsinghua | Tsinghua University | tsinghua.edu.cn | China | zh + en admissions host / Chinese | SSR | CJK title defeats the identity gate; opaque URLs |
| tec | Tecnológico de Monterrey | tec.mx | Mexico | es + en / Spanish (Ingeniería en Tecnologías Computacionales) | **JS-heavy SPA** (expert to confirm) | `js_no_program_list` path without curated seeds; Spanish aliases absent from the ontology |
| uba | Universidad de Buenos Aires | uba.ar | Argentina | es / Spanish (Licenciatura en Ciencias de la Computación) | **PDF-heavy**, federated hosts | multi-host under one domain, study plans as PDFs, no English twin |
| kaznu | Al-Farabi Kazakh National University | kaznu.kz | Kazakhstan | kk/ru/en / three tracks | SSR | home market; `информатика` is the one localized alias already present. Same country as heldout NU, different institution |
| uct | University of Cape Town | uct.ac.za | South Africa | en / English (BSc Computer Science) | Drupal, **PDF handbooks** | PDF-heavy English case; department host cs.uct.ac.za |
| khalifa | Khalifa University | ku.ac.ae (seed says kustar.ac.ae) | UAE | en / English (BSc Computer Science) | SSR | the only case exercising the stale-seed → site-identity fallback |

Mix: 10 countries, none from the cohort; English-taught 3 (tcd, uct, khalifa) + kaznu's English
track; local-language 6; one JS-heavy, two PDF-heavy, two opaque-URL, one CJK, one stale seed.
Each has a computer-science bachelor an international applicant can apply to (programme_hint
names it). Labels go to `evaluation/research/data/dev2.draft1.json` in the `Case` schema
(`schema.py` L72–96: id, university, domain, country, site_types, request, programme_urls, labels).

## 4. Rules, ranked (one flag, one paired run each)

**Rule 0 — `DEV2` cases without registry entries (required).**
`live.py`: add `DEV2 = {"ethz": "qs2027-008", …}` (case → seed_id), accept it in `--case`, and for a
DEV2 case build the entry from `unimatch_top500_seed.json` — `{"name", "country", "city",
"homepage": f"https://www.{domain}/"}` with the domain from `dev2_cohort.json` (so khalifa uses
`ku.ac.ae`) — the exact shape `CatalogueDiscoveryAdapter._identify_site` returns, so the capture
measures the production no-seed path. `canary_discovery.run_canary(only, verbose, batch=None,
*, entries: list[dict] | None = None)`: when `entries` is given skip `select_registry_entries`;
`university_ids` keep using `stable_id(identity_key(name, country))` (the seed row exists because
`import_catalogue` imports all 500). `benchmark-capture.yml`: let the `case` input accept dev2
ids. Offline tests: `tests/test_canary_checks.py` — `run_canary(entries=[…])` with the runner
monkeypatched builds one candidate whose trace has `manual_seeds == {}`; `tests/test_research_benchmark.py`
— `--case ethz` resolves and the child receives a homepage, not a registry selector. Also add a
second DEV2 arm later that goes through `_identify_site` itself (stale khalifa seed) to measure
the identity gate.

| rank | rule / flag | cause fixed | mechanism | precision guard | files | offline test | expected to move |
|---|---|---|---|---|---|---|---|
| 1 | **SM-1 `SITEMAP_CHILD_PRIORITY`** | §0 #1 | In `SitemapReader.collect`: (i) when a fallback sitemap succeeds, stop probing the remaining `SITEMAP_FALLBACK_PATHS`; (ii) order index children by a name score — `program|programme|study|course|degree|page|curricul` first, `post|news|event|announce|blog|press|media|calendar|tag|author` last — and skip the last group once the document cap would be exceeded by children of the first group | none needed: changes read order only; every URL still passes `keep()` and the confirm classifier | `live_discovery.py` (`collect`, new `_child_priority`) | fake fetcher serving an index of 24 `post-sitemap*` + `page-sitemap*` + `sprogram-sitemap*`: assert `sprogram` read within 12 documents; `/sitemap.xml` ok → no request to the other three paths | cohort: none expected to change labels, −3 reads on KAIST/Charles-type hosts; NU −60 s, METU −30 s, TUM −7 docs; dev2: kaznu, uct, uba (WordPress/Drupal indexes) |
| 2 | **SO-1 `COST_AWARE_SEARCH_ORDER`** | §0 #2 | Before navigation/walker, run `_add_search_results` when (a) sitemaps produced no programme candidate (the existing `SEARCH_BEFORE_NAVIGATION` switch) or (b) `fetcher.robots.crawl_delay(homepage) ≥ 5 s` or the median of the first three reads ≥ 5 s; in case (b) also cap sitemap documents at 3 and skip the walker. Search costs no page read and ~1.3 s per query under Serper | same confirm predicate; only order changes. Record `stage_order` in the trace | `live_discovery.py` `_discover_one` (L1182–1204), read `Fetcher.robots.crawl_delay` | fake clock + fake fetcher with 10 s/read: assert the provider is called before the second navigation read and the walker is skipped; a 1 s/read host keeps today's order | METU (searches at ≈50 s instead of never), NU (with SM-1 unnecessary but harmless); cohort: Groningen/UBC (walker reads before search today) must show no loss — this is the measured risk of run 26 under Exa MCP, to be re-measured under Serper |
| 3 | **QA-1 `ALIAS_QUERIES`** | §0 #3 | `queries_for`: the `field_and_degree`/`programmes`/`undergraduate` families take an OR-group of the ontology's **strong** aliases (`("computer science" OR informatics OR computing)`), the `natural_language` family stays unquoted; one extra family in the site language when `<html lang>` of the homepage is known and the ontology has a localized alias for it (`Informatik Bachelor`); `serper._with_domains` does not append `site:` when the query already carries it | domain filter, degree prefilter and the page-subject confirm are unchanged; `matches_field_text` already accepts strong aliases, so an alias hit is confirmed on the page, never on the snippet | `search/intent.py` L207–283, `search/serper.py` L38–44, `search/ontology.py` | `tests/test_discovery_intent.py`: rendered queries contain the OR-group and no profile data; `tests/test_serper_provider.py`: single `site:` | TUM/Serper (title "Informatics"); Masaryk ("Informatics"); dev2 ethz ("Informatik"), uppsala after LI-1 aliases; cohort Groningen ("Computing Science") unchanged or better |
| 4 | **LI-1 `LOCALIZED_IDENTITY`** | §0 #4 | (i) `with_strong_aliases` also returns the ontology's `localized_aliases` (and `_DEGREE_SLUGS` gains certain Bologna words: `laurea`, `laurea-magistrale`, `lisans`, `yuksek-lisans`, `bakalar*`, `magister*`, `kandidat`, `grado`, `mestrado`, `master-s`); (ii) `matches_field_text` accepts a localized alias as subject under the same filler rule; (iii) after a programme candidate on the institution's domain is read, if the page carries `<link rel="alternate" hreflang="en*">` on the same registrable domain and the current page's language is not English, read the alternate once and classify it in place of (or beside) the original | a localized alias matches only when nothing else in the title names another subject (`_TITLE_FILLER` rule, so "Wirtschaftsinformatik" ≠ "Informatik"); the degree-level check stays; the alternate is same-domain, counted as a read, and judged by the classifier like any page. New aliases only where the ontology's own rule holds ("not in doubt") | `live_discovery.py` (L309–346, L493–506, L591–615, `_confirm_programs`/`_recover_search_pages`), `search/ontology.json`, walker inherits | `tests/test_discovery_strong_aliases.py`: `Informatik` matches CS, `Wirtschaftsinformatik`/`Bioinformatik` do not; `tests/test_live_discovery.py`: a German sitemap URL `…/studienangebot/detail/informatik-bachelor-of-science-bsc` is kept with score > 0 and its hreflang twin is read and confirmed with a fake fetcher; Polimi-shaped `laurea-magistrale` URL rejected before a read | TUM (sitemap path, no search needed), Polimi (one wasted read saved), dev2 ethz, psaclay, uppsala, tec, uba, kaznu; cohort Vienna/Warsaw/Groningen must not lose their English pages |
| 5 | **PG-1 `PROGRAMME_PAGE_GUARD`** | §0 #5 | (i) prefilter drops URLs `classify_url` calls IRRELEVANT (existing `reject_irrelevant_kinds` switch) and `_URL_EXCLUSIONS` learns `/publications?/`, `/article/`, `news-single-view`, `/clippings/`; (ii) `classify_page` returns at most UNKNOWN for a URL-IRRELEVANT page or a host root unless the body shows ≥ 2 programme-structure signals (ECTS/credits, semesters/duration, admission requirements, start of studies/intake, tuition); (iii) `_recover_search_pages` no longer promotes unread `pending` leads to programme pages (L1867–1868) — they become `unresolved` diagnostics | a rejection still needs URL *and* body evidence (today's rule), the body test is the structure test; Warsaw's URLs classify UNKNOWN so are untouched; the measured regression of `rank_by_page_kind` concerned ranking, this is rejection, and the paired run must show no cohort loss | `search/prefilter.py` L109–181, `page_classifier.py` L364–377, L449–458, L583–607, `live_discovery.py` L283–292, L1867–1868 | `tests/test_page_classifier.py`: a Pure "fingerprints" fixture and a department home fixture are not `program_detail`; `tests/test_search_identity_recovery.py`: pending leads are not promoted; `tests/test_search_probe.py`: KAIST's ftp/pure/`courses/2006` URLs never take a read | TUM/Serper (publication no longer a programme; frees reads), HKU (`cs.hku.hk/`), Tartu (blog), Aalto (minors via pending), KAIST (reads freed for `cs.kaist.ac.kr` pages); the only rule here that also raises precision |

Not in the five, but cheap and worth a flag each: **HP-1** hop entry roots get an 8 s deadline
(Charles/Exa 64 s); **CU-1** `canonical_url` treats `http`/`https` of one institution page as one
URL (METU 10 s; `navigation.py` already does this locally); **EX-1** rewrite `_named_bands` to
scan `\bIELTS\b` matches and expand to sentence bounds (linear) and add a 2 s per-page extraction
deadline (Masaryk) — EX-1 is a bug fix with a regression test, not a discovery rule, and should
land before any paired run so Masaryk-type cases stop reading as discovery failures.

## 5. What is misleading in the current measurement

1. **"Programme page found" is not identity-checked outside the gold scorer.** Canary
   `program_page_found`, the loop report's 6/10 and `programme_urls` counts include a publication
   (TUM), a department root (HKU), a blog archive (Tartu), two minors (Aalto) and a catalogue
   (`future.utoronto.ca/undergraduate-programs`). Judge discovery by programme identity against
   labels, or at least exclude URLs the classifier called unknown/irrelevant at verify time.
2. **Unread leads count as found.** `_recover_search_pages` L1867–1868 promotes unread
   `pending` URLs when nothing else was confirmed; with robots.txt unreachable from the runner
   (Aalto 3/3) the case reports three "programme pages" it never read.
3. **The clock is charged to stages that are not discovery.** Robots + sitemaps took 75 s at NU
   and 50 s at METU; extraction regex took 15 s per page at Masaryk. `telemetry` records neither
   the stage the clock ended in nor per-stage time. Add `stop_stage` and per-stage seconds, and
   write the confirmed programme list at confirm time (`observed_confirm` already records the
   queue), so NU shows "found at 91 s, killed at 115 s" instead of nothing.
4. **`CAPTURE_IN_PROGRESS` hides work done.** A synchronous CPU hang cannot be cancelled; the
   parent kill discards claims and the confirmed programme (Masaryk 8/8). EX-1, plus a checkpoint
   after confirm, turns this into an honest partial result.
5. **`search_calls = 0` reads as "no provider"** when it means "the clock ended before search"
   (METU). Same fix as 3.
6. **The trace cannot say whether search returned the page.** `rejected_sample` is capped at 40
   and filled by sitemap rejections (Vilnius, Polimi show none of their 8 search reads); the
   ranked provider list is not recorded in the recovery path (the non-recovery path logs
   "offered: …"). For TUM/Serper one cannot tell "not returned" from "returned at rank > 8".
   Record the top-10 ranked URLs per institution (public URLs, no query text, consistent with
   `QueryAuditRecord`'s redaction) and put search rejections in their own capped list.
7. **Provider comparisons are not paired.** Exa MCP and Serper fail differently (TUM 4/4 vs 0/4;
   Charles 1/4 vs 4/4; Sabanci 1/4 vs 4/4 driven by Exa's 15 s timeouts and dead-host hops).
   "No change with either provider" is true of the count and false of the mechanism.
8. **Read counts.** In non-strict mode `get #55` at TUM is 45 network reads + 10 cache hits; the
   log numbering overstates cost while `http_fetches` is right. Harmless, but reviewers quote the
   log.
9. **Network of measurement.** GitHub runners cannot reach `admission.kaist.ac.kr`,
   `admissions.hku.hk`, `www.aalto.fi` robots, `explorer.cuni.cz`, `nomos.is.cuni.cz`; the heldout
   denominator "7 readable" depends on which hosts happened to answer. Track E (Fly runner) or the
   access probe should fix the denominator before dev2 is scored.

## 6. Evidence index

- Logs/traces: `scratchpad/{held1,shel,sctl,rl1run}/x/<case>-<arm>/<stamp>/<case>.{json,log,raw.json}`.
- Hand checks (public pages, not through the pipeline): `scratchpad/tum_studycourse.xml` (182 German
  locations), `scratchpad/tum_pages.xml` (570 locations, 0 `/en/`), `scratchpad/tum_informatik.html`
  (hreflang en-US twin), `scratchpad/tum_informatics.html` (0 × "computer science"),
  `scratchpad/pages/*.html` (Masaryk timing), `https://www.metu.edu.tr/robots.txt` (`Crawl-delay: 10`),
  `https://nu.edu.kz/sitemap_index.xml` (24 post sitemaps before page/sprogram).
- Offline reproductions (venv): `categorise_url`/`matches_field_text` on the decisive URLs and
  subjects; `classify_page` 0.2 s vs `extract_requirements` 4.7–14.8 s with cProfile on `_named_bands`.
