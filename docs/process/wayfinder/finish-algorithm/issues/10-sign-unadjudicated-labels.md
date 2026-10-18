# Sign the programme-page labels for the 12 unadjudicated cases

Type: task
Status: resolved
Blocked by: 15
Map: ../map.md · HITL task — worker E (ticket 15) proposes; the owner signs in round 2. Until signed, the 12
cases count in no target-3 denominator (`programme_status != known`) and their 15 known core labels (tec 3, kaznu
2, uct 1, utokyo 3, ntutw 1, msu 3, usp 2) count in target 4's.

## Question

Nothing to decide about the algorithm: twelve development cases (dev2: tec, kaznu, uct, khalifa; dev3: utokyo,
ntutw, msu, usp; dev4: vut, taltech, boun, itu) have no programme URL in the gold, so the scorecard prints
`unlabelled` and the page we confirm there is neither a hit nor a wrong page. Worker E's proposal table (URL,
verbatim title, declared twin, degree, language, `how_found`, verified quote) arrives per case. For each: accept
the proposed page as the programme page; mark `related` (a specialisation or another CS programme); or
`unknown` with the reason (SPA catalogue — tec; PDF-only study plan — utokyo; site refuses the runner — kaznu
certificates). Per 03/01 Q2 a case signed `unknown` for an access reason leaves the target-3 denominator; one
signed `unknown` for an SPA/PDF reason is `unresolved`, reported, and also leaves it (previous map 01 Q6).

## Done when

- The owner has marked each of the 12 rows; the agent writes `dev2.draft2.json` / `dev3.draft2.json` /
  `dev4.draft2.json` (coordinated with ticket 09's dev4 file — one writer at a time), re-scores `base2-*` and the
  latest defaults captures, and records the new target-3 denominators per set in the loop report.
- Rows signed `known` whose page we already confirm move the stable "found" count; rows we confirm a *different*
  page on become wrong pages — those go to the residue (16) by name, with the worker that owns the host.

## Evidence

`scratchpad/runs/base2-{dev2,dev3,dev4}/sc.md` (`unlabelled`, `no_gold`); ticket 15; previous map
[What counts as the programme page found](../../programme-discovery/issues/03-programme-identity-equivalence.md).

## Answer

Owner (Диас), 2026-10-18: «Раунд 2 и 3: все как рекомендовано» — accept tec, kaznu, uct (+related), khalifa (+related), ntutw, msu, usp (both campuses), taltech related += faculty page; utokyo unknown; vut, boun, itu unchanged. Applied after the CI verify_evidence run of the proposals.

## Done

- `dev2.draft3.json` / `dev3.draft3.json` (`2026-10-18.dev2-draft3` / `dev3-draft3`): tec, kaznu, uct (related
  BA Informatics, BBusSc CS), khalifa (+ AR twin; related ZMU), ntutw, msu and usp (IME + ICMC) are
  `known` with official `programme_evidence` from the 13 verified proposal quotes; utokyo stays `unknown`. The
  core labels of these cases are unchanged and unsigned. `dev4.draft3.json`: taltech related += the IT
  faculty IAIB page; vut, boun, itu unchanged.
- Re-scored base3 and an1b read-only (LOOP_REPORT, "Signed labels: tickets 09 and 10"). Target-3 denominators:
  dev2 6 → 9, dev3 9–10 → 12–13, dev4 4–5 unchanged (taltech now `related` in 8/8). Stable found: kaznu,
  khalifa, usp hit 8/8. Missed: tec 8/8, msu 8/8, ntutw 6/8. New wrong pages, to residue ticket 16 by name:
  uct (5/8 reps; related in the other 3) and ntutw (on#2 of both runs).
