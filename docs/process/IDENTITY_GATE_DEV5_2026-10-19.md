# Identity gate, native names and award bindings on dev4 + dev5 (G-11, 2026-10-19)

Ticket: [generalisation 11](wayfinder/generalisation/issues/11-identity-gate-native-names-dev5.md) (H-E). Offline:
homepages fetched 2026-10-19 by plain `curl` through the agent proxy (normal browser UA, `Accept-Language: en` as
the production `Fetcher` sends, robots.txt read first and honoured, TLS verified, no retries, no bypass). The
production `Fetcher` itself cannot leave this sandbox (every host: `robots.txt unreachable (ConnectError)`), so a
curl shim stands in for it; everything after the fetch is **production code called unchanged**:
`CatalogueDiscoveryAdapter._identity_branch` (R6, `SITE_IDENTITY_V2 = True`, the rule on by default today) with a
stand-in `University` row built the way `importer.import_catalogue` builds it, and the pre-R6 title rule (`legacy`)
re-implemented from the `else` branch of `_probe_site`. No heldout file, capture, log, label or registry row was
opened; nothing here is about the nine.

Scripts and pages (session scratchpad, not in the repo): `scratchpad/g11/fetch_gate_curl.py` (gate),
`scratchpad/g11/fetch_en.py` (English homepages for the name table), `scratchpad/g11/names.py` (name table),
results `gate_results_curl.json`, `en_pages.json`, `names.json`, pages `scratchpad/g11/pages/`.

**Correction to the ticket's premise.** The ticket was charted against the pre-R6 rule (title/h1 must hold the
English seed name). Rule R6 — exactly the three signals of programme-discovery ticket 05 (`official_site`,
`native_name`, `english_alternate`) plus today's title rule — already landed as `SITE_IDENTITY_V2` (IG-1, on by
default since paired runs 39113842507 / 39113844090). The table therefore reports both rules; the verdict is read on
R6, the gate production runs today.

## 1. The gate

Entry for a seed row: name `canonical_name(row.name)`, aliases as the importer builds them, `seed_snapshot.record` =
the row. Off-seed row (no top-500 row; the product never reaches these universities at all): the English name the
institution's own English site uses, no snapshot, so `official_site` and `native_name` cannot fire. Off-seed names
are this worker's choice pending ticket 02's `DEV5_OFF_SEED`.

| set | case | probed → final | `<title>` (homepage) | lang | en alternate found | legacy | **R6** |
|---|---|---|---|---|---|---|---|
| dev5 | kbtu | kbtu.edu.kz | — TLS: `unable to get local issuer certificate` (leaf-only chain, as 2026-10-18) | — | — | — | **inconclusive** |
| dev5 | satbayev | satbayev.university | — TLS: same | — | — | — | **inconclusive** |
| dev5 | aitu | astanait.edu.kz → /en | Astana IT University | (none) | — | PASS | PASS `title_name` |
| dev5 | hacettepe | www.hacettepe.edu.tr | Hacettepe Üniversitesi | tr | /english (language link) | FAIL | PASS `english_alternate` |
| dev5 | bilkent | www.bilkent.edu.tr → w3.bilkent.edu.tr/bilkent/ | EN / Bilkent University | en-US | — | PASS | PASS `title_name` |
| dev5 | ytu | www.yildiz.edu.tr | Yıldız Teknik Üniversitesi | tr | /en (hreflang) — its title is **also** `Yıldız Teknik Üniversitesi` | FAIL | **FAIL conclusive** (native name on both versions) |
| dev5 | upol | www.upol.cz | Univerzita Palackého v Olomouci | cs | /en/ (language link) | FAIL | PASS `english_alternate` |
| dev5 | zcu | www.zcu.cz → /cs/index.html | Západočeská univerzita v Plzni | cs | /en/ (language link) | FAIL | PASS `english_alternate` |
| dev5 | tud | www.tu-dresden.de → tu-dresden.de | Technische Universität Dresden — TU Dresden | en | ?set_language=en | PASS | PASS `official_site` |
| dev5 | lmu | www.lmu.de → /de/index.html | Startseite - LMU München | de | — | FAIL | PASS `official_site` |
| dev5 | unipd | www.unipd.it | Università di Padova \| Università di Padova | it | — | PASS | PASS `title_name` |
| dev5 | sapienza | www.uniroma1.it → /it/ | Home \| Sapienza Università di Roma | it | none detected (the `/en/` homepage's title is Italian too) | FAIL | **FAIL conclusive** (native name; seed row has no domain) |
| dev5 | vilniustech | vilniustech.lt | VILNIUS TECH – Vilniaus Gedimino technikos universitetas | lt | /en/ (hreflang) — title `Homepage - VILNIUS TECH` | FAIL | **FAIL conclusive** (native + brand short name) |
| dev4 | ctu | www.cvut.cz | Home - Veřejný web - České vysoké učení technické v Praze | cs | /en (language link) | FAIL | PASS `english_alternate` |
| dev4 | vut | www.vut.cz | Vysoké učení technické v Brně | cs | /en/ (language link) | FAIL | PASS `english_alternate` |
| dev4 | rwth | www.rwth-aachen.de → /go/id/a/?lidx=1 | RWTH Aachen University \| … \| EN | en-US | yes | PASS | PASS `title_name` |
| dev4 | kit | www.kit.edu | KIT - Karlsruher Institut für Technologie | de-DE | /english/index.php (hreflang) | FAIL | PASS `english_alternate` |
| dev4 | unibo | www.unibo.it → /it | Università di Bologna | it | yes | FAIL | PASS `official_site` |
| dev4 | taltech | taltech.ee | Ülikool \| TalTech on Eesti uuendusmeelseim ülikool | et | none detected (`/en` exists, title `Homepage`) | FAIL | **FAIL conclusive** (native + short name) |
| dev4 | ktu | ktu.edu | Kauno technologijos universitetas \| KTU | lt | en.ktu.edu (hreflang) | FAIL | PASS `english_alternate` |
| dev4 | boun | bogazici.edu.tr | T.C. Boğaziçi Üniversitesi | tr | /en (language link) | FAIL | PASS `official_site` |
| dev4 | itu | itu.edu.tr | İTÜ \| İstanbul Teknik Üniversitesi \| İTÜ 1773 | en | /en (language link) | FAIL | PASS `official_site` |

R6's "parked / names another institution" refusal fired on none of the 20 pages read (homepages and English
alternates).

**Counts.**

| | dev5 (13) | dev4 (9) |
|---|---|---|
| R6 (today) | **PASS 8 · FAIL conclusive 3 (ytu, sapienza, vilniustech) · inconclusive 2 (kbtu, satbayev — TLS)** | PASS 8 · FAIL conclusive 1 (taltech) |
| legacy title rule | PASS 4 · FAIL conclusive 7 · inconclusive 2 | PASS 1 · FAIL conclusive 8 |
| R6 branch that passed | `title_name` 3, `english_alternate` 3, `official_site` 2, `native_name` 0 | `english_alternate` 4, `official_site` 3, `title_name` 1 |

The three signals of ticket 05 recover 4 of the 7 dev5 legacy failures (hacettepe, upol, zcu by the English
alternate; lmu by `official_site`) and 7 of 8 on dev4. `native_name` fired nowhere: no seed record carries one (16-Q8).

**Caveats that move the number.**
- `official_site` fires only where the seed row has `official_domain`/`official_site` (tud, lmu, bilkent, unibo, boun,
  itu). Seed rows without either (satbayev, unipd, sapienza; dev4 ctu, rwth, kit) have no `uni.domain`, so production
  probes nothing until the search fallback (`"<name>" "<country>" official university website`, 1 query) returns a
  host; this table assumes the official host is among the first three results.
- Seven of the thirteen dev5 universities (kbtu, aitu, hacettepe, ytu, upol, zcu, vilniustech) and three dev4 ones
  are not in the top-500 seed: production never offers them, so for the *product* the gate question is moot there;
  for the harness gate arm their result depends on the off-seed name 02 writes.
- kbtu and satbayev are `unavailable` by 02's rule if the runner sees the same TLS refusal; they then leave dev5 and
  the denominator is 11 (3 conclusive failures of 11).

**What would pass the residue — data, not a new rule.** With a `native_name` in the record, the production
`_native_name_match` (lang check included) passes all four residual failures on the saved pages: sapienza
`Sapienza Università di Roma` (it), vilniustech `Vilniaus Gedimino technikos universitetas` (lt), ytu
`Yıldız Teknik Üniversitesi` (tr), taltech `TalTech` (et) — checked. Sapienza would also pass by `official_site`
if its seed row carried `uniroma1.it`. One trap found: `app.domain.dedupe.normalize` keeps the Turkish dotless `ı`
(`normalize("Yıldız") == "yıldız"`), so an ASCII native name `Yildiz Teknik Universitesi` does **not** match the
page, and an English name spelled `Yildiz` never matches a page that writes `Yıldız` (title rule and R6 alike).

## 2. Native-name table: scorer `university` dimension and R6 "another institution"

*Recorded* = what a claim's scope carries: `cand.name` (`runner.py`), i.e. the harness entry name (`canonical_name`
of the seed row, or the off-seed name). *English* = dev4: the label's `scope.university` in `dev4.draft3.json`
(one value per case); dev5: the name the institution's own English page uses (no dev5 labels exist yet — 03/04
open). Scorer = `metrics.dimension_matches("university", label, recorded)` (`_name_parts` ∪ `_acronym_names` both
ways). R6 = `_names_other_institution([normalize(recorded)], normalize("Faculty of Engineering - " + English))` — a
faculty/English page that names us the way the site does in English.

| set | case | recorded (entry) | English (dev4: label) | native | short | scorer: English | scorer: native | scorer: short | R6 "other" on English |
|---|---|---|---|---|---|---|---|---|---|
| dev5 | kbtu | Kazakh-British Technical University | same | Казахстанско-Британский технический университет | KBTU | ✓ | ✗ | ✓ | no |
| dev5 | satbayev | Satbayev University | same | Сәтбаев университеті | — | ✓ | ✗ | — | no |
| dev5 | aitu | Astana IT University | same | (site is English) | AITU | ✓ | ✓ | ✗ | no |
| dev5 | hacettepe | Hacettepe University | same | Hacettepe Üniversitesi | HÜ | ✓ | ✗ | ✗ | no |
| dev5 | bilkent | Bilkent University | same | Bilkent Üniversitesi | Bilkent | ✓ | ✗ | ✗ | no |
| dev5 | ytu | Yildiz Technical University | **Yıldız** Technical University | Yıldız Teknik Üniversitesi | YTÜ | **✗** | ✗ | ✗ | **yes** |
| dev5 | upol | Palacký University Olomouc | same | Univerzita Palackého v Olomouci | UP | ✓ | ✗ | ✗ | no |
| dev5 | zcu | University of West Bohemia | same | Západočeská univerzita v Plzni | ZČU | ✓ | ✗ | ✗ | no |
| dev5 | tud | Technische Universität Dresden | **TU Dresden** | Technische Universität Dresden | TUD | **✗** | ✓ | ✓ | no |
| dev5 | lmu | Ludwig-Maximilians-Universität München | **LMU Munich** | LMU München | LMU | **✗** | ✗ | ✗ | no |
| dev5 | unipd | Università di Padova | **University of Padua** | Università di Padova | UniPD | **✗** | ✓ | ✗ | **yes** |
| dev5 | sapienza | Sapienza University of Rome | same | Sapienza Università di Roma | Sapienza | ✓ | ✗ | ✗ | no |
| dev5 | vilniustech | Vilnius Gediminas Technical University | **VILNIUS TECH** | Vilniaus Gedimino technikos universitetas | VILNIUS TECH | **✗** | ✗ | ✗ | no |
| dev4 | ctu | Czech Technical University in Prague | same | České vysoké učení technické v Praze | ČVUT | ✓ | ✗ | ✗ | no |
| dev4 | vut | Brno University of Technology | same | Vysoké učení technické v Brně | VUT | ✓ | ✗ | ✗ | no |
| dev4 | rwth | RWTH Aachen University | same | Rheinisch-Westfälische Technische Hochschule Aachen | RWTH | ✓ | ✗ | ✗ | no |
| dev4 | kit | KIT, Karlsruhe Institute of Technology | Karlsruhe Institute of Technology | Karlsruher Institut für Technologie | KIT | ✓ | ✗ | ✓ | no |
| dev4 | unibo | Alma Mater Studiorum - Università di Bologna | **University of Bologna** | Università di Bologna | Unibo | **✗** | ✓ | ✗ | no |
| dev4 | taltech | Tallinn University of Technology | same | Tallinna Tehnikaülikool | TalTech | ✓ | ✗ | ✗ | no |
| dev4 | ktu | Kaunas University of Technology | same | Kauno technologijos universitetas | KTU | ✓ | ✗ | ✗ | no |
| dev4 | boun | Boğaziçi University | same | Boğaziçi Üniversitesi | BOUN | ✓ | ✗ | ✗ | no |
| dev4 | itu | Istanbul Technical University | same | İstanbul Teknik Üniversitesi | İTÜ | ✓ | ✗ | ✗ | no |

22 rows. Native names for kbtu/satbayev are public knowledge (pages unreadable); every other native/English form is
the one the fetched page prints.

**Findings.**
- **Scorer — one live dev4 miss.** unibo's label scope `University of Bologna` does not match the recorded
  `Alma Mater Studiorum - Università di Bologna` (parts `alma mater studiorum`, `università di bologna`; no acronym):
  every unibo claim that carries the label's university dimension scores **wrong scope on the name alone** — the
  same class as the KIT and UNSW patches. 8 of 9 dev4 label names match.
- **Scorer — dev5 at risk.** If 04's labels use the English form the site prints, 5 of 13 fail: tud (`TU Dresden`),
  lmu (`LMU Munich`; the acronym of the hyphenated name reads `lmum`), unipd (`University of Padua` vs `Padova`),
  vilniustech (`VILNIUS TECH`), ytu (`Yıldız` vs `Yildiz`: `_plain` folds case, not diacritics). The scorer never
  matches a native name unless it equals the recorded one.
- **R6 "names another institution" is a gate check only.** `_names_other_institution` is called from
  `_refused_page` in `_identity_branch` (homepage and English alternate) and nowhere in confirm; the ticket's "confirm
  step" framing does not match the code. On the 20 real pages it refused nothing. On a page naming us in English it
  would wrongly refuse unipd (`University of Padua` shares no distinctive token with `Università di Padova`) and ytu
  (dotless `ı`); today neither reaches that check on a page that says so (unipd passes on its Italian title first).

## 3. Award bindings

- **dev4 draft3** (`evaluation.research.expressibility --dataset dev4.draft3.json --bindings
  identity_bindings.dev4-draft3.json`): claim recall can be scored on **20 of 20** known facts (0 no claim type, 0
  unbound, 0 bound-but-unmapped); with no bindings, 15 of 20. Award labels: 4 named awards (vut accommodation, rwth
  Deutschlandstipendium, taltech IT-faculty, ktu partial tuition waiver) on 4 of 9 cases, 8 award-key labels (6 known,
  2 unknown: `.exists` ×4 and `.applicability.international` ×4); 5 binding rows (rwth's award bound on 2 URLs) — all
  4 awards bound. The pipeline emits both keys for a bound award (`scholarships.<id>.exists`,
  `.applicability.international`), so the 5 known award facts are reachable only through the bindings.
- **dev5**: no draft (03/04 open) and no `identity_bindings.dev5-draft1.json` (02 open). Coverage today: 0 bindings;
  every award label 04 writes needs one, and any claim on a dev5 award page stays `unmapped.*` until it exists. The
  count of named awards on dev5 award pages cannot be taken before the drafts name the pages.

## Verdict

- **H-E for the product path: not confirmed on today's gate.** On R6, 3 of 13 dev5 homepages fail conclusively
  (ytu, sapienza, vilniustech) and 2 are inconclusive (TLS) — below the pre-registered ≥ 4. It **would** be confirmed
  on the pre-R6 title rule (7 of 13). The gate arm of the second look should be pre-registered as *expected to lose
  about 3 of 11 readable dev5 cases at the gate* (taltech the one on dev4), all native- or brand-name homepages with
  no English name the rule reads. No new rule is needed — `IDENTITY_GATE_NATIVE_NAME` would duplicate R6's
  `native_name` branch, which is built and fires as soon as a record carries the native name; the residue is
  **data** (native names in the seed/off-seed rows, sapienza's missing domain) plus the dotless-ı normalisation.
- **H-E for the scorer: not refuted.** dev4 unibo fails `dimension_matches` on its recorded name today; on dev5, 5 of
  13 would fail if labels use the site's English form. Either the corpus writes the recorded (catalogue) name as the
  scope university or the scorer gains an alias/diacritic fold — an identity decision for 04 / the owner, not taken
  here.
- **Bindings:** dev4 fully bound (20/20 reachable); dev5 unbound by construction until 02/04 land.

Loop id **G-11**. No code change.
