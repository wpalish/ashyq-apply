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

- **S4**, with `index_beyond_budget` on cohort, dev3 and dev4. The process-page half shows on dev3 only, so S4 stays
  one-set (see "S4 process-page check" below).
- **S5**, sibling-host half only, with `award_links_dropped_off_host_same_site` on cohort and dev3.

S6 and S7 have no ES-1 row. They stay one-set, and only a new instrument can lift them.

## S4 process-page check (IB-1 step 1, 2026-10-20)

Note 1 asked whether the index budget went to process or navigation pages before the award index was reached. This
section answers it from the same off-arm captures (`expert-recovery-39355439164`, `-39355443373`, `-39355445801`;
dev2 has no `index_beyond_budget` row). Unlike the tables above, it names development cases, because the check is per
case. Note 1 allows that read. URL paths are shown by shape only, and no award is named. Both reps read the same in
every case.

How it was read: the funding walk writes one `run_diagnostics` line for each index read it charges to the budget
(`classified as …; read as a funding index`) and one for each index it refuses (`not followed, because 3 index pages
have already been read`). Under AP-1 the depth-0 read is not charged, so a case has three charged slots.

| set | case | the 3 charged index reads (path shape) | beyond the budget (path shape) | process page in a slot? | award listing pushed out? |
|---|---|---|---|---|---|
| cohort | ntu | `…/fees-and-funding/financial-aid` (aid hub); `…/financial-aid/<staff-contact list>`; `…/financial-aid/<payment-scheme>` | 6 × `…/financial-aid/<loan, account or emergency-fund slug>` | one slot, a contact list | **no**. The award finder (`…/scholarships-and-awards/scholarship-opportunities`) had already been read as an award read, before any charged slot. It is client-rendered, with 0 links (S1). The six pages refused are loans and payment schemes |
| dev3 | auckland | `…/scholarships-and-awards/scholarship-types` (hub); `…/scholarships-and-awards/scholarship-eligibility`; `…/scholarships-and-awards/how-to-apply` | 10, among them `…/scholarship-types/undergraduate-scholarships`, `…/scholarship-types/scholarships-for-international-students`, `…/undergraduate-scholarships/entry-level-and-first-year-scholarships`, `…/find-a-scholarship`, `…/applications-open-now`, and five population lists (`…/scholarships-for-<group>`) | **two slots**: eligibility and how to apply | **yes**. The undergraduate, international and first-year listings and the finder were all refused |
| dev3 | imperial | `…/fees-and-funding/scholarships-search` (listing); `…/other-funding-sources/external-scholarships` (listing); `…/scholarships-search/<award>-<year>.php` (one award page, classified as an index) | 2 × `…/scholarships-search/<award>-<year>.php`, plus `…/fees-and-funding` (costs) | no | no. Both listings were read |
| dev4 | rwth | `/go/id/<short id>` (listing); `…/Stipendien-Foerderung/…/Liste-von-Stipendien/?page=1` and `?page=2` | 1 × `…/Stipendien-Foerderung/<award>/~<id>/<award>` (one award page) | no | no. The paginated list was read in full |

Why Auckland is the only case: all of its index candidates sit under one `…/scholarships-and-awards/` directory, so
every one gets the same `_award_priority` (`"scholarship"` in the path, rank `(0, 0)`). The stable sort then decides
by queue order alone, and the two process links were queued ahead of the listings. The captures hold no HTML, so this
doc cannot say whether that came from the links' order on the page or from their depth.

**Verdict.** The process-page half of S4 shows on **one set** (dev3, auckland). On cohort, one slot did go to a
navigation page, but no award listing was pushed out. On dev4 and on dev3's imperial the budget went to the award
listings themselves. **S4 stays one-set, and IB-1 is not built** (13-Q2 a). Its trigger is unchanged: an
`index_beyond_budget` case on a second set whose charged slots include a process page while a listing is refused.

**A different shape, recorded and not built.** On dev3 (imperial, 2 per rep) and dev4 (rwth, 1 per rep), the pages
refused for the budget are single-award pages that the classifier calls `scholarship_index`. Their slugs name one award,
and imperial's year-twin of the same award was charged as the third index. That shape is "an award page read as an
index", not S4. It is two-set on the trace row, but it has not been checked against labels: no one has shown that a
refused page is a labelled award, and AP-1 already records the sections on a refused page. If it is worked on, it needs
its own step 1 against the dev3/dev4 labels before any rule.

## AI-1 step 1: does refusing a single-award "index" page cost a labelled claim? (2026-10-20)

The paragraph above recorded a second shape: single-award pages that the classifier calls `scholarship_index` and that
the index budget then refuses (dev3 imperial, dev4 rwth). Before a rule (AI-1: such a page is read as an award page and
is not charged to the index budget) is built, this step asks whether a gold label cites one of those pages. The bar is
two sets: on at least two development sets, a page refused for the index budget, or charged as an index, has to be a
single-award page that a scholarship label cites as evidence. As above, development cases are named, URL paths are
shown by shape only, and no award is named.

**Inputs.** The same off-arm captures (`expert-recovery-39355439164`, `-39355441138`, `-39355443373`, `-39355445801`;
run_tags `lv1-cohort`, `lv1-dev2`, `lv1-dev3`, `lv1-dev4`), two reps per case. Labels: cohort
`ground_truth.reviewed11`, dev2 `dev2.draft3`, dev3 `dev3.draft3`, dev4 `dev4.draft3`. For each case, every
`scholarships.*` label's evidence URL was matched, with the scheme, `www.` and the trailing slash folded, against
every `page_outcomes` row. The rows checked were the ones refused for the budget (`index page beyond the index
budget`) and the ones read as a funding index (`read as a funding index` with page type `scholarship_index`). The same
match was then run the other way: what the off arm did with each gold scholarship evidence URL. Both reps read the same
in every case.

| set | single-award pages classified `scholarship_index` (per rep) | does a scholarship label cite one? | what happened to the labelled award |
|---|---|---|---|
| dev3 | imperial: 2 refused for the budget, both `…/scholarships-search/<award>-<year>.php`, plus 1 charged as the third index, a year-twin of another award (`…/scholarships-search/<award>-<year>.php`) | **no**. None of the three is the labelled award, and the case has a single labelled award | its own page (`…/scholarships-search/<award>-undergraduate-<year>.php`) was read as `scholarship_award` in both reps. The `exists` and `international` predictions both come from that page. Nothing was lost |
| dev4 | rwth: 1 refused for the budget, `…/Stipendien-Foerderung/<award>/~<id>/<award>`, an award for one nationality group | **no**. The case has one labelled award, and its evidence is a costs-and-financing page under `…/Vor-dem-Studium/…` that the walk never reached | not predicted in either rep. Its own award page (`…/Stipendien-Foerderung/<award>/~<id>/<award>`) was read and classified `unknown` ("not an award page"), which is the classifier verdict of S6. It was not classified as an index |
| cohort | none. ntu's six refused pages are loan, account and emergency-fund pages under `…/financial-aid/<slug>`, not awards | no | ntu's labelled award page was never reached (behind the client-rendered finder, S1) |
| dev2 | none (no `index_beyond_budget` row) | no | — |

Across all four sets, a gold scholarship evidence URL shows up among the index-classified pages exactly once: cohort
ubc, `…/scholarships-awards-international-students`. That is a page of several awards, read as an index, with the
labelled award recorded from its own section (AP-1). It is a correct index, not the single-award shape.

**Verdict: 0 sets.** No page refused for the index budget is one a label cites. No single-award page charged as an
index is either. On dev3 the labelled award is already read as an award. On dev4 the labelled award is lost to a
different shape: its own award page, with a German slug, was classified `unknown` (S6's verdict; the captures record
no page language), and the costs page the label cites was never reached.
**AI-1 is not built** (13-Q2 a). Read as award pages, the four refused or charged pages would add only `unmapped.*`
claims, and they would spend award-budget reads.

**Trigger to reopen.** A capture, on two development sets, where a page that a `scholarships.*` label cites appears
with page type `scholarship_index` and either the detail `index page beyond the index budget` or a funding-index read
that records none of that label's claims.

## AW-1 step 1: does the award-page classifier refuse a page a scholarship label needs? (2026-10-20)

S6 note 3 and the AI-1 verdict leave one question open. Is a page that a `scholarships.*` label cites ever fetched and
then classified as not an award page? If so, which classifier test refuses it? The bar for building AW-1 is two sets:
the same refusal cause has to cost a labelled scholarship claim on at least two development sets. As in the sections
above, development cases are named, URL paths are shown by shape only, and no award is named.

**Inputs.** The same off-arm captures (`expert-recovery-39355439164`, `-39355441138`, `-39355443373`, `-39355445801`;
run_tags `lv1-cohort`, `lv1-dev2`, `lv1-dev3`, `lv1-dev4`), two reps per case. Labels: cohort
`ground_truth.reviewed11`, dev2 `dev2.draft3`, dev3 `dev3.draft3`, dev4 `dev4.draft3`. Every evidence URL of a known
`scholarships.*` label was matched against every `page_outcomes` row of every stage. URLs were folded for scheme,
`www.`, trailing slash and `index.html`. A second pass also folded case and dropped the query. It found the same rows.
Separately, every funding-stage row with the detail `not an award page` was listed for the cases that carry scholarship
labels, to catch a labelled award whose own page was refused while the label cites another page. Both reps read the
same in every case, except that rwth's rep 2 refused more unlabelled award pages than rep 1.

| set | known scholarship labels (cases) | cited pages (of them PDF) | cited pages fetched | cited pages fetched and refused as not an award page | labelled award's own page refused (not the cited page) |
|---|---|---|---|---|---|
| cohort | 30 (6) | 9 (1) | 1: ubc's international awards page, read as an index, with the labelled award recorded from its own section (AP-1) | **0** | **0**. ntu's refused pages are the client-rendered award finder and its filtered listings, with 0 links (S1), plus process, costs and loan pages. The labelled award's detail page was never reached |
| dev2 | 14 (7) | 11 (1) | 0 | **0** | **0**. No funding-stage `not an award page` row on any labelled case |
| dev3 | 12 (6) | 7 (2) | 1: imperial's award page, read as `scholarship_award` (3 claims) | **0** | **0**. auckland's two refused pages are a news listing and a PDF guidebook. The labelled award's page was never reached (S4) |
| dev4 | 5 (4) | 4 (0) | 0 | **0** | **1**: rwth, `…/Stipendien-Foerderung/<award>/~<id>/<award>-`, classified `unknown` in both reps. The label cites the costs page under `…/Vor-dem-Studium/…`, which the walk never reached (as AI-1 recorded) |

**Why the one dev4 page is refused.** The capture records no classifier signal for a funding-stage refusal. Its detail
is only `not an award page; no scholarship recorded (<link summary>)`, and no HTML is kept. To find the cause, that one
page was read once, on 2026-10-20, through the production `Fetcher`: robots.txt first, production User-Agent, no
override, no search call. It was then given to today's `classify_page`. That is a re-read of today's page, not the
captured bytes.

- `<html lang="de">`. The identity and title carry the funding word, so the page enters the funding branch.
- `_award_name` accepts the identity as a named award. There is 1 award link, and no listing heading.
- `_AWARD_SIGNALS` finds **0 of 6** signals. The verdict is `funding page with 0 substantive signals and no clear award
  name`, and the type is `unknown`.
- The page states a monthly amount in euros, a target group and an application route, but in German. Every pattern in
  `_AWARD_SIGNALS` is an English word.

The cause is **language**: the value, eligibility and application words exist only in English. It is not structure,
and it is not the name test.

**The same cause elsewhere: latent, not measured.** The other cited pages in a local language were never fetched:

- dev2: kaznu, two `…/ru/…` pages;
- dev2: tec, `…/es/profesional/becas`;
- dev2: uba, a Spanish news page;
- dev3: utokyo, `…/ja/…`;
- dev3: msu, a Russian page;
- dev4: rwth's costs page.

Their loss is reach, not the classifier. Whether the English-only signal words would refuse them cannot be read from
these captures.

**Verdict: 0 sets on the strict reading, 1 set on the loose one.** No page a `scholarships.*` label cites was fetched
and refused, on any set. Only one labelled award's own page was refused: dev4 rwth, for language, and the label cites
a different page. **AW-1 is not built** (13-Q2 a). `AWARD_PAGE_RECOGNITION_V2` was not added, and no replay was
dispatched.

**Trigger to reopen.** A capture, on a second development set, where a page that a `scholarships.*` label cites, or
the labelled award's own page, is fetched in a `languages.json` language other than English and refused with `not an
award page`, with fewer than two `_AWARD_SIGNALS`. It is most likely to show up once reach work brings the dev2 or
dev3 local-language pages above into the walk.

To make that trigger measurable from captures, the funding-stage detail would need two additions:

- the classifier's own signal (for example, `funding page with N substantive signals`), as a controlled category;
- the page's `<html lang>`.

That is an ES-1-style instrument change. It is not part of this step.
