# Human review worksheet: draft2

This is a generated view of the AI-prepared dataset, not a certification. All ten cases remain draft.

Dataset: `2026-09-20.draft2`; SHA-256: `4ee244c53ef3f4a82fa856400a0b65a48e7c666eb3552711b3895bbcb722c3cb`.

Open every official source and check the value and its scope. Unknown fields are gaps, not negatives. Null intake does not establish fall 2027 applicability. Record corrections in a newly versioned dataset; never sign on behalf of another person. See REVIEW_DRAFT2.md and MAPPING.md for report and value-shape limitations.

For each case, a human may fill reviewer/date and record a decision below, then transfer the reviewed facts to the new dataset. Leaving a checkbox or signature blank means unreviewed.

## University of Groningen (`groningen`)

- [ ] Sources and exact programme identity reviewed
- [ ] Requested intake/qualification/population separated from general policy
- [ ] Known values and UNKNOWN gaps reviewed
- [ ] Mapping identities and atomic field conventions reviewed

Reviewer: __________  Date: __________  Decision/corrections: __________

Exact programme URL status: **known**. [https://www.rug.nl/bachelors/computing-science/?lang=en](https://www.rug.nl/bachelors/computing-science/?lang=en)

| Field | Draft value | Evidence scope | Official source |
|---|---|---|---|
| `deadline` | "2027-05-01" | university=University of Groningen; programme=Computing Science; degree=bachelor; intake=fall 2027; population=non-EU/EEA | [source](https://www.rug.nl/bachelors/computing-science/?lang=en) |
| `programme.exists` | true | university=University of Groningen; programme=Computing Science; degree=bachelor | [source](https://www.rug.nl/bachelors/computing-science/?lang=en) |
| `documents.admission.secondary_diploma` | {"completed": "diploma", "not_completed": "school_enrolment_statement"} | university=University of Groningen; degree=bachelor; population=non-Dutch qualification | [source](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-application-documents?lang=en) |
| `documents.admission.transcript` | {"completed": "academic_record", "not_completed": "school_course_list"} | university=University of Groningen; degree=bachelor; population=non-Dutch qualification | [source](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-application-documents?lang=en) |
| `documents.admission.translation` | {"required_unless_language_in": ["English", "Dutch", "French", "German"]} | university=University of Groningen; degree=bachelor; population=non-Dutch qualification | [source](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-application-documents?lang=en) |
| `documents.programme.course_descriptions` | {"initial_upload": "blank_allowed", "board_may_request": true} | university=University of Groningen; degree=bachelor; qualification=Kazakhstan NIS Grade 12 Certificate | [source](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-application-documents?lang=en) |

**Unresolved fields:** `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`.

**Scope notes:** Programme identity confirmed by AI; human review pending. Draft2 source audit: AI-prepared only; evergreen policy has no promised 2027 validity. Human review and exact applicant applicability remain pending.

## Delft University of Technology (`delft`)

- [ ] Sources and exact programme identity reviewed
- [ ] Requested intake/qualification/population separated from general policy
- [ ] Known values and UNKNOWN gaps reviewed
- [ ] Mapping identities and atomic field conventions reviewed

Reviewer: __________  Date: __________  Decision/corrections: __________

Exact programme URL status: **unknown**. 

| Field | Draft value | Evidence scope | Official source |
|---|---|---|---|
| `programme.exists` | true | university=Delft University of Technology; programme=Computer Science and Engineering; degree=bachelor | [source](https://ocw.tudelft.nl/programs/bachelor/computer-science-engineering/) |

**Unresolved fields:** `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`.

**Scope notes:** OCW supports existence, not an exact current admissions page. Main programme redirect inaccessible during review. Draft2 source audit: AI-prepared only; evergreen policy has no promised 2027 validity. Human review and exact applicant applicability remain pending. Main programme URL unavailable through research browser; OCW establishes subject identity only. No IELTS/deadline value guessed from third-party pages.

## Aalto University (`aalto`)

- [ ] Sources and exact programme identity reviewed
- [ ] Requested intake/qualification/population separated from general policy
- [ ] Known values and UNKNOWN gaps reviewed
- [ ] Mapping identities and atomic field conventions reviewed

Reviewer: __________  Date: __________  Decision/corrections: __________

Exact programme URL status: **unknown**. 

| Field | Draft value | Evidence scope | Official source |
|---|---|---|---|

**Unresolved fields:** `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`, `programme.exists`.

**Scope notes:** Related Data Science programme is not automatically equivalent to requested Computer Science. Exact CS match unresolved; do not manufacture a positive. Draft2 source audit: AI-prepared only; evergreen policy has no promised 2027 validity. Human review and exact applicant applicability remain pending. Data Science evidence cannot establish exact requested Computer Science identity; programme.exists corrected from known to unknown.

## University of Vienna (`vienna`)

- [ ] Sources and exact programme identity reviewed
- [ ] Requested intake/qualification/population separated from general policy
- [ ] Known values and UNKNOWN gaps reviewed
- [ ] Mapping identities and atomic field conventions reviewed

Reviewer: __________  Date: __________  Decision/corrections: __________

Exact programme URL status: **known**. [https://aufnahmeverfahren.univie.ac.at/en/computer-science](https://aufnahmeverfahren.univie.ac.at/en/computer-science)

| Field | Draft value | Evidence scope | Official source |
|---|---|---|---|
| `programme.exists` | true | university=University of Vienna; programme=Computer Science; degree=bachelor | [source](https://aufnahmeverfahren.univie.ac.at/en/computer-science) |
| `programme.language` | "German" | university=University of Vienna; programme=Computer Science; degree=bachelor | [source](https://aufnahmeverfahren.univie.ac.at/en/computer-science) |
| `german.application_minimum` | "A2" | university=University of Vienna; degree=bachelor; population=German-taught programme applicants | [source](https://studieren.univie.ac.at/en/admission/german-language-proficiency/) |
| `german.enrolment_minimum` | "C1" | university=University of Vienna; degree=bachelor; population=German-taught programme applicants | [source](https://studieren.univie.ac.at/en/admission/german-language-proficiency/) |

**Unresolved fields:** `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`.

**Scope notes:** Admission page reached through official faculty link. Exact intake requires additional evidence. Draft2 source audit: AI-prepared only; evergreen policy has no promised 2027 validity. Human review and exact applicant applicability remain pending.

## University of Warsaw (`warsaw`)

- [ ] Sources and exact programme identity reviewed
- [ ] Requested intake/qualification/population separated from general policy
- [ ] Known values and UNKNOWN gaps reviewed
- [ ] Mapping identities and atomic field conventions reviewed

Reviewer: __________  Date: __________  Decision/corrections: __________

Exact programme URL status: **known**. [https://informatorects.uw.edu.pl/en/programmes-all/IN/S1-INF/](https://informatorects.uw.edu.pl/en/programmes-all/IN/S1-INF/)

| Field | Draft value | Evidence scope | Official source |
|---|---|---|---|
| `programme.exists` | true | university=University of Warsaw; programme=Computer Science; degree=bachelor | [source](https://informatorects.uw.edu.pl/en/programmes-all/IN/S1-INF/) |
| `programme.language` | "Polish" | university=University of Warsaw; programme=Computer Science; degree=bachelor | [source](https://informatorects.uw.edu.pl/en/programmes-all/IN/S1-INF/) |

**Unresolved fields:** `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`.

**Scope notes:** Teaching language is Polish; identity match does not establish language or intake suitability. Draft2 source audit: AI-prepared only; evergreen policy has no promised 2027 validity. Human review and exact applicant applicability remain pending.

## University of British Columbia (`ubc`)

- [ ] Sources and exact programme identity reviewed
- [ ] Requested intake/qualification/population separated from general policy
- [ ] Known values and UNKNOWN gaps reviewed
- [ ] Mapping identities and atomic field conventions reviewed

Reviewer: __________  Date: __________  Decision/corrections: __________

Exact programme URL status: **known**. [https://you.ubc.ca/programs/computer-science-vancouver-bsc/](https://you.ubc.ca/programs/computer-science-vancouver-bsc/)

| Field | Draft value | Evidence scope | Official source |
|---|---|---|---|
| `ielts.overall` | 6.5 | university=University of British Columbia; degree=bachelor; population=Vancouver applicants using IELTS Academic | [source](https://you.ubc.ca/applying-ubc/requirements/english-language-competency/) |
| `ielts.subscores` | {"reading": 6.0, "listening": 6.0, "speaking": 6.0, "writing": 6.0} | university=University of British Columbia; degree=bachelor; population=Vancouver applicants using IELTS Academic | [source](https://you.ubc.ca/applying-ubc/requirements/english-language-competency/) |
| `programme.exists` | true | university=University of British Columbia; programme=Computer Science (BSc); degree=bachelor | [source](https://you.ubc.ca/programs/computer-science-vancouver-bsc/) |

**Unresolved fields:** `country_credential`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`.

**Scope notes:** Vancouver BSc only. Do not silently equate BA or Okanagan. Draft2 source audit: AI-prepared only; evergreen policy has no promised 2027 validity. Human review and exact applicant applicability remain pending.

## University of Toronto (`toronto`)

- [ ] Sources and exact programme identity reviewed
- [ ] Requested intake/qualification/population separated from general policy
- [ ] Known values and UNKNOWN gaps reviewed
- [ ] Mapping identities and atomic field conventions reviewed

Reviewer: __________  Date: __________  Decision/corrections: __________

Exact programme URL status: **known**. [https://future.utoronto.ca/program/computer-science](https://future.utoronto.ca/program/computer-science)

| Field | Draft value | Evidence scope | Official source |
|---|---|---|---|
| `intake` | "fall 2027" | university=University of Toronto; programme=Computer Science; degree=bachelor; intake=fall 2027 | [source](https://web.cs.toronto.edu/bachelor-of-computer-science) |
| `programme.exists` | true | university=University of Toronto; programme=Computer Science; degree=bachelor | [source](https://future.utoronto.ca/program/computer-science) |
| `documents.programme.supplemental_application` | true | university=University of Toronto; programme=Computer Science (St. George); degree=bachelor | [source](https://future.utoronto.ca/program/computer-science) |

**Unresolved fields:** `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`.

**Scope notes:** Official announcement establishes new degree; exact campus programme URL not yet adjudicated. Draft2 source audit: AI-prepared only; evergreen policy has no promised 2027 validity. Human review and exact applicant applicability remain pending.

## University of Hong Kong (`hku`)

- [ ] Sources and exact programme identity reviewed
- [ ] Requested intake/qualification/population separated from general policy
- [ ] Known values and UNKNOWN gaps reviewed
- [ ] Mapping identities and atomic field conventions reviewed

Reviewer: __________  Date: __________  Decision/corrections: __________

Exact programme URL status: **known**. [https://admissions.hku.hk/programmes/undergraduate-programmes/computing-and-data-science](https://admissions.hku.hk/programmes/undergraduate-programmes/computing-and-data-science)

| Field | Draft value | Evidence scope | Official source |
|---|---|---|---|
| `programme.exists` | true | university=University of Hong Kong; programme=Computer Science; degree=bachelor | [source](https://admissions.hku.hk/programmes/undergraduate-programmes/computing-and-data-science) |
| `scholarships.entrance.exists` | true | university=University of Hong Kong; degree=bachelor | [source](https://www.admissions.hku.hk/node/891) |
| `scholarships.entrance.applicability.application_mode` | "automatic_after_admission_application" | university=University of Hong Kong; degree=bachelor | [source](https://www.admissions.hku.hk/node/891) |

**Unresolved fields:** `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`, `scholarships.computing_data_science.exists`, `scholarships.computing_data_science.amount`, `scholarships.computing_data_science.applicability.international`, `scholarships.computing_data_science.coverage.tuition`.

**Scope notes:** Combined admission route contains multiple programmes; acceptable route needs human confirmation. PDF brochure is linked but not used as evidence here. Draft2 source audit: AI-prepared only; evergreen policy has no promised 2027 validity. Human review and exact applicant applicability remain pending.

## Nanyang Technological University (`ntu`)

- [ ] Sources and exact programme identity reviewed
- [ ] Requested intake/qualification/population separated from general policy
- [ ] Known values and UNKNOWN gaps reviewed
- [ ] Mapping identities and atomic field conventions reviewed

Reviewer: __________  Date: __________  Decision/corrections: __________

Exact programme URL status: **known**. [https://www.ntu.edu.sg/education/undergraduate-programme/bachelor-of-computing-in-computer-science](https://www.ntu.edu.sg/education/undergraduate-programme/bachelor-of-computing-in-computer-science)

| Field | Draft value | Evidence scope | Official source |
|---|---|---|---|
| `programme.exists` | true | university=Nanyang Technological University; programme=Computer Science; degree=bachelor | [source](https://www.ntu.edu.sg/education/undergraduate-programme/bachelor-of-computing-in-computer-science) |
| `scholarships.nanyang_global.exists` | true | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) |
| `scholarships.nanyang_global.applicability.nationality` | "all" | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) |
| `scholarships.nanyang_global.applicability.degree` | "bachelor_full_time" | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) |
| `scholarships.nanyang_global.applicability.application_mode` | "separate_after_admission_application" | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) |
| `scholarships.nanyang_global.coverage.tuition` | {"fraction": 1.0, "basis": "subsidised_after_tuition_grant"} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) |
| `scholarships.nanyang_global.coverage.living` | {"currency": "SGD", "amount": 6500, "period": "academic_year"} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) |
| `scholarships.nanyang_global.coverage.housing` | {"currency": "SGD", "maximum": 2000, "period": "academic_year", "requires": "NTU_hostel_residence"} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) |
| `scholarships.nanyang_global.coverage.travel` | {"currency": "SGD", "maximum": 8000, "requires": "eligible_overseas_programme"} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) |
| `scholarships.nanyang_global.duration` | "normal_programme_duration" | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) |
| `scholarships.nanyang_global.renewal` | {"cgpa_gte": 3.5, "scale": 5.0, "review": "each_semester"} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) |
| `scholarships.nanyang_global.bond` | {"years": 3, "basis": "MOE_Tuition_Grant", "population": ["Singapore_PR", "international"]} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) |
| `documents.scholarship.nanyang_global.essay` | {"required": true, "maximum_words": 250} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) |
| `documents.scholarship.nanyang_global.referee` | {"required": true, "role": "school_teacher", "family_or_relative_allowed": false} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) |

**Unresolved fields:** `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`, `scholarships.nanyang_global.applicability.intake`, `scholarships.nanyang_global.applicability.programme`, `scholarships.nanyang_global.coverage.fees`, `scholarships.nanyang_global.coverage.insurance`.

**Scope notes:** Exact identity; intake not inferred from evergreen programme page. Draft2 source audit: AI-prepared only; evergreen policy has no promised 2027 validity. Human review and exact applicant applicability remain pending.

## KAIST (`kaist`)

- [ ] Sources and exact programme identity reviewed
- [ ] Requested intake/qualification/population separated from general policy
- [ ] Known values and UNKNOWN gaps reviewed
- [ ] Mapping identities and atomic field conventions reviewed

Reviewer: __________  Date: __________  Decision/corrections: __________

Exact programme URL status: **known**. [https://cs.kaist.ac.kr/content?menu=188](https://cs.kaist.ac.kr/content?menu=188)

| Field | Draft value | Evidence scope | Official source |
|---|---|---|---|
| `programme.exists` | true | university=KAIST; programme=Computing; degree=bachelor | [source](https://cs.kaist.ac.kr/content?menu=188) |
| `programme.admission_route` | "undeclared_then_major_selection" | university=KAIST; degree=bachelor | [source](https://cs.kaist.ac.kr/content?menu=40) |
| `scholarships.kaist.exists` | true | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) |
| `scholarships.kaist.applicability.international` | true | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) |
| `scholarships.kaist.applicability.offer` | true | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) |
| `scholarships.kaist.applicability.application_mode` | "admission_form_checkbox" | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) |
| `scholarships.kaist.coverage.tuition` | {"fraction": 1.0, "semesters": 8} | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) |
| `scholarships.kaist.coverage.living` | {"currency": "KRW", "amount": 350000, "period": "month"} | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) |
| `scholarships.kaist.coverage.insurance` | true | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) |
| `scholarships.kaist.renewal` | {"gpa_gt": 2.7, "scale": 4.3, "after": "freshman_year"} | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) |

**Unresolved fields:** `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`, `scholarships.kaist.applicability.intake`, `scholarships.kaist.coverage.housing`, `scholarships.kaist.coverage.travel`, `scholarships.kaist.coverage.fees`, `scholarships.kaist.applicability.programme`.

**Scope notes:** Official curriculum page; exact current admission route/degree equivalence needs Korean-speaking human review. Draft2 source audit: AI-prepared only; evergreen policy has no promised 2027 validity. Human review and exact applicant applicability remain pending.

