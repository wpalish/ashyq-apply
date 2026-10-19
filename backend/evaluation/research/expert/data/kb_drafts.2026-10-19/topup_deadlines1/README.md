# KB deadline pass, batch 1 (K1 / W1, CS bachelor, 2026-10-19)

This top-up covers the merged knowledge base (`app.knowledge.load_knowledge_base()`, 98 universities). It
looks for the official international/undergraduate application deadline that a fall-2027 applicant applies
under, with a verbatim quote that prints the year. On the same page visits it also looks for a
`not_applicable` GPA or scholarship statement backed by a clear quote.

Research was done on 2026-10-19 with live search frozen. Web search was used only to find official URLs and
never as evidence. Every page was read with the production `Fetcher` (the `verify_evidence` reader):

- the `ASHYQApplyBot` user agent, with no user-agent spoofing;
- robots.txt honoured, including `*`/`$` patterns;
- the sandbox HTTPS proxy, with TLS verified;
- no WAF bypass and no robots override.

Only official domains were used (`kb_top100_list.json` `official_domain` + `extra_domains`). No heldout
university was opened.

## Selection (20)

- **Stale ten:** the deadline facts that had passed on 2026-10-19: Cambridge, NUS, Peking, UNSW, Fudan, SNU,
  Zhejiang, Korea, Universiti Malaya and TCD.
- **Unknown ten:** the ten highest-ranked `unknown` deadlines by `list_index`: MIT, Stanford, Oxford,
  Harvard, ETH Zurich, UCL, HKU, CUHK, Cornell and Yale.

## Rule that decides most rows

`core_drafts.propose_deadline` keeps a deadline `known` only when the year of the date is printed in the
quote's first 600 characters. It also needs the date to be on or after the research date and not marked
as the 2026 cycle. A year-less date stays unknown, whatever the cycle obviously is. A long quote that
merely spans to a "Fall 2027" heading elsewhere on the page was not used. For example, the Cornell blog's
"open for Fall 2027 applicants" sits 2,250 characters before "by January 2".

## Files

- `core/<seed_id>.json` holds only questions that were **filled**, in the topup_round2 shape. There is one
  file: NUS `gpa` `not_applicable`. Questions that were researched and are still unknown are listed below and
  in that file's `questions_researched_not_filled`. They are not written as `unknown` answers. A top-up
  `unknown` never overwrites a base value, and the base unknown reasons for the unknown ten already
  describe the same state.
- `core/evidence_check.container-2026-10-19.json` is the container pre-check. It ran
  `scripts/verify_evidence.py <this dir> --trust-env-proxy`, and its result is **1 row, 1 official +
  quote_found**. The file name contains `container`, so `kb_build` skips it. The CI check is still needed:
  `benchmark-capture.yml`, `mode=verify_evidence`,
  `extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_deadlines1`. Save its report as
  `topup_deadlines1/evidence_check.ci-<date>.json`.
- `programme/` is empty because no programme pages were re-researched. Its evidence check is `[]`.

## Results

| seed_id | university | deadline result (2026-10-19) | other |
|---|---|---|---|
| qs2027-006 | Cambridge | **still unknown (passed)**. The 2027-entry page ("start ... in 2027?") gives the UCAS deadline as 15 October 2026, which has already passed. The 2028-entry dates are not published. The KB keeps it as a stale fact. | — |
| qs2027-010 | NUS | **still unknown**. The SoC FAQ still lists only AY2026/27 ("International Qualifications (All Nationalities): 3 December 2025 to 23 February 2026"). nus.edu.sg/oam (important dates, international qualifications) returns HTTP 200 with an empty Incapsula body. | **gpa filled: not_applicable**. The SoC FAQ says "Thus, there is no fixed minimum grade required for admission." |
| qs2027-013 | Peking | **still unknown**. The undergraduate listings (items.php?category2=36/37) hold only the 2026 notices (id=813/816/818; windows to 28 February 2026). There is no 2027 notice. | — |
| qs2027-019 | UNSW | **still unknown (passed)**. The undergraduate offer-round table for non-ISA countries lists only Term 1 2027, and its last completed-application deadline was 24 September 2026. There is no undergraduate Term 2/3 2027 round table: the long general schedule sits under "Applications for postgraduate programs". Offers for ISA-eligible countries are weekly, with no deadline. | — |
| qs2027-026 | Fudan | **still unknown**. The iso.fudan.edu.cn 本科生 list's latest guide is "2026年…本科生中文授课项目招生简章" (posted 2025-09-29). No 2027 guide yet. | — |
| qs2027-038 | SNU | **still unknown (access)**. en.snu.ac.kr robots.txt was unreachable (ConnectError), which RFC 9309 treats as a full disallow. The Spring 2027 round (6 to 9 July 2026) has passed, and no Fall 2027 guide could be read. | — |
| qs2027-047 | Zhejiang | **still unknown**. The Bachelor's application guide page is still "Application Guide for Undergraduate Programs 2026" (1 December 2025 to 28 February 2026). No 2027 guide yet. | — |
| qs2027-053 | Korea University | **still unknown**. On oia.korea.ac.kr Admission-Guide, Spring 2027 closed on August 31, 2026, and Fall 2027 reads "March, 2027 (TBA)". | — |
| qs2027-056 | Universiti Malaya | **still unknown**. study.um.edu.my/how-to-apply shows only Academic Session 2026/2027. The Semester I (October) international window, 09 Feb to 30 Aug 2026, has passed. A Semester II (March) international window to 30 Jan 2027 exists, but the CS (Software Engineering) programme lists an October intake only. | — |
| qs2027-075 | TCD | **still unknown**. The CS course page still shows "Non-EU Applicants ... 01/MAY/2026". The international how-to-apply page says "Final deadline for Application June 30th" and "Applications are accepted from October each year for entry September the following year", with no year. The 2027 non-EU Admission Guide PDF prints no deadline. | — |
| qs2027-001 | MIT | **still unknown (no year)**. The deadlines page says "Regular Action (RA) applications are due January 4". The international page and the catalogue print no dated deadline. | — |
| qs2027-003 | Stanford | **still unknown (no year)**. The first-year page says "Standard Application Deadline - January 5" (updated September 10, 2026), and the counselor resources page says "January 5 (Regular Decision)". Neither prints a year. | — |
| qs2027-004 | Oxford | **still unknown (no year; passed)**. cs.ox.ac.uk says "6pm (UK time) on 15 October" with no year. For 2027 entry that date has passed. | — |
| qs2027-005 | Harvard | **still unknown (no year)**. The page says "Regular Decision candidates apply by January 1". /application-timeline redirects to the same page. | — |
| qs2027-008 | ETH Zurich | **still unknown (no year)**. The page says "from 1 December to 31 March, 23:59 Central European Time". Both registration-application URLs redirect there, and the bachelor application overview reads 379 characters. | — |
| qs2027-009 | UCL | **still unknown (access)**. www.ucl.ac.uk returns HTTP 403 (Cloudflare) for the production user agent. | — |
| qs2027-011 | HKU | **still unknown (access)**. admissions.hku.hk robots.txt was unreachable (ConnectTimeout), so the site counts as disallowed. | — |
| qs2027-018 | CUHK | **still unknown (access)**. admission.cuhk.edu.hk robots.txt was unreachable (ConnectError), so the site counts as disallowed. | — |
| qs2027-016 | Cornell | **still unknown (no year in the application quote)**. Admissions says "January 2 Application; application fee or fee waiver". The finaid international page prints "Regular Decision: January 2, 2027", but that is the CSS Profile deadline, not the application. The blog's "Fall 2027" is out of quote range. | — |
| qs2027-017 | Yale | **still unknown (no year)**. /apply says "Regular Decision (Deadline: January 2)", and /timelines says "Application Deadline: January 2". | — |

**Summary:** deadlines found 0 of 20; NUS GPA `not_applicable` was added. Why the deadlines are still unknown:

- 8 have the 2027 cycle published but with no year printed: MIT, Stanford, Harvard, Yale, Cornell, ETH, TCD and Oxford.
- 7 have no 2027-cycle date yet: NUS, Peking, Fudan, Zhejiang, Korea (Fall 2027 TBA), UM and UNSW (no UG round after the passed Term 1 rounds).
- 1 has the 2027-entry date already passed: Cambridge. Oxford's date has also passed.
- 4 are access-blocked: UCL, HKU, CUHK and SNU.

**Suggested handling (not done here):**

- The year-less US/ETH dates need an owner ruling (a Q7-style "current cycle, year not printed").
- The access-blocked four need the self-hosted refresh run.
- The Chinese, Korean, Malaysian and NUS rows should be re-checked when those universities publish
  their 2027 guides, typically November to December 2026; Korea's Fall 2027 round is due in March 2027.
