# Scholarship-route loss stage on the day-end replay (SR-1, 2026-10-19)

Worker W3, ticket SR-1 of `NEXT_CYCLES_2026-10-19.md` §1.4 row 1 and §4. Input: the day-end replay artifacts
`rp-base3-{cohort,dev2,dev3,dev4}` (`search_provider=recorded`, store `recorded_search.base3.json`, four columns per
set: off ×2, on ×2, `extra_args` empty), scored with
`evaluation.research.scorecard <dir> --dataset … --allow-drafts` (cohort `ground_truth.reviewed11`, dev2/3/4
`devN.draft3`). Per case: `<case>.json` (`page_outcomes`), `<case>.raw.json` (`page_diagnostics`,
`discovery_trace`), `<case>.log` (every `get` and `search`). The live base3 captures (`runs/base3-*`) were read
beside them for the one case live reached (ntu).

Development cases only. **No heldout file, capture, log or label was opened. dev5 was not opened. No search provider
was called.** To name each page's shape, 27 pages were read once each with the production `Fetcher`
(`trust_env_proxy=True`, robots.txt honoured, no override). No page is committed, because no rule was built (§3).

## 0. Answer

- **No shape covers two development sets, so no rule is built.** The 14 core scholarship labels on the eight found
  programme pages fall into seven shapes. Each shape is seen on one set only.
- One group does cross two sets: "only a query reaches the award". It takes in groningen and ntu (cohort) and ethz
  (dev2). It is not a link rule. Those pages are not linked statically from any page the run reads, so the lever is
  the award or index query on a v2 store (R1, regime C). A replay rule cannot reach them.
- The planner's per-case notes are corrected in §2:
  - taltech's award is **not** on the confirmed programme page. It is on the programme's landing twin, which the run
    never read.
  - auckland's gold is linked from the **disabilities type page**. It is not in the content of `find-a-scholarship`,
    which links it only in its sub-navigation.
  - rwth's award page **was read**. The classifier refused it.

All four columns of every set agree on every label below (missed ×4). The off and on arms differ in no funding-route
line.

## 1. The table: case → where the award evidence lives → why it was not read or extracted → shape

The trace line is quoted from the on#1 repetition. on#2 and both off repetitions carry the same line.

| set | case | labels missed (core) | gold evidence URL | where it sits relative to the pages read | exact trace line that lost it | shape |
|---|---|---|---|---|---|---|
| cohort | groningen | `scholarships.nl.exists`, `.applicability.international` | `rug.nl/education/scholarships/nl-scholarship?lang=en` | The index `/education/scholarships` was read (get #37). It links no award (its menu is not in the markup). The finder `/education/scholarships/findscholarships`, linked from `…/international-students/financial-matters`, renders its list client-side: 0 links to `nl-scholarship` in the served HTML. | `https://www.rug.nl/education/scholarships` — "read as a funding index; 0 award links, 0 queued within the award budget"; then `recorded search miss key=bec263b651d3`, `key=40f8583caaaf` (the index and award queries) | **S1** client-rendered finder |
| cohort | ntu | `scholarships.nanyang_global.exists`, `.applicability.international` (+11 non-core nanyang labels) | `ntu.edu.sg/admissions/undergraduate/scholarships/scholarship-opportunities/detail/nanyang-scholarship` | The hub `/scholarships-and-awards` was read. Its listing `scholarship-opportunities` (and two `?listingKeyword=` filters) renders client-side. No page read links the detail page. Live base3 read it (get #41) straight from the funding query's results, not from a link. | `…/scholarship-opportunities` — "not an award page; no scholarship recorded (0 award links, 0 below it: )"; `recorded search miss key=57ed45e22e3a` / `768044a93776` / `693bcf60ee08` | **S1** client-rendered listing |
| dev2 | ethz | `scholarships.eth.exists`, `.applicability.international` | `ethz.ch/students/en/studies/financial/scholarships/cost-of-living/international-students.html` (+ `…/cost-of-living.html`) | No funding page was discovered: robots and every sitemap returned `http_error`, so there are no seeds. The programme page links no funding page; its navigation is script-built (the only "Scholarship" string is a `data-most-searched-quick-links` attribute). | programme page — "read as a funding index; 0 award links, 0 queued within the award budget"; `recorded search miss key=2f686b40401c`, `4dae57158f32`, `d783550b909d` | **S2** no funding entry |
| dev2 | uba | `scholarships.beca_de_ayuda_economica.exists`, `.applicability.international` | `extension.uba.ar/noticias/beca-de-ayuda-economica-sarmiento/` (a news post, another host) | No read page links the news post. UBA's own `uba.ar/becas-grado` describes the same award ("BECAS SARMIENTO DE AYUDA ECONÓMICA", requisitos: "Nacionalidad argentina … o con residencia permanente"). The catalogue walker read it (get #9, `walker.candidates[1]`) as a programme candidate. Discovery selected no scholarships page, so the funding walk never received it. The scorer binds this award to the news URL only. | programme page (`ingresantes.exactas.uba.ar`) — "read as a funding index; 0 award links, 0 queued within the award budget" | **S3** award described on a walker page; gold on a news host |
| dev3 | auckland | `scholarships.pong.exists`, `.applicability.international` | `auckland.ac.nz/en/study/scholarships-and-awards/find-a-scholarship/pong-tams-ko-scholarship-1037-all.html` | Linked in the main content (an `h3` heading link) of `…/scholarship-types/scholarships-for-students-with-disabilities.html`, which **was read** (get #27). It was read as an index beyond the budget, so its links were not followed. The three counted index reads went to `scholarship-types`, `scholarship-eligibility` and `how-to-apply`, which link only other hubs. AP-1 read 4 of that page's 15 award sections. The Pong section's one sentence ("A Scholarship of up to $8,000 to support domestic and international students with …") has no `_ELIGIBILITY_CUE`, and a section claim would carry the index URL, which the binding does not accept. | `…/scholarships-for-students-with-disabilities.html` — "index page beyond the index budget; not followed; 4 awards read from its own sections" | **S4** hub of hubs, index budget spent on process pages |
| dev3 | unsw | `scholarships.scientia_coursework.exists`, `.applicability.international` | `www.scholarships.unsw.edu.au/scholarships/id/1988` | Linked three times ("Find out more") from `unsw.edu.au/study/how-to-apply/scholarships`, the AP-1 navigation pick. TB-1 refused that read at 110 s (a 2.2–5.0 s crawl-delay wait was still due). Had it been read, `_award_links` would still keep 0 of its links: the award sits on the sibling host `www.scholarships.unsw.edu.au`, and the same-host guard drops it. The programme page's "Explore Scholarships" link to the same host is dropped the same way. | `https://www.unsw.edu.au/study/how-to-apply/scholarships` — "blocked — case time budget (TB-1): 0.0 of 110 s left; a award read is expected to take 5.4 s (5.0 s crawl-delay wait) and must leave 0 s; not read" | **S5** time budget + sibling-host award links |
| dev4 | rwth | `scholarships.deutschlandstipendium.exists` | `rwth-aachen.de/cms/root/studium/Vor-dem-Studium/~cgfzv/Kosten-und-Finanzierung/lidx/1/`; owner-bound second source (ticket 09): `…/Stipendien-Foerderung/Bildungsfonds-Deutschlandstipendium/~goap/Bildungsfonds-Deutschlandstipendium-/` | The bound award page **was read** (get #16, an award link of the read index `Liste-von-Stipendien`). The classifier calls it `unknown`: "funding page with 0 substantive signals and no clear award name". The page is German, with the heading "Bildungsfonds (Deutschlandstipendium)". | `…/Bildungsfonds-Deutschlandstipendium-` — "not an award page; no scholarship recorded (1 award links, 0 below it: /cms/root/transfer/Spenden-und-Sponsoring/Deutschlandstipendium/…)" | **S6** local-language award page refused by the classifier |
| dev4 | taltech | `scholarships.taltech_it_faculty.exists` | `taltech.ee/informaatika` | This is the IT faculty's landing page for the programme, a twin of the confirmed `…/infotehnoloogia-teaduskond/bakalaureuseope/informaatika`. Its "Stipendiumid" block holds the gold sentence. The `local_language` family returned it at rank 1. The walker scored it `short_label`. Identity recovery checked one page (the confirmed one) and stopped. The confirmed page does not link the twin, and `en/scholarship` (read, 1 section award) does not link it either. | `discovery_trace.walker.outcomes[28]` — `{"url": "https://taltech.ee/informaatika", "outcome": "short_label"}`; "search identity recovery: checked 1, confirmed 1" | **S7** programme twin with a funding block, returned and not read |

## 2. Shapes, sets and the rule each would take

| shape | cases (sets) | measurable on replay? | the one generic rule that would reach it | guard / words | verdict |
|---|---|---|---|---|---|
| S1 client-rendered finder or listing, no static award link | groningen, ntu (cohort) | no (regime C): only a query returns the award page | none by link. The SQ-1 index query and the award query on a v2 store (R1) | — | **recorded**: one set, not a link shape |
| S2 no funding entry: no scholarships page discovered, programme page links none | ethz (dev2) | no (regime C) | discovery-side: a scholarships seed from the homepage navigation; else the same queries as S1 | — | **recorded**: one set |
| S3 award described on a page the catalogue walker read; gold is a news post on another host | uba (dev2) | the read is; the score is not (the binding is URL-exact) | hand a walker-read page whose heading names funding (`becas`, `scholarships`; `languages.json`) to the funding walk as its index when discovery selected none. The score also needs an **owner binding** of `uba.ar/becas-grado` as a second source URL (as rwth's ticket 09) | one extra read at most: the page is already in the fetch cache | **recorded**: one set + owner question Q-SR1 |
| S4 hub of hubs: the award leaf sits three levels below the hub; the index budget goes to process pages | auckland (dev3) | yes (regime A, link following) | rank index children so that a process page (SP-1's process nouns: `eligibility`, `how to apply`, `application`) comes after a population or type page. Or: follow an over-budget index's award leaves inside the existing award budget | SP-1's own noun table, no new word. reads_total must not rise elsewhere | **recorded**: one set |
| S5 funding index refused by TB-1, and its award links on a sibling host dropped by `_award_links` | unsw (dev3) | partly: the TB-1 refusal is clock-bound and the replay hits it in both reps | `_award_links` keeps a link on another host of the institution's own registrable domain (`is_official_domain`), not only the page's own host | an official-domain check that already exists, no word. The time loss is TB-1's and stays | **recorded**: one set |
| S6 local-language award page read, refused by the classifier | rwth (dev4) | yes (regime A) | the classifier's award vocabulary in the page's language (`Stipendium`, `Förderung`; their `languages.json` rows) when the heading names one award | dictionary words only. The heading must name a proper award | **recorded**: one set |
| S7 programme twin with a funding block, returned rank 1 and never read | taltech (dev4) | yes (the store holds the list) | read a returned twin's funding section (`Stipendiumid` / `Scholarships` heading) once a programme page is confirmed | one extra read. A twin by the same last slug word | **recorded**: one set |

Why no two shapes were merged into one rule:
- S1 + S2 share an outcome ("only a query reaches it"). The mechanisms differ: a client-rendered list versus a missing
  entry page. Neither is a replay rule.
- S4 + S6 share "a funding page in hand". One is a link budget and the other is a classifier vocabulary.
- A merged rule would be fitted to the cases, not to a shape. The two-set bar (13-Q2 (a)) is there to stop that.

What re-opens each shape:
- A second development set (or dev5's design-blind audit) showing the same trace line, on a page of the same shape.
- S4 and S5 are the two that a replay can measure fully. They are the first to re-open.

## 3. What was not done, and why

- **No code, flag, fixture or test.** The ticket builds a rule only for a two-set shape, and there is none.
  HANDOFF §8 is therefore unchanged. The golden demo is untouched, because no product file changed.
- **No new query.** S1 and S2 are R1's to measure. The SQ-1 index query (`scholarship_index`) and the award query are
  the requests the v2 store must hold for groningen, ntu and ethz. All three show `recorded search miss` on the funding
  stage in every column.
- The 27 page reads used for this document are not evidence for any label. They name the shapes only. Their dates are
  today's, and the live pages may differ from what the 17:29–17:35 UTC replay saw.

## 4. Owner question

| # | question | recommendation | why |
|---|---|---|---|
| Q-SR1 | uba: bind `https://uba.ar/becas-grado` ("BECAS SARMIENTO DE AYUDA ECONÓMICA (Educación Universitaria)") as a second source URL of `scholarships.beca_de_ayuda_economica`, as ticket 09 did for rwth's award page? | yes, after a worker reads the page against the expert's note | it is UBA's own page for the same award, it states the residence condition the label quotes, and the run already reads it. The news post on `extension.uba.ar` is linked from no page the run reads |
