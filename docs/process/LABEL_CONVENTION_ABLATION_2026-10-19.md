# Label-convention ablation on development — 2026-10-19 (generalisation ticket 05, loop id G-05)

H-A asks how much of the development numbers depends on label conventions and scorer changes that arrived after
heldout.reviewed1 was signed (2026-10-17, commit `72ff9b15`). **Everything below is development only**: the frozen
base3 captures of cohort / dev2 / dev3 / dev4 (runs 39172483236 / 39172484697 / 39172486984 / 39172488858, pipeline
`1093faaa`, paired off/on × 2 repetitions). No heldout file, capture, log, label or number was opened or computed;
this document names conventions, never heldout labels.

## Verdict

**H-A confirmed on development.** Both a convention change and a scorer change move development page recall or
precision by far more than 10 pp:

- label conventions (twins / department pages / canonical variants / `related`), today's scorer, oldest corpora
  *as signed*: page recall dev3 **−27.9 pp**, dev4 **−42.2 pp**; page precision dev3 −47.9, dev4 −52.4;
- the twin ablation (each label cut to its first URL, `related` dropped): page recall dev3 **−35.7 pp**, dev4
  **−20.0 pp**, dev2 −10.0; precision dev3 −53.3, dev4 −41.2, dev2 −19.5;
- the 2026-10-17 scorer on today's corpora: page precision dev2 **−19.4 pp**, dev4 **−17.6 pp**, recall dev2
  −10.0; claim precision dev2 **−59.6 pp** (seven correct TCD claims read `wrong_scope`).

## Method

Scripts and raw outputs live in the session scratchpad `g05/` (not in the repository; no product code changed):
`run_cells.py` (2×2 driver), `extract.py` / `render2x2.py` / `render_ablation.py` (tables), `ablate.py` (twin
ablation), `remap.py` (bindings ablation), `out/*.md|json` (every scorecard and stage summary).

- **Today's scorer**: `python -m evaluation.research.scorecard` and `stage_summary` at this branch's HEAD.
- **2026-10-17 scorer**: `backend/evaluation` and `backend/app` exported with `git archive 72ff9b15` into the
  scratchpad and run from there. One patch was needed and is the only change: its `schema.Strict` model was
  `extra="forbid"`, so it refuses today's captures (`programme_url_aliases`, `related_programme_urls`, …) and
  corpora (`related_programme_urls`). The export was set to `extra="ignore"` — the old scorer reads exactly the
  fields it knew and ignores what came later, which is what "the old scorer" means. It has no `--summary-only`,
  no hit/wrong/related/missed row and no readable denominator: its comparable rows are `programme_page_recall`,
  `programme_page_precision` (pages returned that are the gold ÷ pages returned), `claim_precision`,
  `wrong_scope_claim_rate`, claims matched, and `known core answered` on the `all` denominator.
- **Oldest corpora.** The ticket names reviewed10 / dev2.draft1 / dev3.draft1 / dev4.draft1. Those files were
  **edited in place after 2026-10-17** (`78e15c5d` equivalent pages into dev2/dev3 draft1; `90b45f59` department
  pages and `related` into reviewed10, dev3.draft1 and dev4.draft1; `f5ee82c1` and `aec3c69b` into dev4.draft1).
  So the 2×2 uses the files **as signed**: `git show 72ff9b15:` for reviewed10 / dev2.draft1 / dev3.draft1, and
  dev4.draft1 at its first commit `50308b0c` (2026-10-18 08:44 — dev4 did not exist on 10-17 and was born after
  the twin scorer, with twins already listed). Column B′ adds today's scorer on the draft1/reviewed10 files *as they
  stand now*, for completeness; it mostly measures corpus round 02 and the core conventions.
- Cells print the four columns `off#1 · off#2 · on#1 · on#2` and the pooled ratio; pp is pooled-ratio minus the
  reference (cell A).

## 1. The 2×2 re-score, per set

### cohort

| row | A: today scorer × today corpus (ref) | B: today scorer × oldest corpus as signed | C: 10-17 scorer × today corpus | D: 10-17 scorer × oldest corpus as signed | B′: today scorer × oldest file as it stands now |
|---|---|---|---|---|---|
| programme_page_recall | 5/10 · 5/10 · 5/10 · 5/10 = **50.0%** | 5/10 · 5/10 · 5/10 · 5/10 = **50.0%** (+0.0 pp) | 5/10 · 5/10 · 5/10 · 5/10 = **50.0%** (+0.0 pp) | 5/10 · 5/10 · 5/10 · 5/10 = **50.0%** (+0.0 pp) | 5/10 · 5/10 · 5/10 · 5/10 = **50.0%** (+0.0 pp) |
| programme_page_precision | 5/9 · 5/8 · 5/10 · 5/9 = **55.6%** | 5/10 · 5/9 · 5/11 · 5/10 = **50.0%** (-5.6 pp) | 5/10 · 5/9 · 5/11 · 5/10 = **50.0%** (-5.6 pp) | 5/10 · 5/9 · 5/11 · 5/10 = **50.0%** (-5.6 pp) | 5/9 · 5/8 · 5/10 · 5/9 = **55.6%** (+0.0 pp) |
| claim_precision | 45/45 · 44/44 · 44/44 · 45/45 = **100.0%** | 39/45 · 38/44 · 38/44 · 39/45 = **86.5%** (-13.5 pp) | 39/39 · 38/38 · 38/38 · 39/39 = **100.0%** (+0.0 pp) | 39/39 · 38/38 · 38/38 · 39/39 = **100.0%** (+0.0 pp) | 39/45 · 38/44 · 38/44 · 39/45 = **86.5%** (-13.5 pp) |
| wrong_scope_claim_rate | 0/45 · 0/44 · 0/44 · 0/45 = **0.0%** | 6/45 · 6/44 · 6/44 · 6/45 = **13.5%** (+13.5 pp) | 0/39 · 0/38 · 0/38 · 0/39 = **0.0%** (+0.0 pp) | 0/39 · 0/38 · 0/38 · 0/39 = **0.0%** (+0.0 pp) | 6/45 · 6/44 · 6/44 · 6/45 = **13.5%** (+13.5 pp) |
| claims matched (labels hit) | 29/83 · 28/83 · 28/83 · 29/83 = **34.3%** | 28/84 · 27/84 · 27/84 · 28/84 = **32.7%** (-1.6 pp) | 28/83 · 27/83 · 27/83 · 28/83 = **33.1%** (-1.2 pp) | 28/84 · 27/84 · 27/84 · 28/84 = **32.7%** (-1.6 pp) | 28/84 · 27/84 · 27/84 · 28/84 = **32.7%** (-1.6 pp) |
| known core answered (all) | 14/27 · 14/27 · 13/27 · 14/27 = **50.9%** | 13/28 · 13/28 · 12/28 · 13/28 = **45.5%** (-5.4 pp) | 13/27 · 13/27 · 12/27 · 13/27 = **47.2%** (-3.7 pp) | 13/28 · 13/28 · 12/28 · 13/28 = **45.5%** (-5.4 pp) | 13/28 · 13/28 · 12/28 · 13/28 = **45.5%** (-5.4 pp) |
| page hit/wrong/related/missed | 5/1/1/3 · 5/0/1/4 · 5/2/1/2 · 5/1/1/3 | 5/2/0/3 · 5/1/0/4 · 5/3/0/2 · 5/2/0/3 | — · — · — · — | — · — · — · — | 5/1/1/3 · 5/0/1/4 · 5/2/1/2 · 5/1/1/3 |
| programme_found_on_readable | 5/8 · 5/8 · 5/8 · 5/8 = **62.5%** | 5/8 · 5/8 · 5/8 · 5/8 = **62.5%** (+0.0 pp) | — · — · — · — | — · — · — · — | 5/8 · 5/8 · 5/8 · 5/8 = **62.5%** (+0.0 pp) |
| wrong_programme_pages | 1 · 0 · 2 · 1 | 2 · 1 · 3 · 2 | — · — · — · — | — · — · — · — | 1 · 0 · 2 · 1 |

### dev2

| row | A: today scorer × today corpus (ref) | B: today scorer × oldest corpus as signed | C: 10-17 scorer × today corpus | D: 10-17 scorer × oldest corpus as signed | B′: today scorer × oldest file as it stands now |
|---|---|---|---|---|---|
| programme_page_recall | 6/10 · 7/10 · 7/10 · 7/10 = **67.5%** | 4/6 · 5/6 · 5/6 · 5/6 = **79.2%** (+11.7 pp) | 5/10 · 6/10 · 6/10 · 6/10 = **57.5%** (-10.0 pp) | 3/6 · 4/6 · 4/6 · 4/6 = **62.5%** (-5.0 pp) | 4/6 · 5/6 · 5/6 · 5/6 = **79.2%** (+11.7 pp) |
| programme_page_precision | 6/8 · 7/7 · 7/8 · 7/8 = **87.1%** | 4/5 · 5/5 · 5/5 · 5/5 = **95.0%** (+7.9 pp) | 5/8 · 6/9 · 6/8 · 6/9 = **67.6%** (-19.4 pp) | 3/5 · 4/5 · 4/5 · 4/5 = **75.0%** (-12.1 pp) | 4/5 · 5/5 · 5/5 · 5/5 = **95.0%** (+7.9 pp) |
| claim_precision | 11/11 · 12/12 · 12/12 · 12/12 = **100.0%** | 10/11 · 11/12 · 11/12 · 11/12 = **91.5%** (-8.5 pp) | 4/11 · 5/12 · 5/12 · 5/12 = **40.4%** (-59.6 pp) | 3/11 · 4/12 · 4/12 · 4/12 = **31.9%** (-68.1 pp) | 10/11 · 11/12 · 11/12 · 11/12 = **91.5%** (-8.5 pp) |
| wrong_scope_claim_rate | 0/11 · 0/12 · 0/12 · 0/12 = **0.0%** | 0/11 · 0/12 · 0/12 · 0/12 = **0.0%** (+0.0 pp) | 7/11 · 7/12 · 7/12 · 7/12 = **59.6%** (+59.6 pp) | 7/11 · 7/12 · 7/12 · 7/12 = **59.6%** (+59.6 pp) | 0/11 · 0/12 · 0/12 · 0/12 = **0.0%** (+0.0 pp) |
| claims matched (labels hit) | 11/28 · 12/28 · 12/28 · 12/28 = **42.0%** | 10/27 · 11/27 · 11/27 · 11/27 = **39.8%** (-2.1 pp) | 4/28 · 5/28 · 5/28 · 5/28 = **17.0%** (-25.0 pp) | 3/27 · 4/27 · 4/27 · 4/27 = **13.9%** (-28.1 pp) | 10/27 · 11/27 · 11/27 · 11/27 = **39.8%** (-2.1 pp) |
| known core answered (all) | 6/21 · 7/21 · 7/21 · 7/21 = **32.1%** | 5/21 · 6/21 · 6/21 · 6/21 = **27.4%** (-4.8 pp) | 2/21 · 3/21 · 3/21 · 3/21 = **13.1%** (-19.0 pp) | 1/21 · 2/21 · 2/21 · 2/21 = **8.3%** (-23.8 pp) | 5/21 · 6/21 · 6/21 · 6/21 = **27.4%** (-4.8 pp) |
| page hit/wrong/related/missed | 6/2/0/2 · 7/0/1/2 · 7/1/0/2 · 7/1/0/2 | 4/1/0/1 · 5/0/0/1 · 5/0/0/1 · 5/0/0/1 | — · — · — · — | — · — · — · — | 4/1/0/1 · 5/0/0/1 · 5/0/0/1 · 5/0/0/1 |
| programme_found_on_readable | 5/9 · 6/9 · 6/9 · 6/9 = **63.9%** | 4/6 · 5/6 · 5/6 · 5/6 = **79.2%** (+15.3 pp) | — · — · — · — | — · — · — · — | 4/6 · 5/6 · 5/6 · 5/6 = **79.2%** (+15.3 pp) |
| wrong_programme_pages | 2 · 0 · 1 · 1 | 1 · 0 · 0 · 0 | — · — · — · — | — · — · — · — | 1 · 0 · 0 · 0 |

### dev3

| row | A: today scorer × today corpus (ref) | B: today scorer × oldest corpus as signed | C: 10-17 scorer × today corpus | D: 10-17 scorer × oldest corpus as signed | B′: today scorer × oldest file as it stands now |
|---|---|---|---|---|---|
| programme_page_recall | 9/14 · 9/14 · 9/14 · 9/14 = **64.3%** | 4/11 · 4/11 · 4/11 · 4/11 = **36.4%** (-27.9 pp) | 9/14 · 9/14 · 9/14 · 9/14 = **64.3%** (+0.0 pp) | 2/11 · 2/11 · 2/11 · 2/11 = **18.2%** (-46.1 pp) | 8/11 · 8/11 · 8/11 · 8/11 = **72.7%** (+8.4 pp) |
| programme_page_precision | 9/10 · 9/9 · 9/10 · 9/10 = **92.3%** | 4/10 · 4/8 · 4/10 · 4/8 = **44.4%** (-47.9 pp) | 9/11 · 9/9 · 9/11 · 9/10 = **87.8%** (-4.5 pp) | 2/10 · 2/8 · 2/10 · 2/8 = **22.2%** (-70.1 pp) | 8/9 · 8/8 · 8/9 · 8/8 = **94.1%** (+1.8 pp) |
| claim_precision | 11/11 · 13/13 · 11/11 · 13/13 = **100.0%** | 11/11 · 13/13 · 11/11 · 13/13 = **100.0%** (+0.0 pp) | 11/11 · 11/13 · 11/11 · 11/13 = **91.7%** (-8.3 pp) | 11/11 · 11/13 · 11/11 · 11/13 = **91.7%** (-8.3 pp) | 11/11 · 13/13 · 11/11 · 13/13 = **100.0%** (+0.0 pp) |
| wrong_scope_claim_rate | 0/11 · 0/13 · 0/11 · 0/13 = **0.0%** | 0/11 · 0/13 · 0/11 · 0/13 = **0.0%** (+0.0 pp) | 0/11 · 2/13 · 0/11 · 2/13 = **8.3%** (+8.3 pp) | 0/11 · 2/13 · 0/11 · 2/13 = **8.3%** (+8.3 pp) | 0/11 · 0/13 · 0/11 · 0/13 = **0.0%** (+0.0 pp) |
| claims matched (labels hit) | 11/26 · 13/26 · 11/26 · 13/26 = **46.2%** | 11/34 · 13/34 · 11/34 · 13/34 = **35.3%** (-10.9 pp) | 11/26 · 11/26 · 11/26 · 11/26 = **42.3%** (-3.8 pp) | 11/34 · 11/34 · 11/34 · 11/34 = **32.4%** (-13.8 pp) | 11/34 · 13/34 · 11/34 · 13/34 = **35.3%** (-10.9 pp) |
| known core answered (all) | 8/22 · 9/22 · 8/22 · 9/22 = **38.6%** | 8/28 · 9/28 · 8/28 · 9/28 = **30.4%** (-8.3 pp) | 8/22 · 8/22 · 8/22 · 8/22 = **36.4%** (-2.3 pp) | 8/28 · 8/28 · 8/28 · 8/28 = **28.6%** (-10.1 pp) | 8/28 · 9/28 · 8/28 · 9/28 = **30.4%** (-8.3 pp) |
| page hit/wrong/related/missed | 9/1/1/3 · 9/0/0/5 · 9/0/1/4 · 9/1/0/4 | 4/6/0/1 · 4/4/0/3 · 4/5/0/2 · 4/4/0/3 | — · — · — · — | — · — · — · — | 8/1/1/1 · 8/0/0/3 · 8/0/1/2 · 8/0/0/3 |
| programme_found_on_readable | 9/13 · 9/12 · 9/12 · 9/12 = **73.5%** | 4/10 · 4/9 · 4/9 · 4/9 = **43.2%** (-30.2 pp) | — · — · — · — | — · — · — · — | 8/10 · 8/9 · 8/9 · 8/9 = **86.5%** (+13.0 pp) |
| wrong_programme_pages | 1 · 0 · 0 · 1 | 6 · 4 · 5 · 4 | — · — · — · — | — · — · — · — | 1 · 0 · 0 · 0 |

### dev4

| row | A: today scorer × today corpus (ref) | B: today scorer × oldest corpus as signed | C: 10-17 scorer × today corpus | D: 10-17 scorer × oldest corpus as signed | B′: today scorer × oldest file as it stands now |
|---|---|---|---|---|---|
| programme_page_recall | 3/5 · 3/5 · 4/5 · 4/5 = **70.0%** | 2/9 · 2/9 · 3/9 · 3/9 = **27.8%** (-42.2 pp) | 3/5 · 3/5 · 4/5 · 4/5 = **70.0%** (+0.0 pp) | 2/9 · 2/9 · 3/9 · 3/9 = **27.8%** (-42.2 pp) | 3/5 · 3/5 · 4/5 · 4/5 = **70.0%** (+0.0 pp) |
| programme_page_precision | 3/3 · 3/3 · 4/4 · 4/4 = **100.0%** | 2/5 · 2/4 · 3/6 · 3/6 = **47.6%** (-52.4 pp) | 3/4 · 3/3 · 4/5 · 4/5 = **82.4%** (-17.6 pp) | 2/5 · 2/4 · 3/6 · 3/6 = **47.6%** (-52.4 pp) | 3/3 · 3/3 · 4/4 · 4/4 = **100.0%** (+0.0 pp) |
| claim_precision | 8/8 · 8/8 · 9/9 · 9/9 = **100.0%** | 3/3 · 3/3 · 3/3 · 3/3 = **100.0%** (+0.0 pp) | 7/8 · 7/8 · 8/9 · 8/9 = **88.2%** (-11.8 pp) | 2/3 · 2/3 · 2/3 · 2/3 = **66.7%** (-33.3 pp) | 4/4 · 4/4 · 5/5 · 5/5 = **100.0%** (+0.0 pp) |
| wrong_scope_claim_rate | 0/8 · 0/8 · 0/9 · 0/9 = **0.0%** | 0/3 · 0/3 · 0/3 · 0/3 = **0.0%** (+0.0 pp) | 1/8 · 1/8 · 1/9 · 1/9 = **11.8%** (+11.8 pp) | 1/3 · 1/3 · 1/3 · 1/3 = **33.3%** (+33.3 pp) | 0/4 · 0/4 · 0/5 · 0/5 = **0.0%** (+0.0 pp) |
| claims matched (labels hit) | 7/20 · 7/20 · 8/20 · 8/20 = **37.5%** | 3/9 · 3/9 · 3/9 · 3/9 = **33.3%** (-4.2 pp) | 6/20 · 6/20 · 7/20 · 7/20 = **32.5%** (-5.0 pp) | 2/9 · 2/9 · 2/9 · 2/9 = **22.2%** (-15.3 pp) | 4/9 · 4/9 · 5/9 · 5/9 = **50.0%** (+12.5 pp) |
| known core answered (all) | 2/8 · 2/8 · 2/8 · 2/8 = **25.0%** | 0/0 · 0/0 · 0/0 · 0/0 | 2/8 · 2/8 · 2/8 · 2/8 = **25.0%** (+0.0 pp) | 0/0 · 0/0 · 0/0 · 0/0 | 0/0 · 0/0 · 0/0 · 0/0 |
| page hit/wrong/related/missed | 3/0/2/4 · 3/0/1/5 · 4/0/2/3 · 4/0/2/3 | 2/3/0/4 · 2/2/0/5 · 3/3/0/3 · 3/3/0/3 | — · — · — · — | — · — · — · — | 3/0/1/4 · 3/0/0/5 · 4/0/1/3 · 4/0/1/3 |
| programme_found_on_readable | 3/5 · 3/4 · 4/5 · 4/5 = **73.7%** | 2/9 · 2/8 · 3/9 · 3/9 = **28.6%** (-45.1 pp) | — · — · — · — | — · — · — · — | 3/5 · 3/4 · 4/5 · 4/5 = **73.7%** (+0.0 pp) |
| wrong_programme_pages | 0 · 0 · 0 · 0 | 3 · 2 · 3 · 3 | — · — · — · — | — · — · — · — | 0 · 0 · 0 · 0 |

What the 2×2 isolates (named by the wrong-claim lists of each cell):

- **C vs A (scorer only).** dev2 claim precision −59.6 pp: seven correct TCD claims (IELTS ×2, Duolingo, TOEFL,
  tuition, two award fields) read `wrong_scope` under the old university-name match; today's acronym / brand-name
  match (`aec3c69b`, `ef021c58`) scores them hits. The same rule explains dev4 −11.8 (KIT `programme.exists`) and
  dev3 −8.3 (UNSW IELTS ×2). Page precision falls dev2 −19.4, dev4 −17.6, cohort −5.6, dev3 −4.5: the old scorer
  counts a returned `related` page as not-the-gold, and does not read the capture's declared hreflang twins (see
  the arm in §2b). dev2 page recall −10.0 is the hreflang-twin rule alone.
- **B vs A (corpus only).** dev3 −27.9 / dev4 −42.2 pp page recall and −47.9 / −52.4 precision come from the
  department / major / equivalent pages and the `related` relabelling added on 2026-10-18 (and, for dev4, four
  cases relabelled from `known` to `unknown + related`). dev2 page recall *rises* (+11.7) because the oldest dev2
  corpus had only 6 known pages — the four added by ticket 10 are cases the pipeline finds less often. Cohort claim
  precision −13.5 is the NTU SAT label's population (round 02 Q2): the pipeline's `international` SAT claim reads
  `wrong_scope` against the population-less label ×12. dev2 −8.5 is the Uppsala international-round deadline (Q5).
- **D** compounds both; dev4 claim precision −33.3 and dev3 page recall −46.1 are the largest single cells.

## 2. Twin / variant ablation (today's scorer)

Every case's `programme_urls` cut to its **first** URL (the ticket's arm; a **last**-URL arm shows how much depends
on which form the label lists), `related_programme_urls` dropped. Captures untouched — the pipeline's own declared
hreflang twins (`programme_url_aliases`) still count, as they would on any set. Stage rows are per column.

### 2a. cohort

| row | reference (today's labels) | labels cut to first URL, no related | labels cut to last URL, no related |
|---|---|---|---|
| gold_returned_by_search | 8 · 8 · 8 · 8 | 8 · 8 · 8 · 8 | 5 · 5 · 5 · 5 |
| gold_never_seen | 0 · 0 · 0 · 0 | 0 · 0 · 0 · 0 | 4 · 4 · 4 · 4 |
| gold_confirmed | 5 · 5 · 5 · 5 | 5 · 5 · 5 · 5 | 2 · 2 · 2 · 2 |
| cases_with_gold | 10 · 10 · 10 · 10 | 10 · 10 · 10 · 10 | 10 · 10 · 10 · 10 |
| confirmed_pages_wrong | 4 · 3 · 5 · 4 | 5 · 4 · 6 · 5 | 8 · 7 · 9 · 8 |
| confirmed_pages_related | 2 · 2 · 2 · 2 | 1 · 1 · 1 · 1 | 1 · 1 · 1 · 1 |
| programme_page_recall | 5/10 · 5/10 · 5/10 · 5/10 = 50.0% | 5/10 · 5/10 · 5/10 · 5/10 = 50.0% | 2/10 · 2/10 · 2/10 · 2/10 = 20.0% |
| programme_page_precision | 5/9 · 5/8 · 5/10 · 5/9 = 55.6% | 5/10 · 5/9 · 5/11 · 5/10 = 50.0% | 2/10 · 2/9 · 2/11 · 2/10 = 20.0% |
| programme_found_on_readable | 5/8 · 5/8 · 5/8 · 5/8 = 62.5% | 5/8 · 5/8 · 5/8 · 5/8 = 62.5% | 2/8 · 2/8 · 2/8 · 2/8 = 25.0% |
| wrong_programme_pages | 1 · 0 · 2 · 1 | 2 · 1 · 3 · 2 | 5 · 4 · 6 · 5 |
| page hit/wrong/related/missed | 5/1/1/3 · 5/0/1/4 · 5/2/1/2 · 5/1/1/3 | 5/2/0/3 · 5/1/0/4 · 5/3/0/2 · 5/2/0/3 | 2/5/0/3 · 2/4/0/4 · 2/6/0/2 · 2/5/0/3 |
| claim_precision | 45/45 · 44/44 · 44/44 · 45/45 = 100.0% | 45/45 · 44/44 · 44/44 · 45/45 = 100.0% | 45/45 · 44/44 · 44/44 · 45/45 = 100.0% |
| claims matched (labels hit) | 29/83 · 28/83 · 28/83 · 29/83 = 34.3% | 29/83 · 28/83 · 28/83 · 29/83 = 34.3% | 29/83 · 28/83 · 28/83 · 29/83 = 34.3% |
| known core answered (all) | 14/27 · 14/27 · 13/27 · 14/27 = 50.9% | 14/27 · 14/27 · 13/27 · 14/27 = 50.9% | 14/27 · 14/27 · 13/27 · 14/27 = 50.9% |

### 2a. dev2

| row | reference (today's labels) | labels cut to first URL, no related | labels cut to last URL, no related |
|---|---|---|---|
| gold_returned_by_search | 7 · 7 · 7 · 7 | 7 · 7 · 7 · 7 | 7 · 7 · 7 · 7 |
| gold_never_seen | 1 · 1 · 1 · 1 | 2 · 2 · 2 · 2 | 1 · 1 · 1 · 1 |
| gold_confirmed | 6 · 7 · 7 · 7 | 5 · 6 · 6 · 6 | 6 · 7 · 7 · 7 |
| cases_with_gold | 10 · 10 · 10 · 10 | 10 · 10 · 10 · 10 | 10 · 10 · 10 · 10 |
| confirmed_pages_wrong | 2 · 0 · 1 · 1 | 3 · 3 · 2 · 3 | 2 · 2 · 1 · 2 |
| confirmed_pages_related | 1 · 3 · 1 · 2 | 1 · 1 · 1 · 1 | 1 · 1 · 1 · 1 |
| programme_page_recall | 6/10 · 7/10 · 7/10 · 7/10 = 67.5% | 5/10 · 6/10 · 6/10 · 6/10 = 57.5% | 6/10 · 7/10 · 7/10 · 7/10 = 67.5% |
| programme_page_precision | 6/8 · 7/7 · 7/8 · 7/8 = 87.1% | 5/8 · 6/9 · 6/8 · 6/9 = 67.6% | 6/8 · 7/9 · 7/8 · 7/9 = 79.4% |
| programme_found_on_readable | 5/9 · 6/9 · 6/9 · 6/9 = 63.9% | 5/9 · 6/9 · 6/9 · 6/9 = 63.9% | 5/9 · 6/9 · 6/9 · 6/9 = 63.9% |
| wrong_programme_pages | 2 · 0 · 1 · 1 | 3 · 2 · 2 · 2 | 2 · 1 · 1 · 1 |
| page hit/wrong/related/missed | 6/2/0/2 · 7/0/1/2 · 7/1/0/2 · 7/1/0/2 | 5/3/0/2 · 6/2/0/2 · 6/2/0/2 · 6/2/0/2 | 6/2/0/2 · 7/1/0/2 · 7/1/0/2 · 7/1/0/2 |
| claim_precision | 11/11 · 12/12 · 12/12 · 12/12 = 100.0% | 11/11 · 12/12 · 12/12 · 12/12 = 100.0% | 11/11 · 12/12 · 12/12 · 12/12 = 100.0% |
| claims matched (labels hit) | 11/28 · 12/28 · 12/28 · 12/28 = 42.0% | 11/28 · 12/28 · 12/28 · 12/28 = 42.0% | 11/28 · 12/28 · 12/28 · 12/28 = 42.0% |
| known core answered (all) | 6/21 · 7/21 · 7/21 · 7/21 = 32.1% | 6/21 · 7/21 · 7/21 · 7/21 = 32.1% | 6/21 · 7/21 · 7/21 · 7/21 = 32.1% |

### 2a. dev3

| row | reference (today's labels) | labels cut to first URL, no related | labels cut to last URL, no related |
|---|---|---|---|
| gold_returned_by_search | 11 · 10 · 11 · 11 | 7 · 7 · 7 · 7 | 10 · 9 · 10 · 10 |
| gold_never_seen | 2 · 3 · 2 · 2 | 7 · 7 · 7 · 7 | 3 · 4 · 3 · 3 |
| gold_confirmed | 9 · 9 · 9 · 9 | 4 · 4 · 4 · 4 | 8 · 8 · 8 · 8 |
| cases_with_gold | 14 · 14 · 14 · 14 | 14 · 14 · 14 · 14 | 14 · 14 · 14 · 14 |
| confirmed_pages_wrong | 1 · 0 · 1 · 1 | 7 · 5 · 7 · 6 | 3 · 1 · 3 · 2 |
| confirmed_pages_related | 4 · 3 · 4 · 4 | 3 · 3 · 3 · 4 | 3 · 3 · 3 · 4 |
| programme_page_recall | 9/14 · 9/14 · 9/14 · 9/14 = 64.3% | 4/14 · 4/14 · 4/14 · 4/14 = 28.6% | 8/14 · 8/14 · 8/14 · 8/14 = 57.1% |
| programme_page_precision | 9/10 · 9/9 · 9/10 · 9/10 = 92.3% | 4/11 · 4/9 · 4/11 · 4/10 = 39.0% | 8/11 · 8/9 · 8/11 · 8/10 = 78.0% |
| programme_found_on_readable | 9/13 · 9/12 · 9/12 · 9/12 = 73.5% | 4/13 · 4/12 · 4/12 · 4/12 = 32.7% | 8/13 · 8/12 · 8/12 · 8/12 = 65.3% |
| wrong_programme_pages | 1 · 0 · 0 · 1 | 7 · 5 · 6 · 6 | 3 · 1 · 2 · 2 |
| page hit/wrong/related/missed | 9/1/1/3 · 9/0/0/5 · 9/0/1/4 · 9/1/0/4 | 4/7/0/3 · 4/5/0/5 · 4/6/0/4 · 4/6/0/4 | 8/3/0/3 · 8/1/0/5 · 8/2/0/4 · 8/2/0/4 |
| claim_precision | 11/11 · 13/13 · 11/11 · 13/13 = 100.0% | 11/11 · 13/13 · 11/11 · 13/13 = 100.0% | 11/11 · 13/13 · 11/11 · 13/13 = 100.0% |
| claims matched (labels hit) | 11/26 · 13/26 · 11/26 · 13/26 = 46.2% | 11/26 · 13/26 · 11/26 · 13/26 = 46.2% | 11/26 · 13/26 · 11/26 · 13/26 = 46.2% |
| known core answered (all) | 8/22 · 9/22 · 8/22 · 9/22 = 38.6% | 8/22 · 9/22 · 8/22 · 9/22 = 38.6% | 8/22 · 9/22 · 8/22 · 9/22 = 38.6% |

### 2a. dev4

| row | reference (today's labels) | labels cut to first URL, no related | labels cut to last URL, no related |
|---|---|---|---|
| gold_returned_by_search | 5 · 5 · 5 · 5 | 5 · 5 · 5 · 5 | 4 · 4 · 4 · 4 |
| gold_never_seen | 0 · 0 · 0 · 0 | 0 · 0 · 0 · 0 | 1 · 1 · 1 · 1 |
| gold_confirmed | 3 · 3 · 4 · 4 | 2 · 2 · 3 · 3 | 3 · 3 · 3 · 3 |
| cases_with_gold | 5 · 5 · 5 · 5 | 5 · 5 · 5 · 5 | 5 · 5 · 5 · 5 |
| confirmed_pages_wrong | 0 · 0 · 0 · 0 | 3 · 2 · 3 · 3 | 2 · 1 · 3 · 3 |
| confirmed_pages_related | 2 · 1 · 3 · 3 | 0 · 0 · 1 · 1 | 0 · 0 · 1 · 1 |
| programme_page_recall | 3/5 · 3/5 · 4/5 · 4/5 = 70.0% | 2/5 · 2/5 · 3/5 · 3/5 = 50.0% | 3/5 · 3/5 · 3/5 · 3/5 = 60.0% |
| programme_page_precision | 3/3 · 3/3 · 4/4 · 4/4 = 100.0% | 2/4 · 2/3 · 3/5 · 3/5 = 58.8% | 3/4 · 3/3 · 3/5 · 3/5 = 70.6% |
| programme_found_on_readable | 3/5 · 3/4 · 4/5 · 4/5 = 73.7% | 2/5 · 2/4 · 3/5 · 3/5 = 52.6% | 3/5 · 3/4 · 3/5 · 3/5 = 63.2% |
| wrong_programme_pages | 0 · 0 · 0 · 0 | 2 · 1 · 2 · 2 | 1 · 0 · 2 · 2 |
| page hit/wrong/related/missed | 3/0/2/4 · 3/0/1/5 · 4/0/2/3 · 4/0/2/3 | 2/2/0/1 · 2/1/0/2 · 3/2/0/0 · 3/2/0/0 | 3/1/0/1 · 3/0/0/2 · 3/2/0/0 · 3/2/0/0 |
| claim_precision | 8/8 · 8/8 · 9/9 · 9/9 = 100.0% | 8/8 · 8/8 · 9/9 · 9/9 = 100.0% | 8/8 · 8/8 · 9/9 · 9/9 = 100.0% |
| claims matched (labels hit) | 7/20 · 7/20 · 8/20 · 8/20 = 37.5% | 7/20 · 7/20 · 8/20 · 8/20 = 37.5% | 7/20 · 7/20 · 8/20 · 8/20 = 37.5% |
| known core answered (all) | 2/8 · 2/8 · 2/8 · 2/8 = 25.0% | 2/8 · 2/8 · 2/8 · 2/8 = 25.0% | 2/8 · 2/8 · 2/8 · 2/8 = 25.0% |

**Read-out (pooled pp vs the reference).**

| set | arm | gold_returned_by_search (per column) | page recall | page precision | programme_found_on_readable | wrong programme pages (per column) |
|---|---|---|---|---|---|---|
| cohort | first URL | 8 → 8 | 0.0 | −5.6 | 0.0 | 1·0·2·1 → 2·1·3·2 |
| cohort | last URL | 8 → 5 | −30.0 | −35.6 | −37.5 | → 5·4·6·5 |
| dev2 | first URL | 7 → 7 (never seen 1 → 2) | −10.0 | −19.5 | 0.0 | 2·0·1·1 → 3·2·2·2 |
| dev2 | last URL | 7 → 7 | 0.0 | −7.7 | 0.0 | → 2·1·1·1 |
| dev3 | first URL | 10–11 → 7 (never seen 2–3 → 7) | −35.7 | −53.3 | −40.8 | 1·0·0·1 → 7·5·6·6 |
| dev3 | last URL | 10–11 → 9–10 | −7.2 | −14.3 | −8.2 | → 3·1·2·2 |
| dev4 | first URL | **5/5 → 5/5** | −20.0 | −41.2 | −21.1 | 0·0·0·0 → 2·1·2·2 |
| dev4 | last URL | 5/5 → 4/5 | −10.0 | −29.4 | −10.5 | → 1·0·2·2 |

dev4's "5/5 gold returned" survives the first-URL cut (the first-listed form is the one search returns), but the
page the pipeline *confirms* is often the other form: 1 hit per column becomes a wrong page, and the related
pages (2–3 per column) become wrong pages too. **The number the nine would read if their labels list one URL form
is, on dev4, 2–3/5 hits with 1–2 wrong pages per column, not 3–4/5 with 0** — and which form is listed moves
cohort by 30 pp and dev3 by 28 pp on its own.

### 2b. Pipeline-declared twins (supplementary arm)

The same captures with `programme_url_aliases` and `programme_page_languages` emptied (today's corpora, today's
scorer): only dev2 moves — page recall −10.0, precision −12.9, `programme_found_on_readable` −11.1 (one case per
column, the hreflang twin rule of WF-17). cohort, dev3 and dev4 are unchanged.

## 3. Bindings ablation (today's scorer, today's corpora)

Each capture's raw claims re-mapped offline (`map_claims.map_predictions`, the capture's own observed university
name) with (control) the base3 binding set — reviewed + `draft2` + `dev2-draft1` + `dev3-draft1` + `dev4-draft1` —
and (arm) the reviewed file only. The control reproduces every observation's prediction keys exactly (176/176).

| set | claims that become `unmapped.*` (all 4 columns) | which | claims matched | known core answered (all) |
|---|---|---|---|---|
| cohort | +8 (2 per column) | `scholarship_exists`, `scholarship_international_eligible` | 34.3% → 31.9% (−2.4 pp) | 50.9% → 43.5% (**−7.4 pp**) |
| dev2 | +8 (2 per column) | same two | 42.0% → 34.8% (−7.2 pp) | 32.1% → 22.6% (**−9.5 pp**) |
| dev3 | +12 (3 per column) | the two + `scholarship_program_restriction` | 46.2% → 38.5% (−7.7 pp) | 38.6% → 29.5% (**−9.1 pp**) |
| dev4 | 0 | — (`dev4-draft1` binds nothing base3 read) | unchanged | unchanged |

Every moved claim is an award claim: one award per set (cohort, dev2, dev3) is answerable only because a draft
binding file names it. Claim precision stays 100% (the claims leave numerator and denominator together); page rows
do not move. A set whose awards have no binding row reads its award questions as unanswered even when the claim
is right.

## 4. Development label changes since 2026-10-17 motivated by a pipeline reading

Source: the as-signed → today diff of each corpus (structural, per case), the commits that made each change, the
finish-algorithm tickets 02 / 10 / 15, `LABEL_PROPOSALS_2026-10-18.md` and the loop report. **P** = the label was
changed to agree with a page or value the pipeline returned, confirmed or read; **S** = changed because no reader
could ever match it (score-driven, no specific reading); **E** = an expert/independent addition.

| set | change | commit / ticket | class |
|---|---|---|---|
| cohort | delft TOEFL evidence URL twin (Q8) | `79017395` / 02 | P |
| cohort | ntu SAT key alias + population `international` (Q1/Q2) | `79017395`, `d7759a29` / 02 | P |
| cohort | ntu award URL alias in the bindings (Q1) | `d7759a29` / 02 | P |
| cohort | hku department/major page added as gold | `90b45f59` | P |
| cohort | ubc BA page labelled `related` | `90b45f59` | P |
| cohort | ntu gpa → `unknown` (prose, Q7) | `79017395` / 02 | S |
| dev2 | uppsala deadline → international round 2027-01-15, national kept as `deadline.eu_national` (Q5) | `79017395` / 02 | P |
| dev2 | kaznu, uct (+2 related), khalifa (+1 related) programme pages known (picked 4/4 by the pipeline) | `b6c37b44` / 10, 15 | P |
| dev2 | tec programme page known (pipeline picked none) | `b6c37b44` / 10 | E |
| dev3 | imperial `/2027/computing-beng` added (the page the pipeline confirmed) | `78e15c5d` | P |
| dev3 | ucph English twin, um's other BCS specialisations, chula Faculty of Science BSc, auckland calendar plan added | `78e15c5d` | P |
| dev3 | puc, ub, auckland department/major pages added; imperial maths-CS and unsw commerce labelled `related` | `90b45f59` | P |
| dev3 | imperial fee population `international` (Q3, the FE-2b claim) | `79017395` / 02 | P |
| dev3 | chula five ISE labels → `not_applicable` (the page we confirm is another programme, Q6) | `79017395` / 02 | P |
| dev3 | ntutw (picked 1/4), usp (picked 4/4) programme pages known | `b6c37b44` / 10 | P |
| dev3 | msu programme page known (picked 0/4) | `b6c37b44` / 10 | E |
| dev3 | um, ucph, msu gpa → `unknown` (Q7) | `79017395` / 02 | S |
| dev4 | rwth department page added; ctu FEL and unibo CSE labelled `related` | `90b45f59` | P |
| dev4 | `programme.exists` evidence scope drops page titles (KIT's correct claim read `wrong_scope`) — 9 labels | `aec3c69b` | P |
| dev4 | taltech IT-faculty page `related` (the URL the pipeline picked 4/4) | `b6c37b44` / 10 | P |
| dev4 | vut, taltech, boun, itu `known` → `unknown + related` (no exact CS programme) | `f5ee82c1` (owner) | S |
| dev4 | 51 core labels added from the CI evidence check; ktu gpa `unknown` | `2ca3f413`, `8b648fa3`, `b6c37b44` / 09 | E (ktu gpa S) |

**Count of pipeline-motivated (P) change items, by set: cohort 5 (4 of 10 cases), dev2 2 (4 of 10 cases), dev3 6
(10 of 15 cases), dev4 3 (all 9 cases, through the evidence-scope edit) — 16 items touching 27 of 44 development
cases; plus 4 score-driven (S) and 3 expert (E) items.** Ticket 15's proposals took the pipeline's picked URLs as their input by
design. On the scorer side, 15 commits to `metrics.py` / `scorecard.py` / `identities.py` since 2026-10-16
(`git log 72ff9b15..HEAD`), of which the acronym/brand match, the related rule, the canonical-variant and twin
rules and the ID-1 aliases were each motivated by a named development case.

## 5. Reading — which conventions move which rows on development (input for H-2's auditor)

On the frozen base3 development captures, **the programme-page rows depend most on the twin / equivalent-page
convention**: listing a second URL form, a department or major page, or a canonical variant beside the expert's page
is worth 20–36 pp of page recall and 41–53 pp of page precision on dev3 and dev4 (first-URL ablation), and which
single form is listed moves cohort by 30 pp and dev3 by 28 pp by itself; on dev4 the 5/5 "gold returned by search"
survives a one-URL label but confirmed hits fall from 3–4 to 2–3 per column and wrong pages rise from 0 to 1–2.
**The `related` label** (and the scorer rule that a returned related page is neither hit nor wrong) is worth
5–18 pp of page precision (cohort −5.6, dev3 −4.5, dev2 / dev4 −19.4 / −17.6 under the old scorer, where related
and declared twins count against). **The pipeline-declared hreflang twin rule** is worth 10 pp of recall on dev2
only. **The acronym / brand-name university match** moves claim precision and wrong-scope by 8–60 pp
(dev2 −59.6, dev4 −11.8, dev3 −8.3) and known core answered by 19 pp on dev2 — any label whose university is
written as an acronym or brand name, scored by the 2026-10-17 scorer, would read correct claims as wrong scope.
**Population on a label** (SAT, fees) and **the international-round deadline** move claim precision by 8.5–13.5 pp
(cohort SAT, dev2 Uppsala). **Draft award bindings** move known core answered by 7–10 pp on cohort / dev2 / dev3
(one award per set). **Prose GPA → `unknown`** and **`not_applicable` for another programme's labels** move only the
known-core denominators (cohort 28 → 27, dev3 28 → 22), i.e. 2–8 pp of known core answered. dev4's corpus was
born after the twin scorer and lists twins from its first draft; its oldest-corpus drop (−42 pp recall) comes from
the `related` relabelling and the department page added later the same day. These are the conventions an audit of any label file signed before
2026-10-18 should check first, in this order: URL forms and department pages, `related`, university-name form
in evidence scope, populations, award bindings.

## Appendix — bindings ablation, full rows

### bindings: cohort

| row | re-mapped, base3 bindings (control) | re-mapped, reviewed bindings only |
|---|---|---|
| gold_returned_by_search | 8 · 8 · 8 · 8 | 8 · 8 · 8 · 8 |
| gold_never_seen | 0 · 0 · 0 · 0 | 0 · 0 · 0 · 0 |
| gold_confirmed | 5 · 5 · 5 · 5 | 5 · 5 · 5 · 5 |
| cases_with_gold | 10 · 10 · 10 · 10 | 10 · 10 · 10 · 10 |
| confirmed_pages_wrong | 4 · 3 · 5 · 4 | 4 · 3 · 5 · 4 |
| confirmed_pages_related | 2 · 2 · 2 · 2 | 2 · 2 · 2 · 2 |
| programme_page_recall | 5/10 · 5/10 · 5/10 · 5/10 = 50.0% | 5/10 · 5/10 · 5/10 · 5/10 = 50.0% |
| programme_page_precision | 5/9 · 5/8 · 5/10 · 5/9 = 55.6% | 5/9 · 5/8 · 5/10 · 5/9 = 55.6% |
| programme_found_on_readable | 5/8 · 5/8 · 5/8 · 5/8 = 62.5% | 5/8 · 5/8 · 5/8 · 5/8 = 62.5% |
| wrong_programme_pages | 1 · 0 · 2 · 1 | 1 · 0 · 2 · 1 |
| page hit/wrong/related/missed | 5/1/1/3 · 5/0/1/4 · 5/2/1/2 · 5/1/1/3 | 5/1/1/3 · 5/0/1/4 · 5/2/1/2 · 5/1/1/3 |
| claim_precision | 45/45 · 44/44 · 44/44 · 45/45 = 100.0% | 43/43 · 42/42 · 42/42 · 43/43 = 100.0% |
| claims matched (labels hit) | 29/83 · 28/83 · 28/83 · 29/83 = 34.3% | 27/83 · 26/83 · 26/83 · 27/83 = 31.9% |
| known core answered (all) | 14/27 · 14/27 · 13/27 · 14/27 = 50.9% | 12/27 · 12/27 · 11/27 · 12/27 = 43.5% |

### bindings: dev2

| row | re-mapped, base3 bindings (control) | re-mapped, reviewed bindings only |
|---|---|---|
| gold_returned_by_search | 7 · 7 · 7 · 7 | 7 · 7 · 7 · 7 |
| gold_never_seen | 1 · 1 · 1 · 1 | 1 · 1 · 1 · 1 |
| gold_confirmed | 6 · 7 · 7 · 7 | 6 · 7 · 7 · 7 |
| cases_with_gold | 10 · 10 · 10 · 10 | 10 · 10 · 10 · 10 |
| confirmed_pages_wrong | 2 · 0 · 1 · 1 | 2 · 0 · 1 · 1 |
| confirmed_pages_related | 1 · 3 · 1 · 2 | 1 · 3 · 1 · 2 |
| programme_page_recall | 6/10 · 7/10 · 7/10 · 7/10 = 67.5% | 6/10 · 7/10 · 7/10 · 7/10 = 67.5% |
| programme_page_precision | 6/8 · 7/7 · 7/8 · 7/8 = 87.1% | 6/8 · 7/7 · 7/8 · 7/8 = 87.1% |
| programme_found_on_readable | 5/9 · 6/9 · 6/9 · 6/9 = 63.9% | 5/9 · 6/9 · 6/9 · 6/9 = 63.9% |
| wrong_programme_pages | 2 · 0 · 1 · 1 | 2 · 0 · 1 · 1 |
| page hit/wrong/related/missed | 6/2/0/2 · 7/0/1/2 · 7/1/0/2 · 7/1/0/2 | 6/2/0/2 · 7/0/1/2 · 7/1/0/2 · 7/1/0/2 |
| claim_precision | 11/11 · 12/12 · 12/12 · 12/12 = 100.0% | 9/9 · 10/10 · 10/10 · 10/10 = 100.0% |
| claims matched (labels hit) | 11/28 · 12/28 · 12/28 · 12/28 = 42.0% | 9/28 · 10/28 · 10/28 · 10/28 = 34.8% |
| known core answered (all) | 6/21 · 7/21 · 7/21 · 7/21 = 32.1% | 4/21 · 5/21 · 5/21 · 5/21 = 22.6% |

### bindings: dev3

| row | re-mapped, base3 bindings (control) | re-mapped, reviewed bindings only |
|---|---|---|
| gold_returned_by_search | 11 · 10 · 11 · 11 | 11 · 10 · 11 · 11 |
| gold_never_seen | 2 · 3 · 2 · 2 | 2 · 3 · 2 · 2 |
| gold_confirmed | 9 · 9 · 9 · 9 | 9 · 9 · 9 · 9 |
| cases_with_gold | 14 · 14 · 14 · 14 | 14 · 14 · 14 · 14 |
| confirmed_pages_wrong | 1 · 0 · 1 · 1 | 1 · 0 · 1 · 1 |
| confirmed_pages_related | 4 · 3 · 4 · 4 | 4 · 3 · 4 · 4 |
| programme_page_recall | 9/14 · 9/14 · 9/14 · 9/14 = 64.3% | 9/14 · 9/14 · 9/14 · 9/14 = 64.3% |
| programme_page_precision | 9/10 · 9/9 · 9/10 · 9/10 = 92.3% | 9/10 · 9/9 · 9/10 · 9/10 = 92.3% |
| programme_found_on_readable | 9/13 · 9/12 · 9/12 · 9/12 = 73.5% | 9/13 · 9/12 · 9/12 · 9/12 = 73.5% |
| wrong_programme_pages | 1 · 0 · 0 · 1 | 1 · 0 · 0 · 1 |
| page hit/wrong/related/missed | 9/1/1/3 · 9/0/0/5 · 9/0/1/4 · 9/1/0/4 | 9/1/1/3 · 9/0/0/5 · 9/0/1/4 · 9/1/0/4 |
| claim_precision | 11/11 · 13/13 · 11/11 · 13/13 = 100.0% | 9/9 · 11/11 · 9/9 · 11/11 = 100.0% |
| claims matched (labels hit) | 11/26 · 13/26 · 11/26 · 13/26 = 46.2% | 9/26 · 11/26 · 9/26 · 11/26 = 38.5% |
| known core answered (all) | 8/22 · 9/22 · 8/22 · 9/22 = 38.6% | 6/22 · 7/22 · 6/22 · 7/22 = 29.5% |

### bindings: dev4

| row | re-mapped, base3 bindings (control) | re-mapped, reviewed bindings only |
|---|---|---|
| gold_returned_by_search | 5 · 5 · 5 · 5 | 5 · 5 · 5 · 5 |
| gold_never_seen | 0 · 0 · 0 · 0 | 0 · 0 · 0 · 0 |
| gold_confirmed | 3 · 3 · 4 · 4 | 3 · 3 · 4 · 4 |
| cases_with_gold | 5 · 5 · 5 · 5 | 5 · 5 · 5 · 5 |
| confirmed_pages_wrong | 0 · 0 · 0 · 0 | 0 · 0 · 0 · 0 |
| confirmed_pages_related | 2 · 1 · 3 · 3 | 2 · 1 · 3 · 3 |
| programme_page_recall | 3/5 · 3/5 · 4/5 · 4/5 = 70.0% | 3/5 · 3/5 · 4/5 · 4/5 = 70.0% |
| programme_page_precision | 3/3 · 3/3 · 4/4 · 4/4 = 100.0% | 3/3 · 3/3 · 4/4 · 4/4 = 100.0% |
| programme_found_on_readable | 3/5 · 3/4 · 4/5 · 4/5 = 73.7% | 3/5 · 3/4 · 4/5 · 4/5 = 73.7% |
| wrong_programme_pages | 0 · 0 · 0 · 0 | 0 · 0 · 0 · 0 |
| page hit/wrong/related/missed | 3/0/2/4 · 3/0/1/5 · 4/0/2/3 · 4/0/2/3 | 3/0/2/4 · 3/0/1/5 · 4/0/2/3 · 4/0/2/3 |
| claim_precision | 8/8 · 8/8 · 9/9 · 9/9 = 100.0% | 8/8 · 8/8 · 9/9 · 9/9 = 100.0% |
| claims matched (labels hit) | 7/20 · 7/20 · 8/20 · 8/20 = 37.5% | 7/20 · 7/20 · 8/20 · 8/20 = 37.5% |
| known core answered (all) | 2/8 · 2/8 · 2/8 · 2/8 = 25.0% | 2/8 · 2/8 · 2/8 · 2/8 = 25.0% |
