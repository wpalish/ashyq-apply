# KB gap fill, round 6 (CS bachelor, 2026-10-19)

A top-up of the merged knowledge base (`app.knowledge.load_knowledge_base()`) for the core questions still
empty (english, deadline, tuition, scholarship_exists, scholarship_international; gpa only where a minimum
is published) at 15 universities: UT Austin (072), KTH (082), UBA (084), Stanford (003), Harvard (005),
ETH Zurich (008), NUS (010), HKU (011), Peking (013), Yale (017), EPFL (022), TU Delft (048), UCLA (049),
University of Chicago (024) and Princeton (027). None is a heldout university.

Intake: fall 2027 (or the first intake of that academic year), international applicant, the KB entry's
programme. Research date 2026-10-19, with live search frozen. Web search was used only to find official URLs,
never as evidence, and no paid API was used. Every page was read with the production `Fetcher` (the
`verify_evidence` reader): the `ASHYQApplyBot` user agent, robots.txt honoured with no override, the sandbox
HTTPS proxy with TLS verified. Only official domains were used.

## Files

- `core/<seed_id>.json` is one file per university with at least one filled question, in the topup_round3
  shape. `answers` holds only the researched-and-filled questions.
- `evidence_check.container-2026-10-19.json` is the container pre-check:
  `scripts/verify_evidence.py --trust-env-proxy <this dir>`. Result: **7 rows, 7 official + quote_found**.
  The file name contains `container`, so `kb_build` skips it.

The CI check is still needed: `benchmark-capture.yml`, `mode=verify_evidence`,
`extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_round6`. Save its report as
`topup_round6/evidence_check.ci-<date>.json`. Until then these answers stay unknown. No KB rebuild was done.

## Filled

| seed_id | question | value | academic_year / cycle as printed | source |
|---|---|---|---|---|
| qs2027-082 KTH | deadline | 2027-01-15 (round 1, non-EU/EEA/Swiss) | "Application deadlines for studies starting 2027" | BSc ICT programme page (last changed Sep 28, 2026) |
| qs2027-008 ETH | deadline | 2027-03-31 23:59 CET (foreign school-leaving certificate) | "starting in autumn semester 2027" | eApply portal, www.lehrbetrieb.ethz.ch |
| qs2027-017 Yale | deadline | 2027-01-02 (Regular Decision) | "Important Dates 2026-2027" | 2026-2027 Information for Counselors (PDF) |
| qs2027-072 UT Austin | scholarship_exists | ISSS Scholarships for International Students (Texas Global) | "Fall 2027 and 2027-2028 academic year scholarships", window 1 Feb - 1 Mar 2027 | global.utexas.edu/isss/advising-services/scholarships |
| qs2027-072 UT Austin | scholarship_international | true | (same page) | same |
| qs2027-084 UBA | tuition | 0 ARS per year (free for Argentine and foreign citizens) | "2026" (ciclo lectivo 2026) | UBA Noticias 919, 11 Nov 2025 |
| qs2027-024 UChicago | tuition | USD 25,320 per quarter (College flat rate) | "2026-27" | bursar.uchicago.edu, Tuition and Fees 2026-27 College |

Notes for the reviewer:

- **Deadline years (KTH, Yale).** The date line itself prints no year; the quote includes the page's printed
  cycle heading ("studies starting 2027" with "16 October (2026): Application opens"; "Important Dates
  2026-2027" with decisions on March 31). Within that printed cycle the date can only be January 2027. If the
  owner wants the year printed next to the date itself, drop these two rows: they then fall under the pending
  `--yearless-deadlines-with-caveat` decision like the base drafts. ETH prints the full date with its year.
- **UT Austin, merge effect.** `kb_build` merges `scholarship_exists` as one unit, so this draft's ISSS award
  would replace the base award `incoming` (onestop.utexas.edu, "Incoming students ... will still be considered
  for scholarships that do not require financial need"), whose international eligibility no page states. The
  ISSS awards are explicitly for international students, but most are small (USD 2,000-5,000), several need
  two completed semesters at UT Austin or schooling in a given region, and an incoming first-year can apply
  to few of them. Same question as the round-3 IP Paris decision; the main session decides whether to keep it.
- **UBA and UChicago tuition** are previous-cycle figures (no 2027 statement or 2027-28 schedule exists yet).
  They are expected to be kept as **stale** facts with their printed year; they fill an empty question but are
  not current. UBA's free tuition is recorded as amount 0; the national proposal to charge non-resident
  foreigners is not reflected on any UBA page read. UChicago's figure is per quarter (not multiplied).

## Left unknown

| seed_id | question(s) | reason |
|---|---|---|
| qs2027-072 UT Austin | deadline | admissions.utexas.edu (international-students and freshman pages) prints "Regular Deadline To Apply December 1" without a year; the 2027 dates on the page are the decision dates. |
| qs2027-072 UT Austin | tuition | onestop cost of attendance is still the 2026-27 range ($42,554-$51,106 non-resident); no single amount and no 2027-28 figure. |
| qs2027-072 UT Austin | gpa | no minimum published (holistic review). |
| qs2027-082 KTH | tuition | full-programme fee SEK 453,000 still printed with no academic year (fees page last changed Feb 17, 2025); already in the KB as a stale fact. |
| qs2027-082 KTH | gpa | no grade threshold published. |
| qs2027-084 UBA | deadline | the 2027 ingreso (CBC preinscripción) is not announced: the newest uba.ar news (to 13 Oct 2026) has none; the 2026 cycle's 14-28 Nov 2025 window is another intake's. cbc.uba.ar is a JavaScript app (9 characters of text). |
| qs2027-084 UBA | scholarship_exists (unknown record) | the KB already holds the Sarmiento award (not open to foreigners without permanent residence); nothing new found. |
| qs2027-003 Stanford | deadline | "Standard Application Deadline - January 5" printed without a year (page updated September 10, 2026). |
| qs2027-003 Stanford | tuition | only 2026-2027 ($67,731) published; already a stale fact. |
| qs2027-003 Stanford | gpa | no minimum published. |
| qs2027-005 Harvard | deadline | "due by January 1 at 11:59pm" without a year. |
| qs2027-005 Harvard | tuition | only 2026-2027 ($62,226) published; already a stale fact. |
| qs2027-005 Harvard | gpa | no minimum published. |
| qs2027-008 ETH | tuition | CHF 2,190 per semester with no academic year (policy since autumn 2025); already a stale fact (standing-policy owner flag). |
| qs2027-008 ETH | gpa | no grade minimum; admission is country- and certificate-specific. |
| qs2027-010 NUS | english, tuition, deadline | nus.edu.sg/oam and the registrar fee PDF still return an empty Incapsula body (HTTP 200, 0 characters). The School of Computing FAQ gives only the AY2026/2027 application period and a fee range ("S$17,950 to S$18,900", year not stated, "fees for the upcoming academic year may change"). |
| qs2027-011 HKU | english, gpa, deadline | admissions.hku.hk and www.admissions.hku.hk: robots.txt unreachable (ConnectError), which counts as disallowed; www.cds.hku.hk robots.txt times out. Not overridden (the robots override is for CI evidence rows only). |
| qs2027-011 HKU | tuition | www.hku.hk still shows only the "2026-2027 cohort" fee (HKD 249,000); already a stale fact. |
| qs2027-013 Peking | tuition, deadline | no 2027 undergraduate notice on isd.pku.edu.cn yet; the 2026 notice defers tuition ("Further notice will be given after approval"). |
| qs2027-017 Yale | english | a test is required, but no minimum score is published. |
| qs2027-017 Yale | tuition | only 2026-27 ($72,500) published; already a stale fact. |
| qs2027-017 Yale | gpa | no minimum published. |
| qs2027-022 EPFL | deadline | "from mid-November to the 30th of April to start your studies at EPFL the following September" and "on April 30 at the latest": no year on any admission page read (how-to-apply, late application, criteria). |
| qs2027-022 EPFL | tuition | CHF 2,190 per semester "from the 2025 fall semester", no academic year; already a stale fact. |
| qs2027-048 TU Delft | - | nothing to fill: english, deadline (2027-01-15), tuition (2027/2028) are known; gpa and scholarships are not_applicable. |
| qs2027-049 UCLA | english | "We look for competitive English proficiency scores" (TOEFL 5 / 100, IELTS 7.5, DET 135): competitive, not a minimum. |
| qs2027-049 UCLA | gpa | indicative only (4.0 average for Fall 2025 admits). |
| qs2027-049 UCLA | deadline | "October 1 - November 30 Application filing period" without a year. |
| qs2027-049 UCLA | tuition | "Updated July 2026", table "Cost Per Academic Year (Nine Months)" with no year; already a stale fact. |
| qs2027-024 UChicago | gpa | no threshold ("Please do not convert your grades into a 4.0 scaled grade-point average"). |
| qs2027-027 Princeton | english, deadline, gpa | admission.princeton.edu robots.txt unreachable (ConnectError) on every try, so no page could be read; earlier rounds found no English minimum and a yearless "Jan. 1" deadline. |
| qs2027-027 Princeton | tuition | not re-read (robots); 2026-27 ($68,140) is already a stale fact. |

## Main session decision (2026-10-19)

UT Austin (qs2027-072) dropped before the CI check: the KB merges `scholarship_exists` as one answer, so
the ISSS awards (USD 2,000–5,000, mostly after two semesters at UT or for given regions) would replace the
incoming first-year award for an applicant who can rarely apply for them. The existing answer stays.
