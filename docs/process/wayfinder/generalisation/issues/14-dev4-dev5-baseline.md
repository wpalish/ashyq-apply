# The dev4 + dev5 baseline: today's defaults, both arms, design-blind on dev5

Type: task
Status: open
Blocked by: 02, 03
Map: ../map.md · AFK — two `expert_paired` runs (main session dispatches), scoring and the stage summary; `loop-engineering`.
dev5's core rows (04) join by re-score when signed — no second run.

## Goal

The development reference the second look is predicted from: dev4 (draft3) and dev5 (draft1 programme pages; draft2
core when signed) under today's defaults, four identical repetitions each, read by the scorecard rows (readable
denominator, per-repetition `unavailable`) and by `stage_summary`. **dev5 is read at aggregate level only (13-Q1).**

## Pre-registration (written in this ticket *before* dispatch, from 10 and 11)

| row | dev4 (base3, known) | dev5 expected (from the offline audits) |
|---|---|---|
| programme page on readable (hit / wrong / related / missed) | 3–4 / 0 / 1–3 / 3–5 of 9 (5 with gold) | 10's ceiling: cases with ≥ 1 acceptable page; wrong pages expected ≤ 1 if 07's guess rate is low, else ≈ guess rate × misses |
| gold returned by search | 5/5 | 08's offline estimate (LOCO without own words) |
| readable core | 2/8 = 0.25 | written only once 04's known count exists; otherwise "no prediction" |
| identity gate (if the gate arm is used) | — | 11's pass count |
| unavailable | 0–1 | 02's probe survivors: 0 expected |

Writing the prediction down is the point: 14 is the first test of whether offline audits of unseen pages predict a run.

## Runs

1. `benchmark-capture.yml`, `mode=expert_paired`, `case=<dev4 ids>`, `extra_args` and `base_args` empty (both arms
   defaults), parallelism 5, `run_tag=g14-dev4` — on the commit after 02 lands (defaults unchanged since base3 except
   AN-1 + AN-1b).
2. Same for `case=<dev5 survivors>`, `run_tag=g14-dev5`.
3. Optional third, if 01-Q4 says the second look has a gate arm: dev5 with `extra_args=--through-identity-gate`, so the
   gate's cost on unseen sites is measured on development first.

## Read

`scorecard --summary-only` and `stage_summary` on both; the full scorecard on dev4 only. Record in `LOOP_REPORT` the
rows above against the pre-registration, per column; `cases_over_budget`; `reads_per_case`. **No dev5 case id, URL or
label appears anywhere** — the tools' leak guards enforce it; the worker does not open the dev5 artifact's per-case
files (`capture.json`, logs) at all.

## Files the worker holds

`docs/process/LOOP_REPORT.md` (one section), this ticket's Answer, `scratchpad/runs/g14-*` (dev4 open; dev5 summary files only).
No code change.

## Done when

Both runs scored; the table "predicted vs read" is in the Answer and LOOP_REPORT; 13's LOCO computation has its input
(15 reads it). Flag: none. Loop id: **G-14**.
