# Discovery without touching the sites: the Common Crawl index and Wikidata official websites

Type: research
Status: open
Blocked by: —
Map: ../map.md · AFK, offline against two public datasets; zero credits; politeness 1 request a second with backoff.

## Question

Two free sources list URLs without a request to any university: the Common Crawl URL index (every URL a monthly
crawl captured, queryable by domain prefix) and Wikidata (`P856`, official website). Could the first replace a search
provider or a crawl as the *URL discovery* step of an own index — and how stale is it for programme pages? Could the
second fill the 147 of 500 catalogue rows that have no `official_domain` (Korea 17, Germany 15, UK 11, USA 9…), which
today cannot enter discovery at all?

## Test

1. **Common Crawl coverage.** For the 44 development gold programme URLs (+ twins) and the KB's 312 evidence URLs:
   query the CDX API of the two most recent crawls (`https://index.commoncrawl.org/CC-MAIN-<id>-index?url=<url>&output=json`
   and a per-domain prefix query `url=<domain>/*&filter==status:200`) — the index server answered HTTP 503 while this
   map was charted; record availability and 429/503 behaviour as a finding (its status page attributes 4xx to
   CloudFront rate limits). If the API stays unreliable, read the columnar index (parquet over HTTPS, one crawl, the
   `url_host_registered_domain` partition for the 100 top-100 domains) with a local query engine instead; note the
   download size. Rows: `in_latest_crawl`, `in_previous_crawl`, `capture_age_days`, per set and per KB question;
   how many programme pages of the 100 top-100 domains the crawl lists at all (URL-pattern count per domain).
2. **Wikidata fill.** For the 147 rows: a SPARQL query by label (several languages) and country, instance-of
   university, returning `P856`; match rate, ambiguity rate; a proposal file `catalogue_official_domains.proposed.json`
   for the owner to confirm row by row — the catalogue is never written automatically.
3. **Terms.** Common Crawl's terms (limited licence, crawled content under its owners' terms, no rate numbers; the
   index is a list of URLs, not content — we fetch nothing from it) and Wikidata's (CC0; the query service's user-agent
   policy). One paragraph each.

## Deliverable

`docs/process/CC_WIKIDATA_DISCOVERY_2026-10-xx.md`: the coverage tables, the staleness distribution, the Wikidata
match table and proposal file, and a verdict: whether CC can seed the own index's URL list (replacing or shortening the
sitemap stage on hosts with no usable sitemap), and whether it is current enough for deadline pages (it is not
expected to be: a monthly crawl against a yearly cycle is fine for programme pages, not for deadlines — say so with
the age numbers).

## Files the worker holds

`backend/evaluation/research/cc_coverage.py` (new, evaluation only, plain HTTP to the two services through the
container's proxy as `search_probe.read_page` documents — these are not university sites), the new doc, the proposal
file. Read-only: the gold and KB files, `unimatch_top500_seed.json`.

## Evidence

Provider survey asset (CC index status page, terms; Wikidata `P856`); `app/catalogue/discovery.py` `_identify_site`
(what a row without a domain cannot do); the KB list's 2 rows without a domain and 12 with `extra_domains`.

## Done when

The doc and the proposal file are committed; 05's build job knows whether it may seed from CC; the owner has a
row-by-row domain proposal to sign.
