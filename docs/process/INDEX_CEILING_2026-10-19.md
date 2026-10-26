# Own-index ceiling: are the gold and evidence pages in a sitemap, or linked? (2026-10-19)

Free-search map, ticket [04](wayfinder/free-search/issues/04-own-index-ceiling-sitemaps-and-links.md). It decides
ticket 05 (the local-index search provider).

**Verdict for 05: do not build.** The ceiling row (`in_sitemap_bounded ∪ linked_2hops`) reaches the gold
programme page in **3/10 cohort, 1/10 dev2, 6/14 dev3 and 1/5 dev4** cases. Serper returned it in 8 / 7 / 10–11 / 5
(base3, `STAGE_SUMMARY_DEV_2026-10-19.md`, row `gold_returned_by_search`). The bar was "≥ Serper, within one case",
and the ceiling misses it on **every** set, by 5, 6, 4 and 4 cases. The generous upper bound misses it too. That
bound counts any sitemap of any host the gold lives on, plus two hops, plus a declared hreflang twin, and it
cheats: it knows the gold's host. It reaches 7 / 3 / 10 / 3, which passes cohort and dev3 but not dev2 or dev4.

## How it was measured

- Tool: `backend/evaluation/research/index_ceiling.py` (tests: `backend/tests/test_index_ceiling.py`). Command, from
  `backend`: `python -m evaluation.research.index_ceiling --trust-env-proxy --concurrency 10 --out … --markdown …`.
- Every read went through the production `Fetcher`: our user agent, robots.txt with wildcards, Crawl-delay, the
  1.5 s per-host spacing and the 5 MB body cap. Nothing was retried around a refusal. No search provider was called.
- The run was from the agent sandbox, through its HTTPS proxy (`trust_env_proxy=True`), on 2026-10-19: run 3,
  137 sites, about 30 minutes. A GitHub-runner job exists as workflow mode `index_ceiling` but has not been
  dispatched. Its re-run on the self-hosted runner takes `extra_args=--refused-from <report.json>`.
- Inputs: the development gold only, meaning `ground_truth.reviewed11` (cohort), `dev2.draft3`, `dev3.draft3` and
  `dev4.draft3`. 39 cases have a programme page. The 5 `unknown` cases (utokyo, vut, taltech, boun, itu) are
  measured on their related pages but kept out of the bar. The KB side is `kb_cs_bachelor.json` plus
  `kb_imported_dev.json`: 336 (entry, URL) pairs on 98 entries, from programme URLs and evidence, `facts.*[].source_url`
  and `not_applicable[].source_url`. No heldout case was opened. The one dev5 university in the KB (LMU) counts in
  the KB aggregates only; the report keeps no row for it.
- Columns, per target URL, matched up to `metrics._page_forms` variants (trailing slash, `.htm`, intake-year segment,
  `http`→`https`):
  - `in_sitemap_bounded`: what the product's own `SitemapReader.collect` keeps from the homepage host under its
    bounds (12 documents, SM-2 trim, depth 3), with no relevance filter.
  - `in_sitemap_any`: the homepage host's sitemap tree read without cap or trim (safety stop: 150 documents, reached
    on 2 KB hosts only), plus the robots.txt-declared tree of **each target's own host**. That second part is an
    oracle: a real index would have to discover those hosts first.
  - `linked_2hops`: the homepage plus up to 59 pages it links through a study, programme, admissions or field anchor
    (`navigation._score`, `study_section_label`, the section and admission words), at most 60 reads per homepage.
  - `twin_declared`: an `hreflang` twin that the target declares is itself listed or linked.
  - `ceiling` = `in_sitemap_bounded ∪ linked_2hops` (the ticket's row). `ceiling_any` = `in_sitemap_any ∪ linked_2hops ∪
    twin_declared`.
  - `host_refused`: 403/401, robots (including "robots.txt unreachable"), crawl-delay above 10 s, or a timeout, on the
    target or the homepage.

## Table 1: development gold, per set (cases)

| set | cases with gold | in_sitemap_bounded | in_sitemap_any | linked_2hops | twin_declared | **ceiling** | ceiling_any | host_refused | Serper gold returned (base3) | bar (Serper − 1) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cohort | 10 | 1 | 4 | 3 | 3 | **3** | 7 | 2 | 8 | 7 |
| dev2 | 10 | 1 | 3 | 1 | 0 | **1** | 3 | 3 | 7 | 6 |
| dev3 | 14 | 4 | 10 | 4 | 2 | **6** | 10 | 2 | 10–11 | 9–10 |
| dev4 | 5 | 0 | 1 | 1 | 3 | **1** | 3 | 0 | 5 | 4 |

The map quotes a stricter Serper reference (dev2 9, dev3 11–12), which only widens the gap.

**Correction (2026-10-20, IC-2b).** dev2's `in_sitemap_bounded` 1 and `linked_2hops` 1 above both rested on the khalifa
row, which does not reproduce (see "Re-measure 2026-10-20" below). Without it, run 3's dev2 row reads bounded **0**,
linked **0**, ceiling **0**, ceiling_any **2** (was 1 / 1 / 1 / 3; uba and uct stay, listed on another host's sitemap). The GitHub-runner re-measure gives dev2 bounded 1 (tec, not khalifa),
linked 1 (khalifa, at hop 2), ceiling 2. The verdict for 05 does not change on either number.

Per case (any of the case's gold URLs). A hop of 0 means the gold is the homepage-level URL itself. "other host's
sitemap" means the page is listed only in the sitemap of a host other than the homepage's.

| set | case | bounded | listed anywhere (why not bounded) | linked hop | twin | refused |
|---|---|---|---|---|---|---|
| cohort | aalto | no | yes (document #13 > 12) | - | yes | - |
| cohort | delft | no | no | - | yes | - |
| cohort | groningen | no | no (1st sitemap over the 5 MB cap) | - | no | - |
| cohort | hku | no | no | - | no | robots |
| cohort | kaist | no | no | 2 | no | - |
| cohort | ntu | yes | yes | 2 | no | - |
| cohort | toronto | no | yes (other host's sitemap) | - | no | homepage 403 |
| cohort | ubc | no | yes (other host's sitemap) | - | no | - |
| cohort | vienna | no | no | 2 | yes | - |
| cohort | warsaw | no | no | - | no | - |
| dev2 | ethz | no | no (no sitemap) | - | no | - |
| dev2 | kaznu | no | no | - | no | homepage robots, timeout |
| dev2 | khalifa | ~~yes~~ no (corrected 2026-10-20, §"Re-measure") | ~~yes~~ no | ~~0~~ 2 | no | - |
| dev2 | psaclay | no | no | - | no | - |
| dev2 | tcd | no | no (no sitemap) | - | no | - |
| dev2 | tec | no | no | - | no | 403 |
| dev2 | tsinghua | no | no | - | no | - |
| dev2 | uba | no | yes (other host's sitemap) | - | no | - |
| dev2 | uct | no | yes (other host's sitemap) | - | no | - |
| dev2 | uppsala | no | no | - | no | timeout |
| dev3 | auckland | yes | yes | 2 | no | - |
| dev3 | chula | no | yes (other host's sitemap) | - | yes | - |
| dev3 | iitd | no | yes (other host's sitemap) | 2 | no | - |
| dev3 | imperial | yes | yes | - | no | - |
| dev3 | kuleuven | no | no | - | no | robots |
| dev3 | msu | no | yes (other host's sitemap) | - | no | - |
| dev3 | ntutw | no | yes (other host's sitemap) | - | no | - |
| dev3 | puc | no | yes (other host's sitemap) | 2 | no | - |
| dev3 | ub | no | no | - | no | homepage 403, 403 |
| dev3 | ucph | yes | yes | 2 | yes | - |
| dev3 | uio | no | no | - | no | - |
| dev3 | um | no | no | - | no | - |
| dev3 | unsw | yes | yes | - | no | - |
| dev3 | usp | no | yes (other host's sitemap) | - | no | - |
| dev4 | ctu | no | no | - | no | - |
| dev4 | kit | no | no | 2 | yes | - |
| dev4 | ktu | no | yes (other host's sitemap) | - | yes | - |
| dev4 | rwth | no | no | - | yes | - |
| dev4 | unibo | no | no (`sitemap.xml.gz` read as unparseable) | - | no | - |

What the 12-document bound costs: once, on aalto (document #13). The trim cost nothing on the gold, and the
product's homepage-host reader saw 70 185 cohort URLs against 99 209 unbounded. The binding limit is **which hosts**
are read, not how many documents. In 11 of 39 cases the gold is listed only in the sitemap of another host
(admissions.*, study.*, a faculty or catalogue host), and the product never reads that sitemap.

## Table 2: knowledge base, per question (distinct (entry, URL) pairs)

| question | URLs | in_sitemap_bounded | in_sitemap_any | linked_2hops | twin_declared | **ceiling** | ceiling_any | host_refused |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| programme | 132 | 17 | 54 | 9 | 10 | **23** | 65 | 26 |
| english | 68 | 9 | 28 | 13 | 2 | **19** | 36 | 10 |
| gpa | 29 | 5 | 10 | 6 | 1 | **9** | 13 | 3 |
| deadline | 41 | 5 | 16 | 11 | 1 | **14** | 24 | 10 |
| tuition | 68 | 9 | 23 | 14 | 7 | **20** | 33 | 9 |
| scholarship | 87 | 9 | 41 | 13 | 4 | **20** | 50 | 19 |
| **all** | 336 | 40 | 145 | 48 | 22 | **77 (23 %)** | 179 (53 %) | 61 |

A URL can serve more than one question, so the question rows sum to more than "all". Of the 142 listed KB URLs,
101 are listed only on another host's sitemap. 121 of the 142 carry a `<lastmod>`, and 26 of the 29 listed dev gold
pages do: useful to ticket 07 for KB re-checks driven by what changed. The refusals cover 61 URLs on 33 hosts:
39 because the homepage refuses (24 robots, 15 HTTP 403), 9 robots, 7 timeouts and 6 crawl-delays above 10 s.

## Gold pages in no sitemap and not linked within two hops

This is the class an own index cannot reach from the homepage and its sitemaps. The read outcome is the target's
own read from the sandbox.

- **Access** (the page or the homepage refuses us): hku (admissions.hku.hk and cds.hku.hk robots unreachable), kuleuven
  (onderwijsaanbod subhost robots), tec (403), ub (403 on the homepage and the page), uppsala (timeout), kaznu (homepage
  robots, page timeout).
- **Other registrable domain**: tsinghua (`international.join-tsinghua.edu.cn/Divisions1.htm`).
- **Department / catalogue host the homepage never links, and with no sitemap**: vienna's
  `aufnahmeverfahren.univie.ac.at` (reached only through a twin), warsaw's `informatorects.uw.edu.pl` and
  `irk.uw.edu.pl`, um's `study.um.edu.my` (four pages), auckland's `study.auckland.ac.nz/ords/…?p7_code=` (a
  client-rendered APEX catalogue; reached at hop 2 by another gold URL), usp's `icmc.usp.br`, ctu's `fit.cvut.cz`,
  rwth's `sc.informatik.rwth-aachen.de`, unibo's `corsi.unibo.it`.
- **Same host, deeper than two hops, and no usable sitemap**: groningen (first sitemap document is over the Fetcher's
  5 MB cap, `too_large`), delft (its one sitemap lists 219 URLs, not the programme), ethz and tcd (no sitemap;
  a menu of 25–40 links), psaclay (13 599 URLs listed, the licence page not among them), uio (195 410 URLs in 19
  documents, the programme page not among them), ntu's second URL, kit's `sle.kit.edu` page, rwth's `/cms/…/~bnzs/`
  pages, and unibo's sitemap (`sitemap.xml.gz` comes back `unparseable` from the Fetcher).
- Related pages only (unknown cases): vut, itu.

## Title / h1 test: does a text index match the R5 alias without a URL lexicon?

The test reads each development page of the 18 non-English cases (gold, or related where there is no gold) and
checks its `<title>` or first `<h1>` for `localized_aliases_in("computer science", <html lang>, flags=…)`. A page
that declares English or no language is tested in its country's languages.

| language | pages read | title/h1 names the alias |
|---|---:|---:|
| cs | 4 | 1 |
| de | 5 | 3 |
| es | 3 | 3 |
| et | 2 | 2 |
| fr | 1 | 1 |
| it | 2 | 1 |
| lt | 2 | 1 |
| no | 1 | 1 |
| th | 2 | 0 |
| tr | 4 | 0 |
| zh | 1 | 0 |

Per case with gold: dev2 2/3, dev3 2/3, dev4 5/5. Every miss is one of three kinds:
- **An English page or twin**, which the local alias cannot match: chula ×2 (all the th rows), tsinghua (the zh
  row), ctu "Informatics", rwth "Computer Science B.Sc.", kit, unibo, ktu, and itu's and boun's English twins.
- **Another field's title**: vut "Informační technologie" (it is a related programme), boun "Bilgisayar Mühendisliği"
  (engineering, not the ontology's "bilgisayar bilimleri").
- **A generic title**: itu "Genel Bilgiler".

Every gold page that is in the local language and carries a local title matched. So a text index over local titles
needs no URL lexicon for de/es/et/fr/it/lt/no/nl. It would still need the English twin indexed beside it, and an
engineering alias for Turkish. The 44 hold no Kazakh page, and too few Thai or Chinese local-language pages to judge.

## What this means for 05 and the map

- A homepage-rooted index over the official domain finds no more than about a third of what Serper found on
  development. Most of the shortfall is structural. The page sits on another host that is neither linked from the
  homepage within two hops nor listed in the homepage's sitemap (11 cases are listed only on that other host's own
  sitemap, and more on hosts with none). The site has no usable sitemap (ethz, tcd, groningen's oversized one,
  unibo's gzip). Or the site refuses us (6 cases, from this vantage point).
- Widening the index to every host a sitemap or link names still leaves dev2 at 3/10 and dev4 at 3/5, and it would
  need a host-discovery step that this measurement assumed for free.
- Close 05 as "not built" on these numbers. The useful by-products are `lastmod` coverage (good, for 07) and the
  title-alias rate (good for the Latin-script European languages, nil for th/tr/zh).

## Caveats

- The vantage point is the agent sandbox, through its proxy: some refusals (uppsala's timeout, kaznu's) are this
  vantage point's, and a GitHub or self-hosted run may open them. None of them would lift a set to its bar: even if
  every refused case became reachable, cohort reaches 5 against a bar of 7.
- Run 4, which repeats run 3 and adds the list of sitemap documents the Fetcher could not read
  (`sitemap_documents_failed`), had not finished when this was written. The groningen `too_large` and unibo
  `unparseable` facts above were checked by hand through the same Fetcher.
- The 150-document safety stop on the unbounded walk was reached on 2 KB hosts and no development host.

## Re-measure 2026-10-20 on the GitHub runner: the hop-2 table, the rank reconciliation, khalifa (IC-2b)

Ticket IC-2b of `NEXT_CYCLES_2026-10-23.md` §3. Run: `benchmark-capture.yml` `mode=index_ceiling`, run 39408839839, at
`b4c0dd39` (IC-2's tool: `hop1_parent`, `hop1_anchor`, `hop1_rank`, `hop1_of`, `hop1_score`), 2026-10-20 10:34–11:17
UTC, from the GitHub runner, not the sandbox. Same inputs as run 3 (development gold, KB). The report is committed as
`backend/evaluation/research/data/index_ceiling.dev-2026-10-22.json` (138 records).

**What was removed before the commit.** No heldout case id or domain was in the artifact (checked by a count-only
script, by site id and by the nine domains). The one dev5 university (in the KB only) had a blind record with no rows
and no homepage, as the tool writes it, but its `sitemap_documents_failed` still listed **28 URLs on its own host**
(`written()` does not clear that field). They were stripped programmatically before anything was read; the record
keeps its counts. **dev5: 1 university, counted in the KB aggregates only, no row.** The committed file was then
checked again by the same script: 0 heldout ids, 0 heldout or dev5 domains.

### Table 1 again, from the runner

| set | cases with gold | in_sitemap_bounded | in_sitemap_any | linked_2hops | twin_declared | **ceiling** | ceiling_any | host_refused | run 3 ceiling |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cohort | 10 | 1 | 2 | 2 | 2 | **2** | 4 | 4 | 3 |
| dev2 | 10 | 1 | 3 | 1 | 0 | **2** | 4 | 3 | 1 (0 after the khalifa correction) |
| dev3 | 14 | 3 | 9 | 3 | 2 | **5** | 10 | 2 | 6 |
| dev4 | 5 | 0 | 1 | 1 | 3 | **1** | 3 | 0 | 1 |

Every difference from run 3 is one case, and every one is a vantage-point or site change, not a tool change:
- cohort: aalto's homepage and sitemaps are `robots_disallowed` from the runner (any and twin lost); toronto's
  `future.utoronto.ca` sitemaps answer 403 (any lost); kaist's `cs.kaist.ac.kr` is `robots_disallowed`, so its hop-1
  page cannot be read and the gold is not linked (linked 3 → 2).
- dev2: tec's gold is now in the bounded sitemap (run 3: 403); khalifa is reached at hop 2 (below); uct's homepage
  times out; uppsala no longer does.
- dev3: puc's homepage times out from the runner, so its hop-2 reach is not measured (linked 4 → 3); ucph's gold is no
  longer in the bounded sitemap (it is still reached at hop 2); kuleuven's robots refusal did not recur.
- KB: 395 (entry, URL) pairs now (the KB grew since run 3), ceiling 95 (24 %), ceiling_any 180.

**The verdict for 05 is unchanged**: the ceiling is 2 / 2 / 5 / 1 against bars of 7 / 6 / 9–10 / 4.

### The hop-2 table: which homepage link leads to the gold

`hop1_rank / hop1_of` is the hop-1 page's place among the homepage's distinct programme-ish links, best first, under
`index_ceiling.programmeish` (`navigation._score` + 3 for a `study_section_label` + 2 for a section/admission word +
1 for a study word in the path; ties by URL ascending). The hop-1 page recorded is the best-ranked one that links the
gold form; a lower-ranked page may link it too. One row per gold form reached at hop 2.

| set | case | gold form reached | hop-1 page | homepage anchor | rank / of | score |
|---|---|---|---|---|---:|---:|
| cohort | vienna | `aufnahmeverfahren.univie.ac.at/informatik` | `studieren.univie.ac.at/studienangebot/bachelor-und-diplomstudien` | Studienangebot Bachelor / Diplom | 1 / 9 | 8 |
| cohort | ntu | `www.ntu.edu.sg/education/undergraduate-programme/bachelor-of-computing-in-computer-science` | `www.ntu.edu.sg/education/degree-programmes` | Degree Programmes | 17 / 135 | 5 |
| dev2 | khalifa | `www.ku.ac.ae/program/bsc-in-computer-science` | `www.ku.ac.ae/academics/undergraduate-programs` | Undergraduate | 2 / 22 | 8 |
| dev3 | auckland | `…/find-a-study-option/bachelor-of-science-bsc.html` | `www.auckland.ac.nz/en/study/study-options/find-a-study-option.html` | Find a study option | 13 / 39 | 5 |
| dev3 | ucph | `www.ku.dk/studier/bachelor/datalogi` | `www.ku.dk/studier/bachelor` | Bachelor | 1 / 10 | 8 |
| dev3 | iitd | `homecse.iitd.ac.in/b-tech-program/` | `www.cse.iitd.ac.in/` | Computer Science and Engineering | 3 / 23 | 6 |
| dev4 | kit | `www.sle.kit.edu/vorstudium/bachelor-informatik.php` | `www.sle.kit.edu/vorstudium/studiengaenge.php` | Studiengänge | 5 / 22 | 3 |
| dev4 | vut (related) | `www.vut.cz/studenti/programy/program/10326` | `www.vut.cz/studenti/programy?data[rok]=2027` | Studijní programy | 2 / 4 | 7 |

Not in the table: **puc** (homepage timeout from the runner: no hop was read) and **kaist** (`cs.kaist.ac.kr` refused by
robots from the runner: the hop-1 page and the gold were not read).

### Reconciliation with NO_SEARCH_FLOOR §2's rank column (the 2026-10-20 05:30 UTC sandbox probe)

| case | NO_SEARCH_FLOOR §2 (probe) | this run | same hop-1 page? | difference, and why |
|---|---|---|---|---|
| auckland | 17 ("Find a study option") | **13 / 39** | yes | **4 places higher.** Same page and anchor. The probe's scorer had no +1 path-word term and its tie order is not recorded; the runner's homepage may differ from the sandbox's 5 h earlier. The gold form reached also differs (this run: `bachelor-of-science-bsc.html`; the probe: the CS undergraduate page). The conclusion "outside any small hop budget" holds at 13. |
| iitd | 3 (`www.cse.iitd.ac.in`) | **3 / 23** | yes | none |
| puc | 4 (`admision.uc.cl/carreras`) | — | not measured | **not reproduced**: the homepage timed out from the runner, so no hop-1 page was read. The probe's rank stands as the only measurement; the floor's "never followed" cause is unaffected (it was read from the captures). |
| kit | 5 (`sle.kit.edu/…/studiengaenge.php`) | **5 / 22** | yes | none (the probe's second parent, `bewerbung.php` rank 7, is not recorded: the tool keeps the best-ranked parent only) |
| kaist | 2 (`cs.kaist.ac.kr`) | — | not measured | **not reproduced**: `cs.kaist.ac.kr` is `robots_disallowed` from the runner (run 3 and the probe read it). The probe's rank stands. |
| ntu | 17 (`education/degree-programmes`, without the seed) | **17 / 135** | yes | none |
| vienna | 1–2 | **1 / 9** | yes | consistent |
| ucph | (no rank given) | 1 / 10 | — | new |

So four of six ranks reproduce exactly (iitd, kit, ntu; vienna within the probe's range), one moves (auckland 17 → 13,
same page), and two cannot be re-measured from this vantage point (puc, kaist). No §2 cause or §4 verdict depends on
the difference: auckland is lost in confirm-queue order and a refused hub, not at the homepage.

### The khalifa correction (CO-1, NO_SEARCH_FLOOR §7.2)

Run 3's row "khalifa: bounded yes, listed yes, hop 0" **does not reproduce**. On the runner, both draft3 gold forms
(`www.ku.ac.ae/program/bsc-in-computer-science` and its `/ar/` twin) are in **no** sitemap, bounded or unbounded,
which is what CO-1 found by re-reading `sitemap.xml` (3 569 URLs) and `sitemap_index.xml` (3 743 URLs). The English
form is reached at **hop 2**, through `/academics/undergraduate-programs` (anchor "Undergraduate", rank 2 / 22): one of
the two hubs CO-1 §7.2 says link the gold and the walker refused. Both gold reads timed out from the runner
(`host_refused` "timeout"); the reach is by link, not by read. Run 3's report was never committed, so the URL that
row matched cannot be named; the most likely explanation stays CO-1's (matched on something other than the draft3
gold). The per-case table above and Table 1's correction paragraph carry the corrected values with the old ones kept.
So khalifa belongs to "reached at hop 2 through a refused hub" (FRH's class), not to "bounded, ranked out".
