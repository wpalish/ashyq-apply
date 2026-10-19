# KB gap fill, round 5 (CS bachelor, 2026-10-19)

A top-up of the merged knowledge base (`app.knowledge.load_knowledge_base()`) for the core questions still
unanswered at 12 universities: `english`, `deadline`, `tuition`, `scholarship_exists`,
`scholarship_international` (and `gpa` only where a page publishes a minimum). Target: the CS bachelor
recorded in each KB entry, an international applicant, the fall 2027 intake (or the university's first
intake of that academic year: Semester 1, February 2027 for Sydney).

Research was done on 2026-10-19 with live search frozen. Web search was used only to find official URLs,
never as evidence, and no paid search API was used. Every page was read with the production `Fetcher`
(the `verify_evidence` reader):

- the `ASHYQApplyBot` user agent, with no user-agent spoofing and no WAF bypass;
- robots.txt honoured, including `*`/`$` patterns. The KB-only robots override was not needed: no page
  read here was refused by robots.txt (Oxford's refusal is an HTTP 403 from the host itself, robots.txt
  included, which the override does not cover);
- the sandbox HTTPS proxy, with TLS verified.

Only official domains were used. No heldout university was opened. Before researching, the merged KB and
the earlier drafts (batch*, topup_imported, topup_round2–4, topup_tuition1) were read, and questions
those rounds had already settled as unknown were only re-checked where a new official page was found. A
**stale** fact (an earlier academic year, or a fee with no year) counts as answered and was not redone:
round 4 re-checked those on the same day.

## Files

- `core/<seed_id>.json`: one file per university with at least one filled question, in the
  `topup_round3` shape. `answers` holds the filled questions plus, as `status: unknown`, the questions
  that were researched and stay unknown, with the updated reason (the build never lets an `unknown`
  overwrite a known record).
- `evidence_check.container-2026-10-19.json`: the container pre-check,
  `scripts/verify_evidence.py --trust-env-proxy topup_round5`. Result: **5 checked rows, 5 official +
  quote_found** (`ok`, HTTP 200). The file name contains `container`, so `kb_build` skips it.

The CI check is still needed: `benchmark-capture.yml`, `mode=verify_evidence`,
`extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_round5`. Save its report as
`topup_round5/evidence_check.ci-<date>.json`. Until that report exists, these answers stay unknown.

## Filled (5 facts, 3 universities)

| seed_id | university | question | value | academic year / cycle | source |
|---|---|---|---|---|---|
| qs2027-028 | Sydney | scholarship_exists | Sydney International Student Award (20% of tuition for the course duration; partial) | "commencing in 2027" (printed) | `sydney.edu.au/study/fees-and-loans/scholarships/sydney-international-student-award.html` |
| qs2027-028 | Sydney | scholarship_international | true: "be an international student", **citizenship-restricted** to listed countries/regions (Kazakhstan is listed) | "commencing in 2027" | same page |
| qs2027-042 | Yonsei | scholarship_exists | Global Korea Scholarship (GKS): government-funded (NIIED), tuition + stipend + insurance + airfare | not printed | `yonsei.ac.kr/en_sc/2245/subview.do` |
| qs2027-042 | Yonsei | scholarship_international | true: "International students have the opportunity to study at Yonsei University through the Global Korea Scholarship" | not printed | same page |
| qs2027-061 | LMU | tuition | EUR 0: "As of the winter semester 2013/14, no tuition fees are charged." | not stated (standing policy) | `lmu.de/en/workspace-for-students/abc-study-guide/fees-and-tuition-fees/` |

**Merge notes.**

- *Sydney*: `scholarship_exists` merges as a whole question. The base draft's Vice-Chancellor's
  International Scholarship was never verified (its source PDF is `too_large` for the reader, and the scheme
  web page renders its body client-side), so nothing known is displaced.
- *Yonsei*: GKS is a Korean-government scholarship, not a Yonsei-funded award. It is the only award
  that Yonsei's scholarship overview ties to the regular, Korean-taught undergraduate route, and the
  page names international students as eligible. NIIED country quotas and the cycle are not on the page.
  **Reviewer decision:** if the KB should hold institutional awards only, drop this draft before the CI
  check.
- *LMU*: the KB will keep this fee **stale** ("the academic year is not stated"). LMU is not in
  `STANDING_FEE_POLICIES`. The Studierendenwerk semester fee is separate and is not tuition.

## Per university

| seed_id | university | filled | left unknown, and why |
|---|---|---|---|
| qs2027-004 | Oxford | — | english, tuition, scholarship_exists/international: every www.ox.ac.uk URL (course page, CIS PDF, Reach Oxford, robots.txt) answers HTTP 403. The department site cs.ox.ac.uk (200) gives no English score, fee or award; it only says "All non-native English speakers must satisfy the University of Oxford's English language requirements". deadline: cs.ox.ac.uk prints "6pm (UK time) on 15 October" and "(usually) 15 October in the year before" with no year. gpa: offers are by qualification (A*AA, IB 39, AP), with no GPA minimum. |
| qs2027-091 | Copenhagen | — | deadline: every ku.dk page prints "15 March at 12:00" / "15. marts kl. 12" with no year. tuition: the non-EU bachelor page states that fees apply but gives no amount; the DKK 130,000 figure sits in an inline script with no year (base draft). scholarship: the only UCPH-administered scheme (the Danish Government Scholarship) is for master's students (base draft), and no bachelor award was found. |
| qs2027-034 | PSL (Dauphine) | — | deadline: the L1 runs through Parcoursup / Études en France / DAP, and no PSL page prints a date (the L1 MI page shows only "Année universitaire 2026/2027"). scholarship: Dauphine's aid page lists no Paris-campus Licence award open to a non-EU applicant: the CROUS grants need French tax residence, the merit exemption for non-EU students is "Master 1 Master 2" only, and the Licence awards are for the London and Frankfurt programmes. |
| qs2027-042 | Yonsei | scholarship (GKS) | deadline: the 2027 guide is for Spring (March 2027) entry (2026-09-01 to 09-17, past, already in the base draft). No Fall 2027 guide exists yet: `…/2027_9_docu/2027_9_intl_plan_eng.pdf` answers 404. english: not re-researched; round 3 found no score in the 2027 guide. |
| qs2027-073 | Sorbonne | — | tuition: the 2026/2027 page gives the national EUR 178, but non-EU students are liable to differentiated fees whose amount is not printed, with exemption case by case. 2027/28 is not published. scholarship: only the fee-exemption policy and state grants were found; there is no Sorbonne award for incoming international Licence students. |
| qs2027-076 | Paris-Saclay | — | deadline: the page says the DAP "must be made between the November and January preceding the academic year … Please go to the Ministry website to find the exact dates". No date is on universite-paris-saclay.fr. scholarship: the generic statement only, with no Licence scheme (base draft re-read). |
| qs2027-099 | FU Berlin | — | deadline: no WS 2027/28 date is published. The base quote has no year, and the Termine page shows only old consultation dates. |
| qs2027-028 | Sydney | scholarship (SISA) | deadline: the only statement is "Semester 1 (Feb) 1 December of the year prior to commencement", which is year-relative. The year was not inferred. |
| qs2027-037 | King's College London | — | tuition: the international fee is not in the served HTML. The course page fee block is client-side, and the raw HTML holds no fee figure. The tuition-fees page gives the Home fee only. scholarship: no international undergraduate entry award on kcl.ac.uk (base draft: the funding database lists only Sanctuary and Hardship schemes). |
| qs2027-052 | CityUHK | — | english, gpa, deadline, scholarship_international: www.cityu.edu.hk/admo still returns an empty body (HTTP 200, 0 characters). The department page (cs.cityu.edu.hk) states no residency condition for its entrance awards. |
| qs2027-061 | LMU | tuition | deadline: "15. Juli für das Wintersemester" with no year. The process is being redesigned from SoSe 2027 ("Ab Dezember 2026 finden Sie weitere Informationen"), and no WS 2027/28 date is published. |
| qs2027-071 | Lund | — | deadline: the Swedish-taught programme has no HT 2027 occasion on lu.se ("Det finns inga tillfällen att söka till just nu", round 4). The national round dates are on antagning.se, which is not an official lu.se host. |

No `gpa` was filled: none of the pages read publishes a minimum.
