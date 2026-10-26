# KB gap fill, round 8: pages read on CI (CS bachelor, 2026-10-20)

This round tops up the merged knowledge base (`app.knowledge.load_knowledge_base()`) for four universities
whose official sites refuse the agent container: HKU (qs2027-011), CUHK (qs2027-018), KAIST (qs2027-065) and
KU Leuven (qs2027-059). It covers only the questions still empty in the merged KB (the six core questions and
`documents`). The target is the CS bachelor recorded in each KB entry, for an international applicant
entering in fall 2027 (or the university's first intake of the 2027/28 year). No held-out university was
opened.

## Source

The only input is the main session's `mode=read_pages` artifact from 2026-10-20: 10 official pages read on the
GitHub Actions runner with the production `Fetcher` (the `verify_evidence` reader: our user agent, robots.txt
honoured, no robots override). Each record has `seed_id`, `url`, `final_url`, `status`, `chars`, `sha256`,
`text` (the readable text from `readable_text` / `pdf_to_text`) and `read_on`. Every page was `ok`, none
was truncated and every `final_url` equals its `url`. The two rows with `seed_id` `kuleuven` (the dev3 twin
check) were ignored. No page was read from the container, no web search was used, and nothing was inferred
beyond the page text.

| seed_id | page | chars | sha256 (first 12) |
|---|---|---|---|
| qs2027-011 HKU | https://www.cds.hku.hk/prospective-students/scholarships/ | 24,089 | — |
| qs2027-018 CUHK | https://www.cuhk.edu.hk/adm/ApplicationGuide/ApplicationGuide_International.pdf | 18,769 | 1d3827357092 |
| qs2027-065 KAIST | https://www.kaist.ac.kr/en/html/edu/03100502.html | 13,749 | — |
| qs2027-059 KU Leuven | https://onderwijsaanbod.kuleuven.be/opleidingen/n/SC_51016742.htm | 6,764 | — |
| qs2027-059 KU Leuven | https://www.kuleuven.be/english/apply/language-requirements | 941 | c69bfbe6050f |
| qs2027-059 KU Leuven | https://www.kuleuven.be/english/apply/requested-documents | 17,255 | e9a9d5026978 |
| qs2027-059 KU Leuven | https://www.kuleuven.be/english/education/student/fees/tuition-fee-breakdown | 3,549 | — |
| qs2027-059 KU Leuven | https://www.kuleuven.be/english/apply/requested-documents/application-fee | 3,294 | — |

(A dash means no quote was drafted from that page.)

## Files

- `core/qs2027-018.json` (CUHK): `deadline` and `documents`.
- `core/qs2027-059.json` (KU Leuven): `documents` (a documents-only draft, merged into the entry and never its
  base: `kb_build._documents_only`).
- **No draft for HKU (qs2027-011) or KAIST (qs2027-065).** Their pages answer only questions the KB already
  holds, so a draft would add nothing; see below. No `unknown` answers were written either, because the build
  keeps the latest unknown reason, and the existing reasons name the target pages better than "the CI read
  did not cover it".

## Quote check (no container evidence check)

These hosts refuse the container, so `verify_evidence --trust-env-proxy` cannot be run here. Instead every
known row was checked against the stored CI text with `verify_evidence`'s own functions: `items()` to list
the rows exactly as the evidence check does (one row per document item), `quote_in()` on the stored
`text` (already the output of `readable_text` / `pdf_to_text`, the extractors `verify_evidence` uses), and
`is_official()` on the URL. **Result: 18 rows, 18 official + quote_found** (CUHK: deadline and 9 document
items on the guide PDF; KU Leuven: 7 items on the requested-documents page and 1 on the language-requirements
page).

The CI check is still needed: `benchmark-capture.yml`, `mode=verify_evidence`,
`extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_round8`. Save its report as
`topup_round8/evidence_check.ci-<date>.json`. Until then these answers stay unknown. No KB rebuild was done.

## Filled

| seed_id | question | value | academic_year / cycle as printed | source |
|---|---|---|---|---|
| qs2027-018 CUHK | deadline | 2027-01-07 (Regular Round; Advance Offer Round 2026-11-12 is optional) | `2027/28` ("International Students Admissions Scheme (2027 Entry)", Note 3 "the 2027 / 28 academic year") | 2027 Entry international application guide (PDF, October 2026) |
| qs2027-018 CUHK | documents | application form: required. Passport, high school transcripts, graduation certificate / diploma, English test results, translation (not in English or Chinese), personal statement (stated as required only for Medicine): conditional. CV, academic referee: optional (9 items) | `2027/28` (same guide) | same PDF, section VIII |
| qs2027-059 KU Leuven | documents | secondary diploma, transcripts, passport identity page, motivation letter, CV: required. Translation, English proficiency test, SAT/ACT/AP Calculus/SOWISO OMPT: conditional (8 items) | none printed (`academic_year: null`, no `cycle_stated`) | requested-documents (Bachelor's section); language-requirements |

Notes for the reviewer:

- **CUHK "if applicable".** Section VIII asks for "the following supporting documents, if applicable"; per
  the documents rule ("if applicable" is a condition) every listed supporting document is `conditional` with
  that condition, and only the application form is `required`. The deadline has no time or timezone printed.
- **CUHK personal statement.** The guide lists "(iii) Personal Statement" but states a requirement only for
  Medicine; drafted `conditional` with that wording. Drop it if the reviewer prefers to leave such an item out.
- **KU Leuven English test vs the KB.** The merged KB has `english` `not_applicable` for this programme
  (Dutch-taught, Dutch B2). The requested-documents page lists "English Proficiency Certificate" among the core
  documents for every Bachelor's applicant, and the language-requirements page requires one of its tests from
  all applicants without an English-taught diploma from six named countries. Both official statements are
  reported; the item is drafted `conditional` with the language page's condition. The main session decides
  whether to keep it for a Dutch-taught programme.
- **KU Leuven list is university-wide.** Only the diploma/transcript and translation sentences are unique to
  the Bachelor's section; the passport, motivation-letter and CV lines repeat in the Master's and other
  sections. `required` rests on the section's "It is not possible to submit your online application without
  the following core documents".

## Left unknown

| seed_id | question(s) | reason |
|---|---|---|
| qs2027-011 HKU | english, gpa, deadline, documents | the only page read is the School of Computing and Data Science scholarships page; it states none of these. (Its entrance scholarships are already in the KB from this same page; it speaks of students "admitted in the 2026/27 academic year".) |
| qs2027-018 CUHK | english | the guide says "Please refer to our office website for the minimum required scores or grades"; no score is printed. |
| qs2027-018 CUHK | gpa | no threshold ("Applicants will be considered on the basis of their educational background, academic and non-academic achievements"). |
| qs2027-018 CUHK | tuition | no tuition amount; only the HK$10,000 first instalment of composition fees payable on offer acceptance and the HK$500 application fee. |
| qs2027-018 CUHK | scholarship_exists, scholarship_international | the guide names no award; it only mentions "the processing of admissions scholarships/bursaries" in its privacy statement, which is not drafted as an award. |
| qs2027-065 KAIST | english, gpa, deadline, documents | the only page read is the general "Scholarship Types" page; it states none of these. Scholarships and tuition are already in the KB. |
| qs2027-059 KU Leuven | tuition | the tuition-fee-breakdown page shows four unlabelled 2026-2027 rows (EUR 1,181.40, 3,093.12, 5,613.12, 9,493.92) with no statement of which applies to a non-EEA student in the Dutch-taught Bachelor in de informatica, and the year is 2026-2027, not 2027-2028. Not inferred. |
| qs2027-059 KU Leuven | scholarship_exists, scholarship_international | no page read names a scholarship for bachelor's applicants (the application-fee page names only a VLIR-ICP master's scholarship exemption). |
