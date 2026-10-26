# Label proposals — unadjudicated programme pages, 2026-10-18

Proposals only. **No gold file is edited**: `dev2.draft1.json`, `dev3.draft1.json` and `dev4.draft1.json`
stay as they are until the owner signs a row below.

- Input: clean baseline 2 (`base2-dev2`, `base2-dev3`, `base2-dev4`; paired `off`/`on`, two repetitions
  each, pipeline `593bd29`). Picked URLs come from each repetition's `capture.json`
  (`programme_urls`, `related_programme_urls`).
- Pages read on 2026-10-18 from official domains only, plain `curl` (default user agent, no spoofing),
  robots.txt read first for every host. One host disallows everything (`oiasystem.ntu.edu.tw`, see ntutw).
  `tec.mx` began returning 403 to every request (robots.txt as well) after the first read; it was not
  retried.
- Evidence check: each proposed URL and quote is written as an expert draft in
  `backend/evaluation/research/expert/data/programme_drafts_labelprop.2026-10-18/` (13 files, same shape
  as `programme_drafts_dev4.2026-10-18`). `verify_evidence.py` cannot reach the internet from this
  sandbox: it reports `robots_disallowed (robots.txt unreachable, ConnectError)` for every URL. As a stand-in, the
  script's own matching (`readable_text`, `is_official`, `quote_in` / `title_in`) was run on the pages
  saved with `curl`, and **all 13 quotes matched on official hosts**. Before signing, run the real check:
  `benchmark-capture.yml`, `mode=verify_evidence`,
  `extra_args=evaluation/research/expert/data/programme_drafts_labelprop.2026-10-18`. A quote that fails
  that run stays `unknown`.
- Verdicts: **(a)** the programme page, **(b)** a related programme (ticket 03 Q3: sibling, major page,
  the field's bachelor in another faculty), **(c)** wrong.

## Why these twelve cases read "unadjudicated"

`adjudicate_programme_pages` returns `unadjudicated` whenever `programme_status == "unknown"`. Each of the
twelve cases has an `unknown` programme. Several of them did not pick any page at all, so the
pipeline did not "pick a page the gold cannot judge" in every case:

| case | picked a page in | status in gold | why unknown |
|---|---|---|---|
| tec, kaznu, uct, khalifa (dev2) | kaznu 4/4, uct 4/4, khalifa 4/4, tec 0/4 | unknown | expert programme page "не проверено" (not verified) in SIGN_DEV2 |
| utokyo, ntutw, msu, usp (dev3) | usp 4/4, ntutw 1/4, utokyo 0/4, msu 0/4 | unknown | expert programme page not verified in SIGN_DEV3 |
| vut, taltech, boun, itu (dev4) | taltech 4/4, others 0/4 | unknown + `related_programme_urls` | owner decision 2026-10-18: closest equivalent is related |

### The dev4 puzzle: a scorer bug, plus one data gap

1. **Scorer bug (fixed in this commit).** Commit `f5ee82c` moved the four dev4 pages from `programme_urls` to
   `related_programme_urls` and set `programme_status` to `unknown`, because no exact CS programme
   exists. `adjudicate_programme_pages` checked `programme_status == "unknown"` before it checked
   anything else, so a labelled related page could never read `related`. The owner's intent was
   "a related page that is found is neither a hit nor an error". The fix is in
   `backend/evaluation/research/metrics.py`. An unknown case **with** labelled related pages now reads
   `related` when a labelled related page is returned or recorded. It reads `missed` when nothing at
   all was returned or recorded. Any other returned page stays `unadjudicated`, because no gold can
   call it wrong. An unknown case **without** related labels is unchanged. Precision and recall still
   leave unknown cases out, so the headline metrics do not move. Test:
   `tests/test_scorer_programme_outcomes.py::test_an_unknown_programme_with_a_labelled_related_one_is_adjudicated_against_it`.
   Re-scoring `base2-dev4` with the fix changes the outcome row from `4/0/1/0`, `3/0/0/2`, `3/0/1/1`,
   `4/0/1/0` (hit/wrong/related/missed) to `4/0/1/3`, `3/0/0/5`, `3/0/1/4`, `4/0/1/3`. vut, boun and
   itu are now `missed`: the pipeline returned no page in any repetition.
2. **Data gap (taltech).** After the fix, taltech is still `unadjudicated`, because the pipeline picked a
   *different* URL from the labelled one in all four repetitions: the IT faculty's page for the same
   IAIB curriculum, not the admissions page. The proposal is in the taltech row below.

---

## dev2

### tec — Tecnológico de Monterrey (bachelor, computer science)

| picked (off#1, off#2, on#1, on#2) | verdict | reason / evidence |
|---|---|---|
| none in all four | — | nothing to judge. Today this reads `unadjudicated`; with the gold below it reads `missed` |

Official page: <https://tec.mx/es/ingenieria-y-ciencias/ingenieria-en-tecnologias-computacionales>, title
"Ingeniería en Tecnologías Computacionales | Tecnológico de Monterrey". It declares the hreflang twin
`https://tec.mx/en/engineering-and-sciences/bs-in-computer-science-and-technology`. Quote: "Este programa
también se ofrece como B.S. in Computer Science and Technology en inglés". The EN twin returned 403 to
the second request, so it is not verified here.

**Proposed:** `programme_status: known`; `programme_urls`: the ES page, plus the EN twin once
`verify_evidence` opens it. `programme_evidence`: the quote above.

### kaznu — Al-Farabi Kazakh National University

| picked | verdict | reason / evidence |
|---|---|---|
| `https://welcome.kaznu.kz/en/education_programs/bachelor/speciality/1730` (all four) | **(a)** | the EN version of the expert's page, the same programme id. "The aim of the educational program 6B06104 – Computer Science is to prepare competitive, competent specialists" |

The expert's RU page (`…/ru/…/speciality/1730`, "Компьютерные науки 6B06104 Бакалавриат") now opens.
The HTTP 500 in the expert notes is gone. Neither page declares hreflang, so the EN page has to be
listed explicitly. Caveat: the page header reads "Admissions 2026", so it is the 2026 cycle, not
fall 2027.

**Proposed:** `programme_status: known`; `programme_urls`: RU and EN `speciality/1730`.

### uct — University of Cape Town

| picked | verdict | reason / evidence |
|---|---|---|
| `https://sit.uct.ac.za/department-computer-science` (off#1, off#2) | **(c)** | a department hub ("Department of Computer Science \| School of Information Technology") that lists every degree. It is not a programme page |
| `https://sit.uct.ac.za/ba-informatics` (on#1, on#2) | **(b)** | a BA in the Humanities faculty with a CS major: "Information Systems or Computer Science can be taken as a major along with another Humanities subject as part of a general BA/BSocSc degree" (same shape as UBC BA, labelled related) |
| recorded related: `…/bachelor-business-science-specialising-computer-science` (all four) | **(b)** | a Commerce-faculty degree with a CS specialisation. Discovery's record is right |

Official page for the BSc with a CS major: <https://sit.uct.ac.za/bsc-degrees> ("BSc degrees | School of
Information Technology"): "A BSc degree in Computer Science includes a sequence of courses that constitute
a complete undergraduate training in Computer Science". The expert's faculty page
(`uct.ac.za/…/science-undergraduate`) only lists "Computer Science" among 20+ majors. It sits one
tier lower and is not proposed.

**Proposed:** `programme_status: known`; `programme_urls`: `https://sit.uct.ac.za/bsc-degrees`;
`related_programme_urls`: `ba-informatics`, `bachelor-business-science-specialising-computer-science`.
With this gold, off reads `wrong` and on reads `related`.

### khalifa — Khalifa University

| picked | verdict | reason / evidence |
|---|---|---|
| `https://www.ku.ac.ae/program/bsc-in-computer-science` (all four; AR twin recorded by hreflang) | **(a)** | "BSc in Computer Science - Khalifa University": "The BSc in Computer Science program is concerned with the theoretical foundations of information and computation" |
| `https://www.ku.ac.ae/zmu` (off#2, on#1, as a second page) | **(b)** | "BSc in Computer Science at ZMU": the same degree delivered to Zayed Military University cadets, a different population: "By combining academic excellence with rigorous military training, ZMU upholds the highest standards to prepare cadets for future security challenges" |

**Proposed:** `programme_status: known`; `programme_urls`: `…/program/bsc-in-computer-science` and its
declared AR twin `…/ar/program/bsc-in-computer-science` (not fetched: connection reset; the hreflang
link is enough for the scorer's twin rule); `related_programme_urls`: `https://www.ku.ac.ae/zmu`.
Without the ZMU label, off#2 and on#1 would read `wrong` even though they also returned the right page.
`hit` outranks `wrong`, so this is only bookkeeping.

## dev3

### utokyo — The University of Tokyo

| picked | verdict | reason / evidence |
|---|---|---|
| none in all four | — | nothing to judge |

There is no CS bachelor that an applicant enters directly. International undergraduates apply to a
科類 (for example 理科一類) through the "外国学校卒業学生特別選考" route
(<https://www.u-tokyo.ac.jp/ja/admissions/undergraduate/e01_02_04.html>, quote "2027年度
東京大学外国学校卒業学生特別選考 募集要項"). Students reach CS (理学部 情報科学科,
<https://www.is.s.u-tokyo.ac.jp/>) only at the year-3 進学選択. The expert's page is an admissions-route page,
not a programme page. The department site is a combined undergraduate and graduate homepage.

**Proposed:** no change; keep `programme_status: unknown`. Optional, if the owner wants dev4's
"closest equivalent" rule here: `related_programme_urls: ["https://www.is.s.u-tokyo.ac.jp/"]`. Its
English quote did not match the readable text, so it needs its own quote before it goes in.

### ntutw — National Taiwan University

| picked | verdict | reason / evidence |
|---|---|---|
| `https://www.csie.ntu.edu.tw/~yvchen/about.html` (off#1 only) | **(c)** | a professor's personal page ("Vivian :: About … She earned a Ph.D. degree in the Language Technologies Institute") |
| none (off#2, on#1, on#2) | — | — |

The expert's URL on `oiasystem.ntu.edu.tw` **cannot be gold**: that host's robots.txt is
`User-agent: * / Disallow: /`, so the Fetcher may never read it. Official page on an allowed host: the
CSIE department's bachelor admissions page <https://www.csie.ntu.edu.tw/zh_tw/Admission/Announcement12>
("大學部招生 | 國立臺灣大學資訊工程學系", quote "115學年臺灣大學資訊工程系學士班簡介手冊"). It is thin: a list
of documents for the 學士班. A department or major page counts as the programme (precedent `90b45f5`).

**Proposed:** `programme_status: known`; `programme_urls`: `…/zh_tw/Admission/Announcement12`. Owner
choice: if a thin list page is not enough, keep `unknown` and record that the real page is robots-blocked.

### msu — Lomonosov Moscow State University

| picked | verdict | reason / evidence |
|---|---|---|
| none in all four | — | nothing to judge |

Official page: <https://pk.cs.msu.ru/bak_educational_programs> (VMK admissions, "Направления подготовки и
количество мест"). Quote: "01.03.02 Прикладная математика и информатика (очная форма)". The page also lists
02.03.02 Фундаментальная информатика и информационные технологии, which is the other CS-equivalent
direction at VMK, including seats for foreign citizens. Caveat: the page is for "Приём 2026".

**Proposed:** `programme_status: known`; `programme_urls`: `https://pk.cs.msu.ru/bak_educational_programs`.

### usp — Universidade de São Paulo

| picked | verdict | reason / evidence |
|---|---|---|
| `https://www.icmc.usp.br/en/admission/undergraduate/computer-science` (all four) | **(a)**, see note | "Computer Science (Bachelor's Degree)", ICMC São Carlos: "The Bachelor´s degree in Computer Science is part of the exact science area of knowledge" (100 places, 5 years) |
| recorded related: `…/applied-mathematics-and-scientific-computing` (all four) | **(b)** | a sibling programme in the same institute. Discovery's record is right |

USP has two full CS bachelors: IME São Paulo (<https://bcc.ime.usp.br/>, "Bacharelado em Ciência da
Computação – BCC – IME – USP", the expert's page) and ICMC São Carlos. The request names neither a campus
nor an institute, so both answer it with the same degree. A literal reading of ticket 03 Q3 ("the
field's bachelor in another faculty") would make ICMC related. I recommend the opposite, because it is
the same degree title at the same university and not a different degree.

**Proposed:** `programme_status: known`; `programme_urls`: `https://bcc.ime.usp.br/` and the ICMC page
(recommended). Alternative: IME only in `programme_urls`, ICMC in `related_programme_urls`.

## dev4

### vut — Brno University of Technology

| picked | verdict | reason / evidence |
|---|---|---|
| none in all four | — | the related page is labelled (`…/program/10326` + EN twin); with the scorer fix this reads `missed` |

**Proposed:** no gold change.

### taltech — Tallinn University of Technology

| picked | verdict | reason / evidence |
|---|---|---|
| `https://taltech.ee/infotehnoloogia-teaduskond/bakalaureuseope/informaatika` (all four) | **(b)** | the IT faculty's page for the **same** curriculum: "Informaatika / Informaatika ja tehisintellekt Programmijuht … Õppekava kood : IAIB". It is aimed at current students (title "Informaatika \| Bakalaureuseõpe \| Tudengile"; internship and thesis rules). The labelled page `taltech.ee/informaatika` is the admissions page: "Informaatika ja tehisintellekt (IAIB) Bakalaureuseõpe" |

This is why taltech stays `unadjudicated` after the fix: the picked URL is not a canonical variant of
the labelled one.

**Proposed:** add `https://taltech.ee/infotehnoloogia-teaduskond/bakalaureuseope/informaatika` to
`related_programme_urls`: the same programme on a faculty page, as precedent `90b45f5` does for known
cases. Caveat for the owner: the page carries no admission facts, so if the owner wants the
pipeline pushed towards the admissions page, leave it out and taltech stays `unadjudicated`.

### boun — Boğaziçi University / itu — Istanbul Technical University

| case | picked | verdict |
|---|---|---|
| boun | none in all four | — (labelled related CmpE pages; with the fix: `missed`) |
| itu | none in all four | — (labelled related CmpE pages; with the fix: `missed`) |

**Proposed:** no gold change. Neither university has a CS bachelor, only Computer Engineering (owner,
2026-10-18).

## Summary of proposed gold changes

| case | file | change |
|---|---|---|
| tec | dev2 | known; programme_urls = ES page (+ EN hreflang twin after verification) |
| kaznu | dev2 | known; programme_urls = RU + EN `speciality/1730` |
| uct | dev2 | known; programme_urls = `sit.uct.ac.za/bsc-degrees`; related = `ba-informatics`, `bachelor-business-science-specialising-computer-science` |
| khalifa | dev2 | known; programme_urls = `program/bsc-in-computer-science` (+ AR twin); related = `/zmu` |
| utokyo | dev3 | none (optional related = `is.s.u-tokyo.ac.jp`, needs a quote) |
| ntutw | dev3 | known; programme_urls = `csie.ntu.edu.tw/zh_tw/Admission/Announcement12` (the expert's oiasystem URL is robots-blocked) |
| msu | dev3 | known; programme_urls = `pk.cs.msu.ru/bak_educational_programs` |
| usp | dev3 | known; programme_urls = `bcc.ime.usp.br/` + ICMC computer-science (alternative: ICMC related) |
| vut, boun, itu | dev4 | none (scorer fix) |
| taltech | dev4 | related += faculty IAIB page |

Every `known` row also needs `programme_evidence` (the quote and URL above, `source_type: official`,
`accessed_on: 2026-10-18`). The schema refuses `known` without it.
