# KB application documents, round 4: the unreadable ones (CS bachelor, 2026-10-19)

The fourth batch of drafts for the KB question `documents` (`docs/process/KNOWLEDGE_BASE.md`, "Application
documents"), in the same shape as `topup_documents1` to `topup_documents3`: one item per document an official
page lists for an international applicant to the bachelor's programme, each with its kind, `required` /
`optional` / `conditional` (with the page's condition), the URL and a verbatim quote that names the document.
Target: bachelor's in Computer Science, international applicant, fall 2027 intake.

This round went back to the universities the earlier rounds listed as unreadable (HTTP 403/405, robots.txt
unreachable, client-rendered, empty body) and to the KB universities no round had drafted. Every page was read
with the production `Fetcher` with `trust_env_proxy=True` (the production user agent, robots.txt honoured, the
sandbox HTTPS proxy, verified TLS), as `verify_evidence --trust-env-proxy` does. Where the main page was
client-rendered or refused, an official alternative on the university's own domain was looked for (a PDF guide,
a department page, the current path of a moved page). Web search was used only to find URLs. There was no
user-agent spoofing, no WAF bypass and no paid search API. The KB-only robots exception (AGENTS.md §6, owner
2026-10-19) was tried, exactly as `verify_evidence --robots-override-kb` implements it, on three refused official
URLs (`uic.yonsei.ac.kr/admission.php`, `admissions.psu.edu/apply/...`, `www.hku.hk/intl`); none gave a usable
page (an error page, a redirect to `www.psu.edu/404`, a redirect to an unreachable host), so **no draft rests on
the override**: every quoted page below was read with robots.txt honoured. No heldout university was opened.

## Files

- `core/<seed_id>.json`: one file per university, `questions_researched: ["documents"]`, `answers` holds only
  `documents`. A documents-only draft is merged into the university's entry and never becomes its base
  (`kb_build._documents_only`). All 15 universities are already in the KB.
- `core/evidence_check.container-2026-10-19.json`: the container pre-check, run from `backend` as
  `PYTHONPATH=. .venv/bin/python scripts/verify_evidence.py --trust-env-proxy
  evaluation/research/expert/data/kb_drafts.2026-10-19/topup_documents4/core --out <report>`. The result is in
  "Container check" below. The file name contains `container`, so `kb_build` skips it. The CI check
  (`benchmark-capture.yml`, `mode=verify_evidence`,
  `extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_documents4`) is still needed; keep
  its report at `topup_documents4/evidence_check.ci-<date>.json`. Until then these documents stay unknown.

## Rules the drafts follow

Those of rounds 1-3. A document is drafted only if the page names it; a general "other documents may be
required" is not turned into items; things with no vocabulary kind (STARS / self-reported academic records,
Yonsei's Academic History Record sheet and parents' documents, birth certificates, criminal-record statements,
medical reports, grading-system explanations, fee receipts) go in the answer's `notes`, and so does a page that
says a document is **not** wanted (UCLA and Penn State: no recommendation letters; NTU: no personal statement or
recommendation except for Medicine; UCLA/UCSD: SAT/ACT not considered). Where one sentence lists several
documents (Sydney, Birmingham), each item quotes the part of it that names its own document. `conditional`
carries the page's condition; "if available" / "if applicable" are conditions, "should you wish to include
them" and "optional" are `optional`.

`academic_year` is set only where the page prints one:

| seed_id | item(s) | academic_year | printed |
|---|---|---|---|
| qs2027-040 Manchester | `academic_reference`, `english_test_report` (BSc Computer Science course page) | `2027/2028 (Year of entry: 2027)` | "Year of entry: 2027" |
| qs2027-010 NUS | `essay` (application guide) | `2026/2027` | "ACADEMIC YEAR 2026/2027" |

**`cycle_stated` / `cycle_is_intake: false`** (the list is printed for another cycle than the fall 2027 intake):

| seed_id | level | cycle_stated | why |
|---|---|---|---|
| qs2027-010 NUS | answer | Updated as of November 2025 | the supporting-document guide of the 2026 intake (it speaks of applicants "graduating from high school in 2026"); the 2027 guide was not yet published |
| qs2027-010 NUS | `essay` | ACADEMIC YEAR 2026/2027 | the application guide's own heading |
| qs2027-042 Yonsei | answer | Fall Semester 2026 | the latest guide found on an official host; the Spring 2027 guide's URL was not found and no Fall 2027 guide exists yet |

## Results

| seed_id | university | page(s) | items (requirement) |
|---|---|---|---|
| qs2027-004 | University of Oxford | Department of Computer Science "How to apply" (cs.ox.ac.uk) | UCAS application, academic referee, TMUA: required (3) |
| qs2027-010 | NUS | OAM Education and Supporting Document Guide (PDF); international qualifications application guide (PDF) | passport, online application form, short response questions (essay): required. Exam result slips (transcript), English test, SAT/AP/ACT: conditional (6) |
| qs2027-012 | NTU Singapore | admissions FAQ (international students' supporting documents); application process | online application form, passport, high school result slip/certificate/diploma, secondary school result slip: required. English test, translation: conditional (6) |
| qs2027-017 | Yale University | requirements; international applicants; standardized testing | Common App/Coalition/QuestBridge, two teacher letters, counselor letter, School Report with transcript, SAT/ACT: required. English test, certified translation: conditional (7) |
| qs2027-028 | The University of Sydney | how to apply as an international student | direct application, certificates and transcripts, English proficiency, proof of identity (passport): required. Translation, CSSD verification (China), CV: conditional (7) |
| qs2027-029 | ANU | international applications; documentation requirements | online application, English proficiency proof, secondary transcript: required. Official ID (if offered a place), translation: conditional (5) |
| qs2027-040 | The University of Manchester | how to apply (2027 entry); UCAS personal statement; BSc Computer Science (2027) | UCAS application, personal statement, reference, English evidence: required (4) |
| qs2027-041 | The University of Queensland | submit your application (senior schooling outside Australia) | application form, certified transcripts, passport or national ID, English evidence: required. Award certificate/testamur: conditional (5) |
| qs2027-042 | Yonsei University | Fall Semester 2026 Application Guide for International Students (PDF) | application form, personal statement, diploma, transcripts, apostille, passport: required. Translation, language certificate (choose one), China CHSI verification: conditional. Standardized tests: optional (10) |
| qs2027-049 | UCLA | international applicants; first-year requirements | UC application, Personal Insight Questions: required. TOEFL/IELTS/DET, secondary records (if admitted), proof of funds: conditional (5) |
| qs2027-052 | CityUHK | List of Supporting Documents for Application Review (PDF) | transcript (per qualification), diploma (if awarded), certified English translation, English results (if available), SAT/ACT/AP (if available): conditional (5) |
| qs2027-069 | University of Birmingham | your journey to Birmingham (supporting documents); undergraduate apply (2027 entry) | UCAS application, results transcript, personal statement, references, passport: required. English certificate: conditional (6) |
| qs2027-081 | UC San Diego | international students | English proficiency: required. Official records (newly admitted), proof of funds (visa): conditional (3) |
| qs2027-088 | University of Technology Sydney | International Student Undergraduate Application Form (PDF), checklist | application form, certified passport, English proficiency, certified qualifications and transcripts: required. Translation, sponsor guarantee letter, supporting statement/portfolio: conditional (7) |
| qs2027-092 | Pennsylvania State University | admission requirements for international students; steps to apply | online application: required. English proficiency, secondary records (after accepting an offer), diplomas, translation, financial certification (admitted): conditional. SAT/ACT, personal statement: optional (8) |

What changed since the earlier rounds for the ones that were unreadable: NUS's PDFs on `nus.edu.sg` and NTU's
sub-pages were readable this time; ANU's robots.txt was reachable; Sydney's and Manchester's old URLs redirect to
`http://` URLs that answer 405 while the current `https://` paths are readable; Penn State's admissions pages moved
to `www.psu.edu/resources/international-students/`; Yonsei's general international guide is on `www2.yonsei.ac.kr`
(the UIC host stays refused); CityUHK's document list is a PDF; Oxford's central pages answer 403 but the
Computer Science department's page does not.

## Still unreadable (access)

Every refusal below is the production fetcher's answer on 2026-10-19 with `trust_env_proxy=True`; none was
retried with another user agent.

| seed_id | university | why |
|---|---|---|
| qs2027-009 | UCL | every `www.ucl.ac.uk` page answers HTTP 403 (Cloudflare challenge, also to curl), including the root |
| qs2027-011 | The University of Hong Kong | `admissions.hku.hk` resets the connection (robots.txt unreachable); `www.hku.hk/intl` redirects there |
| qs2027-018 | CUHK | `admission.cuhk.edu.hk`: TLS verification fails in the container ("self-signed certificate in certificate chain"), robots.txt unreachable |
| qs2027-023 | The University of Melbourne | every `study.unimelb.edu.au` and `www.unimelb.edu.au` page answers HTTP 403, including the root |
| qs2027-024 | University of Chicago | `collegeadmissions.uchicago.edu` returns 45 readable characters (rendered client-side); no official alternative page or PDF was found |
| qs2027-031 | Monash University | every `www.monash.edu` / `www.monash.edu.au` page answers HTTP 403, including the root |
| qs2027-043 | Columbia University | `undergrad.admissions.columbia.edu` and `www.columbia.edu` answer HTTP 403 (the CS department host is readable but lists no application documents) |
| qs2027-051 | University of Michigan-Ann Arbor | `admissions.umich.edu` and `umich.edu` answer HTTP 403; the TeamDynamix knowledge-base article "Materials Needed to Complete a First-year Application" (`teamdynamix.umich.edu`, ID 7570) fails TLS verification in the container ("self-signed certificate in certificate chain"), also under the robots override |
| qs2027-058 | New York University | `www.nyu.edu/admissions/...` answers HTTP 403 (the home page is readable) |
| qs2027-059 | KU Leuven | `www.kuleuven.be` resets the connection (robots.txt unreachable) |
| qs2027-065 | KAIST | `admission.kaist.ac.kr`: TLS verification fails in the container ("self-signed certificate in certificate chain"); the guides are only on that host |
| qs2027-077 | The University of Western Australia | the international how-to-apply page still shows only "Loading component..." (steps rendered client-side) |
| qs2027-085 | Durham University | every `www.durham.ac.uk` / `www.dur.ac.uk` page answers HTTP 403, including the root |
| qs2027-086 | Universität Heidelberg | the application and study-requirement pages say the documents to submit appear only in the Study Programme Finder's application profile (rendered client-side) |
| qs2027-095 | The University of Osaka | the 2027年度 私費外国人留学生特別入試 学生募集要項 (`www.osaka-u.ac.jp/{ja,en}/admissions/faculty/expense/files/2027shihi_guideline.pdf`) is 5,341,139 bytes, over the fetcher's 5,000,000-byte limit (`too_large`); the readable FAQ and certificate notes defer the document list to that guide |
| qs2027-096 | University of Alberta | every `www.ualberta.ca` page answers HTTP 403, including the root; `calendar.ualberta.ca` asks for a 120 s crawl delay (over the 30 s the check waits) |
| qs2027-097 | Institute of Science Tokyo | the 令和9（2027）年度 私費外国人留学生特別選抜 学生募集要項 for the 理工学系 schools (`r9-guidelines-shihi`, published 2026-10-19) downloads, but it is an AES-encrypted PDF that the production `pdf_to_text` (pypdf without `cryptography`) returns as empty text; the readable 2027 guide on the same page is the medical/dental one |
| qs2027-027 | Princeton University | `admission.princeton.edu`: TLS verification fails in the container ("self-signed certificate in certificate chain"), robots.txt unreachable |

Several "self-signed certificate in certificate chain" and connection-reset failures are the container's egress
(curl from the same container fails the same way); the CI runner may read these hosts.

**Read but not drafted.**
- University of Amsterdam (qs2027-060): the Informatica bachelor is Dutch-taught; its "Toelating en inschrijven"
  page names only the Studielink registration and says the UvA then e-mails a request for information about a
  foreign prior education, without naming documents.
- LSE (qs2027-062) and Institut Polytechnique de Paris (qs2027-044) have no Computer Science bachelor in the
  KB (`programme.status: unknown`); LSE's "How to apply" page (2027 entry, UCAS only) was read but not drafted.
- Science Tokyo (qs2027-097): the English pages list no documents (see above).

## Container check

See the end of this file (filled in after the run).
