# Reproduce failure 2 on development: the gold-knockout arm (what confirm does when the gold is absent)

Type: task
Status: open
Blocked by: —
Map: ../map.md · AFK — harness code (measurement only), then one paired run per development set; `loop-engineering`.

## Question

On the nine, identity recovery confirmed 5 pages and 4 were wrong, with the gold never returned in 4–6 of 9. On
development the gold is returned in 36 of 39 labelled cases, so we have almost never *observed* what the confirm
step does when the gold is out of reach — except on the cohort, where 3–5 wrong pages are confirmed per column
beside the gold (masked: the case still reads hit). The DoD says "a site that refuses us says unavailable, never a
guess". **When the gold programme page cannot be reached, does discovery abstain (`programme unresolved`) or confirm
a sibling?** This ticket makes the gold unreachable on purpose, on development only.

## Build (measurement only, `live.py`)

`--knockout-gold`: before the capture, the harness reads the case's gold `programme_urls` and declared twins from the
development dataset (`--dataset` already names it) and installs a fetcher-level refusal for those canonical URLs
(and their `/`-, `.html`- and `?lang=` variants per `metrics._page_forms`): the request is counted (it is on the
wire — target 5 unchanged), the response is replaced by a synthetic 404, and the trace records
`knockout: <n urls refused>` (count only). Nothing else differs. The capture records `config.knockout_gold = True`.
The refusal lives in the benchmark's `bounded()` fetch wrapper (`capture_one`, L878), never in `Fetcher`.
For a case whose gold is `unknown` (no programme label) the arm is a no-op and the trace says so.

## Runs (main session dispatches)

cohort, dev2, dev3, dev4 — `expert_paired`, `extra_args=--knockout-gold` (off = today, on = gold refused),
parallelism 5. Later dev5 (after 14) if the owner's design-blind protocol allows an aggregate-only read.

## Read (stage summary + scorecard, per set, on arm)

- `confirmed_pages_{hit,related,wrong}` and `case_outcome:*` with the gold refused: every `hit` must vanish; what
  replaces it — `missed` (abstained: the honest outcome) or `wrong` (a sibling confirmed)?
- `identity_recovery_leads_confirmed`, the refusal rows (`subject_mismatch`, `degree_level_other`, `reads_as:*`),
  `programme_candidates_read`; claims emitted on the on arm and how many are `unlabelled` vs `wrong_value` /
  `wrong_scope` (the heldout's 37–44 claims with 3 matched is the shape to look for).
- Per set, the **guess rate** = wrong confirms ÷ cases with a refused gold. Development reference for the heldout's
  4/5 — recorded as a number, not compared to the nine beyond the one sentence the map already holds.

## Deliverable

`docs/process/GOLD_KNOCKOUT_2026-10-19.md`: per set, the on-arm funnel against the off arm, the guess rate, the
list of development cases where a sibling was confirmed with *which refusal rule would have caught it* (title/h1
subject absent, degree level absent, only one lead family, URL-only subject match, catalogue hub, faculty page) —
this table is 09's specification. Verdict: **failure 2 reproduced** if the guess rate ≥ 0.3 on any set.

## Files the worker holds

`backend/evaluation/research/live.py` (`capture_one`: the `bounded()` wrapper and the flag; lands after 02 and 06),
`backend/evaluation/research/stage_summary.py` (a `knockout` row in the funnel; after 06's header line),
`backend/tests/test_research_benchmark.py` (the refusal is a 404 with the request counted; a case without gold is a
no-op). Nothing under `app/`.

## Evidence

- `HELDOUT_STAGE_SUMMARY_2026-10-19.md`: `identity_recovery_leads_confirmed 5`, `confirmed_pages_wrong 4`,
  `gold_never_seen 4–6`; `STAGE_SUMMARY_DEV_2026-10-19.md` cohort `confirmed_pages_wrong 3–5` beside
  `confirmed_pages_hit 5`; `live.py` L858–900 (`observed_confirm`, `bounded`), `metrics.py` L396–450
  (`_page_forms`, `same_programme_page`).

## Done when

Four runs scored; the doc and the Answer give the guess rate per set and the refusal-rule table; 09 is unblocked.
Flag: none (harness). Loop id: **G-07**.
