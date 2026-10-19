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
| dev2 | khalifa | yes | yes | 0 | no | - |
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
