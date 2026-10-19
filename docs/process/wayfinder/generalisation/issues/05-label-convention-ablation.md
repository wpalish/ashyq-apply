# H-A: measurement and corpus drift — the 2×2 re-score and the twin ablation on development

Type: research
Status: open
Blocked by: —
Map: ../map.md · AFK, offline, no run; frozen base3 captures only; **no heldout file is read, and the result says
nothing about the nine — it says how much of the development numbers depends on conventions the nine never got.**

## Question

heldout.reviewed1 was signed on 2026-10-17 (with reviewed10). Since then: corpus round 02 (eight conventions —
award URL alias, SAT key alias, population on fees, `period`, international-round deadline, `not_applicable`
for another programme's labels, prose GPA → `unknown`, twin URLs), tickets 09/10 (draft3: `related` pages, second
source URLs), and 15 scorer commits (`git log --since=2026-10-16 -- metrics.py scorecard.py identities.py`: twins
and canonical variants count as the gold, `related` is neither hit nor wrong, acronym and brand-name university
match, fee period, readable denominator, `--summary-only`). The development labels were reconciled against pipeline
output three times; the nine never. **How much of the development performance is convention?**

## Test

Captures: the base3 artifacts (runs 39172483236 / 39172484697 / 39172486984 / 39172488858; download with
`gh api` into the scratchpad; untrusted data, read with `python3 -I` from scripts outside them).

1. **2×2 re-score**, per set and column, with `scorecard` and `stage_summary`:
   - today's scorer × today's corpora (reviewed11 / dev2.draft3 / dev3.draft3 / dev4.draft3) — the reference;
   - today's scorer × the **oldest** corpora (reviewed10 / dev2.draft1 / dev3.draft1 / dev4.draft1, `--allow-drafts`);
   - the **2026-10-17 scorer** (a `git worktree add` at `72ff9b15`, `python -m evaluation.research.scorecard` from
     there; it has no `--summary-only`, read its per-case table — development only) × today's corpora;
   - the 2026-10-17 scorer × the oldest corpora.
   Rows: `claim_precision`, `wrong_scope_claim_rate`, programme page hit/wrong/related/missed, `known core
   answered` (the old scorer has only the `all` denominator; compare that row across cells), claims matched.
2. **Twin / variant ablation** on dev4 (and dev2/dev3): a script strips every label's `programme_urls` to its first
   URL, drops `related_programme_urls`, and re-counts with today's scorer: `gold_returned_by_search`,
   `gold_never_seen`, `programme_found_on_readable`, `wrong_programme_pages`. dev4 reads 5/5 gold returned today;
   the ablated count is the number the nine would read *if* their labels list one URL form.
3. **Bindings ablation**: re-score dev2/dev3/dev4 with no `--extra-bindings` (the reviewed file only): how many
   claims become `unmapped.*`, how `known core answered` moves (the award questions).
4. **Reconciliation count**: from `SIGN_*`, finish-algorithm 02 and the loop report, list every development label
   change since 2026-10-17 that was motivated by a pipeline reading (Uppsala round, NTU alias, Imperial population,
   Delft twin, …) — count per set.

## Deliverable

`docs/process/LABEL_CONVENTION_ABLATION_2026-10-19.md`: the 2×2 tables per set, the ablation tables, the
reconciliation count, and a one-paragraph reading: **which conventions move which rows by how many pp on
development** — that paragraph is the input H-2's auditor needs (it names conventions, never heldout labels). Verdict
for H-A: *confirmed* if a convention or scorer change moves development page recall or precision by ≥ 10 pp;
*refuted* if every cell is within 5 pp of the reference; *partial* otherwise.

## Files the worker holds

`scratchpad/g05/*` scripts and outputs; the new doc. No repository code changes.

## Done when

The doc is committed with every table; the Answer gives the H-A verdict and the pp figures; the map's Decisions line
is one sentence. Flag: none. Loop id: **G-05**.
