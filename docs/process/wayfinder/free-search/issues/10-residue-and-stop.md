# Residue and stop: the filled recommendation table, what stays unreachable for free, and the owner's default

Type: research
Status: open
Blocked by: 03, 04, 07, 09 (05 and 08 when opened)
Map: ../map.md · AFK → HITL — the exit ledger of this map; the owner picks the product's default from it.

## Question

Once every option has its measured row: which free layer, if any, meets 01-Q2's bar; what does the product's `live`
mode default to; which development pages and KB questions stay unreachable at $0 and why; and what would the
cheapest paid option cost per month at the product's measured volume, so the owner compares a price with a gap
instead of guessing?

## Ledger rows (one per option; filled from the tickets' documents)

| option | gold returned (cohort / dev2 / dev3 / dev4) vs Serper 8/10 · 9/10 · 11–12/14 · 5/5 | wrong pages on the arm | monthly cost at 02's volume | terms clean? | verdict | residue class if any |
|---|---|---|---|---|---|---|
| Exa keyed free credit | 03 | 03 | 02/03 (dashboard) | 03 | | |
| Tavily | 03 | 03 | | 03 | | |
| Brave (if opened) | 03 | 03 | | 03 | | |
| Exa MCP keyless | cycle 1 (cohort 6/10 pages) | | $0, ≈ 50/day/IP | | | |
| own index `local_index` | 04 ceiling → 05 row | 05 | $0 | ours | | not in sitemap and not linked (client-rendered, department host, other domain); hosts refusing everywhere |
| Common Crawl seed / Wikidata fill | 06 | — | $0 | 06 | | staleness |
| KB refresh cron (+ home runner) | — | — | $0 | ours | | `ua_or_waf_block`, `robots`, dead hosts (08) |
| model hint | 09 audit | — | 09 | §6.4 / D9 | | |
| cheapest paid (fact only) | Serper $50 per 50 000; Exa $4 per 1 000; Brave $5 per 1 000; Mojeek £2 per 1 000 | | at 02's volume | | not recommended by this map | |

## Residue classes (carried from the finish-algorithm ledger, re-counted for a $0 layer)

- Pages no sitemap lists and no homepage links within two hops (client-rendered catalogues, opaque CMS URLs,
  department hosts never linked, other registrable domains): an own index cannot reach them; a web index might; name
  the cases and the count per set from 04.
- Hosts that refuse datacenter IPs *and* the owner's computer, or refuse our agent in robots.txt: the KB mode serves
  them from the last verified fact with `stale` shown honestly; count the KB questions affected from 08.
- Non-English evidence pages and PDFs: other maps' escalations; count only.
- Questions whose free-tier quota would be exceeded at the product's volume: from 02 — the number of applicant
  researches a month each tier supports.

## Deliverable

This ticket's `## Answer`: the filled table, the residue counts, and the owner's question in `OWNER_QUESTIONS.md`
round 2: **the default for `UNIMATCH_SEARCH_PROVIDER` in `live` mode** (a passing free tier / `local_index` / `none`
with KB only), the cron cadence confirmed, and whether any paid option is wanted (the map recommends none unless the
gap it closes is named by case). A dated line in `docs/process/LOOP_REPORT.md` and HANDOFF §7.

## Done when

The owner has answered round 2; `map.md` "Decisions so far" carries the default; the map closes.
