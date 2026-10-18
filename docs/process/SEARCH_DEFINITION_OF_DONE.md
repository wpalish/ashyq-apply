# Search algorithm — Definition of Done

**Status.** The improvement plan of 2026-10-05 (eval-driven development:
fix the measuring stick → error analysis → one rule at a time against the
signed corpus → heldout check) proposed these targets. The owner approved the
plan the same day ("Начинай выполнение по плану"). Changing a target needs
the owner's approval and is recorded here with the date.

**How it is measured.** `python -m evaluation.research.scorecard RUN_DIR`
(from `backend/`) on an unpacked `expert_paired` artifact. It scores every arm
and repetition with the official scorer against the latest signed corpus and
judges each target on the **worst** repetition. Targets live in
`backend/evaluation/research/scorecard.py` (`TARGETS`, `BUDGET`).

## Targets

| # | Target | Measure | Baseline 2026-10-05 |
|---|---|---|---|
| 1 | At least 95% of the values we state are right | `claim_precision` ≥ 0.95 | 31/42 = 0.74 |
| 2 | At most 3% of values describe the wrong population, year or programme | `wrong_scope_claim_rate` ≤ 0.03 | 5/42 = 0.12 |
| 3 | The programme page is found on every site the run can read; a site that refuses us says "unavailable", never a guess | `programme_hit` on every case whose `access` is not `BLOCKED` and whose own pages mostly load | 6/10 overall; misses: Aalto (blocked), Toronto (HTTP 403 on 21/30 pages), HKU (admissions host unreachable), KAIST (reached, programme not confirmed) |
| 4 | At least 80% of the six core questions are answered wherever the official site publishes the answer and lets us read it | core answers ÷ core labels marked `known` in the signed corpus | not measurable yet: the corpus marks most core questions `unknown` (Phase 0.2, corpus draft8) |
| 5 | Per university: at most 6 search queries, 60 HTTP requests to university sites (every request on the wire: redirect hops, retries and robots.txt count; owner decision 2026-10-18), 120 s | `cases_over_budget` = 0 | 5/10 cases send 7 queries (discovery 6 + scholarship search 1) before ER-08 |
| 6 | No overfitting: on the heldout universities, core coverage is within 15 percentage points of the cohort | scorecard on the heldout split | not measurable yet: heldout has no signed labels |

The six core questions are those of `app.pipeline.runner.CORE_QUESTIONS`:
English test minimum, GPA, deadline, tuition or total cost, a scholarship
exists, the scholarship is open to an international applicant.

## The loop every change goes through

1. A cause from the error analysis (counted, largest first) or an expert
   trace where the cause is unclear.
2. One general rule behind a flag, with offline tests.
3. A paired run (off/on/on/off) on the cohort; the scorecard must show
   **no stable loss, no new wrong claim**, and either a stable gain or fewer
   reads with identical labels.
4. The owner approves turning it on by default; the baseline above moves.

A rule that fails step 3 twice is recorded as rejected in
`backend/evaluation/research/expert/data/hypotheses.json` and not retried
without new evidence. Every three or four enabled rules, the heldout split is
run once; rules are never tuned on it.

## Change log

- 2026-10-18 (owner, option A): a "read" in target 5 is every HTTP request to a university site, as `http_fetches` already counts it (`live.py` patches `fetching._pinned_request`). Code caps must meter the same number. See docs/process/READ_BUDGET_ANALYSIS_2026-10-18.md.
