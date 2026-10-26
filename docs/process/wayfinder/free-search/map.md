# Map — Free search: keeping results without a paid search provider

Label: `wayfinder:map` · Tracker: local markdown (`issues/NN-<slug>.md`; `Type:`, `Status:`, `Blocked by:` lines)
· Charted 2026-10-19 by the planner agent at the owner's request («найти, как получать результаты без платного
поиска»), after the Serper credits ran out (≈ 50 000 credits over ≈ 170 benchmark runs; every call answered
HTTP 400 from 2026-10-19 05:11) and the owner froze live search in favour of the verified knowledge base
(`docs/process/KNOWLEDGE_BASE.md`). **Extends** [Generalisation](../generalisation/map.md) (its hypotheses and the
design-blind dev5 protocol stand; nothing here re-decides them) and inherits the loss classes of
[Finish the search algorithm](../finish-algorithm/map.md). Owner (Диас) answers every HITL ticket through
`OWNER_QUESTIONS.md` (Russian); agents only recommend.

## Destination

**A search layer that costs $0 a month at the product's volume, is clean under every provider's terms and our
own rules, and returns the gold programme page on the development sets at least as often as Serper did — or an
honest record that no free layer does, with the knowledge base kept current for free instead.** Concretely: the
product's `SearchProvider` seam gets at least one configured provider whose quota, terms and measured
`gold_returned_by_search` on cohort / dev2 / dev3 / dev4 are written down; the knowledge base's 312 verified
evidence URLs are re-verified on a schedule that costs nothing; and every option the owner named (free tiers,
self-hosted engines, an own index, no search at all, a model as a hint) has a verdict with numbers from an
experiment that spent **no paid credits**. The map is done when the owner has the recommendation table filled
with measured values and has chosen a default, or when every option has been shown not to reach the bar.

## Notes

- **What the money bought, honestly.** The provider was never the measured bottleneck on development: with Serper the
  gold is returned by search in **8/10 cohort cases, 9/10 dev2, 11–12/14 dev3, 5/5 dev4** (base3,
  `STAGE_SUMMARY_DEV_2026-10-19.md`); swapping Exa MCP for Serper moved nothing on the cohort (6/10 programme pages
  under both; loop report cycle 1), and the 2026-09-21 Exa probe took the retrieval ceiling from 1/10 to 9/10 for 50
  queries (`SEARCH_PROBE.md`). The losses measured since are *after* search — ranking, the read cap, confirm — and,
  on the heldout nine, *before* it: the gold is **never returned in 4–6 of 9** and recovery confirms 4 wrong pages of
  5 (`HELDOUT_STAGE_SUMMARY_2026-10-19.md`, aggregates only). A free layer is therefore judged on one row —
  **gold returned by search on the 44 development cases, same six queries** — and on what it costs; it is not asked
  to fix the confirm step (that is generalisation ticket 09, CA-1) or the read cap (finish-algorithm residue).
- **The arithmetic that shapes this map.** A paired run sends ≈ 3.3–3.9 discovery queries per case per column
  (cohort `discovery_queries` 33–39 per 10 cases; `search_calls_total` 39–40 with the scholarship query), so one
  four-column run on the four sets costs ≈ 600–700 queries and the old loop (≈ 170 runs) ≈ 50 000 — which is what
  was spent. *Corrected by 02 ([ledger](../../SEARCH_VOLUME_LEDGER_2026-10-19.md)): 600–700 was discovery only (660);
  with topic, scholarship and identity queries a four-set paired run is **≈ 820** (4.7 per case per column), the old
  loop's ≈ 294 per run is one or two sets, and the keyed allowances (≈ 4 500) buy **≈ 5** four-set paired runs or
  ≈ 75–95 applicant researches; the keyless MCP's ≈ 50 a day carries no paired run.* The product's live path costs
  ≤ 6 queries per university, ≈ 60 per applicant research of ten. The free
  allowances found on 2026-10-19 (`assets/provider-survey-2026-10-19.md`): Exa $10 of credit a month (≤ 2 500 instant
  searches before contents are billed), Brave $5 a month (≈ 1 000 queries; third parties report a card and public
  attribution are required), Tavily 1 000 credits a month, the keyless Exa MCP ≈ 50 a day per IP. **Together
  ≈ 5 000 queries a month: ≈ 7 paired runs, or ≈ 80 applicant researches.** The old benchmark cadence cannot be
  free; a modest product can; an own index has no quota at all. Google's JSON API is closed to new customers and ends
  2027-01-01; Bing's retired 2025-08-11; scraping DuckDuckGo or running SearXNG against Google/Bing is excluded by our
  own rules (no UA spoofing, no evasion of blocks), not only by theirs.
- **The product serves the knowledge base, not search.** 98 top-100 universities (77 expert-checked entries + 21
  imported), programme page known for 60 of 77, facts: english 36, gpa 4, deadline 28 (+6 stale), tuition 19 (+27
  stale), scholarship 58. Its 312 evidence URLs on 154 hosts were verified by the production fetcher on GitHub
  runners: **237 open (76 %), 51 answer HTTP 403 on 28 hosts** (US/UK admissions and financial-aid hosts: Cambridge,
  Brown, MIT SFS, Cornell, Harvard, JHU, Berkeley…), **21 are robots-refused on 10 hosts** (BU, Northwestern, NYU,
  Princeton, Penn CIS, Cornell CS, Alberta), 3 misc. From Fly (ams) the 2026-10-06 probe opened 18/32 cohort gold
  URLs (Toronto 403 there too; NTU DNS; Aalto robots timeout). So "keep getting results" has two halves: (a) keep the
  KB current — a free cron job through the same `verify_evidence` path, with the owner's computer as the
  self-hosted runner for the quarter that datacenter IPs cannot read; (b) widen what can be *found* for free —
  the provider replay, the own index, discovery without touching sites.
- **What each option can and cannot address (the recommendation table, to be filled by the tickets).**

  | option | monthly cost | addresses "gold never returned"? | addresses "wrong page confirmed"? | main risk | first experiment (no paid credits) | ticket |
  |---|---|---|---|---|---|---|
  | Exa keyed, free credit | $0 (card not required per its pricing page) | plausibly: a neural index returned pages a keyword query cannot name (2026-09-21 probe 9/10; cycle 1 cohort 6/10 = Serper) | no | ≈ 2 500 queries/month; highlights billed as contents; 402 when spent (handled) | [03](issues/03-free-tier-provider-replay.md) replay the six queries × 44 dev cases | 03 |
  | Brave, $5 credit | $0 if no card; else overage risk | unknown; a keyword index shares Google's vocabulary limit (M5: 1/6 with today's shape, 5/6 with the local shape) | no | card + attribution clause; ≈ 1 000/month | 03 | 03 |
  | Tavily, 1 000 credits | $0 | unknown; its free plan answered 432 on every query in 2025-09 | no | quota tiny; 432 handled | 03 | 03 |
  | Exa MCP keyless | $0 | measured = Serper on cohort (6/10); heldout 0/7 both | no | ≈ 50/day/IP, rate limits mid-run (SR-1 on) | none new; fallback only | 02 |
  | Google JSON API / Bing | closed / retired | — | — | — | none | asset |
  | Mojeek, Marginalia | £2/1k (card-backed trial) / free non-commercial key, CC-BY-NC-SA | unknown independent indexes | no | licence (NC) and card; coverage of university sites doubtful | ≤ 20 hand queries on dev cases only if the owner wants (01-Q3) | asset |
  | DuckDuckGo scraping, SearXNG | $0 | — | — | no API; AUP; SearXNG's captcha workaround is block evasion | none — excluded by our rules | asset |
  | YaCy | owner's PC | would, as an own index | no | its crawler is network outside `Fetcher` (AGENTS §6) | none — build the index through `Fetcher` instead | 05 |
  | **Own index** (sitemaps + bounded crawl of official domains through `Fetcher` → page text → BM25 → `SearchProvider`) | $0 (public-repo cron; or owner's PC) | yes for pages a sitemap lists or the homepage links within two hops; indexes *titles and text*, so a local-language title is found by the ontology alias; hreflang twins indexed together | no (fewer junk candidates only) | 24 % of KB hosts refuse datacenter IPs; staleness; ceiling unknown until measured | [04](issues/04-own-index-ceiling-sitemaps-and-links.md) ceiling on 44 dev gold + 312 KB URLs | 04 → 05 |
  | Common Crawl index + Wikidata | $0 | discovery of URLs without hitting sites, months stale; 147 catalogue rows lack an official domain | no | CC index server answered 503 while this map was charted; rate limits | [06](issues/06-common-crawl-and-wikidata-discovery.md) | 06 |
  | **No search: sitemap-first + scheduled KB refresh** | $0 | nothing in live discovery; keeps what the product serves current | n/a | 403 hosts stay stale unless the home runner reads them | [07](issues/07-scheduled-kb-refresh.md), [08](issues/08-runner-vs-home-access-ledger.md) | 07, 08 |
  | A model alone ("ask a chat assistant") | $0–20 subscription / local model | no: no quote, no date, invented URLs | no | privacy table §6.4, D9 zero-retention | [09](issues/09-model-hint-never-evidence.md) offline URL-hint audit on 44 dev cases | 09 |

- **Domain.** Seam `backend/app/adapters/search/{base.py,__init__.py}` (`SearchProvider.search(query, domains,
  max_results)`, `KNOWN_SEARCH_PROVIDERS`, `_ThrottleLatch`); adapters `exa.py`, `exa_mcp.py`, `tavily.py`, `brave.py`,
  `serper.py`, `fake.py`; query construction `intent.py` (`queries_for`, `local_language_terms`, six families, no
  applicant data by construction); ranking `retrieval.py` (`discover_candidates`, `_Bm25`, `RetrievalReport`);
  fusion `fusion.py` (`Generator`, `GENERATOR_WEIGHTS`: sitemap 0.6, web_search 1.0, registry 1.6); sitemaps
  `discovery/live_discovery.py` (`SitemapReader`, `MAX_SITEMAP_DOCUMENTS` 12, `SITEMAP_TRIM`, `declared_alternates`);
  the single network door `fetching.py` (`Fetcher`, `USER_AGENT`, robots, crawl-delay); freshness
  `jobs/source_scanner.py` (sitemap `lastmod`, conditional GET); knowledge `app/knowledge/{claims.py,funding.py,
  kb_cs_bachelor.json}`, `evaluation/research/expert/kb_build.py`, `scripts/verify_evidence.py` (`OFFICIAL_DOMAINS`),
  `scripts/probe_access.py`; harness `evaluation/research/{live.py,search_probe.py,search_preflight.py,
  stage_summary.py}`, workflow `.github/workflows/benchmark-capture.yml` (`search_provider` input: auto / exa /
  exa_mcp / none; `runner` input: `ubuntu-latest` or `self-hosted` — the owner's computer; modes `verify_evidence`,
  `query_probe`); catalogue `app/catalogue/unimatch_top500_seed.json` (500 rows, 353 with `official_domain`),
  `evaluation/research/data/kb_top100_list.json` (100 rows, 98 with a domain, 12 with `extra_domains`). Development
  gold: `ground_truth.reviewed11`, `dev2.draft3`, `dev3.draft3`, `dev4.draft3` (44 cases); base3 captures
  `scratchpad/runs/base3-*` or the artifacts of runs 39172483236 / 39172484697 / 39172486984 / 39172488858.
- **Working model (owner, 2026-10-18/19; LOOP_PROTOCOL).** A planner charts; workers run AFK tickets in their own
  worktrees and commit locally; the main session cherry-picks, runs the gates, pushes. **While no provider answers,
  the loop's paired-run step is suspended**: every ticket here is offline first (captures, gold files, sitemaps and
  sites read through `Fetcher` from a runner), and a live arm runs only on a free allowance under a per-run cap
  (01-Q8). Disjoint files per ticket are the lock.
- **Standing rules (brief §7.4, AGENTS §6, DoD, LOOP_PROTOCOL).** No robots bypass, no UA spoofing, no proxies to
  evade blocks; no applicant attribute in any query; 6 queries / 60 HTTP requests / 120 s per university; `Fetcher`
  never weakened and **no network outside it except a configured provider's own API behind the seam** (owner,
  2026-09-21); a search result is a hint, never evidence; nothing sent to a model beyond the privacy table (§6.4);
  no model identifier in the repository; no pull request unless the owner asks. The owner's own computer as a
  self-hosted runner is a *vantage point*, not a proxy: it sends the same user agent, honours the same robots.txt
  and never retries around a refusal (01-Q4 asks the owner to confirm this reading).
- **Evidence policy — absolute.** The nine (`nu metu sabanci charles masaryk tum tartu polimi vilnius`) are never
  opened: no gold, capture, log, label or per-case row; `scratchpad/HELDOUT_QUARANTINE_DO_NOT_OPEN` and
  `scratchpad/DEV5_BLIND` are never listed. The only heldout inputs are the two owner-approved aggregate documents.
  dev5 stays design-blind (generalisation 13): aggregates only. Every experiment runs on the 44 development cases, the
  KB's own URLs, public sitemaps and provider documentation. **No Serper or other paid credit is spent by this map**;
  a free allowance is spent only under a written cap.
- **Skills every session consults.** `grilling` + `domain-modeling` for 01 and 10; `research` for 02, 04, 06, 08, 09
  and the asset; `loop-engineering` runs 03, 05, 07 (flag-off → offline tests → one capped live arm → default only
  with no stable loss and no new wrong page); `university-admissions-research` for every KB re-draft 07 queues.
- **Tracker conventions.** Claim = `Status: claimed` before any work; resolve = `## Answer`, `Status: resolved`, one
  gist line below. HITL tickets stay `open` until the owner answers through `OWNER_QUESTIONS.md`.

## Decisions so far

<!-- one line per closed ticket: gist, then the link holds the detail -->

(round 1 is open with the owner: ticket 01)

- [02](issues/02-query-volume-and-free-tier-arithmetic.md) — a four-set paired run is ≈ 820 queries (not 600–700);
  free keyed tiers buy ≈ 5 a month; every provider run now needs `--max-search-queries N` / workflow
  `max_search_queries`, refuses to start over its plan and refuses the (N+1)th query unsent.

## Ticket order, parallel groups and the critical path

| group | tickets | runs in parallel with | wall-clock note |
|---|---|---|---|
| **G0 owner round 1 (HITL, batched)** | [01](issues/01-destination-measure-and-rules.md) | everything below except the *spending* of a free allowance (03's live arm) and the home-runner jobs (04/07/08 self-hosted) | one sitting; «да» accepts the recommended answers |
| **G1 now (AFK, offline, disjoint files)** | [02](issues/02-query-volume-and-free-tier-arithmetic.md) volume ledger + quota guard; [04](issues/04-own-index-ceiling-sitemaps-and-links.md) ceiling tool (offline part); [06](issues/06-common-crawl-and-wikidata-discovery.md); [09](issues/09-model-hint-never-evidence.md) audit design; the provider survey asset is written | each other | 02 ≈ 2 h; 04 ≈ 3 h code + one runner job; 06 ≈ 2 h; 09 ≈ 2 h |
| **G2 after 01 (AFK, capped live)** | [03](issues/03-free-tier-provider-replay.md) once keys exist; 04's runner job (GitHub, then self-hosted); [07](issues/07-scheduled-kb-refresh.md) cron | each other | 03 ≈ 264 queries per provider, ≈ 1 h wall; 07 ≈ 2 h + one scheduled run |
| **G3 after 04/07 report (AFK)** | [05](issues/05-local-index-search-provider.md) only if 04's ceiling ≥ Serper's gold-returned per set; [08](issues/08-runner-vs-home-access-ledger.md) | each other | 05 ≈ 6 h + offline tests + one capped arm; 08 one self-hosted job |
| **G4 exit (AFK → HITL)** | [10](issues/10-residue-and-stop.md) | — | the stopping rule below |

**Critical path**: 01 → 03 (needs the owner's free keys) and 04 → 05 (needs 04's ceiling). The longest chain by wall
clock is 04 → 05 → one capped paired arm (≈ 10 h); nothing shortens it except starting 04 in the first hour.
**Minimal path to a free default**: 01 + 03 (if a free tier matches Serper on the 44) or 01 + 04 + 05 (if the own
index does) + 10.

**Ordered by expected gain per hour** (gain = probability of a $0 default × development pages recovered):

1. [04](issues/04-own-index-ceiling-sitemaps-and-links.md) — 3 h; the only option with no quota; its ceiling decides
   whether 05 is worth 6 h.
2. [03](issues/03-free-tier-provider-replay.md) — 1 h once keys exist; the cheapest honest comparison with Serper.
3. [07](issues/07-scheduled-kb-refresh.md) — 2 h; keeps what the product actually serves current, for free, today.
4. [02](issues/02-query-volume-and-free-tier-arithmetic.md) — 2 h; turns "free" into a number and installs the guard
   that makes spending a free allowance by accident impossible.
5. [08](issues/08-runner-vs-home-access-ledger.md), [06](issues/06-common-crawl-and-wikidata-discovery.md) — 1–2 h each.
6. [05](issues/05-local-index-search-provider.md) — 6 h, only on 04's yes.
7. [09](issues/09-model-hint-never-evidence.md) — 2 h design + a hand audit; builds nothing in this map.
8. [10](issues/10-residue-and-stop.md).

**Stopping rule.** The map hands the owner a filled recommendation table when **all** of: (a) 03 has a gold-returned
number per set for every free tier the owner opened; (b) 04 has the sitemap / link ceiling per set and per KB
question; (c) 07's cron has run once and its stale/changed list is in the KB refresh queue; (d) 05 is either built
and measured on one capped arm, or closed "not built" with 04's number as the reason; (e) 09 has the hallucination
rate on the 44. It stops short and escalates when the authorised worker-hours are spent (01-Q7), when a free tier
changes its terms mid-map, or when every option reads below Serper on gold-returned by ≥ 2 cases on every set — then
10 writes the price of the cheapest paid option beside the KB-only alternative, and the owner decides.

## Not yet specified

<!-- in-scope fog: questions coming, not yet sharp enough to ticket -->

- **A local-language query over the own index** (the M5 shape, which lifted gold-in-top-10 from 1/6 to 5/6 on Serper):
  over page *text* it needs no `hl`/`gl`; whether the ontology alias alone matches the local title is 04's question
  (title match rate per language) before 05 commits to a tokenizer.
- **Index freshness and the KB's `stale` policy**: whether `lastmod` from sitemaps (source_scanner already reads it)
  can drive the KB's deadline re-checks in season, so the cron reads only what changed. Sharp after 07's first run.
- **The product's message when the free quota is spent mid-research**: `SearchUnavailable` is honest today ("Search
  service unavailable"); whether the KB answer should be shown *instead of* a degraded live answer for a KB university
  is a product decision (02 reports the codes: Exa 402, Tavily 432, Brave 429/402, Serper 400).
- **A Kazakhstan / Türkiye proxy for the own index's language test**: dev4 and dev5 cover them, dev5 only at aggregate
  level; 04 reports whether the 44 give enough non-English titles to judge.

## Out of scope

<!-- ruled beyond the destination; never graduates -->

- **Any evasion**: proxies, residential-proxy pools, browser-UA strings, captcha solving (SearXNG's documented
  workaround), scraping a search engine's result pages against its terms. Excluded on our rules, whatever it costs.
- **Buying credits** of any provider, or asking the owner to put a card on file for a "free" plan; the map records the
  cheapest paid option in 10 as a fact, not a recommendation.
- **The confirm step, the read cap, the budget 6 / 60 / 120, the browser tier, PDF and non-English evidence readers**
  (generalisation 09, finish-algorithm residue, the PDF map).
- **A model-based extractor or a model-chosen page** (18-Q2 (c), 2026-10-18): 09 designs a *URL hint* only, verified
  by the same classifier, confirm and quote check as every other lead.
- **Per-institution seeds or hardcode**; the own index is built from the catalogue's official domains and their
  sitemaps, never from a hand-picked page list.
- **Changing the DoD or the KB staleness policy** without the owner's dated entry.
