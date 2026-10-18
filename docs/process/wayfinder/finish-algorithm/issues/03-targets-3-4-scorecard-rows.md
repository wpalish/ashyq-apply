# Targets 3 and 4 as scorecard rows, with the readable denominators

Type: task
Status: resolved
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

## Answer

2026-10-18, worker: done as written, with the owner's 01-Q2/Q3 «да» (2026-10-18) applied — the readable
denominator is target 4's row and `unavailable` is judged per repetition. `scorecard.py` only (`metrics.py`
unchanged: its `ratio` and `adjudicate_programme_pages` are reused); new `backend/tests/test_scorecard_readable.py`
(15 tests); DoD change-log line dated 2026-10-18.

- **Unavailable, per repetition** (`Arm.access_by_rep`, `case_readable`, `_wire_access`): `access` is `BLOCKED`, or
  half or more of the case's requests on the wire failed in that repetition's `.raw.json`. Counted on the wire:
  cache hits and our own privacy refusals leave `pages_checked`; those refusals and 404s on robots.txt/sitemap
  probes leave `pages_failed`. Without this unibo base2 off#2 (7 timeouts, 8/17 raw, 8/14 on the wire) stayed in,
  and um off#2 (5 probe 404s, 1 privacy refusal, 8/18 raw) would have left on wire counts alone. A case with no raw
  report stays. The per-case `access` cell keeps the raw counts.
- **Unreadable label** (`failed_hosts`, `label_exclusion`): every evidence URL of the label is a PDF (`pdf`) or on
  a host (`www.` folded) whose every request in that repetition's `.log` failed (`host_failed`; robots.txt and cache
  hits do not count, any outcome but `ok` is a failure; a host never requested is not failed — another registrable
  domain stays).
- **Rows** (`rep["readable"]`, `readable_rows`): `programme_found_on_readable` (hit per
  `adjudicate_programme_pages`: twins in, related not a hit; denominator = `programme_status == known` and
  readable), `wrong_programme_pages` (cases whose outcome is `wrong`), `core_known_rate` (= `known core answered`),
  `core_known_readable_rate` (question level; a question stays when the case is readable and one of its known
  labels is readable), `excluded` (case -> `access`, or `<pdf|host_failed>:<question>`). Metric table gains
  `known core answered (readable)`, `programme page on readable`, `wrong programme pages`.
- **Targets**: `programme_found_on_readable >= 1.0`, `wrong_programme_pages <= 0`, `core_known_readable_rate >= 0.8`
  (default `--core-denominator readable`; `all` judges `core_known_rate` instead), after `cases_over_budget`, so
  the old target rows keep their text and order.
- **Per case**: `excluded` and `page n/N` cells appended to each row.
- **Old output**: on base2 cohort/dev2/dev3/dev4 every line of the previous `sc.md` is still present; per-case rows
  and their header only gain the two trailing cells (checked line by line, and a test).

### Targets 3 and 4 under both denominators, base2 (for the loop report)

Repetitions off#1 / off#2 / on#1 / on#2; worst repetition per arm in brackets.

| set | programme page on readable | wrong programme pages | known core answered (all) | known core answered (readable) |
|---|---|---|---|---|
| cohort | 5/8, 6/8, 6/8, 5/8 (0.625 both arms) | 2, 1, 0, 1 | 11/28, 12/28, 12/28, 11/28 (0.393) | 11/20, 12/20, 12/20, 11/20 (0.550) |
| dev2 | 5/6, 5/6, 4/6, 2/6 (off 0.833, on 0.333) | 0, 0, 1, 1 | 5/21, 5/21, 5/21, 4/21 (off 0.238, on 0.190) | 5/18, 5/18, 5/18, 4/18 (off 0.278, on 0.222) |
| dev3 | 9/10, 8/9, 7/9, 8/9 (off 0.889, on 0.778) | 1, 0, 0, 0 | 8/28 ×4 (0.286) | 8/23 ×4 (0.348) |
| dev4 | 4/5, 3/4, 3/5, 4/5 (off 0.750, on 0.600) | 0 ×4 | — (no core labels) | — |

Pooled target 4 per repetition: 24, 25, 25, 23 of 77 (30–32%) on the old denominator, the same numerators of 61
(38–41%) on the readable one. Every target-3 and target-4 row is NO on every set and arm; wrong pages are 0 in both
arms only on dev4. Unavailable: aalto, toronto, kaznu, ub in every repetition; kuleuven in off#2/on#1/on#2; unibo in
off#2 — ticket 04's host set exactly. Unreadable labels: kaist `host_failed` (cost, scholarship,
scholarship_international); `pdf` warsaw, tec (scholarship_international), utokyo (deadline), msu (gpa,
scholarship_international), usp (scholarship, scholarship_international).
