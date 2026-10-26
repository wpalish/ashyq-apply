# dev5 page audit: does today's confirm predicate accept the dev5 gold pages? (2026-10-19)

Generalisation ticket [10](wayfinder/generalisation/issues/10-dev5-gold-page-audit.md), loop id **G-10**, the offline
half of H-C. Written **before** ticket 14's dev5 baseline runs; the ceiling in §4 is the prediction that baseline is
compared with.

## 1. Method

- **Pages.** Every programme-role URL in `backend/evaluation/research/expert/data/programme_drafts_dev5.2026-10-19/`
  (`local`, `twin`, `department`, `site`, `related`; the `language` evidence items are not programme pages and are
  left out), plus the three `related_programme_urls` of `aitu.0-local` and the two of `satbayev.0-local`. 29 URLs,
  13 cases. dev5.draft1.json is being assembled in parallel and was not read; roles and the exact-vs-related status
  come from the drafts' own notes.
- **Fetch.** By hand through the agent's egress, production User-Agent (`fetching.USER_AGENT`), robots.txt read
  first for every host (a 4xx robots.txt = allow all, as `RobotsPolicy` does; an unreadable one = refuse), at least
  1 s per host and the declared Crawl-delay (corsidilaurea.uniroma1.it: 10 s, waited). No bypass. Saved to
  `scratchpad/g10/pages/` with `fetch_log.json`.
- **Checks** (`scratchpad/g10/tools/audit.py`, `diag.py`; `python -I`; the method of `scratchpad/wf_tools/classifier_audit.py`):
  `page_classifier.classify_page(url, html)` → `live_discovery.profile_rejects(page, "bachelor", ["computer science"],
  url, country)` — the predicate the confirm step and the walker share; `english_alternate` / `local_alternate`;
  `is_front_page`; and R6's `catalogue.discovery._names_other_institution` (and `_refused_page`) with the seed row's
  English name over `_identity_parts` (title + h1 + `og:site_name`). Seed names: the top-500 seed row where one exists
  (lmu, tud, sapienza, unipd, satbayev, bilkent); otherwise the core draft's `university` value (no seed row).
- **Defaults** as on the branch: `LOCALIZED_IDENTITY`, `LOCALIZED_PAGE_IDENTITY` (R1, which absorbs LX-1's degree
  and subject parts), `SUBJECT_TITLE_SHAPES`, `FRONT_PAGE_NOT_PROGRAMME`, `CAMPUS_GUARD`, `INTEGRATED_MASTERS_LEVEL`,
  `PROGRAMME_PAGE_GUARD` on; `LEXICON_V2` off. A second pass with `LEXICON_V2 = True` changed **no verdict**.
- **CI evidence reports** (`scratchpad/verify_dev5prog/`, `verify_dev5core/`) were read as untrusted context only:
  the runner opened 35 of 39 programme items; kbtu and satbayev read `robots_disallowed` there (robots.txt
  unreachable), the same hosts that fail TLS here.

## 2. Per case

Status is the drafts' (owner ruling as applied by the experts): **exact** = a CS bachelor exists and is the gold;
**related only** = no CS bachelor, `programme_status unknown`, the right answer is abstention.

| case | status | role | page (lang · title / h1) | verdict | reason |
|---|---|---|---|---|---|
| aitu | exact | local (en) | `''` · "Astana IT University" / "Computer Science", "6B06101 Computer Science" | `reads_as:unknown` | no level word in title or h1; "bachelor" only in body and slug, the level also in the national code 6B |
| aitu | | twin (ru) | same shape, h1 "… (Компьютерные науки)" | `reads_as:unknown` | same |
| aitu | | twin (kz) | same shape, h1 "… (Компьютер ғылымы)" | `reads_as:unknown` | same |
| aitu | | related ×3 | Software Engineering, Mathematical and Computational Science, Big Data Analysis | `reads_as:unknown` ×3 | same (refused before the subject test) |
| bilkent | related only | local (en catalogue) | "Bilkent University - Online Academic Catalog" / "Bilkent University" | `reads_as:program_catalog` | 59 programme links, reads PhD first; a department page listing B.S./M.S./Ph.D. |
| bilkent | | twin (tr) | "Üniversite Adaylarına – … Computer Engineering Department" | `reads_as:unknown` | prospective-students heading, no programme identity |
| hacettepe | related only | local (tr) | `<title>` empty, no h1 | `reads_as:unknown` | `main_content` keeps 6 characters: the ASP.NET page wraps the whole body in one `<form>` |
| hacettepe | | twin (`lang=en` query; `<html lang="tr">`) | same | `reads_as:unknown` | same |
| kbtu | related only | related | — | **not fetched** | TLS chain incomplete (known since dev4) |
| lmu | exact | local (de) | "Informatik Bachelor mit Nebenfach 30 ECTS ( Bachelor / Hauptfach )" | `subject_mismatch` | left over after the alias and filler: `ects`, `hauptfach`, `nebenfach` |
| lmu | | department (de, ifi.lmu.de) | "Informatik Bachelor" | **accepted** | — |
| sapienza | exact | local (it) | "Informatica \| Course catalogue" / no h1 | `reads_as:program_catalog` | 13 programme links in a 580-character shell (course tabs load by script); no level word in the head |
| sapienza | | twin (en) | "Computer Science \| Course catalogue" | `reads_as:program_catalog` | same |
| satbayev | exact | local (kk) + related ×2 | — | **not fetched** ×3 | TLS chain incomplete from here; `robots_disallowed` on the runner |
| tud | exact | local (de) | h1 "Studiengang Informatik (Bachelor) akkreditiert" | `subject_mismatch` | left over: `akkreditiert` |
| tud | | twin (en) | h1 "Degree program Computer Science (Bachelor) accredited" | **accepted** | the applicant's own words pass without the filler test, so `accredited` is tolerated where `akkreditiert` is not |
| unipd | exact | local (it, unipd.it) | "INFORMATICA \| Università di Padova" | **accepted** | — |
| unipd | | site (it, informatica.math) | h1 "Laurea"; title "Laurea in Informatica :: Computer Science" | `subject_mismatch` | the h1 is the degree only, the subject is in the title / h2 |
| unipd | | twin (en) | h1 "Bachelor’s Degree"; h2 "Bachelor’s Degree in Computer Science" | `subject_mismatch` | same |
| upol | exact | local (cs) | title "Katedra informatiky - bakalářské studium Informatika", no h1; h2 "Informatika bakalářský studijní program" | `subject_mismatch` | the unit's name *before* the dash (`katedra`, `informatiky` left over); the h2 alone would pass |
| vilniustech | related only | local (lt) | "Informacinės technologijos" | `reads_as:unknown` | no level word in the head |
| vilniustech | | twin (en) | "Information Technologies" | `reads_as:unknown` | same |
| ytu | related only | local (tr) | "Bilgisayar Mühendisliği Lisans Programı (%30 İngilizce)" | `subject_mismatch` | R1 refuses the localized related form by name — the right refusal |
| zcu | exact | local (cs) | "Nabídka studia" / h1 "Nabídka studia", "Informatika" | `reads_as:unknown` | generic h1; no level word in the head; the body's first level word is the menu's "magisterské" |
| zcu | | department (cs, kiv.zcu.cz) | title "Informatika", no h1 | `reads_as:unknown` | no level word in the head |

**hreflang / twins.** Declared alternates: aitu (3, but `english_alternate` finds none from the ru/kz pages), unipd's
course site (en ↔ it, found), vilniustech (en ↔ lt, found). tud declares none, so the German page cannot hop to its
accepted English twin through R1 (iii); search must return the twin itself. **English twin alone accepted:** tud
only (sapienza, unipd, vilniustech, aitu, hacettepe twins are refused).

**R6, names another institution.** `_names_other_institution` is **false on all 25 fetched pages** and
`_refused_page` false on all 25: no gold or related page would be refused for naming another institution. On 17
of them the identity text holds no institution word at all, so the check cannot fire; on the 8 that do (aitu ×6,
bilkent ×2) the text shares a distinctive word with the seed name. **Front page:** none.

## 3. Totals per reason (25 fetched pages; 4 not fetched)

| verdict | pages | of which on an exact case's programme page |
|---|---|---|
| accepted | 3 | 3 (lmu department, tud twin, unipd local) |
| `reads_as:unknown` | 13 | 5 (aitu ×3, zcu ×2) |
| `reads_as:program_catalog` | 3 | 2 (sapienza ×2) |
| `subject_mismatch` | 6 | 5 (lmu local, tud local, unipd site, unipd twin, upol) |
| `degree_level_other` | 0 | 0 |
| identity not in text | 2 (inside `unknown`: hacettepe ×2) | 0 |
| front page | 0 | 0 |
| R6 names another institution | 0 | 0 |
| not fetched (TLS) | 4 | 1 (satbayev local) |

**By cause, and whether the shape is already listed** (ticket 10's table, ticket 19's Q1–Q4):

| cause | pages | listed? | gap |
|---|---|---|---|
| **No level word in title or h1** (level only in the body, the slug `-bachelor`, or a national code `6B…`; generic h1 "Nabídka studia") | aitu ×6, zcu ×2, vilniustech ×2 (sapienza also) | **no** — ticket 10's lexicon row was a level word present but unknown; here none is in the head | **rule gap** |
| **Thin script-rendered shell with programme links → catalogue** | sapienza ×2 | no | **rule gap** |
| **Content region emptied** (ASP.NET page in one `<form>`) | hacettepe ×2 | no (ticket 10's kaist/ub rows were short pages, not an emptied region) | **rule gap** (classifier's `main_content`) |
| **Unit name before the dash** ("Katedra informatiky - … Informatika") | upol | no — Q1 tests the head before the dash; here the programme is the tail | **rule gap** |
| **Form / status word not filler** (`akkreditiert`; `Hauptfach`, `Nebenfach`, `ECTS`) | tud local, lmu local | **yes** — Q2's "form word is filler" shape, listed for English (`major`, `with`, and `accredited` passes through the own-words path) | **lexicon gap** |
| **h1 is the degree only** ("Laurea", "Bachelor’s Degree") | unipd site, unipd twin | **yes** — ticket 10's structural-label row (Auckland "Bachelor of Science BSc") | listed, left to the identity decision |
| Correct refusals: related form by name (ytu), department catalogue (bilkent en), prospective-students page (bilkent tr) | 3 | — | none |

LX-1 (`LEXICON_V2`) on top of today's defaults: **0 verdicts change** — R1 already carries its words, and none of
the refusals above is a missing LX-1 word.

## 4. Predicted dev5 ceiling for programme-page confirmation

Cases with at least one page the predicate accepts today:

| status | cases | ceiling |
|---|---|---|
| exact (8: aitu, lmu, sapienza, satbayev, tud, unipd, upol, zcu) | **tud** (via the English twin), **unipd** (local), **lmu** (via the department page ifi.lmu.de) | **3 / 8** — **2 / 8** if dev5.draft1 does not list lmu's department page as a programme URL or variant |
| related only (5: bilkent, hacettepe, kbtu, vilniustech, ytu) | none accepted | **0 wrong confirms** predicted from these pages (every related page is refused, one of them for the right reason) |

Unreachable regardless of the predicate: satbayev (TLS; the runner probe agrees), kbtu (TLS). aitu, sapienza, upol
and zcu cannot be confirmed **whatever search returns**: every labelled page of theirs is refused, four of them by
rule gaps no lexicon closes. tud can be confirmed only if search (or the walker) reaches the English twin, since the
German page declares no alternate.

The baseline of ticket 14 is compared with **3 / 8 (exact cases confirmed ≤ 3)** and **0 wrong confirms on the
pages listed here**; a hit above the ceiling would mean a page outside the label was accepted, a confirm below it
that search or budget lost a page the predicate takes.

## 5. Files

- `scratchpad/g10/pages/*.html`, `scratchpad/g10/pages/fetch_log.json` (fetch, robots notes, status per URL).
- `scratchpad/g10/tools/{pagelist,fetch,audit,diag,show}.py`; outputs `scratchpad/g10/audit_defaults.json`,
  `scratchpad/g10/audit_lx1.json`.
- Code read: `backend/app/adapters/page_classifier.py` (`classify_page`, `_identity`, `main_content`,
  `_degree_words`, `LOCALIZED_PAGE_IDENTITY`), `backend/app/adapters/discovery/live_discovery.py` (`profile_rejects`,
  `_matches_field_text_localized`, `_LOCAL_TITLE_FILLER`, `_LOCALIZED_DEGREE_FILLER`, `_names_related_local_form`,
  `english_alternate`), `backend/app/catalogue/discovery.py` (`_identity_parts`, `_names_other_institution`,
  `_refused_page`), `backend/app/adapters/search/ontology.json` (`computer_science`).
- No heldout file, capture, log or label was opened; no number about the nine was computed.
