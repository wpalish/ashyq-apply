# KB gap fill, round 3 (CS bachelor, 2026-10-19)

A top-up of the merged knowledge base (`app.knowledge.load_knowledge_base()`) for two questions:

- (a) `english` with no fact and no `not_applicable`;
- (b) `scholarship_international` unknown while `scholarship_exists` is known.

Research was done on 2026-10-19 with live search frozen. Web search was used only to find official URLs,
never as evidence, and no paid search API was used. Every page was read with the production `Fetcher`
(the `verify_evidence` reader):

- the `ASHYQApplyBot` user agent, with no user-agent spoofing and no WAF bypass;
- robots.txt honoured, including `*`/`$` patterns, with no override;
- the sandbox HTTPS proxy, with TLS verified.

Only official domains were used. No heldout university was opened.

## Selection

The gaps were listed from the merged KB. These hosts were left out because their access block is already
recorded: Oxford, UCL, Melbourne, Monash, Michigan, NYU, Alberta, Durham, Columbia, CUHK, HKU admissions
and SNU. That left 15 English gaps and 3 scholarship gaps (CityU appears in both lists).

What round 2 and the deadline pass already established was not repeated. For example, Northwestern, UIUC,
UPenn, Yale, Princeton and UCLA publish no English minimum, and the IP Paris Excellence Scholarship states
no nationality condition. Those rows were only re-checked when a new official page was found.

## Files

- `core/<seed_id>.json` is one file per university with at least one filled question, in the topup_round2
  shape. `answers` holds only the filled questions, with the converter's key names (`ielts_overall`,
  `ielts_min_section`, `toefl_ibt`). Every figure sits in the first 600 characters of its quote.
  `core_drafts.propose_english` was run on both English drafts, and every drafted test came back `known`.
- `core/evidence_check.container-2026-10-19.json` is the container pre-check. It ran
  `scripts/verify_evidence.py <this dir> --trust-env-proxy`, and its result is **4 rows, 4 official +
  quote_found**. The file name contains `container`, so `kb_build` skips it.
- `programme/` is empty because no programme pages were re-researched. Its evidence check is `[]`.

The CI check is still needed: `benchmark-capture.yml`, `mode=verify_evidence`,
`extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_round3`. Save its report as
`topup_round3/evidence_check.ci-<date>.json`. Until that report exists, these answers stay unknown.

**Merge note (IP Paris).** `kb_build` merges `scholarship_exists` as a whole question. Once this draft is
verified, its Olympiad award replaces the base Excellence Scholarship fact, and the Excellence Scholarship
details move to the draft's notes. The Olympiad award was chosen because it is the one award on the page
whose eligibility for non-EU/EEA students is stated.

## Results

| seed_id | university | gap | result |
|---|---|---|---|
| qs2027-029 | ANU | english | **filled**: IELTS 6.5, with 6.0 in each band. Source: the ANU policy ANUP_000408, Table 2 (undergraduate). policies.anu.edu.au now answers 200; in round 1 it went through an SSO redirect. TOEFL is still unknown: the 2027 figure (81; R16 W19 L16 S19) is split into separate digits ("8 1") in the page's text layer. |
| qs2027-071 | Lund | english | **filled**: English 6 = IELTS 6.5 with no section below 5.5, or TOEFL 90 (university-wide entry-requirements page). This is a floor: the CS bachelor is Swedish-taught, so Swedish (Svenska 3) is also required, and a programme may set a higher English level. |
| qs2027-044 | IP Paris | scholarship_international | **filled**: Full Scholarship Scheme for International Olympiad Medalists. The page caps it at "87,900 Euros per non-EU/EEA student", so international = true. The need-based tuition-fee waiver is also open to "international … students". |
| qs2027-010 | NUS | english | still unknown (access): nus.edu.sg/oam still serves an empty Incapsula body (HTTP 200, 0 characters). |
| qs2027-015 | UPenn | english | still unknown: no minimum is published, only "competitive" ranges (re-checked in round 2). |
| qs2027-017 | Yale | english | still unknown: no minimum is published, only "most competitive" benchmarks. |
| qs2027-027 | Princeton | english | still unknown: a test is required, but no score threshold is stated. |
| qs2027-042 | Yonsei | english | still unknown: the 2027 guide accepts Korean or English proof with no score stated. |
| qs2027-045 | Northwestern | english | still unknown: no minimum score is published. |
| qs2027-049 | UCLA | english | still unknown: the page gives "competitive" scores only. |
| qs2027-052 | CityU | english, scholarship_international | still unknown (access): every www.cityu.edu.hk and cityu.edu.hk page tried, including /sds/ and /international/ as well as /admo/, returns an empty Incapsula body. The department page (cs.cityu.edu.hk) states no residency condition for its entrance grants and points to the blocked General Entrance Requirements. |
| qs2027-053 | Korea University | english | still unknown: the programme is Korean-taught. English (TOEFL iBT / IELTS) is one alternative route, and the guide states no minimum score. |
| qs2027-054 | NTU | english | still unknown: the 2027 guidelines PDF sets English-taught programmes at CEFR B2 and Chinese-taught programmes at Chinese CEFR A2. No official page stating CSIE's teaching language was found, and www.csie.ntu.edu.tw robots.txt is unreachable (ConnectError), which counts as disallowed. |
| qs2027-065 | KAIST | english | still unknown (access): admission.kaist.ac.kr robots.txt is unreachable (ConnectError), which counts as disallowed. |
| qs2027-074 | UIUC | english | still unknown: the first-year page lists the accepted tests with no minimum, and "This requirement cannot be waived". Published minimums are for transfer applicants only. |
| qs2027-095 | Osaka | english | still unknown: the programme is Japanese-taught. The osaka-u.ac.jp TOEFL threshold notices read cover Medicine, Foreign Studies, Science and Human Sciences, not Engineering Science. The 2027 guideline is encrypted. |
| qs2027-072 | UT Austin | scholarship_international | still unknown: admissions.utexas.edu/apply/international-students names no scholarship. The International Education Fee Scholarship pages found (undergradcollege, global.utexas.edu/isss) return 404, and that is a different award in any case. |
