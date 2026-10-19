# Destination, the measure, the free keys and the rules of this map

Type: grilling
Status: open
Blocked by: —
Map: ../map.md · HITL — the owner confirms what "free search" has to deliver, what it is measured against, which
free accounts he opens, and whether his own computer may read for the knowledge base.

## Question

The Serper credits are spent (≈ 50 000 over ≈ 170 runs); the owner judged the search work to have produced no
result and froze live search behind the knowledge base. He asks how to keep getting results without a paid
provider. Before any worker spends a free allowance or a runner hour: what counts as "results", what is the bar, and
which rules bind the cheapest options?

❓ **Q1** — **Destination as the map states it**: a $0-a-month search layer, clean under every provider's terms and our
rules, that returns the gold programme page on the 44 development cases at least as often as Serper did — or a
written record that none does, with the knowledge base kept current for free instead. Done when the recommendation
table is filled with measured values and the owner has picked a default.

➡️ **Yes.** The alternative — "try the next free API and see" — is how the project went through Exa, Tavily, Exa MCP,
Serper and 50 000 credits. One row (gold returned by search, same queries) and one price per option is what a
decision needs.

---

❓ **Q2** — **The measure and the bar**: for every option, `gold_returned_by_search` on cohort / dev2 / dev3 / dev4
with the *same six queries* the pipeline builds (`queries_for`), twins counted as the scorer counts them; the bar is
the base3 Serper row per set (**cohort 8/10, dev2 9/10, dev3 11–12/14, dev4 5/5**, `STAGE_SUMMARY_DEV_2026-10-19.md`),
"no worse by more than one case on any set". A live arm additionally must add no wrong confirmed page. Cost is read
off the provider's dashboard after the replay, never estimated.

➡️ **Yes.** The provider was not the bottleneck on development (cycle 1: Exa MCP = Serper on the cohort); a free layer
that matches Serper's reach loses nothing measurable. Asking it to also fix the confirm step would mix this map with
generalisation 09.

---

❓ **Q3** — **Free accounts**: the owner opens (a) a keyed Exa account (its pricing page: $10 credit a month, resets on
the 1st, no payment method required) and (b) a Tavily account (1 000 credits a month); (c) Brave only if it asks for
no card at signup (third parties report a card and public attribution are required for the $5 monthly credit — if
so, skip it); no Mojeek (card-backed trial); Marginalia and Jina only as hand probes, never in the product (Marginalia's
free key is non-commercial, CC-BY-NC-SA; Jina Search was allowed for diagnostics only). Keys go into the repository
secrets the adapters already read (`UNIMATCH_EXA_API_KEY`, `UNIMATCH_TAVILY_API_KEY`, `UNIMATCH_BRAVE_API_KEY`); the
workflow's `search_provider` choice gains `tavily` and `brave` (ticket 03).

➡️ **Yes: Exa and Tavily; Brave only without a card.** A "free" plan that needs a card is an overage risk, and the
rule of this map is that nothing can cost money by accident.

---

❓ **Q4** — **The owner's computer as the self-hosted runner** (the `runner: self-hosted` input already exists in
`benchmark-capture.yml`) for the knowledge-base refresh (07), the own-index ceiling (04) and the access ledger (08):
the production `Fetcher` unchanged — our own user agent, robots.txt honoured, crawl-delay honoured, no retry around a
refusal — only the IP differs. 76 % of the KB's 312 evidence URLs open from GitHub runners; 51 answer HTTP 403 on 28
hosts and 21 are robots-refused on 10 hosts. A robots refusal is per user agent and stays refused at home; only the
403s can differ. The live product path never runs there.

➡️ **Yes, under those conditions.** This is a different vantage point with the same honest identity, not a proxy
to evade a block: a site that refuses datacenter IPs and admits a person's computer has made that choice itself, and
we never pretend to be a browser. A host that refuses at home too stays "unavailable" and its KB facts go stale
honestly.

---

❓ **Q5** — **The own index as a product generator** (`local_index`, ticket 05): built only if ticket 04 shows that
sitemaps plus two link hops from the homepage reach the gold on each set at least as often as Serper's row; stored
under `backend/data/` (never committed), rebuilt by the same free cron as the KB refresh, behind a flag, measured on
one capped paired arm; its queries are not HTTP requests to the site, so the 60-request budget is untouched.

➡️ **Yes, conditional on 04.** It is the only option with no quota and no terms but our own; 04 costs three hours
and one runner job and says whether it can work before six hours are spent building it.

---

❓ **Q6** — **A model as a hint** (ticket 09): in this map, an offline audit on the 44 development cases and a design
note only — a URL proposer behind the fusion seam with the sitemap's weight, verified by the same classifier,
confirm and quote check as any lead, fed the public institution / field / level words only (the `DiscoveryIntent`,
which carries no applicant data by construction), under D9 (zero-retention provider or a local model). Nothing is
built until 03 and 05 report.

➡️ **Yes.** A chat assistant's answer alone has no quote and no date and invents URLs; as a *hint* it costs one read
per URL and can be measured like any generator. The 44-case audit tells whether that read is worth spending.

---

❓ **Q7** — **Hours and the stopping rule**: ≤ 15 worker-hours offline, three runner jobs (one GitHub, two
self-hosted), ≤ 300 free queries per provider for the replay; the map stops at the rule in `map.md` or when a free
tier changes its terms mid-map.

➡️ **Yes.** —

---

❓ **Q8** — **Paired runs while search is free**: the loop's paired-run step stays suspended except for arms whose
provider is `none` or `local_index`; a run on a free allowance needs the preflight (`search_preflight`) and a
per-run query cap (ticket 02) and is refused by the harness above it; no run uses a paid key.

➡️ **Yes.** The old cadence spent ≈ 300 queries a run; every free allowance together is ≈ 5 000 a month.

## Evidence

- `backend/evaluation/research/runs/2026-10-17/LOOP_REPORT.md` cycle 1 (Exa MCP vs Serper) and the outage section;
  `docs/process/STAGE_SUMMARY_DEV_2026-10-19.md` (gold returned per set); `SEARCH_PROBE.md` (2026-09-21, 1/10 → 9/10);
  `HELDOUT_STAGE_SUMMARY_2026-10-19.md` (gold never returned 4–6/9, aggregates only).
- KB evidence outcomes from the CI reports under `backend/evaluation/research/expert/data/kb_drafts.2026-10-19/batch*/evidence_check.ci-*.json`
  (312 URLs: 237 ok, 51 HTTP 403, 13 robots_disallowed, 8 robots_crawl_delay, 3 misc); `runs/2026-10-06/access_probe_fly.md`.
- Provider terms: `../assets/provider-survey-2026-10-19.md`.

## Done when

The owner has answered Q1–Q8 in `OWNER_QUESTIONS.md`; the answers are copied here under `## Answer`; `map.md`
"Decisions so far" carries one line.
