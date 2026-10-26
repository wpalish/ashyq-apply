# The ceiling of an own index: are the gold and evidence pages in the sitemaps, or linked from the homepage?

Type: research
Status: resolved
Blocked by: —
Map: ../map.md · AFK — offline tool first, then one GitHub runner job (public sitemaps and pages through `Fetcher`),
then one self-hosted job for the hosts that refuse datacenter IPs (01-Q4). Zero credits. Decides ticket 05.

## Question

An own index can only return what it has crawled. Before building one: of the 44 development gold programme pages
(and their twins) and the knowledge base's 312 verified evidence URLs, how many are (a) listed in a sitemap document
the product's `SitemapReader` would read under its bounds (12 documents, news/events trimmed, depth 3), (b) listed in
any sitemap at all, (c) reachable within two link hops from the homepage following programme-ish anchors under the
60-request budget, (d) declared as an hreflang twin of a page that is listed? And for the non-English gold pages:
does the page title or `<h1>` contain the ontology's localized alias of the field, so a text index would match the
R5 query without a URL lexicon? The cohort alone saw 15 185 sitemap URLs and kept 226 per column — the bound costs
something; this measures what.

## Tool (`evaluation/research/index_ceiling.py`, evaluation only)

- Input: the gold files (programme URLs + twins per case) and the KB file (`programme.evidence[].url`,
  `facts.*[].source_url`, `not_applicable[].source_url`); the homepage per case / per KB entry (`official_site`).
- Per host, through `Fetcher` (robots, crawl-delay, our user agent): read robots.txt sitemap directives, the sitemap
  tree twice — once under `SitemapReader`'s bounds, once unbounded up to `MAX_SITEMAP_URLS` — and record for each
  target URL whether its canonical form (`metrics._page_forms`) is listed, in which document, and the document's
  index position (would the 12-document cap have reached it?). `lastmod` presence is recorded for 07.
- Two-hop reach: from the homepage, follow anchors whose text or path carries a study/programme/admissions word
  (`navigation.py` already classifies them), at most 60 requests per host, record the hop at which each target is
  met; count `declared_alternates()` twins.
- Title test: for each gold page actually read, `<title>`/`<h1>`, `<html lang>`, and whether `localized_aliases_in`
  (field, language) matches. Non-English development cases: psaclay, kuleuven, uio, uba, puc, tec, tsinghua, ub,
  chula, ctu, vut, rwth, kit, unibo, taltech, ktu, boun, itu.
- Output: a per-set table (cohort / dev2 / dev3 / dev4) and a per-KB-question table (programme, english, gpa,
  deadline, tuition, scholarship) with `in_sitemap_bounded`, `in_sitemap_any`, `linked_2hops`, `twin_declared`,
  `title_alias_match`, `host_refused` (403 / robots / timeout); the union `in_sitemap_bounded ∪ linked_2hops` is the
  ceiling row 05 is judged against (01-Q2's bar: ≥ Serper's gold-returned per set, within one case).
- Runs: GitHub runner first; the self-hosted runner for the hosts the first run recorded as refused (08 reads the
  same job). No heldout case, no dev5 per-case row.

## Deliverable

`docs/process/INDEX_CEILING_2026-10-xx.md`: the two tables, the list of gold pages in no sitemap and not linked
(the class an own index cannot reach — client-rendered catalogues, department hosts the homepage never links,
other registrable domains, as the residue ledger names them), the title-match rate per language, and the verdict
for 05: **build** if the union row meets the bar on every set; **do not build** otherwise, with the numbers.

## Files the worker holds

`backend/evaluation/research/index_ceiling.py` (new), `backend/tests/test_index_ceiling.py` (fixture sitemaps and
pages; offline), one workflow job `mode=index_ceiling`. Read-only: `live_discovery.py` (`SitemapReader`,
`parse_sitemap`, `declared_alternates`), `navigation.py`, `ontology.py`, `metrics.py`, the gold and KB files.

## Evidence

`STAGE_SUMMARY_DEV_2026-10-19.md` (`sitemap_urls_seen` 15 185 / `sitemap_urls_kept` 226 / `sitemaps_read` 12 on the
cohort; `returned_by_family:local_language` 4 cohort, 5 dev4); `RESIDUE_LEDGER_2026-10-18.md` Table A (department
host / opaque URLs, other registrable domain, not linked / client-rendered); programme-discovery tickets
[08](../../programme-discovery/issues/08-loss-stages-today.md) (where the page is lost on development: class B
"never returned") and [09](../../programme-discovery/issues/09-url-lexicon-audit.md) (the URL lexicon is English /
cohort-only — the reason an index over page *text* is proposed rather than another URL rule); `live_discovery.py`
`SITEMAP_TRIM` / `MAX_SITEMAP_DOCUMENTS` (the bound whose cost this ticket measures). Development evidence only.

## Done when

The doc is committed with both tables and the verdict; 05 is opened or closed "not built" from it.

## Answer

[`INDEX_CEILING_2026-10-19.md`](../../../INDEX_CEILING_2026-10-19.md). The run was from the sandbox through the
production Fetcher (137 sites); the GitHub-runner job (`mode=index_ceiling`) has not been dispatched yet. The ceiling
(bounded sitemap ∪ two hops) reaches the gold in 3/10 cohort, 1/10 dev2, 6/14 dev3 and 1/5 dev4 cases, against
Serper's 8 / 7 / 10–11 / 5. Even the oracle-host upper bound reaches only 7 / 3 / 10 / 3. KB: 77 of 336 URLs (23 %),
upper bound 179 (53 %). **Verdict: do not build 05.**

Gist: an own index rooted at the homepage reaches about a third of what Serper found; the gold sits on hosts that
neither the homepage nor its sitemap names.
