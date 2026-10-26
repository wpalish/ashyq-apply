# Next cycles plan, 2026-10-21: cycles 16–18, all at $0 and without the owner's answers

Planner, 2026-10-21, from the cycle 14–15 record (`LOOP_REPORT.md` 2026-10-20 01:15 → 04:40), `REACH_ROWS_2026-10-20.md`,
`LOCAL_LANGUAGE_LOCO_2026-10-20.md`, `HELDOUT_PROVENANCE_AUDIT_2026-10-20.md`, `TWIN_CHECKS_2026-10-20.md`,
`KNOWLEDGE_BASE.md`, `KB_E2E_SMOKE_2026-10-19.md` (v10 and v18 sections), `SEARCH_DEFINITION_OF_DONE.md`, the five
wayfinder maps' ticket statuses, the committed KB `2026-10-20.kb-cs-bachelor.20` with `kb_imported_dev.json`, the
top-up round READMEs 7–10, `RELEASE_CHECKLIST.md`, and the code. Development data only: **no heldout file, capture,
log or label was opened; no dev5 per-case row was read; no other scratchpad was read; no provider was called; no credit
was spent.** The three inventory scripts (KB per question, merged KB view, unknown-reason classes) are in this session's
scratchpad and read only the two KB files, the top-100 list and the four development corpora.

Constraints, unchanged: paid search frozen; no free key (Q6 open); dev5 design-blind (13-Q1, treated as binding); a rule
goes on by default only under 13-Q2; the 6 / 60 / 120 budget; no PR unless the owner asks; model identifiers stay out.

## 0. Where we stand after cycles 14–15

| row | cohort | dev2 | dev3 | dev4 | all |
|---|---|---|---|---|---|
| gold pages hit / wrong / related / missed, recorded replay (today's defaults, LV-1 on) | 5/0/0/5 | 6/0/1/3 | 10/0–1/0/3–4 | 5/0/1/3 | **26/39**, wrong 0 (+ kuleuven flake) |
| the same with **no search provider** (D-F, `columns=1`) | 4/0/0/6 | 2/0/1/7 | 3/0/0/11 | 0/0/0/9 | **9/39**, wrong 0 |
| sitemap ∪ two-hop **ceiling** of an own index (`INDEX_CEILING`) | 3 | 1 | 6 | 1 | 11/39 |
| knockout guesses (gold hidden) | 0 | 1 (khalifa) | 1 (uio) + flake | 1 (ctu) | 3 + flake |
| precision · wrong scope · over budget | 1.0 · 0 · 0 | same | same | same | targets 1, 2, 5 met |

What closed since the 2026-10-20 plan: LV-1 **on**; LL-1, SP-2, SH-1 **off** (fire, no gain); D-D ablations complete
(8 load-bearing, 4 `no_dev_evidence`, none harmful); H-B partial (seeds carry claims, not hits); H-C confirmed (LOCO-1:
store 20 → 15, pages 18 → 13; the mechanism is one alias per language); H-D confirmed narrowly (et integrated study);
H-E residue measured (IG-2: dev4 8/9, dev5 7/13 → 9/13 with fold + proposed native names, overlay unsigned); HP-AUDIT
re-sourced 114 rows, removed 0; reach shapes S4 / AI-1 / AW-1 failed step 1 (one set or zero sets), the only cause found
is language (English-only `_AWARD_SIGNALS`), so AW-2 was built as a language-coverage rule and its 8 replays were running
at 04:43 (cohort, dev2, dev4 done; dev3 in flight); ES-2 records page language and classifier category on funding
outcomes. KB v20: 808 facts, 98 of the 98 eligible top-100 rows (the two absent rows are the heldout exclusions by design),
programme page known for **89/98 at runtime** (the imported development pages fill 20 of the built file's 29 gaps),
verified data for 95/98, document lists for 71. CI `read_pages` on the blocked list: the GitHub runner is refused by the
same hosts as the container.

**Two benches, not one.** The recorded-search replay is exhausted for rule gains (§2.1). The **no-search bench** is not:
`search_provider=none` needs no store, is deterministic, is the regime the live path runs in for a non-KB university
when no key exists, and today sits **2 cases under the measured ceiling on dev3 and 1 on dev4** (9/39 vs 11/39). That
gap is the one place left where a $0 rule can still move a programme-page row on two sets.

## 1. The ranked list

Ranking = expected movement (a DoD row, a launch gate, or an applicant-visible correctness fix) per worker hour.
Dispatches cost no worker time and are in §4. "Why it pays" is the 13-Q2 (a) question, or the launch question, answered
in advance. Effort `medium` unless marked.

| # | item | kind | worker h | runs | what it moves | why it pays on a set, or a screen, that did not motivate it | expected outcome |
|---|---|---|---|---|---|---|---|
| 1 | **CAT-1** verified-data coverage in the catalogue and capabilities | product (API + UI) | 4 | 0 | launch readiness: the kb-mode counterpart of release gate 79 ("live mode says how far it reaches") | every catalogue card today reads "Programme verification needed · Not assessed · Research required" and a "Historical estimate" fee, for the 95 universities whose verified data the run will then show; the applicant cannot pick the 5 that have data | per-card "verified knowledge base: n/6 answers, documents, programme page" chip, a filter, the KB fee beside the historical one; `/api/capabilities` lists the KB adapter and marks web adapters inactive in kb mode |
| 2 | **NS-1a** the no-search floor against the ceiling, per case and stage | research, no code | 2 | 0 (re-read of `ns-floor-*` and `INDEX_CEILING`) | target 3 on the live path beyond the KB, no key | the gap is on dev3 (≥ 3 cases: of auckland, imperial, ucph, unsw, iitd, puc) **and** dev4 (kit): a cause shared by two sets is the two-set evidence the replay bench could never supply | a table case → reachable by (bounded sitemap / hop 2) → what the no-search run did (trimmed, never followed, read and refused, clock) → the shared cause, or "none shared" |
| 3 | **NS-1b** the rule NS-1a names, behind a flag, measured on the no-search bench | pipeline rule, effort **high** | 3 (conditional on 2) | 10 | target 3 (+1–3 hits without search on dev3, +1 on dev4), 0 wrong | measured on `search_provider=none` where the store cannot help; the recorded replay is the guard arm (no hit lost, no new wrong page) | 9/39 → 11–13/39 with 0 wrong; default-on only with a stable gain on both sets |
| 4 | **E2E-KB** a kb-mode browser journey in CI | test harness | 3.5 | 0 (CI) | launch readiness: the 13 kb-mode UI fixes of the two smokes (D1–D6, U1–U8) are covered by unit tests only; CI's e2e runs in demo mode | a committed Playwright spec against a scratch database in kb mode re-runs the smoke every push; the smokes' method is written down and was done twice by hand | one spec, three locales, the shortlist card, the four detail tabs, the documents screen; red on any regression of the 13 fixes |
| 5 | **REL-1** "no standalone CS bachelor" said as a fact, not asked as a question | product (kb_build + runtime + UI) | 2.5 | 0 | kb-mode correctness for 7 of the 98 entries (6 related-only, 1 not offered) | the entries record a verified related page and its reason; the runtime still asks the blocking "Which official page publishes the programme?" — the KB already knows the answer and withholds it | a non-blocking statement with the official related page: "no standalone bachelor's in Computer Science; CS is a major within <degree>", or "not offered", in en/ru/kk; the 2 access cases keep the question |
| 6 | **LQ-2a** the local query from the site's own words: code behind a flag, offline table | rule (regime C) + research | 3 | 0 | H-C's confirmed mechanism; the one rule a key unlocks on day one | built from each homepage's own link text, so no language row can be fitted in advance; measured only when a key exists, but the phrase table on the 28 development cases is regime A and tells now whether the phrase reproduces the gold title (puc singular vs uba plural, tec in neither) | flag off byte-identical; a table case → phrase → equals the gold title shape yes/no; the R1-adjacent `query_probe` list pre-registered |
| 7 | **RP-1** the read list for the owner's computer: every access-class KB cell | data prep | 1 | 0 | KB coverage the day 01-Q4 is answered; zero drafting then | 57 unknown cells on 22 universities are access-class (container and GitHub runner alike); the only lever is a different vantage point; the list is owner-independent to write | one `read_pages/self-hosted-2026-10-21.json` (≤ 300 URLs: the 57 cells' target pages, the 25 kb-refresh "blocked" rows, the 2 access programme pages), with a topic per row |
| 8 | **WHY-1** the unknown reason class on the row | product (kb_build + API + UI) | 2.5 | 0 | kb-mode honesty: an empty cell says *why* | 198 unknown rows: 81 "the university publishes no such value", 57 access, 44 generic draft notes; today they all read "unknown" | `unknown[].kind` (controlled vocabulary, derived at build from a reviewed table, no fact changed); the Requirements / Costs / Funding tabs show "Not published by the university (expert check <date>)" vs "official page not readable from our servers" vs "not yet researched" |
| 9 | **TW-2** the kuleuven twin: fill the §4.2 excerpt from the CI read | research | 0.5 | 0 (artifact of the 2026-10-20 `read_pages` run) | Q2 signable; dev3 wrong → hit in readable reps after signature | the rows were read on the runner on 2026-10-20 (topup_round8 README: "two rows with seed_id kuleuven … ignored"); TW-1's conditions (a)–(c) can be checked from them | `TWIN_CHECKS_2026-10-20.md` §2 Q2 gets the `final_url` check and the quote; nothing applied |
| 10 | **G-16a** evidence-stage sizing on the four development sets | research, no code | 2 | 0 | ticket 16 items 1, 3, 4 (dev-wide vs set-dependent), ahead of R2 | the unlabelled-claim share, the costs-page refusal reasons and award expressibility read the same way on four sets as they will on dev5 aggregates; the dev5 column is added when R2 exists | `EVIDENCE_GENERALISATION_2026-10-21.md` with the three tables; no DoD row moves |

Not on the list, and why: §2 (the exhausted benches and the KB rounds), §7 (rules that would gain 0 on any bench today:
AW-3 local-language award value readers, PD-1 PDF readers, CA-1 confirm-abstention, the three one-set knockout shapes).

## 2. What is exhausted, honestly

### 2.1 The recorded-search replay, for rule gains: exhausted

| what the v1 store can still measure | what it cannot | evidence |
|---|---|---|
| guards and ablations (regime A), knockout arms, the no-seed path (regime B lower bound), harness changes, ES-1/ES-2 rows | any rule that changes a query (regime C), the 13 misses (access 5, department host 1, other registrable domain 1, replay artefact 1, labels 2, never returned 3), the reach shapes (S4 one set, S5 fired with no gain, S6/S7 no row), the three remaining knockout guesses (one shape each: delivery-site qualifier, related-field subtitle, process URL) | NEXT_CYCLES_2026-10-20 §2–§4; REACH_ROWS §S4/AI-1/AW-1; SH-1 and LL-1 replays; GOLD_KNOCKOUT §3 |

AW-2 is the last replay with a plausible gain (dev4 rwth). After its verdict the recorded bench runs only guard arms.

### 2.2 KB manual rounds: stop, with the numbers that say why

The merged KB as the runtime sees it (built v20 + imported development pages):

| measure | value |
|---|---|
| entries / eligible top-100 rows | 98 / 98 (the two other rows are heldout exclusions) |
| programme page known | 89; the 9 others: 6 related-only (Melbourne, Sydney, PSL, IP Paris, Lund, KTH), 1 not offered (LSE), 2 access (UCL, Alberta) |
| entries with verified data | 95 |
| core questions answered (known or verified not-applicable) per entry | 6/6: 17 · 5/6: 37 · 4/6: 22 · 3/6: 9 · ≤ 2/6: 13 |
| facts | 808 (documents 438 on 71 entries; english 97; tuition 73; scholarship 130; deadline 64; gpa 6) |
| stale facts | 141: tuition 37 (2026/27 fees, re-published spring 2027), deadline 11, documents 93 (another cycle's list, said so) |
| caveated facts (owner flags on) | 40 |

The 198 `unknown` rows by class (reason text, classified by a deterministic keyword table in the scratchpad):

| class | rows | can a container round fill it? |
|---|---|---|
| the university publishes no such value (no GPA minimum, holistic, no English minimum for the route, no scholarship found) | 81 | **no** — nothing to find; WHY-1 (#8) is the honest representation |
| access: the official page refuses the container and the GitHub runner (HTTP 403, robots, reset) — 22 universities | 57 | **no** — RP-1 (#7) prepares the owner's-computer read; 01-Q4 decides |
| generic draft note ("expert did not establish it"), 2026-10-19 rounds | 44 | rarely — rounds 7, 9 and 10 re-checked these on current pages |
| quote failed CI (value not in the excerpt, quote not found) | 7 | maybe, one re-read each; folded into RP-1 where the host is blocked |
| undated deadline / other year only / not researched | 9 | no — the year rules and the 2027/28 publication schedule decide |

Round yields on the container-reachable set, from the READMEs: round 7 (English, 12 universities) **0** facts; round 8 (CI
read, 4 universities) 2 drafts (CUHK deadline + documents, KU Leuven documents); round 9 (scholarships, 8) 2 facts + 2
not-applicable; round 10 (tuition, 14) 2 facts + 1 held back for the owner. That is the ≈ 1 fact per university-hour the
loop recorded, and the remaining pool is the table above. **No manual round is scheduled in cycles 16–18.**

When a round pays again: (a) the owner's computer as runner (01-Q4) — the 57 access cells and the 25 kb-refresh blocked
rows in one `read_pages` batch, drafted from the artifact as round 8 was (RP-1 writes the list now); (b) spring 2027,
when 2027/28 fees replace the 37 stale tuition facts (the kb-refresh cron queues them once it runs from `main`).

### 2.3 Measurement that already exists and needs no work

`search_failures` and `search_failures_by_status` rows (the outage guard asked for on 2026-10-19) are in `stage_summary`.
ES-1 and ES-2 rows print on every capture made after `42d6181b` / `6aec5fc6`. The scorecard's readable denominators,
knockout arms and `--summary-only` leak guard stand.

## 3. Worker tickets

Common to every ticket: design on cohort/dev2/dev3/dev4 captures, the KB files and code; no dev5 or heldout page, label,
capture or row; word tables dictionary-grade for every `languages.json` language at once; a pipeline flag is off by
default with its `NEGATABLE_RULES` entry; HANDOFF §8 line for any contract change; golden demo byte-identical
(`UNIMATCH_DEMO_MODE=true UNIMATCH_ENABLE_BROWSER_TIER=false python seed_demo.py`, brief §5.7 order); gates green
(AGENTS §5); commit locally with the `Agent:` trailer; the main session cherry-picks, runs the suite and dispatches.
`runner.py` and `scoring.py` are touched by no ticket here except where named (REL-1 touches `runner.py`'s KB question
only).

### CAT-1 — verified-data coverage in the catalogue and capabilities (product worker, ≈ 4 h)

- **Do.** `backend/app/api/routes_universities.py::view` gains a `knowledge` block per university, computed from
  `app.knowledge.load_knowledge_base()` (loaded once per process, by `seed_id` then official domain as
  `claims.entry_for` does): `in_kb`, `programme_page` (`known` / `related_only` / `not_offered` /
  `unknown`), `core_answered` (0–6: known or verified not-applicable), `documents` (item count), `verified_on`,
  `stale_count`, `review_label`, and `tuition` (`amount`, `currency`, `period`, `academic_year`, `stale`, `caveat`) when
  a fee fact exists. `null` in live and demo mode. `GET /api/universities` accepts `verified=true` to keep only
  `in_kb` rows and returns `kb_total` beside `catalogue_total`. `routes_meta.capabilities` adds
  `{"name": "verified-knowledge-base", "role": "discovery and verification", "live": false}` and, in kb mode, marks the
  six live adapters (the registry and the five `web-*` readers) `"active": false` (the field is additive; `live` is
  unchanged).
- **UI.** `UniversityCatalogue.tsx`: in kb mode the chip row reads "Verified knowledge base · n/6 answers · documents ·
  programme page" (or "No verified data yet"), the `dl` shows the KB fee ("CHF 2,190 per semester, fee policy" with its
  caveat / stale chip reused from `format.ts`) above the historical estimate, which is kept and labelled as such; a
  "verified data only" checkbox drives `verified=true`; the heading count says "n of N universities have verified data".
  Live and demo mode render exactly as today. Strings in en/ru/kk (`i18n.results.ts` or the catalogue dictionary).
- **Tests.** `backend/tests/test_university_catalogue.py`: kb mode → the block for an entry with facts, a related-only
  entry, a university outside the KB; live mode → `null`; `verified=true` filters; `tests/test_frontend_contract.py`
  `CONTRACT` gains the new keys and `types.ts` follows. `UniversityCatalogue.test.tsx`: chip, fee line with caveat, filter,
  the three locales, live mode unchanged. `tests/test_api.py` (the capabilities test) and `tests/test_knowledge_base.py`:
  the KB adapter row and `active=false` in kb mode, absent in live mode.
- **Bar.** No network in any test; `seed_demo.py` byte-identical; `npm run build` size within the gate; the catalogue
  shows nothing a result row would later contradict (the fee line uses the same stale / caveat rules as the detail).
- **Why it pays.** Release gate 79 passes for live mode by saying how far the registry reaches; kb mode has no such
  statement anywhere before the run. This is the launch-day screen.

### NS-1a — the no-search floor against the ceiling (research worker, ≈ 2 h, no code)

- **Do.** Download the four `ns-floor-<set>` artifacts (`expert-recovery-<run id>`, 2026-10-20 01:15 dispatch, one
  capture per case) and read, for every development case the `INDEX_CEILING` per-case table marks reachable (bounded
  sitemap, or linked within two hops): did the no-search run (1) list the gold in `sitemap_urls_seen` (or trim it:
  `MAX_SITEMAP_DOCUMENTS`, `SITEMAP_TRIM`, `too_large`, `unparseable`); (2) queue it from the catalogue walker / hop
  (`navigation_candidates`, `hop_entry_points`); (3) read it and refuse it (`page_outcomes` detail, classifier verdict,
  `profile_rejects` reason, CH-1 / CQ-1 / SP-1 head rules); (4) run out of reads or clock before it. Name the stage per
  case for dev3 (auckland, imperial, ucph, unsw, iitd, puc) and dev4 (kit), and record what the three dev3 hits and the
  four cohort hits did right. Also list every reachable case on cohort / dev2 for the same stages.
- **Output.** `docs/process/NO_SEARCH_FLOOR_2026-10-21.md`: the stage table; a verdict "shared cause on dev3 and dev4:
  <stage, mechanism>" or "no shared cause"; if shared, the NS-1b rule written as a flag name, the files, the guard, and
  the pre-registered expectation per set (which cases move, which must not).
- **Bar.** None (no pipeline change). Development captures and the ceiling doc only.

### NS-1b — the rule NS-1a names (pipeline worker, effort high, ≈ 3 h; runs only if NS-1a finds a shared cause)

- **Change.** One flag, `--<ns1-flag>` / `--no-…`, in the module NS-1a names (`live_discovery.py` sitemap reader or hop
  walker, or `navigation.py`); nothing in `intent.py`, the classifier or the evidence stages. The rule must be a
  structural one (a trim, an order, a budget split, a link class), never a word from a development page.
- **Tests.** Synthetic sitemaps / homepages reproducing the dev3 and dev4 shapes without their words; the off arm
  byte-identical; the 60-request and 120 s budgets unchanged (`test_read_budget*`).
- **Dispatch (§4).** `search_provider=none`, `columns=4`, `extra_args=--<ns1-flag>`, four sets normal + four knockout
  (`ns1-<set>`, `ns1-ko-<set>`); plus the recorded replay on dev3 and dev4 as the guard (`rp-ns1-<set>`).
- **Bar.** No-search: no hit lost on any set, 0 wrong pages (today 0), knockout `wrong_programme_pages` not up, a stable
  gain on **both** dev3 and dev4 (13-Q2 a by construction, since the gap is two-set). Recorded replay: identical or
  better, `recorded_search_misses` = off arm. Default-on then; otherwise `hypotheses.json` with the cause.

### E2E-KB — the kb-mode journey in CI (test worker, ≈ 3.5 h)

- **Do.** `frontend/e2e/kb-journey.spec.ts` and a second Playwright project (`playwright.kb.config.ts`, script
  `e2e:kb`) whose web server starts the API and worker with `UNIMATCH_DEMO_MODE=false`, `UNIMATCH_KNOWLEDGE_MODE=kb`,
  `UNIMATCH_SEARCH_PROVIDER=none`, `UNIMATCH_ENABLE_BROWSER_TIER=false`, a scratch SQLite database migrated by
  `alembic upgrade head`, and the network guard the smokes used (`sitecustomize.py` refusing every non-local socket; one
  probe asserts it blocks). The spec: the CS-bachelor profile (Kazakhstan, fall 2027, IELTS 7.0); nine catalogue
  universities covering the smoke's cases (a caveated deadline, a standing fee per semester / per programme / per year,
  another cycle's document list, a passed deadline, a plain current entry, a university without document facts, one
  outside the KB); approve all, collect documents; assert on the shortlist card, the hero, and the Requirements, Costs,
  Documents and Sources tabs in en, ru and kk exactly the 13 facts the smokes fixed (D1–D6, U1–U8: chips "Current, with
  caveat" / "not current" / "deadline passed", the kb completeness chip, the open-question count, localised fee lines
  and steps, the "no fee in the knowledge base" wording, the "instead" question only where another language is named),
  and that the browser made 0 external requests.
- **CI.** `ci.yml` runs `e2e:kb` beside `e2e` (same browser install step; artifact `playwright-report-kb`).
- **Bar.** Green on the committed KB; red when any of the 13 fixes is reverted (verify by reverting one locally); runtime
  ≤ 5 min; no test reads the network. `RELEASE_CHECKLIST.md` gains one gate line for it, `PASS` only with the CI output.

### REL-1 — "no standalone CS bachelor" as a statement (product worker, ≈ 2.5 h)

- **Change.** `kb_build`: carry the related draft's reason and the `programme_offered: false` flag into the entry
  (`programme.related_reason`, `programme.offered`; today `related_programme_urls` is kept but its reason and the flag
  are dropped). `app/knowledge/__init__.py`: `KnowledgeEntry.programme_route` → `known` / `related_only` /
  `not_offered` / `unknown`. `runner._no_verified_programme_page`: for `related_only` return a **non-blocking** question
  "No standalone bachelor's in Computer Science is published; the closest official route is <degree> (<official URL>).
  Does that route suit you?" (topic `official source`, the related URL as the suggested source); for `not_offered`,
  "The university publishes no bachelor's in Computer Science (checked <date>)." as a statement with no question; for
  `unknown` (access), today's blocking question. `ResultDetail.tsx` and `Deadline`/hero unchanged; the Requirements tab's
  KB question block shows the statement; en/ru/kk keys in `message_keys.py`.
- **Tests.** `tests/test_knowledge_base.py` (the build and merge tests live there, beside `test_kb_owner_flags.py`): the
  two fields survive the build from a related and a not-offered draft; the three routes → the three outcomes, blocking
  only for `unknown`; `test_message_keys.py`; `ResultDetail.kb.test.tsx` (en, ru, kk). A KB rebuild from the same drafts (`v21`), facts byte-identical except the two new programme fields
  (assert with a diff script in the ticket).
- **Bar.** Gates; `seed_demo.py` byte-identical (demo ignores kb mode); no entry changes route except the 7 named.

### LQ-2a — the local query from the site's own words, offline half (rule worker, ≈ 3 h)

- **Change.** As `LOCAL_LANGUAGE_LOCO_2026-10-20.md` §5: `LOCAL_QUERY_FROM_PAGE_EVIDENCE = False`
  (`--local-query-from-evidence`); `intent.LocalQueryTerms.phrase: str | None`, rendered by `queries_for` as one quoted
  phrase (≤ 8 words, digits and personal names refused, `_reject_applicant_data` applied) in place of the alias in the
  one `local_language` query; `live_discovery.py` builds it after the homepage and navigation read from (1) the link text,
  in the page's `<html lang>`, of a link R4 / LL-1 classifies as a programme listing or page and whose text contains a
  localized alias head, else (2) the seed record's `native_name`, else (3) today's words. Off → byte-identical.
- **Offline table (regime A, no run).** For the 28 development cases with a local-language gold or a known miss, fetch
  the homepage (and its programme-listing link, one hop) through the production `Fetcher` (robots first, our agent, no
  override; dev cases only) and record the phrase the rule would send beside the gold title shape:
  `docs/process/LOCAL_QUERY_PHRASES_2026-10-21.md`. Pre-register the key-day measurement: `query_probe` on the eight
  misses the family has today (puc, tec, psaclay, kaist, kaznu, msu, ntutw, tsinghua) plus the five local-only hits
  (warsaw, uba, kuleuven, uio, ctu) as the guard — 13 queries.
- **Tests.** `test_local_language_queries.py`: synthetic homepages per language → phrase; the cap, the refusals, the
  fallback; flag off → the query text of today, byte for byte.
- **Bar.** Gates; demo byte-identical; the phrase table shows ≥ 1 miss whose phrase equals its gold title shape, else the
  rule is recorded "built, no offline evidence" and waits.

### RP-1 — the read list for the owner's computer (data worker, ≈ 1 h)

- **Do.** From the merged KB's 198 unknown rows keep the 57 access-class cells (22 universities) and the 7 "quote failed
  CI" cells, add the 25 `KB_REFRESH_2026-10-19.md` "blocked from this vantage point" rows and the 2 access programme
  pages (UCL, Alberta); for each cell name the target URL the earlier round reported (the round READMEs name them) with a
  `topic`. Write `backend/evaluation/research/expert/data/read_pages/self-hosted-2026-10-21.json` (≤ 300 rows, official
  domains only, no heldout `seed_id`), and a README with the per-university row count and the expected yield per cell
  (fact / not-applicable / still unknown).
- **Bar.** `scripts/read_pages.py --check` (or `resolve_list` + `parse_rows` in a test) accepts the list; every host is in
  `verify_evidence.official_domains` for its `seed_id`.

### WHY-1 — the unknown reason class on the row (product worker, ≈ 2.5 h)

- **Change.** `kb_build`: `unknown[].kind` ∈ {`not_published`, `access`, `unverified_quote`, `undated`, `other_year`,
  `not_researched`, `unspecified`}, derived from a reviewed table committed beside the drafts
  (`kb_drafts.2026-10-19/unknown_kinds.json`: `seed_id`, `question`, `kind`, 198 rows, seeded by the keyword script and
  read by a person once; a row without an entry is `unspecified`). The API's result row gains `kb_unknown:
  [{question, kind, checked_on}]` for a KB row; `ResultDetail.tsx` renders one line per kind under the tab that owns the
  question ("Not published by the university, expert check 2026-10-19" / "Official page not readable from our servers;
  ask the admissions office" / "Not yet verified"), en/ru/kk. No question is added; nothing blocks.
- **Tests.** `tests/test_knowledge_base.py` (the table is applied at build; an unlisted row is `unspecified`; the API
  field), `ResultDetail.kb.test.tsx` (three kinds, three locales), `test_frontend_contract.py`.
- **Bar.** Gates; v21 facts byte-identical apart from the new field (shared with REL-1's rebuild if both land in one
  cycle: one rebuild, one version).

### TW-2 — the kuleuven twin's CI read (research worker, ≈ 0.5 h)

- **Do.** From the main session's `read-pages-<run id>` artifact of 2026-10-20 (the one topup_round8 drafted from), read
  the two `seed_id: kuleuven` rows: `final_url` equals the request (a), the text names "Bachelor in de informatica" with
  Leuven and 180 studiepunten or Bachelor of Science (b), and a quote `quote_in` finds (c). Fill §4.2 of
  `TWIN_CHECKS_2026-10-20.md` and change Q2's recommendation from conditional to plain, or record which condition failed.
  Nothing is applied to any gold file.

### G-16a — evidence-stage sizing on the four development sets (research worker, ≈ 2 h, no code)

- **Do.** On the `lv1-*` and `aw2-*` off-arm captures: (1) unlabelled claims ÷ claims per set, by claim type and by the
  page they came from (confirmed programme page / related / unconfirmed; the knockout arm says what a wrong page yields);
  (3) `pages:costs` vs `pages_fetched_ok:costs` and the refusal reasons; whether the fee sits on the programme page on dev4
  (FE-2b); (4) `expressibility` of the known award labels under the dev4 draft3 bindings. Item 2 is answered (LV-1).
- **Output.** `docs/process/EVIDENCE_GENERALISATION_2026-10-21.md` with a dev5 column left empty for R2; a verdict per
  item: dev-wide or set-dependent (≥ 15 pp between any two development sets).

## 4. Dispatch table (main session, 0 worker hours)

Common inputs as NEXT_CYCLES_2026-10-20 §7 (`benchmark-capture.yml`, `runner=ubuntu-latest`, `mode=expert_paired`,
`seconds_per_case=120`, `max_pages=60`, `case_parallelism=5`, `max_search_queries` empty). Score cohort on
`ground_truth.reviewed11.json`, dev2/dev3/dev4 on `draft3` with `--allow-drafts`; dev5 with `--summary-only` only.

| run | set(s) | inputs that differ | `run_tag` | read |
|---|---|---|---|---|
| **AW-2 verdict** (in flight) | 4 sets normal + knockout | `extra_args=--award-signals-all-languages`, `search_provider=recorded` | `aw2-*`, `aw2-ko-*` | the pre-registered bar in REACH_ROWS §AW-2: no stable claim loss, no new wrong claim or page, knockout not up → on by default (coverage rule, as LV-1); the only expected gain dev4 rwth |
| **ES-2 rows** | the `aw2-*` off arms (first captures with `html_lang` / `classifier_signal`) | `python -m evaluation.research.stage_summary … --dataset …` | — | `funding_refused_by_lang`, `funding_refused_by_signal`, `funding_refused_signals_lt2` per set → LOOP_REPORT; S6 becomes measurable; a non-English refusal on a second set re-opens AW-1's trigger |
| **D-F5 dev5 no-search floor** | dev5 (13 cases, LOOP_PROTOCOL list) | `search_provider=none`, `columns=1`, `extra_args` empty | `ns-floor-dev5` | `scorecard --summary-only` on `dev5.draft1 --allow-drafts`: `programme_found_on_readable`, `wrong_programme_pages`, `cases_over_budget`; `stage_summary` aggregates. **Pre-registered** (ticket 10's offline ceiling): found ≤ 3/8 readable, wrong **0**, over budget 0; two cases `unavailable` (kbtu, satbayev). The first dev5 aggregate under today's defaults; the 13-Q2 (b) reading for the eight guards in the regime without a key |
| **KB refresh, first CI run** | — | `gh workflow run kb-refresh.yml --ref claude/greeting-16wj2z` (workflow_dispatch; the schedule fires only from `main`, which needs the owner's merge) | — | the `kb-refresh-<run id>` artifact's queue vs `KB_REFRESH_2026-10-19.md` (sandbox): classes `verified / quote_gone / http_403 / robots_*`; the 403 count from the runner is the number RP-1 and 01-Q4 answer |
| **NS-1b** (if built) | 4 sets normal + knockout, no search | `search_provider=none`, `columns=4`, `extra_args=--<ns1-flag>` | `ns1-<set>`, `ns1-ko-<set>` | §3 NS-1b bar |
| **NS-1b guard** | dev3, dev4 | `search_provider=recorded`, same flag | `rp-ns1-<set>` | no hit lost, no new wrong page, `recorded_search_misses` = off arm |
| **D-D interaction check** (optional, idle runners) | 4 sets | `extra_args=--no-<rule>` for the rules flipped on 2026-10-19 whose paired runs predate the later flips (`abstain-on-unreadable-entry`, `confirm-head-identity`, `reject-combination-head`, `reject-subpage-head`), knockout arms too | `rp-abl-<rule>-<set>` | each rule was measured against an older default set; an off arm on today's defaults that reads identical means the rule's gain was absorbed by a later rule (ledger note), a stable loss means still load-bearing; no default changes from this alone |

## 5. The cycles

| cycle | dispatches (0 worker h) | worker tickets (parallel, disjoint files) | gate / read |
|---|---|---|---|
| **16 (now)** | AW-2 verdict; ES-2 rows; D-F5 dev5 no-search floor; KB refresh first CI run | **CAT-1** (product), **NS-1a** (research), **E2E-KB** (tests), **TW-2 → RP-1** (one research worker) | AW-2 default decision → LOOP_REPORT, `hypotheses.json`; D-F5 against the pre-registration (aggregates only); CAT-1 and E2E-KB green on the committed KB; NS-1a's verdict decides whether NS-1b opens |
| **17** | NS-1b replays (10) if built; D-D residue as runners idle | **NS-1b** (pipeline, high) or, if no shared cause, **G-16a**; **REL-1**, **WHY-1** (one KB rebuild, v21), **LQ-2a** | NS-1b bar; v21 facts byte-identical apart from the two new fields; the LQ-2 phrase table; `RELEASE_CHECKLIST.md` gains the E2E-KB gate |
| **18** | re-score after any owner signature (Q1–Q3 → draft4); R1 / R2 / self-hosted reads the day an answer arrives (§6) | follow-ups the verdicts name (an NS-1b diagnosis, an AW-2 loss), **G-16a** if not done, a ledger refresh of `RELEASE_CHECKLIST.md` for kb mode (one worker, 2 h: which of the 96 gates kb mode changes, with today's command output) | the loop continues on the no-search bench and the product; the recorded bench runs guard arms only |

Expected after cycles 16–18 without the owner: recorded-replay hits unchanged at 26/39; no-search floor 9/39 → 11–13/39
if NS-1a names a shared cause, else unchanged with the cause table written; AW-2 and ES-2 settle S6; the first dev5
aggregate under today's defaults on record; the catalogue tells the applicant where the verified data is; the kb-mode
UI is guarded in CI; 7 entries state their programme route instead of asking; 198 empty cells say why. With the owner's
five answers: §6.

## 6. What each pending owner answer unlocks

| answer | unlocks (one line) |
|---|---|
| **U7**, deadline variant A (skip the eligibility deadline check when every stated date precedes the intake's cycle) or B (soften to a non-GAP note) | the Fudan-type row stops reading GAP for a window the applicant never had; `eligibility.evaluate` is domain code shared with live mode, so `seed_demo.py` is re-checked; ≈ 1.5 h after the answer |
| **KFUPM** (two official pages disagree on the waived tuition) | one held-back tuition fact enters v21 (SAR 0, standing policy) or stays unknown with the disagreement recorded; no other row moves |
| **Native-name overlay signature** (`catalogue_native_names.proposed.json` rows) | production `native_name` for the signed rows; the identity gate reads dev5 **7/13 → 9/13** (IG-2), dev sets unchanged; the 15-Q2 gate arm of the second look becomes credible; NN-1b's fold can then be measured with it |
| **Three twin signatures** (Q1 uct keep, Q2 kuleuven conditional on TW-2, Q3 tcd) | `dev2.draft4` / `dev3.draft4` applied after CI `verify_evidence`: knockout dev2 1 → 0 (tcd), dev3 kuleuven wrong → hit in readable repetitions, uct unchanged; recorded hits 26 → 27–28/39 by re-score, **0 code** |
| **Exa key** (Q6) | R1 (44 cases, `columns=1`, cap 264) → the `recorded-search/2` store with titles and the topic / scholarship / identity lists → re-baseline: warsaw `missed → hit`, 10 regime-C labels measurable, LQ-2a measurable on 13 queries, the 51-query miss probe; then R2 (dev5 baseline, cap 312, aggregates) once 13-Q1…Q5 are signed → 13-Q2 (b) for the eight flipped rules and the second set for S1–S7 via ES-1 rows |

Two answers not in the pending list carry more KB coverage than any of the five: **01-Q4** (the owner's computer as
self-hosted runner, same agent, same robots, no retries) is the only lever on the 57 access cells, the 25 kb-refresh
blocked rows and the access five of the development misses — RP-1 makes it a one-dispatch job; **merging to `main`**
is what lets the kb-refresh schedule fire at all.

## 7. What this plan does not build, and why

| item | why not now | re-opens when |
|---|---|---|
| AW-3 local-language award value readers (amount, coverage, deadline in the page's language) | gain 0 on every bench: the only labelled local-language award page (dev4) has its label on a costs page the walk never reaches; the other cited local pages are never fetched (reach) | AW-2 on by default **and** a second set's local-language award page fetched (ES-2 row) |
| PD-1 PDF evidence readers (pdf-evidence 04) | the 6 gold PDF evidence pages are never fetched on development (`evidence_reach_pdf` 0/1, 0/2, 0/1); the PDFs met (`pdf_met:other` 3 / 2–3) carry no label; a reader alone gains 0 (18-Q2 c) | a reach rule brings a labelled PDF into the walk, or the owner opens PD-3 |
| CA-1 confirm-abstention guard (generalisation 09) | the three remaining knockout guesses are three one-set shapes whose heads name subject and level (GOLD_KNOCKOUT §3); CA-1's sub-rule 1 does not fire on them, and sub-rule 2 (two independent signals) would refuse the five normal hits that only the `local_language` family returns (LOCO-1 §2) | a second development case of any of the three shapes |
| IB-1, AI-1, AW-1, SH-1 default-on, LL-1, SP-2 | one set, zero sets, or fired with no gain — all recorded | the triggers written in REACH_ROWS and LOOP_REPORT |
| a KB manual round | §2.2: the pool is 81 unpublished + 57 access + 44 generic notes; rounds 7–10 yielded ≈ 1 fact per university-hour | 01-Q4 (RP-1's list), or spring 2027 fees |
| the own index as a provider (free-search 05) | the ceiling (3 / 1 / 6 / 1) is a third of Serper's row; NS-1 closes the gap between today's path and that ceiling instead | never, on this evidence |
| Common Crawl discovery (free-search 06, second half) | a network path outside `Fetcher` needs an owner exception like SR-06 | the owner grants one |
| DoD targets, denominators, the 6 / 60 / 120 budget, the seven 2026-10-19 defaults, model extraction, any heldout look | as in NEXT_CYCLES_2026-10-20 §9 | — |
