# Reach rows on the four development sets (ES-1, 2026-10-20)

This doc asks one question for NEXT_CYCLES_2026-10-20 §3. Which of the regime-A reach shapes S4–S7 show their ES-1
trace row on **two or more** development sets? Two sets is the bar for building a reach rule (13-Q2 a).

Everything below is an aggregate. No per-case row, no dev5 data, no held-out data. No search provider was called; the
captures are recorded-search replays.

## Inputs

- **Captures.** The `expert_paired` runs of `benchmark-capture.yml` with run_tag `lv1-{cohort,dev2,dev3,dev4}`, branch
  `claude/greeting-16wj2z`, pipeline `4d7c6b41`, dispatched 2026-10-20 01:48 UTC. Run ids, in set order: 39355439164,
  39355441138, 39355443373, 39355445801. Artifacts `expert-recovery-<run id>`. These are the newest completed paired
  runs whose off arm is the default config.
- **Columns.** `off#1` and `off#2` are the default arm, with LV-1 off as it was at `4d7c6b41`. The on arm adds
  `--lexicon-language-coverage`, which is today's default. LV-1 had no stable change on any set, and every reach row
  below reads the same within noise in both arms.
- **Store.** `recorded_search.base3.json`. Bindings: draft2, dev2-draft1, dev3-draft1, dev4-draft3, dev5-draft1. The
  dev5 file is loaded by the workflow, but no dev5 case was run.
- **Corpora.** cohort `ground_truth.reviewed11`, dev2 `dev2.draft3`, dev3 `dev3.draft3`, dev4 `dev4.draft3`.
- **Command.** `python -m evaluation.research.stage_summary <captures> --dataset <corpus> --out …`. The leak check
  passed on all four sets (exit 0).

**`run_diagnostics` coverage.** ES-1 (`42d6181b`) is an ancestor of `4d7c6b41`, so these captures carry the
off-host award-link line. Of the off-arm raw reports, the number with a non-empty `discovery_trace.run_diagnostics`
is: cohort 20/20, dev2 20/20, dev3 28/30, dev4 14/18. The field is written only when it has lines, so a missing field
means none. Every zero below is therefore a measured zero.

**Rows that are 0 by construction on older captures.** On any capture made before ES-1, such as `rp-base3-*` and every
earlier dispatch, these two rows read 0 no matter what the pipeline did:

- `award_links_dropped_off_host`
- `award_links_dropped_off_host_same_site`

The drop in `_award_links` was silent before ES-1, and the funding stage's `errors` were not serialised into the
capture. The other ES-1 rows come from `PageOutcome.detail` or the trace's `selected` field, so they read correctly on
older captures too:

- `funding_index_zero_links`
- `index_beyond_budget`
- `award_sections_read`
- `funding_entry_none`
- `pdf_met`
- `evidence_reach`

## Evidence rows per set (default arm, off#1 / off#2)

Cases per set: cohort 10, dev2 10, dev3 15, dev4 9. A row that is missing from the tool's output is shown as 0.

| row | cohort | dev2 | dev3 | dev4 |
|---|---|---|---|---|
| funding_index_zero_links | 6 / 6 | 11 / 12 | 14 / 13 | 6 / 5 |
| index_beyond_budget | 6 / 6 | 0 / 0 | 13 / 13 | 1 / 1 |
| award_sections_read (sum) | 3 / 3 | 0 / 0 | 34 / 34 | 1 / 1 |
| award_links_dropped_off_host (sum) | 21 / 21 | 0 / 0 | 37 / 37 | 2 / 2 |
| award_links_dropped_off_host_same_site (sum) | 7 / 7 | 0 / 0 | 5 / 5 | 0 / 0 |
| funding_entry_none (cases) | 0 / 0 | 6 / 7 | 9 / 9 | 6 / 6 |
| pdf_met:other | 0 / 0 | 3 / 3 | 3 / 2 | 0 / 0 |
| refusals `budget_refused:funding:award` (TB-1) | 2 / 2 | 0 / 0 | 2 / 2 | 5 / 0 |
| pages_fetched_ok:scholarships | 11 / 11 | 0 / 0 | 14 / 14 | 6 / 6 |

`evidence_reach:<question>` is the number of known labels whose evidence page was fetched ok, out of all known labels.
It counts HTML evidence only. A dash means the set has no label for that question.

| question | cohort | dev2 | dev3 | dev4 |
|---|---|---|---|---|
| programme_exists | 3/10, 3/10 | — | — | 4/9, 3/9 |
| deadline | 3/6, 4/6 | 1/3, 1/3 | 2/4, 2/4 | — |
| tuition | 2/4, 2/4 | 1/1, 1/1 | 1/1, 1/1 | — |
| ielts_overall | 1/4, 1/4 | 2/3, 1/3 | 2/4, 2/4 | 0/3, 0/3 |
| ielts_subscores | 1/3, 1/3 | 2/3, 1/3 | 2/3, 2/3 | 0/1, 0/1 |
| english_evidence | 2/2, 2/2 | 2/4, 2/4 | 0/1, 0/1 | 0/2, 0/2 |
| scholarship_exists | 1/7, 1/7 | 0/7, 0/7 | 1/5, 1/5 | 0/4, 0/4 |
| scholarship_international | 1/6, 1/6 | 0/6, 0/6 | 1/4, 1/4 | 0/1, 0/1 |
| scholarship_coverage | 0/7, 0/7 | — | — | — |
| other | 1/33, 1/33 | — | — | — |

The following questions have PDF-only evidence, so they sit outside the HTML denominator:

| question | cohort | dev3 | dev2 |
|---|---|---|---|
| `evidence_reach_pdf:scholarship_international` | 0/1 | 0/2 | 0/1 |
| `evidence_reach_pdf:deadline` | — | 0/1 | — |
| `evidence_reach_pdf:scholarship_exists` | — | 0/1 | — |

On every set, `scholarship_exists` and `scholarship_international` are the lowest HTML reach rows, together with
`scholarship_coverage` on cohort. SR-1 pre-registered exactly that.

## Verdict per shape (S4–S7)

| shape | ES-1 signature row | sets where it is non-zero (stable in both reps) | verdict |
|---|---|---|---|
| S4 hub of hubs, index budget spent on process pages | `index_beyond_budget` (+ `award_sections_read` on the same indexes) | cohort 6, dev3 13, dev4 1 → **3 sets** | **two sets → candidate rule**, at the trace-line level. See note 1 |
| S5 funding index refused by TB-1; award links on a sibling official host dropped | `award_links_dropped_off_host_same_site` (the sibling-host half); `budget_refused:funding:award` (the TB-1 half) | same-site drop: cohort 7, dev3 5 → **2 sets**. TB-1 refusal: cohort, dev3 (2/2 each), dev4 unstable (5/0) | **two sets → candidate rule** for the sibling-host half only (`_award_links` keeps a link on the index's own registrable domain). See note 2 |
| S6 local-language award page refused by the classifier | none. ES-1 has no row for a classifier "not an award page" verdict, and pages carry no recorded `<html lang>` | not measurable by ES-1 | **one set** (dev4, on record). Not built. See note 3 |
| S7 programme twin with a funding block, returned and never read | none. A returned twin that is never read is a walker outcome, not an evidence detail | not measurable by ES-1 | **one set** (dev4, on record). Not built |

### Notes

1. **S4.** The row shows that indexes beyond the budget occur on three sets. It does not show the other half of the
   shape: that the budget went to process pages (`eligibility`, `how to apply`). Before building the rule from SR-1
   §2, a worker should check, on the cohort and dev4 traces, that the counted index reads include an SP-1 process page.
   That is a development-set read and is allowed. If none does, S4 stays one-set. The guard stands as written:
   `reads_total` must not rise elsewhere.
2. **S5.** The same-site count is the number of dropped links, not the number of indexes or cases. It does not show
   that a dropped link leads to a labelled award. The rule's bar on replay is the usual one: no new wrong page, no
   stable claim loss, and a stable gain on at least one set. The TB-1 half is clock-bound and stays out of scope, as
   in SR-1. Other-host drops (cohort 14, dev3 32, dev4 2) are third-party links, and following them is not part of S5.
3. **S6.** This one is outside the ES-1 rows. A raw count of capture text finds the classifier's "not an award page"
   verdict on cohort (2 cases), dev3 (1) and dev4 (2), and on none of dev2. That count is an upper bound for S6. It
   includes English pages, and no aggregate row can say which pages were in the local language. Making S6 measurable
   needs one more ES-1 category, such as `award_page_not_award`, and a page-language source, because the captures
   record no `<html lang>`.

**Answer.** Two shapes clear the two-set bar at the level of their ES-1 trace rows:

- **S4**, with `index_beyond_budget` on cohort, dev3 and dev4. The process-page half is still to be confirmed (note 1).
- **S5**, sibling-host half only, with `award_links_dropped_off_host_same_site` on cohort and dev3.

S6 and S7 have no ES-1 row. They stay one-set, and only a new instrument can lift them.
