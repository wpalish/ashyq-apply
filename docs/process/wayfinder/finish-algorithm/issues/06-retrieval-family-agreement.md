# Build the rank rule ticket 05 names (candidate: family agreement)

Type: task
Status: resolved (not built)
Gist: not built — ticket 05 found no single rule covering ≥ 2 cases without a predicted loss; unibo, tcd, unsw, ubc, ctu go to the residue (16).
Blocked by: 05
Map: ../map.md · AFK task — one flag, one paired run on all four sets; exists only if ticket 05 says one rule
covers ≥ 2 cases with no predicted loss. Disjoint from workers A/B: touches `retrieval.py` only.

## Goal

Read the gold page when the provider returns it and confirm reads something else first (unibo, unsw, tcd, ubc;
ctu if worker B has not already landed it). Shape to start from (05 may replace it): a candidate URL returned by
**two or more** query families, or at rank 1 of the `local_language` family, is promoted ahead of a single-family
URL of equal or lower `rank_candidates` score — a tie-break, never a new score; the confirm predicate is
unchanged; the number of confirm reads (`MAX_PROGRAM_CANDIDATES_CHECKED`) is unchanged.

## Guard (what RK-2 taught)

The rule must not displace any page read today on uba or unsw: before the paired run, replay the base2 traces
offline (`search_results` + today's scores) and show the promoted list per case; a case whose confirmed page would
drop out of the first eight is a predicted loss and the rule is reshaped or dropped before any run.

## Files (the lock)

`backend/app/adapters/search/retrieval.py` (`rank_candidates` / the ordering step only), `backend/app/config.py`
(the flag), `backend/evaluation/research/live.py` (the `--retrieval-family-agreement` switch, one line),
`backend/tests/test_retrieval*.py`. **Not** `live_discovery.py` (workers A/B).

## Flag

`RETRIEVAL_FAMILY_AGREEMENT` · harness `--retrieval-family-agreement` · loop id RA-1 · off.

## Done when

- Offline replay table committed with the PR (per case: list before/after, confirmed page position).
- Paired run `expert_paired` on cohort, dev2, dev3, dev4 (2 reps per arm, `extra_args=--retrieval-family-agreement`):
  stable gain on ≥ 1 of unibo/unsw/tcd/ubc, **no stable loss on any set, 0 new wrong claims, 0 new wrong
  programme page, `cases_over_budget` 0**, reads not above the off arm by more than the promoted reads.
- Default-on under the cycle-4c delegation (01 Q5) or rejected into `hypotheses.json` with the cause; either way one
  table in the loop report and a HANDOFF §8 line.

## Evidence

Ticket 05's table; LOOP_REPORT "RK-2 … rejected" (uba, unsw lost both reps; hku once);
`scratchpad/runs/rk2-{dev2,dev3}/x/` for the displacement.

## Answer

Not built. Ticket 05 ([analysis](../../../RETURNED_NOT_READ_2026-10-18.md)) found no rule that meets this ticket's
entry bar: one rule covering ≥ 2 cases with no predicted loss. The offline replay guard was run in 05, and it
rejects every shape it tried:

| rule | gain | predicted loss |
|---|---|---|
| this ticket's shape | unibo only | uba, warsaw, ctu |
| local_language rank 1 first | unibo only | warsaw, ctu |
| family count | tcd | ethz 4/4 |

No flag, no CLI switch, no paired run. The cases go to ticket 16 with these causes:

- **unibo:** a one-family English sibling is ranked first.
- **tcd:** the joint-honours sibling is confirmed first.
- **unsw:** the provider's order flips.
- **ubc:** the degree word, BA against BSc.
- **ctu:** the gold is at local_language 5 only (worker B).

Recorded for `hypotheses.json`: RA-1, family agreement, rejected before build, cause above.
