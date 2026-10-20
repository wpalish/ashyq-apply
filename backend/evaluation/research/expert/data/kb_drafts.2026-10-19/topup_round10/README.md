# KB gap fill, round 10: tuition (CS bachelor, 2026-10-20)

This round tops up the merged knowledge base (`app.knowledge.load_knowledge_base()`) for one question,
`tuition`. The target is the CS bachelor recorded in each KB entry, for an international (non-EU,
for example Kazakh) first-year applicant entering in fall 2027 (or the first intake of that academic
year), with the fee per year as printed, its period and its currency.

The rules were these:

- The 2027/28 figure is preferred.
- A 2026/27 figure is accepted. The build keeps it as a stale fact with its printed year.
- A standing policy page with no year is accepted, and is noted as such.
- Free tuition counts as amount 0, with the quote.
- No year and no amount is inferred.
- A range is kept as printed in the notes. A value is drafted only when the page states one for the
  programme.

## Method

The research was done on 2026-10-20. Web search was used only to find official URLs, never as evidence,
and no paid API was used. Every page was read with the production `Fetcher` (the `verify_evidence`
reader):

- the `UnimatchBot/0.2` user agent, with no spoofing and no WAF bypass;
- robots.txt honoured, with no override;
- the sandbox HTTPS proxy (`trust_env_proxy=True`), with TLS verified.

Only official domains were used, and no held-out university was opened. Before researching, the
topup_round4, topup_round5 and topup_round6 READMEs were read. Questions those rounds had already left
unknown were re-checked on the current pages.

## Selection

The selection covers merged KB entries with no `tuition` fact: 24 entries, none of them held out. Ten
of them were skipped as container-blocked sites, as instructed: Oxford (004), UCL (009), NUS (010),
CUHK (018), Melbourne (023), Monash (031), Michigan (051), KU Leuven (059), Durham (085) and Alberta
(096). That leaves 14 researched entries: 007, 013, 035, 037, 046, 053, 063, 069, 072, 073, 077, 083,
091 and 092.

## Files

- `core/<seed_id>.json` holds one file per filled university, in the topup_round6 shape. `answers` holds
  only `tuition`.
- `evidence_check.container-2026-10-20.json` is the container pre-check, made with
  `scripts/verify_evidence.py --trust-env-proxy <this dir>`. It has 12 rows. Its result is **2 checked rows,
  2 official + quote_found** (`ok`, HTTP 200). The other 10 rows are the unresearched questions:
  `unknown`, with no URL. The file name contains `container`, so `kb_build` skips it.

The CI check is still needed: run `benchmark-capture.yml` with `mode=verify_evidence` and
`extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_round10`, and save its report as
`topup_round10/evidence_check.ci-<date>.json`. Until then these answers stay unknown. No KB rebuild was
done.

## Filled (2)

| seed_id | university | amount | currency | period | academic_year as printed | source |
|---|---|---|---|---|---|---|
| qs2027-077 | University of Western Australia | 54,400 | AUD | year | "2027" (table "Course fees for 2027", start year 2027) | `fees.uwa.edu.au/Browse/BrowseCourses?feeType=INTUG&feeYear=2027`, row "Bachelor of Advanced Computer Science (Honours) BH008 192 48 $54,400" |
| qs2027-063 | KFUPM | 0 (tuition waived) | SAR | year (convention; the page names none) | not stated (standing policy) | `kfupm.edu.sa/study/international-students/fees-and-scholarships`: "As an international student living outside Saudi Arabia, your tuition fees are waived. You will receive a full scholarship to attend KFUPM." |

Notes for the reviewer:

- **UWA.** The course pages still say "There is no current fee information available for this course.
  Please visit the fee calculator". The fee browser that the calculator links to publishes 2027 fees
  through a plain GET form. The year is a calendar (Australian academic) year, printed as "2027", not a
  2027/28 academic year. As with Auckland (topup_round4), `core_drafts.propose_tuition` is therefore
  expected to keep it **stale** ("academic year 2027"). It is still the newest published fee.
  - The same table gives the Bachelor of Science (BP004), the degree of the Computer Science major page,
    the same amount, "$54,400".
  - The page prints "$" only, and the currency is recorded as AUD.
- **KFUPM.** This is a standing policy with no year. KFUPM is not in `STANDING_FEE_POLICIES`, so the
  fee is kept **stale** ("the academic year is not stated") unless the main session adds KFUPM to the
  standing list. Two other points are for the reviewer:
  - The waiver is framed as a full scholarship. Base draft batch8 recorded it as `not_applicable`
    ("no amount published"), which the KB did not carry over.
  - Another official page conflicts with it. The Student Excellence & Success scholarship page
    (`ses.kfupm.edu.sa/scholarships`, no year) says "non-Saudis are expected to cover the tuition fees
    which is SR 20,000 per year", with need- and merit-based aid of 10–100% of tuition. The
    international-admissions page is the newer, applicant-facing one, but the reviewer decides which
    one governs, or drops the row.

## Left unknown (12)

| seed_id | university | reason |
|---|---|---|
| qs2027-007 | Caltech | The cost pages cannot be read. `www.finaid.caltech.edu` (costs page and 2025-26 fee PDF), `www.bursar.caltech.edu` and `www.catalog.caltech.edu` (undergraduate expenses) all answer HTTP 403. The robots.txt of `finaid.caltech.edu` is unreachable (ConnectError), which counts as disallowed. The readable `www.admissions.caltech.edu/afford` gives aid figures only, with no tuition. Base batch6 had 2026-27 tuition of $68,574 from the finaid page, which is now unreadable. |
| qs2027-013 | Peking | No 2027 notice exists. The newest undergraduate notice (`isd.pku.edu.cn/en/detail.php?id=818`, "2026 Undergraduate Program Entrance Examination") says "Tuition fee. Further notice will be given after approval." Ids 819–836 are 2026 scholarship, housing and office-hour notices, and ids 837–855 are empty ("内容不存在或已被删除"). The Yuke page on `isdplus.pku.edu.cn` (36,000 CNY) is the Fall 2021 pre-university programme, not the bachelor. |
| qs2027-035 | Edinburgh | The fee table is rendered client-side. Both pages read in the container have no figure in their readable text: the degree finder page (`study.ed.ac.uk/programmes/undergraduate-fees?programme_code=UTBSCIS`, "Estimate your tuition fees (2027–2028 entry)") and the registry page "Full-time fees for new students 2027-2028". The registry page also still says "The tuition fees published below only apply if you are entering study in 2026-2027". |
| qs2027-037 | King's College London | The fee is only in embedded JSON. The `…/computer-science-bsc/fees` page carries `"internationalFee":"35,800"` (and a second entry with "42,900") in its page-state script. Neither is in the readable text, so the quote check would fail. The university fees page gives the Home fee only. |
| qs2027-046 | UBC | The fee is not per year. The Vancouver Calendar (`vancouver.calendar.ubc.ca/fees/tuition-fees/undergraduate`) prints Science at "$1,789.18" per credit for international students (column "commenced in 2026S or later"). The page states no annual amount and no Science credit load, so nothing was multiplied. `students.ubc.ca` tuition pages answer HTTP 403. The 2027/28 tuition engagement proposes "+4%" for new international undergraduates, but that is a proposal with no amount. **Reviewer option:** draft the per-credit rate with `period: "credit"` if the KB should hold it. |
| qs2027-053 | Korea University | The category is undetermined. `oia.korea.ac.kr/oia2026/Tuition.do` gives "※ as of 2026 academic year / per semester": Natural Sciences approx. 6,700,000 KRW and Engineering approx. 7,700,000 KRW. Neither the tuition page nor the 2027 application guide says which tuition category the College of Informatics (Computer Science and Engineering) pays. The guide lists the college under the admission field "Science", but it does not name a tuition category, so none was inferred. `oia2027/Tuition.do` answers 404. |
| qs2027-069 | Birmingham | The international fee appears only after a country is chosen. The CS BSc course page's readable text shows only "£10,050 per year for domestic (UK) students for 2027/28", and the international figure (£33,300, base batch2) sits in embedded data. The university's international fees and undergraduate tuition pages give no international amount ("will be quoted on your offer letter"). |
| qs2027-072 | UT Austin | No single amount with its period. The cost of attendance for 2026-27 gives non-resident tuition as a range, "$42,554-$51,106" (Fall & Spring). The catalog's tuition tables (`catalog.utexas.edu/…/tables-tuition-for-fall-and-spring/`) give "Undergraduate Traditional Flat Rate Tuition: Fall 2026 - Spring 2027 Nonresident" with Natural Sciences at "$6,757 … 22,485" by hours (1 to 12+), but print no period on the table (per semester is implied, not printed). No 2027-28 figure is published. The onestop tuition-rate PDFs are on `utexas.box.com`, which is not an official domain. |
| qs2027-073 | Sorbonne | No amount is printed. The 2026/2027 enrolment page explains the differentiated fees for non-EU students (with exemptions and an exemption committee) but prints no amount. The figure on the page, the national €178, applies to students not subject to differentiated fees. |
| qs2027-083 | Sheffield | Only a university-wide range is published. `sheffield.ac.uk/new-students/tuition-fees/undergraduate-overseas` prints "For the 2027/28 academic year, the University of Sheffield will charge new full-time overseas undergraduates, tuition fees between £27,650 and £34,670 (except for Medicine and Dentistry courses)". No CS value is given. The course page's fee block is a JavaScript look-up, and the look-up tool's host, `tools.sheffield.ac.uk`, has an unreachable robots.txt (ConnectError), which counts as disallowed. **Reviewer option:** an Auckland-style range draft (amount 27,650, amount_max 34,670, GBP, year, "2027/28"), scoped to all overseas undergraduates. |
| qs2027-091 | Copenhagen | The fee is not in the readable text. The English and Danish CS bachelor pages give no fee, and `studies.ku.dk/bachelor/tuition-fees…` redirects to the bachelor index. The DKK 130,000 figure (base topup_imported) sits in an inline script with no year, as round 5 found. |
| qs2027-092 | Penn State | The fee table cannot be read. `tuition.psu.edu` and `bursar.psu.edu` answer HTTP 403. The Penn State Global "University Park Undergraduates: Breakout of Expenses" page renders its tuition table client-side; its readable text has only the policy text and living expenses ($20,700). Its PDF is on `psuglobalprod.prod.acquia-sites.com`, which is not an official domain. |
