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
| 6 | No overfitting: on the heldout universities, core coverage is within 15 percentage points of the pooled development sets (owner, 2026-10-18; the cohort reading is reported beside it) | `core_known_readable_rate` on the heldout split, worst repetition, against the pooled cohort + dev2 + dev3 + dev4 rate (primary) and the cohort's (secondary); both pre-registered before the run | not measurable yet: heldout has no signed labels |

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
- 2026-10-18 (owner): a case ended by the wall clock (`BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED`) counts as over the 120 s budget in `cases_over_budget` (scorecard default; `--no-count-timeouts-over-budget` gives the old count).
- 2026-10-18 (owner, finish-algorithm 01-Q2/Q3): targets 3 and 4 are judged by the scorecard's own rows, on the worst repetition, leaving out a case in the repetition where its site was unavailable (`BLOCKED`, or half or more of its requests on the wire failed; cache hits, our privacy refusals and 404s on robots.txt/sitemap probes are not the site failing). Target 3: `programme_found_on_readable` ≥ 1.0 (twins count, a related programme does not) and `wrong_programme_pages` = 0. Target 4: `core_known_readable_rate` ≥ 0.80, whose denominator keeps a known core question only when one of its labels' evidence is an HTML page on a host that answered in that repetition; a non-English page, another registrable domain and a case whose programme page was not found stay in. `--core-denominator all` prints the old `known core answered` measure as `core_known_rate`. Targets 1, 2 and 5 are unchanged.
- 2026-10-18 (owner, finish-algorithm 18-Q1 — «все как рекомендовано»): **target 3 is recorded "not met"** at the development exit (clean baseline 3, runs 39172483236 / 39172484697 / 39172486984 / 39172488858, four repetitions of today's defaults per set): `programme_found_on_readable` cohort 5/8 in every repetition, dev2 4–5/6, dev3 8/9–10, dev4 3–4/4–5; `wrong_programme_pages` 0–2 per repetition (cohort 0–2, dev2 0–1, dev3 0–1, dev4 0). Residue by class (docs/process/RESIDUE_LEDGER_2026-10-18.md, Table A): department host / opaque URLs 1 (kaist), other registrable domain 1 (tsinghua), returned-not-read 4 (hku, ctu, unibo, kuleuven when its host answers), provider rank 2 (unsw, iitd — flaky), degree word 1 (ubc), order / stage clock 3 (tcd, rwth, uio/puc — flaky); `unavailable` by definition: aalto, toronto, ub, kuleuven 16/20, kaznu. No rule is attempted on these classes (01-Q4 stopping rule); the measure is unchanged.
- 2026-10-18 (owner, 18-Q2): **target 4 is recorded "not met"**: `core_known_readable_rate` pooled over the four development sets 124/255 ≈ 0.49 on baseline 3 (per repetition 30/63, 32/64, 30/64, 32/64 — ≈ 48 %; per set cohort 13–14/19 = 0.68–0.74, dev2 6–7/18 = 0.35–0.39, dev3 8–9/18 = 0.44–0.50, dev4 2/9 = 0.22). Residue by class (ledger Table B, question level, typical repetition): not linked / client-rendered 9, non-English evidence without a route 9, other host never linked 4, other registrable domain 3, returned-not-read 3, ours-still 4 (none flips a set); outside the denominator: access 12 (+3 hku in some repetitions), PDF 6 (re-enter only when PD-1 is on). **The measure is not changed**: the denominator stays `core_known_readable` as defined on 01-Q2 — no exclusion for non-English, never-linked or other-domain evidence is added.
- 2026-10-18 (owner, 18-Q2 (c) and 08-Q3): a **model-based extractor** for the six core questions (D9, proposer-only, verifier against the page text, privacy table unchanged) is not part of the finish-algorithm map. It may open only as a separate map, and only **paired with a rule that reaches the pages** it would read — on today's captures 13 of the 16 non-English evidence pages and all 6 PDF evidence pages are never fetched, so a reader alone gains 0 — with its price and its privacy-table row written before any run.
- 2026-10-18 (owner, 18-Q3): the **heldout acceptance run** (finish-algorithm ticket 19, protocol of programme-discovery ticket 21) **goes ahead** with targets 3 and 4 recorded "not met". The development numbers, the residue by class and count, and both target-6 readings are fixed before dispatch in docs/process/HELDOUT_PREREGISTRATION_2026-10-18.md; aggregates only are read (`scorecard --summary-only`).
- 2026-10-18 (owner, 18-Q4): **target 6's reference set is the pooled development sets** (cohort + dev2 + dev3 + dev4), not the cohort alone: the cohort is the English-site set and does not represent the nine's countries. Reading: the nine's `core_known_readable_rate` on the worst repetition is within 15 pp of the pooled development rate (primary); the original cohort reading is pre-registered too and reported beside it (secondary). Table row 6 updated; both readings are written down before the run.
