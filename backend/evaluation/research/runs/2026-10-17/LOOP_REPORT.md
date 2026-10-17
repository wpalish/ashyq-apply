# Loop report, finish plan v2 (2026-10-17)

Scored against the **unsigned** drafts `ground_truth.draft10.json` (cohort) and
`heldout.draft1.json`, built from 19 independent expert drafts whose quotes the
production fetcher verified (evidence check 39059316157: 100/128).

## Cycle 1: is the search provider the bottleneck?

Built: Serper as the benchmark's search layer (owner's key, `search_provider=auto`).
Ran: cohort 39058503662 and heldout 39058505075, all rules at their defaults.

| run | provider | known core answered | claim precision | programme page |
|---|---|---|---|---|
| cohort rl1 37545452839 | Exa MCP | 9/27 | 46/46 | 6/10 |
| cohort 39058503662 | Serper | 7/27 | 27/29 | 6/10 |
| heldout 37554279823 | Exa MCP | 0/23 | — | 0/7 readable |
| heldout 39058505075 | Serper | 0/23 | — | 0/7 readable |

Finding: **no**. Swapping the provider moves nothing on unseen sites; the
programme page is lost after search (a Serper smoke query returns TUM's exact
programme page first, the pipeline never confirms it). Root cause under
analysis in `docs/process/DISCOVERY_ANALYSIS_2026-10-17.md`.

Defects found:
- D1 (precision, UBC, Serper run): "Deadline November 15, 2026 … deadline to
  apply and submit an award application if you wish to be considered for the
  … Scholarship" read as the admission deadline. Root cause: a deadline
  conditioned on an award application is claimed as ADMISSION_DEADLINE.
  Queued as rule DL-3.
- D2 (measurement): the expert-draft converter stamped the request's field
  and intake on label evidence; the scorer compares scope literally, so a
  correct NTU claim scored as wrong scope. Fixed (`label_scope`), test added.
- D3 (measurement): the verify script's exact-substring check rejected quotes
  whose table cells the expert joined with " | ". Fixed: words in order,
  separators ignored; a changed figure or a paraphrase still fails.

Decision (delegated): keep the nine heldout universities for the final check
only and build a new development cohort (dev2) for discovery tuning.

## Cycle 2a: DL-3 (award-conditional deadline)

Run 39063173594 (cohort, Serper, off/on/on/off). Wrong claims: off#1 2 (UBC
2026-11-15), on 0 in both repetitions; stable losses 0; known core 7/27 both
arms. The right UBC deadline (2027-01-15) is not a stable gain: Serper's path
does not always reach /dates-deadlines/. **On by default** (precision gain, no
loss; owner delegation).

## Side finding: the golden demo test was a time bomb (product bug)

`WebScholarshipAdapter._derive_availability` judged "deadline passed" on the
server's local `date.today()` while `_stage_assess` uses the run's UTC day.
After 2026-10-15 TUM's Deutschlandstipendium flipped in stored results; CI was
red on main from 2026-10-17. Fixed in 06323a8; full suite 94.87%.
