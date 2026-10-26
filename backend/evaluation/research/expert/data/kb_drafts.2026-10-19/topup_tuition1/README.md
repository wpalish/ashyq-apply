# KB tuition re-drafts, round 1 (CS bachelor, 2026-10-19)

A tuition-only top-up of the merged knowledge base (`app.knowledge.load_knowledge_base()`:
`kb_cs_bachelor.json` and `kb_imported_dev.json`, 98 universities), for the row of
`docs/process/NEXT_CYCLES_2026-10-19.md` §3: "UK and IE 2027-entry fees are mostly published → re-draft that
subset now; the 4 past now". Researched 2026-10-19 with live search frozen: web search was used only to find
official URLs. Every page was read with the production `Fetcher`: the `ASHYQApplyBot` user agent, robots.txt
honoured, through the sandbox HTTPS proxy, with TLS verified. There was no user-agent spoofing, no WAF bypass
and no robots override. No heldout university was opened.

## Selection

- **UK and Ireland.** The merged KB has **no stale UK/IE tuition fact**: the stale list (48) holds none of the
  17 UK/IE rows. The UK/IE tuition gaps are of two other kinds, and both were taken:
  - **unknown** (7): Oxford, UCL, Edinburgh, King's, Birmingham, Sheffield, Durham;
  - **known without period or academic year** (2): Imperial and Trinity College Dublin. Both facts come from
    `kb_imported_dev.json` with `period: null` and `academic_year: null`, so they never enter the yearly
    cost table although the quote is a 2027 fee.

  Cambridge, Manchester, Bristol, LSE, Warwick, Leeds, Glasgow and Nottingham already hold a current
  2027/28 fee and were not touched.
- **The 4 past fees:** Toronto (2025/26), Universiti Malaya (2025/26), Paris-Saclay (2025/26) and Institute of
  Science Tokyo (bachelor rate "entering on or after 1 April 2019").

## Files

- `core/<seed_id>.json`: one file per university **with a filled tuition answer**, in the `topup_round2`
  shape (`questions_researched: ["tuition"]`, `answers` holds only `tuition`). The amount, the currency mark
  and the academic year sit in the first 600 characters of every quote.
- `core/evidence_check.container-2026-10-19.json`: the container pre-check,
  `scripts/verify_evidence.py --trust-env-proxy topup_tuition1/core`. Result: **4 tuition rows, 4 official +
  quote_found** (the other 20 rows are the unresearched questions, `unknown`, no URL). The file name contains
  `container`, so `kb_build` skips it. The CI check (`benchmark-capture.yml`, `mode=verify_evidence`,
  `extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_tuition1`) is still needed; keep its
  report at `topup_tuition1/evidence_check.ci-<date>.json`. Until then these answers stay unknown.
- `programme/`: programme pages were not re-researched; the evidence check there is `[]`.

**Build note.** Imperial's and TCD's current tuition facts come from `kb_imported_dev.json`, not from a
`batch*` core draft. Check after the rebuild that the new fact (with `period: year` and `academic_year`)
replaces the imported one rather than standing beside it.

## Results

| seed_id | university | gap | result |
|---|---|---|---|
| qs2027-002 | Imperial College London | known, no period/year (imported) | **filled**: GBP 47,800 per year, 2027 entry, Overseas fee (Computing BEng course page) |
| qs2027-075 | Trinity College Dublin | known, no period/year (imported) | **filled**: EUR 30,450, 2027/28, Non-EU Student Total Fee - Year 1 (fee schedule; 2026/27 was €29,570) |
| qs2027-032 | University of Toronto | past (2025/26) | **filled, 2027/28 planned**: CAD 68,750, 2027 cohort Computer Science (first year), Table D2 of the 2026-27 Tuition Fee Report, column "2027-28 INFO": "currently planned fees for 2027-28 for information only … subject to change". Approved 2026-27 first-year fee: CAD 66,110. The registrar's college schedules still stop at 2025-26 |
| qs2027-076 | Université Paris-Saclay | past (2025/26) | **filled, 2026/27**: EUR 178 per year, Licence national rate (non-EU differentiated fees partially exempted down to it, CA-2026-013). French page; the English page still says "2026-2027 fees coming soon". Still stale for a 2027 intake (2027/28 not published) |
| qs2027-056 | Universiti Malaya | past (2025/26) | still past: the programme page (updated 16 Oct 2026) still shows "International RM 89,200" with no session, and the latest international fee sheet on study.um.edu.my is "Updated 22 Oct 2025", academic session 2025/2026. No 2026/27 or 2027/28 UG international sheet found |
| qs2027-097 | Institute of Science Tokyo | past ("2019" entry rule) | still past: the tuition page is unchanged (学士課程 2019年4月1日以降 授業料 635,400). The 令和9 (2027) 理工学系 privately-financed international students' guideline (r9-guidelines-shihi, published 2026-10-19) is a PDF with no extractable text for the production PDF reader. The 医歯学系 2027 guideline prints tuition as "授業料（2026年度実績）", i.e. the 2027 fee is not fixed yet. This is a standing-policy fee (Q7) |
| qs2027-004 | University of Oxford | unknown | still unknown: www.ox.ac.uk answers HTTP 403 to the production user agent (re-checked) |
| qs2027-009 | UCL | unknown | still unknown: www.ucl.ac.uk answers HTTP 403 (re-checked) |
| qs2027-085 | Durham University | unknown | still unknown: www.durham.ac.uk answers HTTP 403 (re-checked) |
| qs2027-035 | University of Edinburgh | unknown | still unknown: registryservices.ed.ac.uk "Full-time fees for new students 2027-2028" renders the fee table client-side (1,179 readable characters, no amount; no amount in the served HTML) |
| qs2027-037 | King's College London | unknown | still unknown: the course page and its `/fees` subpage (397 characters) render the fee block client-side |
| qs2027-069 | University of Birmingham | unknown | still unknown: the course page's readable text has no international figure (it sits in embedded data only); the UG tuition page refers internationals to /study/international/fees, which links back without a figure |
| qs2027-083 | University of Sheffield | unknown | still unknown: the overseas-fees page gives only the 2027/28 range "between £27,650 and £34,670"; its fee look-up tool (ssd.dept.shef.ac.uk → tools.sheffield.ac.uk) is a cross-site redirect and tools.sheffield.ac.uk's robots.txt is unreachable (treated as disallowed) |
