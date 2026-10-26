# Wikidata official websites for the catalogue: 2026-10-19

This is the Wikidata half of wayfinder issue `free-search/issues/06-common-crawl-and-wikidata-discovery.md`.
The Common Crawl half is not covered here.

- **Question.** Can Wikidata `P856` (official website) fill the catalogue rows that have no `official_domain`?
  Does it agree with the domains on the KB top-100 list?
- **Code.** `backend/evaluation/research/wikidata_domains.py`. It is evaluation code and never ships.
  Tests are in `backend/tests/test_wikidata_domains.py` and run offline against `httpx.MockTransport`.
- **Output.** `backend/evaluation/research/data/catalogue_official_domains.proposed.json` holds the
  **proposals**. Nothing was applied: `backend/app/catalogue/unimatch_top500_seed.json` and the KB list are
  unchanged. Each proposal has a `review` block (`decision`, `reviewer`, `note`) for the owner to sign row by
  row.
- **Rerun.** `cd backend && .venv/bin/python -m evaluation.research.wikidata_domains`, which makes about 40
  requests and takes about a minute.

## Counts

| | rows |
|---|---:|
| Catalogue rows (`unimatch_top500_seed.json`) | 500 |
| No `official_domain` | **147** |
| Held out, excluded and not queried | 4 |
| Queried | 143 |
| A domain is proposed | **142** |
| high | **109** |
| medium | 28 |
| low | 5 |
| none (nothing proposed) | 1 |

The four rows held out by seed id are `qs2027-025` (tum), `qs2027-087` (polimi), `qs2027-273` (charles) and
`qs2027-456` (masaryk). Nothing about them was looked up. The other held-out institutions (metu, sabanci,
tartu, vilnius) already have a domain. Nazarbayev University is not in the seed.

The high-confidence rows by country are Korea 15 of 17, Germany 11 of 14 queried, Australia 8 of 8, Taiwan
8 of 8, USA 7 of 9, UK 6 of 11, France 4 of 8 and Switzerland 4.

**KB top-100 check.** 98 rows have a domain. The other 2 are the held-out rows tum and polimi.

| verdict | rows |
|---|---:|
| agree: Wikidata `P856` has the KB domain or one of its `extra_domains` | **96** |
| disagree | **0** |
| unresolved: the item matched, but `P856` has only a *deprecated*-rank value | 2 |

The 96 agreements break down as 83 high, 12 medium and 1 low. The two unresolved rows are
`northwestern.edu` (Q309350) and `psu.edu` (Q739627). Both items carry the same domain as the KB, but at
deprecated rank, so the best-rank `wdt:P856` path does not return it. Neither row is a disagreement.

Politeness on this run: 39 requests and 0 throttled.

## Method

1. **Name variants with tiers.** A row's name produces variants, each with a tier:
   - Tier 0 is the name as written. It is also tried without its parenthesis, without a leading "The",
     without quotes, and with `Universitaet` spelled `Universität`.
   - Tier 1 reshapes the name but keeps the institution:
     - the parenthesis on its own (`NTU Singapore`)
     - the name with a trailing place removed (`…, Singapore`)
     - an inverted name turned round (`Essex, University of`)
     - an acronym and name pair (`KIT, Karlsruhe…`)
   - Tier 2 is any other piece of a split name. Such a piece can name a different body:
     `Birkbeck, University of London` yields `University of London`.
2. **Batched label query.** The variants of 20 rows go into one SPARQL query. The query matches on
   `rdfs:label|skos:altLabel` in `en` and `mul`, and keeps instances of higher education institution
   (`wdt:P31/wdt:P279* wd:Q38723`). It returns `P856`, `P17` and whether the item is dissolved (`P576`).
3. **Entity search fallback.** This runs only for rows with no usable hit. It uses Wikidata's `EntitySearch`
   inside the query service, with up to 4 texts per row. It first tries the full names, then the names with
   hyphens replaced by spaces, then names cut to their first three words. A hit found only through a cut
   name is capped at low.
4. **Match confidence** comes from name plus country. It is a category, not a probability.
   - Dissolved items are dropped first.
   - The item's `P17` must match the row's country. Hong Kong and Macao rows also accept the People's
     Republic of China.
   - **high**: one item whose label (or, in the label query, an alias) equals a tier-0 or tier-1 variant,
     with exactly one registrable domain in `P856`.
   - **medium**: an alias-only match, a search hit whose label differs from the catalogue's (often an
     English translation), or `P856` spread over several registrable domains.
   - **low**: an equally strong rival item, a tier-2 match only, or a hit found only by a cut name.
   - **none**: no live item in the country, or one with no `P856`.
5. The proposed domain is `registrable_domain(P856)` from `app.domain.site_identity`, the same public-suffix
   rule discovery uses. Every proposal includes the Wikidata item id, its label, the raw `P856` values, a
   reason string and any alternative items.

## What a reviewer should know before signing

- **The low rows contain real misses.**
  - `qs2027-280` University of Navarra was proposed as `iese.edu`. IESE is its business school; the
    university's own domain is not in the top hit. Three rival items were found.
  - `qs2027-363` City St George's, University of London was proposed as `london.ac.uk`. That is the
    federal university, matched on a tier-2 piece of the name.

  Both should be rejected or corrected by hand. Read every low row this way.
- **`qs2027-376` Goethe University Frankfurt** was proposed as `goethe-university-frankfurt.de`. That is
  Wikidata's `P856`, but the university's main domain is `uni-frankfurt.de`. Check it.
- **Medium rows with several domains**: Korea University (`korea.ac.kr`, `korea.edu`), POSTECH and
  Lancaster. In each case the proposal is the first domain Wikidata lists; the `p856` field shows the
  others.
- **No match at all**: `qs2027-461` TIIAME-NRU (Uzbekistan). Its only label hit carries `P17` Russia, and
  entity search found nothing.
- Wikidata `P856` is the institution's main site. For admissions, discovery may also need a sibling host,
  as the KB's 12 `extra_domains` rows already show (for example `mitadmissions.org`). A proposal fills
  `official_domain` only.

## Terms and politeness

**Wikidata.** Wikidata's structured data is CC0, so the proposals carry no attribution or licence burden.
The query service's user-agent policy asks for a descriptive `User-Agent` with a way to identify the client.
This run sent `ashyq-apply-evaluation/0.1 (https://github.com/wpalish/ashyq-apply; …)`.

**Politeness rules in the code.** One request at a time, at least 1 s apart. Name lookups are batched, so the
whole run is about 40 requests. A `429` or `503` is answered by waiting the server's `Retry-After`, capped at
120 s, with at most 4 attempts in total before giving up.

**Rate limits observed.** The MediaWiki Action API (`wbsearchentities`) answered **429 with
`Retry-After: 7`** to this container's very first request. The egress IP is shared, so the rate limiter
had already been triggered. The code therefore does not call the Action API directly; entity search goes
through the query service's `mwapi` bridge instead. The query service never throttled this run.

This is not a search provider. Wikidata is a public dataset; no university site was fetched and no
applicant data was sent.

## Verdict

- **Fill.** Wikidata can fill the gap. 109 of the 143 queryable rows have a high-confidence single-domain
  proposal, which is 76%. Another 28 have a medium proposal that is usually right. Only one row has nothing.
  With the owner's sign-off, discovery could gain up to 142 rows.
- **KB check.** The check found **no disagreement** with the KB's 98 domains: 96 agree and 2 are only
  deprecated-rank. The KB's domain choices stand.
- **Not done.** Nothing has been applied. The main session or the owner decides row by row.
