# Draft2 review candidate — 2026-09-20

`data/ground_truth.draft2.json` is AI-prepared, not human-certified: **0/10**
human-verified cases. It preserves draft1 and scores the same frozen capture in
`baseline/metrics.draft2.json`. No additional live calls or pipeline changes were
made for this report. Source URLs, access dates, minimal quotations and explicit
scope are stored with each label. Review the full linked page, not just the quote.

Use the [human review worksheet](REVIEW_WORKSHEET_DRAFT2.md) for all 46 known
facts, their scopes/sources and the unresolved fields. Signatures are blank;
the worksheet does not change dataset verification status.

## Annotation changes

| Case | Known / all labels | Exact programme URL | Changes and review limits |
|---|---:|---|---|
| Groningen | 6/20 | known | Diploma/enrolment, transcript/course-list and translation conditions; course-description exception applies specifically to Kazakhstan NIS Grade 12, not every Kazakhstan credential. Tuition changed to UNKNOWN because the quoted year is not the requested 2027 intake. |
| Delft | 1/16 | unknown | Main admissions page remains inaccessible through the research browser. OCW supports subject identity only; no language threshold guessed. |
| Aalto | 0/16 | unknown | Corrected programme existence to UNKNOWN: the available Data Science source does not establish the exact requested Computer Science programme. Its 2026 fee is not a 2027 CS fee. |
| Vienna | 4/19 | known | German teaching language; A2 at application and C1 at enrolment are different requirements. The 2026 entrance-exam deadline remains UNKNOWN for 2027. |
| Warsaw | 2/17 | known | Polish teaching language confirmed despite an English information page. |
| UBC | 3/16 | known | IELTS Academic overall and component requirements, scoped to the Vancouver IELTS route. Other English-standard routes/exemptions remain possible. No 2027 policy guarantee. |
| Toronto | 3/17 | known | Central CS programme identity and September 2027 BCS launch; supplemental application scoped to St. George only. The launch is not direct admission to every CS major: programme selection follows first year. |
| HKU | 3/22 | known | Generic entrance-award consideration separated from the named Computing/Data Science award. Named-award 2026 terms remain UNKNOWN for 2027. |
| NTU | 14/33 | known | Nanyang Global eligibility, application, separate expense categories, renewal and Tuition Grant bond; scholarship essay/referee documents. Full subsidised tuition is not full unsubsidised tuition; housing/travel have conditional caps. |
| KAIST | 10/30 | known | Computing undergraduate identity and undeclared-entry route; scholarship application, tuition/living/insurance and renewal. GPA must be above 2.7/4.3 after freshman year, not an entry requirement. |

Total: **46/206** known labels, versus 12/160 in draft1; exact programme identities
8/10, versus 6/10. Evergreen source policies use a null intake: they do not establish
fall 2027 applicability. Separate requested-intake/expense gaps remain UNKNOWN.
Generic unresolved family placeholders are retained alongside detailed award and
document keys, so coverage denominators across versions are not directly comparable.
Before acceptance, replace family placeholders with a reviewed fixed field inventory.

## Reproduce the separate report

From `backend`:

```sh
python -m evaluation.research --dataset evaluation/research/data/ground_truth.draft2.json --capture evaluation/research/baseline/capture.json --out evaluation/research/baseline/metrics.draft2.json --allow-drafts
```

Programme precision and recall are both **1/8**; candidate recall @5/10/20 is 1/8.
This changes the adjudicable denominator, not retrieval quality. Claim precision
is 0/5 and recall 0/46; claim adjudication is still only 5/13. Critical-field
coverage is 0/197. Scholarship discovery recall is 0/3 and applicability recall
0/7; coverage/applicability precision are null because no mapped predictions
exist. Award/document identity mapping remains incomplete, so these are harness
observations, not a calibrated verdict on extraction quality.

Support adjudication remains 0/13; unsupported/currentness/conflict rates remain
null. The compact capture has truncated evidence, which cannot establish automatic
support. Operations are unchanged: 520 HTTP attempts, two PDFs, three timeouts and
two page-budget failures. See the frozen baseline README for capture provenance.

## Required before acceptance

The final Delft retry returned HTTP 403 for the official admissions-requirements
page. Its accessible [student welcome links](https://cs.pages.ewi.tudelft.nl/useful-links/)
corroborate the bachelor name but do not resolve admissions policy or the canonical
prospective-student programme page. No search-snippet requirement was promoted to a label.

1. Resolve Delft and Aalto exact identities without silently broadening the subject
   ontology. Complete Kazakhstan-qualification, SAT, deadlines, fees and document
   requirements; leave unavailable 2027 policies explicitly UNKNOWN.
2. Review programme/campus, nationality, intake and renewal conditions separately
   for each award. Confirm fee categories rather than treating an allowance as full
   cost coverage. Expand named award/document identities and their output mapping.
3. Adjudicate support/currentness/conflicts from full source evidence, not the
   abbreviated publication capture. Refresh capture only as an explicit separate run.
4. Have an actual human review each case and enter reviewer/date. Create a newly
   versioned reviewed dataset and run strict scoring without `--allow-drafts`.
   Do not sign these AI-prepared cases on a person's behalf.

V2-01 remains in progress. V2-10 starts only after benchmark acceptance.
