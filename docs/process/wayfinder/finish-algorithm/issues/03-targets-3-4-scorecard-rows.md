# Targets 3 and 4 as scorecard rows, with the readable denominators

Type: task
Status: open
Blocked by: —
Map: ../map.md · AFK task — measurement only; no discovery or evidence code changes. Needed before the exit
gate (17) can be read mechanically. Builds both denominators now; ticket 01 decides which one the target row uses.

## Goal

`python -m evaluation.research.scorecard RUN_DIR` judges targets 1, 2 and 5 on the worst repetition
(`TARGETS` in `backend/evaluation/research/scorecard.py`). Targets 3 and 4 are read by hand from the per-case
table. Add them as rows so "met" is the scorecard's verdict, and print the two denominators of ticket 01 Q2 side
by side until the owner picks one.

## Work

1. `metrics.py` / `scorecard.py`: per case and repetition, `readable` = `access` not `BLOCKED` **and** fewer than
   half of the case's requests failed (reuse `_access`); per known core label, `evidence_readable` = the label's
   evidence URL host is not a host whose every request failed in that repetition's `.log`/`.raw.json`, and the
   evidence URL does not end in `.pdf`. Record the reason when a label or case is excluded (`access`, `host_failed`,
   `pdf`).
2. New metric rows: `programme_found_on_readable` = programme hits ÷ cases with `programme_status == known` and
   `readable` (twins and `related` per today's `metrics.adjudicate`); `wrong_programme_pages` (count);
   `core_known_readable_rate` = known core questions answered ÷ known core questions whose labels are
   `evidence_readable` (question level, as `core_known` does today); keep `known core answered` unchanged beside it.
3. `TARGETS`: `programme_found_on_readable >= 1.0`, `wrong_programme_pages == 0`, `core_known_readable_rate >= 0.80`
   — judged on the worst repetition like the others; a `--core-denominator all|readable` option (default
   `readable` only after 01 is answered; until then the table prints both columns and the target row says
   `pending owner decision 01-Q2`).
4. Per-case table: an `excluded` column naming the reason for that repetition; a stability column `page n/N`
   (programme hit in n of the N repetitions of the arm) — the input ticket 04 reads.
5. Tests: `backend/tests/test_scorecard*.py` — a blocked case leaves the denominator, a half-failed host leaves it,
   a PDF label leaves the denominator while its HTML sibling stays, a non-English page stays, a case with no
   programme page found stays; frozen-replay outputs byte-identical for the existing rows.

## Files (the lock)

`backend/evaluation/research/scorecard.py`, `backend/evaluation/research/metrics.py`,
`backend/tests/test_scorecard*.py`, `docs/process/SEARCH_DEFINITION_OF_DONE.md` (one dated line under "Change
log" **only after** 01 Q2/Q3 are answered — the worker drafts it, the planner commits it).

## Done when

- `scorecard` on `scratchpad/runs/base2-{cohort,dev2,dev3,dev4}` prints the new rows; the old rows are
  byte-identical; the loop report gets one table "targets 3 and 4 under both denominators, base2".
- Gates green (`ruff`, `mypy`, `pytest --cov-fail-under=92`); golden demo untouched (no product file changed).

## Flag

None — measurement. Scorecard option `--core-denominator`.

## Evidence

`scorecard.py` L45 (`TARGETS`), L286–305 (`core_known`), L311–335 (`cases_over_budget`), L423 (`_access`);
`scratchpad/runs/base2-dev2/sc.md` (tcd `REACHED (7/40 failed)` miss in on#1 while hit in off#1/off#2 — the
flaky-host shape); `docs/process/CORE_GAP_ANALYSIS_2026-10-18.md` §1 group X (A5 access 7, A6 other domain 3).
