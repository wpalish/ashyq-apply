# T26 contract audit — 2026-09-08

## Verdict

`BLOCKED_SCOPE_CONTRACT`. Do not implement T26 from the current task card.

## Why

The product promise is a dated News layer that an applicant can see separately
from verified facts, with source/date/applicability and no silent mutation of
material claims. The frozen `allowed_paths` permit only models, domain code,
`pipeline/runner.py`, a migration and backend tests. They exclude all three
seams needed for a real vertical slice:

1. a source or discovery adapter that creates a `NewsEvent` from official data;
2. an API schema/route that exposes events;
3. frontend types, client and presentation for the separate News block.

A migration and unused model would satisfy the file list while failing the
user-visible product requirement. That would be false completion.

## Required decision before code

Choose one contract and freeze it in `crew.json` and `tasks/T26.md`:

- **Vertical slice (recommended):** authorize the relevant discovery/extraction
  adapter, API schema/route, frontend types/client/view/tests, plus the existing
  model/domain/migration/runner paths. Acceptance must include a fixture-driven
  official-event ingest, source and event dates, applicability, API output and a
  separate UI block. No live network in tests.
- **Storage foundation:** explicitly remove UI/ingestion claims and accept only
  an additive `NewsEvent` model/migration/domain contract. Keep the task named
  as a foundation, not a completed News layer.

T28 and T32 satisfy the dependency side. The blocker is contract authority,
not technical uncertainty.
