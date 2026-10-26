# Programme-page discovery on non-English universities — where the gold page is lost, and what would generalise (2026-10-18)

Analyst: claude-opus-5, read-only (no repo file changed, nothing committed). Branch `claude/greeting-16wj2z`,
HEAD `26d6f7b`. The heldout nine were not opened in any form: no `heldout.*.json`, no `runs/heldout-final`,
no `held1`, `dl_charles`, `dl_metu`, `tum_*` scratch files. Every statement about them below rests on the
public facts stated in the brief (nine universities in KZ, TR×2, CZ×2, DE, EE, IT, LT, publishing mainly in
the local language).

**Inputs.** Development captures `scratchpad/runs/bundle5-{cohort,dev2,dev3}/x/<case>-{on,off}/<ts>/`
(`pipeline_sha 2ad5065`; the `on` arm = SB-1 + QR-1 + FI-1 + CG-1, i.e. today's defaults minus IM-1 and the
later extraction fixes; `off` = the defaults before the bundle) plus `lx1-*` for comparison; the official
scorecard run on each (`pd_tools/sc-bundle5-*.json`); gold `ground_truth.reviewed10.json`, `dev2.draft1.json`,
`dev3.draft1.json`; code at HEAD. Tooling: `scratchpad/pd_tools/dump.py` (per-capture funnel → `rows.json`),
`detail.py` (per-case dumps `detail_*_on.txt`), `predicates.py` (runs today's `categorise_url`, `score_url`,
`matches_field`, `classify_page`, `profile_rejects`, `english_alternate`, walker `score_link` offline on the
local-language gold pages, with LX-1 off and on), `links.py` (language-switch and catalogue links on a saved
homepage). Twenty-six public pages of development universities were fetched by hand into
`scratchpad/pd_pages/` (homepages, local gold pages, catalogue pages, robots/sitemaps of catalogue hosts);
nothing went through the pipeline and no search provider was called.

**Two limits that shape the answers.**
1. **Query text and the provider's result lists are not recorded** — by design (`intent.redacted_audit_record`
   keeps family, provider and count only; `RetrievalReport` keeps `found_by` per candidate but discovery writes
   neither to the trace). The queries below are therefore *reconstructed exactly* from `intent.queries_for`
   with the institution name and registrable domain each capture used (verified by running the function);
   they are deterministic, so the reconstruction is the text that was sent. "Top results" can only be read
   off what identity recovery *read*: the first ≤ 8 leads after prefilter and ranking, in rank order
   (`MAX_PROGRAM_CANDIDATES_CHECKED = 8`), which the `.log` records as fetches. A URL the provider returned
   below that rank, or that the prefilter dropped, is invisible.
2. "Gold seen" below means the gold URL (or its first 100 characters, the log truncates at 120) appears in
   the log's fetches or anywhere in the trace (`selected`, `rejected_sample`, walker outcomes, errors).

## 0. Headline

| set (bundle5, on arm = closest to defaults) | programme recall rep1 / rep2 | hits | misses |
|---|---|---|---|
| cohort (10 with a gold URL) | 5/10, 5/10 | groningen, delft, vienna, warsaw, ntu | aalto, toronto, hku, kaist, ubc |
| dev2 (6) | 3/6, 3/6 | ethz, uppsala, tcd | psaclay, tsinghua, uba |
| dev3 (11) | 4/11, 3/11 | um, ucph, chula, unsw (rep 1 only) | imperial, iitd, kuleuven, auckland, puc, uio, ub, unsw (rep 2) |

Of the 24 development universities that publish mainly in a language other than English (the list in
question 2), **nine are found today and every one of the nine is found through an English page**: ETH `/en/`,
Uppsala `/en/`, UCPH's `hreflang=en` twin, UM, Chula (math.sc, English), Groningen `?lang=en`, Delft `/en/`,
Vienna `/en/`, Warsaw `/en/`. **No development programme page has ever been confirmed through a
local-language page.** The seven local-language gold pages the development sets hold (psaclay-fr, uba,
kuleuven, ucph-da, uio, puc, and UB's Catalan plan page) are each refused by at least one of today's
predicates when run offline on the real HTML (§2.2), and five of them (uba, kuleuven, uio, puc, psaclay-fr)
are never even listed by any stage (§1). The discovery queries have never contained a word in any language
but English (§2.1). That is the mechanism behind "0-1/9 on the heldout nine": the search is English-first at
every stage — query text, sitemap URL signals, catalogue-link labels, the classifier's degree words and the
subject matcher's filler — and a university that publishes its bachelor pages only in the local language has
no path through it.

Two structural defects were found that are language-independent and hit unseen universities first:

- **D1 — SB-1b's early search is refused when the sitemap filled the slots with *unconfirmed* leads, and is
  then never retried.** `_add_search_results` returns "Search not run … all 3 programme-page slots were
  already filled" (L2992) whenever `selected[PROGRAM_PAGE]` has three entries, confirmed or not;
  `search_now()` sets `searched_early = True` regardless, so the post-walker search is skipped too. UiO under
  today's defaults sends **zero discovery queries in both repetitions** (`search_limitations` in
  `bundle5-dev3/x/uio-on/*/uio.raw.json`; `discovery_query_passes` absent) because three
  `hf.uio.no/studier/karriere/underveis/praksis/ba/*` URLs (the `/ba/` slug reads as bachelor) took the slots;
  all eight confirm reads were rejected and nothing searched. The off arm sent 6. Any site whose sitemap offers
  three bachelor-looking slugs loses search entirely.
- **D2 — the scorer compares canonical URLs only, so a university found through its English twin is a miss
  when the gold lists the local URL** (psaclay: confirmed `/en/education/licence-undergraduate-programme/
  informatique` in all four bundle5 repetitions; gold lists only `/formation/licence/informatique`; the two
  pages declare each other as `hreflang` alternates). UCPH was the same case until the draft gold added the
  twin. This is measurement, not search, but it decides what "recall on local-language universities" means.

## 1. Question 1 — for every missed development case, the stage where the gold page is lost

Stages: **S0** host or page unreachable from the runner (robots fail-closed, 403, connection drop, other
registrable domain); **S1** never returned or listed by any query, sitemap, navigation or walker;
**S2** listed/returned but never read (ranked out of the 8 confirm reads or the 8 recovery reads, or the
clock ran out); **S3** read and rejected (predicate named); **S4** the programme was confirmed under another
URL and the scorer counts a miss.

The six discovery queries are the same six shapes for every case (`intent.queries_for`, `site_prefix=True`,
`ALIAS_QUERIES` off; Serper's `_with_domains` appends `site:<domain>` a second time). For Pontificia
Universidad Católica de Chile they were, in order (QB-1 first pass = q1–q3, second pass q4–q6 only if nothing
confirmed):

```
q1 [field_and_degree]  site:uc.cl "computer science" "bachelor" site:uc.cl
q2 [natural_language]  Pontificia Universidad Católica de Chile bachelor undergraduate first cycle computer science programme site:uc.cl
q3 [programmes]        site:uc.cl programmes "computer science" site:uc.cl
q4 [courses]           site:uc.cl courses "computer science" site:uc.cl
q5 [undergraduate]     site:uc.cl undergraduate "computer science" site:uc.cl
q6 [admissions]        site:uc.cl admissions bachelor site:uc.cl
```

Every other case differs only in the institution name and domain (full list in the reconstruction run,
`pd_tools/`; e.g. `site:uio.no "computer science" "bachelor" site:uio.no`, `site:uba.ar programmes
"computer science" site:uba.ar`, `Al-Farabi Kazakh National University bachelor undergraduate first cycle
computer science programme site:kaznu.kz`). The field term is always the applicant's English words in quotes.

### 1.1 Cohort misses (bundle5 on, both repetitions unless noted)

| case | gold | stage | what the captures show |
|---|---|---|---|
| aalto | `aalto.fi/en/study-options/computer-engineering-bachelor-…` | **S0** | `robots.txt` unreachable → RFC 9309 fail-closed; 4 reads, every one `robots_disallowed`. Gold URL "seen" only as a refused lead. |
| toronto | `future.utoronto.ca/program/computer-science` | **S0** | HTTP 403 on every `future.utoronto.ca` page (both arms, both reps). |
| hku | `admissions.hku.hk/programmes/undergraduate-programmes/computing-and-data-science` | **S0 → S4** | The gold URL **was returned by the first-pass queries and queued** (rep 1 fetch #16, rep 2 #16) and refused: `admissions.hku.hk` robots.txt unreachable → `search lead unresolved (robots_disallowed)`. Rep 1 then confirmed the school's own page `cds.hku.hk/prospective-students/undergraduate-old-2026/6999-computing-and-data-science` (sibling host); rep 2 read hkuspace, two 2013 talks and `master.cds.hku.hk/msccs` and confirmed nothing. Top recovery reads rep 2: `hkuspace.hku.hk/prog/bsc-hons-computer-science-cyber-security` (unknown), `jmsc.hku.hk/2013/02/feb-4-talk-…` (unknown, 10 s), `…/video-public-talk-…` (unknown), `master.cds.hku.hk/msccs` (master), a prospectus PDF. |
| kaist | `cs.kaist.ac.kr/content?menu=188` | **S3** (classifier) | Listed from `www.kaist.ac.kr/sitemap.xml` as **program_catalog** (score ties: a query-string URL has no slug), read at t=11–13 s, walked (5 candidates: `aiiscs/undergraduate` "AI 교과목 리스트" …, 0 confirmed). Offline, `classify_page` on the saved page returns **UNKNOWN** ("no decisive signals"): title "KAIST School of Computing, 카이스트 전산학부 - 컴퓨터공학과 컴퓨터과학(Computer Science & Engineering)…", no degree word in the identity, no English programme title. Search (6 queries) read 8 leads: `cs.kaist.ac.kr/content?menu=318`, `kaist.ac.kr/en/html/admission/0201.html`, lab/people pages (`urobot`, `plrg`, `human`, `hfel`, `wit`, `3dmems`), `me.kaist.ac.kr/eng/education/…` — all `unknown`; `stp.kaist.ac.kr/masters_students` master. The gold is a department page without a programme title; it cannot pass `_program_name` as written (gold/identity question for the owner, not a lexicon gap). `admission.kaist.ac.kr` is robots-refused (S0 for the admissions evidence). |
| ubc | `you.ubc.ca/programs/computer-science-vancouver-bsc/` | **S2 → S4 (sibling)** | Killed at 115 s in both reps (`you.ubc.ca` 4–25 s per read: `/programs` 25.3 s, `english-language-competency/development-programs` 15.1 s). First query at 47 s / 35 s; recovery read `…/computer-science-vancouver-ba` (7.9 s / 4.2 s) and confirmed it; the BSc gold was never read (not in the ≤ 3 preconfirmed recovery checks, or not returned — unknowable). Offline the BSc page classifies `program_detail`, subject "Computer Science (BSc)", accepted. The identity predicate cannot prefer BSc over BA for a "computer science" request; the gold does. |

### 1.2 dev2 misses

| case | gold | stage | what the captures show |
|---|---|---|---|
| psaclay | `universite-paris-saclay.fr/formation/licence/informatique` (French) | **S1 for the gold URL; S4 for the programme** | Sitemap: 13 599 URLs seen, 61 kept; the French URL is in the sitemap but `categorise_url` returns **None** for `/formation/licence/informatique` (no PROGRAM_PAGE signal: `_LOCALIZED_PROGRAM_SIGNALS` knows `formations` but not `formation`; `/licence/` is a degree slug, not a programme-path signal), so `keep()` dropped it. The English twin `/en/education/licence-undergraduate-programme/informatique` matched `/[a-z0-9]+-(programmes?)/…` (+4) and `matches_field` (+8: `informatique` is a settled fr alias) and was confirmed by the walker at t=31 s in every repetition (QB-1 then capped search at 3 checks). Offline the French page classifies **UNKNOWN**: identity "Informatique" has no degree word, and `_program_name_from_context` derives the degree from title or path, where the only level word is `licence`, which `_DEGREE_WORDS` and `_LEXICON_V2_DEGREE_WORDS` both lack. Both pages carry `hreflang` fr/en pointing at each other. **Fix is label-side (add the twin to dev2 gold) or scorer-side (hreflang aliases, §4).** |
| tsinghua | `international.join-tsinghua.edu.cn/Divisions1.htm` | **S0 (other registrable domain)** | No sitemaps (robots 404, 4 guesses 404). Homepage walked: `join-tsinghua.edu.cn`, `www.join-tsinghua.edu.cn` → `off_domain` (walker outcomes), as `same_institution` requires `tsinghua.edu.cn`. Search (6 queries) read: `cs.tsinghua.edu.cn/csen/info/1303/4316.htm` and four more `/csen/info/` news (unknown), `yz.tsinghua.edu.cn/en/info/1014/1154.htm` (general_admissions — graduate admissions host), `sigs.tsinghua.edu.cn/en/2021/…` (general_admissions), `ac.cs.tsinghua.edu.cn` (unknown). The homepage's "本科生招生" link is the gold's host (`join-tsinghua.edu.cn`) — exactly what DI-1 (`ADMISSIONS_HOST_FROM_HOMEPAGE`, off) reads. |
| uba | `ingresantes.exactas.uba.ar/licenciatura-en-ciencias-de-la-computacion/` (Spanish) | **S1** | `uba.ar/sitemap.xml`, `sitemap_index.xml`, `sitemap-index.xml` answered 200 but parsed to **0 URLs** (HTML, not XML); `sitemap/sitemap.xml` 500. Homepage walked: candidates were `cyt.rec.uba.ar/investigacion/…` (research, score 10) and `uba.ar/becas-grado`; the homepage's "Carreras de Grado" link → `uba.ar/facultades` (categorise None, label matches no field word) was not followed. Search at 37 s (SB-1b): leads read `qpl2024.dc.uba.ar/abstracts/75.pdf`, `lafhis.dc.uba.ar/~ezoppi` (robots), `licar.dc.uba.ar/`, `cms.dm.uba.ar/…/Kevin Houston - How to Think Like a Mathematician` (8.7 s), `robotica.dc.uba.ar/en/members`, `fscd2021.dc.uba.ar`, `bibliotecadigital.exactas.uba.ar/…` — research/lab pages that contain the English words. The gold host `ingresantes.exactas.uba.ar` never appears. Its `wp-sitemap-posts-page-1.xml` lists 38 pages including the gold (hand check). Offline the gold page is **UNKNOWN** today (no degree word: "Licenciatura") and `program_detail`/accepted with LX-1 (`licenciatura` + the settled plural alias "ciencias de la computación"). |

### 1.3 dev3 misses

| case | gold | stage | what the captures show |
|---|---|---|---|
| imperial | `…/undergraduate/computing-beng/` and `…/undergraduate/2027/computing-beng` | **S2 → S4 (wrong programme)** | Killed at 115 s both reps (5–7 s per read). Sitemap `sitemap.xml` (+ `business-school`, `people` children) listed the 2027 catalogue; the confirm queue read, in order: two `tuition-fees---2027/group-7---mathematics-and-computer-science` tables, `mathematics-computer-science-meng`, `-beng`, `-ai-meng`, `-ai-beng`, `entry-requirements---2027/mathematics-and-computer-science-for-ai` — the per-word substring bonus ("science" +8, "computer" ≠ "computing") ranks every `mathematics-computer-science-*` and fee page above `computing-beng` (DEV3 analysis: rank 35/40). `mathematics-computer-science-meng` and `-beng` were **confirmed** (IM-1 landed after this capture), the walker was skipped ("stop when confirmed") and one query went out at 66 s. The gold was never read. Not a language problem: ranking + slow host; SR-1 (`FIELD_SLUG_SCORING`, off) is the built fix. |
| unsw (rep 2) | `unsw.edu.au/study/undergraduate/bachelor-of-computer-science` | **S2 → S4** | Rep 1 read the gold as the first search lead at t=22 s and confirmed it (hit). Rep 2's first two leads were `bachelor-of-science-in-computer-science-bengaluru` (refused by CG-1) and `bachelor-of-commerce-computer-science` (a double degree, **confirmed**: no "double degree" word in its slug or title), after which recovery stopped ("stop when confirmed") and the gold, if returned, was never read. 9–10 s per read; `news.sitemap.xml` took 11–19 s and the `study/undergraduate.sitemap.xml` child was never reached. |
| iitd | `homecse.iitd.ac.in/b-tech-program/` | **S3** (rep 2) / **S2** (rep 1) | Rep 2 read the gold at t=50 s and rejected it: `reads as unknown, not a programme page` — `_DEGREE_WORDS` has no B.Tech (LX-1 has it, off); CSE is also `related_not_equivalent`. Rep 1's eight recovery reads were `cse.iitd.ac.in/~suban/CSL102`, `COL100/index.html`, `homecse.iitd.ac.in/ms-program`, `/all-courses` (catalog), `/col100-…`, a maths PDF, two department roots — the gold did not make the eight. Sitemap: 1 URL. |
| kuleuven | `onderwijsaanbod.kuleuven.be/opleidingen/n/SC_51016742.htm` (Dutch) | **S0** | `www.kuleuven.be/robots.txt` ConnectTimeout (10 s) → fail-closed on every `*.kuleuven.be` host; 14 refused reads. Mechanism if unblocked (offline on the saved gold): classifies `intake_specific_program`, degree bachelor, subject "Bachelor in de informatica (Leuven) - Studieprogramma" → **refused by `_matches_field_text_localized`**: `informatica` (nl) is a settled alias, but "leuven" and "studieprogramma" are not filler. URL `/opleidingen/n/SC_51016742.htm` scores 0 (`/(opleidingen|…)/[a-z-]{4,}` needs a 4-letter slug right after; the segment is `n`). |
| auckland (on arm) | `…/find-a-study-option/bachelor-of-science-bsc.html`, `study.auckland.ac.nz/…/plan?p7_code=COMP-BSc` | **S4** | With FI-1 the CS pages `computer-science/undergraduate/bsc-compsci-from-2019.html` and `computer-science/undergraduate.html` are no longer read as a scholarship index and are confirmed first (t=10 s and 39 s); QB-1 then caps search, so the `plan?p7_code=COMP-BSc` page the off arm found by search is never reached. Gold accepts the BSc page and the plan page, not the CS-major pages. Label question (DEV3 analysis Fix D), not discovery. |
| puc | `admision.uc.cl/carreras/licenciatura-en-ingenieria-en-ciencia-de-la-computacion/` (Spanish) | **S1** | `www.uc.cl/sitemap.xml` (21 s, slow host → search first, walker skipped): 247 URLs, 3 kept (`/en/keywords/academic-programs`, `/en/strategic-axis/…`, `/en/keywords/admission`); the catalogue host `admision.uc.cl` is not in it. Search leads read: `ing.uc.cl/en/major-en-computacion-y-sistemas-de-informacion` (unknown), `dcc.uc.cl/` (unknown), two `cargosacademicos.uc.cl/en/oferta/call-for-applications-…` vacancies, `doctorados.uc.cl/en/programa/doctor-in-engineering-sciences-computer-science-area` (15–20 s), `uc.cl/noticias/…phd-program` (prefilter: master/phd). All English pages that contain "computer science". The homepage links "Carreras de pregrado → `admision.uc.cl/carreras/`" (106 links, the gold is labelled "Licenciatura en Ingeniería en Ciencia de la Computación") and `admision.uc.cl/carreras-sitemap.xml` lists 71 programme URLs including the gold (hand checks) — neither is reachable by any current stage: `categorise_url("https://admision.uc.cl/carreras/")` is None, `looks_like_catalogue` False. Offline the gold page is **UNKNOWN** today (no "licenciatura" degree word); with LX-1 it is `program_detail`/bachelor and then **refused on subject**: "ingenieria" is not filler and "ciencia de la computación" (singular) is LX-1-only. |
| uio | `uio.no/studier/program/informatikk-programmering/` (Norwegian) | **S1 (+ D1)** | Sitemap index has 18 relative children; the reader took the first five (`globe`, `hf`, `jus`, `med`) under the 13-document allowance; `sitemap-www.uio.no-{0,1,2}.xml` are children 16–18. Hand check of those three: **the programme pages are not in UiO's sitemaps at all** (1 `/studier/program/` URL in 18 MB; `informatikk` appears only in course material). 104 kept URLs; the three slots went to `hf.uio.no/studier/karriere/underveis/praksis/ba/*`; **no discovery query was sent (D1)**; the walker walked `med.uio.no/imb/english/about/hse/courses/first-aid-course`. The homepage links "Studier → `/studier/`" (categorise None); `/studier/program/` ("Finn studier", 428 links, categorise `program_catalog` 5) is one hop further and lists the gold as "Informatikk: programmering og systemarkitektur (bachelor)". Offline the gold page classifies `program_detail`/bachelor and is **refused on subject** ("programmering", "systemarkitektur" are not filler; `informatikk` is LX-1-only). |
| ub | `www.ub.edu/grad/infes/fitxaInfe.jsp?…&ens=TG1148` (Catalan plan page) | **S0** | `sitemap/sitemap.xml` 20.8 s, `sitemap_443.xml` 21 s timeout → `www.ub.edu` marked stalled; every `web.ub.edu` lead 403 (Cloudflare challenge): `…/w/infograu-bachelordegree-g1077`, `…/treball-final-de-grau-enginyeria-informàtica`. Not fixable without bypassing. |

Cases without a gold URL (kaznu, tec, msu, utokyo, ntutw, usp, khalifa, uct) do not count in recall but
show the same shape: KazNU's `www.kaznu.kz` is unreachable from the runner (and from this sandbox); the
reachable `welcome.kaznu.kz/en/education_programs/bachelor/speciality/2546` and `/1730` were read and refused
because their h1 is the site title "Bachelor — Admissions 2026" (the page's API call failed: "adapi
GetSpecialityById returned HTTP 500" in the saved HTML — site-side). Tec's `tec.mx/en/engineering-and-sciences/bs-in-
computer-science-and-technology` was returned twice and rejected `irrelevant` (title-level rule; worth a look,
not a language issue). MSU's leads were `asvk.cs.msu.ru` course pages; NTU Taiwan's `csie.ntu.edu.tw/en/
Education/*` (unknown/catalog); UTokyo's `i.u-tokyo.ac.jp/edu/course/cs/index_e.shtml` (catalog) and a PDF
`too_large`; USP confirmed `icmc.usp.br/en/admission/undergraduate/computer-science` (English). In every one of
these the local catalogue is one or two homepage hops away (§2.3).

## 2. Question 2 — local-language universities: queries, identity, LI-1

### 2.1 Do the discovery queries ever use the local-language programme name? **No, never.**

`intent._field_terms` returns the applicant's field quoted (`"computer science"`); with QA-1 (off) it would
add the ontology's *strong* aliases only (`computing science`, `computing`, `informatics`). `queries_for` has
no language input: `DiscoveryIntent` carries institution, domain, degree, field, intake year, population
marker — no country and no language. The ontology's `localized_aliases` are read by `with_strong_aliases`
(URL and link-text matching) and `retrieval_candidates` (ranking: BM25 terms are strong aliases only; the
`strong_alias_in_title` +3 counts settled localized aliases fi/de/nl/pl/fr/ru, not the flagged it/cs/sv/es/pt
or LX-1 no/da/ca/es), **never by the query generator** (LI-1's docstring says so explicitly: "never the strong
aliases or the query terms"). `_degree_in_words`/`_degree_aliases` are English. The institution name is the
only non-English token that can appear (q2: "Pontificia Universidad Católica de Chile …", "Universidade de
São Paulo …"), and it is the seed's canonical name, not a programme word.

Consequence, visible in every local-language capture: the recovery reads are the English pages on the domain
that contain the quoted words — research groups, labs, vacancies, doctoral pages, English course pages
(puc, uba, msu, kaznu, tsinghua, ntutw, utokyo above). Whether Serper would have returned the Spanish or
Norwegian programme page for an English quoted query is unknowable from the captures; what is certain is that
no query asked for it.

### 2.2 Does identity confirmation accept a local-language title?

Only under narrow conditions. `profile_rejects` needs (a) `classify_page` to return `PROGRAM_DETAIL` or
`INTAKE_SPECIFIC_PROGRAM`, which needs a degree word — `_DEGREE_WORDS` are English (bachelor/bsc/ba/beng/
llb/undergraduate; LX-1 adds B.Tech, licenciatura, "grado en", "bachillerato en", bachelor-compounds; nothing
for fr `licence`, it `laurea`, pl, cs, tr, ru, kk, ja, zh, ko, th) in the identity, or in the title/path via
`_program_name_from_context` (path slugs do include `licence`, `licenciatura`, `laurea`, `lisans`, `bakalar*`,
`grado`, `kandidat` on `.se`); and (b) `_matches_field_text_localized` to accept the subject: a localized
alias from the ontology (settled: fi/de/nl/pl/fr/ru; LI-1-flagged: it/cs/sv/es-plural/pt; LX-1-only:
no/da/ca/es-singular) as whole folded words, with every other word in `_TITLE_FILLER ∪ _LOCAL_TITLE_FILLER`.

Offline on the real pages (`pd_tools/predicates.py`), today's defaults (LI-1 on, LX-1 off) vs LX-1 on:

| page | `<html lang>` | classify today | reject today | with LX-1 |
|---|---|---|---|---|
| psaclay fr `/formation/licence/informatique` | fr | **UNKNOWN** (no degree word; "licence" unknown to both tables) | not a programme page | same |
| psaclay en twin | en | program_detail "Informatique"/bachelor | **accepted** | accepted |
| uba `ingresantes…/licenciatura-en-ciencias-de-la-computacion/` | es-AR | **UNKNOWN** | not a programme page | program_detail, **accepted** |
| kuleuven `opleidingen/n/SC_51016742.htm` | nl | intake_specific "Bachelor in de informatica (Leuven) - Studieprogramma" | **subject refused** ("leuven", "studieprogramma") | same |
| ucph da `/studier/bachelor/datalogi` | da-DK | intake_specific "Bachelor i datalogi" | **subject refused** (datalogi is LX-1-only) | **accepted**; `english_alternate` → `/studies/bachelor/computer-science` |
| uio `/studier/program/informatikk-programmering/` | no | program_detail "Informatikk: programmering og systemarkitektur" | **subject refused** | still refused ("programmering", "systemarkitektur") |
| puc `admision.uc.cl/carreras/licenciatura-en-ingenieria-en-ciencia-de-la-computacion/` | es | **UNKNOWN** | not a programme page | program_detail; **subject refused** ("ingenieria") |
| kaznu `welcome.kaznu.kz/en/…/speciality/2546` | en | program_detail "Bachelor — Admissions 2026" | subject refused | same (site-side) |

So: **a local-language title is accepted today only when the page states its level in an English word and
its title is exactly `<alias> + filler`** (e.g. "Informatik Bachelor of Science", "Informatique" with
`/licence/` in the path). None of the seven development local pages passes; two pass with LX-1 (uba, ucph-da),
two more would need a subject-head rule (uio, kuleuven), one a policy call on "Ingeniería en Ciencia de la
Computación" (puc), one a French degree word (psaclay-fr).

### 2.3 What LI-1 (`LOCALIZED_IDENTITY`, on) does, and where it stops short

LI-1 (live_discovery L230–253, 1023–1040, 1117–1300, 1360–1500, 2730–2790, 3478–3484) does three things:
(i) `with_strong_aliases` adds the ontology's localized aliases to URL/link matching (`matches_field` whole
slug word, `_matches_field_text_localized` any script, accents folded) and `_LOCAL_TITLE_FILLER` adds local
level/form words; `_LOCALIZED_PROGRAM_SIGNALS` scores `/(studienangebot|studiengaenge|corsi-di-laurea|
carreras|grados|titulaciones|formations|utbildningar|studijni-programy)/<slug>` as programme paths (+3);
`_localized_degree_level` reads local degree slugs (`laurea`, `lisans`, `bakalar*`, `grado`, `magister`,
`mestrado`, `kandidat` on `.se`, compounds `laurea-magistrale`, `yuksek-lisans`); (ii) `matches_field_text`
accepts a localized alias as the subject under the filler rule; (iii) a programme candidate read on the
institution's domain whose `<html lang>` is not English and that declares `<link rel=alternate hreflang=en>`
on the same registrable domain has that twin queued next (`_queue_english_alternate` in `_confirm_programs`,
and inline in `_recover_search_pages`).

Where it stops short, with the development evidence:

1. **Queries** — untouched (§2.1). LI-1 can only recognise a local page some other stage already produced.
2. **Reaching the local page** — the sitemap signals cover 11 catalogue words and nothing for `formation/`
   (psaclay: categorise None), root-level slugs (uba), opaque codes (`/opleidingen/n/SC_….htm`), or
   `/studier/program/<slug>` (handled only by the English `programs?` rule, +4 — below any English
   bachelor/BSc URL on the same sitemap). Catalogue roots in local words (`/carreras/`, `/studier/`,
   `/opleidingen/n`, `/formation`, `/studier/bachelor`, `本科专业`) are not `PROGRAM_CATALOG` for
   `categorise_url`, `looks_like_catalogue` or `_CATALOGUE_PATH`, so the navigation fallback and the walker
   never enter them; the homepage harvest keeps a link only when its *URL* categorises or (on a catalogue
   page) its label names the field — a label "Carreras de pregrado", "Studier", "Opleidingen",
   "学部・大学院等", "本科专业" is dropped. Hand check of the homepages (`pd_pages/`, `links.py`): uc.cl →
   `admision.uc.cl/carreras/`; uio.no → `/studier/` → `/studier/program/`; uba.ar → `/facultades`;
   ku.dk → `/studier/bachelor`; universite-paris-saclay.fr → `/formation/choisir-sa-formation`;
   tsinghua.edu.cn → `/jyjx/bksjy/bkzy.htm` ("本科专业") and `join-tsinghua.edu.cn` ("本科生招生");
   u-tokyo.ac.jp → `/ja/schools-orgs/faculties/faculty.html` ("学部"); ntu.edu.tw → `/academics/academics.html`
   ("教學"); usp.br → `/ensino/graduacao/` ("Graduação"). Every one is a one- or two-hop local catalogue
   entry the current fallback cannot take.
3. **Reading the local page** — the classifier's degree words are English (plus LX-1's Spanish/Indian set,
   off). `licence`, `laurea`, `lisans`, `bakalář`, `бакалавриат`, `学部/本科/학부`, `ปริญญาตรี`, `bakalaureus`,
   `bakalauras` exist nowhere in page-text tables; `laurea`/`lisans`/`bakalar` exist only as URL slugs.
4. **Accepting the local title** — the filler rule has no head-before-colon/dash rule (uio "Informatikk:
   programmering og systemarkitektur"; kuleuven "… (Leuven) - Studieprogramma"), no domestic-campus rule
   (CG-1 knows campuses *abroad*; a city in the institution's own country is still a foreign word to the
   matcher), and the alias set is thin: 11 languages have an entry, half of them flag-gated; tr, et, lt,
   kk, ja, zh, ko, th have none.
5. **hreflang** — followed only local → English, only after the local page was read, only from a programme
   candidate (never from the homepage or a catalogue), and never recorded as an alias of the confirmed page
   (D2). English → local is never followed, so a university whose *English* page is a stub and whose local
   page holds the content stays on the stub.
6. **Ranking** — `rank_candidates` gives `strong_alias_in_title` only for settled aliases and BM25 terms
   from English aliases, so a Spanish/Norwegian/Turkish/Czech programme title ranks below any English page
   whose snippet says "computer science"; with 8 recovery reads that is decisive (puc, uba above).

## 3. Question 3 — the three changes most likely to raise programme-page recall on unseen, mostly
## non-English universities

Ranked by how much of the §1/§2 mechanism each removes, with the constraint that no change is tuned to a
listed case: every lexicon entry is a dictionary translation of "computer science" / "bachelor" / the
listing word, every rule is a language-general rule, and the development cases are the *check*, not the
source. The heldout nine's countries publish in kk/ru, tr, cs, de, et, it, lt (public fact); today the
ontology has one alias for de, cs (flagged), it (flagged), ru, and **none for tr, et, lt, kk**; the
classifier has no local degree word for any of the seven. That gap is what the three changes close, and it
is closed the same way for every language, which is the only honest route to "not fitting to a case".

Budget and policy invariants hold throughout: no new network path (every read is a `Fetcher.get`, robots
obeyed, no UA change, no proxy); no applicant attribute in any query — the language comes from the
**institution's** country (`entry["country"]`, registry/seed data, already in `trace.country` for CG-1) and
the words from the bundled ontology; 6 queries (a family is *replaced*, not added), 60 reads (LC-1 adds at most
3 discovery reads inside `DISCOVERY_READ_CAP = 28`), 120 s.

### Change 1 — LI-2: accept a local-language programme page (prerequisite for the other two)

Flag `LOCALIZED_PAGE_IDENTITY` (`page_classifier.py`, `live_discovery.py`; harness `--localized-page-identity`).
Without it, pages that Change 2 or 3 reach are refused (§2.2: 7 of 7 development local pages).

Design:
1. **Degree words per language in page text** — `page_classifier._LOCALIZED_DEGREE_WORDS` (bachelor and
   master both, so a master's page is never read as a bachelor's): es `licenciatura|grado en|bachillerato
   (en|universitario)` / `maestría|magíster|máster`; fr `licence (en|de|d'|professionnelle)?|licence\b` only
   when `<html lang>` is fr (the English word "licence" otherwise) / `master`; it `laurea triennale|corso di
   laurea\b(?!\s+magistrale)` / `laurea magistrale`; pt `bacharelado|graduação` / `mestrado`; nl `bachelor
   (in de|of)` (English word, already), `masteropleiding|master in de`; da/no/sv `bachelor|bachelorprogram|
   kandidatprogram (sv only)` / `kandidat (da)|master`; de `bachelorstudium|bachelorstudiengang` (LX-1 has) /
   `masterstudium`; pl `studia pierwszego stopnia|licencjackie|inżynierskie` / `drugiego stopnia|
   magisterskie`; cs/sk `bakalářsk\w+|bakalársk\w+` / `magistersk\w+|navazující`; tr `lisans` (not preceded by
   `yüksek`/`ön`) / `yüksek lisans`; et `bakalaureuse\w*` / `magistri\w*`; lt `bakalauro` / `magistrantūros|
   magistro`; ru/kk `бакалавриат|бакалавр` / `магистратура|магистр`; ja `学部|学士` / `大学院|修士`;
   zh `本科|学士` / `研究生|硕士|碩士`; ko `학부|학사` / `대학원|석사`; th `ปริญญาตรี` / `ปริญญาโท`. Read by
   `_degree_level` (earliest match wins, as today) and `_program_name_from_context` (path and title).
   LX-1's part (i) is the Spanish/Indian subset of this; LI-2 generalises it and is measured on its own.
2. **Subject head rule** in `_matches_field_text_localized`: when the whole identity fails, test the head
   before the first `:`, ` – `, ` - `, ` | ` and the identity with a trailing parenthesis removed when the
   parenthesis names a place in the institution's country (reuse CG-1's `foreign_campus_named` inversely:
   a place that is *not* abroad is filler) or a level word; and add the local form words `studieprogramma|
   studiengang|programa de estudios|plan de estudios|studieprogram|opleiding|formation|corso|
   программа|学科|학과` to `_LOCAL_TITLE_FILLER`. "Informatikk: programmering og systemarkitektur" →
   head "Informatikk" → alias; "Bachelor in de informatica (Leuven) - Studieprogramma" → "Bachelor in de
   informatica" → alias. "Wirtschaftsinformatik", "Bioinformatik", "Ingegneria Informatica" stay refused
   (one compound word; a subject word that is not filler).
3. **Alias coverage** — `ontology.json` `localized_aliases` for computer_science, dictionary-grade, each
   flagged `LOCALIZED_PAGE_IDENTITY` until measured: no `informatikk`, da `datalogi`, es `ciencia de la
   computación` (promote the three LX-1 entries), tr `bilgisayar bilimleri`, et `informaatika`, lt
   `informatika`, kk `информатика`, ja `情報科学`, zh `计算机科学与技术|計算機科學`, ko `전산학|컴퓨터과학`,
   th `วิทยาการคอมพิวเตอร์`; and `related_not_equivalent` local forms so they are refused by name rather
   than by luck: `ingeniería informática|enginyeria informàtica|ingegneria informatica|bilgisayar
   mühendisliği|计算机工程|컴퓨터공학|technische informatik|informatique industrielle`. Owner decisions to
   record (not guessed here): Chile's "Ingeniería en Ciencia de la Computación" (PUC's bachelor *is* the
   CS degree; a CL-specific alias or a rule "ingeniería en <alias>" → alias), Taiwan's 資訊工程 (CSIE),
   India's CSE — all three are the same `related_not_equivalent` question the owner already decided for
   IIT Delhi.
4. **hreflang both ways and recorded**: `english_alternate` also returns the *local* alternate of an English
   programme candidate (`hreflang` = the institution country's language) so the local page is queued
   when the English one is a stub; and every confirmed page's same-domain `hreflang` alternates are kept on
   the trace as `programme_url_aliases` (feeds §4).

Expected development effect (offline, `predicates.py`): uba, ucph-da, uio, kuleuven pages become accepted
(puc with the owner's alias decision); psaclay-fr with the fr degree word. **No programme-page recall gain
by itself** on today's captures — none of these pages is reached today — but zero loss is the thing to
measure, and it is the gate for Changes 2 and 3. Precision risks: a local master's page read as bachelor
(mitigated by adding master words in the same table, earliest-match rule); an alias that names a
neighbouring field (`informatica` is CS in it and nl; `informática` in es is also "IT" — keep es on
`ciencia(s) de la computación` only; `informatics`-style aliases stay out of tr/et/lt where the word means
IT); extraction on a non-English page — the English-regex extractors (IELTS/deadline/tuition) mostly find
nothing there, so the risk is a wrong-scope number from a stray English table; `claim_precision` and
`wrong_scope_claim_rate` are the guards. Measure: paired run on cohort/dev2/dev3; required no stable loss,
0 new wrong claims; offline unit tests on the eight saved pages (both outcomes per flag).

### Change 2 — LQ-1: one local-language query family in the first pass

Flag `LOCAL_LANGUAGE_QUERIES` (`intent.py`, `retrieval.py`, `prefilter.py`; harness `--local-language-queries`).

Design:
1. **Institution language** — a static `country → publication languages` table (ISO codes; one file beside
   `ontology.json`, e.g. `languages.json`: Chile/Argentina/Mexico/Spain → es (Spain + ca), Norway → no,
   Denmark → da, Belgium → nl, fr, France → fr, Netherlands → nl, Sweden → sv, Finland → fi, Germany/
   Austria/Switzerland → de, Poland → pl, Czechia → cs, Italy → it, Turkey → tr, Estonia → et, Lithuania →
   lt, Kazakhstan → kk, ru, Russia → ru, Japan → ja, China → zh, Taiwan → zh, Korea → ko, Thailand → th,
   Brazil/Portugal → pt). `DiscoveryIntent` gains an optional `languages: tuple[str, ...]` filled from
   `entry["country"]` (institution data, validated like every other field; never from the profile).
2. **The query** — `queries_for` emits, when the institution has a non-English language for which the
   ontology holds a computer_science alias, `site:{domain} "{alias}" {local bachelor word}` (first alias
   and first bachelor word per language, e.g. `site:uc.cl "ciencia de la computación" licenciatura`,
   `site:uio.no informatikk bachelor`, `site:uba.ar "ciencias de la computación" licenciatura`,
   `site:kuleuven.be informatica bachelor`), family `local_language`, **in place of `programmes`** in the
   first pass (so pass 1 = field_and_degree, natural_language, local_language; `programmes` moves to pass 2
   ahead of `courses`). English-country institutions are untouched (byte-identical plan). Still six
   families, still `SHARED_QUERY_BUDGET`; the local bachelor words come from a new `degrees.bachelor.
   localized_aliases` list in the ontology (the same words as Change 1's tables, as single query terms:
   es licenciatura, fr licence, it "laurea triennale", pt graduação, pl licencjat, cs bakalářské, tr lisans,
   et bakalaureuseõpe, lt bakalauro, ru/kk бакалавриат, ja 学部, zh 本科, ko 학부, th ปริญญาตรี; nl/da/no/sv/de
   bachelor).
3. **Ranking and prefilter aware of the family** — `rank_candidates` counts a localized alias (flagged
   included) as `strong_alias_in_title` for candidates whose `found_by` includes `local_language`, and adds
   the alias's tokens to the BM25 terms for them; `names_other_degree_level` learns the local master slugs
   (`maestria|master-s|masterstudium|masterprogramma|magistratura|магистратура|yuksek-lisans|magistri|
   magistrantura|修士|硕士|碩士|석사`) so wrong-level local pages do not take the eight reads.
4. **Trace** — record the family of each recovery lead (`found_by`) and the per-family candidate count in
   `errors`, so the next analysis can say which family found the page (the §0 limit).

Expected development effect, conditional on Change 1 and stated as expectation (no provider here): the
three local gold pages whose *titles* carry the query terms — uba "Licenciatura en Ciencias de la Computación :
Ingresantes", puc "Licenciatura en Ingeniería en Ciencia de la Computación", uio "Informatikk: programmering
og systemarkitektur (bachelor)" — are what a `site:` keyword query on those words is built to return; the
same holds for the KazNU, MSU, Tsinghua, UTokyo, NTU-TW, USP, Tec local catalogues (no gold URL). UiO also
needs D1 fixed (§3, Change 3 item 4) or no query goes out at all. Cohort: the only non-English cohort cases
without a confirmed page before search are aalto (robots) and kaist (ko alias; the gold's identity problem
stays) — no expected change; vienna/warsaw/groningen/delft confirm before search (QB-1b), so their query
plan change is unobservable. Precision risks: the provider returns local *news* or course pages carrying the
alias (prefilter path exclusions already cover `/news|/noticias|/nieuws|/actueel`; add `/nyheter|/nyheder|
/aktuelt|/aktualnosci|/aktuality|/haberler|/uudised|/naujienos|/новости|/жаңалықтар|/ニュース|/新闻|/新聞`
to `_URL_EXCLUSIONS`); a local master's page confirmed as bachelor (Change 1's master words + item 3);
every claim still goes through the unchanged verify stage. Measure: paired run on cohort/dev2/dev3 with
Change 1 on in both arms; required: no stable programme-page loss, 0 new wrong claims, `cases_over_budget`
0, and the new per-family trace line showing `local_language` candidates read.

### Change 3 — LC-1: the local catalogue as an entry point (homepage section links, local listing URLs,
### the catalogue host's own sitemap), plus the D1 fix

Flag `LOCAL_CATALOGUE_ENTRY` (`live_discovery.py` `_navigation_fallback`, `_URL_SIGNALS`, `_CATALOGUE_PATH`,
`SitemapReader`; `catalog_walker.py`; `navigation.py` `_SECTION_WORDS`; harness `--local-catalogue-entry`).

Design:
1. **Section-link lexicon per language** (navigation.py already does this for Korean 교육/교과과정 and
   `_ADMISSION_WORDS` for 20 languages under ER-05): a homepage/section link whose *label* is a study-section
   or catalogue word becomes a `PROGRAM_CATALOG` lead (score 4, recorded in `kept_by_link_text`, read and
   classified like any lead) even when its URL categorises as nothing: es `carreras|carreras de (grado|
   pregrado)|oferta académica|estudios|admisión`, fr `formation(s)|choisir sa formation|offre de formation`,
   it `corsi di laurea|offerta formativa|didattica`, pt `graduação|cursos de graduação|ensino`, nl `opleidingen|
   onderwijsaanbod|studeren`, da `uddannelser|studier|bachelor`, no `studier|studieprogrammer|finn studier`,
   sv `utbildning(ar)|program och kurser`, de `studienangebot|studiengänge|studium`, pl `kierunki studiów|
   oferta kształcenia|kandydaci`, cs `studijní programy|studium|uchazeči`, tr `bölümler|programlar|lisans
   programları|aday öğrenciler`, et `õppekavad|sisseastumine|õppimine`, lt `studijų programos|stojantiesiems|
   studijos`, ru/kk `образование|образовательные программы|бакалавриат|абитуриентам|поступление|білім беру
   бағдарламалары|оқу бағдарламалары|қабылдау`, ja `学部|学部・大学院|入学案内`, zh `本科专业|本科生教育|
   招生|教學|大學部`, ko `교육|학부|입학`, th `หลักสูตร|คณะ|การรับเข้าศึกษา`. Two hops at most from the
   homepage (homepage → section → catalogue), inside `MAX_FALLBACK_PAGES = 5` and the SB-1 budget.
2. **Local listing words in URL signals** — `_URL_SIGNALS[PROGRAM_CATALOG]` and `_CATALOGUE_PATH` learn the
   slug forms of the same words (`/(carreras|grados|titulaciones|pregrado|formation|formations|
   corsi(-di-laurea)?|offerta-formativa|graduacao|cursos|opleidingen|onderwijsaanbod|studier|studieprogram
   (mer)?|uddannelser|utbildning(ar)?|studienangebot|studiengaenge|kierunki|studijni-programy|bolumler|
   programlar|oppekavad|studiju-programos|obrazovanie|bakalavriat|programmy)/?$` and `/opleidingen/[a-z]$`),
   and `_URL_SIGNALS[PROGRAM_PAGE]` the matching `/<word>/<slug>` forms (`/(formation|carreras?|grados|
   opleidingen|studier/program|uddannelser|cursos|corsi-di-laurea|programy|studijni-programy|bolumler|
   oppekavad|programos|bakalavriat)/[^/]{4,}`), extending LI-1's `_LOCALIZED_PROGRAM_SIGNALS`.
3. **Catalogue host sitemap** — when the homepage or a section page links a host on the same registrable
   domain whose label or path is a catalogue word (`admision.uc.cl`, `onderwijsaanbod.kuleuven.be`,
   `ingresantes.exactas.uba.ar`, `informatorects.uw.edu.pl`), `SitemapReader` reads that host's `robots.txt`
   sitemap (or `/sitemap.xml`, `/wp-sitemap.xml`) for at most 3 documents, preferring children whose name
   carries a programme word in any language (`carreras|programas|opleidingen|studier|formation|…`; the
   SM-1 idea, applied only to the catalogue host), inside `DISCOVERY_SITEMAP_ALLOWANCE`. Hand checks:
   `admision.uc.cl/carreras-sitemap.xml` = 71 URLs with the gold; `ingresantes.exactas.uba.ar/wp-sitemap-posts-
   page-1.xml` = 38 with the gold.
4. **D1 fix (bug, on by default once tested)** — `_add_search_results` counts only `self._confirmed` pages
   as filled slots when SB-1 is on (an unconfirmed sitemap lead is not a reason to skip search), and
   `search_now()` sets `searched_early` only when a query was actually sent (`trace.search_queries_sent`
   grew), so a refused early search is retried after the walker as before SB-1b.

Expected development effect (with Change 1): puc — homepage "Carreras de pregrado" → `admision.uc.cl/
carreras/` (106 links; the gold link's label passes the subject rule only with the owner's alias decision) or
the carreras sitemap (71 URLs, gold scores `program_page` 3 + field 16 + degree 4 = 23 under today's
`matches_field`, highest on that host); uio — "Studier" → `/studier/` → "Finn studier" `/studier/program/`
(428 links; label "Informatikk: programmering og systemarkitektur (bachelor)" → walker `score_link` ≥ 8+4 with
the head rule) and D1 restores its six queries; uba — "Carreras de Grado" → `/facultades` is a faculty list,
the exactas catalogue is two more hops away (`exactas.uba.ar/ensenanza/carreras-de-grado/`, label "Ciencias de
la Computación" already passes `matches_field_text` today) — reachable only through the catalogue-host
sitemap if `ingresantes.` is linked from a page we read, otherwise this is Change 2's case; kuleuven (if the
runner is ever unblocked) — `onderwijsaanbod.kuleuven.be/opleidingen/n` is linked from the homepage and has an
English switch `/opleidingen/e`; tsinghua — "本科专业" → `tsinghua.edu.cn/jyjx/bksjy/bkzy.htm` is the
majors list on the main domain (the gold is on `international.join-tsinghua.edu.cn`, DI-1's case). No gold,
same shape: utokyo "学部", ntutw "教學"/"招生", usp "Graduação", msu, kaznu. Precision risks: more catalogue
reads on slow hosts (bounded by SB-1 and the 2-hop rule; the walker already stops when confirmed); a
"carreras" label on a careers page (es: the university sense dominates; the page is classified before it
counts and a non-catalogue is dropped as today — `not_program_catalog`); a local catalogue listing another
faculty's "informática" programme (the confirm predicate and FS-1 are unchanged). Measure: paired run on
cohort/dev2/dev3 (Change 1 on both arms); required no stable loss, 0 new wrong claims, reads per case not
above today's, and D1 verified by `discovery_query_passes` present for every reachable case (uio: 0 → 6).

### Not in the top three

- **National registries / official catalogues off the institution's domain** (Parcoursup, samordnaopptak.no,
  ug.dk, DEMRE/mifuturo.cl, antagning.se, Studiekeuze123, Hogeronderwijsregister, RUCT): they would need a
  new network path outside `same_institution` and a per-country adapter each; the prefilter would reject
  their URLs as `other_institution`; and every one is third-party content, which the brief's evidence rules
  (official site, verbatim) exclude as a source. As a *lookup* for the official programme URL they are
  possible later, behind `Fetcher`, but they are the most work for the least generality.
- **DI-1 (second admissions domain from the homepage)** — Tsinghua's and KazNU-type sites; built and off;
  re-measure after Change 2 gives topic search a reason to run on the second domain (structural analysis §3).
- **SR-1 ranking / slow hosts** — imperial, unsw, ubc; not language problems; already proposed.
- **Site access** — aalto, toronto, kuleuven, ub, hku admissions, kaist admissions, kaznu www: Track E.

Order: Change 1 first (zero expected gain, zero expected loss, unlocks the rest), then Change 3's D1 fix
alone (it is a bug), then Change 2, then Change 3's catalogue items. Each a paired run on cohort/dev2/dev3;
the heldout nine are run **once**, after the three are on by default, and never used to tune an alias.

## 4. Measurement prerequisites (no pipeline risk)

1. **Record query families and provider result URLs** (public URLs only, no applicant data): the trace keeps
   `found_by` per recovery lead and, per family, the first 10 URLs the provider returned. Without it the
   §0 limit stays and "never seen" cannot be split into "not returned" and "ranked out".
2. **hreflang aliases in the scorer**: discovery records each confirmed programme page's same-domain
   `<link rel=alternate hreflang>` targets as `programme_url_aliases`; `metrics.score` counts a hit when an
   alias matches a gold URL. Alternatively widen the development gold: dev2 psaclay add
   `/en/education/licence-undergraduate-programme/informatique` (the gold's own `hreflang` partner — the
   pipeline has found it in 4/4 bundle5 repetitions and 4/4 lx1 repetitions); dev3 uba consider
   `exactas.uba.ar/ensenanza/carreras-de-grado/ciencias-de-la-computacion/` beside the ingresantes page.
3. **Persist the discovery trace at the confirm checkpoint** for killed captures (ubc, imperial, unsw show
   `stage_order: None`), as the structural analysis asked.

## 5. Evidence index

- Per-capture funnel: `scratchpad/pd_tools/rows.json` (built by `dump.py` over `runs/bundle5-*` and
  `runs/lx1-*`, heldout excluded by name); case dumps `pd_tools/detail_{cohort,dev2,dev3,nogold}_on.txt`;
  official scorecards `pd_tools/sc-bundle5-{cohort,dev2,dev3}.json` (programme_page_recall 5/10, 3/6,
  4/11 → 3/11).
- Query reconstruction: `intent.queries_for(DiscoveryIntent(institution=<seed name>, domain=<registrable
  domain>, degree=BACHELOR, field="computer science"))` for all 35 cases (run in this session; shapes
  identical, see §1).
- Predicates on local pages: `pd_tools/predicates.py` output (§2.2), pages in `scratchpad/pd_pages/`:
  `psaclay_fr_gold.html`, `psaclay_en_twin.html`, `uba_gold.html`, `kul_gold.html`, `ucph_da_gold.html`,
  `uio_gold.html`, `puc_gold.html`, `welcome_kaznu_2546.html`; catalogues `uio_studier_program.html`,
  `admision_uc_carreras.html`, `exactas_carreras.html`; homepages `uio.html`, `uc.html`, `admision_uc.html`,
  `uba.html`, `uba_exactas.html`, `kul_onderwijsaanbod.html`, `kudk.html`, `psaclay.html`, `msu.html`,
  `utokyo.html`, `ntutw.html`, `tsinghua.html`, `usp.html` (`links.py` output in §2.3); sitemaps
  `admision_uc_sitemap.xml`, `admision_uc_carreras_sm.xml`, `ingresantes_sitemap.xml`,
  `ingresantes_pages_sm.xml`, `uio_sm{0,1,2}.xml`, `uc_sitemap.xml`; earlier `scratchpad/fetched/uio_smi.xml`,
  `scratchpad/funnel_pages/kaist188.html`, `ubc.html`.
- D1: `runs/bundle5-dev3/x/uio-on/*/uio.raw.json` → `search_limitations` "Search not run at University of
  Oslo: all 3 programme-page slots were already filled…", `discovery_query_passes` absent; off arm `[3, 3]`.
  Code: `live_discovery.py` L2982–2998 (`_search_attempted`, slots check), L2583–2590 (`search_now`),
  L2616–2628.
- Code references: `intent.py` `_field_terms`, `queries_for`, `redacted_audit_record`; `serper.py`
  `_with_domains`; `retrieval.py` `rank_candidates` L204–290, `discover_candidates` L367–487;
  `prefilter.py`; `live_discovery.py` L230–253 (LI-1), L405–445 (`_LOCALIZED_PROGRAM_SIGNALS`,
  `_LOCALIZED_DEGREE_SLUGS`), L537–700 (`_URL_SIGNALS`, `_URL_EXCLUSIONS`, `_DEGREE_SLUGS`), L1117–1300
  (`matches_field`, `_localized_names`, `with_strong_aliases`, `degree_level_named`), L1352–1500
  (`looks_like_catalogue`, `matches_field_text`, `_LOCAL_TITLE_FILLER`, `english_alternate`), L1609–1650
  (`profile_rejects`), L2385–2680 (`_discover_one`, stage order), L2683–2790 (`_confirm_programs`,
  `_queue_english_alternate`), L3129–3230 (QB-1 passes), L3406–3560 (`_recover_search_pages`), L3688–3800
  (`_navigation_fallback`); `page_classifier.py` L89–101 (LX-1, FI-1), L257–275 (`_DEGREE_WORDS`,
  `_LEXICON_V2_DEGREE_WORDS`), L585–857 (`classify_page`), L879–895 (`_degree_level`), L974–1025
  (`_program_name`, `_program_name_from_context`); `catalog_walker.py` L273–310 (`score_link`);
  `navigation.py` L55–140 (`_SECTION_WORDS`, `_ADMISSION_WORDS`); `ontology.py` L99–245; `ontology.json`.
