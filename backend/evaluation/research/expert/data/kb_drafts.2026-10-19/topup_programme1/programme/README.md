# KB top-up: the 11 missing programme pages (CS bachelor, 2026-10-19)

These are the universities in the merged KB (`app.knowledge.load_knowledge_base()`, 98 entries) whose
`programme_known` is false. The list comes from NEXT_CYCLES_2026-10-19 F5: UCL, Melbourne, Sydney, PSL,
UTokyo, IP Paris, Michigan, LSE, Lund, KTH and Alberta.

The research was done on 2026-10-19 with live search frozen. Web search was used only to find official
URLs. Every page was read with the production `Fetcher`: the normal user agent, robots.txt honoured,
through the sandbox HTTPS proxy, with TLS verified. There was no UA spoofing, no WAF bypass and no robots
override. No heldout university was opened.

Owner rulings on "related" programmes were kept as the earlier batches recorded them, with nothing
relabelled. A related draft here restates the earlier batch's page and reason, so that the decision is on
record for this pass. Related pages are never programme evidence in `kb_build` (role `related`).

## Result

| seed_id | university | outcome | page | reason |
|---|---|---|---|---|
| qs2027-009 | UCL | **page known, unreadable** | `ucl.ac.uk/study/.../courses/computer-science-bsc` (Computer Science BSc, G400) | Every www.ucl.ac.uk URL answers HTTP 403, including the department's own pages. www.cs.ucl.ac.uk has no reachable robots.txt, and wwwapps-live does not resolve. It is an access case and stays unknown unless CI can read it. |
| qs2027-023 | Melbourne | related only | `study.unimelb.edu.au/.../computing-and-software-systems/` | There is no CS bachelor, only the Computing and Software Systems major of the BSc/BDes (batch7). The study host answers 403, and the handbook returns 200 with no readable text. |
| qs2027-028 | Sydney | related only | `sydney.edu.au/.../bachelor-of-advanced-computing.html` | CS is a major inside the Bachelor of Advanced Computing (batch1). The title is verified. |
| qs2027-034 | PSL | related only | `dauphine.psl.eu/.../informatique-des-organisations` | There is no Licence Informatique, only business-informatics (batch6). Verified. |
| qs2027-039 | UTokyo | **found** (flag for owner) | `is.s.u-tokyo.ac.jp/en/about/` (+ site page `s.u-tokyo.ac.jp/en/rigakuru/is/`) | See the UTokyo note below. Both quotes verified. |
| qs2027-044 | IP Paris | related only | `programmes.polytechnique.edu/.../double-major-in-mathematics-computer-science` | The only BSc is a double major, Maths & CS, a joined shape (batch5). Verified. |
| qs2027-051 | Michigan | **found** (department-level, flag) | `teamdynamix.umich.edu/TDClient/154/Portal/KB/ArticleDet?ID=7445` | See the Michigan note below. The KB article is verified. The cse.engin page is restated and still answers 403. |
| qs2027-062 | LSE | **none** (related Data Science) | `lse.ac.uk/study-at-lse/undergraduate/bsc-data-science` | LSE offers no CS bachelor. BSc Data Science is restated as related. The full programme list could not be read as evidence, see the LSE note below. `programme_offered: false` is in the draft, for an honest "not offered" answer. |
| qs2027-071 | Lund | related only | `lu.se/studera/hogskoleingenjorsutbildning-i-datateknik-TGDAT` | A search on lu.se found no kandidatprogram in datavetenskap. TGDAT/EGSYS are related (batch4). Verified. |
| qs2027-082 | KTH | related only | `kth.se/utbildning/civilingenjor/datateknik/...-1.4116` | There is no CS bachelor. Civilingenjör Datateknik and BSc ICT are related (batch3). Verified. |
| qs2027-096 | Alberta | **page known, unreadable** | `calendar.ualberta.ca/preview_program.php?catoid=69&poid=110935` (BSc Computing Science) | robots.txt on calendar.ualberta.ca asks for a 120 s Crawl-delay, which is over the 30 s cap. www/gsa.ualberta.ca answer 403, robots.txt included. It is an access case. |

**UTokyo.** The undergraduate Department of Information Science (情報科学科, Faculty of Science) titles its
English site "Department of Computer Science, The University of Tokyo". Its curriculum "focuses on basic
courses in computer science". "Information Science" is not literally in the owner's CS list. Change the
role to `related` if the owner rules otherwise.

Entry is through the College of Arts and Sciences (Komaba), with the department chosen in year 2. The
programme is taught in Japanese, and the English-taught PEAK programme has no CS course.

**Michigan.** The article is an official U-M advising article, "Computer Science Degree in LSA versus
Engineering". It names both CS bachelor's degrees: the BS (LSA) and the BSE (Engineering). Every
CSE/admissions/LSA/bulletin page answers 403 (Cloudflare). The article is not a marketing programme page,
so drop the draft if the owner wants only programme pages.

**LSE.** The 2027 Undergraduate Guide PDF is larger than the fetcher's 5 MB cap, and
`/study-at-lse/undergraduate/programmes` returns 404.

Net effect once CI verifies this dir and the KB is rebuilt (not done here): 2 more programme pages known
(UTokyo, Michigan). There are 2 access cases (UCL, Alberta), 6 related-only (Melbourne, Sydney, PSL,
IP Paris, Lund, KTH) and 1 not offered (LSE).

## Files

- `<seed_id>.<n>-<role>.json` are the programme-page drafts in the dev5 format. The quote sits in the
  `title` slot.
- `evidence_check.container-2026-10-19.json` is the container pre-check from
  `PYTHONPATH=. .venv/bin/python scripts/verify_evidence.py <this dir> --trust-env-proxy` (production
  Fetcher, `quote_in`/`title_in`).
  - **13 rows, 9 official + quote_found.** The 4 that did not pass are UCL 403, Melbourne 403 (a related
    page), Michigan cse.engin 403 and Alberta `robots_crawl_delay`.
  - Its name contains `container`, so `kb_build` skips it. The CI check (`benchmark-capture.yml`,
    `mode=verify_evidence`, `extra_args=evaluation/research/expert/data/kb_drafts.2026-10-19/topup_programme1`)
    still has to run, and its report goes beside this dir as `evidence_check.ci-<date>.json`.
- There is no `core/` dir: this pass covered programme pages only.

The restated UCL, Michigan (cse.engin) and Alberta `local` drafts repeat the earlier batch's URL. Until CI
can read them, the entry's programme `reason` lists that URL's failure once per dir.
