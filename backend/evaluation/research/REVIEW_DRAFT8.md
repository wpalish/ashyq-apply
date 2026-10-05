# Draft8: the six core questions, and sources that moved

Prepared by claude-opus-5 on 2026-10-05 (plan phase 0.2). Every value below
was read on the official page that day; excerpts in
[the dataset](data/ground_truth.draft8.json) are verbatim. **Nothing here is
signed**: changed cases are `draft` until the owner reviews them.

**74/220 known labels** (signed corpus: 62/220). Canonical SHA-256
`c46c21ef837514922176abcdbcfd884c517edb3d1f3b6e078282ef5bd6890eeb`.

## Why

The signed corpus labels documents and scholarships well and the applicant's
first questions hardly at all: IELTS was known for 1 case of 10, the deadline
for 1, tuition for 0. ER-08's answers (NTU IELTS, Delft TOEFL, Groningen fee)
were therefore unadjudicated and moved no metric. Two signed sources also
answer 404 now.

## Added (known)

| Case | Field | Value | Source |
|---|---|---|---|
| Groningen | `tuition` | EUR 19,800, non-EU/EEA, 2027-2028 | [programme page](https://www.rug.nl/bachelors/computing-science/?lang=en) |
| Groningen | `ielts.overall`, `ielts.subscores` | 6.5; 6.5 each band | [FSE language page](https://www.rug.nl/fse/education/admission-and-application/apply-bsc/language?lang=en) |
| Delft | `ielts.overall` | 6.5 (Computer Science and Engineering) | [admission requirements](https://www.tudelft.nl/en/education/admission-and-application/bsc-international-diploma/1-admission-requirements/) |
| Aalto | `deadline` | 2027-01-22 (end of the application period) | [programme page](https://www.aalto.fi/en/study-options/computer-engineering-bachelor-of-science-and-master-of-science-technology) |
| Aalto | `tuition` | EUR 12,000/year, non-EU/EEA | same |
| NTU | `ielts.overall`, `ielts.subscores` | 6.5; writing 6.5, speaking 6.5 | [general admission requirements](https://www.ntu.edu.sg/admissions/undergraduate/admissions/general-admission-requirements) |
| NTU | `deadline` | 2027-01-20 ("all other international qualifications" window) | same |
| UBC | `deadline` | 2027-01-15 (Winter Session 2027) | [dates and deadlines](https://you.ubc.ca/applying-ubc/dates-deadlines/) |
| Toronto | `ielts.overall`, `ielts.subscores` | 6.5; 6.0 each band | [English requirements](https://future.utoronto.ca/english-language-requirements) |
| Toronto | `deadline` | 2027-01-15 (Arts & Science, St. George) | [deadlines](https://future.utoronto.ca/deadlines) |
| KAIST | `tuition` | KRW 6,866,000/year | [cost of attendance](https://admission.kaist.ac.kr/intl-undergraduate/support/coa) |

## Not applicable

| Case | Field | Reason |
|---|---|---|
| Aalto | `ielts.overall`, `ielts.subscores` | Science and Technology, high-school-diploma route: "You are not required to submit a language test result." Admission round A ranks on SAT/ACT. |

## Changes to signed labels — need the owner's decision

| Case | Field | Signed | Proposed | Why |
|---|---|---|---|---|
| NTU | `english_evidence.ielts.minimum` | 6 / writing 6 / speaking 6 | **6.5 / 6.5 / 6.5** | The signed source answers 404; the current requirements page states 6.5. |
| NTU | `english_evidence.sat.minimum` | 1250 | 1250 (new source) | Moved to the general requirements page. |
| NTU | `country_credential.nis_grade12.minimum_grades`, `country_credential.high_school_certificate.additional_qualification_required` | known | **unknown** | Source answers 404; no current official page restates them. |
| Vienna | `german.application_minimum`, `german.enrolment_minimum` | A2, C1 | A2, C1 (new source) | Old page 404; the current language page states the same levels. |

## Looked for, not established (stay `unknown`, with the reason in the label)

Delft deadline ("15 January", no year printed) and tuition (fee tool); UBC
tuition (cost estimator); NTU tuition (only AY2026/27 published); KAIST
deadline (timeline page timed out); Vienna deadline (page shows the 2026
period only). Not attempted: Warsaw, HKU (admissions host unreachable),
scholarship identities (need bindings, an owner decision), GPA (no corpus key).

## Conventions used

Money is `{"amount": <float>, "currency": <ISO 4217>}` per year, as the
pipeline's tuition claim. A deadline written without a year is not dated.
"No band below 6.0" is 6.0 per band, as UBC's signed label. The academic year
is written as the page writes it ("2027-2028"); the pipeline writes "2027/28",
which the scorer currently treats as a different scope — an owner decision.
