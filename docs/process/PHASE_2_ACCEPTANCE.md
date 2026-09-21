# Phase 2 — evidence graph and scope: what was built, what was measured

Written by `claude-opus-5` on 2026-09-21/22, for the owner's review. Companion to
`backend/evaluation/research/ACCEPTANCE.md`, which covers V2-01.

Read this if you read nothing else: **the metric Phase 2 was built around did not improve.**
`wrong_scope_claim_rate` was 5/5 on the frozen capture and came back 3/3 — still 100% — on the first
honest live one. What did improve is retrieval (1/10 → 3/10 exact programme pages), and what changed
most is that the benchmark now says *why* it fails instead of only *that* it fails.

## Exit criteria from `analysis/v2/05_PHASE_2_EVIDENCE_GRAPH.md`

| Criterion | State | Where |
|---|---|---|
| source/version entities persist without overwriting historical truth | **done** | `source_snapshots`; `claims.superseded_at` / `superseded_by_id` (migrations `a1f3c8d75e29`, `c5d01b7e4f83`) |
| scope is structured, not buried in prose | **done** | `app/domain/claim_scope.py`, `app/adapters/scope_reader.py`, all five claim-producing adapters |
| current claims can be queried by entity / intake / population | **done** | `app/domain/evidence_queries.py` |
| conflict reasons distinguish true conflict from different scope | **done** | `ConflictKind`, `classify_conflict` |
| change detection can create a new version | **partly** | conditional GET + hash + supersession exist; material-change classification is in (`change_detection.py`), acting on it awaits an owner decision (§7) |
| existing claim/provenance invariants remain green | **done** | 1916 tests, 0 failed, coverage 94.68% |

Plan item **V2-22 (entity resolution)** is built but deliberately unwired: `resolve_institution` and the
registry identities exist and are tested, while `dedupe.university_key` keeps every caller until the
replacement is measured.

## What the numbers actually say

Live capture, run 35655438326, branch, Exa, 60 fetches / 90 s per case (the frozen baseline's own
budgets):

| metric | certified capture | this run |
|---|---|---|
| `wrong_scope_claim_rate` | 5/5 | **3/3 — unchanged at 100%** |
| `programme_page_recall` | 1/10 | **3/10** |
| `programme_page_precision` | 1/9 | 3/18 |
| `recall_at_5/10/20` | 1/10 | 1/9 |
| `primary_source_rate` | 13/13 | 11/11 |

Two things must be said beside those figures:

1. **Half the cohort runs out of budget.** On the frozen capture, 5 of 10 cases stopped early. Every
   recall number above is a floor, not a measurement of the pipeline's ceiling.
2. **The first live run reported nothing at all**, and looked like it had. The scoring step died, a
   `| tee` swallowed the failure, and the comparison printed a committed draft report under the
   heading "this run". Fixed, and recorded in HANDOFF §9 as the general rule: never let a pipe or a
   glob stand between a result and the thing that reports it.

## Why the headline metric did not move

The diagnostic built for exactly this question (`evaluation/research/scope_report.py`) answers it, and
it refuted my own hypothesis. I expected pages that stayed **silent** about the intake. The truth:

```
by shape:     differs=5
by dimension: programme (differs)=5
```

- **Three cases read the wrong page** — an open-day page, a "preparing for a bachelor" page, a
  visual-studies degree. That is retrieval, not scope. Two of the three are fixed at the classifier
  (an event heading is no longer a programme); the third is a real programme and a ranking problem.
- **Two cases are NTU's right programme under its full official title** — "Bachelor of Computing
  (Hons) in Computer Science" against a label reading "Computer Science". By the ontology's own strong
  aliases those are one programme. Whether the scorer should compare identity instead of strings is
  §7's first question, and I did not answer it myself: changing a metric so your own work scores
  better is not a measurement.

So Phase 2's scope work made the measurement **honest**, and the number it exposes belongs mostly to
Phase 1's job. That is a worse-sounding and more useful result than a rate that moved.

## Decisions waiting for you (all in HANDOFF §7)

1. Should the scorer compare programme *identity* or programme *strings*?
2. Should a programme-specific rule stay usable when a university-wide rule disagrees? (The guide says
   yes; a contract test says no.)
3. Should an unchanged claim still be superseded on re-read?
4. Ontology: is `Mathematical and Computer Sciences` the same field as `Computer Science`? I left it
   UNKNOWN rather than merge a joint degree into a single-subject one.
5. KAIST's Undergraduate Curriculum Roadmap has no seed category left; it or the requirements page
   holds the `program_page` slot.

## What is worth doing next, in order

1. **Re-run the capture** on the branch. Two of the five programme mismatches should disappear because
   the pages that produced them are no longer claimed as programmes — visible in the diagnostic, with
   no metric redefined.
2. **Measure `reject_irrelevant_kinds=True`** (publications and profile pages dropped at the
   prefilter). Built, tested, off by default, unmeasured: §12 allows a discovery change only when the
   benchmark improves.
3. **Raise the per-case budgets** for one run and see how much of the recall ceiling is budget rather
   than pipeline.
