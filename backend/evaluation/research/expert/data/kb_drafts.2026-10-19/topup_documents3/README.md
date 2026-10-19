# KB application documents, round 3 (CS bachelor, 2026-10-19)

The third batch of drafts for the KB question `documents` (`docs/process/KNOWLEDGE_BASE.md`, "Application
documents"), in the same shape as `topup_documents1` and `topup_documents2`: one item per document an
official page lists for an international applicant to the bachelor's programme. Each item has its kind,
`required` / `optional` / `conditional` (with the page's condition), the URL and a verbatim quote. Target:
bachelor's in Computer Science, international applicant, fall 2027 intake. Researched 2026-10-19 with live
search frozen: web search was used only to find official URLs. Every page was read with the production
`Fetcher`, which means the production user agent, robots.txt honoured, the sandbox HTTPS proxy and verified
TLS. There was no user-agent spoofing, no WAF bypass, no robots override and no paid search API. No heldout
university was opened. No university that `topup_documents1` or `topup_documents2` drafted, could not read or
did not draft was redone, and that includes the guessed URLs that answered 404 in round 2 (Amsterdam,
Queensland, UTS, Birmingham, Institut Polytechnique de Paris). This round favours Asian, European, Latin
American and Australian universities.

## Files

- `core/<seed_id>.json`: one file per university. Each has `questions_researched: ["documents"]`, and
  `answers` holds only `documents`. A documents-only draft is merged into the university's entry and never
  becomes its base (`kb_build._documents_only`). All 25 universities are already in the KB.
- `core/evidence_check.container-2026-10-19.json`: the container pre-check, run from `backend` as
  `PYTHONPATH=. .venv/bin/python scripts/verify_evidence.py --trust-env-proxy
  evaluation/research/expert/data/kb_drafts.2026-10-19/topup_documents3/core --out <report>`. Result:
  **164 document rows, 164 official + quote_found**. The other 150 rows are the six unresearched core
  questions, which are `unknown` and have no URL. Each document is its own row, with item `documents.<kind>`.
  The file name contains `container`, so `kb_build` skips it. The CI check is still needed: run
  `benchmark-capture.yml` with `mode=verify_evidence` and
  `extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_documents3`, and keep its report at
  `topup_documents3/evidence_check.ci-<date>.json`. These documents stay unknown until that check passes.

## Rules the drafts follow

- A document is drafted only if the page names it. A page's general "we may ask for additional documents"
  is not turned into items. Things with no vocabulary kind go in the answer's `notes`. Examples are
  Chinese-proficiency (HSK), Korean (TOPIK), Danish, German and Spanish language certificates, consent and
  commitment forms, nationality documents for former Chinese or Korean citizens, parents' passports, guardian
  statements, self-introduction videos, the APS certificate, residence permits and non-criminal-record proofs.
- A page that tells applicants **not** to send something (LMU: no references or recommendation letters for the
  International Office application) is recorded in `notes` only.
- `conditional` carries the page's own condition, for example "a document is in a language other than
  Chinese or English", "native language is not English", "after admission" or "sponsored students".
  "Not required, but you may submit" (Harvard's and Stanford's English tests, MIT's "strongly recommend")
  and Korea University's optional standardized tests are `optional`.
- Only one item per kind is allowed. Where a page lists both the national CSCA report and optional SAT/A-Level
  results, `entrance_test` is the required one and the rest are in `notes`. A uni-assist VPD (LMU, FU Berlin)
  and the Argentine Ministry *convalidación* of a foreign secondary diploma (UBA) are `credential_evaluation`.
  A counselor's school report or Kyoto's Form B school evaluation is `academic_reference`, and teacher letters
  are `recommendation_letter`. A "statement of purpose" or UTokyo's 志願理由書 is `motivation_letter`. Kyoto's
  Form D essay and Harvard's supplement questions are `essay`.
- `academic_year` is set only where the page states one:
  - NTU Taiwan: "2027/2028 September Entry", recorded as `2027/2028`.
  - UTokyo: "2027 年度", recorded as `2027/2028 (2027年度, April 2027 entry)`.
  - Cambridge: "For 2027 entry", recorded as `2027/2028 (2027 entry)`.

  Everything else is `null`. Application-cycle labels go in `notes`, as they did in round 2. Examples are
  Korea University's "Key Changes for the 2027 Academic Year" in a Spring 2027 guide, the 2026 intake labels
  on Fudan, PKU, SJTU, ZJU and Tsinghua, Kyoto's "October 2027 Enrollment" and LMU's "nur gültig für
  Wintersemester 2026/27".
- **Older cycles.** Several Chinese lists are the 2026 intake's, the latest published on 2026-10-19. Korea
  University's and SNU's are the Spring 2027 guides, because no Fall 2027 guide exists yet. Universiti
  Malaya's FAQ was last updated in 2021. Each answer's `notes` says so, and a reviewer may want to re-read them
  once the 2027 lists appear.

## Results

| seed_id | university | page(s) | items (requirement) |
|---|---|---|---|
| qs2027-001 | MIT | first-year international applicants | Secondary School Report, transcript, SAT/ACT: required. English test: optional, recommended (4) |
| qs2027-003 | Stanford University | first-year requirements; international FAQ | Common App, ACT/SAT, School Report + counselor letter, official transcript, two teacher letters: required. Translation: conditional. English test: optional (7) |
| qs2027-005 | Harvard University | application requirements; international applicants | Common App, Harvard supplement questions, secondary school report, transcript, two teacher recommendations, SAT/ACT: required. Translation: conditional. English test: optional (8) |
| qs2027-006 | University of Cambridge | completing your UCAS application (2027 entry) | UCAS application, personal statement, school reference: required. Transcript: conditional (4) |
| qs2027-007 | Caltech | first-year application requirements | Common App/QuestBridge, two teacher letters, School Report, official transcripts, SAT/ACT: required. English test (international), translation: conditional. Portfolio: optional (8) |
| qs2027-013 | Peking University | 2026 Undergraduate Program Entrance Examination | passport page, proof of high-school education, transcript, personal statement, application form, photo: required. Translation: conditional (7) |
| qs2027-014 | Tsinghua University | list of uploading documents; eligibility; application procedures | application form, passport, graduation/pre-graduation certificate, CV, transcripts, national/international test results, two recommendation letters, personal statement, financial sponsor form: required. English test, translation: conditional (11) |
| qs2027-021 | UC Berkeley | requirements for international students | official exam results once admitted, English test, financial guarantee (admitted): conditional (3) |
| qs2027-026 | Fudan University | 2026 admission information, Chinese-taught undergraduate (PDF) | online application, passport, diploma, transcript, CSCA report, financial statement, photo, personal statement: required. Translation: conditional (9) |
| qs2027-036 | Shanghai Jiao Tong University | undergraduate programs in Chinese for international students | application form, transcript, pre-graduation certificate, CSCA score: required. English test: conditional (5) |
| qs2027-038 | Seoul National University | 2027 Spring undergraduate admissions guide (PDF) | application form, personal statement & study plan, recommendation letter, transcript, graduation certificate, passport, photo: required. English test, apostille (after preliminary admission), translation: conditional (10) |
| qs2027-039 | The University of Tokyo | 2027年度 外国学校卒業学生特別選考募集要項, Type 1 (PDF) | 入学志願票, 志願理由書, 成績証明書, 卒業(見込)証明書, EJU voucher, TOEFL/IELTS, passport: required. 推薦書 (一部必須), translation: conditional (9) |
| qs2027-047 | Zhejiang University | undergraduate application guide | online application, passport, diploma, transcripts, CSCA report, personal statement, two recommendation letters: required. English test (English-taught), translation: conditional (9) |
| qs2027-053 | Korea University | Spring 2027 international undergraduate application guide (PDF) | application copy, statement of purpose, photo, passport, transcript, graduation certificate, apostille: required. English test, translation (family documents), proof of bank balance (after admission): conditional. Standardized tests: optional (11) |
| qs2027-054 | National Taiwan University | admission guidelines, 2027/2028 September entry (PDF) | online application form, graduation certificate, transcript, photo, financial statement: required. Translation, English test (English-taught), recommendation letters (department): conditional (8) |
| qs2027-056 | Universiti Malaya | FAQ undergraduate international admission | e-application, photo, passport, certificate, transcripts: required. Translation, English test (if available), sponsor guarantee: conditional (8) |
| qs2027-061 | LMU München | Studienbewerbung für internationale Bewerbende | Hochschulzugangsqualifikation, VPD (uni-assist), Lebenslauf: required. Certified translation: conditional (4) |
| qs2027-063 | KFUPM | apply as an international student (SAT Track) | SAT scores, online application: required (2) |
| qs2027-064 | Kyoto University | Kyoto iUP application guidelines, October 2027 enrollment (PDF) | online application, photo, passport, transcripts, Form A (graduation), Form B (school evaluation), standardized test, Form D essay: required. English test (or Form C), translation: conditional (10) |
| qs2027-071 | Lund University | documentation (Bachelor's studies) | certificates and transcripts, final upper-secondary documents: required. English test: conditional (3) |
| qs2027-079 | Adelaide University | apply now: international students | online application, transcripts, passport: required. Graduation certificate (if applicable), translation, English test: conditional (6) |
| qs2027-084 | Universidad de Buenos Aires | CBC inscription news (2026); Dirección de Legalizaciones | legalized secondary certificate: required. Convalidación of a foreign diploma, apostille (pre-2010 diplomas): conditional (3) |
| qs2027-090 | Nanjing University | Institute for International Students: bachelor's programs | application form, passport, graduation certificate, score report, CSCA report, two recommendation letters, personal statement: required (7) |
| qs2027-091 | University of Copenhagen | bachelor admission; non-EU/EEA countries | application form, diploma, transcripts: required. Translation: conditional (4) |
| qs2027-099 | Freie Universität Berlin | application with non-German university entrance qualification | FU portal application, VPD, school-leaving certificates: required. Translation: conditional (4) |

**Unreadable (access).** Every refusal below is the production fetcher's answer. None was retried with a
different user agent or around robots.txt.

| seed_id | university | why |
|---|---|---|
| qs2027-004 | University of Oxford | `www.ox.ac.uk` undergraduate application guide answers HTTP 403 |
| qs2027-024 | University of Chicago | `collegeadmissions.uchicago.edu` international applicants page returns 45 readable characters (rendered client-side) |
| qs2027-058 | New York University | `www.nyu.edu` freshman how-to-apply page answers HTTP 403 |
| qs2027-077 | The University of Western Australia | `www.uwa.edu.au` international how-to-apply pages show only "Loading component..." (the steps are rendered client-side) |
| qs2027-086 | Universität Heidelberg | the application guide's "required documents" view (`/en/studium/bewerbungswegweiser/...`) returns only navigation (772 characters, rendered client-side). The certification page alone gives no document list |
| qs2027-097 | Institute of Science Tokyo | the 2027 私費外国人留学生特別選抜募集要項 PDF (`admissions.isct.ac.jp/plugins/cms/component_download_file.php?...`) returns an empty body to the fetcher. The English pages list no documents |

**Read but not drafted.**
- Uppsala University (qs2027-089): the application guide covers the international round for English-taught
  Bachelor's programmes, while the Computer Science bachelor is taught in Swedish and applied for through
  antagning.se. The documents themselves are on universityadmissions.se, which is not a UU domain.
- Sorbonne Université (qs2027-073): the "Postuler en Licence 1" page names only the DAP / Études en France
  application and a French B2 certificate (no vocabulary kind).
- Université Paris-Saclay (qs2027-076): the international first-cycle page names only the DAP dossier blanc /
  vert and eCandidat / Études en France steps.
- Université PSL (qs2027-034): the bachelor's page points to Parcoursup / Études en France only.
- The University of Osaka (qs2027-095): only the 2016 special-entrance guidelines were found, and that
  overseas route closed after AY2025 admission. The 2027 privately financed (私費外国人留学生) guide was not
  located.

**Not attempted in this round** (US universities, left for later): Yale, Princeton, UCLA and UCSD pages were
fetched but not drafted. Princeton's page has no checklist text, and Yale's
`admissions.yale.edu/application-requirements` answers 404. LSE (`/study-at-lse/undergraduate/how-to-apply`)
answered 404, and its replacement URL was not found.
