# Draft3: lossless document-field projection

`data/ground_truth.draft3.json` is derived from frozen draft2, with **0/10 human
verified cases**. No new source facts, pipeline run, retrieval improvement or
eligibility decision are claimed. Draft1, draft2 and their reports remain unchanged.

Seven known document records become thirteen explicit fields. The corpus now has
**52 known / 212 total labels**, compared with 46/206 in draft2. This is a change
in measurement granularity, not six additional discoveries.

| Case / old document key | New suffixes | Meaning retained |
|---|---|---|
| Groningen / admission.secondary_diploma | completed; not_completed | Diploma versus school enrolment statement, conditional on completion. |
| Groningen / admission.transcript | completed; not_completed | Academic record versus school course list, conditional on completion. |
| Groningen / admission.translation | required_unless_language_in | The entire language-exemption list stays together; no unconditional required flag. |
| Groningen / programme.course_descriptions | initial_upload; board_may_request | Blank upload permission and possible later request remain distinct, scoped to NIS Grade 12. |
| Toronto / programme.supplemental_application | required | Existing boolean, still scoped to Computer Science at St. George. |
| NTU / scholarship.nanyang_global.essay | required; maximum_words | Requirement and word limit independently addressable by the mapper. |
| NTU / scholarship.nanyang_global.referee | required; role; family_or_relative_allowed | Requirement, school-teacher role and family restriction remain separate. |

All keys retain the `documents.` prefix. Explicit booleans become `.required`;
object members keep their original names and JSON values. Evidence, access date,
scope, critical flag, notes, unknown labels and all non-document facts are unchanged.
There is no inferred `.required=true` for a conditional document alternative.

The [projection manifest](data/document_projection.draft3.json) records exact
source/target keys, projection modes and canonical dataset hashes. The regression
test reconstructs every original record, checks JSON types and rejects unexplained
additions or losses. The source and target versions remain drafts.

## Offline replay and limits

From `backend`:

```sh
python -m evaluation.research --dataset evaluation/research/data/ground_truth.draft3.json --capture evaluation/research/baseline/capture.json --out evaluation/research/baseline/metrics.draft3.json --allow-drafts
```

The same frozen capture gives programme precision/recall **1/8**, claim precision
**0/5**, claim recall **0/52**, and critical-field coverage **0/203**. Claim
adjudication stays **5/13**; support adjudication stays **0/13**. Operation counters,
scholarship rates and all other metrics are unchanged. The two larger denominators
reflect projection granularity and must not be described as a pipeline regression.

The mapping-contract test demonstrates that `.required` and `.maximum_words` now
join the new labels; a wrong limit or absent evidence earns no precision credit.
It is synthetic, not a new live document extraction. The discovery canary does
not run post-approval document collection. Real identity aliases still need review.

Generic UNKNOWN document-family placeholders remain, as do conditional alternatives
that the current mapper cannot express. Coverage is therefore a provisional field
inventory, not a final exhaustive applicant checklist. Do not treat the language
exception list or completion alternatives as an unconditional requirement.

## Remaining review

Use [the draft3 worksheet](REVIEW_WORKSHEET_DRAFT3.md), which includes every known
field, its source, scope, conditions and the unresolved fields. Actual humans must
check and sign cases; no signature or status is copied from a different version.
Resolve exact Delft/Aalto programme URLs, qualification/intake/fee/SAT gaps and
award identity/conditions. Establish a fixed applicable field inventory and
independently adjudicate full evidence support, freshness and conflicts before
V2-01 acceptance. Only then start V2-10 SearchProvider work.
