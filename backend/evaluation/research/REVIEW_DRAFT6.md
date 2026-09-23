# Draft6: the Delft programme identity

AI-prepared source annotations accessed 2026-09-22; **0/10 human verified**.
There are **61/219 known/total labels** — unchanged from draft5 — and now
**10/10 programme identities**. One field changes. Every earlier dataset, report,
worksheet, the capture and all other values are unchanged.

## Source decision

[TU Delft, Bachelor of Computer Science and Engineering](https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/bachelor-of-computer-science-and-engineering)
is the official programme page and its heading is verbatim "Bachelor of Computer
Science and Engineering". That resolves the exact bachelor identity the requested
scope asks for, which every draft since draft2 has carried as the last `unknown`.

The OCW alias earlier drafts kept reaching is not that page and errored twice; it
stays in the record as the existence evidence it always was, not as the identity.

Nothing else is taken from the page. Its 15 January deadline belongs to a
Matching & Selection procedure whose academic year the requested fall 2027 scope
does not establish, and the numerus fixus and Maths B statements are likewise
unscoped to that intake. Copying any of them would repeat the other-year transfer
every draft has refused. `deadline`, `intake`, `country_credential`, `ielts.*`,
`sat.*`, `tuition` and the document families stay UNKNOWN for Delft.

## Replay and review

```sh
# From backend
python -m evaluation.research --dataset evaluation/research/data/ground_truth.draft6.json --capture evaluation/research/baseline/capture.json --out evaluation/research/baseline/metrics.draft6.json --allow-drafts
```

The same frozen capture yields programme precision **1/9**, recall **1/10**;
claim precision **0/5**, recall **0/61**, critical coverage **0/210**.

**Read the two programme numbers carefully: they fall, and that is the correct
result.** Resolving a ground-truth identity does not improve retrieval — it adds a
tenth answerable case and a ninth judgeable prediction, so both denominators grow
while the frozen capture's one correct page stays one. This is an annotation
change, not a pipeline run; no quality improvement or regression is measured here.
Claim and coverage figures are identical to draft5.

Use [the draft6 worksheet](REVIEW_WORKSHEET_DRAFT6.md) for all 61 known fields.
Review the new Delft identity against the page itself before accepting it. The
remaining Kazakhstan fall-2027 intake, fee and general SAT/IELTS evidence is still
unresolved. Finalize field applicability, adjudicate evidence independently and
obtain ten actual human reviewer/date signoffs before strict acceptance. A
worksheet is not a signature. V2-10 remains after V2-01 acceptance only.
