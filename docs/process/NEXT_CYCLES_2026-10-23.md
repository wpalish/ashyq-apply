# Next cycles plan, 2026-10-23: cycles 22–24, all at $0 and without the owner's answers

Planner, 2026-10-23, from the cycle 19–21 record (`LOOP_REPORT.md` 2026-10-20 06:45 → 09:15), `NEXT_CYCLES_2026-10-22.md`
(what closed, §0), `NO_SEARCH_FLOOR_2026-10-21.md` §7–§8 (CO-1 step 1, FRH step 1 and its step-2 spec §8.5),
`INDEX_CEILING_2026-10-19.md`, `SECURITY_REVIEW_2026-10-22.md`, `RELEASE_CHECKLIST.md` (counted on `87453b32`),
`EVIDENCE_GENERALISATION_2026-10-21.md` (the FR-3 sizing), `I18N_RESULTS_2026-10-19.md` §"Still English after I18N-2",
`KB_REFRESH_2026-10-19.md`, `KB_E2E_SMOKE_2026-10-19.md`, `PERF_2026-10-22.md`, HANDOFF §8, the five wayfinder maps,
the committed KB v22, the CI and `benchmark-capture` run lists of the branch (read through `gh`, counts and job names
only), and the code at `b4c0dd39`. Development data only: **no heldout file, capture, log or label was opened; no dev5
per-case row was read; no other scratchpad was read; no provider was called; no credit was spent.** The only numbers
computed here were read from committed files, `git` and the CI job list.

Constraints, unchanged: paid search frozen; no free key (01-Q3 / Q6 open); dev5 design-blind (13-Q1); a rule goes on by
default only under 13-Q2; the 6 / 60 / 120 budget; no PR unless the owner asks; model identifiers stay out; the nine
heldout universities are never opened.

## 0. Where we stand after cycles 19–21

| row | cohort | dev2 | dev3 | dev4 | all |
|---|---|---|---|---|---|
| recorded replay, today's defaults (LV-1, AW-2, NS-1b, PC-1 on): hit / wrong / related / missed | 5/0/0/5 | 6/0/1/3 | 10/0–1/0/3–4 | 5/0/1/3 | **26/39**, wrong 0 (+ kuleuven flake) |
| **no search provider**, today's defaults (NS-1b + PC-1 on, LOOP_REPORT 09:15) | 4/0/0/6 | 2/0/1/7 | **5**/0/0/9 | **1**/0/0/8 | **12/39**, wrong 0 |
| own-index ceiling (`INDEX_CEILING`; psaclay and tcd are found beyond it) | 3 | 1 | 6 | 1 | 11/39 |
| knockout guesses (gold hidden) | 0 | 1 (khalifa) | 1 (uio) + flake | 1 (ctu) | 3 + flake |
| precision · wrong scope · over budget | 1.0 · 0 · 0 | same | same | same | targets 1, 2, 5 met |

What closed since the 2026-10-22 plan:

| item | outcome |
|---|---|
| PC-1, NS-1b | **on by default** (`SITEMAP_STAGE_CAP`, `HOMEPAGE_HOP_READS`): the 06:45 verdict was a column misreading (the scorecard's columns are off#1, off#2, on#1, on#2); re-read, puc and iitd gained on dev3, kit on dev4, 0 wrong, knockout and recorded guards identical → no-search floor 9/39 → **12/39** |
| RM-1 | merged: `live_coverage` is `mode: "kb"` in kb mode (95 of the catalogue's universities answer), `kb-mode-notice` in en/ru/kk; gate 79 recounted |
| RC-1 | merged: ledger recounted on `87453b32` — 96 PASS, 2 PARTIAL (87, 92), 2 BLOCKED (29, 94); gate 97 PASS on two green `release-gates` runs; gates 98–100 added with command output |
| CO-1 step 1 | **not shared**: auckland's gold is ranked 26/40 in the confirm queue (reverse-alphabetical tie, level hidden by `.html`); khalifa's gold is not in its sitemap at all. V1 (selection order) reaches auckland alone; the two-set shape is "a refused hub's links are never followed" (§7.5) → FRH |
| FRH step 1 | **bar met, by the strict shape only**: a refused listing hub whose URL or head names the field, its own children first, ≤ 3 follows a case, stop once a programme page is confirmed → khalifa (dev2) and auckland (dev3) in 5/5 no-search captures each, 0 non-gold page confirmed on any of 569 captures. The plain best-link shape reaches one set; the label-only shape confirms a wrong BSc(Hons) page on auckland. Step-2 spec: NO_SEARCH_FLOOR §8.5 |
| SEC-2 | `SECURITY_REVIEW_2026-10-22.md`: two Highs fixed (SR2-01 `<html lang>`, SR2-02 the discovery tag scans — both quadratic on page text), SR2-03 (self-hosted runner on a public repo) mitigated in repo and left for the owner, four Lows fixed; SR2-09's `index_ceiling` half fixed with IC-2, its `site_search` half open |
| I18N-2 | merged: requirement checks, award reasons, ranking reasons, conflicts and the Documents screen in ru and kk; what stays English is listed in I18N_RESULTS §"Still English after I18N-2". **It also turned CI red (§0.1)** |
| PERF-1 | kb catalogue p50 33 ms a page, KB load 17 ms, nine-university kb run 2.1 s, JS 169.3 kB gzip; `npm run build` fails over 200 kB gzip JS / 35 kB CSS |
| KB-1 | `merge_entries` compares on `verified_on` then `accessed_on`; a built access note survives an import with no page; committed merged view byte-identical |
| SG-1 | built (`SITEMAP_GUESS_RULE`, off); the five replay runs finished at 10:20 (`sg1-cohort/dev2/dev3/dev4`, `rp-sg1-dev4`): **verdict not yet read** (§4) |
| IC-2 | tool landed (`hop1_parent`, `hop1_anchor`, `hop1_rank`; linear `<html lang>` scan); the `mode=index_ceiling` run 39408839839 is in flight; the report and the rank table are not committed (§3 IC-2b) |
| G-16a item 3 (costs) | the 34 costs-stage no-figure reads classified: 24 correct (no fee for this population), 9 unparsed shapes, 1 wrong year; **none costs a labelled tuition claim on any set → FR-3 not built, CX-1 step 2 closed** |
| TR-1 | **in flight** (trace rows `confirm_queue`, `sitemap_keep`, `navigation_queue`, `host_cost.samples`; scorecard `gold_confirm_rank`); holds `live_discovery.py` |
| D-F5 | the dev5 no-search floor ran (39408880008, `search_provider=none`, one column): **aggregates not yet read** against the pre-registration (§4) |

### 0.1 CI is red, and it is not a flake

`release-gates` run 39405712087 on `e48fd3d6` (a docs-only commit) failed in the `frontend` job at `npm run e2e:kb`:
`kb-journey.spec.ts:334 › ru: the shortlist cards, the four detail tabs and the documents screen`, "Expected substring:
`verified, some items not current`", received the Documents screen in Russian ("проверено, часть пунктов не актуальна").
Lines 551–557 of the spec assert five hard-coded English strings on the Documents screen for every locale (`verified,
some items not current`, `from the verified knowledge base`, `allow ~1 day`, and the negatives `partially read`, `~1
days`), while every other assertion in the file goes through `wordsFor(locale)`. I18N-2 (`f635e477`) localised that
screen, so the ru test fails and the kk test, which the runner skipped after the first failure, will fail the same way.
The two runs in flight (`d4c31727`, `b4c0dd39`) are expected to fail identically. The last green run is 39405494090 on
`dd5e7a14`, the commit before I18N-2. **Gates 2, 97 and 98 read PARTIAL until E2E-KB-2 (§3) lands and a run is green.**
This is a 30-minute fix and the first ticket of cycle 22.

**Three benches, where each is.** The recorded replay is exhausted for rule gains (§2.1, unchanged). The **no-search bench**
is at 12/39, one rule (FRH) above its measured ceiling with a two-set, pre-registered expectation of +2; after it the bench
is exhausted at $0 (§2.2). The **product in kb mode** is the launch path: its journey is walked in CI, its ledger is counted,
and what is left is hygiene a worker can do without the owner — a red test, a container stack that has never run kb mode,
an export that calls KB facts "live official sources", fourteen KB quotes the page no longer prints, and the README that
does not mention the mode the product ships in.

## 1. The ranked list

Ranking = expected movement (a launch gate, an applicant-visible correctness fix, a DoD row on a two-set cause) per worker
hour. Dispatches cost no worker time and are in §4. "Why it pays" is the 13-Q2 (a) question, or the launch question,
answered in advance. Effort `medium` unless marked. File ownership is in §3; the parallel groups in §5.

| # | item | kind | worker h | runs | what it moves | why it pays on a set, or a screen, that did not motivate it | expected outcome |
|---|---|---|---|---|---|---|---|
| 1 | **E2E-KB-2** the kb journey asserts the locale's words on the Documents screen | test fix | 0.5 | 0 (CI) | **CI green again**; gates 2, 97, 98 back to PASS | every push since `f635e477` is red; nothing else in this plan can cite a green run until it lands | lines 551–557 go through `wordsFor(locale)`; `e2e:kb` 8/8 on CI |
| 2 | **FRH-2** follow a refused hub's field link (after TR-1) | pipeline, effort **high** | 3.5 | 12 | target 3 without a key: no-search **12/39 → 14/39** (khalifa related → hit, auckland missed → hit) | two sets by measurement (NO_SEARCH_FLOOR §8.3: 5/5 captures each, 0 wrong on 569 captures); structural (a page class, an order, a cap), no word | both gains in ≥ 3 of 4 columns, knockout and recorded guards identical → default-on; else `hypotheses.json` and the bench is declared at 12/39 |
| 3 | **CS-1** the container stack runs the kb launch path, in CI | infra + CI | 3 | 0 (CI) | launch readiness: gate 22 proved a **demo** run through web → api → worker on 2026-09-06; no container has ever completed a **kb-mode** run, and `docker-compose.yml` defaults to demo mode | the stack the owner would deploy is the one thing no gate exercises in the mode the product ships in; GitHub runners have Docker, so the proof can be automatic | `verify_compose.sh` runs a kb-mode run (`pages_checked` 0, `knowledge_mode` kb, a non-KB university answers "No verified data yet"); a `compose-stack` CI job; gate 101 |
| 4 | **KB-2** the fourteen KB facts whose quote the page no longer prints | KB maintenance | 3 | 0 (sandbox reads through `Fetcher`) | correctness of what is served: gate 99 found **14 of 999** records "read but the quote not found" (NUS documents 6, CityU documents 5, Auckland tuition 1, Paris-Saclay "no English test" 2); the product still shows them as verified on their old date | not a manual round for new facts (§2.3): these are facts already on screen whose evidence drifted; none is on a heldout or dev5 university | v23 with the 14 re-quoted or marked `unverified quote`; `KB_REFRESH_2026-10-23.md` committed; the journey's nine universities untouched |
| 5 | **A11Y-KB** axe, keyboard and 390 px on the kb journey in en/ru/kk | e2e test | 2 | 0 (CI) | launch readiness: gate 21's axe scan runs the **demo** journey in English only; the kb screens (CAT-1 chips and filter, WHY-1 rows, the kb notice, the Documents screen) and the longer ru/kk strings have never been scanned or squeezed to a phone width | the audience reads ru/kk on phones; a horizontal scroller or an unlabelled chip there is invisible to every current gate | `kb-accessibility.spec.ts` in `e2e:kb`: 0 serious violations, no horizontal scroll at 390 px, the catalogue filter and tabs reachable by keyboard, in three locales; gate 102 |
| 6 | **EX-1** the export says a KB fact comes from the knowledge base | product (export) | 1.5 | 0 | applicant-visible correctness: `tabular.py` writes `data_origin` = "live official sources" for every non-fixture row, so a kb-mode CSV/XLSX calls a verified-on-2026-10-19 KB quote a live read; the JSON export and the Sources screen already name the KB | the export is what a school adviser keeps; a wrong origin column outlives the screen | `data_origin` = "verified knowledge base (official sources, checked <date>)" for KB rows, live and fixture rows unchanged; 3 tests |
| 7 | **DOC-1** the README and ONBOARDING say what the product ships as | docs | 1.5 | 0 | launch readiness: README documents demo and "Live mode" and 11 env rows; `UNIMATCH_KNOWLEDGE_MODE` (default `kb`) and `UNIMATCH_SEARCH_PROVIDER` (default `none`) are not in it; the launch path is described only in `docs/process/KNOWLEDGE_BASE.md` | the README is the first page a deployer or a reviewer reads | a "Modes" section (kb / live / demo), the two env rows, the refresh workflow and the owner's KB exception linked; ONBOARDING's first-session list names kb mode |
| 8 | **SEC-3** the three small items SEC-2 left | security hardening | 1.5 | 0 | `extraction.pdf_to_text` keeps a 40-page cap but no time cap (`pdf_document.read_pdf` has both); `wikidata_domains._qid` passes an unvalidated id into the next query (SR2-10); `site_search.py` still carries the SR2-01/02 quadratic patterns (SR2-09, unreachable today) | each is ≤ 30 min with a test; none changes a label | three tests; HANDOFF §8 line for the PDF cap |
| 9 | **MODE-1** gate 79's uncovered case | product (API + UI) | 1 | 0 | a demo-mode server whose `knowledge_mode` is kb shows the **live** notice when the applicant unticks demo, although the run then goes kb (`runner.kb_mode = not demo and knowledge_mode == "kb"`) | the compose stack defaults to demo mode today (CS-1 changes that), and every developer sandbox does | additive `kb_coverage` in demo mode; `PreferencesScreen` picks the kb notice; the pinned demo/live responses unchanged |
| 10 | **LG-1** the hypotheses ledger catches up | docs (data) | 0.5 | 0 | the DoD says a rule that fails twice is recorded in `hypotheses.json`; CO-1 V1/V2, FR-3, SH-1, LL-1 and the NS-1b/PC-1 flip are in prose only | the next planner reads the ledger, not five documents | six rows with their re-open triggers; SG-1's row once its verdict is read |
| 11 | **IC-2b** the ceiling report committed, the rank table written | measurement (docs) | 1 | 0 (run in flight) | NO_SEARCH_FLOOR §2's "rank" column came from a scratch probe; CO-1 found the khalifa "bounded, hop 0" row does not reproduce | the next no-search ticket reads a committed report | `index_ceiling.dev-2026-10-22.json` (dev5 aggregates only), the rank table and the khalifa correction in `INDEX_CEILING_2026-10-19.md` |
| 12 | **CM-1** a moderation runbook beside the community guidelines draft | docs | 1 | 0 | gate 96 says "community rules and a moderation SLA are not written"; `LegalScreen` already carries "Community guidelines (draft)", the runbook does not exist | the report queue (gate 96) has a reader but no written procedure | `docs/MODERATION.md`: what a moderator does with a report, in what time, what is logged; marked draft like gate 87's texts |
| 13 | **RC-2** the ledger re-counted after cycles 22–23 | docs | 2 | 0 (CI) | gate 2 (the red run and its fix, with the green link), 3, 15–16 dates, 92 (I18N-2's list), 96 (CM-1), 99 (KB-2), 101–102 new, the summary | a ledger that says 96 PASS while CI is red is a wrong ledger | every row cited with today's output; counted on the branch head |

Not on the list, and why: §2 (the exhausted benches and rounds), §7 (rules that would gain 0 on any bench today, and the
one-set rule CO-1 V1 that FRH supersedes).

## 2. What is exhausted, honestly

### 2.1 The recorded-search replay, for rule gains: exhausted (unchanged)

No rule since AW-2 has had a plausible gain on it, and none is proposed here. It runs guard arms only in cycles 22–24
(FRH's `rp-frh-*`, the optional D-D interaction check). The 13 misses keep their classes (NEXT_CYCLES_2026-10-20 §2).

### 2.2 The no-search bench: one rule from done, then exhausted too

| cause (NO_SEARCH_FLOOR §4, §7.5) | sets | status |
|---|---|---|
| navigation fallback never reads the hop-1 study page | dev3 (puc, iitd), dev4 (kit) | **closed**: NS-1b + PC-1 on, 3 gained |
| a refused hub's links are never followed (confirm on auckland, walker on khalifa) | dev2, dev3 | **FRH-2**, this plan |
| confirm-queue order (reverse-alphabetical tie) | dev3 (auckland) only | one set by measurement; superseded by FRH on the same case (§7) |
| read and refused in a catalogue role | cohort (kaist, behind a seed; its refused pages link the gold only as "교육") | one set; no word-free rule reaches it; not built |
| clock on a reachable gold | none | the clock cases (uio, ctu, ubc, uppsala) are all unreachable golds; SG-1 may cut ctu's seconds, not its outcome |
| trimmed on a reachable gold | none | — |

After FRH the bench sits at 14/39 if both gains hold, 12–13 otherwise. The remaining 25 cases are, by class: access from
every vantage point we have (aalto, toronto, hku, kaznu, ub, kuleuven), golds on a department or catalogue host the homepage
never links and no sitemap we read lists (kaist, ntutw, msu, um, unibo, ktu, chula, usp, warsaw), another registrable
domain (tsinghua), sites with no usable sitemap and a gold deeper than two hops (ethz, tcd, groningen's 5 MB document,
delft), catalogue picks without the programme (tec, uba, uct, rwth), and the four clock cases above. **None is a $0 rule.**
Every one needs a key (search), a vantage point (the owner's computer, 01-Q4) or a different product decision. When FRH's
verdict is read, §5's cycle 24 writes this residue by class into LOOP_REPORT and the bench is declared exhausted.

### 2.3 KB manual rounds: still stopped — KB-2 is maintenance, not a round

The pool is unchanged (60 not published, 63 access, 47 not researched); RP-1's 105 URLs wait for the owner's computer.
KB-2 re-quotes facts the product already serves whose evidence drifted; it adds no fact from a new page. The two owner
flags (`--yearless-deadlines-with-caveat`, `--standing-fee-policy-current`: ETH, EPFL, FU Berlin, Heidelberg, UZH, KTH,
Lund, IP Paris, Osaka, Nanjing, Kyoto, ISCT) stay off until answered (§6).

### 2.4 The kb-mode smoke gaps: closed, except the owner's

As the 2026-10-22 plan §2.4: U7, U9, B7, D7, P3, P4 are owner decisions; P1, P5 done; P7 one set. Nothing new opened.

### 2.5 Localisation: at its $0 floor

I18N-2 templated what can be templated. What stays English (I18N_RESULTS §"Still English after I18N-2") is the page's own
scope words (`published_scope`), parameters as the university wrote them, document names, a v1 score explanation that kb
mode never shows, the on-purpose admissions e-mail, and the 11 glossary-reserved shell keys. The next step is a person
who advises applicants in ru/kk settling `docs/i18n/GLOSSARY.md` (gate 92) — not a worker ticket.

### 2.6 Rules and research with nothing left to do at $0

LQ-2a (built; needs a key). LOCO-1 / NN-1 / IG-2 (need the overlay signature). S4, AI-1, AW-1, SH-1 (recorded, triggers
written). D-D ablations (complete). G-16a (done; FR-3 not built). CX-1 (closed on FR-3). The twin checks (signatures
pending). The own index as a provider (closed on the ceiling; IC-2b only records), Common Crawl (owner exception), the
model hint (design only).

## 3. Worker tickets

Common to every ticket: design on cohort/dev2/dev3/dev4 captures, the KB files and code; no dev5 or heldout page, label,
capture or row; word tables dictionary-grade for every `languages.json` language at once; a pipeline flag is off by
default with its `NEGATABLE_RULES` entry; a HANDOFF §8 line for any contract change (§8 is append-only, so the main
session resolves the mechanical conflict at cherry-pick); golden demo byte-identical (`UNIMATCH_DEMO_MODE=true
UNIMATCH_ENABLE_BROWSER_TIER=false python seed_demo.py`, brief §5.7 order); gates green (AGENTS §5); commit locally with
the `Agent:` trailer; the main session cherry-picks, runs the suite and dispatches. `runner.py` and `scoring.py` are
touched by no ticket here. **`live_discovery.py` is held by one worker at a time: TR-1 (in flight) → the SG-1 default
flip, one line, by the main session at cherry-pick if §4 reads its bar met → FRH-2.** No two tickets below own the same
file; `RELEASE_CHECKLIST.md` belongs to RC-2 alone and is touched last.

### E2E-KB-2 — the kb journey asserts the locale's words on the Documents screen (e2e worker, ≈ 0.5 h)

- **Change.** `frontend/e2e/kb-journey.spec.ts` lines 551–557 only: replace the five literals with the dictionary
  (`w.t('detail.docs.kb.partial')`, `w.t('detail.docs.kb.official')`, `w.tn('detail.docs.leadTime', 1)`; the negatives
  through the keys the Documents screen uses for "partially read" and the singular/plural lead time, read from
  `i18n.results.ts`, never a literal). Nothing else in the file moves.
- **Tests.** `npm run e2e:kb` locally (ports 5173/8099 free; the harness's own scratch dir), 8/8 in en, ru and kk; then
  the CI run of the commit, cited by id in the commit message.
- **Bar.** Green `release-gates` run on the branch head; that run id goes to RC-2's gate 2 beside the red one.
- **Owns.** `frontend/e2e/kb-journey.spec.ts`.

### FRH-2 — follow a refused hub's field link (pipeline worker, effort high, ≈ 3.5 h, 12 runs; after TR-1)

- **Spec.** NO_SEARCH_FLOOR_2026-10-21.md **§8.5, verbatim**: `FOLLOW_REFUSED_HUB_LINK = False`,
  `FOLLOW_REFUSED_HUB_LINK_CAP = 3`; the pure helper `refused_hub_lead(...)` in `catalog_walker.py` next to `score_link`
  (children first, then `-score`, then URL; exactly one link per hub); the two call sites (`_confirm_programs` in the
  `reason is not None` branch after the R2b / SP-1 / LI-1 insertions and outside `MAX_PROGRAM_CANDIDATES_CHECKED`;
  `CatalogWalker._read_lead` through the optional `follow` callable, outcome `hub_link_<…>` never `reads_as_*`); the
  trigger (refused, listing `page_type` in `_LISTING_PAGE_TYPES`, URL or head names a requested field); the stop
  (nothing confirmed yet, follows under the cap, `not self._spent()`); one network read per follow inside SB-1, the
  60-read ledger and the case clock, no retry; trace `refused_hub_links` written only when non-empty.
- **Sequencing.** Rebase on TR-1's trace rows; record in `confirm_queue` that a follow happened. If the SG-1 flip landed
  in between, rebase on that one line too.
- **Tests.** `backend/tests/test_follow_refused_hub_link.py` as §8.5 lists them (confirm shape, walker shape, trigger,
  link filters, order and cap, refused follow, the three budget files with the flag off and on, the R2b / SP-1 tests
  with the flag on, `seed_demo.py` byte-identical). Synthetic hosts only; no development page's words.
- **Dispatch (§4).** `search_provider=none`, `columns=4`, `--follow-refused-hub-link`: `frh-<set>` ×4, `frh-ko-<set>` ×4;
  `search_provider=recorded`, same flag: `rp-frh-<set>` ×4.
- **Pre-registered expectation.** dev2: khalifa related → **hit** 4/4 (walker lead 1 → the gold; `zmu` no longer read).
  dev3: auckland missed → **hit** 4/4 (confirm read 1 → `…/computer-science/undergraduate.html`); imperial, ucph, unsw,
  puc, iitd unchanged. cohort, dev4: no outcome change; follows there are refused reads, ≤ 3 a case (tcd; taltech,
  vut, unibo, rwth). Knockout: no outcome change, `wrong_programme_pages` unchanged. Recorded guard: identical outcomes
  (uct may also return the labelled-related `ba-informatics`), `recorded_search_misses` equal. Total no-search **+2**,
  0 wrong.
- **Bar.** No hit lost on any set; 0 wrong pages; knockout not up; a stable gain on **both** dev2 and dev3 in ≥ 3 of 4
  columns; recorded guard identical or better. Then default-on. A page confirmed through a follow that is neither gold
  nor labelled related is a **stop**: diagnose before any default change. Fails → `hypotheses.json` with the §8.2/§8.3
  rows, and §7's CO-1 V1 opens under a one-set bar only if auckland failed while khalifa passed.
- **Owns.** `backend/app/adapters/discovery/live_discovery.py`, `backend/app/adapters/discovery/catalog_walker.py`,
  `backend/evaluation/research/live.py`, `backend/tests/test_follow_refused_hub_link.py` (new).

### CS-1 — the container stack runs the kb launch path, in CI (infra worker, ≈ 3 h)

- **Change.**
  1. `docker-compose.yml`: `UNIMATCH_KNOWLEDGE_MODE: ${UNIMATCH_KNOWLEDGE_MODE:-kb}` and
     `UNIMATCH_SEARCH_PROVIDER: ${UNIMATCH_SEARCH_PROVIDER:-none}` on `api` and `worker`; `UNIMATCH_DEMO_MODE` defaults
     to `false` (the production-like stack ships the launch mode; a demo run is still a per-run choice, as
     `verify_compose.sh` already makes it). `fly.toml`: `UNIMATCH_KNOWLEDGE_MODE = "kb"` written explicitly (it is the
     code default, so no behaviour changes; the owner deploys, the file is the record). Both `.env.example` files gain the
     two rows.
  2. `scripts/verify_compose.sh`: after the demo run, a **kb-mode run**: `demo_mode: false`, two universities picked
     from `GET /api/universities?verified=true` and one with `knowledge.has_verified_data` false (or a non-KB catalogue
     row); wait for `awaiting_user_decision`; assert from `GET /api/runs/{id}` that `settings.knowledge_mode == "kb"`,
     `pages_checked == 0` and every `fetch_tiers` count is 0; assert the non-KB row's blocking question starts with
     "No verified data yet"; assert `GET /api/meta/live-coverage` (or the route `routes_meta.live_coverage` serves) says
     `mode: "kb"`. The script's network fence: the compose network already has no proxy; add
     `HTTP_PROXY=http://127.0.0.1:9` to the two services in the CI override only (`docker-compose.ci.yml`), so a stray
     read fails rather than succeeds.
  3. `.github/workflows/ci.yml`: a `compose-stack` job on `ubuntu-latest` (Docker is on the image) that runs
     `POSTGRES_PASSWORD=ci-only-not-a-secret scripts/verify_compose.sh` and uploads the compose logs on failure. It is a
     push/pull-request job, so `backend/tests/test_workflow_runners.py` holds it to a hosted image by construction. The
     `security-and-containers` build step stays (it is faster and fails earlier).
  4. `docs/DOCKER_VERIFICATION.md`: the kb-mode section with the first green run's output.
- **Tests.** The script is the test; a `bash -n` and shellcheck pass if available; `test_workflow_runners.py` unchanged
  and green; `test_payments_config.py` / settings-dump tests unchanged.
- **Bar.** The CI job green twice; the demo path of the script unchanged (gate 22 stays as recorded); no secret in the
  job; the stack's `/api/health` still `ok`. Gate 101 text for RC-2: "the container stack completes a kb-mode run with
  no page read, on every push".
- **Owns.** `docker-compose.yml`, `docker-compose.ci.yml` (new), `fly.toml`, `backend/.env.example`,
  `frontend/.env.example`, `scripts/verify_compose.sh`, `.github/workflows/ci.yml`, `docs/DOCKER_VERIFICATION.md`.

### KB-2 — the fourteen KB facts whose quote the page no longer prints (KB worker, ≈ 3 h)

- **Do.**
  1. Re-run the gate-99 check from the sandbox and **commit** its report and diff this time:
     `PYTHONPATH=. python scripts/verify_evidence.py --from-kb app/knowledge/kb_cs_bachelor.json --trust-env-proxy`
     (no `--robots-override-kb`: that is the owner's exception and this ticket does not use it), then
     `kb_refresh_diff` → `docs/process/KB_REFRESH_2026-10-23.md` (counts, re-draft list, blocked list, stale list) and
     the report under `evaluation/research/expert/data/kb_refresh/`.
  2. For every `quote_gone` row on a non-heldout, non-dev5 university — expected: NUS documents (6, two of them PDFs),
     CityU documents (5, one PDF), Auckland tuition (1), Paris-Saclay "no English test" not-applicable (2), plus NTU
     Singapore's deadline from the 10-19 queue — read the page as it stands today through `Fetcher` (same URL; if it
     moved, the new URL on the same official domain) with the `university-admissions-research` skill: a verbatim quote
     that still states the fact, or the fact becomes `unknown` with kind `unverified quote` and the date. A PDF quote
     comes from `pdf_document.read_pdf`'s text, never retyped.
  3. Drafts into `evaluation/research/expert/data/kb_drafts.2026-10-23/batch1/{core,programme}/` in the dev5 formats;
     `mode=verify_evidence` on that batch (§4); `kb_build --refresh` with the batch and the new evidence report;
     commit **v23** (`2026-10-23.kb-cs-bachelor.23`).
- **Tests.** `tests/test_knowledge_base.py` green (`test_the_committed_merge_loses_no_verified_fact`, the REL-1 route
  pins, the fee-shape tests); the kb journey's nine universities (Edinburgh, ETH, Kyoto, Stanford, Fudan, Oxford, KTH,
  Sheffield, Groningen) have **no row in the 14**, so `e2e:kb` is unchanged — assert it locally once.
- **Bar.** Every re-quoted fact's quote is found by the same checker on the committed URL; no fact gains a value the page
  does not print; `has_verified_data` count ≥ 95 or the drop is written down per university; `seed_demo.py` unchanged
  (demo mode never reads the KB). No heldout or dev5 row is read, drafted or listed.
- **Owns.** `backend/app/knowledge/kb_cs_bachelor.json`, `backend/evaluation/research/expert/data/kb_drafts.2026-10-23/`
  (new), `backend/evaluation/research/expert/data/kb_refresh/` (new files only), `docs/process/KB_REFRESH_2026-10-23.md`
  (new), the version line in `docs/process/KNOWLEDGE_BASE.md`.

### A11Y-KB — axe, keyboard and 390 px on the kb journey in three locales (e2e worker, ≈ 2 h; after E2E-KB-2 is cherry-picked)

- **Change.** New `frontend/e2e/kb-accessibility.spec.ts`, run by `playwright.kb.config.ts` (its `testMatch` widens to
  `**/kb-*.spec.ts`; the demo config's `testIgnore` adds the new file). It reuses the kb-env harness and the journey's
  helpers (`openPage`, `wordsFor`) and, per locale en/ru/kk: (1) `AxeBuilder` with the WCAG A/AA tags on the catalogue
  (verified filter on, a card with the knowledge block expanded), the shortlist, each of the four detail tabs of one KB
  card and one card with WHY-1 rows, the Documents screen, and the research screen with demo unticked (the kb notice) —
  0 serious or critical violations; (2) at `viewport 390×844`, `document.documentElement.scrollWidth <= clientWidth` on
  every one of those screens; (3) keyboard: the verified filter, a card's tabs and the "Add to calendar" control reachable
  by Tab and operable by Enter/Space; (4) the `kb-mode-notice`, the `verified` chip and the WHY-1 rows carry an accessible
  name in the locale (axe's `label` rule plus an explicit `toHaveAccessibleName`).
- **Bar.** Green on CI in `e2e:kb`; a real violation found is fixed in the component in this ticket only if ≤ 30 min and
  the component is not owned by MODE-1 (`PreferencesScreen.tsx`); otherwise it is reported with the axe id and screen
  for a follow-up. Gate 102 text for RC-2: "the kb journey has no serious axe violation and no horizontal scroll at 390 px
  in en, ru and kk".
- **Owns.** `frontend/e2e/kb-accessibility.spec.ts` (new), `frontend/playwright.kb.config.ts`,
  `frontend/playwright.config.ts` (the `testIgnore` line), any component file a fix needs except `PreferencesScreen.tsx`.

### EX-1 — the export says a KB fact comes from the knowledge base (backend worker, ≈ 1.5 h)

- **Change.** `app/export/tabular.py` `data_origin`: three values, decided per row from what the row records —
  "DEMO FIXTURE (synthetic)" as today; **"verified knowledge base (official sources, checked YYYY-MM-DD)"** when the
  row's claims come from the KB adapter (`app.knowledge.claims`: `KB_DISCOVERY_SOURCE = "knowledge-base"` on the
  candidate, the claims' `notes` "Verified knowledge base (…)" — the worker picks the field the row actually carries and
  pins it in a test, never a string match on the note); "live official sources" otherwise. The date is the row's
  `last_verified`. The XLSX writer shares the function. The JSON export and the ICS are unchanged (they carry the claims
  themselves).
- **Tests.** `tests/test_export_evidence_fidelity.py`: a kb-mode run's CSV and XLSX rows carry the KB origin with the
  date; a live-mode row and a fixture row read exactly as before (byte-identical header and values); a run that mixes
  (a KB university and a "No verified data yet" row) labels each row by its own claims.
- **Bar.** Gates; the export header's 38 columns unchanged; `TestDemoRunIsByteIdentical` unchanged.
- **Owns.** `backend/app/export/tabular.py`, `backend/tests/test_export_evidence_fidelity.py`.

### DOC-1 — the README and ONBOARDING say what the product ships as (docs worker, ≈ 1.5 h)

- **Do.** `README.md`: the "Live mode" section becomes "Modes" — **kb** (default; the verified knowledge base, no page
  read, `UNIMATCH_SEARCH_PROVIDER=none`, link to `docs/process/KNOWLEDGE_BASE.md` and `RELEASE_CHECKLIST.md` gates
  97–100), **live** (as written today, with the `exa_mcp` note and the 6 / 60 / 120 budget), **demo** (the fixture
  corpus); the env table gains `UNIMATCH_KNOWLEDGE_MODE` (`kb`) and `UNIMATCH_SEARCH_PROVIDER` (`none`); a "Refreshing
  the knowledge base" paragraph (`kb-refresh.yml` runs only once the branch is on `main`; the KB evidence robots
  exception is the owner's and expires at launch); the "What Unimatch does" table gets the kb row ("No verified data
  yet" for a university or programme outside it). `docs/process/ONBOARDING.md`: the first-session list names
  `KNOWLEDGE_BASE.md`, the kb-env harness (`npm run e2e:kb`) and the two env rows. `docs/CURRENT_STATE.md` is a dated
  snapshot by its own first line and is left alone.
- **Bar.** Every statement checkable against the code (`config.py` defaults, `routes_meta.capabilities`); no number
  that the ledger does not also state; the brand stays Unimatch (gate 66).
- **Owns.** `README.md`, `docs/process/ONBOARDING.md`.

### SEC-3 — the three small items SEC-2 left (security worker, ≈ 1.5 h)

- **Change.** (1) `app/adapters/extraction.py::pdf_to_text` takes `time_cap_s` with the same default as
  `pdf_document.PDF_TIME_CAP_S` and stops between pages when it is spent, returning what it has (the 40-page cap stays);
  (2) `evaluation/research/wikidata_domains.py::_qid` returns only an id matching `^Q\d+$`, else `""`, and
  `native_query` skips empty ids (SR2-10); (3) `app/adapters/search/site_search.py`'s `_FORM`, `_ATTR`, `_SEARCH_INPUT`
  rewritten with the linear tag scan of `live_discovery._link_tags` / `_attributes` (import, do not copy), with the old
  patterns kept in the test as the oracle on generated input (SR2-09; the module stays, since `fusion.Generator`
  names it).
- **Tests.** A 200-page synthetic PDF with a 0.01 s cap returns within a second and `read_pdf`'s existing tests pass;
  `test_wikidata_domains.py`: a URI with `Q1;DROP` yields no item; `test_site_search.py`: the three hostile inputs of
  SR2-02 under 0.5 s and equivalence on 20,000 generated tags.
- **Bar.** Gates; HANDOFF §8 line for the PDF cap; `SECURITY_REVIEW_2026-10-22.md` is **not** edited (RC-2 cites this
  ticket's hashes under SR2-09/SR2-10).
- **Owns.** `backend/app/adapters/extraction.py`, `backend/evaluation/research/wikidata_domains.py`,
  `backend/app/adapters/search/site_search.py`, `backend/tests/test_site_search.py`, `backend/tests/test_wikidata_domains.py`,
  `backend/tests/test_live_extraction.py` (the PDF case).

### MODE-1 — gate 79's uncovered case (product worker, ≈ 1 h)

- **Change.** `routes_meta.live_coverage`: in demo mode with `settings.knowledge_mode == "kb"`, the response is today's
  body **plus** an additive `kb_coverage` key holding `kb_coverage(settings, session)` (so the pinned "reads as before"
  test passes on the existing keys). `PreferencesScreen`: `kbMode = coverage?.mode === 'kb' || (demoMode === false &&
  coverage?.kb_coverage != null)`; the kb notice and the KB numbers come from `kb_coverage` in that case. `types.ts`
  follows.
- **Tests.** `tests/test_api.py::TestMeta`: the demo-mode body keeps every existing key and value, gains `kb_coverage`
  only when `knowledge_mode == "kb"`; `tests/test_frontend_contract.py` (additive); `PreferencesScreen.test.tsx`: a
  demo-mode server with kb → unticking demo shows `kb-mode-notice`, never `live-mode-notice`; the live-mode server case
  unchanged.
- **Bar.** Gates; `seed_demo.py` byte-identical; RC-2 removes gate 79's "Not covered" sentence citing this hash.
- **Owns.** `backend/app/api/routes_meta.py`, `backend/tests/test_api.py` (TestMeta only), `backend/tests/test_frontend_contract.py`,
  `frontend/src/screens/PreferencesScreen.tsx`, `frontend/src/screens/PreferencesScreen.test.tsx`, `frontend/src/types.ts`.

### LG-1 — the hypotheses ledger catches up (docs worker, ≈ 0.5 h)

- **Do.** `backend/evaluation/research/expert/data/hypotheses.json`, in the file's own row shape (`id`, `status`,
  `case_ids`, `observation`, …): **CO-1 V1** `CONFIRM_QUEUE_SELECTION_ORDER` (not built; one set by measurement,
  auckland rank 26 → 4; re-opens under a one-set bar only if FRH fails auckland while passing khalifa); **CO-1 V2**
  `LEVEL_SLUG_IGNORES_EXTENSION` (not built; needs its own knockout look); **FR-3** (not built; 0 of 4 sets lose a
  labelled tuition claim to a (b) cause); **SH-1**, **LL-1** (built, off, fired with no gain; triggers as recorded);
  **NS-1b + PC-1** (on by default 2026-10-20, the 09:15 columns); **SG-1** once §4 reads it. Each row cites its document
  and section.
- **Bar.** The file parses; `python -m evaluation.research.scorecard --help` unaffected; nothing else in the directory
  touched.
- **Owns.** `backend/evaluation/research/expert/data/hypotheses.json`.

### IC-2b — the ceiling report committed and the rank table written (measurement worker, ≈ 1 h; when run 39408839839 finishes)

- **Do.** Download the run's artifact into this session's own scratchpad; commit the development report as
  `backend/evaluation/research/data/index_ceiling.dev-2026-10-22.json` with **every dev5 and heldout row removed** (dev5
  aggregates only, as a count line in the markdown; the committed file is checked by a grep for the 13 + 9 seed ids
  before the commit). Add to `INDEX_CEILING_2026-10-19.md` a dated section: the per-case `hop1_parent` / `hop1_anchor` /
  `hop1_rank` table for the hop-2 cases (puc, iitd, kit, auckland, ucph, ntu, vienna, kaist), reconciled against
  NO_SEARCH_FLOOR §2's rank column with every difference written down; and the **khalifa correction** (CO-1 §7.2: the
  "bounded, hop 0" row does not reproduce — the gold is in neither sitemap document; the row was matched on something
  other than the draft3 gold). Update Table 1's dev2 `in_sitemap_bounded` count if the re-measure changes it, with the
  old value kept in the text.
- **Bar.** No heldout case id, URL or domain in the committed JSON or the markdown; the ceiling verdict for ticket 05
  unchanged unless the numbers change it, in which case the planner is told, not the map.
- **Owns.** `docs/process/INDEX_CEILING_2026-10-19.md`, `backend/evaluation/research/data/index_ceiling.dev-2026-10-22.json` (new).

### CM-1 — a moderation runbook beside the community guidelines draft (docs worker, ≈ 1 h)

- **Do.** `docs/MODERATION.md`, marked **draft, not reviewed by the owner** in its first line like gate 87's texts: what
  the report queue is (`ModerationScreen`, the `test_social_moderation.py` contract), who may read it (owners of the
  organisation), what a moderator does with a report (read, decide hide / keep / block, record the reason), target times
  (first look within one working day; a message report within the same day), what is logged and what the reported
  person is told, how a person leaves (account deletion's community seam), and what is **not** decided here (the rules'
  wording, the appeal path — the owner's). Link it from `LegalScreen`'s "Community guidelines (draft)" panel only if the
  panel already links documents; otherwise leave the screen alone.
- **Bar.** Every statement true of the code (cite the test or route); no promise the product does not keep.
- **Owns.** `docs/MODERATION.md` (new); `frontend/src/screens/LegalScreen.tsx` only for a link, and only if a link
  pattern exists there.

### RC-2 — the ledger re-counted after cycles 22–23 (docs worker, ≈ 2 h; `RELEASE_CHECKLIST.md` only; last)

- **Do.** On the branch head after the tickets above are cherry-picked: gate 2 (the red run 39405712087, its cause, the
  E2E-KB-2 fix and the first green run; PASS only with the green link, PARTIAL otherwise), gate 1 (test counts), 3 (sizes
  from `npm run build`), 15–16 (re-run `pip-audit`, `npm audit`, the secret grep, dated), 21 + **102** (A11Y-KB), 22 +
  **101** (CS-1 with the CI job id), 79 (MODE-1 closes "Not covered"), 92 (I18N-2's key counts and the remaining list),
  96 (CM-1; the guidelines draft that already exists in `LegalScreen`), 99 (KB-2: v23's check counts — the 14 moved to
  re-quoted or `unverified quote`), 20 (EX-1's origin column), 24 (DOC-1). SR2-09 / SR2-10 noted under gate 15 with
  SEC-3's hashes. Recount the summary; "Order of work remaining" item 10 stays (kb mode on `main` is the owner's).
- **Bar.** `PASS` only with output shown; no gate moves on reasoning alone; the owner-dependent rows (87, 94, 29) stay.
- **Owns.** `RELEASE_CHECKLIST.md`.

## 4. Dispatch table (main session, 0 worker hours)

Common inputs as NEXT_CYCLES_2026-10-20 §7 (`benchmark-capture.yml`, `runner=ubuntu-latest`, `mode=expert_paired`,
`seconds_per_case=120`, `max_pages=60`, `case_parallelism=5`, `max_search_queries` empty). Score cohort on
`ground_truth.reviewed11.json`, dev2/dev3/dev4 on `draft3` with `--allow-drafts`; dev5 with `--summary-only` only.

| run | set(s) | inputs that differ | `run_tag` | read |
|---|---|---|---|---|
| **SG-1 verdict** (runs done 10:20: 39407237273 cohort, 39407239955 dev2, 39407243537 dev3, 39407246813 dev4, 39407250150 guard) | 4 sets + guard | already run with `--sitemap-guess-cap` | `sg1-*`, `rp-sg1-dev4` | pre-registered: ctu `case_time` −20–30 s; kit, itu, msu, um, ethz, utokyo −3–6 s; hits unchanged everywhere, 0 wrong, guard identical → `SITEMAP_GUESS_RULE = True` as a one-line commit **before FRH-2 starts** on `live_discovery.py`; LOOP_REPORT entry; LG-1's row. A hit lost or a wrong page → stays off, `hypotheses.json` |
| **D-F5 dev5 no-search floor** (run done 10:34: 39408880008) | dev5 | `search_provider=none`, `columns=1` | `ns-floor-dev5` | `scorecard --summary-only` on `dev5.draft1 --allow-drafts`; **aggregates only**, against the pre-registration (NEXT_CYCLES_2026-10-21 §4): found ≤ 3/8 readable, wrong 0, over budget 0, kbtu and satbayev `unavailable`. Record which defaults the pipeline had (NS-1b/PC-1 on or off at `f0d1830e` vs today); LOOP_REPORT line with counts |
| **IC-2 run** (in flight: 39408839839) | — | `mode=index_ceiling` | — | artifact to IC-2b's worker; the committed report is the output |
| **E2E-KB-2 green run** | — | the `release-gates` run of its commit | — | green → RC-2 gate 2; red → the job name goes back to the e2e worker the same hour |
| **CS-1 compose job** | — | the `release-gates` run of its commit, new `compose-stack` job | — | green twice → gate 101 |
| **KB-2 batch check** | — | `mode=verify_evidence`, `extra_args=evaluation/research/expert/data/kb_drafts.2026-10-23/batch1` | — | the `evidence-check-<run>` artifact beside the drafts; rows CI could not read are re-checked from the sandbox with `--trust-env-proxy` (no robots override) |
| **FRH-2** (when built) | 4 sets normal + knockout; guard 4 sets | `search_provider=none` / `recorded`, `columns=4`, `extra_args=--follow-refused-hub-link` | `frh-*`, `frh-ko-*`, `rp-frh-*` | §3 FRH-2 bar; 12 runs |
| **Clean baseline 4** (optional, idle runners) | 4 sets, recorded; 4 sets, no-search | today's defaults, `extra_args` empty, `columns=4` | `base4-<set>`, `ns-base4-<set>` | one "where we stand" row per bench with every flipped rule on (LV-1, AW-2, NS-1b, PC-1, SG-1 if flipped); replaces §0's composite row in LOOP_REPORT |
| **D-D interaction check** (optional, idle runners) | 4 sets | `extra_args=--no-<rule>` for `abstain-on-unreadable-entry`, `confirm-head-identity`, `reject-combination-head`, `reject-subpage-head`; knockout arms too | `rp-abl-<rule>-<set>` | identical → absorbed (ledger note); a stable loss → still load-bearing; no default change from this alone |

The KB refresh workflow is still **not** dispatchable from the branch (`kb-refresh.yml` reads the default branch); §6.

## 5. The cycles

| cycle | dispatches (0 worker h) | worker tickets (parallel, disjoint files) | gate / read |
|---|---|---|---|
| **22 (now)** | SG-1 verdict (runs done); D-F5 aggregates (run done); IC-2 artifact when it lands; E2E-KB-2's CI run; the SG-1 flip commit before FRH-2 | **E2E-KB-2 → A11Y-KB** (one e2e worker, in that order), **CS-1** (infra), **KB-2** (KB), **EX-1 → SEC-3** (one backend worker), **DOC-1 → LG-1 → CM-1** (one docs worker), **MODE-1** (product); **TR-1** finishes and hands `live_discovery.py` to **FRH-2** | CI green on E2E-KB-2's commit; SG-1's default decision in LOOP_REPORT and `hypotheses.json`; D-F5 against its pre-registration; KB v23's check counts |
| **23** | FRH arms (12) the moment FRH-2 lands; KB-2's batch check; CS-1's compose job; clean baseline 4 as runners idle | **FRH-2** (pipeline, high), **IC-2b** (when the run is in), follow-ups the verdicts name (an axe violation over 30 min, a CS-1 service that will not start on the runner, a KB row that needs the owner), then **RC-2** once every other ticket is cherry-picked | FRH bar → default decision; gates 101–102 with run ids; the ledger recounted on the branch head |
| **24** | D-D interaction check as runners idle; re-score the day any signature arrives (§6) | the no-search residue table by class into LOOP_REPORT (12–14/39 declared the $0 ceiling); CO-1 V1 only on FRH's auckland failure (§7); SEC-3 / A11Y follow-ups; otherwise the product hygiene list is empty and the main session says so to the owner with §6 | the bench declared exhausted or at 14/39; the ledger's count the owner reads |

Expected after cycles 22–24 without the owner: CI green again; recorded-replay hits unchanged at 26/39; no-search floor
12/39 → 14/39 (FRH) and then declared at its $0 ceiling with its residue by class; the container stack proven in kb mode
on every push; the kb journey scanned for accessibility in three locales; every KB fact served with a quote its page
prints today; the export, the README and the ledger say what the product ships as. With the owner's answers: §6.

## 6. What each pending owner answer unlocks

| answer | unlocks (one line) |
|---|---|
| **U7**, deadline variant A (skip the eligibility deadline check when every stated date precedes the intake's cycle) or B (soften to a non-GAP note) | the Fudan-type row stops reading GAP for a window the applicant never had; `eligibility.evaluate` is shared with live mode, so `seed_demo.py` is re-checked; ≈ 1.5 h |
| **KFUPM** (two official pages disagree on the waived tuition) | one held-back tuition fact enters v24 (SAR 0, standing policy) or stays `unknown` with the disagreement as its kind |
| **Q7 standing fee policies** (`--standing-fee-policy-current`: ETH, EPFL, FU Berlin, Heidelberg, UZH, KTH, Lund, IP Paris, Osaka, Nanjing, Kyoto, ISCT) and **the yearless-deadline flag** | 12 fees shown as current with the "fee policy page; no academic year printed" caveat instead of stale; yearless deadlines become facts with `year_inferred`; one `kb_build` rebuild, 0 code |
| **Melbourne's related route with `verified: false`** (SR2-05's open question) | whether a REL-1 route whose quote failed the check is offered at all; one KB statement served or withheld |
| **Native-name overlay signature** (`catalogue_native_names.proposed.json`) | production `native_name` for the signed rows; the identity gate reads dev5 **7/13 → 9/13** (IG-2); the 15-Q2 gate arm becomes credible; LQ-2a's `native_name` branch stops being inert |
| **Three twin signatures** (Q1 uct keep; Q2 kuleuven, "yes if (b) without the credits clause"; Q3 tcd) | `dev2.draft4` / `dev3.draft4` after CI `verify_evidence`: knockout dev2 1 → 0, dev3 kuleuven wrong → hit in readable repetitions; recorded hits 26 → 27–28/39 by re-score, **0 code** |
| **Exa key** (01-Q3 / Q6; Tavily beside it) | R1 (44 cases, cap 264) → the `recorded-search/2` store → re-baseline; the LQ-2a `query_probe` (15 queries); then R2 (dev5, cap 312, aggregates) once 13-Q1…Q5 are signed → 13-Q2 (b) for the flipped rules and the no-search bench's 25 search-dependent cases |
| **Self-hosted runner** (01-Q4; SR2-03's setup rules first: fork approval, `--ephemeral`, a dedicated user or VM) | one `read_pages` dispatch of RP-1's **105 rows on 28 universities**; the access five of the development misses re-probed for the floor; the kb-refresh workflow's self-hosted input |
| **Merge to `main`** | `kb-refresh.yml` runs at all (schedule and `workflow_dispatch` read the default branch) and the 60-day clock starts; gates 97–102 hold on `main`; "Order of work remaining" item 10 closes |
| **U9, B7, D7, P3, P4** | a funding label for "no award offered", the brand question, the thin document quotes, two date conventions |
| **The glossary person** (gate 92) | the 11 reserved shell keys and the provisional terms settled; gate 92 PASS |
| **A lawyer (87), an ApiPay account and price (94), the release tag (29)** | the three rows that need a person, not a cycle |

**13-Q1…Q5 and 15-Q1…Q5** (the second look's arms and reading) remain the only route to a target-6 number; nothing in
cycles 22–24 touches them.

## 7. What this plan does not build, and why

| item | why not now | re-opens when |
|---|---|---|
| **CO-1 V1** `CONFIRM_QUEUE_SELECTION_ORDER` | one set by measurement (auckland); FRH reaches the same case on a two-set bar, and two rules on one case make the attribution unreadable | FRH's `frh-dev3` arms fail auckland in ≥ 2 of 4 columns while `frh-dev2` passes khalifa → V1 under a one-set bar (NO_SEARCH_FLOOR §7.4 (a)) |
| CO-1 V2 `LEVEL_SLUG_IGNORES_EXTENSION` | changes what `keep()` refuses; needs its own knockout look; no case needs it once V1 or FRH lands | V1 opens and fails |
| CX-1 step 2 / FR-3 | the costs stage's no-figure reads are 71 % correct behaviour and the rest cost no labelled claim on any set | a labelled tuition claim on ≥ 2 sets is lost to an unparsed fee shape |
| the kaist catalogue-role refusal (cohort) | one set, behind a registry seed; its refused pages link the gold only as "교육" | a second development case reads the gold in a catalogue role |
| R4 `--local-catalogue-entry` on by default for the no-provider regime | NS-1b covers kit and puc; R4 adds nothing stable beside it (`ns-r4b-dev3` 3 → 4, puc only) | NS-1b is ever turned off |
| AW-3, PD-1, CA-1, IB-1, AI-1, AW-1, SH-1 default-on, LL-1, SP-2 | gain 0 on every bench today (NEXT_CYCLES_2026-10-21 §7, REACH_ROWS) | the triggers written there |
| a KB manual round for new facts | §2.3: the pool is unpublished, access or unresearched cells; rounds 7–10 yielded ≈ 1 fact per university-hour | 01-Q4 (RP-1's list), or spring 2027 fees |
| I18N-3 | §2.5: what is left is the page's own words, parameters, and glossary terms a person must choose | the glossary person |
| U7, U9, B7, D7, P3, P4, Q7, the Melbourne route | owner decisions | the answer |
| the own index as a provider, Common Crawl discovery, model extraction, any heldout look, DoD targets or denominators, the 6 / 60 / 120 budget, the 2026-10-19 defaults before R2 | as NEXT_CYCLES_2026-10-20 §9 and 2026-10-21 §7 | — |
