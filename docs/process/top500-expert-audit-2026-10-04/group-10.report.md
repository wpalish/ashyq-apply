# Group 10: evaluation blind spots and a practical benchmark

Date: 2026-10-04. Audit input baseline: `144881b`. Exactly 50 packet rows, indices 10,20,…,500. Independent non-blind engineering diagnosis; no other group report read. Full production seed importer and retriever executed in isolated SQLite memory database: **500 seed observations, 501 university identities**. No production database, network, provider, gold-answer file, source-code change or commit. Socket connections are disabled by the probe.

## Reproduction and evidence

From repository root:

```sh
backend/.venv/bin/python docs/process/top500-expert-audit-2026-10-04/group-10.probe.py
```

The script writes only `group-10.rows.json`, including every original seed ID/name, imported ID, actual query/results/ranks, aliases, hints, route reasoning, observations, risk, and `live_checked=false`. It records packet/seed/registry and relevant source hashes. Six invented draft-only scorer examples are under `synthetic_metric_probes`; none is an admissions observation. Route classifications inspect actual imported fields and the production branch in `catalogue/discovery.py:88-114`; no live enrichment was executed.

| Measurement | Result | What it establishes |
|---|---:|---|
| Exact seed name / canonical name target presence | 50/50 each | Imported identity is locally retrievable |
| Unique canonical-name result | 44/50 | Six exact name queries also match unrelated rows |
| Canonical-name target ranked first | 47/50 | Three exact-name searches put another institution first |
| Normalized/accent-folded names | 50/50 | Normalization preserves target inclusion |
| Short name variant | 50/50 presence; 42/50 unique | Removing generic words preserves recall, sometimes broadens results |
| Supplied aliases | 68/68 query hits; 59/68 unique | Counts aliases, not universities |
| Name plus original seed country | 34/50 | Sixteen misses from query-country vocabulary |
| Name plus normalized country / separate country filter | 50/50 each | Controls recover all sixteen misses |
| Name plus city | 50/50 presence; 46/50 unique | City alone cannot reliably distinguish institutions |
| Domain-as-query exploratory test | 1/34 | Domain is not indexed; exploratory feature limitation, not a promised contract |
| Curated / generic with hints / generic needing search | 1 / 35 / 14 of 50 | Unequal discovery starting conditions |
| Imported domain curated / seed / unknown | 1 / 33 / 16 of 50 | Unknown domain does not mean failed research |
| Conflicting seed domain and website hosts | 2/50 | Importer intentionally abstains; website hint remains available |
| Included in unfiltered first 50 catalogue results | 1/50 | Default bounded list is not representative of this packet |
| Overlap with fixed ten-case cohort | 1/50, Warsaw | Existing benchmark cannot establish performance for other 49 |
| Programme / fact / live verification cases measured here | 0 / 0 / 0 | All such recall values remain null |

All 50 are unverified seed observations. No missing seed field is classified as a confirmed source defect. The two conflicts are Johns Hopkins (`jh.edu` vs `jhu.edu`) and Indiana Bloomington (`indiana.edu` vs `iu.edu`); their imported unknown status is consistent with `importer.py:139-144` and does not establish which live site is valid.

## Ranked hypotheses for general improvement

### 1. Add a joint supported, scoped, current fact metric before interpreting recall as usable answers

**Observed metric property**, not a claim that any of the 50 has a wrong admissions fact. `evaluation/research/metrics.py:186-203` accepts any nonempty, untruncated sibling-domain excerpt when value and scope match. `:212-221` records currentness separately; `correct` does not require it. Mapper `map_claims.py:28-45` deliberately leaves adjudication unknown; production confidence is not human review.

Synthetic production-scorer probes reproduce:

- A matching tuition value/scope with an unrelated football quote on a sibling page scores claim recall **1/1**, same-page recall **0/1**, support adjudication **0/1**, unsupported rate **0/0=null**.
- Exact evidence with `current=false` scores claim recall **1/1**, current-evidence rate **0/1**.
- Exact evidence with unknown currentness scores recall **1/1**, current rate **0/0=null**.
- Negative controls: wrong intake and explicit `supported=false` score recall **0/1**.

**Affected counts:** 50/50 have no live supported/scoped/current fact measurement in this audit; number with actual source-support errors is **unmeasured**, not 50 or zero. The current metric remains useful as its defined reference-corpus score, but its name cannot stand in for the joint student-answer criterion. `reference_acceptance.py:51-55` already explicitly excludes freshness, unadjudicated extras and new institutions from acceptance scope.

**Hypothesis:** A companion metric requiring independently confirmed support and current applicability will prevent false confidence while allowing truly equivalent official sibling pages. Do not silently rewrite signed scoring definitions. Preserve legacy score; add separate exact-source, adjudicated-sibling, current, and joint indicators. **Counterexample/control:** legitimate duplicate fee pages must receive credit after support adjudication; exact URL alone does not prove the quote supports the value either. **Held-out test:** on the independently selected cohort below, adjudicators inspect every scored positive prediction and a fixed random sample of abstentions under equal review time; compare both metric classifications and actual supported/scoped/current recall. No additional crawl or token budget for either arm.

### 2. Rank whole-name and whole-alias matches ahead of substring/location matches

**Observed retrieval weakness.** `catalogue/retrieval.py:97-99` checks each token as a substring of a concatenation of name, country, city and aliases. Ordering `:104-110` prioritizes curated status then alphabetic name, without exact-name relevance.

Affected: **6/50** canonical queries return multiple rows, **3/50** put target below rank 1. Qatar University ranks second behind Hamad Bin Khalifa University; University of Tehran third behind Amirkabir and Sharif; LUT University second behind Complutense because `lut` occurs inside `Complutense`. University of Glasgow, Nanjing University and North Carolina State University have extra hits but remain first. Student impact: the full input name can select another university if UI or user assumes first result is exact.

**Hypothesis:** Lexically exact canonical/alias tier, followed by whole-token matches and only then substring matches, improves top-1 without dropping candidate recall. **Controls:** Glasgow/Nanjing already have correct rank 1; short-prefix autocomplete must still work, so removing substring support globally is not established as safe. **Held-out test:** independently authored full-name, acronym, partial-name and city queries; equal candidate limit; report target recall@1/@5, candidate recall, ambiguity and wrong-institution selections separately. Freeze query lists before implementation. No hardcoded university exceptions.

### 3. Normalize country aliases consistently between free text and structured filters

**Observed query miss.** Exact names all work, but appending original seed country misses **16/50**. `importer.py:22-45` canonicalizes country storage and `retrieval.py:95` canonicalizes the country filter, whereas `retrieval.py:89,97-99` uses unexpanded free-text tokens. US, mainland China and Hong Kong raw labels expose this asymmetry. Johns Hopkins + “United States of America” is a representative miss; Nanjing + “China (Mainland)” is another.

**Hypothesis:** Conservatively recognize country phrases in free-text search using the existing alias vocabulary, then apply equivalent filters. All sixteen are recovered by normalized-country or structured-filter controls. **Controls:** remaining **34/50** already work with raw country; distinguish “Georgia” in an institution name from a country constraint; a broad word-deletion rule could hurt precision. **Held-out test:** same independently authored queries paired across raw/canonical country phrases, reporting recall and false inclusions. Equal query count and result limit; require unchanged exact-name recall and no increase in wrong-institution top-1.

### 4. Evaluate generic discovery strata explicitly and allocate early research fairly

**Observed representativeness gap; downstream performance is unmeasured.** **49/50** assigned rows use generic discovery, split **35** with hints and **14** needing search immediately. Warsaw is the only curated row and only overlap with `evaluation/research/live.py:27-40`'s fixed ten. None overlaps its nine legacy held-out registry domains (`:46-56`). `catalogue/discovery.py:44-49,65-76` slices candidates before enrichment and only enriches the first `live_limit`; retriever ordering makes only **1/50** packet identities appear in the first 50 unfiltered results.

**Hypothesis:** A benchmark sampled across discovery routes will reveal budget sensitivity hidden by curated-only cohorts; a bounded per-stratum exploratory schedule may improve useful student coverage. The first-50 figure is a selection scenario, not a measured live failure. Selecting a university explicitly is a negative control: it bypasses the unfiltered catalogue ordering. Missing hints merely shift work to identity search, and conflict rows still have a website hint.

**Held-out test:** matched fixed total budgets, explicit per-stage logging, and two independently selected cohorts: explicit-university requests and open-ended student searches. Report identity established, correct programme discovered, admissible current facts recovered, and useful result latency per stratum. A scheduling arm must have the same total provider, HTTP, token and wall-clock limits as baseline; unused budgets and skipped rows remain visible.

### 5. Track run status and mapping coverage as separate stages so a zero has a cause

**Observed evaluation design limitation**, not a new pipeline crash. `metrics.py:137-145` creates `MISSING_OBSERVATION` and includes every known case in the recall denominator. This is appropriate for a prespecified full run with missing outputs, but an intentionally selected `--case` run (`live.py:450`) is scored against a full dataset unless the caller scopes interpretation; capture config still lists all cohort IDs (`:545`). A synthetic absent observation yields recall **0/1**, with an explicit missing error. That cannot show a search failure occurred.

Mapper identity depends on exact source URL and subject (`identities.py:43-53`); unrecognized identities retain fallback/unmapped keys (`mapping.py:168+`). A raw fact can therefore be present but unmapped, a distinct event from not extracted or not found. `map_claims.py:76-89` already records raw/prediction/unmapped counts and three mapper-module hashes, while live capture records `mapping.py` hash at `live.py:553-555`. Current binding metadata is `2026-10-03.observed-supplemental`, 13 bindings; no binding values or reviewed gold answers were used as targets.

**Affected counts:** all **50/50** have not-attempted live stages here; none can be labelled failed programme/fact discovery. Legacy ten-case overlap is 1/50, not evidence that remaining 49 failed. No actual mapper miss count is measured for these 50.

**Hypothesis:** Prespecified attempted-ID manifest plus explicit not-attempted/budget-exhausted/fetch-failed/identity-rejected/programme-miss/extraction-empty/unmapped/unadjudicated statuses makes experiment decisions accurate. Preserve full-cohort intention-to-test recall for required cases, but also show attempted-only diagnostics and omitted-case counts. **Controls:** an attempted timeout must remain a failure in the prespecified denominator; intentionally unselected cases must never count as success. **Held-out test:** same raw captures and fixed mapper/binding hashes for both arms, then a separately reported equal-review-budget mapping-only ablation. Do not attribute remapping gains to discovery or extraction.

## Independent validation protocol before promotion

This entire 500-university audit is development input. None of it is held out from these hypotheses. Recruit an independent reviewer to select **60 additional universities outside all 500 audit inputs and all prior development/evaluation universities**, with 20 identity hints consistent, 20 absent, and 20 ambiguous or stale only where independently established. Within each stratum balance regions, site languages, and rendering types. Curated routes can be exercised in a separate preregistered stratum if enough genuinely unseen curated entries exist; otherwise report that transfer gap explicitly rather than inventing them. This is a proposed protocol, not completed research.

Freeze cohort, applicant degree/field/intake profiles, query variants, source date window, label ontology and budgets before either run. Independent annotators collect exact programme identity plus requirement/fee/deadline facts with scope/currentness, unknowns and absence labels; developers and capture runners do not see answers. Archive source snapshots/hashes where permitted. The same annotators review baseline and candidate outputs in randomized order without seeing arm labels; disagreement remains unresolved until adjudicated.

Use paired baseline/candidate cold runs in a balanced randomized order on the same date window. Suggested initial budget is 90 seconds, 60 uncached Fetcher reads, 3 search-provider calls and a fixed model-token ceiling **per university**, with a separately declared identical total budget for open-ended multi-university runs. Choose affordable ceilings before running and never raise them selectively after a miss. Report actual HTTP attempts separately from Fetcher calls; robots, retries, blocked requests, cache rules, model/provider version and browser setting must match. If these ceilings leave most cases unattempted, revise the protocol for both arms before a fresh run, preserving the original failed experiment.

Score the funnel with explicit denominators: catalogue target presence/top-1 → independently verified official identity → exact programme discovery → extracted assertions → mapped assertions → independently supported correct-scope current facts. Unknown adjudication stays null. Report each route/region/language stratum, counts and paired uncertainty intervals; no single overall “accuracy”. Promotion requires a preregistered improvement in joint fact recall or useful coverage at equal cost, no increase in independently adjudicated wrong-institution/wrong-programme or wrong-scope claims, and preserved negative controls. Sixty cases are an initial test, not proof for every university.

## Retained evidence and limitations

Inspected retained `backend/evaluation/research/baseline/capture.json` metadata and errors: captured **2026-09-20T04:02:56Z**, pipeline SHA `51f951239b2f3224791476945ae7ba11bd0379ee`, production app tree `5c98f59a1f56eaa22e6cd76546ef3039e2e2eee5`, 90-second/60-call HTTP-only configured budget. Its Warsaw observation has `BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED`; this is one historical attempted failure, not current Warsaw performance. The capture describes a preserved multi-segment assembly with no quality-based discards. README's older budget description counts Fetcher calls including hits, while current `live.py:533` labels network reads with cache hits free; cross-version comparisons must freeze this semantic difference.

No fresh official pages were read. No paid or live search was made. Identity checks use the actual 501-row imported catalogue; route classification is source-backed inference, and metric counterexamples are explicitly synthetic. There is no estimate of real admissions error prevalence, supported/scoped/current recall, programme recall, source freshness or deployment readiness for these 50. Generated outputs are reviewable audit artifacts only.
