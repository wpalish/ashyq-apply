# dev5 core-question labels (the six core questions; four expert workers)

Type: task
Status: open
Blocked by: 03
Map: ../map.md · AFK experts → owner signs `dev5.draft2.json`. Starts as soon as a country group's programme page is
drafted (it does not wait for the signature); only signed pages enter the final file.

## Goal

Target 6 is read on `core_known_readable_rate`; without core labels dev5 predicts nothing about it. For each dev5 case:
English test minimum (`ielts.overall` / subscores / `english_evidence.<test>.minimum`), `gpa` (grade threshold as a
string, or `not_applicable` for a test-score threshold, or `unknown` for prose — 02-Q7), `deadline` (`YYYY-MM-DD`,
population stated — 02-Q5's international-round rule), tuition (`period` as published — 02-Q4; never multiplied),
scholarship exists, scholarship open to an international applicant — each `known` / `not_applicable` / `unknown` with
an official URL and a verbatim quote, under the rules of `expert/core_drafts.py` (verification, English, GPA, deadline,
award conventions). Apply the eight signed conventions of corpus round 02 from the start, so dev5 never needs the
reconciliation round that H-A says the nine never got.

## Four parallel workers

Same country groups as 03 (KZ / TR / CZDE / ITLT); same protocol; `scholarship-audit` on every award (class, who is
eligible, what is covered — never "full ride" from a headline). Output
`backend/evaluation/research/expert/data/core_drafts_dev5.2026-10-19/<case>.json` in the shape of
`core_drafts_dev4.2026-10-18`. Award bindings: each named award page gets a `Binding` row proposal (kind `award`,
`source_url`, `subject` = the award name as the page spells it, `key = scholarships.<id>`) for
`identity_bindings.dev5-draft2.json` — the H-E test (11) counts how many dev5 awards the pipeline could ever map.

## Verification and signing

`mode=verify_evidence` on the runner; the assembler runs a `core_drafts_dev5.py` converter (copy of
`core_drafts_dev4.py` with dev5 paths) → `dev5.draft2.json` + `identity_bindings.dev5-draft2.json` + the signing
worksheet (`SIGN_DEV5_CORE_2026-10-19.md`, the form of `SIGN_DEV4_CORE_2026-10-18.md`). The owner signs in round 2.
Non-English evidence pages are labelled as such (`<html lang>` in the note), PDFs too — they stay in the file; the
scorer's denominator rules decide what counts.

## Files the workers hold

`expert/data/core_drafts_dev5.2026-10-19/*` (disjoint per case); assembler: `core_drafts_dev5.py`,
`data/dev5.draft2.json`, `data/identity_bindings.dev5-draft2.json`, `docs/process/SIGN_DEV5_CORE_2026-10-19.md`,
the workflow `MEASUREMENT_BINDINGS` line (replace the draft1 bindings path from 02).

## Evidence

- `expert/core_drafts.py` docstring (the label rules); `SIGN_DEV4_CORE_2026-10-18.md`; finish-algorithm ticket
  [02](../../finish-algorithm/issues/02-corpus-corrections-round.md) (the eight conventions) and
  [09](../../finish-algorithm/issues/09-dev4-core-labels.md).

## Done when

Every dev5 case has six core rows; every `known` row has a runner-verified quote; the worksheet is in
`OWNER_QUESTIONS.md` round 2. Flag: none. Loop id: **G-04**.
