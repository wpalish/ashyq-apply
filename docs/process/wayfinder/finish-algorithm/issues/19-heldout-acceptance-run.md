# The heldout acceptance run under ticket 21's protocol

Type: task
Status: open
Blocked by: 17
Map: ../map.md · AFK task — the destination's last step. The protocol is decided (previous map, ticket 21: ≤ 2
looks, pre-registered expectation, two arms × two repetitions, aggregates only); this ticket executes it. If
ticket 18 was opened, it waits for 18's answers.

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
