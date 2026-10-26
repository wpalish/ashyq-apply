# Next cycles plan, 2026-10-22: cycles 19–21, all at $0 and without the owner's answers

Planner, 2026-10-22, from the cycle 16–18 record (`LOOP_REPORT.md` 2026-10-20 05:20 → 06:45), `NEXT_CYCLES_2026-10-21.md`
(every item closed, see §0), `NO_SEARCH_FLOOR_2026-10-21.md`, `EVIDENCE_GENERALISATION_2026-10-21.md`,
`LOCAL_LANGUAGE_LOCO_2026-10-20.md` §6, `TWIN_CHECKS_2026-10-20.md` (TW-2), `KB_E2E_SMOKE_2026-10-19.md`,
`CODE_REVIEW_2026-10-19.md`, `SECURITY_REVIEW_2026-10-19.md`, `I18N_RESULTS_2026-10-19.md`, `RELEASE_CHECKLIST.md`,
`SEARCH_DEFINITION_OF_DONE.md`, the five wayfinder maps, HANDOFF §8, the committed KB v22, the read list
`read_pages/self-hosted-2026-10-21.json`, the CI run list of the branch, and the code. Development data only: **no heldout
file, capture, log or label was opened; no dev5 per-case row was read; no other scratchpad was read; no provider was
called; no credit was spent.** The only numbers computed here were read from the committed KB file and `git`.

Constraints, unchanged: paid search frozen; no free key (01-Q3 / Q6 open); dev5 design-blind (13-Q1); a rule goes on by
default only under 13-Q2; the 6 / 60 / 120 budget; no PR unless the owner asks; model identifiers stay out.

## 0. Where we stand after cycles 16–18

| row | cohort | dev2 | dev3 | dev4 | all |
|---|---|---|---|---|---|
| recorded replay, today's defaults (LV-1, AW-2 on): hit / wrong / related / missed | 5/0/0/5 | 6/0/1/3 | 10/0–1/0/3–4 | 5/0/1/3 | **26/39**, wrong 0 (+ kuleuven flake) |
| **no search provider**, today's defaults (NS-1b off) | 4/0/0/6 | 2/0/1/7 | 3/0/0/11 | 0/0/0/9 | **9/39**, wrong 0 |
| the same with `--homepage-hop-reads` (NS-1b, 4 columns) | 4 | 2 | 3 + puc in 2 of 4 | **1** (kit, stable) | 10/39 stable, 11/39 in two columns |
| own-index ceiling (`INDEX_CEILING`) | 3 | 1 | 6 | 1 | 11/39 |
| knockout guesses (gold hidden) | 0 | 1 (khalifa) | 1 (uio) + flake | 1 (ctu) | 3 + flake |
| precision · wrong scope · over budget | 1.0 · 0 · 0 | same | same | same | targets 1, 2, 5 met |

What closed since the 2026-10-21 plan (all ten items):

| item | outcome |
|---|---|
| CAT-1 | merged: per-card "verified knowledge base" chip, KB fee beside the historical one, `verified=true` filter, `kb_total`; `/api/capabilities` lists the KB adapter and marks the six web adapters inactive in kb mode |
| NS-1a | the shared dev3 + dev4 cause is the navigation fallback never reading the homepage's top study link on a sibling host (puc, iitd, kit) |
| NS-1b | built (`HOMEPAGE_HOP_READS`), replayed on the no-search bench: **kit stable gain on dev4; puc hit in 2 of 4 columns; 0 wrong; knockout and recorded guard identical** → **stays off** (the bar wants both sets). R4 (`--local-catalogue-entry`) alone also reaches kit. puc's instability is "under the 120 s clock: the sitemap read marks the host slow" |
| E2E-KB | merged: `npm run e2e:kb` in CI, 8 tests, the network guard with a probe, `RELEASE_CHECKLIST` gate 97 added as PENDING |
| REL-1, WHY-1 | merged, KB **v22** rebuilt: 7 entries state their programme route (6 related-only, LSE not offered); 194 unknown records carry a kind (access 63, not published 60, not researched 47, unverified quote 12, other year 8, undated 4) |
| LQ-2a | built (flag off); offline table on 28 development cases: 3 phrases, all the gold shape, **puc's phrase is its gold title verbatim**; `query_probe` list of 15 pre-registered; waits for a key |
| RP-1 | `read_pages/self-hosted-2026-10-21.json`: **105 rows on 28 universities** (63 access cells on 21 universities, the 25 kb-refresh blocked rows, UCL and Alberta, Monash's English cells) |
| TW-2 | the kuleuven CI read: (a) no redirect and (c) a quote hold; (b) holds for the degree, the university and the campus but the page prints no "180 studiepunten / Bachelor of Science" line → Q2 is "yes if (b) is accepted without the credits clause" |
| G-16a | item 1 (unlabelled claims) set-dependent through award-page reach and corpus label coverage; item 3 (costs pages) dev-wide and borderline — **the costs stage yields a figure on 0 pages on dev3 and dev4, 2 on cohort**; item 4 (award expressibility) dev-wide; dev5 column empty for R2 |
| AW-2 | on by default (language-coverage bar); ES-2 rows print |
| CI | `release-gates` was red on `d3cd6904` and `4c33bfb5` in `security-and-containers` only (the web image build imported the kb e2e config); `a15bf7d4` fixes it and its run was in flight when this plan was written. Gate 97's PASS link is that run |

Not dispatched from the previous plan's §4: **D-F5** (dev5 no-search floor) and the **KB refresh first CI run**. The second cannot
be dispatched at all from the branch: `gh` answers 404 for `kb-refresh.yml` because the workflow file is not on `main`
(the schedule and `workflow_dispatch` both need it there). It moves to §6 as an owner-dependent line.

**Three benches now.** The recorded replay is exhausted for rule gains (§2.1). The **no-search bench** is 2 cases under its
measured ceiling (9/39 vs 11/39) and NS-1b has one of the two in hand; the clock on puc is the one thing between the rule
and its bar, and a second two-set cause (confirm-queue order on dev2 + dev3) is already named. The **product in kb mode**
has one launch-screen statement that is wrong today (§3 RM-1) and a release ledger counted on a commit from September.

## 1. The ranked list

Ranking = expected movement (a DoD row on a two-set cause, a launch gate, an applicant-visible correctness fix) per
worker hour. Dispatches cost no worker time and are in §4. "Why it pays" is the 13-Q2 (a) question, or the launch
question, answered in advance. Effort `medium` unless marked.

| # | item | kind | worker h | runs | what it moves | why it pays on a set, or a screen, that did not motivate it | expected outcome |
|---|---|---|---|---|---|---|---|
| 1 | **PC-1** puc's clock on the no-search bench, then NS-1b's verdict re-run | pipeline, effort **high** | 1 research + 2.5 | 13 | target 3 without a key: 9/39 → **11/39**, NS-1b on by default | the two cases are on two sets (kit dev4, puc dev3); the rule is a size, time or reserve bound in the sitemap stage or the stage budget, never a word | puc hit in 4/4 columns beside kit; NS-1b and PC-1 default-on together, or R4-no-search as the cheaper verdict; else `hypotheses.json` |
| 2 | **RM-1** the research-mode screen says what kb mode reaches | product (API + UI) | 1.5 | 0 | launch readiness: gate 79's kb-mode counterpart; today the `live-mode-notice` ("Live mode fetches real university websites … search terms are sent to search providers") and "Live mode searches 19 curated institutions in 15 countries" render **in kb mode too**, where no page is read, nothing is sent to a provider and 98 universities answer | the sentence is read by every applicant before every run; CAT-1 fixed the catalogue, not this screen | `live_coverage` in kb mode names the KB's reach and the "No verified data yet" rule; en/ru/kk; live and demo byte-identical |
| 3 | **RC-1** the release ledger refreshed for kb mode | docs, commands | 2.5 | 0 (CI) | launch readiness: `RELEASE_CHECKLIST.md` is counted on `2be6b55`, still says CI red since 2026-09-04 (fixed: the `Saved` chip is `exact: true`), gate 2 PARTIAL stale, gate 97 PENDING | the ledger is what the owner reads to decide a release; a wrong row costs a wrong decision | every stale row re-run with today's output; gate 97 PASS with the CI link; three kb-mode gates added (98–100) |
| 4 | **CO-1** the confirm-queue order (auckland dev3, khalifa dev2) | research 1.5 h → pipeline rule 2.5 h | 4 | 10 | target 3 without a key: +1–2 (auckland missed → hit, khalifa related → hit) | a two-set cause (dev2 + dev3) that NS-1 does not touch; the rule is an order or a budget split in `keep()` / `_confirm_programs`, not a word | the per-case rank table, then a flagged rule with the pre-registered expectation; the no-search bench reaches its ceiling |
| 5 | **SEC-2** security review of the ≈ 114 commits since `5de8b6a3` | security | 2 | 0 | launch readiness: the 2026-10-19 review stopped before CAT-1, REL-1, WHY-1, E2E-KB, NS-1b, LQ-2a, the fee shapes and RP-1 | the surfaces are new API fields, a CI harness that starts the real API, URL lists CI executes, and a query built from page text | `SECURITY_REVIEW_2026-10-22.md`; findings ≤ 1 h fixed in the ticket, the rest proposed |
| 6 | **I18N-2** the sentences still English on the results screens | product (backend keys + UI) | 4 | 0 | gate 92's remaining list: requirement explanations, funding eligibility and classification reasons, ranking reasons, document steps, conflicts, the Documents screen | the audience is Kazakh- and Russian-speaking; the kb journey's Requirements, Funding and Documents tabs still show English sentences beside localised labels | ≈ 15 more templates in `message_keys.py` with en/ru/kk entries; stored payloads unchanged; glossary rows marked provisional |
| 7 | **TR-1** the no-search trace explains itself | measurement | 2 | 0 | NS-1a needed a scratch probe from another vantage point; CO-1 and PC-1 step 1 would need the same | the next floor run is read from its own rows: confirm queue with scores and read/unread, the sitemap keep verdicts, the navigation queue, per-read seconds and bytes | `DiscoveryTrace` rows + a scorecard column `gold_confirm_rank` (evaluation only) |
| 8 | **CX-1 step 2** the costs-stage rule step 1 names | pipeline, effort **high**, conditional | 3 | 8 | target 4's tuition row: the stage reads and extracts nothing almost everywhere (G-16a item 3) | the mechanism is dev-wide by measurement (0 / 0 / 0 / 2 ok pages), so any fix is two-set by construction | step 1 is in flight with another worker; step 2 opens only on its verdict (§3) |
| 9 | **PERF-1** kb-mode performance budgets | measurement + tests | 1.5 | 0 | launch readiness: no number exists for the catalogue list with the knowledge block, the KB load, a 10-university kb run or today's bundle size | gate 3's 74 kB build and gate 83's latency rows predate the i18n catalogue (404 keys × 3) and CAT-1 | p50/p95 for the four, two budget tests, numbers for RC-1 |
| 10 | **SG-1** sitemap guesses on a crawl-delay host | pipeline rule | 2 | 6 | the clock: four guessed sitemap paths cost 6–8 s on most hosts without a declared sitemap and 30 s on ctu (dev4) | a DoD step-3 gain of the "fewer reads with identical labels" kind; hits are not expected to move | `case_time` down on ≈ 10 development cases; no hit lost; 0 wrong |
| 11 | **IC-2** the ceiling tool records the hop-1 parent and its rank | measurement | 1.5 | 1 (CI) | NS-1a's rank column came from a scratch probe "from another vantage point and some hours later" | CO-1 / PC-1 and any later no-search ticket read a committed report | `index_ceiling` report gains `hop1_parent`, `hop1_rank`; the development report is committed |
| 12 | **KB-1** `merge_entries` gaps and comment drift | product (KB runtime) | 1 | 0 | correctness: a fact dated only by `accessed_on` loses to any dated fact (P8); two flag comments say "off" for rules that are on (P9) | no row changes today; it is the next import that would | tests in `test_knowledge_base.py`; comments fixed |

Not on the list, and why: §2 (the exhausted benches and rounds), §7 (rules that would gain 0 on any bench today).

## 2. What is exhausted, honestly

### 2.1 The recorded-search replay, for rule gains: exhausted (unchanged)

AW-2 was the last replay with a plausible gain. Since then the recorded bench ran guard arms only (NS-1b's `rp-ns1-*`),
and that is all it runs in cycles 19–21: the CO-1, PC-1 and CX-1 guards. The 13 misses keep their classes
(NEXT_CYCLES_2026-10-20 §2); nothing here re-opens them.

### 2.2 The no-search bench: two cases from its ceiling, then exhausted too

| cause (NO_SEARCH_FLOOR §4) | sets | status |
|---|---|---|
| navigation fallback never reads the hop-1 study page | dev3 (puc, iitd), dev4 (kit) | NS-1b built; kit gained; puc blocked by the clock → **PC-1** |
| confirm-queue order on a bounded-sitemap gold | dev3 (auckland), dev2 (khalifa) | **CO-1** |
| read and refused in a catalogue role | cohort (kaist, behind a seed) | one set, not built |
| clock on a reachable gold | none | — (the clock cases are all unreachable golds: uio, ctu, ubc, uppsala) |
| trimmed on a reachable gold | none | — |

After PC-1 and CO-1 the bench sits at its measured ceiling (11–13/39). The other 26–28 cases need a key (search) or a
different vantage point (access: aalto, toronto, hku, kaznu, ub, kuleuven) or a department host no read page links
(kaist, ntutw, msu, um, unibo, ktu, chula, usp, warsaw). None of those is a $0 rule.

### 2.3 KB manual rounds: still stopped

v21 and v22 added fee shapes and the two REL-1 / WHY-1 fields, no new fact from a round. The pool is unchanged (60 not
published, 63 access, 47 not researched); RP-1 holds the 105 URLs for the owner's computer. No manual round in
cycles 19–21.

### 2.4 The kb-mode smoke gaps: closed, except the owner's

B1–B6 and B8, D1–D6, U1–U6 and U8 are fixed and guarded by `e2e:kb`. Open and owner-dependent: U7 (deadline variant),
U9 (the "Not eligible" chip for "no award offered"), B7 (brand), D7 (thin document quotes — a data review), P3 (winter
intake convention), P4 (the "academic year past" date). P1 (knowledge mode recorded per run) and P5 (`covers()` only for
CS and its ontology aliases) are already done in the code. P7 (CC-1 and a year slug) is one set, discovery frozen.

### 2.5 Rules and research with nothing left to do at $0

LQ-2a (built; one offline case; needs a key). LOCO-1 / NN-1 / IG-2 (need the overlay signature). The reach shapes S4,
AI-1, AW-1, SH-1 (recorded, triggers written). D-D ablations (complete). G-16a (done; dev5 column for R2). The twin
checks (TW-1/TW-2 done; signatures pending). The own index as a provider (closed on the ceiling), Common Crawl (needs an
owner exception), the model hint (design only).

## 3. Worker tickets

Common to every ticket: design on cohort/dev2/dev3/dev4 captures, the KB files and code; no dev5 or heldout page, label,
capture or row; word tables dictionary-grade for every `languages.json` language at once; a pipeline flag is off by
default with its `NEGATABLE_RULES` entry; HANDOFF §8 line for any contract change; golden demo byte-identical
(`UNIMATCH_DEMO_MODE=true UNIMATCH_ENABLE_BROWSER_TIER=false python seed_demo.py`, brief §5.7 order); gates green
(AGENTS §5); commit locally with the `Agent:` trailer; the main session cherry-picks, runs the suite and dispatches.
`runner.py` and `scoring.py` are touched by no ticket here. `live_discovery.py` is held by one worker at a time:
PC-1 (cycle 19) → TR-1 → CO-1 step 2 (cycle 20) → SG-1 (cycle 21).

### PC-1 — puc's clock, then NS-1b's verdict (pipeline worker, effort high, ≈ 3.5 h, 13 runs)

- **Step 1 (1 h, research).** List the NS-1b runs with `gh run list --workflow benchmark-capture.yml --json
  name,databaseId` (`ns1-dev3`, `ns1-ko-dev3`, `ns-r4-dev3`, 2026-10-20 06:17) and read puc's trace in every column:
  `stage_budget` (seconds and reads per stage, `stopped_by`), `host_cost` (`slow`, `median_read_seconds`,
  `crawl_delay`), the read ledger (per read: URL, seconds, outcome), `homepage_hop_reads`, `stage_order`, `pages_read`,
  `case_time`, the SB-1 lines in `errors`. One table, column → sitemap seconds → hop pages read (which, at what second)
  → was `admision.uc.cl/carreras` read → was the gold queued → was it read in confirm → what stopped it (the 55 s
  deadline, the 28-read cap, a refused read, not queued). Name the mechanism. `_search_due` already ignores the 33 s
  cut when no provider is configured (`_search_wanted` is false), so that is not it; the candidates are the sitemap
  document's own read time (21 s in NS-1a, 40 % of the discovery deadline) and the slow-host verdict it triggers
  (`HostCost.first_read_rule`: one read over 5 s among the first two).
- **Step 2 (2.5 h).** One flag, chosen by step 1 from this pre-registered menu, registered in HANDOFF §8 before any run:

  | mechanism step 1 finds | rule | where |
  |---|---|---|
  | the sitemap document's read time leaves navigation and confirm no room | **(A)** `SITEMAP_DOCUMENT_MAX_BYTES` — a per-call byte cap the fetcher's streaming reader enforces for sitemap documents only (it can only lower `MAX_BYTES`); over the cap the document is `too_large` for the stage and the walk goes on | `SitemapReader.collect`, `Fetcher.get(max_bytes=)` |
  | the hop reads and their leads' confirm reads fall past the SB-1 deadline | **(B)** `HOP_READ_RESERVE_READS` — when no provider is configured, hop reads and the confirm of a lead they produced may run past the discovery deadline up to a reserve, as `RECOVERY_RESERVE_READS` does for recovery; the 60-read ledger and the case clock are unchanged | `_navigation_fallback`, `_confirm_programs`, `StageBudget` |
  | the slow-host verdict itself cuts the path (a cap of 3 documents, the walker skipped) | **(C)** `SLOW_HOST_SAMPLE_MAX_BYTES` — a read whose body is over the cap is not a latency sample (its seconds are its size, not the host's speed) | `HostCost.get` |
  | the sitemap stage alone spends the deadline | **(D)** `SITEMAP_STAGE_MAX_SECONDS` — with no provider configured the sitemap stage keeps at most this share of `DISCOVERY_DEADLINE_SECONDS`, so navigation always starts | `before_document` |

  Every one is structural (a size, a time, a reserve); none adds a word. Nothing in `intent.py`, the classifier,
  `profile_rejects` or the evidence stages.
- **Tests** (`tests/test_puc_clock.py`, synthetic `example-uni.edu` / `admit.example-uni.edu`, a fake fetcher whose
  sitemap read advances the `_clock` hook by N seconds and returns a large body): on, the hop page is read and the
  field-named lead confirmed with `--homepage-hop-reads`; off, byte-identical to the flag-less trace; the three budget
  files (`test_case_read_ledger.py`, `test_stage_budgets.py`, `test_case_time_budget.py`) and
  `test_homepage_hop_reads.py` pass with the flag off and on (the plugin pattern of `tests/_homepage_hop_reads_on.py`).
- **Dispatch (§4).** `search_provider=none`, `columns=4`: `--homepage-hop-reads --<pc1>` on four sets normal
  (`ns1b-<set>`) and knockout (`ns1b-ko-<set>`); `--<pc1>` alone on dev3 and dev4 (`pc1-<set>`); the recorded guard
  on dev3 and dev4 (`rp-ns1b-<set>`); the R4 comparison `--local-catalogue-entry --<pc1>` on dev3 (`ns-r4b-dev3`).
- **Pre-registered expectation.** dev3: puc **hit in 4/4**; iitd, auckland stay missed; imperial, unsw, ucph unchanged.
  dev4: kit **hit in 4/4**; ctu unchanged unless (D) frees its 30 s; unibo, ktu, rwth unchanged; a newly returned page on
  vut, taltech, boun or itu reads "unadjudicated" and is listed. cohort, dev2: no change. `--<pc1>` alone: no hit
  change on any set (it is the clock arm). Total **9/39 → 11/39**, 0 wrong.
- **Bar.** NO_SEARCH_FLOOR §5's bar for NS-1b, read on the `ns1b-*` arms: no hit lost on any set; 0 wrong pages;
  knockout `wrong_programme_pages` not up (today 0 / 1 / 1–2 / 1); a stable gain on **both** dev3 (puc) and dev4 (kit);
  recorded guard identical or better. Then NS-1b and PC-1 on by default together. If `ns-r4b-dev3` gains puc as well, the
  cheaper verdict "R4 on when no provider is configured" is written beside it and the owner is told which one is
  recommended; NS-1 keeps iitd-shaped (English) cases either way. Two failures on the same cause → `hypotheses.json`,
  NS-1b stays off, and §2.2's bench is declared at 10/39 stable.

### RM-1 — the research-mode screen says what kb mode reaches (product worker, ≈ 1.5 h)

- **Change.** `app/api/routes_meta.live_coverage()` takes the settings: in kb mode (not demo, `knowledge_mode == "kb"`)
  it returns `mode: "kb"`, `institutions` = KB entries with verified data (`load_knowledge_base` through the
  `routes_universities._knowledge_base` cache, `has_verified_data`), `countries` = their countries sorted,
  `catalogue_total`, and `recall_note` = "The verified knowledge base answers for {n} of {total} catalogue universities
  (bachelor's in Computer Science). A university outside it, or another programme, gets 'No verified data yet'; no
  page is read during a run." Live mode returns today's dict plus `mode: "live"`; demo unchanged. The note is also
  served as a `MessageRef` (`msg.coverage.kb`, `msg.coverage.live` in `message_keys.py`) so `PreferencesScreen` renders
  it in en/ru/kk through `localize`; the country list is shown only in live mode. `PreferencesScreen`'s
  `live-mode-notice` paragraph is keyed on `mode`: in kb mode it says that no university page is read and nothing is
  sent to a search provider during a run (`data-testid="kb-mode-notice"`), in live mode it reads as today.
- **Tests.** `tests/test_frontend_contract.py::test_live_coverage_reaches_the_frontend_with_the_shape_it_declares`
  (additive keys; `types.ts` follows); `tests/test_knowledge_base.py::test_capabilities_name_the_knowledge_base_in_kb_mode`
  extended with the coverage block; `tests/test_api.py` live mode byte-identical apart from `mode`;
  `PreferencesScreen.test.tsx`: kb note in three locales, live note unchanged; `test_message_keys.py` sync guard.
- **Bar.** Gates; `seed_demo.py` byte-identical; the note's numbers come from the loaded KB, never a literal.

### RC-1 — the release ledger refreshed for kb mode (docs worker, ≈ 2.5 h; `RELEASE_CHECKLIST.md` only)

- **Do.** On the branch head, re-run every command the ledger cites and rewrite the stale rows with today's output:
  gate 1 (test counts), 2 (the `Saved` locator is `exact: true` in `e2e/profile-persistence.spec.ts`; cite the green
  `release-gates` run of `a15bf7d4` or its successor — PARTIAL stays if it is red, with the job named), 3 (build sizes
  from `npm run build`), 15–16 (`pip-audit`, `npm audit`, the secret scan), 25, 26 (skips), 79 (live) + RM-1 (kb), 82
  (coverage), 92 (the I18N_RESULTS inventory: 404 keys; the still-English list), 97 (PASS with the CI link, else stays
  PENDING with the reason). Replace the "CI on `main` is red since 2026-09-04" paragraph with the branch's state and the
  fact that `main` is at 2026-10-07. Add three kb-mode gates with real command output: **98** "kb mode reads no page
  during a run" (the `e2e:kb` network guard log and `test_knowledge_base`'s offline assertions), **99** "every KB fact
  shown carries its official quote and date, re-verifiable by `verify_evidence --from-kb`" (the v22 evidence report's
  pass count), **100** "the applicant can tell which universities have verified data before a run" (CAT-1 + RM-1
  tests). Recount the summary; rewrite "Order of work remaining" (item 5 is done; item 9 reads from I18N_RESULTS).
- **Bar.** `PASS` only with output shown; no gate's status moves on reasoning alone; the owner-dependent rows (87, 94,
  29) stay as they are.

### CO-1 — the confirm-queue order on auckland and khalifa (research worker 1.5 h → pipeline worker 2.5 h, 10 runs)

- **Step 1 (research, no code).** From `ns-floor-dev3` (39350480488) auckland and `ns-floor-dev2` (39350477901)
  khalifa, plus the `ns1-dev3` / `ns1-dev2` columns: (1) is the gold (and each twin form) in `sitemap_urls_seen`;
  (2) does `keep()` keep it — recompute offline with the production functions (`categorise_url`, `matches_field`,
  `matches_degree`, `names_other_degree_level`, `MAX_CANDIDATES_PER_CATEGORY` = 40 eviction) on the seen list, no
  network; (3) its position in `_confirm_programs`' queue (`sorted(ranked, reverse=True)` then `_prefer_exact_field`)
  against the 8 reads (`MAX_PROGRAM_CANDIDATES_CHECKED`); (4) what the 8 read URLs scored and why they outrank it — on
  auckland `computer-science.html`, the `/doctoral` and `/postgraduate` siblings and three conjoint pages (were they
  queued by `keep()` or inserted by `_queue_english_alternate` / `_queue_field_sibling` / `_queue_subpage_parent`?),
  on khalifa a news item and two minors ahead of `/program/bsc-in-computer-science`; (5) auckland's walker: the 88
  `walker_budget_exhausted` on undergraduate-options, foundation and summer-start pages. Output
  `docs/process/CONFIRM_ORDER_2026-10-22.md`: the per-case rank table and a verdict "shared mechanism on dev2 and
  dev3: <stage, mechanism>" or "not shared"; if shared, the rule as a flag, files, guard and the expectation per set.
- **Step 2 (pipeline, opens only on "shared").** One structural flag in `keep()` or `_confirm_programs`, from the shape
  step 1 names: an order (a candidate inserted beside a refused page goes behind the sitemap's own candidates; an
  exact-field slug ahead of a field-plus-other-subject slug — `_prefer_exact_field` already does this within one score,
  so the change would be across scores), a budget split (at most N confirm reads per URL directory before the next
  directory), or an exclusion class already in the code applied before ranking (`_url_excluded` for news paths). No
  word from a development page; the word tables stay as they are.
- **Tests.** Synthetic sitemaps reproducing the two shapes without their words; the off arm byte-identical; the
  budget files unchanged.
- **Dispatch.** `search_provider=none`, `columns=4`, four sets normal (`co1-<set>`) and knockout (`co1-ko-<set>`); the
  recorded guard on dev2 and dev3 (`rp-co1-<set>`).
- **Bar.** No hit lost on any set; 0 wrong; knockout not up; a stable gain on **both** dev2 (khalifa related → hit) and
  dev3 (auckland missed → hit); recorded guard identical or better. Default-on then.

### SEC-2 — security review of the commits since `5de8b6a3` (security worker, ≈ 2 h)

- **Do.** Same method and format as `SECURITY_REVIEW_2026-10-19.md`, range `5de8b6a3..HEAD` (≈ 114 commits). Surfaces
  to read first: `GET /api/universities` (`verified` parsing, the `knowledge` block — only KB data, no draft note);
  REL-1's `programme.related_reason.statement` (served text taken from an expert note's first sentence — confirm it
  carries no personal data, no non-official URL) and WHY-1's `kb_unknown`; `frontend/e2e/kb-env/serve-api.sh` and
  `sitecustomize.py` (fails closed? scratch paths under the repo? the dead proxy variables); the committed `read_pages`
  lists CI executes (`is_official`, heldout refusal, no `--robots-override-kb` outside the KB check); NS-1b's hop reads
  (`on_institution_site`, no DI-1 extra domain, the cap, no retry); LQ-2a's phrase (`local_query_phrase` refusals; no
  operator or quote can be smuggled from page text into `site:<d> "<phrase>"`); the fee range and per-credit parsing
  (no arithmetic on page text beyond min < max); `kb-refresh.yml` and the `a15bf7d4` image build change; `ci.yml`'s
  new step and artifact paths.
- **Output.** `docs/process/SECURITY_REVIEW_2026-10-22.md`; a finding fixable in ≤ 1 h is fixed in the ticket with a
  test; the rest are proposals with severity. SR-07 / SR-08 re-read against the new code.
- **Bar.** No held-out material opened; no provider called; nothing weakens `Fetcher`.

### I18N-2 — the remaining English sentences on the results screens (product worker, ≈ 4 h)

- **Change.** Templates in `app/domain/message_keys.py` and `msg.*` keys in `frontend/src/lib/i18n.results.ts`
  (en, ru, kk) for: `RequirementCheck.explanation`, `eligibility_checks[].explanation`, scholarship
  `classification_reason`, `ranking.bucket_reason`, axis `reason`, `knocked_out_by`, `ranking.disclaimer`, checklist
  `ordered_steps` text, `Conflict.subject` / `resolution_rule`, `capabilities.currency.stale_warning`, the `/questions`
  endpoint's `why_it_matters`; the Documents screen's fixed labels through `t()`. `annotate_result` attaches the refs on
  the way out only; stored payloads and the golden are unchanged. Parameters stay as the backend wrote them (names,
  URLs, intake labels). New provisional terms go to `docs/i18n/GLOSSARY.md` with the question each poses; nothing
  calls the fit a probability in any locale.
- **Tests.** `tests/test_message_keys.py` (the sync guard covers the new templates by construction; add the
  recognition cases), `i18n.results.test.ts`, `ResultDetail.i18n.test.tsx` (ru and kk re-renders), a Documents
  screen test, `TestDemoRunIsByteIdentical` unchanged.
- **Bar.** Gates; an unkeyed sentence still renders as its served English (`tOr`/`localize` fallbacks); gate 92 stays
  PARTIAL on its own terms (a person who advises applicants has not reviewed the terms) and RC-1 says so.

### TR-1 — the no-search trace explains itself (measurement worker, ≈ 2 h; lands before CO-1 step 2)

- **Change.** `DiscoveryTrace` gains, serialised only when non-empty: `confirm_queue` (every queued programme candidate
  with `score`, `source` seed / sitemap / navigation / walker / search, `read`, and the verdict or the reason it was
  not read), `sitemap_keep` (counts: seen, kept, evicted by the 40 cap, zero score, other level, excluded; plus the kept
  list per category, already bounded), `navigation_queue` (url, score, reason), `host_cost.samples` (url, seconds,
  bytes), and `stage_budget.stopped_by` per stage where missing. No behaviour change; the golden demo (fixture adapter)
  is unchanged.
- **Harness.** `scorecard.py`: per-case `gold_confirm_rank` (the position of any gold form or twin in `confirm_queue`,
  else `not_queued` / `not_seen`; evaluation only — the product never sees a gold URL); `stage_summary.py`:
  `confirm_queue_len`, `gold_queued_not_read` per set, inside the leak guard.
- **Tests.** `tests/test_discovery_trace.py`: the rows appear on a synthetic run and are absent on an empty one; the
  scorecard column on a fixture capture.

### CX-1 step 2 — the costs-stage rule step 1 names (pipeline worker, effort high, ≈ 3 h; conditional)

- **Precondition.** Step 1 — the per-page look at why the costs stage extracts no figure on pages it reads (G-16a
  item 3's two open questions: no figure, a figure for the wrong year, a table it does not parse; the ≈ 2–3 k readable
  characters) — is **in flight with another worker; do not duplicate it.** Step 2 opens when its verdict names one
  mechanism on ≥ 2 sets.
- **Change.** One flag in `cost/web_costs.py`, `structured_extraction.py` or the FE-2 block of `extraction.py`, from the
  mechanism (a table shape, a year-selection rule, a fee-page link class); synthetic fee pages in the tests without a
  development page's words; off byte-identical.
- **Dispatch.** Recorded replay, four sets normal (`cx1-<set>`) and knockout (`cx1-ko-<set>`).
- **Bar.** `pages_fetched_ok:costs` up on ≥ 2 sets; tuition claim precision stays 1.0; no new wrong claim; knockout
  `wrong_scope_claim_rate` not up; `seed_demo.py` byte-identical. 13-Q2 (a) by construction (dev-wide mechanism).

### PERF-1 — kb-mode performance budgets (test worker, ≈ 1.5 h)

- **Do.** On a scratch database with the 501-row catalogue in kb mode: p50 / p95 of `GET /api/universities?limit=500`
  (the knowledge block per row) over 20 requests; `load_knowledge_base` wall time (cold); a kb-mode run of the e2e's
  nine universities end to end (from the `e2e:kb` timings); `npm run build` gzip sizes beside gate 3's 74.0 kB. Pin two
  budgets as tests sized like `tests/test_named_bands_linear.py` (generous on CI: the list ≤ 1.0 s, the KB load ≤ 0.5 s)
  in `tests/test_runtime_budgets.py`; the numbers go to RC-1's gates 3 and 83.
- **Bar.** No product change; a budget test that fails on CI is reported with its number, not loosened.

### SG-1 — sitemap guesses on a crawl-delay host (pipeline worker, ≈ 2 h; after CO-1 step 2 on `live_discovery.py`)

- **Change.** `SITEMAP_GUESS_CAP = 4` (today's four) and, behind `--sitemap-guess-cap`: when robots.txt names no sitemap
  and the host asks a crawl delay ≥ `SLOW_HOST_SECONDS`, guess `/sitemap.xml` only; on any host, stop guessing after
  two consecutive 404s. Structural; `SITEMAP_FALLBACK_PATHS` unchanged.
- **Tests.** A fake fetcher counts guesses on a crawl-delay host and on a 404-everything host; off byte-identical.
- **Dispatch.** `search_provider=none`, four sets normal (`sg1-<set>`); recorded guard dev4 (`rp-sg1-dev4`).
- **Pre-registered.** ctu `case_time` −20–30 s; kit, itu, msu, um, ethz, utokyo −3–6 s; hits unchanged everywhere.
  **Bar.** No hit lost; 0 wrong; reads down with identical labels (DoD step 3); then default-on.

### IC-2 — the ceiling tool records the hop-1 parent (measurement worker, ≈ 1.5 h, one CI run)

- **Do.** `index_ceiling.crawl_two_hops` records, for every target reached at hop 2, the hop-1 page's URL, its anchor text
  (institution text only) and its rank under `programmeish`; the report gains `hop1_parent`, `hop1_anchor`, `hop1_rank`.
  Run `mode=index_ceiling` once; commit the development report (dev cases per URL; dev5 aggregates only) as
  `evaluation/research/data/index_ceiling.dev-2026-10-22.json` and add the rank table to `INDEX_CEILING_2026-10-19.md`.
- **Bar.** No heldout case in the report; the per-case table of NO_SEARCH_FLOOR §2 reconciles with it or the difference
  is written down.

### KB-1 — `merge_entries` gaps and comment drift (product worker, ≈ 1 h)

- **Change.** `merge_entries` compares facts on `verified_on`, then `accessed_on` (P8); the built programme block with an
  access note survives an import with no verified page (REL-1 did the settled-route half — assert the note half); the
  comments on `COURSE_LEAD_GUARD` and `ABSTAIN_ON_UNREADABLE_ENTRY` say "on" (P9).
- **Tests.** `tests/test_knowledge_base.py`: the two merge cases. **Bar.** v22 merged view unchanged (assert on the
  committed files).

## 4. Dispatch table (main session, 0 worker hours)

Common inputs as NEXT_CYCLES_2026-10-20 §7 (`benchmark-capture.yml`, `runner=ubuntu-latest`, `mode=expert_paired`,
`seconds_per_case=120`, `max_pages=60`, `case_parallelism=5`, `max_search_queries` empty). Score cohort on
`ground_truth.reviewed11.json`, dev2/dev3/dev4 on `draft3` with `--allow-drafts`; dev5 with `--summary-only` only.

| run | set(s) | inputs that differ | `run_tag` | read |
|---|---|---|---|---|
| **gate 97 link** | — | the `release-gates` run of `a15bf7d4` (or the next green one) | — | green → RC-1 writes PASS with the link; red → the job name goes to RC-1 and a fix ticket opens |
| **D-F5 dev5 no-search floor** (still pending) | dev5 (13 cases) | `search_provider=none`, `columns=1`, `extra_args` empty | `ns-floor-dev5` | `scorecard --summary-only` on `dev5.draft1 --allow-drafts`; **pre-registered** (NEXT_CYCLES_2026-10-21 §4): found ≤ 3/8 readable, wrong 0, over budget 0, kbtu and satbayev `unavailable` |
| **PC-1** (when built) | 4 sets normal + knockout; dev3 + dev4 alone; dev3 R4 | `search_provider=none`, `columns=4`, `extra_args=--homepage-hop-reads --<pc1>` / `--<pc1>` / `--local-catalogue-entry --<pc1>` | `ns1b-*`, `ns1b-ko-*`, `pc1-*`, `ns-r4b-dev3` | §3 PC-1 bar |
| **PC-1 guard** | dev3, dev4 | `search_provider=recorded`, `extra_args=--homepage-hop-reads --<pc1>` | `rp-ns1b-*` | no hit lost, no new wrong page, `recorded_search_misses` = off arm |
| **CO-1** (if shared) | 4 sets normal + knockout; guard dev2 + dev3 | `search_provider=none` / `recorded`, `extra_args=--<co1>` | `co1-*`, `co1-ko-*`, `rp-co1-*` | §3 CO-1 bar |
| **CX-1** (if opened) | 4 sets normal + knockout | `search_provider=recorded`, `extra_args=--<cx1>` | `cx1-*`, `cx1-ko-*` | §3 CX-1 bar |
| **SG-1** | 4 sets no-search; guard dev4 | `extra_args=--sitemap-guess-cap` | `sg1-*`, `rp-sg1-dev4` | §3 SG-1 bar |
| **IC-2** | — | `mode=index_ceiling` | — | the committed report |
| **D-D interaction check** (optional, idle runners) | 4 sets | `extra_args=--no-<rule>` for `abstain-on-unreadable-entry`, `confirm-head-identity`, `reject-combination-head`, `reject-subpage-head` (their paired runs predate the later flips), knockout arms too | `rp-abl-<rule>-<set>` | identical → absorbed by a later rule (ledger note); a stable loss → still load-bearing; no default change from this alone |

The KB refresh workflow is **not** dispatchable from the branch (404 on `kb-refresh.yml`: the file is not on `main`);
it is in §6.

## 5. The cycles

| cycle | dispatches (0 worker h) | worker tickets (parallel, disjoint files) | gate / read |
|---|---|---|---|
| **19 (now)** | gate 97 link; D-F5; PC-1 arms the moment it lands (13 runs) | **PC-1** (pipeline, high; holds `live_discovery.py`), **RM-1 → RC-1** (one product worker: RM-1 first, RC-1 cites it), **CO-1 step 1** (research, no code), **SEC-2** (security) | PC-1's bar → NS-1b + PC-1 default decision in LOOP_REPORT and `hypotheses.json`; D-F5 against its pre-registration (aggregates); CO-1's verdict decides whether step 2 opens; RC-1 counted on the branch head |
| **20** | CO-1 arms (10) when built; CX-1 arms (8) if opened | **TR-1 → CO-1 step 2** (one pipeline worker, sequential on `live_discovery.py`), **I18N-2**, **PERF-1**, **CX-1 step 2** if step 1 names a dev-wide mechanism (`web_costs.py` / `structured_extraction.py`, disjoint) | CO-1 bar; CX-1 bar; PERF-1 numbers into RC-1; the trace rows on the next floor run |
| **21** | SG-1 arms (6); IC-2's CI run; D-D interaction check as runners idle; re-score the day any signature arrives (§6) | **SG-1**, **IC-2**, **KB-1**, follow-ups the verdicts name (a PC-1 or CO-1 diagnosis, a SEC-2 proposal over 1 h) | SG-1 bar (reads down, labels identical); the no-search bench declared at its ceiling or with its residue table |

Expected after cycles 19–21 without the owner: recorded-replay hits unchanged at 26/39; no-search floor 9/39 → 11/39
(PC-1) → 12–13/39 (CO-1), i.e. the measured ceiling, after which that bench is exhausted too and its residue is written
by class; the research-mode screen and the release ledger say what kb mode is; every sentence the kb journey shows is
localisable; a second security pass on the launch surfaces; the trace and the ceiling report explain the next floor run
without a probe. With the owner's answers: §6.

## 6. What each pending owner answer unlocks

| answer | unlocks (one line) |
|---|---|
| **U7**, deadline variant A (skip the eligibility deadline check when every stated date precedes the intake's cycle) or B (soften to a non-GAP note) | the Fudan-type row stops reading GAP for a window the applicant never had; `eligibility.evaluate` is domain code shared with live mode, so `seed_demo.py` is re-checked; ≈ 1.5 h after the answer |
| **KFUPM** (two official pages disagree on the waived tuition) | one held-back tuition fact enters v23 (SAR 0, standing policy) or stays `unknown` with the disagreement recorded as its kind; no other row moves |
| **Native-name overlay signature** (`catalogue_native_names.proposed.json`) | production `native_name` for the signed rows; the identity gate reads dev5 **7/13 → 9/13** (IG-2), development sets unchanged; the 15-Q2 gate arm becomes credible; NN-1b's fold is then measurable; LQ-2a's `native_name` branch stops being inert |
| **Three twin signatures** (Q1 uct keep; Q2 kuleuven, now "yes if (b) without the credits clause" after TW-2; Q3 tcd) | `dev2.draft4` / `dev3.draft4` applied after CI `verify_evidence`: knockout dev2 1 → 0 (tcd), dev3 kuleuven wrong → hit in readable repetitions, uct unchanged; recorded hits 26 → 27–28/39 by re-score, **0 code** |
| **Exa key** (01-Q3 / Q6; Tavily beside it) | R1 (44 cases, `columns=1`, cap 264) → the `recorded-search/2` store with titles → re-baseline (warsaw `missed → hit`, 10 regime-C labels measurable); the LQ-2a `query_probe` (15 queries, puc's gold in the top 10 is the bar); then R2 (dev5 baseline, cap 312, aggregates) once 13-Q1…Q5 are signed → 13-Q2 (b) for the eight flipped rules, the G-16a dev5 column, and the no-search bench's 26 search-dependent cases |
| **Self-hosted runner** (01-Q4: the owner's computer as a vantage point, same agent, same robots, no retries) | one `read_pages` dispatch of RP-1's **105 rows on 28 universities** (63 access cells, the 25 kb-refresh blocked rows, UCL and Alberta's programme pages, Monash's English cells) drafted as round 8 was; the access five of the development misses (aalto, toronto, hku, kaznu, ub) re-probed for the floor; the kb-refresh workflow's `runner: self-hosted` input |

Two more, not in the pending list: **merging the branch to `main`** is what lets `kb-refresh.yml` run at all (schedule and
`workflow_dispatch` both read the default branch) and what starts the 60-day clock on its schedule; **13-Q1…Q5 and
15-Q1…Q5** (the second look's arms and reading) are the only route to a target-6 number, and nothing in cycles 19–21
touches them.

## 7. What this plan does not build, and why

| item | why not now | re-opens when |
|---|---|---|
| R4 on by default for the no-provider regime, on its own | one set (kit); puc is unstable for the same clock reason as NS-1b | PC-1's `ns-r4b-dev3` arm gains puc stably — then it is the cheaper verdict and is recommended instead of NS-1b |
| the kaist catalogue-role refusal (cohort) | one set, behind a registry seed | a second development case reads the gold in a catalogue role |
| AW-3 local-language award value readers, PD-1 PDF readers, CA-1 confirm-abstention | gain 0 on every bench today (NEXT_CYCLES_2026-10-21 §7, unchanged) | the triggers written there |
| IB-1, AI-1, AW-1, SH-1 default-on, LL-1, SP-2 | one set, zero sets, or fired with no gain — recorded | REACH_ROWS / LOOP_REPORT triggers |
| a KB manual round | §2.3: the pool is unpublished, access or unresearched cells; rounds 7–10 yielded ≈ 1 fact per university-hour | 01-Q4 (RP-1's list), or spring 2027 fees |
| U9, B7, D7, P3, P4 | owner decisions (a label, the brand, a data review, two date conventions) | the answer |
| the own index as a provider, Common Crawl discovery, model extraction, any heldout look, DoD targets or denominators, the 6 / 60 / 120 budget, the 2026-10-19 defaults before R2 | as NEXT_CYCLES_2026-10-20 §9 and 2026-10-21 §7 | — |
