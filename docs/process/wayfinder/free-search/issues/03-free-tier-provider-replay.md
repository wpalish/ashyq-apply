# Replay the six queries of the 44 development cases on every free tier the owner opened

Type: task
Status: open
Blocked by: 01 (Q3 keys), 02 (the cap)
Map: ../map.md · AFK, one capped live job per provider on the GitHub runner; `loop-engineering`. Spends free
allowances only, under the cap; never a paid key.

## Question

Does any free tier return the gold programme page on the 44 development cases as often as Serper's recorded lists
(base3: cohort 8/10, dev2 9/10, dev3 11–12/14, dev4 5/5)? The captures record Serper's top-10 per family but not the
query text; the queries are deterministic from public words (`queries_for(DiscoveryIntent)`), so the comparison is
exact: rebuild the same six queries, send them once per provider, score the lists the same way.

## Build (evaluation tooling only)

1. **Probe** `evaluation/research/free_provider_replay.py` (or `query_probe` mode extended): for every case of
   cohort / dev2 / dev3 / dev4 build the `DiscoveryIntent` exactly as `live.py` does (institution, domain, field
   `computer science`, bachelor, institution country), take `queries_for(intent)` (the six families, R5's local shape
   included — a provider without `search_localized` gets the words without `hl`/`gl`, as `discover_candidates` does),
   send each once through the configured adapter, record `{case, family, urls[:10]}` — public URLs only, no query
   text, as WF-17 records them. Hard cap 300 queries per run (02's guard); `search_preflight` first.
2. **Score**: `metrics.returned_matching_gold` against the dev gold files with the recorded twins
   (`identity_bindings.*`, `programme_url_aliases` from the base3 traces); rows per set: gold returned (any family),
   per family, rank of the gold where returned; the same rows recomputed from the base3 Serper lists as the control.
3. **Providers**: `exa` (keyed, free credit), `tavily`, `brave` if opened, `exa_mcp` (keyless) — one job each,
   `search_provider` workflow choice extended with `tavily` and `brave`; dev5 is not sent (design-blind).
4. **Cost**: the dashboard balance before and after each job, written down; per-query cost derived.
5. **Terms**: one row per provider — storage/caching of results (we store URLs and titles only, never snippets as
   evidence), attribution, commercial use — quoting the provider's page (`../assets/provider-survey-2026-10-19.md`).

## Deliverable

`docs/process/FREE_PROVIDER_REPLAY_2026-10-xx.md`: the table provider × set (gold returned / Serper control), per
family, cost per query read off the dashboard, terms row, and the verdict against 01-Q2's bar ("no worse by more than
one case on any set"). A provider that passes becomes the candidate default for the product's `live` mode (owner
decides in 10); one that fails is recorded with its numbers so nobody retries it without new evidence.

## Files the worker holds

`backend/evaluation/research/free_provider_replay.py` (new), `.github/workflows/benchmark-capture.yml` (the
`search_provider` choice list and one job), `backend/tests/test_free_provider_replay.py` (query rebuild equals
`queries_for`, cap, redaction: no query text, no applicant word, no `site:` in the artifact). Read-only:
`intent.py`, `metrics.py`, the gold files. Disjoint from 02's cap code (02 lands first; 03 calls it).

## Evidence

`STAGE_SUMMARY_DEV_2026-10-19.md` (`gold_returned_by_search`, `returned_by_family:*`); programme-discovery ticket
[17](../../programme-discovery/issues/17-record-provider-results.md) (what the trace records); M5 probe
(`../../programme-discovery/assets/m5-query-probe-2026-10-18.md`: shape matters more than provider on local-language
cases); `SEARCH_PROBE.md` (Exa 2026-09-21).

## Done when

The doc is committed with one row per opened provider and the control row; the balances before/after are in it;
no paid key was configured in any job (the workflow log names the provider and the secret).
