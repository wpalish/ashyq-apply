# Where the programme page is lost today on the development sets

Type: research
Status: resolved
Blocked by: —
Map: ../map.md · AFK — resolved 2026-10-18 by claude-opus-5 from the bundle5 captures (today's defaults) and code.

## Question

Under today's defaults (SB-1, QR-1, FI-1, CG-1, FS-2, CL-1, QB-1+b, FS-1, PG-1, LI-1 on), at which discovery
stage, and by which mechanism, is the programme page lost on each development case that misses it — and what
share of the misses is design (fixable here) versus access (out of scope)? No heldout capture is opened.

## Answer

Inputs: `scratchpad/runs/bundle5-{cohort,dev2,dev3}/x/<case>-on/<stamp>/<case>.{json,raw.json,log}` (on arm,
first repetition; both repetitions agree on every programme-page outcome), `sc.md` per set, gold
`evaluation/research/data/{ground_truth.reviewed10,dev2.draft1,dev3.draft1}.json`. Scorecards: programme
page recall cohort 5/10, dev2 3/6, dev3 4/11 (`bundle5-*/sc.md`).

### Outcome per case (35 cases)

| outcome | cases | count |
|---|---|---|
| **Confirmed, labelled URL** | delft, groningen, vienna, warsaw, ntu; ethz, uppsala, tcd; um (sibling, accepted by gold), unsw, ucph (English twin, accepted by gold), chula (math.sc BSc, accepted by gold) | 12 |
| **Confirmed a page the gold does not list** | psaclay (English twin of the French `licence`), khalifa (`ku.ac.ae/program/bsc-in-computer-science`, gold unknown), usp (`icmc.usp.br/en/admission/undergraduate/computer-science`, gold unknown), auckland (`computer-science/undergraduate…`, gold lists BSc + plan page), hku (`cds.hku.hk/…/undergraduate-old-2026/6999-computing-and-data-science`, gold on the robots-refused admissions host) | 5 |
| **Confirmed the wrong programme** | uct ("Bachelor of Business Science specialising in Computer Science", sit.uct.ac.za), imperial (`mathematics-computer-science-{meng,beng}`; gold `computing-beng` sat at rank 35/40 of the confirm queue), ubc (`computer-science-vancouver-ba`; gold `-bsc`) | 3 |
| **Nothing confirmed — access** | aalto (robots.txt unreachable → fail-closed), toronto (HTTP 403 on 23/24 reads), kaist (gold host `cs.kaist.ac.kr` reachable but see below; admission host robots-refused), kaznu (robots unreachable on www; gold unknown), kuleuven (connections dropped), ub (Cloudflare challenge), tsinghua (programme on another registrable domain `join-tsinghua.edu.cn`; no sitemap; CS-department pages read as `unknown`) | 7 |
| **Nothing confirmed — local-language page never returned by the English queries** | uba (`ingresantes.exactas.uba.ar/licenciatura-en-ciencias-de-la-computacion/` never seen; 16 recovery reads were lab/PDF pages), puc (slow host 10.7 s/read, sitemap 21 s, search at 22 s, 5 reads, deadline at 64 s; `admision.uc.cl` never appears), uio (see defect below), msu (Russian; gold unknown), utokyo (Japanese; `i.u-tokyo.ac.jp/edu/course/cs` read as `program_catalog`), tec (Spanish SPA; the English `bs-in-computer-science-and-technology` page *was* returned and read and rejected "reads as irrelevant" — see classifier note) | 6 |
| **Nothing confirmed — page read, refused** | iitd (`homecse.iitd.ac.in/` root read as unknown; the gold `/b-tech-program/` is refused for want of a B.Tech degree word — [Classifier audit](10-classifier-audit.md)), ntutw (`csie.ntu.edu.tw/en/Education/*` pages read as unknown / catalogue; "CSIE Required Courses for Undergraduate" subject refused; gold unknown) | 2 |

KAIST is both: the gold `cs.kaist.ac.kr/content?menu=188` was *seen* by the walker and dropped as
`short_label` (120 of the department's links are `content?menu=N` behind short Korean labels); read by hand it
classifies `unknown` (Korean title, no English programme identity in the text).

### Where the clock goes on the misses (stage_budget.stage_seconds, on arm)

- Sitemap stage ≥ 20 s on uio (34 s, six faculty sitemaps, 76 583 URLs seen, 104 kept — all medicine/law/
  humanities), uct (20 s, 13 documents), khalifa (22 s), puc (21.5 s, one slow document). The SB-1 sitemap
  allowance (13 documents) is a read cap, not a time cap.
- Search ran on every miss except uio (defect below) and ran at or after 33 s on 11 of 35 cases.
- The two killed cases are not discovery losses: ubc read its programme page at t=58 s (BA variant) and
  imperial confirmed two pages by t≈46 s; both spent the rest of the clock in the evidence/scholarship stages
  (`imperial.log` reads at t=99–115 s are `fees-and-funding/…`), and the kill discards the trace
  ([Measurement gaps](14-measurement-gaps.md)).

### Defect found (no decision needed; hand to the loop)

**Search is skipped for the whole run when the SB-1b 33-second rule fires while unconfirmed sitemap picks
fill the slots.** `live_discovery.py`: `_discover_institution` calls `search_now()` when `_search_due()`
(nothing confirmed by `SEARCH_LATEST_START_SECONDS = 33`); `_add_search_results` then returns at once with
"Search not run …: all 3 programme-page slots were already filled by the registry, the sitemaps and the
catalogue walker" (L2985–2995) because `selected[PROGRAM_PAGE]` holds three *unconfirmed* sitemap picks — and
has already set `self._search_attempted = True`. Confirm then rejects all eight candidates, the walker finds
nothing, and the post-walker search is skipped because `searched_early` is `True`. Evidence: uio, both
repetitions: `discovery_query_passes` absent, `search_queries_sent` `None`, `stage_seconds.search = 0.01`,
`search_limitations` = the slots message, `stage_order = ['sitemaps','search','confirm','walker']`
(`bundle5-dev3/x/uio-on/*/uio.raw.json`). The same early return is *correct* on ntu and tcd, whose slots
held confirmed pages. The check must count confirmed pages (`self._confirmed`), or search must run again when
confirm empties the slots.

### Classifier note on tec

`tec.mx/en/engineering-and-sciences/bs-in-computer-science-and-technology` (returned twice, with
`?srsltid=` tracking parameters) was rejected "reads as irrelevant". The page could not be re-fetched here
(tec.mx answers plain `curl` with 403), so the firing rule is unverified; the candidates are `_IRRELEVANT`
tested on *every* heading (`low_head`, page_classifier.py L336–340 — "cookie", "contact us", "alumni",
"careers" are common footer/consent headings) — the same heading-scope defect CL-1 and FI-1 fixed for the
catalogue and funding gates. Worth one offline check once a copy of the page is obtained through the Fetcher.

### Split: design vs access

Of the 18 cases without the labelled page: 7 access (out of scope), 6 local-language query/identity (design),
3 wrong programme confirmed (design: ranking and subject guards), 2 page read and refused (design: lexicon).
With the five "confirmed, unlisted" cases, the identity rule of
[What counts as the programme page found](03-programme-identity-equivalence.md) decides whether recall reads
17/35 or 12/35 today.

### Sources

- Captures: `scratchpad/runs/bundle5-{cohort,dev2,dev3}/x/*-on/*/` (`discovery_trace.stage_budget`,
  `stage_order`, `rejected_sample`, `errors`, `search_limitations`, `walker.outcomes`).
- Code: `backend/app/adapters/discovery/live_discovery.py` L2385–2680 (`_discover_one`,
  `_discover_institution`), L2942–3000 (`_add_search_results` early return), L3117–3230 (QB-1 passes),
  L3406–3580 (`_recover_search_pages`); `backend/app/adapters/page_classifier.py` L585–660.
- Prior analyses reused, not repeated: `docs/process/STRUCTURAL_ANALYSIS_2026-10-18.md` §1–§2 (lx1 captures),
  `scratchpad/DEV3_DISCOVERY_ANALYSIS.md` (qb1b captures).
