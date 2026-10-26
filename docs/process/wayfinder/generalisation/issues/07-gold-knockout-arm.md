# Reproduce failure 2 on development: the gold-knockout arm (what confirm does when the gold is absent)

Type: task
Status: resolved (harness built; the four runs are the main session's to dispatch)
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

## Answer

**Harness built, no run dispatched** (worker, 2026-10-19). Measurement only: nothing under `app/` changed, `Fetcher`
is untouched and the off arm is byte-identical (`TestDemoRunIsByteIdentical` green; no new field is serialised off
the arm).

- **Flag:** `--knockout-gold DATASET` in `backend/evaluation/research/live.py`. `live.py` has no `--dataset`, so the
  flag takes the development dataset path itself. Forwarded parent → child (`--knockout-gold <path>`) →
  `capture_one(knockout_gold=...)`; the capture records `config.knockout_gold = true` and
  `config.knockout_dataset = <file name>`. The parser refuses a missing file or a heldout `--case`;
  `GoldKnockout.from_dataset` refuses a heldout case id, a non-`development` split and a case absent from the file.
- **What is refused** (`GoldKnockout`, in the benchmark's `bounded()` wrapper only): every URL in the case's
  `programme_urls` (so a twin listed in the label is refused too), matched on `metrics._page_forms` (trailing `/`,
  `index.html`, `.htm`/`.html`, intake-year segment) plus any `lang=` query parameter dropped, with the scheme and a
  leading `www.` ignored. A matching read is answered *before* the wrapped `get` with
  `FetchResult(HTTP_ERROR, 404, error="KNOCKOUT_GOLD; synthetic 404, not read")`. No request reaches the Fetcher or
  the wire, but the read spends the page budget (`fetcher_calls` in strict mode, the legacy page cap otherwise).
  After a real read, the result is replaced by the same 404 when its `final_url` is a gold form (a redirect onto the
  gold) or the page declares a gold form as its `hreflang` alternate (`live_discovery.declared_alternates`: a twin
  the label does not list). A case whose gold is unlabelled is a no-op (`knockout: no-op` in the log).
- **Recorded:** `Telemetry.knockout_gold_urls` (gold URLs made unreachable; 0 = no-op) and
  `Telemetry.knockout_refused` (reads answered with the 404), count only; the case log prints
  `knockout: <n> urls refused`.
- **New rows** (`stage_summary`, discovery funnel, on arm only): `knockout_cases`, `knockout_cases_gold_refused`,
  `knockout_cases_no_gold_noop`, `knockout_reads_refused`, **`knockout_guess_cases`** (a programme page confirmed
  while the gold was knocked out), `knockout_guess_cases_wrong`, `knockout_guess_pages`, `knockout_guess_pages_wrong`,
  `knockout_guess_pages_related`, `knockout_abstained` and `knockout_leaked_hits` (must stay 0: a hit means a gold
  form got past). **Guess rate = `knockout_guess_cases_wrong` ÷ `knockout_cases_gold_refused`**, per column.
- **Tests:** `backend/tests/test_gold_knockout.py`: forms matched and not matched; on, a synthetic 404 with no
  request and the budget spent, with the redirect and the hreflang twin replaced; off, nothing refused and nothing
  serialised; the no-gold no-op; the heldout and validation refusals; parent → child forwarding and config; the
  stage-summary rows.

### Dispatch inputs (main session; `benchmark-capture.yml`, working directory `backend`)

All four: `mode=expert_paired`, `base_args` empty, `case_parallelism=5`, other inputs default (`runner=ubuntu-latest`,
`seconds_per_case=120`, `max_pages=60`, `search_provider=auto`). Off = today, on = gold refused.

| set | `case` | `extra_args` (score with the same file as `--dataset`) |
|---|---|---|
| cohort | `groningen delft aalto vienna warsaw ubc toronto hku ntu kaist` | `--knockout-gold evaluation/research/data/ground_truth.reviewed11.json` |
| dev2 | `ethz psaclay uppsala tcd tsinghua tec uba kaznu uct khalifa` | `--knockout-gold evaluation/research/data/dev2.draft3.json` |
| dev3 | `imperial unsw utokyo ntutw um kuleuven auckland ucph msu iitd puc uio usp ub chula` | `--knockout-gold evaluation/research/data/dev3.draft3.json` |
| dev4 | `ctu vut rwth kit unibo taltech ktu boun itu` | `--knockout-gold evaluation/research/data/dev4.draft3.json` |

Read per set: `python -m evaluation.research.stage_summary <artifact> --dataset <same file>` and the scorecard. The
deliverable `docs/process/GOLD_KNOCKOUT_2026-10-19.md`, the guess rates and the refusal-rule table are written once
the runs are scored. dev5 waits for 14 and the owner's design-blind protocol.
