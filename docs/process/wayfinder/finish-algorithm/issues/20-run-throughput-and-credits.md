# How many paired runs can run at once, and what each costs

Type: research
Status: open
Blocked by: —
Map: ../map.md · AFK research — the wall-clock optimisation needs the real constraint. Output: a short section in
the loop report ("Run throughput") and a line in HANDOFF §9 (traps).

## Question

The map assumes up to five workers each dispatching four `expert_paired` runs (one per set, ~25 min, `case_parallelism
5`). What actually limits that: GitHub Actions concurrent-job limits on this plan (the workflow runs one job per
dispatch; how many were observed running at once in today's run ids 3911…–3915…?), the Serper credit cost per run
(queries per case × cases × 4 repetitions; credits left on the key), the provider's rate limit when 20 runs hit it
at once (`429` handling in `serper.py` — a 429 is a lost query, which changes the measurement), and the sites
themselves (five universities at once per run; two runs on the same set double-hit the same hosts — is that within
robots `crawl-delay` and the rate limiter, or does it make a paired run's off and on arms non-comparable?).

## Done when

- A table: constraint · observed value today · the safe number of concurrent runs · what breaks first.
- A rule for the workers: how many paired runs may be in flight at once, whether two runs may share a set at the
  same time (recommendation: never — the same hosts see double load and `access` flips), and the dispatch order
  that keeps the critical path (worker C/D runs before 06's).
- Serper credits: cost per full paired run on the four sets, credits remaining, and the number of rules that buys;
  if fewer than the map's open tasks need, say so (the owner tops up or the map orders by expected gain).

## Files

Read-only: `.github/workflows/benchmark-capture.yml`, `backend/app/adapters/search/serper.py`,
`backend/app/adapters/fetching.py` (rate limiter, crawl-delay), GitHub Actions run list via `gh api`. No code.

## Evidence

LOOP_REPORT run ids per rule (four per rule); `benchmark-capture.yml` `case_parallelism` note ("5 since run
39076880836: same labels as serial, 12 min instead of 45"); M5 probe cost (30 credits for 30 queries).
