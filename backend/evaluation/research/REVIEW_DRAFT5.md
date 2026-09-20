# Draft5: qualification and conditional English evidence

AI-prepared source annotations accessed 2026-09-21; **0/10 human verified**.
There are **61/219 known/total labels**, and **9/10 programme identities**.
Four fields are added and one Toronto UNKNOWN is resolved. Earlier datasets,
reports, capture, programme identities and all other field values are unchanged.

## Source decisions

[NTU Other International Qualifications](https://www.ntu.edu.sg/admissions/undergraduate/admission-guide/international-qualifications/other-international-qualifications)
separates NIS Grade 12 from the ordinary Kazakhstan school certificate. We annotate
NIS exam minimum grades and the additional-qualification requirement for the latter.
The supplement has AP/A-Level subject and timing conditions; this boolean is not
rejection of applications with an eligible supplement. Neither minimum guarantees admission.

The same page conditionally requires English evidence where instruction is not
English or English is a second/additional language. SAT and IELTS are alternatives,
not universal mandatory exams. Their scoped minima use `english_evidence.*` keys;
existing general SAT/IELTS policy UNKNOWNs stay unresolved. IELTS reading/listening
minima are not inferred. Page dates include the 2026 exercise: no 2027 applicability
is asserted, no 2026 deadline is copied into the requested intake.

[Toronto country table, Kazakhstan row](https://future.utoronto.ca/high-school-requirements-country?page=3)
resolves the general credential name only. It does not establish programme admission,
grades, NIS equivalence or fall 2027 terms. The table is paginated; page one does
not contain Kazakhstan. Preserve its English wording rather than guessing a local title.

Delft's OCW-linked official programme alias returned an error again. Exact admissions
page identity remains UNKNOWN; the existence evidence was already recorded.

## Replay and review

```sh
# From backend
python -m evaluation.research --dataset evaluation/research/data/ground_truth.draft5.json --capture evaluation/research/baseline/capture.json --out evaluation/research/baseline/metrics.draft5.json --allow-drafts
```

The same capture yields programme precision **1/8**, recall **1/9**; claim precision
**0/5**, recall **0/61**, critical coverage **0/210**. Only the latter two aggregate
denominators change from draft4. Operations, scholarship and adjudication measurements
are identical. This is not a new pipeline run or a quality improvement/regression.
The field inventory still includes generic UNKNOWN families and needs review.

Use [the draft5 worksheet](REVIEW_WORKSHEET_DRAFT5.md) for all 61 known fields.
Keep conditional English evidence separate from academic entry requirements when
reviewing aliases/mapping. Resolve remaining evidence gaps, finalize field applicability,
adjudicate evidence independently and obtain ten actual human reviewer/date signoffs
before strict acceptance. V2-10 remains after V2-01 acceptance only.
