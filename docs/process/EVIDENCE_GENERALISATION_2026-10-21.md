# Evidence-stage sizing on the four development sets (G-16a, 2026-10-21)

Ticket 16 (`wayfinder/generalisation/issues/16-evidence-stage-generalisation.md`) items 1, 3 and 4, read on the four
development sets ahead of R2. Item 2 is answered (LV-1, in the ticket). Each item gets a verdict:

- **dev-wide**: no two development sets differ by 15 pp or more.
- **set-dependent**: two sets differ by 15 pp or more.

A dev-wide item is a residue line for the finish algorithm. A set-dependent item names its mechanism.

Everything below is an aggregate. The doc has no per-case row and no university name. No dev5 data and no held-out
file, capture, log or label was opened. No search provider was called, because the captures are recorded-search
replays. The **dev5** column is left empty and is filled when R2 exists. Research only: no code change, no default
change, and no DoD row moves.

## Inputs

- **Captures.** These are `benchmark-capture.yml` runs on branch `claude/greeting-16wj2z` at pipeline `441756a6`, with
  `mode=expert_paired`, `search_provider=recorded` and store `recorded_search.base3.json`. Their `run_tag` is
  `aw2-{set}`, and `aw2-ko-{set}` for the knockout arm. They were dispatched 2026-10-20 04:43 UTC. Run ids, in set order
  cohort, dev2, dev3, dev4:
  - normal arm: 39371051329, 39371053780, 39371056063, 39371058290;
  - knockout arm: 39371060304, 39371062161, 39371064285, 39371066311.

  The artifacts are `expert-recovery-<run id>`.
- **Columns.** The **off** arm is the default config at `441756a6`, with LV-1 on and AW-2 off. It is shown as
  `off#1 / off#2`, with the two values merged into one when they are equal. AW-2 has since been turned on by default
  (HANDOFF §8, 2026-10-20). Today's default is therefore the **on** arm. Where the on arm differs from the off arm, it is
  given in its own row.
- **Corpora.** cohort `ground_truth.reviewed11`, dev2/dev3/dev4 `*.draft3`. Bindings are those the workflow loads:
  draft2, dev2-draft1, dev3-draft1 and dev4-draft3. The dev5 binding file is also loaded by the workflow, but no dev5
  case was run and this doc did not read it.
- **Tools.** `python -m evaluation.research.stage_summary <captures> --dataset <corpus>` gives the rows named in
  backticks. The leak check exited 0 on all eight captures. The other rows come from a scratch reader. It uses the
  scorer's own functions:
  - `metrics.adjudicate` decides `labelled`. A claim is unlabelled when the case has no label for its key, or when
    the label is `unknown` or `not_applicable`.
  - `metrics.adjudicate_programme_pages` gives the case outcome and the hit, related and wrong page sets.
  - `stage_summary.claim_type` and `_evidence_stage` give the claim type and the evidence stage.
  - `expressibility.report` gives item 4.

  The reader prints counts only, and it is not committed.
- **Cases.** cohort 10, dev2 10, dev3 15, dev4 9.

## Item 1: unlabelled claims

### 1a. Share, and what the unlabelled claims are

| row (off arm) | cohort | dev2 | dev3 | dev4 | dev5 |
|---|---|---|---|---|---|
| `claims` | 55 | 21 | 83 / 82 | 8 | |
| `verdict:unlabelled` | 32 | 14 | 72 / 71 | 2 | |
| **unlabelled ÷ claims** | **58.2%** | **66.7%** | **86.7% / 86.6%** | **25.0%** | |
| on arm (today's default, AW-2 on) | 58.2% | 63.2% / 65.0% | 86.4% / 86.6% | 50.0% / 45.5% | |
| *by why* | | | | | |
| no label for the key in this case | 21 | 13 | 70 / 69 | 2 | |
| label exists but `unknown` (reviewer could not establish it) | 11 | 1 | 2 | 0 | |
| *by key class* | | | | | |
| `unmapped.*` (no corpus key can ever match) | 18 | 2 | 52 | 1 | |
| key never labelled `known` anywhere in this set | 2 | 11 | 19 / 18 | 1 | |
| key labelled elsewhere in this set (scorable in principle) | 12 | 1 | 1 | 0 | |
| *by claim type* | | | | | |
| `programme.exists` | 0 | 8 | 13 / 12 | 0 | |
| `unmapped.scholarship_*` | 6 | 0 | 44 | 1 (on: 5 / 4) | |
| other `unmapped.*` (accepted test types, waivers, interview, entrance exam, credential evaluation, GPA) | 12 | 2 | 8 | 0 | |
| English and other tests (TOEFL, Duolingo, IELTS, SAT) | 8 | 1 | 3 | 0 | |
| other mapped keys (intake, intake.open, faculty, language, deadline, tuition, award applicability) | 6 | 3 | 4 | 1 | |

### 1b. Where the unlabelled claims come from

The sources are:

- **programme page**: the claim's evidence URL is a confirmed programme page, split by
  `adjudicate_programme_pages`;
- **evidence page**: any other page, by the evidence stage of its page outcome.

| unlabelled claims by source (off arm) | cohort | dev2 | dev3 | dev4 | dev5 |
|---|---|---|---|---|---|
| confirmed programme page = gold | 2 | 8 | 16 | 1 | |
| confirmed programme page = related | 1 | 3 | 2 | 0 | |
| confirmed programme page = wrong | 0 | 0 | 1 / 0 | 0 | |
| requirements-stage page | 17 | 0 | 2 | 0 | |
| scholarships-stage page | 6 | 0 | 44 | 1 | |
| costs-stage page | 1 | 0 | 0 | 0 | |
| other page type | 0 | 3 | 6 | 0 | |
| evidence URL with no page outcome (PDF or alias) | 5 | 0 | 0 | 0 | |
| no evidence | 0 | 0 | 1 | 0 | |
| **in cases whose programme outcome is `hit`** | **31 of 32** | **11 of 14** | **71 of 72** | **1 of 2** | |

### 1c. What a wrong page yields (knockout arm, gold page removed)

| row (knockout, off arm) | cohort | dev2 | dev3 | dev4 | dev5 |
|---|---|---|---|---|---|
| `claims` | 32 / 40 | 9 | 45 / 44 | 3 | |
| unlabelled ÷ claims | 75.0% / 67.5% | 77.8% | 100% | 33.3% | |
| labelled claims kept | 8 / 13 | 2 | 0 | 2 | |
| unlabelled claims from a wrong or related programme page | 1 | 4 | 4 / 3 | 0 | |
| unlabelled `unmapped.scholarship_*` | 3 / 4 | 0 | 35 | 1 | |

### Reading

The unlabelled share ranges from **25.0% (dev4) to 86.7% (dev3)**, a spread of 61.7 pp. On today's default (AW-2 on)
the range is 45.5% to 86.6%.

Wrong pages do not drive it. Two counts show this:

- at most 1 unlabelled claim per set comes from a wrong programme page;
- 97%, 79%, 99% and 50% of unlabelled claims come from cases whose programme page is the gold page.

Three things set-specific to the set drive it instead:

1. **How many award pages the funding stage reads.** dev3 reads 34 award sections (REACH_ROWS). Its 44
   `unmapped.scholarship_*` claims are 53% of all its claims. Those claims are award names that bind to no labelled
   award. dev4 has 1 such claim with AW-2 off and 4–5 with AW-2 on, which is the expected AW-2 shape.
2. **Which keys the corpus labels at all.** The dev2 and dev3 corpora carry no `programme.exists` label. Their 8 and
   13 confirmed-programme claims therefore read as unlabelled. cohort and dev4 label that key, so the same claims count
   as matched there.
3. **Reviewer `unknown` labels.** In cohort, 11 claims answer a question the reviewer marked `unknown`. They are
   unscored and could be right or wrong. dev2 has 1 and dev3 has 2.

Other `unmapped.*` claims appear on three of the four sets (12, 2, 8, 0). These are claim types with no corpus key:
accepted IELTS variants, waivers, interview, entrance exam. This is the dev-wide part. It is a residue of the corpus
schema, not a sign that discovery fails to generalise.

**Verdict, item 1: set-dependent** (61.7 pp between dev3 and dev4). The mechanism is not country, and dev4 is the low
set, not the high one. The share is set by two things:

- how many award pages the funding stage reads, which turns into `unmapped.scholarship_*`;
- the corpus's label coverage: whether the set labels `programme.exists`, and how many `unknown` labels it has.

Matched-claim precision does not hide wrong-page output. On the sets where the gold page is found, the knockout arm
shows the wrong-page shape: claims fall by 27–63%, and what is left is mostly unlabelled. On cohort, the labelled
claims that remain come from university-wide requirements pages. On dev5 the item will read whatever its corpus labels. Before R2 compares the dev5 unlabelled share with
these columns, check whether dev5 labels `programme.exists` and how many `unknown` labels it has.

## Item 3: costs pages

### 3a. The `stage_summary` rows (pages whose classified type is `costs`, any stage)

| row (off arm) | cohort | dev2 | dev3 | dev4 | dev5 |
|---|---|---|---|---|---|
| `pages:costs` | 14 | 5 | 7 / 9 | 2 | |
| `pages_fetched_ok:costs` | 2 | 0 | 0 | 0 | |
| **fetched ok ÷ pages** | **14.3%** | **0%** | **0%** | **0%** | |
| distinct costs-typed pages, fetched ok ÷ all | 2 of 11 (18.2%) | 0 of 4 | 0 of 6 / 0 of 7 | 0 of 2 | |
| why not ok: read, no cost figures extracted (`no-pattern-match`) | 9 | 4 | 6 / 8 | 2 | |
| why not ok: funding stage read it, "not an award page" | 3 | 0 | 0 | 0 | |
| why not ok: requirements stage read it, "classified as costs; no requirement can be read" | 0 | 1 | 0 | 0 | |
| why not ok: index beyond the index budget, not followed | 0 | 0 | 1 | 0 | |
| `budget_refused:*` in a costs phase | 0 | 0 | 0 | 0 | |
| discovery: candidate read and refused as `reads_as:costs` | 0 | 0 | 2 / 3 | 1 | |

The on arm reads the same, except that dev2 has 4 / 5 pages and dev3 has 9 / 9.

### 3b. The cost stage itself (`WebCostAdapter` page reads, any page type, distinct page × outcome)

`pages:costs` cannot see two kinds of cost-stage read:

- a read that failed, because a fetch-failed or unreadable outcome carries no `page_type`;
- a read of a fee page classified as another type (QR-1 fee-question pages).

This table counts the stage by its own outcome text instead.

| row (off arm) | cohort | dev2 | dev3 | dev4 | dev5 |
|---|---|---|---|---|---|
| cost-stage reads | 13 | 10 | 13 / 15 | 4 | |
| fetched ok (≥ 1 cost figure) | 2 | 1 | 0 | 0 | |
| **ok ÷ reads** | **15.4%** | **10.0%** | **0%** | **0%** | |
| read, no cost figures extracted | 8 | 9 | 12 / 14 | 3 | |
| fetch failed: robots disallowed | 2 | 0 | 0 | 0 | |
| fetch failed: HTTP error | 1 | 0 | 0 | 1 | |
| fetch failed: timeout | 0 | 0 | 1 | 0 | |
| PII guard | 0 | 0 | 0 | 0 | |
| page type of the no-figure reads: `costs` / programme or detail / other / `unknown` | 6 / 1 / 0 / 1 | 3 / 0 / 1 / 5 | 5 / 1 / 1 / 5 (off#1) | 2 / 0 / 0 / 1 | |
| median readable characters of the no-figure reads (off#1) | 1,986 | 2,355 | 3,298 | 3,005 | |

### 3c. Is the fee on the programme page? (FE-2b)

| row | cohort | dev2 | dev3 | dev4 | dev5 |
|---|---|---|---|---|---|
| `tuition` labels known / unknown | 4 / 6 | 1 / 9 | 1 / 14 | 0 / 9 | |
| known tuition labels citing the gold programme page | 2 of 4 | 0 of 1 | 1 of 1 | — | |
| tuition claims from a confirmed programme page / another page (off arm) | 2 / 3 | 0 / 1 | 1 / 0 | 0 / 0 | |
| cost-stage ok read on a programme-typed page | 0 | 1 | 0 | 0 | |

dev4 has no known tuition label, so FE-2b cannot score there. The expert notes on dev4's 9 `unknown` tuition labels
say where the fee sits:

| where the fee sits (dev4, 9 labels) | count |
|---|---|
| on the programme page, for 2026/27 only | 1 |
| explicitly not on the programme page | 2 |
| on a separate fees, costs or tuition page | 3 |
| no location stated: free by law, fees by income band, or not established | 3 |

### Reading

The costs stage refuses almost nothing. It reads the page and then extracts no figure:

- on the stage's own count, no-figure reads are 62%, 90%, 92–93% and 75% of cost-stage reads;
- fetch failures (robots, HTTP error, timeout) total 0–3 per set;
- there were no budget refusals in a costs phase and no PII-guard refusals.

The stage yields a figure on at most 2 pages per set, and on 0 pages on dev3 and dev4. Two of cohort's four known
tuition labels cite the programme page, as does dev3's single label. dev4's labels place the fee on the programme page
once in nine. So the fee sits on the programme page on some sites and on a separate page on others, on every set where
it can be told. A rule that reads the fee in one place covers about half the sites.

**Verdict, item 3: dev-wide.** On the pre-registered row (`pages_fetched_ok:costs ÷ pages:costs`) the sets are 14.3%,
0%, 0% and 0%, a spread of 14.3 pp, below the 15 pp bar. The verdict is borderline. On distinct pages (18.2 pp) and on
the stage's own read count (15.4 pp), cohort's 2 ok pages cross the bar. That is two pages on one set against zero
elsewhere, and the mechanism is the same on all four: the page is read and no figure is extracted. The costs stage is
a stage that works nowhere. It is a finish-algorithm residue line, not a generalisation cause. Two things are left open:

- why the extractor finds no figure on pages it reads, whether there is no figure, a figure for the wrong year, or a
  table it does not parse;
- the ≈ 2–3 k readable characters per page, which suggest thin pages or navigation shells.

Both need a per-page look on development, which is out of scope here.

## Item 4: award expressibility

`expressibility.report` was run with each set's own bindings: cohort draft2, dev2-draft1, dev3-draft1 and dev4-draft3.
The union of all four reads the same. A known award label (`scholarships.*`) is unexpressible when no claim could
ever map to it:

- its award is not bound (`identity not bound`);
- its field is not mapped (`bound, field not mapped`).

| row | cohort | dev2 | dev3 | dev4 | dev5 |
|---|---|---|---|---|---|
| known award labels | 30 | 14 | 12 | 5 | |
| awards they name | 7 | 7 | 6 | 4 | |
| reachable | 28 | 14 | 12 | 5 | |
| identity not bound | 2 (1 award: `exists`, `applicability.application_mode`) | 0 | 0 | 0 | |
| bound, field not mapped | 0 | 0 | 0 | 0 | |
| **unexpressible ÷ known award labels** | **6.7%** | **0%** | **0%** | **0%** | |
| fields labelled | 14 kinds (`exists`, applicability ×5, coverage ×5, bond, duration, renewal) | `exists`, `applicability.international` | `exists`, `applicability.international` | `exists`, `applicability.international` | |
| all known labels reachable (context) | 72 / 83 | 27 / 28 | 26 / 26 | 20 / 20 | |
| *live side (off arm): award claims emitted that mapped to a bound award* | 2 of 8 | — (0 emitted) | 3 of 47 | 0 of 1 (on: 0 of 5 / 4) | |
| *known award labels answered by a claim* | 2 of 30 | 0 of 14 | 2 of 12 | 0 of 5 | |

### Reading

Unexpressible award labels are 0–6.7% on every set, a spread of 6.7 pp. This reads near 0 by construction. Each
development draft's bindings were written together with its labels, so a reviewer who labels an award also binds it.
The ceiling therefore measures binding completeness, and it is complete. The award gap sits on the emit side:

- the pipeline names awards that bind to no labelled award (`unmapped.scholarship_*`, item 1);
- it answers 0–2 known award labels per set.

**Verdict, item 4: dev-wide** (6.7 pp). Expressibility is not a generalisation cause on development. Its dev5 reading
depends only on whether dev5's draft bindings cover its award labels, not on the pipeline. The live award loss is
item 1's `unmapped.scholarship_*` mechanism, and it is set-dependent through award-page reach.

## Summary

| item | measure | cohort | dev2 | dev3 | dev4 | spread | dev5 | verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | unlabelled ÷ claims (off arm) | 58.2% | 66.7% | 86.7% | 25.0% | 61.7 pp | | **set-dependent**: award-page reach and corpus label coverage, not wrong pages, not country |
| 3 | `pages_fetched_ok:costs ÷ pages:costs` | 14.3% | 0% | 0% | 0% | 14.3 pp | | **dev-wide**, borderline: the stage reads and extracts nothing almost everywhere |
| 4 | unexpressible ÷ known award labels | 6.7% | 0% | 0% | 0% | 6.7 pp | | **dev-wide**: bindings are complete; the gap is on the emit side (item 1) |

For R2, fill the dev5 column with the same rows from `stage_summary`, at aggregate level. Items 1b, 1c and 3b need
the scorer's per-claim and per-outcome fields, so on dev5 they can be read only as aggregates of a script like this
one, run inside the leak check. If that is not cleared under 13-Q1, item 1's dev5 cell is `verdict:unlabelled ÷
claims` alone.
