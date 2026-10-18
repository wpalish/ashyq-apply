# Worker A (in flight): wrong or missed programme pages — toronto, hku, kaist, tcd

Type: task
Status: claimed
Blocked by: —
Map: ../map.md · AFK task, **already in progress** when this map was charted (2026-10-18). Registered so the
frontier skips it and tickets 05/06/16 can reference it. The worker keeps its own write-ahead in HANDOFF §5.

## Goal

Target 3 on the cohort and dev2: toronto confirms a wrong page in some repetitions while 22/23 of its requests
fail (403) — a refusing site must say `unavailable`, never a guess; hku confirms the `cs.hku.hk` page in some
repetitions and a wrong one in others (`admissions.hku.hk` robots unreachable); kaist is reached (1/18 failed) but
the gold is seen only as a walker link dropped as `short_label` (opaque URLs, department host `cs.`); tcd is a hit
in some repetitions and a miss or wrong page in others (host 7/40 failed, gold `returned` by three families).

## Bar (the map's standard)

Each change one flag, flag-off → `expert_paired` on cohort, dev2, dev3, dev4 (2 reps per arm) → default-on only
with **no stable loss on any set, 0 new wrong claims, 0 new wrong programme page, `cases_over_budget` 0**. A rule
that fails twice on the same cause → `hypotheses.json`, and the case goes to the residue (16) with its class
(toronto, hku admissions: **access**; kaist: **opaque URL / department host**; tcd: **host flakiness** → 01 Q3).

## Files the worker holds

`backend/app/adapters/discovery/live_discovery.py`, `backend/app/adapters/page_classifier.py`,
`backend/app/adapters/discovery/catalog_walker.py`, their tests. Ticket 06 stays out of these; worker B shares
`live_discovery.py` only by landing order (one PR at a time).

## Done when

Its paired-run table is in the loop report, the flag names are in HANDOFF §8, and each of the four cases is
either stably found/`unavailable` or named in 16 with its class. The planner then sets `Status: resolved` and
copies the gist to the map.
