# Worker B (in flight): missed programme pages — tsinghua, kuleuven, ub, iitd, uio, uba, ctu

Type: task
Status: claimed
Blocked by: —
Map: ../map.md · AFK task, **already in progress** (2026-10-18). Registered for the frontier and for 05/06/16.

## Goal

Target 3 on dev2/dev3/dev4: tsinghua (reached; gold on another registrable domain — `never` seen), kuleuven
(BLOCKED 12/12 — `unavailable` is the right answer; verify it is reported so), ub (13/18 failed, Cloudflare
challenge — same), iitd (PARTIALLY_BLOCKED, `never` seen), uio and uba (found in most repetitions, missed in one —
flaky), ctu (gold `returned` by the `local_language` family, never read).

## Bar

As ticket 11. Classes for the residue (16) if a case stays missed: tsinghua **other registrable domain**;
kuleuven, ub **access**; iitd **access / never returned**; uio, uba **host flakiness** (01 Q3) or **order**;
ctu **returned, not read** (hand to 05/06 if the fix is rank, keep here if it is confirm).

## Files the worker holds

`backend/app/adapters/discovery/live_discovery.py` (shared with worker A by landing order),
`backend/app/adapters/search/intent.py`, `prefilter.py`, `ontology.json`, their tests. **Not** `retrieval.py`
(ticket 06).

## Done when

As ticket 11: paired-run table, HANDOFF §8 lines, every case stably found / `unavailable` / named in 16.
