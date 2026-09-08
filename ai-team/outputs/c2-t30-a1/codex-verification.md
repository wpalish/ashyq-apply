# T30 independent verification — 2026-09-08

## Authorization boundary

The owner instructed Codex to execute the actions requested by the prior GLM
dispatcher. This was recorded as authorization for exactly two bounded public
canary batches of five institutions each. Fetcher robots, SSRF, PII and host
politeness guards stayed enabled. Temporary SQLite databases and a synthetic
bachelor/CS profile were used. No production data or secrets were involved.

No additional live batch is authorized by this record.

## Result

| Batch | Programme recall | Category recall | Material FP | Seconds |
|---|---:|---:|---:|---:|
| Groningen, Delft, Aalto, Vienna, Warsaw | 3/5 | 13/15 | 0 | 638.3 |
| UBC, Toronto, HKU, NTU, KAIST | 4/5 | 13/15 | 0 | 681.6 |
| **Combined** | **7/10** | **26/30** | **0** | **1319.9** |

The measured KPI reaches the frozen floor exactly. It does not prove the
registry-expansion half of T30.

## Evidence and repair

- Raw JSON/Markdown reports are in `live/batch-1/` and `live/batch-2/`.
- Totals: 481 HTTP reads, 14 browser reads, one PDF read, 15 catalogues walked,
  20 programme leads confirmed and 239 `SourcePage` rows across the two DBs.
- HKU exposed a malformed/PDF catalogue parsing failure. A minimal `<f/{>`
  regression was made RED, then fixed by parser fallback in `5c42934`.
- The same HKU root completed post-fix with 22 candidates, one confirmed
  programme and 52 recorded outcomes.

## Honest incomplete item

`institution_registry.json` remains at 19 entries. The frozen acceptance rule
allows a new entry only after a canary proves at least two of four categories.
There is no reviewed 41-institution candidate set with official seeds in the
task inputs, so no names were fabricated and 19→60 is not claimed.

This work was executed directly by Codex under a system-level no-subagent
constraint. No planner/QA/reviewer invocation IDs or acceptance packet were
invented; evidence consists of commits, tests, raw canary artifacts and gates.
