# The heldout acceptance run under ticket 21's protocol

Type: task
Status: claimed
Blocked by: 17
Map: ../map.md · AFK task — the destination's last step. The protocol is decided (previous map, ticket 21: ≤ 2
looks, pre-registered expectation, two arms × two repetitions, aggregates only); this ticket executes it. If
ticket 18 was opened, it waits for 18's answers.

**Progress (2026-10-18, planner).** 17 resolved (baseline 3), 18 answered by the owner (targets 3/4 recorded "not met",
the run proceeds, target 6 against the pooled development sets with the cohort reading beside it). **Step 1 done:**
[`docs/process/HELDOUT_PREREGISTRATION_2026-10-18.md`](../../../HELDOUT_PREREGISTRATION_2026-10-18.md) — exact dispatch
inputs, scoring command, denominators, the pooled development reference recomputed from the baseline-3 scorecards
(core readable 124/255 = 0.486, 128/255 = 0.502 with AN-1 + AN-1b; page on readable 85/112 = 0.759), the expected
ranges and both target-6 readings (primary bar 0.352, secondary 0.534), the stop and no-retune rule. **Steps 2–4 are the
main session's.** Two corrections to the text above, found while writing step 1: (i) `expert_paired` takes the nine ids
space-separated (`nu metu sabanci charles masaryk tum tartu polimi vilnius`) — `case=heldout` is the description's name
for the set, not a value `live.py --case` accepts; (ii) `--through-identity-gate` acts only on seed-only cases (`DEV2`),
so on the nine (registry institutions) both arms take the registry path, `identity established` will read 0/0, and
21-Q2 (c) is recorded *not measured* — pre-registered in §1.1 of the file, not changed here.

## Steps

1. **Pre-register** in the loop report, before dispatch: (a) programme-page recall on readable heldout sites within
   15 pp of the cohort's (03's `programme_found_on_readable`, 01 Q3 applied), with the pooled four-set development
   number beside it; (b) every refusing site `unavailable`, 0 pages confirmed on it; (c) identity established on
   every readable site on the `--through-identity-gate` arm; (d) 0 wrong programme pages (`related` is not wrong);
   (e) **target 6**: `core_known_readable_rate` on the nine within 15 pp of the cohort's; (f) targets 1, 2, 5 as on
   the development sets. Any residue recorded in 17/18 is written here as expected, by class and count only.
2. **Dispatch** one `benchmark-capture.yml` run, `mode=expert_paired`, `case=heldout`, `extra_args=--through-identity-gate`
   (so off = today's harness entry, on = the production gate), 2 reps per arm, defaults otherwise; commit SHA
   recorded. **No other heldout run** in this effort unless 21-Q1's second look applies.
3. **Read aggregates only**: the scorecard's metric rows and target rows (`scorecard --summary-only`, or the
   per-case table suppressed); per-case rows, traces, logs and captures stay closed; the artifact is kept but not
   opened beyond the summary. If the summary-only option does not exist, ticket 03's worker adds it first (one flag).
4. **Record**: DoD status table updated in `SEARCH_DEFINITION_OF_DONE.md` (met / not met per target with the date),
   the baseline row moved, one line in the change log; the map's Decisions-so-far gets the gist.
5. **If it fails**: the design returns to the development sets with the aggregate numbers as the only heldout input
   (21-Q5); the second look is spent only after a development-evidenced fix (21-Q1); a stage-level heldout
   aggregate is a separate explicit owner decision (21-Q4), asked in `OWNER_QUESTIONS.md`, never taken here.

**Note — the flag for step 3 now exists:** `python -m evaluation.research.scorecard <artifact> --summary-only
[--out summary.json]` prints and writes aggregates only — per arm and repetition the metric ratios, the readable
rows (targets 3 and 4), wrong programme pages, identity established, counts of cases scored / unavailable /
excluded / over budget / wrong claims, excluded core questions by reason, access status counts, the stable
gains/losses/unstable as counts, and the targets table. No per-case row, case id, URL, university, claim value,
label or gain/loss item appears in stdout or in the JSON (`backend/tests/test_scorecard_summary.py`, on synthetic
data; it also pins that the numbers equal the full card's and that the default output is unchanged).

## Files

`backend/evaluation/research/runs/<date>/LOOP_REPORT.md`, `docs/process/SEARCH_DEFINITION_OF_DONE.md` (status rows,
change log), HANDOFF. No code; no heldout data file touched.

## Done when

The DoD status table carries the acceptance result per target with the run id, the map's destination is marked
reached (or the second-look condition is recorded), and nothing from the heldout per-case level has been read.

## Evidence

Previous map [Acceptance protocol for the next heldout check](../../programme-discovery/issues/21-heldout-acceptance-protocol.md)
Q1–Q5 (all yes); LOOP_REPORT "Final check: the heldout nine" (the aggregate-only template); `benchmark-capture.yml`
`case=heldout`.
