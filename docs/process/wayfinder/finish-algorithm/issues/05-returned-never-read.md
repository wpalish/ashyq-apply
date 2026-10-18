# Returned by the provider, never read: the rank of the gold page against what confirm read instead

Type: research
Status: open
Blocked by: —
Map: ../map.md · AFK research — read-only on development traces (M1's `search_results` is in every base2 capture).
Decides whether ticket 06 exists and in what shape. Output: `docs/process/RETURNED_NOT_READ_2026-10-18.md`.

## Question

The scorecard's "gold seen" column says `returned` — the provider listed the gold URL, confirm never read it — on
**unibo** (three families), **ctu** (`local_language`), **tcd** (three families, the on#1 miss), **unsw**
(`field_and_degree`, `programmes`), **ubc** (two families), toronto and aalto (access). RK-2 (retrieval rank v2)
tried to fix this class and was rejected: it lost uba and unsw in both repetitions. For every development case
whose gold (or recorded twin) appears in any `search_results` row: at what rank, in which families, how many
families agree, and which eight URLs confirm read instead (`pages_read` with verdicts) — and for uba and unsw,
what exactly RK-2 changed that displaced their pages? Is there **one** rank rule that reads the gold on unibo,
ctu, tcd, unsw and ubc without displacing any page read today — e.g. "a URL returned by ≥ 2 families, or at
rank 1 of the `local_language` family, enters the confirm list before a single-family URL of equal score"?

## Done when

- One table: case · gold rank per family (`field_and_degree`, `programmes`, `natural_language`, `local_language`,
  `undergraduate`, `courses`) · families agreeing · the eight URLs read and their verdicts · what the gold
  would have needed to be read. From `x/<case>-*/*/<case>.raw.json` (`trace.search_results`, `pages_read`,
  `selected`), both arms, all repetitions, and the `rk2-*` captures for the RK-2 displacement.
- A yes/no on a single rule with its predicted effect per case (gain / unchanged / risk), and the RK-2
  post-mortem in three lines (what displaced uba and unsw). If no single rule covers ≥ 2 cases without a predicted
  loss, say so — ticket 06 is then closed as "no rule" and the cases go to the residue (16).
- No worker-A/B case is re-analysed for discovery mechanics beyond the rank table (toronto, kaist, tsinghua,
  kuleuven, ub, iitd, uio, uba, ctu are theirs); ctu and tcd appear here only as rank rows.

## Files

Read-only: `scratchpad/runs/{base2,ap1c,rk2}-*/x/`, `backend/app/adapters/search/retrieval.py`
(`rank_candidates`, `discover_candidates`), `backend/app/adapters/discovery/live_discovery.py`
(`_select_candidates`, `MAX_PROGRAM_CANDIDATES_CHECKED`). Writes only the analysis file.

## Evidence

`scratchpad/runs/base2-dev4/sc.md` (unibo `returned (returned:field_and_degree, returned:local_language,
returned:natural_language)`), `base2-dev2/sc.md` (tcd on#1), `base2-dev3/sc.md` (unsw), LOOP_REPORT "RK-2 …
rejected, off" (loses uba and unsw in both reps; hku once).
