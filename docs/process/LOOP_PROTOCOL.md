# Loop protocol: the owner's standing agreement (read after every context compaction)

Owner: Диас.
- Replies are in Russian and plain, decisions go in tables, and internal IDs stay out.
- This file holds what was agreed about how the search algorithm gets finished.
- It survives context compaction.

## Roles

| Role | Used for | Setting |
|---|---|---|
| Planner / orchestrator | wayfinder maps and plans; root-cause and loss-stage analysis; wrong-claim triage; reviewing a Codex PR that touches `runner.py` or a migration | the planning model at maximum effort |
| Worker | rule implementation, test alignment, label drafts, fixes | the coding model at medium effort; high only for a hard pipeline rule |

- The exact agent settings are in the session's scratchpad `AGENT_ROLES.md`. Model identifiers stay out of the repo.
- Every agent runs in its own git worktree, in the background, and commits locally.
- The session's main agent then:
  1. cherry-picks the commits;
  2. runs the gates;
  3. pushes to `claude/greeting-16wj2z`.
- Several workers run in parallel. The owner authorised maximum resources.

## The plan

- The wayfinder maps live in `docs/process/wayfinder/`:
  - `programme-discovery/map.md` covers discovery v3;
  - `finish-algorithm/map.md` covers finishing against every DoD target.
- After a compaction, re-read in this order:
  1. this file;
  2. the maps;
  3. `docs/process/SEARCH_DEFINITION_OF_DONE.md`;
  4. the tail of `backend/evaluation/research/runs/2026-10-17/LOOP_REPORT.md`.

## Loop engineering: no idle time, no waiting for the owner between cycles

1. **When a worker finishes:**
   - cherry-pick its commits;
   - run the full suite (`cd backend && .venv/bin/pytest -q -p no:cacheprovider -o addopts="" -n 4 tests`) and check its exit status;
   - run the golden demo test;
   - push;
   - dispatch paired runs for every new flag on cohort, dev2, dev3 and dev4: `benchmark-capture.yml`, mode `expert_paired`, `extra_args=--<flag>`.
2. **While the paired runs are in flight:**
   - schedule a check-in about **15 minutes** out (a run takes 10–16 minutes);
   - keep other workers busy.
3. **When the runs finish:**
   - score each set;
   - turn a flag on by default only if it shows no stable loss and no new wrong claim; otherwise a worker diagnoses it;
   - record the result in LOOP_REPORT;
   - start the next cycle at once.
4. **Owner questions:** batch them, and keep working on everything that does not depend on the answer.

## Case lists

| Set | Cases |
|---|---|
| cohort | groningen delft aalto vienna warsaw ubc toronto hku ntu kaist |
| dev2 | ethz psaclay uppsala tcd tsinghua tec uba kaznu uct khalifa |
| dev3 | imperial unsw utokyo ntutw um kuleuven auckland ucph msu iitd puc uio usp ub chula |
| dev4 | ctu vut rwth kit unibo taltech ktu boun itu |

## Hard rules

- Never open heldout files, captures, logs or labels for: nu metu sabanci charles masaryk tum tartu polimi vilnius.
- No robots bypass, no user-agent spoofing, no proxies.
- No applicant attributes in queries.
- Budget per university: 6 queries, 60 HTTP requests, 120 s.
- Never commit `backend/data/*`, `.env*` or keys.
- No pull requests unless the owner asks.
