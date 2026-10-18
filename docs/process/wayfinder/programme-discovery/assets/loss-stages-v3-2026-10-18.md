# Where the programme page is lost after v3 R1 / R5 / TB-1 — development sets only

Read-only analysis, 2026-10-18, claude-opus-5. No repo edit. Heldout nine never opened.

## 0. Evidence and a discrepancy to settle first

Captures read (all under `scratchpad/runs/<run>/x/<case>-<arm>/<ts>/`):

| run | pipeline | flags on top of the tree's defaults | used for |
|---|---|---|---|
| `r5-{cohort,dev2,dev3,dev4}` ON arm | `5f401c4` | `--local-language-queries` (R5); TB-1 off; **R2 off** | the per-case loss stage asked for |
| `tb1-{…}` both arms | `7f50e1c`-era | `--case-time-budget` (TB-1); R5 off | killed-case comparison (unsw, ubc) |
| `r2b-{…}` ON arm | `3df3e62` | `--subject-title-shapes` (R2 + R2b); R5 already default | what is *already* fixed |

**HEAD `4e7ec14` turns R2 (`SUBJECT_TITLE_SHAPES`, with R2b) on by default** ("dev3 4 → 6-7 (imperial, uio,
unsw), dev4 1 → 2-3 (kit), 0 losses"; runs 39129349634/351411/352826/354412 = `runs/r2b-*`). The brief for this
analysis lists R2 as off; the tree says on. Every statement below is given for the r5 ON arm as asked, and then
"at HEAD" = the r2b ON arm.

Gold: `ground_truth.reviewed10.json`, `dev2.draft1.json`, `dev3.draft1.json`, `dev4.draft1.json` (vut, taltech,
boun, itu related-only → `unadjudicated`, not counted). Scorer: `gold_seen` stages per WF-17.

Programme-page recall, ON arms: r5 — cohort 5/10, dev2 5/6, dev3 4/11, dev4 1/5 · r2b — cohort 5/10, dev2 5/6,
dev3 6-7/11, dev4 2-3/5.

## 1. Loss stage per development case not found on the r5 ON arm (17 cases)

Legend for "fix": **access** (not fixable; DoD "unavailable"), **rule**, **label** (gold should list another URL),
**ordering** (rank/slot — returned, not read).

| case (set) | r5 ON outcome, both reps | exact loss stage | evidence (r5 ON) | at HEAD (r2b ON) | fix |
|---|---|---|---|---|---|
| **aalto** (cohort) | missed | **blocked site**: robots.txt `ReadTimeout` → RFC 9309 fail-closed; 19/20 reads refused | gold returned rank 1 `field_and_degree`, rank 4 `programmes`, rank 4 `undergraduate`; `rejected: search lead unresolved (robots_disallowed)` | same | access |
| **toronto** (cohort) | missed | **blocked site**: HTTP 403 on robots, sitemaps, homepage and every `future.utoronto.ca` lead (21-22/23 reads) | gold rank 3 `programmes`, rank 2 `undergraduate`; `unresolved (http_error)`; the two readable `utsc.utoronto.ca` pages read `unknown` / `irrelevant` | same | access |
| **kuleuven** (dev3) | missed | **blocked site**: robots.txt `ConnectTimeout` on every host (14/14) | `local_language` returned `…/SC_51016742/diploma_omschrijving` (rank 1) and `…/SC_51016742` (rank 2, the gold without `.htm`); both `unresolved (robots_disallowed)`. Scorer wrote `gold_seen=never`: `canonical_url` does not equate `SC_51016742` with `SC_51016742.htm` (M2 variant gap, see §7) | same | access (+ scorer variant) |
| **ub** (dev3) | missed | **blocked site**: `www.ub.edu` timeouts, `web.ub.edu` HTTP 403 (Cloudflare) on 7 of 8 leads; sitemap 404 | gold (`ub.edu/grad/infes/fitxaInfe.jsp?…ens=TG1148`) never returned by any of 6 families; `field_and_degree` top-3: `web.ub.edu/en/web/estudis/w/bachelordegree-g1148` (the modern page of the same Grau, 403), `…/facultat-matematiques-informatica/learn`, `…/treball-final-de-grau-enginyeria-informàtica` | same | access; gold could also list `web.ub.edu/en/web/estudis/w/bachelordegree-g1148` (same programme, newer host) |
| **hku** (cohort) | rep1 **wrong** (`cds.hku.hk/prospective-students/undergraduate-old-2026/6999-computing-and-data-science`), rep2 wrong (`www.cs.hku.hk/`) | **blocked host**: gold host `admissions.hku.hk` robots `ConnectError` → every lead there `unresolved (robots_disallowed)`; the readable department host is then confirmed | gold rank 1 `field_and_degree`, rank 1 `natural_language`; `zh-hans` twin rank 1 `local_language` | miss, nothing confirmed (R2 reads "6999 Computing and Data Science" as related: data science is a related head) | access for the gold; **label**: add the `cds.hku.hk/…/6999-computing-and-data-science` page as the same programme (owner to confirm against the gold's "BEng in Computer Science" evidence title) |
| **ubc** (cohort) | rep1 **wrong** (`you.ubc.ca/programs/computer-science-vancouver-ba`, case killed at 115 s), rep2 missed | **access-flaky + sibling confirmed**: rep2 `you.ubc.ca` robots `ConnectTimeout` → all leads unresolved; rep1 readable: BA page (rank 1 `field_and_degree`) read first and accepted, gold BSc at rank 7-8 never read | gold rank 1 in `programmes`, `courses`, `undergraduate` (pass 2 — never sent after a confirmation) | rep1 miss (timeout), rep2 wrong (BA) | access-flaky; **label**: BA = "the field's bachelor in another faculty" → `related_programme_urls`; ordering (§5 #1) would still read BA first |
| **kaist** (cohort) | missed | **listed, never read** (`walker:short_label`): the gold `cs.kaist.ac.kr/content?menu=188` is the sitemap/registry *catalogue* pick and a walker link behind a short Korean label; page text carries no programme identity (ticket 10); `admission.kaist.ac.kr` robots unreachable | 6 families, 0 gold; top results are `ftp.kaist.ac.kr/ctan/…pdf`, `sociology.kaist.ac.kr/alumni`, news, `pure.kaist.ac.kr` clippings, `cs.kaist.ac.kr/` (read: `unknown`) | same | not fixable by a small rule (opaque URL + identity-less page); fog on the map |
| **tsinghua** (dev2) | missed | **never returned**: gold is on another registrable domain (`international.join-tsinghua.edu.cn`); `site:tsinghua.edu.cn` can never return it; DI-1 off | top results `cs.tsinghua.edu.cn/csen/info/1135/3805.htm` (unknown), `tsinghua.edu.cn/en/Admissions/Undergraduate/Degree_Programs.htm` (subject 'Degree Programs' refused), `yz.tsinghua.edu.cn` (general_admissions) | same | out of scope (second registrable domain = DI-1, its own decision) |
| **puc** (dev3) | missed | **never returned** (gold `admision.uc.cl/carreras/licenciatura-en-…`) **and a department twin read but refused**: `dcc.ing.uc.cl/pregrado/licenciatura-en-ingenieria-en-ciencia-de-la-computacion` refused "page subject 'Licenciatura en Ingeniería en Ciencia de la Computación - Departamento de Ciencia de la Computación' does not match" (R2 off: the ' - Departamento…' subtitle) | 6 families, 0 gold; `local_language` (`site:uc.cl "ciencias de la computación" licenciatura`) top-3: `imc.uc.cl/investigador-uc-liderara-el-simposio…` (news), `dcc.ing.uc.cl/tag/computacion/`, `imc.uc.cl/docencia/pregrado/licenciatura-en-ingenieria-en-ciencia-de-datos/…`; `field_and_degree`: a Major PDF, a magíster page, a faculty-position post. Slow host (10 s/read): sitemap 20 s, search at 21 s, deadline at 57 s | **wrong**: dcc page confirmed both reps (R2 head = first segment → field) | **label**: dcc page = same Licenciatura on the department host → second programme URL (then hit). Gold host itself: only R4(c) (`admision.uc.cl/carreras-sitemap.xml`), rejected for cost |
| **uio** (dev3) | missed | **read but refused — subject**: "page subject 'Informatikk: programmering og systemarkitektur' does not match requested fields ['computer science']" (the `: subtitle`); sitemap stage 44-45 s of the 55 s clock (76 583 URLs, 104 kept, all medicine/law), search at 44-45 s, 3-4 recovery reads | gold rank 1 `local_language` (both reps); siblings `informatikk-robotikk`, `informatikk-ledelse` rank 2-3, same refusal | **hit** both reps (R2 head "Informatikk" → field) | fixed by R2; fragile on the clock (§5 #2); **label**: list the sibling "Informatikk: …" bachelors as related, since R2 cannot tell them apart by title |
| **imperial** (dev3) | **wrong** (`/2027/mathematics-computer-science-beng` + `/2027/entry-requirements---2027/mathematics-and-computer-science-for-ai`) | **confirmed a different page; gold listed, never read**: confirm queue from the sitemap (28 047 URLs seen, 358 kept); 7 reads in 39 s (5-6 s each): #1-2 `tuition-fees---2027/group-7---mathematics-and-computer-science/standard-courses/{home,overseas}` (refused 'Home'/'Overseas'), #3 maths-CS BEng **confirmed → stop**, #4-6 more maths-CS sub-pages, #7 earth-science; deadline 55.6 s in confirm; `search_skipped`; gold `computing-beng` at rank ~36/40 of the kept queue (ticket 08: 35/40; R2b docstring: 37/40 — the trace keeps no kept list, only a 40-row `rejected_sample`, so it cannot be re-read from captures) | **hit** both reps: maths-CS → related (R2), R2b reads `/2027/computing-beng` next | fixed by R2+R2b; remaining risks in §3 |
| **unsw** (dev3) | **wrong** (`bachelor-of-commerce-computer-science`), killed at 115 s both reps | **confirmed a different page** (Commerce/CS double degree, rank 1 `natural_language`) after the Bengaluru page was refused by CG-1; gold rank 3 `field_and_degree`, rank 2 `programmes`, never read; then the evidence stages ran the clock out | checkpoint trace only (`checkpoint: timeout`) | **hit** both reps (TB-1 on: 115 s but gold confirmed; r2b `unsw` hit; tb1 ON arm hit) | fixed by TB-1 (+ R2: "Commerce" is a business head → related) |
| **auckland** (dev3) | **wrong** (`…/computer-science/undergraduate/bsc-compsci-from-2019.html`, `…/computer-science/undergraduate.html`) | **confirmed pages the gold does not list**: both are the BSc Computer Science major's own pages ("Undergraduate study in Computer Science – University of Auckland"); gold lists the BSc degree page and the `plan?p7_code=COMP-BSc` calendar page (rank 2 `field_and_degree`, rank 4 `programmes`, never read because a page was already confirmed) | — | same (wrong) | **label**: add both pages as the same programme (ticket 03 Q3 "same-programme sibling page") |
| **kit** (dev4) | missed | **read but refused — subject**, both gold pages (EN rank 1 `field_and_degree` + `natural_language`; DE rank 1 `local_language`; DE read as the EN page's hreflang twin): "page subject 'KIT - Study programs - Informatics Bachelor of Science' does not match requested fields" — the subject is the breadcrumb `<title>`; 'informatics' is a strong alias but 'kit' and the award word 'science' are not filler | 8 recovery reads: 2 gold + `informatik.kit.edu` pages (unknown / master) + 3 hreflang twins of refused non-programme pages | **hit** both reps (R2 skips the 'KIT' and 'Study programs' segments, strips "Bachelor of Science") | discovery fixed by R2; **verify still refuses `programme.exists`** (§2) |
| **rwth** (dev4) | missed | **returned, never read**: gold EN twin `…/~bnzs/informatik-b-sc-/?lidx=1` rank 1 in `field_and_degree`, `programmes`, `courses`, `undergraduate` (rank 2 once), DE page rank 1 `local_language`; all 8 recovery reads went to `sc.informatik.rwth-aachen.de` (4 pages + their 4 hreflang twins): 6 read `unknown`, `…/en/studium/bachelor/informatik` + `/de/` refused "page subject 'Bachelor Informatik – Studiencenter Informatik' does not match" (R2 off); slow host (3.4 s/read), deadline 56 s | the department pages outrank the central page in `rank_candidates`: 'informatik' twice in host+path and 'bachelor' in the URL (+2.0 `degree_in_title`), vs the gold's `b-sc` (tokenised away) and a long CMS path | **wrong**: `sc.informatik…/en/studium/bachelor/informatik` confirmed both reps (R2 head "Bachelor Informatik" → field) | **label**: the Studiencenter page = same B.Sc. Informatik on the department host → second URL (then hit); **ordering** rule (§5 #1) reads the rank-1 central EN page first, whose title "Computer Science B.Sc. \| RWTH Aachen University \| EN" already passes |
| **ctu** (dev4) | rep1 missed, rep2 **wrong** (`intranet.fel.cvut.cz/en/education/bk/obory/obor1014257275005.B.B.P.…` = "Bachelor programme - Artificial Intelligence and Computer Science - CTU FEE") | **returned, not read** (rank 5 `local_language`, both reps); pass-1 reads went to `bilakniha.cvut.cz` study-plan/course pages and `fel.cvut.cz/…/eecs-electrical-engineering-and-computer-science` (unknown); crawl-delay 10 s host, sitemap 404 ×3 (22 s), deadline in navigation at 60 s | gold title 'Bakalářský studijní program Informatika - FIT ČVUT' would have been refused with R2 off ('cvut' is not filler); 'bakalarske-studium' / 'studijni-programy' earn no `degree_in_title` / `catalogue_path` (English-only lists) | rep1 miss (gold still rank 5, unread), rep2 **hit** (gold read 4th, accepted) | **ordering** (§5 #1); the FEL AI&CS page becomes related under R2 |
| **unibo** (dev4) | **wrong** (`corsi.unibo.it/1cycle/ComputerScienceEngineering`) | **confirmed a different page**: rank 1 `field_and_degree`, read 2nd, accepted (own words "computer science" in the title; 19-Q4 makes "Computer Science and Engineering" the field) → stop; gold `laurea/informatica` rank 1 `local_language` and `1cycle/ComputerScience` rank 2 `natural_language`, never read | sitemap `sitemap.xml.gz` unparseable (gzip not handled) | same (wrong) | genuinely different (L-8 Ingegneria informatica; its Italian twin is `laurea/IngegneriaInformatica`) → **label** as related; **ordering** (§5 #1 top-1 guarantee) reads `laurea/informatica` beside it → hit |

Also on dev3 at HEAD: **iitd** flips (r2b rep1 miss, rep2 hit): gold `homecse.iitd.ac.in/b-tech-program/` is returned only by
`natural_language` at rank 8 (and `undergraduate` rank 5 in one rep); 8 recovery reads go to `homecse.iitd.ac.in`
course pages (`col100…`, `col703…`) and a maths PDF. Same ordering mechanism as ctu.

### Split of the 17 r5 misses

- access / blocked / second domain (7): aalto, toronto, kuleuven, ub, hku (gold host), ubc (flaky), tsinghua.
- fixed at HEAD by R2/R2b/TB-1 (4): kit, uio, imperial, unsw.
- confirmed a page the gold does not list, same programme (3 + hku's twin): auckland, puc (dcc), rwth (sc.informatik).
- returned, not read — ordering (2, + iitd flake): ctu, unibo (unibo also a label question).
- opaque URL / identity-less page (1): kaist.

## 2. What remains for KIT

Discovery: fixed. R2's `subject_head` gives way past "KIT" (no word > 3 letters) and "Study programs" (filler) to
"Informatics Bachelor of Science"; `_without_award` removes "Bachelor of Science"; verdict `field` for both the EN and
DE titles (verified offline; r2b ON: hit in both reps, `programme_urls=[…/english/vorstudium/bachelor-informatics.php]`).

Verify: **`programme.exists` is still not claimed** (r2b kit: 1 claim, `intake.open` only; labels 0/1). Cause, reproduced
offline from `app.adapters.matching.program_matches`:

- the discovered programme is named by `_program_name_from_url` (live_discovery.py L5270), which strips only
  `.html` → name **`"Bachelor Informatics.Php"`** (the raw claim shows `"program": "Bachelor Informatics.Php"`);
- `wanted = content_tokens(name) | content_tokens("computer science") = {informatics, php, computer, science}`;
  `found = {kit, programs, informatics, science}`; overlap `{informatics, science}` = 2/4 = **0.5 < 0.6** → "does not
  match the requested 'Bachelor Informatics.Php' (shared: ['informatics', 'science'])". With the extension stripped
  the same call gives 2/3 = 0.67 → True — by the luck of the award word "science";
- `_named_after_its_url` is also False for the same reason (`.php` survives), so the `matches_field_text(page.subject,
  [field])` guard that would reuse R2's verdict is skipped.

Fix (two parts, both verify-side, no discovery change): (a) strip any extension (`php|aspx?|jsp|cfm|html?`) in
`_program_name_from_url` and `_named_after_its_url`; (b) make `program_matches` alias-aware — `wanted` is the token set of
the applicant's field **or of any strong / localized alias of it** (ontology), so "Informatics" / "Informatik" /
"Informatika" cover the field without borrowing "science" from an award name. Expected: kit `programme.exists` +1; the
same silent loss waits on every `.php`/`.aspx`/`.jsp` host (common in the heldout countries).

## 3. What remains for Imperial

At HEAD Imperial is a hit (R2: maths-CS → related; R2b `_queue_field_sibling` → `/2027/computing-beng` read next;
r2b both reps `programme_urls=[…/2027/computing-beng]`, `related=[…mathematics-computer…]`). What is still fragile:

1. **The confirm queue is polluted by fee / entry-requirement sub-pages.** `categorise_url` scores
   `…/2027/tuition-fees---2027/group-7---mathematics-and-computer-science/standard-courses/home` as `program_page` **11**
   (field 16 + degree 4, 'courses' structural) and the two `entry-requirements---2027/…` pages **7** — equal to or above
   `computing-beng`'s 7 — because `_is_fee_path` (True for these) is consulted only under `FIELD_SLUG_SCORING` and R3's
   evidence-sum path, not in `score_url`. Four of the first seven confirm reads (≈22 s on a 5-6 s/read host) are such
   pages; the related verdict that triggers R2b arrives at read 3 (~34 s) and the sibling read at ~40 s, inside a 55 s
   deadline. A slower day loses the page again.
2. **Search never runs for Imperial** (`stage_order … search_skipped`; the two queries at 64-67 s are evidence-stage):
   confirm consumes the clock, so the sitemap queue is the only route and `computing-beng`'s rank in it decides.
3. **The kept queue is not in the trace**: `selected` holds only the confirmed pages and `rejected_sample` 40 rows, so
   "rank 36/40" cannot be re-verified from any capture; record `selected_before_confirm` (the 40 kept per category)
   at the confirm checkpoint.
4. The gold already lists both `/computing-beng/` and `/2027/computing-beng`; M2's canonical-variant rule covers them.

## 4. Department-site twins (rwth sc.informatik, puc dcc.ing.uc.cl)

Both are the *same programme* published on the department's host and are now accepted by the predicate (R2 heads
"Bachelor Informatik", "Licenciatura en Ingeniería en Ciencia de la Computación" → field), so at HEAD they score
**wrong** in both reps of both cases. They are not hreflang twins, so M1's twin recording cannot see them, and no safe
rule makes "same title on another host of the institution" a hit (it would also accept Bologna's CSE-type pages). The
honest route is ticket 03 Q3 ("same-programme sibling page" = found): add
`https://sc.informatik.rwth-aachen.de/en/studium/bachelor/informatik` (+ `/de/…`) and
`https://dcc.ing.uc.cl/pregrado/licenciatura-en-ingenieria-en-ciencia-de-la-computacion` as second programme URLs.
Effect: rwth and puc become hits on the existing r2b captures (dev4 2-3/5 → 3-4/5; dev3 6-7 → 7-8). For rwth the
central page is additionally reachable by ordering (§5 #1): its EN twin is rank 1 in four families and its title
"Computer Science B.Sc. | RWTH Aachen University | EN" passes today; its DE title "Informatik B.Sc. | RWTH Aachen
University | DE" does **not** (the pipe is not a subtitle mark in R2, and 'rwth', 'aachen', 'university' are not filler).

## 5. Next three changes, ranked by expected programme pages gained (all four sets, on top of HEAD)

### #1 Retrieval rank v2 — `RETRIEVAL_RANK_V2` (harness `--retrieval-rank-v2`), `retrieval.py` + `live_discovery.py`
Three parts, one flag:
(a) **family consensus**: `rank_candidates` already receives `found_by` (families per URL; the prefilter docstring
promises "V2-16 will want it") but ignores it; add `+1.0` per additional family that returned the URL (cap +3).
(b) **local URL signals**: `degree_in_title` and `catalogue_path` test English words only (`bachelor`, `bsc`, …;
`_CATALOGUE_PATH`); when R5's `local_language_terms` is active, the language's bachelor words
(`_LOCALIZED_DEGREE_FILLER`: `bakalarske`, `laurea`, `licenciatura`, `bakalauro`, `lisans`, …) and the local listing
roots already written for R4 (`_LOCAL_CATALOGUE_ROOT`: `/studijni-programy/`, `/studier/program/`, `/carreras/`,
`/formation/`, `studiengaenge`, …) count the same way. (c) **pass-1 top-1 read guarantee**: before the first
confirmation stops recovery (`added and not multi_requested → break`), the rank-1 result of each pass-1 family that
survived the prefilter is read, inside `MAX_PROGRAM_CANDIDATES_CHECKED` (≤ 2 extra reads per case).
Cases: **rwth** (central EN page rank 1 in 4 families → read first, accepted today: +1 dev4 without any label),
**ctu** (gold rank 5 `local_language` only; (b) adds +3.5 → read in both reps instead of one: stable +1 dev4),
**unibo** (gold rank 1 `local_language`; (c) reads it beside the CSE page → hit: +1 dev4), **iitd** stability
(rank 8 `natural_language`; (a)+(c) help only if another family returns it). Expected +3 stable pages, all dev4.
Precision risk: (c) can return two confirmed pages per case (more claims, two scopes); (a) promotes hub pages every
family returns (department homepages) — `profile_rejects` still decides, cost is a read; (b) can promote local
*master* pages unless `names_other_degree_level` knows the local master slugs (R5 planned it; check `magistrale`,
`navazující`, `magistr`, `yüksek lisans`). Bar: +1 on dev4 in both reps, reads per case not above today's, 0 new wrong
claims, `cases_over_budget` 0.

### #2 Read economy in confirm/recovery — `LOCAL_TWIN_ON_IDENTITY_REFUSAL` + `FEE_SUBPAGE_EXCLUSION`
(a) `_recover_search_pages` and `_queue_english_alternate` read the hreflang twin of **every** refused page; a page
refused for its *kind* ("reads as unknown / navigation / country_credential_requirements") has a twin of the same kind.
Read the twin only on a subject or level refusal. r5 evidence: kit 3 of 8 recovery reads were twins of non-programme
pages, rwth 3-4 of 8, puc 1, ctu 1 — on rwth those freed checks reach the rank-1 central page in pass 1. (b) consult
`_is_fee_path` and an entry-requirements segment (`entry-requirements---\d{4}`, `standard-requirement`) in
`score_url` for `program_page`, not only under R3/`FIELD_SLUG_SCORING`: Imperial's four fee/entry sub-pages leave
the queue (22 s of its 55 s). Cases: rwth (ordering, with #1), imperial (first-pass robustness, −4 reads), kit/puc/ctu
(−1 to −3 reads each). Expected +0-1 page (rwth without labels), −3 to −4 reads on four cases; precision risk none
(fewer reads, same predicate). Bar: identical or better pages, reads strictly down on kit/rwth/imperial.

### #3 Verify-side identity — `PROGRAMME_NAME_EXTENSION` (bug fix, no flag) + `ALIAS_AWARE_PROGRAM_MATCH`
As in §2: strip URL extensions in `_program_name_from_url` / `_named_after_its_url`; `program_matches` accepts a page
whose subject tokens cover the field **or one of its strong/localized aliases**, and reuses discovery's R2 verdict
through `matches_field_text` when the name is a URL placeholder. Cases: **kit** (`programme.exists` +1 label; the page
is already a hit), every `.php`/`.aspx`/`.jsp` host later. Expected programme pages gained: **0** — it converts a found
page into claims (DoD target 4), which is why it ranks third; if only pages count, the alternative #3 is **title filler
v2** (`TITLE_INSTITUTION_FILLER`: `|` as a subtitle mark in `subject_head`, the seed row's institution name words and
host label as filler) — rwth's DE title and the "Programme | Level | Institution" shape (ktu, taltech, vut) — expected
+0-1 on the development sets, more in the heldout countries' title conventions. Precision risk of alias-aware matching:
an alias that is a whole word in a related title ("Business Informatics") must still be refused — route through the
same `matches_field_text` filler rule, never a bare token test.

Not ranked, already decided: R4 (rejected: cost), R3 (rejected: psaclay loss), DI-1 (tsinghua; its own decision), any
access bypass.

## 6. The "wrong" programme pages: same programme vs genuinely different

**Same programme — the gold should list the page as a second programme URL (scored hit):**

| case | page confirmed | why it is the same programme |
|---|---|---|
| rwth | `sc.informatik.rwth-aachen.de/en/studium/bachelor/informatik` (+ `/de/`) | "Bachelor Informatik – Studiencenter Informatik": the department's page of the one B.Sc. Informatik (gold = central CMS page) |
| puc | `dcc.ing.uc.cl/pregrado/licenciatura-en-ingenieria-en-ciencia-de-la-computacion` | same title as the gold Licenciatura, department host (gold = `admision.uc.cl/carreras/…`) |
| auckland | `…/find-a-study-option/computer-science/undergraduate/bsc-compsci-from-2019.html`, `…/computer-science/undergraduate.html` | "Undergraduate study in Computer Science": the BSc CS major's own pages; gold = BSc degree page + calendar plan `COMP-BSc` |
| hku | `cds.hku.hk/prospective-students/undergraduate-old-2026/6999-computing-and-data-science` | same code/slug (6999 Computing and Data Science) on the School's host; gold host refuses robots. **Owner to confirm**: the gold's evidence title is "Bachelor of Engineering in Computer Science"; if 6999 is the School-wide entry rather than the BEng, it is related, not the page |
| ub (never confirmed) | `web.ub.edu/en/web/estudis/w/bachelordegree-g1148` (403) | the current page of the same Grau G1148 (gold is the legacy `fitxaInfe.jsp?…ens=TG1148`); worth listing so a future readable run can score |
| imperial | `/2027/computing-beng` ↔ `/computing-beng/` | already both in gold (canonical variant) |

**Genuinely different — should be `related` (gold `related_programme_urls`), not a hit, so they stop counting as wrong:**

| case | page | what it is |
|---|---|---|
| unibo | `corsi.unibo.it/1cycle/ComputerScienceEngineering` | Ingegneria informatica (L-8, computer engineering; Italian twin `laurea/IngegneriaInformatica`); accepted only because 19-Q4 makes "Computer Science and Engineering" the field |
| ubc | `you.ubc.ca/programs/computer-science-vancouver-ba` | BA in Computer Science (Faculty of Arts); gold is the BSc — "the field's bachelor in another faculty" |
| ctu (r5 rep2) | `intranet.fel.cvut.cz/…/obor1014257275005.B.B.P.…` | FEL's "Artificial Intelligence and Computer Science" bachelor branch (Open Informatics); R2 now refuses it as related |
| imperial (r5) | `/2027/mathematics-computer-science-beng` | joint honours; R2 records it related. `/2027/entry-requirements---2027/mathematics-and-computer-science-for-ai` is not a programme page at all (entry-requirements sub-page) — wrong by any rule; §5 #2(b) removes it |
| unsw (r5) | `bachelor-of-commerce-computer-science` | Commerce / Computer Science double degree; business head → related under R2; fixed by TB-1 (gold now confirmed) |
| uio (r2 run, pre-R5) | `informatikk-ledelse` ('Informatikk: digital økonomi og ledelse') | sibling "Informatikk: …" bachelor; R2's head rule cannot separate the UiO siblings — list `informatikk-robotikk`, `-ledelse`, `-sprak…`, `-design…` as related |
| hku (r5 rep2) | `www.cs.hku.hk/` | department homepage — wrong, not related |

## 7. Measurement notes found on the way

- `canonical_url` does not equate `…/SC_51016742` with `…/SC_51016742.htm` (kuleuven `gold_seen=never` while the
  `.htm`-less gold sat at `local_language` rank 2); M2's variant list has `index.html`, not a bare `.htm` suffix.
- The confirm checkpoint records no kept queue (`selected` is overwritten by the confirmed pages; `rejected_sample`
  is 40 rows); Imperial's "rank 36/40" and every "returned, not read" rank inside the sitemap stage are unverifiable
  from captures. Record `selected_before_confirm`.
- Killed cases (unsw, ubc r5) keep only the checkpoint trace (`checkpoint: timeout`), nested under `discovery_trace`;
  the scorer reads it, the dump tooling must too.
- Bologna's `sitemap.xml.gz` is declared and refused as `application/octet-stream` (gzip sitemaps are not parsed) —
  a sitemap-reader gap, not a discovery rule.

## Sources

Captures: `scratchpad/runs/{r5,tb1,r2b}-{cohort,dev2,dev3,dev4}/x/<case>-<arm>/<ts>/<case>.{json,raw.json,trace.json,log}`,
`sc.{md,json}`. Dumps: `scratchpad/loss_tools/dump_case.py`, `scratchpad/loss_tools/out/*.txt`.
Code: `backend/app/adapters/discovery/live_discovery.py` (`profile_rejects` L2460-2480, `matches_field_text` L1531,
`subject_head` L1681, `_queue_field_sibling` L1857, `_recover_search_pages` L4628, `_add_search_results` QB-1 passes
L4340-4440, `categorise_url`/`matches_field` L2500ff, `_program_name_from_url` L5270, `SUBJECT_TITLE_SHAPES` L383),
`backend/app/adapters/search/retrieval.py` (`SIGNAL_WEIGHTS` L79, `rank_candidates` L214), `prefilter.py`, `intent.py`
(`queries_for`, `local_language_terms`), `backend/app/adapters/matching.py` (`program_matches`),
`backend/app/adapters/requirements/web_requirements.py` (`_claim_program_exists`, `_named_after_its_url`),
`backend/evaluation/research/{scorecard,metrics}.py`. Prior: tickets 03, 08, 10, 11, 14, 17; LOOP_REPORT cycles 4c-v3;
commits `3df3e62`, `4e7ec14`.
