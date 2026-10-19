# `local_index`: an own index over the catalogue's official domains behind the SearchProvider seam

Type: task
Status: open
Blocked by: 04 (ceiling verdict "build"), 01-Q5
Map: ../map.md · AFK task behind a flag; `loop-engineering` (flag-off → offline tests → the 04 tool's row with the
index as provider → one capped paired arm on the four sets, provider `local_index` vs `none`). Zero credits.

## Question

Nothing to decide if 04 says the pages are there: build a search provider that answers the six query families from
an index we build ourselves — sitemaps plus a bounded crawl of each official domain through `Fetcher`, page title,
`<h1>`, language, hreflang twins and readable text — so that discovery keeps a search layer with no quota, no
vendor terms and no HTTP request to the site at query time.

## Design

- **Build job** (runs on a runner or the owner's computer, never in the request path): for each catalogue row with an
  `official_domain` (top-100 list first, then the 353 of the 500), read robots.txt and the sitemap tree under the
  product's bounds, then crawl at most N pages per host (N ≈ 500, programme/admissions/fees/scholarship paths first by
  `navigation.py`'s words, crawl-delay honoured, the host's refusal recorded and never retried in the same build),
  extract `readable_text` (first ~20 kB), `<title>`, `<h1>`, `<html lang>`, `declared_alternates()`, `lastmod`/ETag.
  Store in `backend/data/local_index/index.sqlite` (FTS5 where the interpreter has it; otherwise the project's
  `_Bm25` over a plain table) — never committed; rebuilt by 07's cron; `lastmod`/ETag skip unchanged pages.
- **Provider** `LocalIndexSearchProvider` (`name = "local_index"`, `KNOWN_SEARCH_PROVIDERS` + `"local_index"`,
  `UNIMATCH_LOCAL_INDEX_PATH`): `search(query, domains, max_results)` strips `site:` operators (its scope comes from
  `domains`, by registrable domain as `same_institution` reads it), keeps quoted phrases as phrases, ranks by BM25 with
  title/`<h1>` boosted, returns `SearchResponse` rows with `snippet=""` (there is nothing to cite from an index and the
  seam forbids it). `search_localized(query, hl, gl, …)` is the same search: text matches the alias in any language.
  Raises `SearchUnavailable` when the index file is missing or older than a configured age, never an empty answer
  in that case (the seam's rule: "no provider" must not read as "found nothing").
- **Fusion**: results enter as `Generator.WEB_SEARCH` through `discover_candidates` unchanged — the fetch of every
  returned page still goes through `Fetcher` and the classifier / confirm / quote path; or, if measured better, as a
  new `Generator.LOCAL_INDEX` with its own weight (table in `fusion.py`, argued not tuned).
- **Budget**: index queries are not requests to the site; the 60-request budget is spent only on reads, as today.
  Discovery's own sitemap stage can be skipped for a host the index covers (flag `LOCAL_INDEX_SKIPS_SITEMAPS`,
  off), which is the read saving 04 measures.
- **Privacy**: the index holds public pages only; queries carry the `DiscoveryIntent` words and nothing else (the
  intent rejects applicant data by construction).

## Measure

1. Offline: provider contract tests (the suite every provider passes), fixture index built from fixture sitemaps and
   pages, a query returning the fixture programme page at rank 1 by title alias in two languages.
2. The 04 tool re-run with the index as provider: `gold_returned` per set — the exact comparable row.
3. One capped paired arm `--search-provider local_index` (on) vs `none` (off) on cohort / dev2 / dev3 / dev4: bar =
   gold returned ≥ Serper's base3 row within one case per set, `wrong_programme_pages` not up, 0 over budget, reads
   not up. dev5 aggregates only, if the owner allows a read (generalisation 13).

## Files the worker holds

`backend/app/adapters/search/local_index.py` (new), `backend/app/adapters/search/__init__.py` (factory line),
`backend/app/config.py` (`UNIMATCH_LOCAL_INDEX_PATH`, the age setting), `backend/app/jobs/index_builder.py` (new;
`Fetcher` only), `backend/tests/test_local_index.py`, `backend/tests/test_index_builder.py`, one workflow job
`mode=build_index`. Read-only: `retrieval.py`, `fusion.py`, `live_discovery.py`. Disjoint from 02/03/04.

## Evidence

04's tables; `fusion.py` (`GENERATOR_WEIGHTS` sitemap 0.6 vs web_search 1.0 — a sitemap listing is unranked, an
index answer is ranked, which is why it may deserve the web_search weight); `SEARCH_PROBE.md` (ranking with a real
candidate set); finish-algorithm ticket [05](../../finish-algorithm/issues/05-returned-never-read.md) (returned-not-read
losses are a read-order problem the index does not touch).

## Done when

Flag off by default with tests green; the 04 row and the paired arm are in `docs/process/LOCAL_INDEX_2026-10-xx.md`;
HANDOFF §8 names the provider, the settings and the job; the owner decides the default in 10.
