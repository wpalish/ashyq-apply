# KB application documents, pilot round 1 (CS bachelor, 2026-10-19)

The first drafts of the new KB question `documents` (`docs/process/KNOWLEDGE_BASE.md`, "Application
documents"): one item per document an official page lists for an international applicant to the bachelor's
programme, each with its kind, `required` / `optional` / `conditional` (plus the page's condition), the URL and
a verbatim quote. Researched 2026-10-19 with live search frozen: web search was used only to find official
URLs. Every page was read with the production `Fetcher`: the production user agent, robots.txt honoured,
through the sandbox HTTPS proxy, with TLS verified. There was no user-agent spoofing, no WAF bypass, no robots
override and no paid search API. No heldout university was opened.

## Files

- `core/<seed_id>.json`: one file per university, `questions_researched: ["documents"]`, `answers` holds only
  `documents`. A documents-only draft is merged into the university's entry and never becomes its base
  (`kb_build._documents_only`), although `topup_documents1` sorts before `topup_imported`.
- `core/evidence_check.container-2026-10-19.json`: the container pre-check,
  `scripts/verify_evidence.py --trust-env-proxy topup_documents1/core`. Result: **46 document rows, 46 official
  + quote_found** (the other 48 rows are the six unresearched core questions, `unknown`, no URL). Each document
  is its own row, item `documents.<kind>`. The file name contains `container`, so `kb_build` skips it. The CI
  check (`benchmark-capture.yml`, `mode=verify_evidence`,
  `extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_documents1`) is still needed; keep its
  report at `topup_documents1/evidence_check.ci-<date>.json`. Until then these documents stay unknown.

## Rules the drafts follow

- Only a document the page names is drafted; a page's general "you may be asked for other documents" is not
  turned into items. Things with no vocabulary kind (ETH's signed declaration of consent, Delft's residence
  permit, TCD's fee payment form, a German language certificate) are left in the answer's `notes`.
- A page that tells applicants **not** to send something (ETH: no motivation letters, portfolios or reference
  letters for Bachelor's admission) cannot be expressed as an item; it is recorded in `notes` only.
- `conditional` carries the page's own condition ("documents not in English", "first language is not
  English", "US and Canadian applicants only").
- `academic_year` is set only where the page states it (Imperial's TMUA: "for 2027 entry"; UBC's 2027-cycle
  document deadlines). Everything else is `null`: the lists are standing policy pages.

## Results

| seed_id | university | page(s) | items (requirement) |
|---|---|---|---|
| qs2027-008 | ETH Zurich | bachelor how-to-apply (non-Swiss certificate) | photo, passport, CV, secondary diploma, transcript (school reports, last 3 years), application form (eApply) — required; translation, entrance test — conditional |
| qs2027-048 | TU Delft | BSc international diploma, admission requirements | secondary diploma, transcript, English test report (TOEFL/IELTS/Cambridge), CV, passport — required; translation — conditional |
| qs2027-002 | Imperial College London | UG application process; Computing BEng page | UCAS application, personal statement, academic reference, TMUA (2027 entry), English — required |
| qs2027-032 | University of Toronto | After you apply: Required Documents | transcripts — required; English proof, standardized tests, notarized translations — conditional |
| qs2027-046 | University of British Columbia | Submit your documents; personal profile | transcript — required; ELAS documents — conditional (or a waiver request); personal profile (essay) — required for high school applicants |
| qs2027-035 | University of Edinburgh | What you need to apply; submitting certificates | UCAS application, personal statement, reference, English evidence, passport scan — required; school leaving certificate (after a firm acceptance), translations — conditional |
| qs2027-067 | University of Auckland | Documents to support your application | transcript, English test report — required; identity document (passport or birth/citizenship certificate), translation, portfolio/supplementary forms — conditional |
| qs2027-075 | Trinity College Dublin | Direct application information (non-EU) | application form, second-level results, two letters of recommendation, passport, personal statement — required; English scores, SAT/AP/ACT, translation — conditional. The page's application dates are for the 2026 cycle; the document list states no year |

**Not drafted (access).** NUS: the OAM supporting-documents PDF and page answer with an empty, non-PDF body to
the production fetcher (`www.nus.edu.sg`), and `nus.edu.sg`'s robots.txt was unreachable (treated as a full
disallow). KAIST: `admission.kaist.ac.kr` robots.txt unreachable (treated as a full disallow). University of
Melbourne: `study.unimelb.edu.au` answers HTTP 403. KU Leuven: network unavailable from the sandbox. All four
stay without a document list; the kb-mode document stage keeps asking for them.
