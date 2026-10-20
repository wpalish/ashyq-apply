# Seen-site ledger: every default-on rule since 2026-10-17, by motivating cases and gains elsewhere (2026-10-19)

Generalisation ticket [12](wayfinder/generalisation/issues/12-seen-site-rule-ledger.md), hypothesis H-F, loop id G-12.
Offline. Development data only: no heldout file, capture, log or label was opened, and this ledger computes no
number about the nine.

## Sources

- The flag comments in `backend/app/**` and `backend/evaluation/**`. Every module-level `NAME = True` was
  scanned, including the `NAME = (True  # on: …)` form: 51 flags in all. The script and its dump are in
  `scratchpad/g12/flags.py` and `scratchpad/g12/flags.txt`.
- `backend/evaluation/research/runs/2026-10-17/LOOP_REPORT.md`, every cycle table, except the two sections about
  the nine.
- `git log --since=2026-10-17`: the "on by default" commits and their bodies (runs, gains).
- The scored paired runs in `scratchpad/runs/*/sc.json`, using `changes.gained`, `changes.lost` and
  `changes.unstable` from 54 set-runs.
- `expert/data/hypotheses.json`.
- `CORE_GAP_ANALYSIS_2026-10-18.md` §3.
- Programme-discovery tickets 07 and 19.

## Definitions

- **Motivating cases**: the development cases the flag comment, its analysis or its commit names as the reason
  for the rule. **Motivating sets** are the sets those cases belong to: C = cohort, D2 = dev2, D3 = dev3,
  D4 = dev4.
- **Stable gain**: what the loop recorded. That is the same change in both on repetitions and in no off
  repetition. A removed wrong claim or a removed wrong programme page also counts as a gain.
- **Verdict**, in the ticket's vocabulary:
  - **general**: a stable gain on at least one case in a set other than the motivating sets, or a precision
    guard. A precision guard here means a rule that only refuses or skips a read, a page or a claim. It adds no
    read and fires on unseen pages by construction.
  - **seen-site**: every recorded gain falls on the motivating sets.
  - **unmeasured**: on without a paired run of its own.
- **Kind**: *guard* (refuses or skips only), *recall* (adds or accepts a read, page, query or claim) or *scorer*.

## The noise floor (read this before the table)

The scratchpad holds 8 A/A set-runs: base2 and base3, where both arms are identical defaults and each arm has
2 repetitions. **1 of the 8 shows a "stable gain"**: `ctu:programme.exists` on base3-dev4, at pipeline
`1093faaa` in both arms.

The same label is also EF-1's only gain (ef1-dev4), and EF-1 did not repeat. The cohort's `ubc:deadline`
appears as a stable gain or a stable loss under three unrelated rules (ef1b, pd1, dl6), and dl6b showed the
dl6 loss was noise.

So a single label gained over 2+2 repetitions has a false-positive rate on the order of 1 in 8 set-runs. Three
**general** verdicts below rest on exactly one such gain outside the motivating sets: LI-1, CL-1 and R1. They
are marked *weak*.

## Ledger

Gains are given as case:label (set). In the "outside?" column, "set" means a gain in a set other than the
motivating sets. "case" means a gain on a case that was not named but sits in a motivating set.

| # | flag / loop id | on since (runs) | motivating cases (set) | stable gains recorded, by case (set) | gains outside the motivating set? | kind | verdict |
|---|---|---|---|---|---|---|---|
| 1 | `DEADLINE_AWARD_CONDITION` DL-3 | 39063173594 (C only) | ubc (C) | ubc wrong deadline removed (C) | no | guard | **general** (guard) |
| 2 | `CANONICAL_HTTP_HTTPS` CU-1 | 39067189351 / 90840 | none in development; the comment names a heldout-set trace | no label; dev2 reads 345→326 (D2) | set (D2 reads) | guard (dedupe) | **general** |
| 3 | `PROGRAMME_PAGE_GUARD` PG-1 (+ `/cs` root fix) | 39067949720 / 51214 | hku (C); also a heldout-set trace | non-programme pages no longer reported: kaznu, tec, uba, khalifa (D2), aalto minor, hku root (C) | set (D2) | guard | **general** |
| 4 | `LOCALIZED_IDENTITY` LI-1 | 39068981447 / 82766 | none in development; the comment names heldout-set traces | psaclay programme page (D2) | set (D2) | recall | **general**, *weak* (one 2-rep gain) |
| 5 | `CATALOG_HEADING_SCOPE` CL-1 | 39074829596 / 31170 | tcd, uppsala (D2) | tcd, uppsala programme pages (D2); groningen ielts.overall (C) | set (C) | recall | **general**, *weak* (groningen only) |
| 6 | `DISCOVERY_QUERY_RESERVE` QB-1 + QB-1b | 39080847253 / 50234 / 51464 | every dev2 trace (D2); ntu, groningen, warsaw (C) | uppsala ielts.overall + subscores (D2); auckland ielts.overall (D3), seen in 2 runs | set (D3) | recall | **general** |
| 7 | `TOPIC_FACULTY_SCOPE` FS-1 | same runs | groningen (C) | groningen wrong IELTS removed (C) | no | guard | **general** (guard) |
| 8 | `TOPIC_PROGRAMME_SCOPE` FS-2, narrowed | 39096181406 / 82669 / 83785 | um (D3); the narrowing used auckland, imperial (D3) and delft (C) | um wrong claims removed (D3); warsaw programme.exists + language (C) | set (C), but a guard has no plausible path to the warsaw gain, so it is likely noise | guard | **general** (guard) |
| 9 | `STAGE_BUDGETS` SB-1 | bundle 39098957286 / 8087 / 8849 | ubc, groningen (C); tcd (D2); imperial, unsw (D3) | alone: none (and unsw wrong + dev3 pages 4→2-3); bundle: delft deadline (C), uct ielts (D2), imperial deadline (D3), not attributable to SB-1 | no; dev4 never measured | recall (order / stop) | **seen-site** |
| 10 | `QUESTION_ROUTED_EVIDENCE` QR-1 + QR-1b/c | alone 39092653528/…; bundle as above | tcd, uct (D2); ucph (D3); "12 of 16" fee pages (C/D2/D3) | delft:deadline alone (C); bundle as above | case only (delft is unnamed but in C); dev4 never measured | recall | **seen-site** (closest to general) |
| 11 | `FUNDING_IDENTITY_SCOPE` FI-1 | bundle only | unsw, auckland (D3) | none attributable | — | recall | **unmeasured** |
| 12 | `CAMPUS_GUARD` CG-1 | bundle | unsw (D3) | unsw Bengaluru page refused (D3) | no | guard | **general** (guard) |
| 13 | `INTEGRATED_MASTERS_LEVEL` IM-1 | follow-up, no own run | imperial (D3) | — | — | guard + order | **unmeasured** |
| 14 | `REDIRECT_MEMORY` RS-1 | 39111356705 / 58435 / 60138 | imperial (D3) | dev3 over budget 6→2, together with rows 15–18 (D3) | no | guard (saver) | **general** (guard) |
| 15 | `URL_VARIANT_DEDUPE` RS-2 | same | chula, imperial (D3) | same | no | guard (saver) | **general** (guard) |
| 16 | `SITEMAP_TRIM` SM-2 | same | chula (D3) | same | no | guard (skip) | **general** (guard) |
| 17 | `SCHOLARSHIP_LEVEL_SCOPE` SL-1 | same | imperial, chula (D3) | same | no | guard (skip) | **general** (guard) |
| 18 | `CASE_READ_LEDGER` RL-1 | 39111362101 / 63921 / 65418 | the DoD budget, all sets | same | no | guard (cap) | **general** (guard) |
| 19 | `SITE_IDENTITY_V2` R6 | 39113842507 / 44090 (D2, D3 through the gate) | M3's failures: kaznu, tcd, tsinghua, uppsala, khalifa (D2); auckland, chula, iitd, ntutw, ub, ucph, uio, utokyo, msu, kuleuven (D3) | identity 5-6→8/10 (D2), 6→12/15 (D3), on those cases | no; C and D4 never measured through the gate | recall | **seen-site** |
| 20 | `LOCALIZED_PAGE_IDENTITY` R1 | 39119685301 … 90148 | uba, psaclay (D2); puc, iitd, ucph (D3), as offline fixtures | rwth programme page (D4) | set (D4) | recall | **general**, *weak* (one 2-rep gain) |
| 21 | `SUBJECT_TITLE_SHAPES` R2 + R2b | 39129349634 … 54412 | uio, kuleuven, imperial, iitd (D3); uct (D2); delft (C) | imperial, uio, unsw pages (D3); kit page (D4) | set (D4) | recall + guard | **general** |
| 22 | `LOCAL_LANGUAGE_QUERIES` R5 | 39127583646 … 88639 | the M5 six: uba, psaclay (D2); puc, uio, kuleuven, ucph (D3) | uba (D2), iitd (D3) programme pages; dev4 1→1 | case only (iitd is not in the six but is in D3) | recall (query) | **seen-site** |
| 23 | `CASE_TIME_BUDGET` TB-1 | 39127473231 / 74664 / 39128704750 / 06390 | ubc (C); unsw, kuleuven (D3) | over budget C 1→0, D3 2→0; no loss on D2 or D4 | no | guard (cap) | **general** (guard). Note: it cost ubc's deadline read, which is why QP-1 exists |
| 24 | `FEE_SUBPAGE_EXCLUSION` | 39134950075 … 56132 | imperial (D3) | fewer reads, no label | no | guard | **general** (guard) |
| 25 | `LOCAL_TWIN_ON_IDENTITY_REFUSAL` | same | kit, rwth, ctu (D4); puc (D3) | fewer reads, no label | no | guard | **general** (guard) |
| 26 | `ALIAS_AWARE_PROGRAM_MATCH` | same | kit (D4) | rwth programme.exists (D4) | case only (same set) | recall (confirm) | **seen-site** |
| 27 | `INTAKE_SECTION_DEADLINE` DL-5 + DL-5b | 39145855313 / 57030 / 58769 (C, D2, D3) | auckland (D3); uppsala (D2) | uppsala deadline (D2), auckland deadline (D3) | no; D4 not run | recall | **seen-site** |
| 28 | `QUESTION_PAGE_ORDER` QP-1 | same bundle | ubc (C) | none attributable (ubc deadline not gained) | no | recall (order) | **seen-site** |
| 29 | `PARENT_DEGREE_LINK` QR-2 | same bundle | auckland (D3) | auckland deadline, shared with DL-5 (D3) | no | recall (adds a read) | **seen-site** |
| 30 | `SCHOLARSHIP_INDEX_QUERY` SQ-1 | same bundle | uppsala (D2); groningen (C) | none in its runs | no | recall (adds a query) | **seen-site** |
| 31 | `AWARD_PAGE_EVIDENCE` AP-1 + AP-1b | 39149288366 / 90043 | imperial (D3); ubc, hku (C); tcd (D2) | ubc major_entrance (C), imperial_inspires (D3) | no | recall | **seen-site** |
| 32 | `ENGLISH_READERS_V2` EN-2 + EN-2b | 39150325173 / 26857 / 28178 | imperial, unsw (D3); tcd (D2); TF-2's delft (C), uppsala (D2) | delft toefl (C); tcd ×4, uppsala toefl (D2); imperial ×2 (D3) | no | recall | **seen-site** |
| 33 | `FEE_READERS_V2` FE-2 + FE-2b | 39150329872 / 31765 / 33407 | imperial (D3); tcd (D2) | tcd tuition (D2), imperial tuition (D3) | no | recall | **seen-site** |
| 34 | `NAV_LINK_LEVEL_GUARD` AP-1c | 39153129640 … 34257 | the base2 trace (postgraduate nav pick) | none | no | guard | **general** (guard) |
| 35 | `ID1_URL_ALIAS` + `ID1_SCORER_ALIASES` ID-1 | owner-signed 02-Q1/Q2; base2/ap1c re-scored | ntu (C) | ntu +3 labels (C); the re-score changed only ntu | no | scorer | **seen-site** (scorer) |
| 36 | scorer acronym / brand-name match (`.htm`, "KIT, Karlsruhe…", UNSW Sydney) | re-score of every saved capture | kit (D4), unsw (D3) | kit precision 1.00 (D4); evb-dev3 on#1 wrong_scope 2→0 (D3), the only change in the full re-score | no | scorer | **seen-site** (scorer) |
| 37 | `FRONT_PAGE_NOT_PROGRAMME` FP-1 | 39164210866 / 212652 / 214438 / 215839 | hku (C) | none | no | guard | **general** (guard) |
| 38 | `QUOTED_HREF_GUARD` QH-1 | 39164236421 … 41246 | tcd (D2) | tcd E3 exists + international (D2), with AN-1 | no | guard (skip) | **general** (guard) |
| 39 | `INTERNATIONAL_ROUND_DEADLINE` DL-6 | 39168347411 … 52273 + 39170267444 | uppsala (D2) | uppsala deadline wrong→hit (D2) | no | recall (adds a read) + guard | **seen-site** |
| 40 | `COORDINATED_DEGREE_SCOPE` SC-2 | 39164239686 + 39170160596 (D3, 4 reps) | unsw (D3) | unsw ielts.overall + subscores (D3) | no | recall (scope inheritance) | **seen-site** |
| 41 | `AWARD_NAME_QUALIFIER` AN-1 | 39173608793 … 13552 | uppsala (D2) | uppsala Anders Wall exists (D2); tcd E3 with QH-1 (D2) | no | recall | **seen-site** |
| 42 | `AWARD_COORDINATED_DEGREE_SCOPE` AN-1b | same | uppsala (D2) | uppsala award scoped bachelor, not master (D2) | no | guard (scope silent) | **general** (guard) |

These bug fixes went on by default without a paired run of their own, and each counts as **unmeasured**. All of
them carry tests. None has a flag, so none can be re-measured off/on.

| # | fix | motivating case (set) |
|---|---|---|
| 43 | IELTS plural "bands" floor | auckland (D3) |
| 44 | sitemap https namespace and relative locs ("changed no label by itself") | unsw (D3) |
| 45 | TOEFL read from TOEFL's own statement | um (D3) |
| 46 | an opening or announcement date is never the deadline | imperial (D3) |
| 47 | ISO deadline more than a year past, and exchange pages, not claimed | puc (D3) |
| 48 | cycle 4a extraction fixes (deadline before a test window, "Score required" cell, IELTS in a list) | cohort/dev3 traces |
| 49 | programme name without a file extension | kit (D4) |
| 50 | R6 fallback query inside the 6-query budget | auckland, ntutw, utokyo (D3) |
| 51 | QP-1 and SQ-1 product fixes landed in test alignment | — |

Flags on before 2026-10-17 are outside this ledger. They were measured in the 2026-10-05/06 runs, not in this
loop report: `TOPIC_SEARCH` ER-08, `NAVIGATION_FIELD_LEADS` ER-09, `DEADLINE_V2`, `TUITION_ROW_YEAR`,
`APPLICANT_ACADEMIC_YEAR`, `FEE_YEAR_COLUMNS`, `SHARED_QUERY_BUDGET`, `RATE_LIMIT_RETRY`, `ROUTE_LEADS`,
`DOCUMENT_RULES_V2`, `DOCUMENT_LEADS`, `FORM_LABEL_HEADINGS`, `RECOVER_SEARCH_CANDIDATES`,
`SEARCH_FUNDING_FALLBACK` and `TARGET_AWARD_SEARCH`. They are the cohort's ER-era rules, and every motivating
case named in their comments is a cohort case.

**The award route is not on.** The ticket lists it among the rules turned on, but `AWARD_ROUTE = False`.
AR-1 stayed off: it changes the golden demo and never gained a label.

## Rules motivated by a heldout trace (HP-AUDIT D5, added 2026-10-20)

`HELDOUT_PROVENANCE_AUDIT_2026-10-20.md` (`e30dd2d5`), decision D5, hands four rules to this ledger: they are not
language rows, but their introducing commits cite the quarantined discovery analysis and their old comments named
heldout universities (the comments are generic since `e30dd2d5`). Built from commit hashes, commit subjects and the
current generic comments only; the quarantined analysis and no heldout file, capture, log or label were opened.
Same columns as the ledger, plus the heldout reference. For every row the heldout look of 2026-10-19 is
**in-sample** evidence, not out-of-sample.

| # | flag / loop id | introduced (commit) | on since (runs) | motivating trace, generic shape | heldout reference | stable gains recorded, by case (set) | gains outside the motivating set? | kind | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 52 | PG-1's `news-single-view` exclusion (`live_discovery._PG1_URL_EXCLUSIONS`, read only under `PROGRAMME_PAGE_GUARD`) | `ae3ce135` | with PG-1 (row 3): 39067949720 / 51214; no run of its own | a CMS news-article view path, `…/news-single-view…/article/…`, offered as a programme lead | commit cites the quarantined analysis; the trace was a heldout-set run | none attributable (PG-1's gains are on other page shapes) | — | guard (excluded path) | **general** (guard, by construction), not separately measurable: its only off arm is `--no-programme-page-guard`, which removes all of PG-1 |
| 53 | `CANONICAL_HTTP_HTTPS` CU-1 (already row 2) | `90f9da55` | 39067189351 / 90840 | one navigation offered `http://…/<listing>` and `https://…/<listing>` on a Crawl-delay 10 host, so the same page was read twice | the comment named a heldout university (now generic) | no label; dev2 reads 345→326 (D2) | set (D2 reads) | guard (dedupe) | **general** (unchanged); off arm `--no-canonical-http-https` |
| 54 | `COST_AWARE_SEARCH_ORDER` SO-1 | `23f71b26` | **off** (no default-on run) | a slow host: Crawl-delay 10 s, every read ~10 s, search never reached (`search_calls = 0` in 8/8 repetitions) | commit cites the quarantined analysis; the comment cited heldout timings and named a heldout university (now generic) | — | — | recall (stage order) | **off — not counted**; its order code lives on inside SB-1 (row 9), so SB-1's slow-host branch inherits this provenance |
| 55 | `SITEMAP_CHILD_PRIORITY` SM-1 | `0305b0fb` | **off** (no default-on run) | a sitemap index that lists `post-sitemap1..24` before its page and programme sitemaps, so the document cap ran out on posts; Crawl-delay 10 hosts probing conventional locations after `/sitemap.xml` answered | commit cites the quarantined analysis; the comment cited heldout timings and named a heldout university (now generic) | — | — | guard (read order) | **off — not counted**; SM-2 (row 16) shares its stop-probing rule and `_SITEMAP_CHILD_FIRST`, so that part of SM-2 inherits this provenance |

Effect on the counts: none. Rows 52 and 53 sit inside rows 3 and 2, which keep their verdicts; rows 54 and 55 are off
by default. What changes is how a heldout result reads: PG-1, CU-1 and the SO-1/SM-1 code that SB-1 and SM-2 reuse
were designed with heldout traces in view, so dev5 (design-blind) is their only out-of-sample test.

## Counts

| verdict | rules | of which |
|---|---|---|
| **general** | **23** | 18 guards by construction (rows 1–3, 7, 8, 12, 14–18, 23–25, 34, 37, 38, 42); 5 recall rules with a gain in another set (LI-1, CL-1, QB-1, R1, R2), of which 3 are *weak* (LI-1, CL-1, R1) |
| **seen-site** | **17** | 15 pipeline rules (rows 9, 10, 19, 22, 26–33, 39–41); 2 scorer rules (rows 35, 36) |
| **unmeasured** | **11** | FI-1, IM-1 and 9 bug fixes (rows 43–51) |

What the counts show:

- **Every evidence-stage rule turned on since 2026-10-18 is seen-site:** DL-5, QP-1, QR-2, SQ-1, AP-1, EN-2,
  FE-2, DL-6, SC-2 and AN-1. Each one's gains are on the cases that motivated it, and none was run on dev4
  except DL-6 (no change there).
- **Of the discovery recall rules, only QB-1 and R2 have a gain in another set that was seen in more than one
  run.** For both, the outside case is auckland (D3) or kit (D4).
- **dev4 is the only out-of-set test any of them got.** dev4 shares the nine's countries but not their harness
  path (see H-B).
- **The register is incomplete.** `hypotheses.json` holds 10 entries (ER-01…ER-10), all cohort-era, with
  status 3 candidate, 3 rejected and 4 tested. **None of the 51 flags on since 2026-10-17 has an entry.**
- **Guards count as general by the ticket's construction, but they can still lose.** FS-2's first form cut
  auckland, and TB-1 cost ubc's deadline. "General" for a guard means "no seen-site vocabulary to overfit", not
  "harmless".

## Lexicon entries from one development case (feeds ticket 08)

An entry counts as single-case when the flag comment, the commit body or the analysis names exactly one
development case as its source.

| rule | entries added | single-case | named cases | not case-derived |
|---|---|---|---|---|
| LX-1 (`LEXICON_V2`, now inside R1/FI-1) | 16: 4 ontology aliases, ~7 degree words and slugs, 5 publication paths | **11**: informatikk (uio), datalogi (ucph), informàtica-ca (ub), ciencia de la computación (puc), B.Tech/BTech, M.Tech, b-tech/m-tech slugs (iitd), "grado en" (ub), publicaties (kuleuven), publikasjoner (uio), lirias (kuleuven) | licenciatura (uba + puc) | 4 (bachelorprogram/-studium, bachillerato en, publicaciones/publicación) |
| R1 ontology `LOCALIZED_PAGE_IDENTITY` | 19 aliases + 11 `related_not_equivalent` terms; the degree-word table for every `languages.json` language | **0**: "dictionary-grade aliases for every languages.json language" (commit d44d32d3), heldout countries' languages included by design (16-Q5) | — | all |
| R2 (ticket 19 shapes) | 9 form-filler words, 1 bracket filler, 8 related-field words, 4 shapes | **6**: studieprogramma (kuleuven), beng (imperial), btech (iitd), the subject-head-before-subtitle rule (uio), "X specialising in" (uct), "Mathematics and …" (imperial) | "<field> and Engineering" (delft + iitd, 19-Q4); bracketed place (kuleuven, generalised to the seed rows' cities) | 8 related-field words (owner's 19-Q4 list); studieprogram/-met, studiengänge, opleiding, 专业, 学科, "(International)" |
| R5 | no words of its own: it uses the ontology alias and R1's degree word | **0** words; its **query shape** was fitted on the M5 six (5/6), all of them development cases | — | — |
| CG-1 places | 29 | **2**: bengaluru, bangalore (unsw) | — | 27 |

That makes **19 entries from a single development case**: LX-1 11, R2 6, CG-1 2. R2 and LX-1 carry them. R1's
table and R5's query family carry no case words, but R5's shape was chosen on six development cases and gained
only within their sets.

## Re-measure order for 13's protocol

One `expert_paired` run per rule on **dev5 only**, aggregate off/on. Check `extra_args` before ordering the
runs: **no rule below has a negative form today.** Every flag in `evaluation/research/live.py` is
`store_true`, which can only turn a default-on flag on. So the worker adds `--no-<flag>`, using the
`argparse.BooleanOptionalAction` pattern three existing flags use (live.py:1695–1707), and the off arm becomes
`extra_args=--no-<flag>`.

Order: the nine's loss stages first (gold never returned, wrong confirms, query count), then evidence readers,
then awards, then the scorer.

| order | rule | why here | `extra_args` (worker adds the negative form) |
|---|---|---|---|
| 1 | R5 `LOCAL_LANGUAGE_QUERIES` | its shape was fitted on six development cases and gained only in their sets; gold never returned is the nine's largest loss | `--no-local-language-queries` |
| 2 | R6 `SITE_IDENTITY_V2` | gains only on the cases that motivated it; never measured on C or D4 through the gate; the production path for 481 universities | `--through-identity-gate --no-site-identity-v2` (both arms through the gate) |
| 3 | `ALIAS_AWARE_PROGRAM_MATCH` | a confirm predicate (wrong confirms are a heldout symptom named in the map) motivated and gained inside dev4 | `--no-alias-aware-program-match` |
| 4 | SB-1 `STAGE_BUDGETS` | discovery stop and order; no gain alone; plausibly tied to the low query count per case | `--no-stage-budgets` |
| 5 | QR-1 `QUESTION_ROUTED_EVIDENCE` | evidence routing; one unnamed-case gain (delft) | `--no-question-routing` |
| 6 | SC-2 `COORDINATED_DEGREE_SCOPE` | one case; degree scope (H-D) | `--no-coordinated-degree-scope` |
| 7 | DL-6 `INTERNATIONAL_ROUND_DEADLINE` | one case; adds a read | `--no-international-round-deadline` |
| 8 | EN-2 `ENGLISH_READERS_V2` | gains on its motivating cases only | `--no-english-readers-v2` |
| 9 | FE-2 `FEE_READERS_V2` | UK/Irish fee words; two cases | `--no-fee-readers-v2` |
| 10 | DL-5 `INTAKE_SECTION_DEADLINE` | two cases | `--no-intake-section-deadline` |
| 11 | QR-2 `PARENT_DEGREE_LINK` | one case; adds a read | `--no-parent-degree-link` |
| 12 | QP-1 `QUESTION_PAGE_ORDER` | no attributable gain | `--no-question-page-order` |
| 13 | AP-1 `AWARD_PAGE_EVIDENCE` | award claims (unmapped scholarship claims are a known heldout symptom) | `--no-award-page-evidence` |
| 14 | AN-1 `AWARD_NAME_QUALIFIER` | one case | `--no-award-name-qualifier` (AN-1b stays on: it is a guard) |
| 15 | SQ-1 `SCHOLARSHIP_INDEX_QUERY` | no gain; spends a query | `--no-scholarship-index-query` |
| 16–17 | ID-1 aliases, scorer acronym match | no run: re-score the dev5 captures with each scorer switch off and on | scorer switch |

Unmeasured rules need the same run once: FI-1 (`--no-funding-identity-scope`) and IM-1 (the worker adds the
flag's negative form). The weak general rules, LI-1, CL-1 and R1, are optional at the end of the queue, because
their outside evidence is one gain at the A/A noise floor.

What follows from 15:

- A seen-site rule that **loses** on dev5 is proposed for default-off.
- A rule with **no effect** on dev5 keeps its default and its *seen-site* label.
- A rule that **gains** on dev5 becomes *general*.
