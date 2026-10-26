# Demo order vs brief §5.7 — 2026-10-19

The question: `seed_demo.py` does not print the order in `analysis/AI_TASK_BRIEF.md` §5.7, yet
`TestDemoRunIsByteIdentical` is green. Did the golden baseline drift away from the brief?

**Short answer: no.** The demo table has not changed at all since ranking v2 was first wired into the
runner (`0b8d97f`, [0.5], 2026-09-05). All three divergences have been there from that first commit.
The §5.7 table never came from the product. It came from `analysis/reference/ranking_v2.py::_demo`,
which skips one knock-out rule and approximates one axis. No code, test or golden was changed for this
note.

## 1. The two tables

### Product, HEAD `835d139`

`UNIMATCH_DEMO_MODE=true UNIMATCH_ENABLE_BROWSER_TIER=false`, run on a fresh migrated SQLite in a
scratch directory, `DEMO_PROFILE` with the default priorities. Rows are ordered by `score_total`
(= `sort_key`). The bucket is `payload.ranking.bucket`.

| # | University | v1 | fit | coverage | sort_key | Bucket |
|---|---|---|---|---|---|---|
| 1 | Groningen | 6.39 | 0.820 | 0.939 | 0.795 | PLAUSIBLE |
| 2 | KU Leuven | 5.92 | 0.801 | 0.939 | 0.776 | PLAUSIBLE |
| 3 | **Tokyo** | 5.18 | 0.719 | 0.939 | 0.697 | PLAUSIBLE |
| 4 | **Toronto** | 5.54 | 0.810 | **0.735** | 0.695 | PLAUSIBLE |
| 5 | McGill | 2.06 | 1.000 | 0.255 | 0.505 | NEEDS_CLARIFICATION |
| 6 | Amsterdam | 2.06 | 1.000 | 0.255 | 0.505 | NEEDS_CLARIFICATION |
| 7 | Eindhoven | 2.06 | 1.000 | 0.255 | 0.505 | NEEDS_CLARIFICATION |
| 8 | Vienna | 3.29 | 0.678 | 0.531 | 0.494 | AMBITIOUS |
| 9 | NUS | 4.46 | 0.501 | 0.735 | 0.429 | AMBITIOUS |
| 10 | Aalto | 6.18 | 0.419 | 0.939 | 0.406 | OUT_OF_BUDGET |
| 11 | **UBC** | 6.54 | 0.413 | 0.939 | 0.401 | **OUT_OF_BUDGET** |
| 12 | Oslo | 2.46 | 0.598 | 0.386 | 0.371 | NEEDS_CLARIFICATION |
| 13 | Arizona State | 5.33 | 0.305 | 0.939 | 0.295 | OUT_OF_BUDGET |
| 14 | TU Munich | 4.91 | 0.286 | 0.939 | 0.277 | OUT_OF_BUDGET |
| 15 | Edinburgh | 1.16 | 0.521 | 0.255 | 0.263 | NEEDS_CLARIFICATION |
| 16 | Trinity College Dublin | 4.01 | 0.262 | 0.939 | 0.254 | OUT_OF_BUDGET |
| 17 | Warsaw | 4.45 | 0.260 | 0.939 | 0.252 | OUT_OF_BUDGET |
| 18 | **TU Delft** | 5.93 | — | 0 | 0 | **EXCLUDED** (IELTS writing: published minimum 6.5, applicant 6) |
| 19 | Melbourne | 3.77 | — | 0 | 0 | EXCLUDED (deadline 2026-01-15 passed) |
| 20 | EPFL | 4.57 | — | 0 | 0 | EXCLUDED (IELTS writing 6.5, applicant 6) |

### Brief §5.7, with the product value beside each brief value

| # brief | University | v1 | fit | coverage | Bucket | Product # / bucket |
|---|---|---|---|---|---|---|
| 1 | Groningen | 6.39 | 0.83 | 0.97 | PLAUSIBLE | #1 PLAUSIBLE (0.820 / 0.939) ✓ |
| 2 | KU Leuven | 5.92 | 0.80 | 0.94 | PLAUSIBLE | #2 PLAUSIBLE ✓ |
| 3 | Toronto | 5.54 | 0.82 | 0.77 | PLAUSIBLE | **#4** PLAUSIBLE (0.810 / 0.735) ✗ |
| 4 | Tokyo | 5.18 | 0.72 | 0.94 | PLAUSIBLE | **#3** PLAUSIBLE ✗ |
| 5 | TU Delft | 5.93 | 0.68 | 0.97 | AMBITIOUS | **#18 EXCLUDED** ✗ |
| 12 | UBC (was #1) | 6.54 | 0.43 | 0.97 | OUT_OF_BUDGET | #11 OUT_OF_BUDGET (bucket ✓, position off by one) |

The v1 column matches the brief exactly. The AGENTS.md §5 acceptance line ("Groningen #1, UBC in
OUT_OF_BUDGET") passes.

## 2. Bisection

Each commit's `backend/` was extracted with `git archive` into a scratch directory. Each was run on a
fresh SQLite with the clock frozen at 2026-09-07, the golden capture date. HEAD was also run on the real
clock (2026-10-19). Every run below printed a table identical to the one above: the same rows, order,
buckets, knock-out reasons, and fit, coverage and sort_key to 6 decimals.

| Commit | Date | What it is |
|---|---|---|
| `0b8d97f` | 09-05 | [0.5] first commit where the runner writes `ranking`: **divergences first appear here** |
| `f018307` | 09-06 | PR #2 merged ([0.1]–[0.8]) |
| `65e1522` | 09-08 | T32: `GOLDEN_DEMO_SHA256` introduced |
| `9f8a71f` | 09-21 | V2-22 golden re-capture |
| `768e8d7` | 09-22 | owner decision: programme rule beside a university-wide rule (Delft IELTS 6.5 vs 6.0) |
| `4bb50d9` | 09-28 | last golden re-capture (previous-cycle deadline) |
| `87e315e` | 10-04 | PR #43 |
| `efea7ab` | 10-17 | loop report 2c |
| `19a7288` | 10-18 | R2 default on |
| `835d139` | 10-19 | HEAD (frozen clock and real clock) |

Before `0b8d97f` there is no `ranking` in the payload. At `844e225c`, just before [0.1], the v1
pipeline ran. Running `analysis/reference/ranking_v2.py` over that commit's stored demo rows reproduces
brief §5.7 to the second decimal: Groningen 0.83/0.97, Leuven 0.80/0.94, Toronto 0.82/0.77,
Tokyo 0.72/0.94, Delft 0.68/0.97 *ambitious*, UBC #12 0.43/0.97 *out_of_budget*. So §5.7 is the
reference script's output, and the product has never printed it.

**The golden baseline did not cause this.**
- `GOLDEN_DEMO_SHA256` first appears on 09-08, three days after the divergences. It was re-captured 14
  times, from `9f8a71f` to `4bb50d9`, and never moved the demo order. Every re-capture note beside the
  constant says "no bucket, rank … moved", and the sweep above confirms it.
- The golden cannot guard §5.7 even in principle. `TestDemoRunIsByteIdentical` replays the pipeline with
  the conftest `profile` fixture ("Test Applicant (synthetic)"), not `DEMO_PROFILE`. It hashes payloads,
  not the `DEMO_PROFILE` order. A green golden says nothing about `seed_demo.py` against §5.7.

## 3. Each divergence

| Divergence | Introduced | Cause | Golden regenerated then? | Classification |
|---|---|---|---|---|
| **TU Delft EXCLUDED, not AMBITIOUS #5.** EPFL (brief: not listed, reference: ambitious #10) and Melbourne go the same way. | `0b8d97f` [0.5], when the runner calls `rank_result`. The knock-out itself is in `0f46079` [0.3], `domain/ranking_v2.py`. | Brief §5.4 rule 2: a confirmed hard filter (`RequirementCheck.is_hard_filter`) is a knock-out. The demo profile's IELTS writing 6.0 misses a published 6.5 per-band minimum at Delft and EPFL. Melbourne's 2026-01-15 deadline has passed. The reference `_demo` never applies rule 2. Delft was already GAP / AMBITIOUS fit at `844e225c`, so the owner's 09-22 IELTS decision (`768e8d7`) changed nothing here. | No (the golden did not exist yet) | **Intended. Brief §5.7 is stale** (it contradicts the brief's own §5.4). Documented at the time as "Deviation from the §5.7 sample, by design … the spec beats the sample" in HANDOFF §6 (`a721804`) and in the PR #2 body, which the owner (wpalish) merged on 2026-09-05. Never put in HANDOFF §8. The HANDOFF note was dropped in a later rewrite (`c220095`), so it now survives only in PR #2. No explicit owner decision beyond the merge. |
| **Toronto #4 / Tokyo #3** (brief: Toronto #3). Toronto coverage is 0.735, not 0.77. | `0b8d97f` [0.5]. The axis itself is in `0f46079` [0.3]. | `post_study_work` is UNKNOWN for every row: `ranking_v2.py` calls `u_post_study_work(None, …)` with the comment "Months are parsed from ClaimType.POST_STUDY_WORK_MONTHS in [2.2]. Until then the axis says unknown rather than inventing a number". The reference instead assumes 24 months whenever `post_study_work` is non-empty. Toronto loses a known axis (weight 0.0306) and Tokyo does not, because it was already unknown in the reference. The two then sit 0.002 apart: 0.697 vs 0.695. With PSW known at 1.0, Toronto would score about 0.715 and be back at #3. The same axis explains Groningen's 0.97 → 0.94. | No (the golden did not exist yet) | **Intended code behaviour. Brief §5.7 is stale, and this is a documentation gap, not a regression.** It follows brief §5.2 (months not parsed → UNKNOWN) and brief §10 (PSW months deferred to [2.2]). §5.7's own footnote warns that the reference simplifies career/post_study_work, but promises only third-decimal differences, not a reordering. The swap was **never flagged as a deviation**: PR #2 printed "KU Leuven #2 · Tokyo #3 · Toronto #4" and still ticked "`seed_demo` matches §5.7". [2.2] is still not done: `ClaimType.POST_STUDY_WORK_MONTHS` does not exist at HEAD. |
| **UBC "FULL_TUITION, not OUT_OF_BUDGET"** | none | Not a divergence. `seed_demo.py` does not print the bucket. Its "Funding" column is `best_funding_classification`, which is FULL_TUITION for UBC. `ranking.bucket` is **OUT_OF_BUDGET** (gap 21,471 = 3.6× the 6,000 ceiling, past the decisive 1.5× limit). UBC is #11, not #12, only because EPFL moved from ranked to EXCLUDED (row 1 above). | — | **No divergence in the bucket.** The position is a knock-on effect of row 1. |

## 4. Consequences (not acted on here)

- The brief §5.7 table and the "Toronto #3 → #8" sensitivity line under it describe the reference
  script, not the product. If the owner wants the brief to be the oracle, §5.7 needs rewriting to the
  product table in §1 above, with notes on Delft, EPFL and Melbourne (§5.4 rule 2) and on PSW unknown
  until [2.2].
- The real demo-order guard is the AGENTS.md §5 line (Groningen #1, UBC OUT_OF_BUDGET), and it passes.
  No test pins the `DEMO_PROFILE` order. `TestDemoRunIsByteIdentical` uses another profile.
- When [2.2] lands, Toronto should go back to #3. That will move the golden and the demo order, and the
  move is expected.
