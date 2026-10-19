# Query and read volume ledger, the free-tier arithmetic, and a guard against spending by accident

Type: research
Status: open
Blocked by: —
Map: ../map.md · AFK, offline — captures, stage summaries and provider documentation only. Output: a ledger document
and a small harness change (a per-run query cap), no pipeline rule.

## Question

"Free" is a number only once the demand is one. How many provider queries does (a) one paired run per set, (b) one
applicant's research in the product, (c) one knowledge-base refresh cost today, and how many of each does every
free allowance buy a month? And can the harness make it structurally impossible to spend an allowance — or a paid
key — by accident, the way the 2026-10-19 outage spent eight runs on a dead provider before anyone read the logs?

## Ledger (from the base3 captures and `STAGE_SUMMARY_DEV_2026-10-19.md`; no run)

1. **Per case and per column**: `discovery_queries` and `search_calls_total` for cohort, dev2, dev3, dev4 (the cohort
   reads 33–39 discovery queries and 39–40 search calls per 10 cases per column); mean, max; the share of the six
   families actually sent; the scholarship query (`SQ-1`) on top.
2. **Per run**: columns × cases × queries; the old loop's ≈ 170 runs reconciled with the ≈ 50 000 credits.
3. **Per applicant in the product**: ≤ 6 per university (brief) × the typical shortlist (the demo's twenty? the
   catalogue selector's top-k) → queries per research; and the KB path's zero.
4. **Per KB refresh**: zero queries (07 re-reads URLs, it does not search) — 312 HTTP reads on 154 hosts.
5. **Allowances** (`../assets/provider-survey-2026-10-19.md`): Exa $10/month (instant search $4 per 1 000; the adapter
   asks for `highlights`, which Exa bills as contents — read the real per-query cost off the dashboard after 03's
   replay), Brave $5/month at $5 per 1 000, Tavily 1 000 credits at 1 per basic search, Exa MCP ≈ 50/day/IP. Table:
   allowance → paired runs per month → applicant researches per month → KB refreshes (0 needed).
6. **Quota-exhaustion codes**, one line each, and whether the adapter maps them to `SearchUnavailable` with a test:
   Serper 400 (2026-10-19), Exa 402 (2025-09-24), Tavily 432 (2025-09-25), Brave 429/402, Exa MCP rate-limit text. The
   product shows "Search service unavailable (<provider>; HTTP n)" and never guesses — confirm, do not change.

## Guard (harness only; `evaluation/research/live.py`, `search_preflight.py`, workflow)

- `--max-search-queries N` per capture (default the brief's 6 × cases × columns): the counted search wrapper refuses
  the (N+1)th query locally with `SearchUnavailable`, the capture records `search_budget_exhausted`, the scorecard
  reads the run as invalid-as-measurement (the outage guard of `e9948442` already does this for failures).
- The workflow refuses `expert_paired` on a keyed provider unless `extra_args` carries the cap, and prints the
  provider and the cap in `out/config.txt`.
- Tests: the cap trips at N+1 with no request sent; preflight failure still starts no capture.

## Deliverable

`docs/process/SEARCH_VOLUME_LEDGER_2026-10-19.md` with the tables above; the cap in the harness with tests; a line in
HANDOFF §8 (flag name) and §9 (the trap: a free allowance's reset day is the 1st — a run on the 31st can straddle it).

## Files the worker holds

`backend/evaluation/research/live.py` (counted search wrapper only), `backend/evaluation/research/search_preflight.py`,
`.github/workflows/benchmark-capture.yml` (one guard step), `backend/tests/test_search_preflight.py` or a new
`test_benchmark_query_cap.py`, the new doc. Disjoint from 03 (probe script) and 05 (adapter).

## Done when

The ledger is committed with the numbers per set; the cap is on with tests; the map's arithmetic note is corrected
if the measured demand differs from its estimate (≈ 600–700 queries per four-set run; ≈ 60 per applicant research).
