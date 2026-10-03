# Expert07: budgets, interruption, provider failure, fair scheduling

Audit date: 2026-10-04. Packet/source baseline: `144881b`. All50 assigned seed universities were imported and exercised inside the actual full501 SQLite catalogue (500 seed observations plus curated identities), using the production importer, retrieval, catalogue adapter and search integration. Only these three group07 artifacts were written. No live provider/site calls, quota probes, gold edits, admissions validation or production changes were made.

Reproduce from repository root:

```sh
backend/.venv/bin/python docs/process/top500-expert-audit-2026-10-04/group-07.probe.py
```

The command writes `group-07.rows.json`, prints a machine-readable summary and asserts the principal reproductions. Every row includes seed ID, name, canonical identity, aliases, actual query results, hints, routing, budget positions, synthetic outcomes and `live_checked=false`. Source is unchanged; fake fetchers/providers are injected only inside the probe process. Timeout injection is2ms, while the wrapper's actual timeout argument300 seconds is recorded.

## Coverage and observations

- 50/50 seed-exact and50/50 canonical queries contain their intended university. All318 query tests, including imported aliases, uppercase/whitespace, punctuation and accent variants, contain their targets. This is recall within local identities, not programme discovery success.
- Six universities have ambiguous exact queries: Khalifa University, United Arab Emirates University, University of Canterbury, University of Macau, University of Jordan and IE University. IE's exact query returns24 rows; UAE's returns6. The importer/retriever accepts tokens in name/country/city/aliases, explaining the ambiguity. Macquarie's imported `Sydney, Australia` alias returns5; ITB returns2. No target is falsely reported absent.
- 2/50 use curated discovery entries: Politecnico di Milano and University of Groningen. 48/50 require generic site identification. 11/50 have no imported domain; missing hints are limitations, not evidence of wrong domains or failed live identity.
- The unfiltered full501 default ordering places6/50 in the first40 candidate positions and2/50 in the first20 live positions. The six are Politecnico di Milano, University of Groningen, Al-Farabi Kazakh National University, Beijing Normal University, Ajman University and Aston University. Both live recipients are the curated two. These are one explicit no-preference scenario; geography preferences change ordering.
- With all50 group IDs explicitly selected, limit50/live20,50/50 local candidates survive,20 receive enrichment and30 do not. Reversing the supplied IDs changes no enrichment recipients. All30 skipped traces have no search-limitations explanation.
- Synthetic timeout after mutation of the actual inner discovery trace:50/50 retain a local candidate and timeout warning, but50/50 lose the inner sitemap progress and diagnostic marker. No programme facts are invented.
- Synthetic repeated HTTP429 in actual single-field search integration:6 calls for each of50 institutions,300 total; every preexisting programme URL survives and vendor body text is redacted. Eleven rows use a clearly marked `example.edu` placeholder only to exercise the downstream algorithm because their domain is unknown. Actual generic identity-gate tests separately use original seed hints:48/48 retain candidates without programmes after unavailable hint fetches/provider.

## Ranked general hypotheses and promotion experiments

### 1. Preserve the in-flight discovery trace across per-university cancellation

**Observed synthetic defect, conditional exposure50/50.** `catalogue/discovery.py:56-78` allocates the outer trace and retains it on timeout. `_enrich` only receives the inner trace after `_discover_one` returns (`catalogue/discovery.py:96-99`). `_discover_one` allocates another trace at `adapters/discovery/live_discovery.py:1063-1082`; sitemap collection mutates it at1122-1125. Cancellation interrupts the return, leaving already collected discovery evidence absent from the returned trace. The reproduction executes these actual paths, injects a marker inside fake sitemap collection, and cancels through real `asyncio.wait_for` shortened to2ms.

Student effect: a partial investigation is reported with only a generic timeout; completed inner discovery work cannot inform continuation or explain which routes were already attempted. This proves loss from the returned trace, **not** deletion of all source-page records: `page_recorder` and session observation paths may retain other evidence and were not tested for durability here.

Negative controls: local candidates and timeout warnings survive50/50, facts are not invented50/50, and a completed inner discovery result retains its trace marker. Proposed change: share one trace object or attach partial state before awaiting each bounded stage; make resumable evidence storage explicit.

Held-out experiment: after implementation, use unseen institutions and recorded pages with matched cancellation points after sitemap, walker and provider stages; allocate the same300 seconds, page/read caps and provider-query caps to both variants. Compare retained already-completed evidence, duplicate reads on resume, candidate validity and time to first usable result. Include successful completion, cancellation before any work, cancellation during identity verification and cross-domain rejection controls. Do not promote based on this500 audit set.

### 2. Add run-scoped suppression for terminal provider availability failures

**Observed synthetic behavior; benefit remains hypothesis.** Search retrieval loops over every query and continues after `SearchUnavailable` (`adapters/search/retrieval.py:378-404`). Identity fallback independently calls the provider (`catalogue/discovery.py:109-127`); multi-field integration continues to remaining fields (`live_discovery.py:1607-1623`). There is no run-scoped terminal-outage suppression in these inspected paths. Six HTTP429 responses produce six paid-provider attempts per institution in50/50 downstream probes. For48 generic identities, unavailable hint fetches produce one fallback request each; that route then stops without downstream programme search. Do not add those48 identity calls to the300 downstream calls as one real run: these are separate test scenarios.

Student effect: an unavailable provider can consume most of the allotted search attempts and time repeatedly, even while official-page discovery already has useful results. HTTP429 alone does not establish exhausted credit; it can be temporary rate limiting. A real quota diagnosis requires provider metadata, so no claim of current exhaustion is made.

Negative controls: prior programme URLs survive50/50, diagnostics retain HTTP status and redact arbitrary provider body50/50; successful empty responses run six queries and report zero failed queries. Proposed policy: distinguish known terminal failure from temporary failure; suppress only appropriately classified run-scoped outages while preserving sitemap/walker work and explicit coverage diagnostics.

Held-out experiment: replay persistent quota denial, one transient429 then recovery,403/401, transport failure and successful empty results on unseen institutions. Hold query/read/time ceilings equal; report useful results and calls saved together. Require no regression in transient-recovery yield, privacy, cross-site filtering or prior-evidence retention. This probe establishes the repeated-failure mechanism, not optimal circuit-breaker thresholds.

### 3. Make the end-to-end discovery deadline and checkpoints explicit

**Source-observed design limitation, scope50/50; runtime incidence unknown.** The adapter processes rows serially with an independent300-second timeout each (`catalogue/discovery.py:56-79`). Runner defaults are40 candidates and20 verifications (`config.py:57-58`); the runner passes verify_limit as live_limit (`pipeline/runner.py:149-152,183-189`). Discovery nominally allocates20×300=6000 seconds, or100 minutes; a caller allowing50 live rows allocates15000 seconds, or250 minutes. These sums are theoretical timeout allotments, **not observed runtime and not strict upper bounds**: cancellation cleanup/synchronous work can overrun, other stages consume additional time, and successful rows finish early.

`pipeline/runner.py:453-493` saves before discovery and after the full adapter returns. It checks cancellation before discovery; no per-university runner checkpoint is exposed by the inspected adapter. Students can therefore wait through long serial discovery without candidate-level stage progress. A worker restart may repeat uncheckpointed discovery; that is a source-based risk, not a reproduced crash result.

Negative control: `jobs/worker.py:134,161-176` runs a separate heartbeat task. Therefore lack of discovery progress commits is **not evidence that a120-second worker lease necessarily expires**. Existing local candidate retention on individual timeout also works.

Held-out experiment: use unseen institutions with identical controlled latency/failure distributions and enforce the same total wall-clock ceiling, read cap and provider-query cap. Compare the current serial design with a global deadline, small bounded concurrency and per-institution checkpoints. Measure time to first candidate, completed useful evidence, cancellation acknowledgement, restart duplicate work, and host-rate compliance. Do not compare a higher-resource concurrent variant to a lower-resource baseline.

### 4. Expose and improve deterministic enrichment allocation

**Observed allocation, fairness improvement hypothesis.** Retrieval sorts preferred geography, curated route, normalized name and ID (`catalogue/retrieval.py:102-111`). Discovery takes the first limit rows then enriches only the first live_limit (`catalogue/discovery.py:44-49,65`). Selected IDs become a set (`retrieval.py:90-94`), so caller ordering carries no priority. In the explicit50-selected/live20 scenario30/50 receive no enrichment and no trace limitation. In the default full501/no-preferences scenario48/50 receive no live attempt, including all48 generic rows;44/50 are outside candidate_limit40 altogether. This does not prove unfair student outcomes across different preferences; it establishes deterministic exposure in the specified scenarios.

Student effect: repeat searches under unchanged preferences enrich the same early institutions while users cannot distinguish “not attempted because of budget” from “attempted and found nothing” using these traces. Curated-route preference may increase early yield; simply randomizing could lower quality.

Negative controls: all50 explicitly selected candidates remain present, no fabricated programme facts appear, and reversing selection order reproduces the same allocation. Proposed change: emit per-row skipped/deferred reasons and evaluate resumable rotation or fair allocation across identity readiness, geography and requested fields while preserving useful curated routes.

Held-out experiment: choose an unseen stratified pool, randomize evaluation order once, and compare fixed budgets20 institutions/identical calls/read/time to a rotation strategy over repeated runs. Measure cumulative institution and subject coverage, useful verified programmes, redundant reads, worst-case delay and geographic distribution. Include a small request fully inside budget and a curated-only pool where current prioritization should remain competitive.

## Historical context and limits

The retained `backend/evaluation/research/expert/data/runs.2026-10-02/baseline.capture.json` is dated2026-10-02, labelled live, with mixed pipeline SHAs and harness settings300 seconds/case and60 network reads. Its Groningen observation contains five page outcomes saying the host had already stopped responding and was not waited on again. Groningen is in this packet. This is a historical availability observation and an existing per-host avoidance control; it does not measure today's provider state, current end-to-end latency or the synthetic trace-loss incidence. The aggregate captures and harness budgets must not be treated as current production limits.

All50 institutions are diagnosis inputs, not a held-out set. Live checked0/50. No official-source admissions facts were certified. The programme URL used in the preservation control is expressly synthetic. Query ambiguity is reported alongside recall and never interpreted as automatic misidentification. The four proposed changes require equal-budget unseen validation before promotion.
