# Human review worksheet: draft6

Dataset: `2026-09-22.draft6`; canonical SHA-256: `af19e617bdd07f7e6e62ab07b6db169deb78f41a192a928bc658953ef6d852c2`.

AI-prepared: 0/10 human verified. See [source notes](REVIEW_DRAFT6.md). Exact excerpts/access dates are in [the dataset](data/ground_truth.draft6.json). Null intake is not fall 2027 confirmation; UNKNOWN is not rejection.

## University of Groningen (`groningen`)

- [ ] Sources, programme identity and teaching language reviewed
- [ ] Intake, qualification, population and conditions reviewed
- [ ] UNKNOWN gaps, field applicability and mapping reviewed
- [ ] Evidence support, freshness and conflicts adjudicated

Reviewer: __________  Date: __________  Decision/corrections: __________

Programme status: **known**. [source](https://www.rug.nl/bachelors/computing-science/?lang=en)

| Field | Draft value | Evidence scope | Source | Conditions |
|---|---|---|---|---|
| `deadline` | "2027-05-01" | university=University of Groningen; programme=Computing Science; degree=bachelor; intake=fall 2027; population=non-EU/EEA | [source](https://www.rug.nl/bachelors/computing-science/?lang=en) | Table cells joined with spaces for review; 2026 tuition is NOT a 2027 quote. |
| `programme.exists` | true | university=University of Groningen; programme=Computing Science; degree=bachelor | [source](https://www.rug.nl/bachelors/computing-science/?lang=en) |  |
| `documents.admission.secondary_diploma.completed` | "diploma" | university=University of Groningen; degree=bachelor; population=non-Dutch qualification | [source](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-application-documents?lang=en) | Faculty of Science and Engineering section; statement includes qualification and expected graduation date. |
| `documents.admission.secondary_diploma.not_completed` | "school_enrolment_statement" | university=University of Groningen; degree=bachelor; population=non-Dutch qualification | [source](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-application-documents?lang=en) | Faculty of Science and Engineering section; statement includes qualification and expected graduation date. |
| `documents.admission.transcript.completed` | "academic_record" | university=University of Groningen; degree=bachelor; population=non-Dutch qualification | [source](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-application-documents?lang=en) | Additional prior-year transcripts accompany required course descriptions. |
| `documents.admission.transcript.not_completed` | "school_course_list" | university=University of Groningen; degree=bachelor; population=non-Dutch qualification | [source](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-application-documents?lang=en) | Additional prior-year transcripts accompany required course descriptions. |
| `documents.admission.translation.required_unless_language_in` | ["English", "Dutch", "French", "German"] | university=University of Groningen; degree=bachelor; population=non-Dutch qualification | [source](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-application-documents?lang=en) | Originals plus translations; course descriptions have a separate English/Dutch rule. |
| `documents.programme.course_descriptions.initial_upload` | "blank_allowed" | university=University of Groningen; degree=bachelor; qualification=Kazakhstan NIS Grade 12 Certificate | [source](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-application-documents?lang=en) | NIS-specific exemption, not generic Kazakhstan Attestat recognition or unconditional waiver. |
| `documents.programme.course_descriptions.board_may_request` | true | university=University of Groningen; degree=bachelor; qualification=Kazakhstan NIS Grade 12 Certificate | [source](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-application-documents?lang=en) | NIS-specific exemption, not generic Kazakhstan Attestat recognition or unconditional waiver. |
| `country_credential.nis_grade12.level_equivalence` | "Dutch VWO" | university=University of Groningen; degree=bachelor; qualification=Kazakhstan NIS Grade 12 Certificate | [source](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-entry-requirements/bachelorlinkscountry/kazakhstan?lang=en) | General diploma level only, not admission guarantee. Individual assessment and additional requirements remain; no Attestat or fall 2027 determination. |
| `subjects.mathematics.required` | true | university=University of Groningen; programme=Computing Science; degree=bachelor; field=computer science; qualification=Kazakhstan NIS Grade 12 Certificate | [source](https://www.rug.nl/education/application-enrolment-tuition-fees/admission/procedures/application-informatie/with-non-dutch-diploma/bachelor/bachelor-entry-requirements/bachelorlinkscountry/kazakhstan?lang=en) | FSE Computing Science row. Different-school curricula require individual academic assessment and course descriptions; this does not decide ordinary Attestat eligibility. No mathematics grade or level is inferred from other faculties. |

Unresolved: `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`.

## Delft University of Technology (`delft`)

- [ ] Sources, programme identity and teaching language reviewed
- [ ] Intake, qualification, population and conditions reviewed
- [ ] UNKNOWN gaps, field applicability and mapping reviewed
- [ ] Evidence support, freshness and conflicts adjudicated

Reviewer: __________  Date: __________  Decision/corrections: __________

Programme status: **known**. [source](https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/bachelor-of-computer-science-and-engineering)

| Field | Draft value | Evidence scope | Source | Conditions |
|---|---|---|---|---|
| `programme.exists` | true | university=Delft University of Technology; programme=Computer Science and Engineering; degree=bachelor; field=computer science | [source](https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/bachelor-of-computer-science-and-engineering) | Draft6 programme identity, heading "Bachelor of Computer Science and Engineering" read 2026-09-22. The [OCW page](https://ocw.tudelft.nl/programs/bachelor/computer-science-engineering/) stays as earlier existence evidence. Identity only: no requirement, deadline, fee or language value is taken from this page. |

Unresolved: `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`.

## Aalto University (`aalto`)

- [ ] Sources, programme identity and teaching language reviewed
- [ ] Intake, qualification, population and conditions reviewed
- [ ] UNKNOWN gaps, field applicability and mapping reviewed
- [ ] Evidence support, freshness and conflicts adjudicated

Reviewer: __________  Date: __________  Decision/corrections: __________

Programme status: **known**. [source](https://www.aalto.fi/fi/koulutustarjonta/tietotekniikka-tekniikan-kandidaatti-ja-diplomi-insinoori)

| Field | Draft value | Evidence scope | Source | Conditions |
|---|---|---|---|---|
| `programme.exists` | true | university=Aalto University; programme=Tietotekniikka; degree=bachelor; field=computer science | [source](https://www.aalto.fi/fi/koulutustarjonta/tietotekniikka-tekniikan-kandidaatti-ja-diplomi-insinoori) | Identity only: Finnish-route bachelor major; no fall 2027 intake confirmation or English-taught-route equivalence. |
| `programme.teaching_language.primary` | "Finnish" | university=Aalto University; programme=Tietotekniikka; degree=bachelor; field=computer science | [source](https://www.aalto.fi/fi/koulutustarjonta/tietotekniikka-tekniikan-kandidaatti-ja-diplomi-insinoori) | Some teaching is also in English and Swedish. The English-language master stage does not make the bachelor English-taught. |

Unresolved: `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`.

## University of Vienna (`vienna`)

- [ ] Sources, programme identity and teaching language reviewed
- [ ] Intake, qualification, population and conditions reviewed
- [ ] UNKNOWN gaps, field applicability and mapping reviewed
- [ ] Evidence support, freshness and conflicts adjudicated

Reviewer: __________  Date: __________  Decision/corrections: __________

Programme status: **known**. [source](https://aufnahmeverfahren.univie.ac.at/en/computer-science)

| Field | Draft value | Evidence scope | Source | Conditions |
|---|---|---|---|---|
| `programme.exists` | true | university=University of Vienna; programme=Computer Science; degree=bachelor | [source](https://aufnahmeverfahren.univie.ac.at/en/computer-science) |  |
| `programme.language` | "German" | university=University of Vienna; programme=Computer Science; degree=bachelor | [source](https://aufnahmeverfahren.univie.ac.at/en/computer-science) | No inference that English tests are accepted or required for this German-taught programme. |
| `german.application_minimum` | "A2" | university=University of Vienna; degree=bachelor; population=German-taught programme applicants | [source](https://studieren.univie.ac.at/en/admission/german-language-proficiency/) | Application threshold is distinct from enrolment threshold. |
| `german.enrolment_minimum` | "C1" | university=University of Vienna; degree=bachelor; population=German-taught programme applicants | [source](https://studieren.univie.ac.at/en/admission/german-language-proficiency/) | Entrance-exam participation can precede adequate proof; proof is needed by enrolment. |

Unresolved: `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`.

## University of Warsaw (`warsaw`)

- [ ] Sources, programme identity and teaching language reviewed
- [ ] Intake, qualification, population and conditions reviewed
- [ ] UNKNOWN gaps, field applicability and mapping reviewed
- [ ] Evidence support, freshness and conflicts adjudicated

Reviewer: __________  Date: __________  Decision/corrections: __________

Programme status: **known**. [source](https://informatorects.uw.edu.pl/en/programmes-all/IN/S1-INF/)

| Field | Draft value | Evidence scope | Source | Conditions |
|---|---|---|---|---|
| `programme.exists` | true | university=University of Warsaw; programme=Computer Science; degree=bachelor | [source](https://informatorects.uw.edu.pl/en/programmes-all/IN/S1-INF/) |  |
| `programme.language` | "Polish" | university=University of Warsaw; programme=Computer Science; degree=bachelor | [source](https://informatorects.uw.edu.pl/en/programmes-all/IN/S1-INF/) | English webpage language is not the programme teaching language. |

Unresolved: `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`.

## University of British Columbia (`ubc`)

- [ ] Sources, programme identity and teaching language reviewed
- [ ] Intake, qualification, population and conditions reviewed
- [ ] UNKNOWN gaps, field applicability and mapping reviewed
- [ ] Evidence support, freshness and conflicts adjudicated

Reviewer: __________  Date: __________  Decision/corrections: __________

Programme status: **known**. [source](https://you.ubc.ca/programs/computer-science-vancouver-bsc/)

| Field | Draft value | Evidence scope | Source | Conditions |
|---|---|---|---|---|
| `ielts.overall` | 6.5 | university=University of British Columbia; degree=bachelor; population=Vancouver applicants using IELTS Academic | [source](https://you.ubc.ca/applying-ubc/requirements/english-language-competency/) | One route to ELAS; exemptions and other routes exist. Page does not confirm a particular 2027 cycle. |
| `ielts.subscores` | {"reading": 6.0, "listening": 6.0, "speaking": 6.0, "writing": 6.0} | university=University of British Columbia; degree=bachelor; population=Vancouver applicants using IELTS Academic | [source](https://you.ubc.ca/applying-ubc/requirements/english-language-competency/) | General/Indicator/One Skill Retake are not accepted; this is an Academic-test route, not a universal requirement to take IELTS. |
| `programme.exists` | true | university=University of British Columbia; programme=Computer Science (BSc); degree=bachelor | [source](https://you.ubc.ca/programs/computer-science-vancouver-bsc/) |  |

Unresolved: `country_credential`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`.

## University of Toronto (`toronto`)

- [ ] Sources, programme identity and teaching language reviewed
- [ ] Intake, qualification, population and conditions reviewed
- [ ] UNKNOWN gaps, field applicability and mapping reviewed
- [ ] Evidence support, freshness and conflicts adjudicated

Reviewer: __________  Date: __________  Decision/corrections: __________

Programme status: **known**. [source](https://future.utoronto.ca/program/computer-science)

| Field | Draft value | Evidence scope | Source | Conditions |
|---|---|---|---|---|
| `country_credential` | "Certificate of Completed Secondary Education" | university=University of Toronto; degree=bachelor; qualification=Kazakhstan secondary education | [source](https://future.utoronto.ca/high-school-requirements-country?page=3) | Kazakhstan row: minimum general credential, not guaranteed admission, programme prerequisites, required grades or 2027-specific confirmation. Preserve the source wording; do not infer an exact local certificate title or NIS equivalence. |
| `intake` | "fall 2027" | university=University of Toronto; programme=Computer Science; degree=bachelor; intake=fall 2027 | [source](https://web.cs.toronto.edu/bachelor-of-computer-science) | First incoming BCS cohort; enrolment in a specific major follows the admission-category year. |
| `programme.exists` | true | university=University of Toronto; programme=Computer Science; degree=bachelor | [source](https://future.utoronto.ca/program/computer-science) | Identity only; admission route/intake are separate. |
| `documents.programme.supplemental_application.required` | true | university=University of Toronto; programme=Computer Science (St. George); degree=bachelor | [source](https://future.utoronto.ca/program/computer-science) | St. George requirement; do not transfer automatically to UTM or UTSC. |

Unresolved: `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`.

## University of Hong Kong (`hku`)

- [ ] Sources, programme identity and teaching language reviewed
- [ ] Intake, qualification, population and conditions reviewed
- [ ] UNKNOWN gaps, field applicability and mapping reviewed
- [ ] Evidence support, freshness and conflicts adjudicated

Reviewer: __________  Date: __________  Decision/corrections: __________

Programme status: **known**. [source](https://admissions.hku.hk/programmes/undergraduate-programmes/computing-and-data-science)

| Field | Draft value | Evidence scope | Source | Conditions |
|---|---|---|---|---|
| `programme.exists` | true | university=University of Hong Kong; programme=Computer Science; degree=bachelor | [source](https://admissions.hku.hk/programmes/undergraduate-programmes/computing-and-data-science) |  |
| `scholarships.entrance.exists` | true | university=University of Hong Kong; degree=bachelor | [source](https://www.admissions.hku.hk/node/891) | Generic entrance-award category; do not conflate with named faculty awards. |
| `scholarships.entrance.applicability.application_mode` | "automatic_after_admission_application" | university=University of Hong Kong; degree=bachelor | [source](https://www.admissions.hku.hk/node/891) | Special scholarships can require separate applications; automatic consideration is not an award guarantee. |

Unresolved: `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`, `scholarships.computing_data_science.exists`, `scholarships.computing_data_science.amount`, `scholarships.computing_data_science.applicability.international`, `scholarships.computing_data_science.coverage.tuition`.

## Nanyang Technological University (`ntu`)

- [ ] Sources, programme identity and teaching language reviewed
- [ ] Intake, qualification, population and conditions reviewed
- [ ] UNKNOWN gaps, field applicability and mapping reviewed
- [ ] Evidence support, freshness and conflicts adjudicated

Reviewer: __________  Date: __________  Decision/corrections: __________

Programme status: **known**. [source](https://www.ntu.edu.sg/education/undergraduate-programme/bachelor-of-computing-in-computer-science)

| Field | Draft value | Evidence scope | Source | Conditions |
|---|---|---|---|---|
| `programme.exists` | true | university=Nanyang Technological University; programme=Computer Science; degree=bachelor | [source](https://www.ntu.edu.sg/education/undergraduate-programme/bachelor-of-computing-in-computer-science) |  |
| `scholarships.nanyang_global.exists` | true | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Nanyang Global Scholarship, current published policy. |
| `scholarships.nanyang_global.applicability.nationality` | "all" | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Nationality openness is only one eligibility dimension. |
| `scholarships.nanyang_global.applicability.degree` | "bachelor_full_time" | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Academic, co-curricular and leadership selection still apply. |
| `scholarships.nanyang_global.applicability.application_mode` | "separate_after_admission_application" | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Admission application must be submitted first; this does not require an admission offer first. |
| `scholarships.nanyang_global.coverage.tuition` | {"fraction": 1.0, "basis": "subsidised_after_tuition_grant"} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Not full unsubsidised tuition; MOE Tuition Grant conditions remain. |
| `scholarships.nanyang_global.coverage.living` | {"currency": "SGD", "amount": 6500, "period": "academic_year"} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Annual allowance; not demonstrated full living-cost coverage. |
| `scholarships.nanyang_global.coverage.housing` | {"currency": "SGD", "maximum": 2000, "period": "academic_year", "requires": "NTU_hostel_residence"} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Conditional cap, not unconditional free housing. |
| `scholarships.nanyang_global.coverage.travel` | {"currency": "SGD", "maximum": 8000, "requires": "eligible_overseas_programme"} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Subject to travel-grant terms, not unrestricted airfare. |
| `scholarships.nanyang_global.duration` | "normal_programme_duration" | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Good performance and conduct conditions apply. |
| `scholarships.nanyang_global.renewal` | {"cgpa_gte": 3.5, "scale": 5.0, "review": "each_semester"} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Maintenance condition, not an admission threshold. |
| `scholarships.nanyang_global.bond` | {"years": 3, "basis": "MOE_Tuition_Grant", "population": ["Singapore_PR", "international"]} | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | No additional award bond; Tuition Grant service obligation is retained. |
| `documents.scholarship.nanyang_global.essay.required` | true | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Compulsory essay in the scholarship application. |
| `documents.scholarship.nanyang_global.essay.maximum_words` | 250 | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Compulsory essay in the scholarship application. |
| `documents.scholarship.nanyang_global.referee.required` | true | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Online appraisal; not an applicant-authored recommendation. |
| `documents.scholarship.nanyang_global.referee.role` | "school_teacher" | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Online appraisal; not an applicant-authored recommendation. |
| `documents.scholarship.nanyang_global.referee.family_or_relative_allowed` | false | university=Nanyang Technological University; degree=bachelor; population=full-time undergraduate scholarship applicants | [source](https://www.ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship) | Online appraisal; not an applicant-authored recommendation. |
| `country_credential.nis_grade12.minimum_grades` | {"all_subjects": "A"} | university=Nanyang Technological University; degree=bachelor; qualification=Kazakhstan NIS Grade 12 Certificate | [source](https://www.ntu.edu.sg/admissions/undergraduate/admission-guide/international-qualifications/other-international-qualifications) | Minimum NIS exam grades to apply, not an admission offer. Programme subject prerequisites still apply. Page contains 2026 dates; fall 2027 applicability is unconfirmed. |
| `country_credential.high_school_certificate.additional_qualification_required` | true | university=Nanyang Technological University; degree=bachelor; qualification=High School Certificate (Kazakhstan) | [source](https://www.ntu.edu.sg/admissions/undergraduate/admission-guide/international-qualifications/other-international-qualifications) | Certificate alone is insufficient for direct consideration. Page describes AP or GCE A-Level supplement routes with subject/timing conditions; this boolean is not rejection of supplemented applications. Fall 2027 conditions remain unknown. |
| `english_evidence.sat.minimum` | 1250 | university=Nanyang Technological University; degree=bachelor; population=English is not the high-school medium of instruction or is taken as a second/additional language; qualification=Other International Qualifications | [source](https://www.ntu.edu.sg/admissions/undergraduate/admission-guide/international-qualifications/other-international-qualifications) | One accepted English-evidence alternative when the stated language condition holds, not a mandatory academic SAT or NIS requirement. Other accepted evidence routes remain available. No fall 2027 confirmation. |
| `english_evidence.ielts.minimum` | {"overall": 6, "writing": 6, "speaking": 6} | university=Nanyang Technological University; degree=bachelor; population=English is not the high-school medium of instruction or is taken as a second/additional language; qualification=Other International Qualifications | [source](https://www.ntu.edu.sg/admissions/undergraduate/admission-guide/international-qualifications/other-international-qualifications) | One accepted English-evidence alternative when the stated language condition holds. Reading/listening thresholds are not established by this excerpt; omitted components do not mean zero. No fall 2027 confirmation. |

Unresolved: `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`, `scholarships.nanyang_global.applicability.intake`, `scholarships.nanyang_global.applicability.programme`, `scholarships.nanyang_global.coverage.fees`, `scholarships.nanyang_global.coverage.insurance`.

## KAIST (`kaist`)

- [ ] Sources, programme identity and teaching language reviewed
- [ ] Intake, qualification, population and conditions reviewed
- [ ] UNKNOWN gaps, field applicability and mapping reviewed
- [ ] Evidence support, freshness and conflicts adjudicated

Reviewer: __________  Date: __________  Decision/corrections: __________

Programme status: **known**. [source](https://cs.kaist.ac.kr/content?menu=188)

| Field | Draft value | Evidence scope | Source | Conditions |
|---|---|---|---|---|
| `programme.exists` | true | university=KAIST; programme=Computing; degree=bachelor | [source](https://cs.kaist.ac.kr/content?menu=188) | Identity only; admission route/intake are separate. |
| `programme.admission_route` | "undeclared_then_major_selection" | university=KAIST; degree=bachelor | [source](https://cs.kaist.ac.kr/content?menu=40) | Computing department explains undeclared entry and major choice in the second semester. Not direct guaranteed admission to a Computing major. |
| `scholarships.kaist.exists` | true | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) | Current advertised award; 2027 applicability is separately unknown. |
| `scholarships.kaist.applicability.international` | true | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) | Must use the international admission route. |
| `scholarships.kaist.applicability.offer` | true | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) | Award follows admission selection, not merely application. |
| `scholarships.kaist.applicability.application_mode` | "admission_form_checkbox" | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) | Select the scholarship in the financial resources section; no separate scholarship process. |
| `scholarships.kaist.coverage.tuition` | {"fraction": 1.0, "semesters": 8} | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) | Tuition exemption; not a claim that all expenses are covered. |
| `scholarships.kaist.coverage.living` | {"currency": "KRW", "amount": 350000, "period": "month"} | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) | Published monthly living subsidy. |
| `scholarships.kaist.coverage.insurance` | true | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) | Insurance listed; amount and detailed coverage are not specified. |
| `scholarships.kaist.renewal` | {"gpa_gt": 2.7, "scale": 4.3, "after": "freshman_year"} | university=KAIST; degree=bachelor; population=International Student Admission | [source](https://admission.kaist.ac.kr/intl-undergraduate/support/scholarships/kaist/) | Strictly over 2.7, not greater than or equal to; separate from admission eligibility. |

Unresolved: `country_credential`, `ielts.overall`, `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`, `intake`, `scholarships`, `scholarship_applicability`, `scholarship_coverage`, `documents.admission`, `documents.programme`, `documents.scholarship`, `scholarships.kaist.applicability.intake`, `scholarships.kaist.coverage.housing`, `scholarships.kaist.coverage.travel`, `scholarships.kaist.coverage.fees`, `scholarships.kaist.applicability.programme`.
