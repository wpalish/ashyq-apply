# KB stale-fact refresh, round 4 (CS bachelor, 2026-10-19)

A top-up of the committed KB (`backend/app/knowledge/kb_cs_bachelor.json`) for its `stale_facts`: 57 facts
(47 tuition, 10 deadline) at 52 universities. For each one we looked for the same fact on the
university's official site, published for the fall 2027 intake or the 2027/28 academic year.

Research was done on 2026-10-19 with live search frozen. Web search was used only to find official URLs,
never as evidence, and no paid search API was used. Every page was read with the production `Fetcher`
(the `verify_evidence` reader):

- the `ASHYQApplyBot` user agent, with no user-agent spoofing and no WAF bypass;
- robots.txt honoured, with no override;
- the sandbox HTTPS proxy, with TLS verified.

No heldout university was opened.

**Rule.** A fact is refreshed only when an official page prints the newer year or cycle next to the
figure or date. A draft is written only in that case. No year was inferred. That excludes a guideline
whose title names the 2027 intake but whose fee line prints no year, a deadline with no year, and an
undated fee table.

## Method

1. All 54 distinct source URLs of the 57 stale facts were re-read with the production `Fetcher`. All
   54 answered 200, and each still shows the year the KB already holds, or no year.
2. For each university, newer official pages were looked for. Web search was used to find URLs, plus a
   few guessable successor URLs, such as UCSD `…/registration/2027-28/`, Illinois `TermCode=120278` and
   Yonsei `2027_fee1.pdf`. Every candidate page was read with the same `Fetcher`.

## Files

- `core/<seed_id>.json` holds one file per refreshed university, in the `topup_round3` shape. `answers`
  holds only the refreshed answer.
- `evidence_check.container-2026-10-19.json` is the container pre-check from
  `scripts/verify_evidence.py --trust-env-proxy topup_round4`. Its result is 1 checked row, 1 official +
  quote_found. The other 5 rows are the unresearched questions: `unknown`, no URL. The file name
  contains `container`, so `kb_build` skips it.

The CI check is still needed: `benchmark-capture.yml`, `mode=verify_evidence`,
`extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_round4`. Save its report as
`topup_round4/evidence_check.ci-<date>.json`. Until that report exists, the draft stays unknown.

## Refreshed (1 fact)

| seed_id | university | fact | old year → new year | new value | source |
|---|---|---|---|---|---|
| qs2027-067 | University of Auckland | tuition | 2026 → 2027 | NZD 49,581.60 – 60,909.60 per year, Bachelor of Science, international (range by courses taken) | `auckland.ac.nz/en/study/fees-and-money-matters/tuition-fees/international-student-fees/undergraduate-international-fees.html`, table "2027 fees" |

**Build note (Auckland).** The 2027 figure is a calendar (NZ academic) year. `core_drafts.propose_tuition`
accepts only a `2027/28`-shaped year, and `stale_reasons` reads "2027" as ending in 2027. So after the CI
check, the rebuilt fact still carries `stale: true` ("academic year 2027 is before the fall 2027
intake's 2027/28"). It is still the latest published fee, and it replaces the 2026 one. The quote is the
table row only. The heading "2027 fees" sits about 1,050 characters before the row. A quote running from
the heading to the row would put the figure past the 600-character excerpt cut, so the heading is
recorded in the draft's notes instead. The quoted row occurs once on the page. The 2026 row reads
"NZ$47,221 - NZ$58,009".

## Still old (56 facts): no draft written

What the page shows on 2026-10-19 is given for each fact.

### Tuition, published for 2026/27 (or 2026), no 2027/28 figure found

| seed_id | university | page shows |
|---|---|---|
| qs2027-001 | MIT | "Cost of attendance for the 2026–2027 academic year", tuition $66,720 |
| qs2027-003 | Stanford | "2026-2027 Academic Year Tuition 67,731" |
| qs2027-005 | Harvard | "2026-2027 Cost of Attendance Tuition $62,226" |
| qs2027-011 | HKU | "HKD249,000 Per annum, 2026-2027 cohort". The press reports that 2027-28 non-local fees are published, but admissions.hku.hk (where they would be) has an unreachable robots.txt (ConnectTimeout), which counts as disallowed. |
| qs2027-012 | NTU Singapore | "Tuition fees for Academic Year 2026/2027" |
| qs2027-015 | UPenn | "Cost of Attendance 2026-2027 Academic Year" |
| qs2027-016 | Cornell | 2026-27 cost to attend (no 2027-28) |
| qs2027-017 | Yale | 2026-27 COA (no 2027-28) |
| qs2027-019 | UNSW | Programme page: "2026 Indicative First Year Fee $61,000". No 2027 UG fee on any readable official page. |
| qs2027-020 | Johns Hopkins | 2026-27 tuition (no 2027-28) |
| qs2027-021 | UC Berkeley | Fee schedule up to the 2026-27 cohort ($31,525/semester nonresident). No 2027-28 cohort column. |
| qs2027-026 | Fudan | The 2026 Chinese-taught UG guide (same PDF). The search found no 2027 UG guide on iso.fudan.edu.cn. |
| qs2027-027 | Princeton | 2026-27 cost (no 2027-28) |
| qs2027-030 | McGill | "Annual fees for 2026-2027" |
| qs2027-034 | PSL (Dauphine) | "Année universitaire 2026-2027". The page adds that rates "sont susceptibles d'évoluer pour l'année universitaire 2027 - 2028". |
| qs2027-038 | Seoul National University | The Spring 2027 guide gives the 2026 tuition. No Fall 2027 guide is published. |
| qs2027-042 | Yonsei | `2026_fee1.pdf`. `2027_fee1.pdf` answers with a 404 page. |
| qs2027-043 | Columbia | "Facts and Figures 2026-2027" |
| qs2027-047 | Zhejiang | The 2026 UG guide (same PDF). No 2027 guide was found, and iczu.zju.edu.cn HTML pages have an unreachable robots.txt (ConnectError). |
| qs2027-052 | CityU | The CS department page gives a non-local fee only up to "2026 HK$190,000". The local table runs to 2027/28 (HK$49,500), but that is not the international fee. www.cityu.edu.hk/admo answers with an empty Incapsula body. |
| qs2027-054 | NTU Taiwan | The 2027/2028 September Entry guidelines print "The 2026/27 Academic Year Tuition and Fees are listed below for reference. For the 2027/2028 Academic Year Tuition and Fees information, please refer to the latest information …". The 2027/28 fee is not published. |
| qs2027-055 | Carnegie Mellon | "2026-2027 Undergraduate Tuition & Fees" |
| qs2027-056 | Universiti Malaya | The programme page still shows "International RM 89,200" (2025/26 sheet). No 2026/27 or 2027/28 UG international sheet was found. |
| qs2027-058 | NYU | "Estimated Cost of Attendance 2026-2027" |
| qs2027-066 | Brown | "2026-2027 Undergraduate Student Tuition & Fees" |
| qs2027-070 | Duke | "2026-2027 Estimated Cost of Attendance" |
| qs2027-074 | UIUC | "2026 - 2027 Undergrad Tuition Rates" ($47,800 international, Engineering). The `TermCode=120278` (2027-28) page exists, but every rate is "$0.00", so it is not published. |
| qs2027-076 | Paris-Saclay | "Pour l'année 2026-2027, les droits d'inscription sont fixés comme suit". 2027-28 is set later by arrêté. |
| qs2027-081 | UC San Diego | The 2026-27 registration-fee page. `…/registration/2027-28/index.html` answers 404. |
| qs2027-093 | University of Washington | 2026-27 COA (no 2027-28) |
| qs2027-094 | Boston University | "Billed expenses for the 2026/2027 academic year" |

### Tuition with no academic year printed (standing fee pages), still undated

| seed_id | university | page shows |
|---|---|---|
| qs2027-008 | ETH Zurich | CHF 2,190 per semester for foreign students (ETH Board decision, from autumn 2025). No year. |
| qs2027-014 | Tsinghua | The Fees page (RMB 30,000/year), no year. The 2027 admission guides are out, but only for the English-taught Zijing/Zhishan programmes (not CS). The home page's 2027 schedule gives application rounds, not fees. |
| qs2027-022 | EPFL | CHF 2,190 per semester, with indexation "first adaptation in 2029". No academic year. |
| qs2027-044 | IP Paris | The Bachelor tuition-fees page, no year printed |
| qs2027-045 | Northwestern | "a standard academic year", no year printed |
| qs2027-049 | UCLA | "Updated July 2026 Cost Per Academic Year (Nine Months)", no year |
| qs2027-064 | Kyoto | The October 2027 Enrollment guidelines (same PDF) print "Undergraduate Course … JPY 535,800 (Annual)" with no year on the fee line. The intake is named only in the document title, so no year was inferred. |
| qs2027-071 | Lund | TGDAT: "Start Höst 2026", "Det finns inga tillfällen att söka till just nu". Total 555,000 kr, no HT2027 occasion yet. |
| qs2027-082 | KTH | "The full programme tuition fee … is SEK 453,000", no year |
| qs2027-086 | Heidelberg | EUR 1,500 per semester since WS 2017/18, no academic year |
| qs2027-090 | Nanjing | The tuition page, no year |
| qs2027-095 | Osaka | The tuition page, no year |
| qs2027-097 | Institute of Science Tokyo | The tuition page (EN and JA): the bachelor rate applies to students entering on or after 1 April 2019, no year |
| qs2027-099 | FU Berlin | The fee page: no tuition fee, as a standing policy; the semester fees shown are for WS 2026/27 |
| qs2027-100 | UZH | The fee page: CHF 720 per semester plus CHF 500 surcharge, no year |

### Deadlines, no fall 2027 date published

| seed_id | university | page shows |
|---|---|---|
| qs2027-006 | Cambridge | Not a past-year fact. "15 October 2026 Deadline to submit your UCAS application" is the 2027-entry deadline itself, and it has passed. The page lists only 2027-entry dates. The next one is 2028 entry, so there is nothing to refresh. |
| qs2027-010 | NUS | The SoC FAQ still gives the AY2026/27 window ("3 December 2025 to 23 February 2026"). The SoC admissions page ("NUS Computing Admissions 2027") lists AY2027/28 windows for the IB Diploma ("16 December 2026 to 17 February 2027"), the NUS High School Diploma, Polytechnic and A-Level. It gives none for "International Qualifications (All Nationalities)", the population of the stale fact. The NUS College page that reportedly gives the same IQ window (16 Dec 2026 – 17 Feb 2027) returns an empty challenge body, and nus.edu.sg/oam is behind Incapsula. **Not drafted:** the IB-only date is a different population. The main session should decide whether to add it as an IB-scoped fact. |
| qs2027-013 | Peking | The newest notices (id=813, 815, 818) are 2026-entry. No 2027 international UG notice was found. |
| qs2027-019 | UNSW | The UG offer-round table lists only Term 1 2027 rounds; the last completed-application deadline, 24 September 2026, has passed. The Term 2/3 2027 rows on the page belong to the postgraduate table. |
| qs2027-026 | Fudan | 2026 entry, Phase 2 "February 23 - March 6, 2026". No 2027 guide was found. |
| qs2027-038 | Seoul National University | Spring 2027 round (6–9 July 2026, closed). No Fall 2027 guide was found. |
| qs2027-047 | Zhejiang | The 2026 cycle (28 February 2026). No 2027 guide was found. |
| qs2027-053 | Korea University | "Fall 2027 … March, 2027 (TBA)". The fall round is not dated. |
| qs2027-056 | Universiti Malaya | Semester I (October) 2026/2027 window ("09 Feb 2026 30 Aug 2026"). The only later international UG window, "07 Sept 2026 30 Jan 2027", is Semester II (March) 2026/2027. |
| qs2027-075 | Trinity College Dublin | The course page still shows "Non-EU Applicants … 01/MAY/2026". The international how-to-apply page gives "June 30th" and "February 1st" with no year, and its footnote still says "September 2025 admission". The 2027 Admission Guide PDF gives no deadline. Not drafted, because no year is printed. |
