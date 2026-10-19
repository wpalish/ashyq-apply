# KB gap fill, round 2 (CS bachelor, 2026-10-19)

A top-up of the merged knowledge base (`app.knowledge.load_knowledge_base()`: `kb_cs_bachelor.json` and
`kb_imported_dev.json`, 98 universities). Researched 2026-10-19 with live search frozen: web search was
used only to find official URLs. Every page was read with the production `Fetcher`: the `ASHYQApplyBot`
user agent, robots.txt honoured (including `*`/`$` patterns), through the sandbox HTTPS proxy, with TLS
verified. There was no user-agent spoofing, no WAF bypass and no robots override. No heldout university
was opened.

## Selection

The gaps came from the merged KB's `unknown` lists and stale facts, in this order of priority:

1. English unknowns that are not caused by an access block. This includes key-level ones, such as a TOEFL
   or Duolingo figure "not in the quoted excerpt", and an IELTS figure the converter could not read
   because a round-1 draft wrote it under `overall` instead of `ielts_overall`.
2. Deadlines that are unknown or stale.
3. Tuition that is stale (prior year), where a 2027/28 fee might now be published.
4. Scholarships that are unknown.

GPA was skipped. The 25 highest-value gaps were chosen across 25 distinct universities. Hosts that answered
403, or a bot challenge, to the production user agent were not picked: in this round's probe that was
ox.ac.uk, ucl.ac.uk, unimelb, monash.edu, umich, nyu.edu, ualberta, durham.ac.uk, columbia, cuhk (robots
unreachable) and cityu `/admo/` (empty challenge stub).

## Files

- `core/<seed_id>.json` is one file per university **with at least one filled question**. It uses the
  topup_imported shape:
  - `questions_researched` lists the questions this file answers;
  - `questions_already_known_not_researched` lists what the KB already had;
  - `answers` holds **only the filled questions**.

  An English answer is complete in itself: it restates the IELTS figure the KB already had, so that the
  one quote carries every number. Every number must sit in the first 600 characters, which is the
  converter's excerpt.
- `core/evidence_check.container-2026-10-19.json` is the container pre-check. It ran
  `scripts/verify_evidence.py --trust-env-proxy topup_round2`, which uses the production Fetcher with
  `quote_in`/`title_in`. Result: **16 rows, 16 official + quote_found**. The file name contains
  `container`, so `kb_build` skips it. The CI check (`benchmark-capture.yml`, `mode=verify_evidence`,
  `extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_round2`) is still needed.
- `programme/`: programme pages were not re-researched, so the evidence check there is `[]`.

**Build caution.** `kb_build.build()` keys core drafts by case, and a later batch dir *replaces* an earlier
one (`cores[case] = (draft, batch.name)`). `topup_round2` sorts after `batch*`. Built as it is today,
these partial cores would therefore replace the batch1–10 core drafts of the same seed ids and drop
their other answers. Before these files go into a build, `kb_build` needs an answer-level merge for
`topup*` cores, the way the loader already merges facts. Either that, or the files must be merged
into the batch drafts first.

## Results

| seed_id | university | gap | result |
|---|---|---|---|
| qs2027-050 | PolyU | english (IELTS unreadable: `overall` key) | **filled**: IELTS 6.0, TOEFL iBT 80 |
| qs2027-092 | Penn State | english (IELTS unreadable: `overall` key) | **filled**: IELTS 6.5, TOEFL 80, DET 120 |
| qs2027-078 | Leeds | english (no IELTS figure) | **filled**: IELTS 6.0, 5.5 per section (course page) |
| qs2027-037 | King's College London | english (Band D, no figure) | **filled**: IELTS 6.5 / 6.0 each, TOEFL 92 (Band D, 2027/28 list) |
| qs2027-094 | Boston University | english IELTS (not in quote) | **filled**: IELTS 7 ("will satisfy ... for all programs") |
| qs2027-001 | MIT | english DET (not in quote) | **filled**: DET 120 (+ IELTS 7). TOEFL is still unknown: the run is split by an embedded link block |
| qs2027-016 | Cornell | english TOEFL/DET (not in quote) | **filled**: TOEFL 100, DET 130 (+ IELTS 7.5) |
| qs2027-081 | UC San Diego | english DET (not in quote) | **filled**: TOEFL 83, DET 115 (+ IELTS 7) |
| qs2027-030 | McGill | english DET (not in quote) | **filled**: DET 125 (+ IELTS 6.5/6.0). TOEFL is still unknown (table cell) |
| qs2027-055 | Carnegie Mellon | english TOEFL (not in quote) | **filled**: TOEFL 102 (+ IELTS 7.5). DET 135 is still unknown (beyond the 600-char excerpt) |
| qs2027-019 | UNSW | scholarship unknown | **filled**: International Scientia Coursework Scholarship, international = true |
| qs2027-075 | Trinity College Dublin | scholarship unknown | **filled**: E3 Balanced Solutions scholarship (lists B.A. Computer Science; the GEUG excludes CS), non-EU only |
| qs2027-007 | Caltech | scholarship_exists (finaid 403) | **filled**: re-sourced to admissions.caltech.edu/afford; international restated |
| qs2027-068 | Warwick | deadline | still unknown: warwick.ac.uk key dates still show 14 January **2026** (2026 entry) |
| qs2027-075 | Trinity College Dublin | deadline (stale 2026-05-01) | still unknown: the non-EU page says "June 30th" with no year and still mentions "September 2025 admission" |
| qs2027-077 | UWA | deadline | still unknown: the dates table is a client-side component, not in the readable text |
| qs2027-079 | Adelaide | deadline | still unknown: the international how-to-apply page says "Check the application closing date for your chosen degree"; no date on the 2027 degree page |
| qs2027-028 | Sydney | deadline, scholarship | still unknown: the dates page prints "1 December of the year prior to commencement" (no year); the VCIS page renders client-side (815 chars) |
| qs2027-082 | KTH | deadline | still unknown: "Application deadlines for studies starting 2027 … 15 January: Last day to apply". The date line carries no year (the converter needs the year in the quote) |
| qs2027-067 | Auckland | tuition (2026), scholarship | still unknown: the BSc page shows "2026 fees" only; the International Student Excellence Scholarship is now Master's-only for 2027 |
| qs2027-056 | Universiti Malaya | tuition (2025/26), deadline, scholarship | still unknown: the latest international fee sheet is 2025/2026; the how-to-apply table is the 2026/2027 session; no UM undergraduate scholarship page for internationals found (aasd page 404) |
| qs2027-076 | Paris-Saclay | tuition (2025/26) | still unknown: the page still says "2026-2027 fees coming soon" |
| qs2027-073 | Sorbonne | scholarship, tuition | still unknown: 2026/27 national rate €178; the board's 7 July 2026 exemption policy for non-EU students is a fee exemption on request, not a scholarship; 2027/28 not published |
| qs2027-029 | ANU | english | still unknown: study.anu.edu.au names the tests without scores; the policy (policies.anu.edu.au) goes through SSO; BCOMP 2027 has no figure |
| qs2027-010 | NUS | deadline (stale) | still unknown: the SoC FAQ still lists the AY2026 window (to 23 February 2026); nus.edu.sg/oam is behind Incapsula |
| qs2027-072 | UT Austin | scholarship_international | still unknown: no admissions.utexas.edu or onestop page states international eligibility for incoming-student scholarships |

Also checked and left unchanged:

- Northwestern, UIUC, UPenn, Yale, Princeton and UCLA English: the pages publish no minimum, or give
  only "competitive" ranges.
- Glasgow TOEFL 92: the figure sits beyond the 600-character excerpt in any contiguous quote that also
  carries the IELTS line, so it was not drafted.
- IP Paris `scholarship_international`: the Excellence Scholarship section states no nationality
  condition.
- UNSW tuition: the course page is still "2026 Indicative".
- Yonsei scholarship: `ocx.yonsei.ac.kr` does not resolve.
