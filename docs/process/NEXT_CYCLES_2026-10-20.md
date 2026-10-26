# Next cycles plan, 2026-10-20: cycles 14–16, all at $0

Planner, 2026-10-20, from the day-end replay baseline (loop report 17:55; seven rules on by default: UA-1, CH-1,
CQ-1, SP-1, CC-1, QT-1, CL-2), the SP-2 replay (no gain, stays off), SR-1 (`SCHOLARSHIP_ROUTE_2026-10-19.md`), W4
(`RECORD_RUN_2026-10-19.md`), the identity-gate audit (`IDENTITY_GATE_DEV5_2026-10-19.md`), the index ceiling
(`INDEX_CEILING_2026-10-19.md`), the seen-site ledger, the store `recorded_search.base3.json` and the code. Development
cases only: **no heldout file, capture, log or label was opened; no dev5 per-case row was used for design; no provider
was called; no credit was spent.** The two scripts used (store and lexicon inventories) are in the session scratchpad.

Constraints: paid search frozen; no free key yet (Q6 open); every rule designed on cohort/dev2/dev3/dev4 and code; dev5
design-blind (13-Q1, recommended, not yet signed — treated as binding); a rule goes on by default only under 13-Q2
(stable gain outside the motivating set or a guard by construction; dev5 aggregate not worse — unmeasurable until R2).

## 0. Where we stand, and what changed since the 2026-10-19 plan

| row | cohort | dev2 | dev3 | dev4 | all |
|---|---|---|---|---|---|
| gold pages hit / wrong / related / missed | 5/0/0/5 | 6/0/1/3 | 10/0–1/0/3–4 | 5/0/1/3 | **26/39**, wrong 0–1 (kuleuven flake) |
| knockout guesses (gold hidden) | 0 | 1 (tcd) | 1–2 (uio; kuleuven flake) | 1 (ctu) | 3–4 |
| precision · wrong scope · over budget | 1.0 · 0 · 0 | same | same | same | targets 1, 2, 5 met |

Since the evening plan: **SP-2** built and replayed, no gain on any set, stays off. **LL-1** built, flag off, **not yet
replayed**. **W4** landed (record run, v2 store builder, `columns=1`, tavily/brave choices) — R1 waits on the owner's key.
**SR-1** found seven one-set shapes and no two-set shape, so no reach rule exists to build. **The search log landed
after the outage** (`29e48cb9`, 2026-10-19), so no existing live capture carries titles or topic/scholarship lists: a v2
store cannot be built at $0 from anything on disk. Traces record `pages_read` as `(url, verdict)` without titles, so the
warsaw URL-only artefact (MISS_STAGES §0.1) has no $0 fix either. Owner answers: Q7 (KB caveats) yes; Q1–Q6, Q-SR1 and
13-Q1…Q5 still open.

## 1. The ranked list

Ranking = DoD rows moved or hypotheses closed per worker hour; dispatches cost no worker time and are ordered by the
information one batch returns. "Gain beyond the motivating set" is the 13-Q2 (a) question answered in advance.

| # | item | kind | worker h | runs | targets | why a gain is expected on a set that did not motivate it | expected outcome |
|---|---|---|---|---|---|---|---|
| 1 | **TW-1** twin / label hand-checks for Q1 (uct), Q2 (kuleuven), Q3 (tcd) | research, no code | 1.5 | 0 (one re-score) | misses 9, 10; knockout dev2 | none claimed: it is label honesty, not a rule | if signed: hits 26 → 28–29/39, normal wrong 0 everywhere, knockout 3–4 → 2 + flake, with **0 code** |
| 2 | **D-F** no-search floor: the 44 cases with `search_provider=none` | dispatch | 0 (+0.5 reading) | 4 | the live path beyond the KB today; a second "gold absent" condition for the guards | the guards were tuned with search present; a wrong page here is a guess shape no rule has seen | hits ≈ the index-ceiling row (3/10, 1/10, 6/14, 1/5); wrong pages pre-registered ≤ the knockout count (0/1/1–2/1) |
| 3 | **D-A** LL-1 replay, normal + knockout | dispatch | 0 | 8 | miss 11 (msu) | motivated by msu/kaznu/vut; a gain must appear on cohort or dev2 to go on | +0–1 (msu, unverified); honest expectation "recorded, stays off" |
| 4 | **D-B** H-B no-seed arm on the cohort (+ knockout) | dispatch | 0 | 2 | hypothesis H-B (generalisation 06) | the registry path is the one structural fact true of the nine and of the cohort only | partial verdict (lower bound; regime B: second pass unrecorded) |
| 5 | **ES-1** evidence-reach rows in `stage_summary` | harness (measurement) | 2 | 0 (re-run on day-end artifacts) | the 18 reach-lost labels (NEXT_CYCLES_10-19 §1.3); ticket 16; 15-Q3 | makes S1–S7 visible on dev5 (aggregates only) and on the R1 re-baseline — the only legitimate way a second set appears | the seven shapes become rows; no DoD row moves |
| 6 | **LV-1** lexicon battery: every language-keyed table covers every `languages.json` language; level words read right in all 25 | tests + dictionary rows | 1.5 | 0 (8 only if a dev-set language row changes) | H-D (ticket 16 item 2); countries no dev set covers | a per-language dictionary test touches no page; it finds gaps for kk, ca, sk, fi, ja, ko that no dev case can | H-D verdict; `ca` gap closed (`_LOCAL_BACHELOR_QUERY_WORDS`); 0 or more table rows |
| 7 | **IG bundle**: NN-1a native names (Wikidata proposal + signed overlay), NN-1b fold dotless-ı/ł/ø/ß in the gate, IG-2 CI gate probe | data + rule + tool | 5.5 (2.5 + 1.5 + 1.5) | 0 (CI probe jobs) | H-E residue: R6 fails conclusively on taltech (dev4) and 3 of 11 readable dev5; production entry for 500 catalogue rows | a data field and a Unicode fold carry no site word; `native_name` is the branch that fired nowhere because no record has one | gate residue 4/20 → 0 once rows are signed; the 15-Q2 second-look arm becomes credible |
| 8 | **LOCO-1** H-C offline: inventory with provenance, leave-one-language-out on the store and on hand-fetched dev gold pages | research | 3 | 0 | H-C (ticket 08 steps 1–2); the lexicon's generality | the test removes a language's own rows and reads the same language's cases | H-C confirmed / refuted / not testable, with numbers; LQ-2 proposal if confirmed (live-only) |
| 9 | **D-D** ablations of 12 default-on rules on replay (IM-1, alias, ten evidence readers) | dispatch | 0 | ≤ 48, idle runners | H-F detail; a harmful rule | an off arm with a *stable gain* means the rule costs development hits or claims — removing it is a guard by construction | most read identical (`no_dev_evidence`); any stable gain → a worker diagnosis |
| 10 | **D-C** gate floor: `--through-identity-gate` on cohort + dev2 replay | dispatch, optional | 0 | 2 | how many cases pass R6 from the homepage alone (no identity query) | floor only; IG-2 answers the same from outside the pipeline | `identity established n/N`; outcome rows ignored |

Not on the list, and why: §3 (reach rules, one-set each), §4 (rank rules, wrong-scope rules, the remaining knockout
guesses). Owner-dependent $0 items (no worker hours, not scheduled): §4.2.

## 2. The 13 misses: what each needs

| # | case | class | $0 rule? | free keys (R1)? | owner? | owner's PC as runner? |
|---|---|---|---|---|---|---|
| 1 | aalto | access (robots timeout) | no | no | no | maybe (vantage) |
| 2 | toronto | access (HTTP 403) | no | no | no | **likely** (403 class) |
| 3 | hku | access + cds form never returned | no | partly (6 queries for the cds form) | no | maybe |
| 4 | kaist | department host / opaque URL | no | no | **Q4** (residue) | no |
| 5 | warsaw | replay artefact (URL-only store) | no | **yes** (v2 store) | no | no |
| 6 | kaznu | access + never returned | no | optional | no | maybe |
| 7 | tec | classifier residue (DA-2) + Spanish gold never returned | no | partly (6 queries) | **Q5** | no |
| 8 | tsinghua | other registrable domain | no | **no** (no `site:` query returns it) | domain decision | no |
| 9 | uct | label question | no | no | **Q1** | no |
| 10 | kuleuven | twin question (+ host flaky) | no | no | **Q2** | partly |
| 11 | msu | never returned | no | **yes** (6, Russian family) | no | no |
| 12 | ntutw | never returned | no | **yes** (6, Chinese family) | no | no |
| 13 | ub | access (timeout, robots) | no | no | no | **likely** (403 class) |

**Verdict.** No miss is reachable by a rule the replay can measure. Truly unreachable without paid search *or* an owner
answer: all 13 — but the split matters: **owner answers alone** (no search) move uct, kuleuven, kaist-as-residue and
tec-as-residue (+2–3 hits on the readable denominator, wrong pages 0, knockout −1 with Q3); **free keys** (R1, inside the
free tiers, $0) move warsaw and can move msu, ntutw, hku-cds, tec's Spanish gold; **the owner's computer as runner**
(free-search 01-Q4, unconfirmed) is the only lever on the access five; **tsinghua** is reachable by none of them.

## 3. Reach for claims: can it be tested on the replay?

| shape (SR-1) | cases (set) | regime on replay | measurable? | two-set evidence? | decision |
|---|---|---|---|---|---|
| S1 client-rendered finder / listing | groningen, ntu (C) | C (award / index query) | no until a v2 store | — | wait for R1 |
| S2 no funding entry | ethz (D2) | C | no | — | wait for R1 |
| S3 award described on a walker-read page; gold on a news host | uba (D2) | A for the read, binding for the score | partly | one set | owner Q-SR1 (binding) |
| S4 hub of hubs; index budget spent on process pages | auckland (D3) | A (link following) | **yes** | one set | not built; re-opens on an ES-1 row from a second set |
| S5 funding index refused by TB-1; award links on a sibling official host dropped | unsw (D3) | A, but clock-bound | partly | one set | not built (TB-1 blocks the read anyway) |
| S6 local-language award page refused by the classifier | rwth (D4) | A | **yes** | one set; also 08-Q2 "no localized readers now" | not built |
| S7 programme twin with a funding block, returned and never read | taltech (D4) | A (store holds the list) | **yes** | one set | not built |
| topic-query labels (uppsala ×3, tcd ×2, ktu ×3, ntu ×2) | D2, D4, C | C | no until a v2 store | — | wait for R1 |
| fees pages | tuition labels on dev are hits or upstream; "costs pages fetched ok ≈ 0" is a heldout aggregate | — | ES-1 row `evidence_reach:tuition` | — | measure first |

Answer: **yes for the four regime-A shapes** (S4, S6, S7 fully; S5 partly), deterministic on replay — but each has
one-set evidence, so even a passing replay cannot turn one on (13-Q2 a). **No** for the query-reached labels until the
v2 store. Extraction is not the loss (2 of 59 missed labels were on a read page). So this plan builds no reach rule and
instead makes reach measurable per shape at aggregate level (ES-1), which is what lets dev5 or the R1 re-baseline supply
the second set without opening a per-case row.

## 4. Is the replay bench exhausted?

**For rule gains: yes, after the cycle-14 dispatches.** The v1 store (174 discovery requests, URLs only) has measured
every post-search rule with development evidence: the remaining misses need queries, access or labels (§2); the
remaining knockout guesses are one twin (tcd, Q3) and two one-set shapes (uio subtitle, ctu process-URL); the reach
shapes are one-set (§3); wrong scope is 0. What the v1 replay still measures honestly: guards and ablations (regime A),
the no-seed path (regime B, lower bound), the no-search floor, and any harness change.

### 4.1 What would unblock it

| unblock | who | cost | what it buys |
|---|---|---|---|
| **R1 record run** (`RECORD_RUN_2026-10-19.md` §2: 44 cases, `columns=1`, Exa, cap 264) | owner's free Exa key (Q6) | $0 inside the free tier | v2 store with titles and the topic/scholarship/identity lists → re-baseline (4 runs): warsaw `missed → hit`, 10 regime-C labels measurable, ticket 03's `gold_returned_by_search` row, the 51-query miss probe (msu, ntutw, hku-cds, second passes) |
| **R2 dev5 baseline** (cap 312, aggregates only) | owner's key + 13-Q1…Q5 | $0 inside the tier | 13-Q2 (b) for the seven rules flipped on 2026-10-19; ticket 14; the second set for S1–S7 via ES-1 rows |
| **Q1–Q5** signed | owner | 0 | +2–3 hits, knockout −1, wrong pages 0 (§2) |
| **Self-hosted replay of the access cases** (`runner=self-hosted`, `search_provider=recorded`) | owner starts the runner; 01-Q4 confirmed | 0 | aalto / toronto / hku / kaznu / ub enter or stay out of the denominator; five fresh sites for the guards (free-search 08) |
| Exa MCP keyless (≈ 50/day/IP) for the 51-query probe over two days | owner's go (01-Q3/Q8) | 0 | the miss probe only; a provider call, so outside this plan |

### 4.2 Owner-dependent, $0, zero worker hours (dispatch the day the answer arrives)

Self-hosted replay per set: cohort `aalto toronto hku` (reviewed11), dev2 `kaznu` (draft3), dev3 `ub kuleuven`, dev4
`unibo`; `search_provider=recorded`, `runner=self-hosted`, `extra_args` empty, `run_tag=rp-home-<set>`. Read: the
`access` cell per case, `programme_found_on_readable`, hit/wrong on any newly readable site (a wrong page there is a
guess on a site no rule has seen — it goes to the knockout table). R1 and R2 as written in `RECORD_RUN_2026-10-19.md`
and `NEXT_CYCLES_2026-10-19.md` §2.

## 5. The cycles

| cycle | dispatches (0 worker h) | worker tickets | gate / read |
|---|---|---|---|
| **14 (now)** | D-F no-search floor (4); D-A LL-1 normal + knockout (8); D-B no-seed + knockout (2) | **TW-1**, **ES-1**, **LV-1** (parallel, disjoint files) | D-F wrong pages vs the pre-registered bound; LL-1 verdict → `hypotheses.json`; H-B partial verdict → ticket 06 Answer; ES-1 table on the day-end artifacts; owner round re-sent as one table (§8) |
| **15** | D-D ablations as runners idle (≤ 48, IM-1 and alias first); D-C (2, optional); LV-1's replay only if a dev-set language row changed | **IG bundle** (NN-1a → NN-1b → IG-2, one worker, or NN-1a ∥ NN-1b), **LOCO-1** | H-C, H-D, H-E verdicts written into tickets 08, 16, 11; IG-2 CI probe table (dev4 per case, dev5 counts); ledger rows for every ablation |
| **16 (first owner-dependent)** | R1 (if a key) → v2 store → re-baseline (4); self-hosted access replay (if the runner); R2 (if key + 13-Q answers) | re-open S4/S5/S6/S7 only if ES-1 shows a shape on a second set; LQ-2 only if LOCO-1 confirms H-C | the loop returns to $0 per rule on the v2 store; otherwise the bench stays exhausted and the loop continues on ablations and the KB |

Expected after cycles 14–15 without the owner: hits unchanged at 26/39; verdicts for H-B (partial), H-C, H-D and H-E's
residue; the gate's data ready to sign; the no-search floor known. With Q1–Q5: 28–29/39, knockout 2 + flake.

## 6. Worker tickets

Common to every ticket: design on cohort/dev2/dev3/dev4 captures, the store and code; no dev5 or heldout page, label,
capture or row; word tables dictionary-grade for every `languages.json` language at once, no entry from a single page;
flag off by default with a `store_true` harness flag plus its `NEGATABLE_RULES` entry where a flag exists; HANDOFF §8
line; golden demo byte-identical (`UNIMATCH_DEMO_MODE=true UNIMATCH_ENABLE_BROWSER_TIER=false python seed_demo.py`,
brief §5.7 order); gates green; commit locally; the main session cherry-picks and dispatches. Effort `medium`.

### TW-1 — twin and label hand-checks (research worker, ≈ 1.5 h, no code)

- **Do:** through the production `Fetcher` rules (robots.txt first, production User-Agent, no override; dev cases):
  `sit.uct.ac.za/bsc-degrees` (what it lists; is there a CS entry page below it; is `ba-informatics` the BA of the same
  school), `www.kuleuven.be/programmes/opleidingen/bachelor-informatica` against
  `onderwijsaanbod.kuleuven.be/opleidingen/n/SC_51016742` (redirect, `rel=canonical`, hreflang, programme code),
  `tcd.ie/scss/courses/undergraduate/computer-science` against the gold (same course code / degree; canonical link).
- **Output:** `docs/process/TWIN_CHECKS_2026-10-20.md`: case → page A, page B, relation → recommendation (sign as
  `programme_url_aliases` twin / keep gold / `related`), plus proposal snippets for `dev2.draft4.json` and
  `dev3.draft4.json` **not applied**; the main session applies after the owner signs, as ticket 10 did (CI
  `verify_evidence` on the quotes).
- **Bar:** none (no pipeline change). Re-score the day-end artifacts with the new drafts: cohort identical; dev2 uct hit
  or related; dev3 kuleuven wrong → hit in its readable repetitions; knockout dev2 1 → 0.

### ES-1 — evidence-reach rows in the stage summary (harness worker, ≈ 2 h; loop id ES-1; no flag)

- **Change:** `backend/evaluation/research/stage_summary.py`: an `_EVIDENCE_CATEGORIES` table over
  `PageOutcome.detail` (a field the capture already carries and `stage_summary` does not read today) and the funding
  result's `errors` lines as the capture serialises them, same leak discipline as `_REFUSAL_CATEGORIES` (controlled
  lowercase categories only; a URL or title never becomes a row). Rows under `evidence`: `funding_index_zero_links`
  ("read as a funding index; 0 award links"), `index_beyond_budget` ("index page beyond the index budget"),
  `award_sections_read` (the "n awards read from its own sections" count), `funding_entry_none` (discovery selected no
  scholarships page: the candidate's funding URLs empty), `award_links_dropped_off_host` — today the drop in
  `web_scholarships._award_links` is silent, so add one counted diagnostics line to the result's `errors` there (no flag;
  claims and page outcomes byte-identical), `pdf_met:<stage>`; and a dataset-aware row `evidence_reach:<question>` = known
  labels whose evidence URL (any of them, `metrics._page_forms` variants) was fetched ok ÷ known labels, HTML only, with
  `evidence_reach_pdf:<question>` beside it (01-Q2 keeps PDFs out of the denominator).
- **Tests:** `backend/tests/test_stage_summary.py`: a synthetic capture with each detail string → the row counts; a
  detail string carrying a URL and a title yields the category only; the dataset-aware row on a synthetic dataset;
  `--summary-only` unchanged; `scorecard` output byte-identical (`tests/test_scorecard.py` untouched).
- **Dispatch:** none; the main session re-runs `stage_summary` on `rp-base3-{cohort,dev2,dev3,dev4}` and records the
  four tables in LOOP_REPORT. Pre-registered expectation from SR-1: `funding_index_zero_links` groningen, ethz, uba;
  `index_beyond_budget` auckland; `budget_refused:funding:award` unsw; `evidence_reach:scholarship_exists` the lowest row.
- **Why it generalises:** it is the instrument ticket 16 and 15-Q3 need; dev5 is read at aggregate level only, so an
  aggregate row is the only way dev5 can show the same shape as a dev4 case and lift a one-set shape to two sets.

### LV-1 — the lexicon battery (worker, ≈ 1.5 h; loop id LV-1; flag only if a dev-set language row changes)

- **Change:** new `backend/tests/test_lexicon_language_coverage.py`: (1) every language-keyed table (`_UNIT_WORDS`,
  `_SUBPAGE_YEAR_WORDS`, `_SUBPAGE_PROCESS_WORDS` in `live_discovery.py`; `_LOCAL_BACHELOR_QUERY_WORDS`,
  `_DEGREE_FIELD_LABELS`, the bachelor/master level words in `page_classifier.py`; the Bologna forms in `_DEGREE_SLUGS`;
  `ontology.localized_aliases_in("computer science", lang)`) has a row for every language `languages.json` names — today
  `_LOCAL_BACHELOR_QUERY_WORDS` lacks `ca`; (2) one synthetic programme page per language, dictionary title
  `<CS alias> — <bachelor word>` and the level in the slug → `classify_page` + `profile_rejects(page, "bachelor",
  ["computer science"], url, country)` accepts; the master variant is refused `degree_level_other`; the integrated-master
  word, where the language has one, reads as IM-1 says. Any failure is a table gap, closed in the same ticket from a
  dictionary (one cited source per row, in the table comment), in `page_classifier.py` / `live_discovery.py` /
  `ontology.json` (version bump).
- **H-D verdict (ticket 16 item 2):** a wrong level read in the battery = confirmed on development evidence; none =
  refuted for the level dimension.
- **Bar:** gates green, demo byte-identical. If a row changed for a language present in a dev set (any but `ca`): one
  replay per set normal + knockout (`rp-lv1-<set>`, `rp-lv1-ko-<set>`): no hit lost, 0 new wrong page, knockout
  `wrong_programme_pages` not up, `recorded_search_misses` (discovery) = off arm. A `ca`-only change needs no run (ub is
  unreadable).
- **Why it generalises:** no page is read; it tests the tables against dictionaries for languages no dev case speaks.

### IG bundle — the production identity gate for universities beyond the KB (≈ 5.5 h; H-E residue)

Context (`IDENTITY_GATE_DEV5_2026-10-19.md`): R6 passes 8/9 dev4 and 8/11 readable dev5 homepages; the four conclusive
failures (taltech; three dev5) all pass by `native_name` on the saved pages — a branch that fired nowhere because no
seed record carries a native name — and one trap: `dedupe.normalize` already folds combining marks but keeps letters
that have none (`ı`, `ł`, `ø`, `ß`), so an ASCII name never matches a Turkish title.

- **NN-1a native names (data, ≈ 2.5 h).** `backend/evaluation/research/wikidata_domains.py` gains `--native-names`: the
  same bounded SPARQL (≥ 1 s between requests, body cap, no redirects, heldout rows skipped before any query is built,
  catalogue names and countries only sent) also selects the official name (`P1448`) and the labels in the row's
  `languages.json` languages → `evaluation/research/data/catalogue_native_names.proposed.json` with a `review` block
  per row (`decision`, `reviewer`, `note`), applied nowhere. `backend/app/catalogue/importer.py` reads a **signed**
  overlay `catalogue_native_names.signed.json` (absent today → identical behaviour) into the seed record's
  `native_name`, which `catalogue.discovery._native_name_match` already consumes. Tests: `tests/test_wikidata_domains.py`
  (mock transport, new field, heldout skip unchanged), importer tests beside `tests/test_university_catalogue.py`
  (overlay absent → identical; present → `native_name` on the record; a row without a `decision: accept` is ignored).
  One line for the owner: confirm the SR-06 exception covers reading `P1448` (what is *sent* is unchanged).
- **NN-1b fold marks (rule, ≈ 1.5 h; `IDENTITY_FOLD_MARKS = False`, `--identity-fold-marks`).** `app/domain/dedupe.py`:
  `fold_letters(text)` mapping the letters NFKD leaves (`ı→i`, `ł→l`, `ø→o`, `đ→d`, `ß→ss`, `æ→ae`, `œ→oe`), applied in
  `catalogue/discovery.py` to both sides of `_native_name_match`, `_names_other_institution` and the `title_name`
  comparison when the flag is on. Tests in `tests/test_site_identity_v2.py`: synthetic homepages in tr, pl, no, cs, lt, de
  (title with the letter, record without) → pass on, fail off; off → byte-identical. Not a scorer change: ticket 04's
  experts label the recorded name form (the audit's scorer risk is a convention, not code).
- **IG-2 CI gate probe (tool, ≈ 1.5 h).** Workflow mode `identity_gate` in `.github/workflows/benchmark-capture.yml`
  (as `index_ceiling`: no provider), new `backend/evaluation/research/identity_gate_probe.py`: for every case id of the
  four dev sets and dev5, build the entry as `live.seed_entry` / `cohort_entry` do, fetch the homepage through the
  production `Fetcher`, run `CatalogueDiscoveryAdapter._identity_branch` with the fallback search disabled, print branch
  or refusal per case for cohort/dev2/dev3/dev4 and **counts only** for dev5 (leak guard as `stage_summary`'s); flags
  `--fold-letters`, `--native-names <file>` (the proposed file may be read by the probe for measurement; production reads
  only the signed one). Tests `tests/test_identity_gate_probe.py` (fake fetcher; dev5 aggregation; no dev5 id printed).
- **Dispatch:** `mode=identity_gate`, `extra_args` empty (today), then `--fold-letters --native-names <proposed>`.
  Pre-registered: today dev4 8/9 and dev5 8/11 (ticket 11); with both, 9/9 and 11/11; cohort/dev2/dev3 numbers are new
  (the live gate runs read 8/10 dev2, 12/15 dev3 *with* the identity query). D-C's replay arm is the same question from
  inside the pipeline and is optional once IG-2 reports.
- **Bar:** no pipeline behaviour until rows are signed; gate pass per dev case ≥ today's; 0 new "names another
  institution" refusals on the 20 homepages of ticket 11 (re-fetched); knockout and normal replays untouched (the
  benchmark bypasses the gate except under `--through-identity-gate`).
- **Why it generalises:** the gate is the first step of the live path for the 481 non-registry universities and for the
  second look's 15-Q2 arm; a data field and a letter fold carry no site word and fire on every language with the letter.

### LOCO-1 — H-C offline (research worker, ≈ 3 h, no code; ticket 08 steps 1–2)

- **Do:** (1) inventory per language of every word and shape in R5 (`intent.local_language_terms`), LX-1, the
  subject-title shapes, `LOCALIZED_IDENTITY` / `localized_aliases_in`, with the commit that introduced each row
  (`git log -S`) and any dev case the commit names; (2) leave-one-language-out on the store: for each non-English dev case
  with gold, which families returned the gold (the store says; gold only in `local_language` = query-side dependence) and,
  on the hand-fetched gold page (dev only; production User-Agent after robots.txt), whether `profile_rejects` still
  accepts it with that language's page-side rows removed (English twin, slug level) — regime A, no run; (3) reuse LV-1's
  synthetic battery as the control. dev5 titles are **not** read (13-Q1); INDEX_CEILING's per-language title/alias rates
  stand in (de 3/5, es 3/3, et 2/2, it 1/2, lt 1/2, cs 1/4, tr 0/4, th 0/2, zh 0/1).
- **Output:** `docs/process/LOCAL_LANGUAGE_LOCO_2026-10-20.md`; ticket 08's verdict rule: confirmed if gold-returned drops
  by ≥ 2 cases without a language's own words, refuted if ≥ 80 % survive; if confirmed, the LQ-2 proposal
  (`LOCAL_QUERY_FROM_PAGE_EVIDENCE`, `--local-query-from-evidence`) as written in ticket 08 — regime C, built only when a
  key exists.

## 7. Dispatch table (main session)

Common inputs: `benchmark-capture.yml`, `runner=ubuntu-latest`, `mode=expert_paired`, `columns=4`,
`seconds_per_case=120`, `max_pages=60`, `case_parallelism=5`, `search_provider=recorded`, `max_search_queries` empty.
Score cohort on `ground_truth.reviewed11.json`, dev2/dev3/dev4 on `draft3` with `--allow-drafts`; read
`recorded_search_misses` (discovery) before any outcome row. Case lists as in LOOP_PROTOCOL.

| run | set(s) | inputs that differ | `run_tag` | expected misses | read |
|---|---|---|---|---|---|
| D-F | each set | `search_provider=none`, `columns=1`, `max_search_queries` empty | `ns-floor-<set>` | n/a (no search) | hit/wrong/related/missed; `wrong_programme_pages` against the bound (0/1/1–2/1); `stage_summary` `confirmed_pages_wrong`, `reads_by_kind:sitemap`; one capture per case → variance ≈ 1 flip per set, record only. If the harness refuses `none` in expert mode, a 0.5 h fix precedes. Optional follow-up: the same with `--knockout-gold <set file>` in `base_args` if wrong pages exceed the bound |
| D-A | each set | `extra_args=--listing-follows-local-aliases` | `rp-ll1-<set>` | = off arm (regime A) | bar: msu `missed → hit` both on reps or unchanged; no hit lost; 0 new wrong page; default-on only with a gain outside dev3 — expected none |
| D-A ko | each set | `base_args=--knockout-gold <set file>`, same `extra_args` | `rp-ll1-ko-<set>` | ≤ +3 per knocked-out case with two recorded families | knockout `wrong_programme_pages` on the on arm not above the off arm's; knockout page recall 0 (no leaked hit) |
| D-B | cohort | `extra_args=--no-registry-seeds` | `rp-g06-noseed` | regime B: up to +3 (delft, groningen, vienna, ubc), +6 ntu | ticket 06 rows: families per case, `sitemap_urls_seen`, `identity_recovery_leads_confirmed`, `confirmed_pages_{hit,related,wrong}`, gold read/confirmed; verdict rule as 06 (≥ 2 cases, both reps); a lower bound (three readers keep registry knowledge) |
| D-B ko | cohort | `base_args=--knockout-gold ground_truth.reviewed11.json`, `extra_args=--no-registry-seeds` | `rp-g06-noseed-ko` | as above | does the no-seed path guess more with the gold hidden |
| D-D | each set, one rule at a time | `extra_args=--no-<rule>` for `integrated-masters-level`, `alias-aware-program-match`, then `english-readers-v2`, `fee-readers-v2`, `intake-section-deadline`, `parent-degree-link`, `question-page-order`, `award-page-evidence`, `award-name-qualifier`, `funding-identity-scope`, `coordinated-degree-scope`, `international-round-deadline` | `rp-abl-<rule>-<set>` | = off arm | `--summary-only`: identical arms → ledger `no_dev_evidence`; a stable **gain** on the off arm → worker diagnosis (the rule costs development hits or claims); a stable loss → load-bearing, keep. The evidence readers run in the degraded regime (topic search dead): aggregate read, no default change from an ablation alone |
| D-C (optional) | cohort, dev2 | `extra_args=--through-identity-gate` | `rp-gate-<set>` | regime C on the identity query (expected) | `identity established n/N` only; outcome rows ignored |
| LV-1 (conditional) | each set | `extra_args` = LV-1's flag, normal and knockout | `rp-lv1-<set>`, `rp-lv1-ko-<set>` | = off arm | §6 LV-1 bar |

## 8. Owner round (batched; everything above proceeds without it)

| # | question | recommendation |
|---|---|---|
| Q1–Q5 of 2026-10-19 | uct label, kuleuven twin, tcd twin, kaist residue, tec residue | as written there; TW-1 delivers the page facts for Q1–Q3 first |
| Q6 | Exa and Tavily keys (free-search 01-Q3) → R1, R2 | yes; the only unblock for warsaw, msu, ntutw, the topic labels and dev5 |
| Q-SR1 | bind `uba.ar/becas-grado` as a second source of uba's award | yes, after a worker reads the page against the note |
| 13-Q1…Q5 | dev5 blindness protocol, default-on bar, LOCO prediction, per-rule dev5 runs, when dev5 opens | «да» as recommended; needed before R2 |
| 01-Q4 | the owner's computer as self-hosted runner (same agent, same robots, no retries) | yes; it is the only lever on the access five, at $0 |
| new | the SR-06 Wikidata exception also covers reading the official-name property (`P1448`) in the same bounded query | yes (nothing new is sent) |
| new | sign `catalogue_native_names.proposed.json` rows (NN-1a) and the 142 `P856` domain proposals, row by row | when convenient; until then production behaviour is unchanged |

## 9. What this plan does not change

DoD targets and denominators (targets 3 and 4 stay "not met" on development); the 6 / 60 / 120 budget; no rule on the
access, other-registrable-domain or department-host classes (01-Q4 stopping rule); no rank rule fitted to the URL-only
store; no one-set shape built (13-Q2 a); no reach rule and no localized evidence reader (08-Q2); no heldout look and no
number about the nine; model extraction stays outside every map here (18-Q2 c). The seven rules flipped on 2026-10-19
keep their defaults until R2 gives the dev5 reading they were flipped without.
