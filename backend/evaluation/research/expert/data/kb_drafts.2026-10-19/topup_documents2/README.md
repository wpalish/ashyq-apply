# KB application documents, round 2 (CS bachelor, 2026-10-19)

The second batch of drafts for the KB question `documents` (`docs/process/KNOWLEDGE_BASE.md`, "Application
documents"), in the same shape as `topup_documents1`: one item per document an official page lists for an
international applicant to the bachelor's programme, each with its kind, `required` / `optional` /
`conditional` (plus the page's condition), the URL and a verbatim quote. Target: bachelor's in Computer
Science, international applicant, fall 2027 intake. Researched 2026-10-19 with live search frozen: web search
was used only to find official URLs. Every page was read with the production `Fetcher`: the production user
agent, robots.txt honoured, through the sandbox HTTPS proxy, with TLS verified. There was no user-agent
spoofing, no WAF bypass, no robots override and no paid search API. No heldout university was opened, and
none of the eight `topup_documents1` universities was redone.

## Files

- `core/<seed_id>.json`: one file per university, `questions_researched: ["documents"]`, `answers` holds only
  `documents`. A documents-only draft is merged into the university's entry and never becomes its base
  (`kb_build._documents_only`). All 20 universities are already in the KB.
- `core/evidence_check.container-2026-10-19.json`: the container pre-check, run from `backend` as
  `PYTHONPATH=. .venv/bin/python scripts/verify_evidence.py --trust-env-proxy
  evaluation/research/expert/data/kb_drafts.2026-10-19/topup_documents2/core --out <report>`. Result:
  **116 document rows, 116 official + quote_found** (the other 120 rows are the six unresearched core
  questions, `unknown`, no URL). Each document is its own row, item `documents.<kind>`. The file name contains
  `container`, so `kb_build` skips it. The CI check (`benchmark-capture.yml`, `mode=verify_evidence`,
  `extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_documents2`) is still needed; keep its
  report at `topup_documents2/evidence_check.ci-<date>.json`. Until then these documents stay unknown.

## Rules the drafts follow

- Only a document the page names is drafted; a page's general "we may ask for additional documents" is not
  turned into items. Things with no vocabulary kind are left in the answer's `notes`: UZH's signed declaration
  of consent and German certificate, EPFL's French certificate and Swiss residence permit, HKUST's public
  examination certificates and prize evidence, the U.S. self-reported academic records (UIUC SRAR, UW STARS),
  Brown's Secondary School Report form.
- A page that tells applicants **not** to send something (CMU: no resumes or portfolios; UW: no letters of
  recommendation; Duke: no separate resumes; McGill: no additional documents for unlisted programmes) is
  recorded in `notes` only.
- `conditional` carries the page's own condition ("first language is not English", "if admitted", "F-1 or J-1
  visa", "school outside the U.S. that follows a national curriculum").
- "Recommended but not required" (Duke's and Brown's English tests) and "test optional" (BU, Duke,
  Northwestern, UIUC) are `optional`.
- A counselor recommendation / school report from the counselor is `academic_reference`; teacher
  recommendations are `recommendation_letter`; a Common App or university supplement essay is `essay`; a
  "personal statement" by that name is `personal_statement`.
- `academic_year` is `null` everywhere. Several pages show the 2026–27 cycle's dates (HKUST, Northwestern,
  Penn, JHU, UT Austin) or label a policy by application cycle (JHU's "2026–2027" essay prompt, Duke's
  "2026-2027 admissions cycle" test-optional policy); none states the study year of the document list, and an
  application cycle written as "2026-2027" would read as a past academic year for the fall 2027 intake.

## Results

| seed_id | university | page(s) | items (requirement) |
|---|---|---|---|
| qs2027-015 | University of Pennsylvania | first-year application requirements; international FAQ | Common App/Coalition, personal statement, official transcript, counselor recommendation, teacher recommendation, Penn essays, SAT/ACT — required; English test, certified translation — conditional (9) |
| qs2027-016 | Cornell University | first-year applicants (international URL redirects there) | Common App, official transcript, counselor recommendation, two teacher recommendations, Cornell supplement essays, SAT/ACT — required; English exam — conditional (7) |
| qs2027-020 | Johns Hopkins University | application deadlines & requirements | Common App/Coalition, personal statement, Hopkins supplemental essay, standardized testing, transcript and counselor recommendation (secondary school report), two teacher evaluations, Certification of Finances (international) — required (8) |
| qs2027-022 | EPFL | bachelor "How to apply?" | registration form, photo, passport/ID, grade sheets of the last two years, upper secondary certificate — required; legalized translation — conditional (6) |
| qs2027-030 | McGill University | how to apply; other international high schools | online application, high school transcript — required; English test results — conditional (3) |
| qs2027-033 | HKUST | application procedures for international qualification holders | online application, ID/travel document, personal statement, school reports/transcripts, English proficiency proof, academic referee — required (6) |
| qs2027-037 | King's College London | how to apply; important information for applying | UCAS application, personal statement, reference — required; transcripts, English translations, English test results — conditional (6) |
| qs2027-045 | Northwestern University | apply: application materials | Common App/Coalition, Northwestern supplement, official transcript and school report, counselor recommendation, teacher recommendation — required; English proficiency — conditional; SAT/ACT — optional (7) |
| qs2027-050 | The Hong Kong Polytechnic University | Non-JUPAS Year 1 application procedures | eAdmission application, certificates/transcripts — required; official English translation — conditional (3) |
| qs2027-055 | Carnegie Mellon University | apply; admission requirements; international applicants | Common App, standardized testing, counselor evaluation, teacher recommendation, Common App essay and writing supplement — required; English test, official translation, diploma proof and final transcript (if admitted) — conditional (9) |
| qs2027-066 | Brown University | international applicants FAQ | Common Application — required; official translations — conditional; English test — optional (highly recommended) (3) |
| qs2027-068 | The University of Warwick | how to apply; personal statement; your reference | UCAS application, personal statement, reference — required (3) |
| qs2027-070 | Duke University | apply (checklist, transcripts, recommendations, essays) | Common App, official transcripts, counselor letter, two teacher letters, personal essay and Duke short essays — required; translation — conditional; English test, SAT/ACT — optional (8) |
| qs2027-072 | University of Texas at Austin | international freshman; transcript info | Common App, essay and short answers, SAT/ACT, transcripts — required; TOEFL/IELTS/DET, official translations — conditional; resume, recommendation letters — optional (8) |
| qs2027-074 | University of Illinois Urbana-Champaign | international requirements; first-year requirements; essays | Illinois essays + Common App essay — required; English test, official transcript (only if enrolling) — conditional; test scores — optional (4) |
| qs2027-082 | KTH Royal Institute of Technology | BSc Information and Communication Technology, entry requirements | English test, transcripts with syllabus (alternative Physics credentials) — conditional (2). KTH's only English-taught bachelor; the per-country document list is on universityadmissions.se, not a KTH domain |
| qs2027-093 | University of Washington | first-year how to apply | Common App, Common App essay, English proficiency scores (international) — required; transcript upload and English translation (national-curriculum schools abroad), SAT/ACT (homeschool / non-standard grading) — conditional (6) |
| qs2027-094 | Boston University | international applicant checklist | Common App, secondary school transcripts, counselor recommendation and school report, teacher evaluation, passport data page — required; English test, financial documentation (F-1/J-1), notarized translation — conditional; standardized tests — optional (9) |
| qs2027-098 | University of Nottingham | how we assess undergraduate applications | UCAS form, personal statement, reference — required (3) |
| qs2027-100 | University of Zurich | fact sheet: documents to submit, bachelor's, foreign qualification (01.07.2026) | photo, passport/ID, CV, upper secondary school-leaving certificate, school reports for the last three years — required; certified translation — conditional (6) |

**Not drafted (access).** Every refusal below is the production fetcher's answer; none was retried with a
different user agent or around robots.txt.

| seed_id | university | why |
|---|---|---|
| qs2027-009 | UCL | `www.ucl.ac.uk` undergraduate how-to-apply / international guidance / FAQ pages answer HTTP 403 |
| qs2027-011 | The University of Hong Kong | `admissions.hku.hk` robots.txt unreachable (ConnectTimeout), treated as a full disallow |
| qs2027-012 | NTU Singapore | `www.ntu.edu.sg/admissions/undergraduate` returns only a testimonial (444 readable characters); the content is rendered client-side |
| qs2027-018 | CUHK | `admission.cuhk.edu.hk` robots.txt unreachable (ConnectError), treated as a full disallow |
| qs2027-028 | The University of Sydney | `sydney.edu.au` international how-to-apply answers HTTP 405 |
| qs2027-029 | ANU | `study.anu.edu.au` robots.txt unreachable (ConnectError), treated as a full disallow |
| qs2027-031 | Monash University | `www.monash.edu` international how-to-apply answers HTTP 403 |
| qs2027-040 | The University of Manchester | `www.manchester.ac.uk` how-to-apply answers HTTP 405 |
| qs2027-042 | Yonsei University | robots.txt disallows the `uic.yonsei.ac.kr` admission path |
| qs2027-043 | Columbia University | `undergrad.admissions.columbia.edu` answers HTTP 403 |
| qs2027-051 | University of Michigan-Ann Arbor | `admissions.umich.edu` international page answers HTTP 403 |
| qs2027-052 | City University of Hong Kong | `www.cityu.edu.hk/admo` Non-JUPAS page returns HTTP 200 with no readable text |
| qs2027-085 | Durham University | `www.durham.ac.uk` undergraduate apply page answers HTTP 403 |
| qs2027-092 | Pennsylvania State University | robots.txt disallows `admissions.psu.edu/apply/international/` |
| qs2027-096 | University of Alberta | `www.ualberta.ca` international transcripts & documents page answers HTTP 403 |

**Read but not drafted (the page names no document beyond the application itself).** University of Bristol
(qs2027-057: international applications page names only the UCAS form), University of Glasgow (qs2027-080:
offer-holder page says only that admissions will email if documents are needed), University of Sheffield
(qs2027-083: applying essentials name only the UCAS application), UNSW (qs2027-019: international how-to-apply
names only the online form "and all the required documents"), University of Leeds (qs2027-078: only a regional
page with undergraduate guidance was found). Guessed URLs that answered 404 and were not pursued further:
University of Amsterdam (CS bachelor international page), University of Queensland, UTS, Birmingham,
Institut Polytechnique de Paris, Brown's and JHU's older paths (current pages were found and used).
