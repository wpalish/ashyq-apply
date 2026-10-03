# Group 08 — trace observability and evidence provenance

Audit date: 2026-10-04. Input source baseline: `144881b`. This is non-blind offline engineering diagnosis. No real network, provider, admissions verification, production state, signed gold, or source files changed. Only the three assigned group-08 outputs were written. All discovery responses below are explicitly synthetic unless described as retained historical captures.

## Reproduce and denominator

From repository root:

```sh
backend/.venv/bin/python docs/process/top500-expert-audit-2026-10-04/group-08.probe.py
```

The probe executes the actual `import_catalogue`, `retrieve`, `CatalogueDiscoveryAdapter.discover`, route selection in `_enrich`, and identity probing with fake transport. Each execution uses a fresh in-memory SQLite database containing **500 seed records + the complete curated registry = 501 university identities**, with 500 immutable seed observations. `group-08.rows.json` contains all **50/50** assigned individual records, 266 name/alias query tests, route calls, allocation, risks, and `live_checked:false` for each. Its SHA-256 fingerprints identify the seed and historical inputs.

| Actual offline measurement | Result |
|---|---:|
| Full seed name query includes target | 50/50 |
| Canonical, normalized, reordered name queries include target | 150/150 |
| Alias queries include target | 66/66 |
| Exact seed query has extra identities | 4/50 |
| Canonical query has extra identities | 5/50 |
| Curated discovery route | 3/50 |
| Generic identity route | 47/50 |
| Imported domain statuses | 3 curated; 36 seed; 11 unknown |
| Candidate allocation at server defaults 40/20 | 7/50 |
| Enrichment allocation at server defaults 40/20 | 3/50 |
| Live source verification performed by this audit | 0/50 |

Curated controls are Delft University of Technology, Sabanci University, and Vilnius University. The actual generic route mock returns an unidentified site for all 47 generic records; each retains its candidate and produces an explicit identity limitation. This tests routing behavior, **not 47 actual identity failures**. Missing domain metadata on 11 records is likewise not a failed crawl.

The default allocation uses the actual discovery loop over the full database, with enrichment replaced by an offline recorder. Of the seven assigned candidates, four lie after the enrichment cap and get an empty trace; 43 assigned identities are outside the candidate cap and get no trace. Defaults originate at `backend/app/config.py:57` and runner wiring at `backend/app/pipeline/runner.py:151` and `:187`. These are one unfiltered synthetic profile's exposure counts, not universal exposure across all student preferences.

## Ranked hypotheses and experiments

### 1. Explicit per-stage attempt status will prevent unattempted universities being diagnosed as failed research

**Observed defect in observability:** `backend/app/catalogue/discovery.py:53-78` constructs the same fresh trace whether enrichment is run or skipped after `live_limit`. `DiscoveryTrace.as_dict` (`backend/app/adapters/discovery/live_discovery.py:815-838`) has no budget allocation or identity attempt status. Our paired scenario selects each university alone, once with live_limit=0 and once with live_limit=1 and a no-result fake enrichment. Serialized traces are identical in **50/50** pairs, although the recorded enrichment calls are respectively 0 and 1. The no-result enrichment is a synthetic counterexample; it does not claim that every real enrichment produces an empty trace.

**Student effect:** a support or retry system cannot reliably say “not researched within this run's budget” versus “research attempted and returned no evidence.” Empty facts must not become a negative admissions conclusion.

**Equal-budget result:** 50 paired states, zero external requests/provider calls in both arms. Current trace distinguishes 0/50 pairs; an instrumentation-only attempt sidecar distinguishes 50/50 without changing candidate selection or facts. This is a measured diagnostic signal improvement, not measured admissions recall improvement.

**Negative controls:** actual `_enrich` when site identity is not established records a search limitation (`catalogue/discovery.py:91-95`); timeout handling records errors and limitations (`:69-75`). Walker telemetry already explicitly distinguishes never run via zero catalog counts (`live_discovery.py:747-769`). Preserve those useful distinctions.

**Held-out promotion gate:** on newly chosen institutions outside these 500, replay identical frozen transport and fixed request/time caps through baseline versus explicit status instrumentation. Assert identical requests, candidates, claims and ranking, but complete status assignment across excluded, candidate-cap omitted, enrichment-cap skipped, attempted-empty, failed, timed-out and successful stages. Include curated and generic paths and interruption before the first request.

### 2. Record each identity probe's typed outcome before moving to fallback search

**Observed defect in observability:** `_probe_site` returns `None` for bad fetch, cross-site redirect or failed name recognition at `backend/app/catalogue/discovery.py:135-167` without recording which occurred. `_identify_site` only records configured-provider exceptions (`:123-126`); ordinary empty results and unsuccessful hint probes are silent. A `page_recorder` is supported by the parent adapter (`backend/app/adapters/discovery/live_discovery.py:1020-1037`) but `_probe_site` never calls it.

**Synthetic actual-code measurement:** for assigned Aarhus University, three separate fake conditions—HTTP error, identity mismatch, and off-site redirect—each consume **2 fake fetch calls + 1 fake search call**, return no identity, produce the same completely blank identity trace, and call the page recorder **0 times**. Thus equal-cost conditions with different repair actions have identical trace output. A matched-title control succeeds in 1 fake fetch/0 fake searches and also leaves the trace blank, while persisting a site-identity observation. See `synthetic_identity_cases` and `synthetic_identity_proofs` in rows JSON.

**Exposure, not failure count:** 47/50 assigned universities use the generic identity route; 36 of those have seed domains and 11 require missing-hint discovery. The three failing conditions were executed on **one** assigned university, not on all 47. Their general reach is inferred from the shared implementation.

**Student effect:** retries should distinguish inaccessible official pages, stale hints, identity mismatch and identity not yet found. Without the distinction, a timeout can trigger the wrong corrective path or spend another capped run on the same inaccessible hint.

**Negative controls:** cross-site redirects and unrelated titles are correctly rejected; retain those safety boundaries. The importer records seed status as unverified, and a successful identity probe creates only `site_identity_checked`, not verified admissions facts. Provider-specific exceptions already have sanitized diagnostic handling.

**Held-out equal-budget gate:** replay a balanced set of bad URLs, robots refusal, HTTP failure, redirects, title mismatch, acronym success, full-name success, provider outage and provider-empty conditions on unseen institutions. Fix identical fetch/provider and wall-clock budgets. Measure typed outcome completeness against fake transport ground truth, unchanged acceptance/rejection, retry usefulness and zero fabricated admissions claims. Add instrumentation; do not relax identity checks to improve the diagnostic score.

### 3. Link identity proof, discovery trace and run/candidate provenance in the persisted result

**Observed design limitation:** a successful generic identity check writes a `UniversityObservation` with source URL, access timestamp, excerpt, name and domain (`backend/app/catalogue/discovery.py:169-192`). This is useful evidence. However the returned entry has only name/country/city/homepage (`:193`), so its observation ID/content fingerprint is not handed into the new discovery trace. `_enrich` replaces the identity trace with `_discover_one`'s trace and copies only `search_failures` (`:96-99`). The runner's discovery stage reads failures/limitations and records aggregate candidate count (`backend/app/pipeline/runner.py:462-491`), not the full adapter trace.

**Measurements and scope:** the single successful synthetic Aarhus probe persists one correct site-identity proof, with no run ID, candidate ID, observation link in the trace, or page-recorder event. A separate actual `_enrich` handoff test injects three explicitly synthetic identity diagnostics: one error, one limitation, one provider failure. Only the provider failure survives the returned trace. The inserted error/limitation are future-contract counterexamples, not claims that current `_identify_site` emits them today. Potential route exposure is 47/50; direct success/handoff experiment count is 1 institution.

**Student effect:** “official identity checked” and “admission requirement supported by this page in this run” are separate conclusions. A reproducible explanation must follow the exact observation used, particularly after the current domain is updated by a later run. This hypothesis improves traceability; no observed wrong admissions claim is alleged.

**Historical counterexamples and boundaries:** retained traces already demonstrate useful provenance. The 2026-09-27 Aalto expert trace stores packet/baseline hashes, action timestamps, policy mode, raw-log SHA and cumulative budgets. The 2026-10-02 `identity-replay.capture.json` explicitly says `mode=replay`, `pipeline_sha=mixed-see-config`, and carries per-case source metadata; it cannot be treated as one current live run. Its Delft observation (one of our assigned 50) has 6 predictions and 14 page outcomes: 2 classifier-rejected, 8 fetched-ok and 4 no-pattern-match. These are historical stored results, not newly verified admissions truth.

The 2026-10-03 `er15.37112534809/capture.json` has a **single** Groningen observation, 0 predictions, no page outcomes, 77 HTTP fetches, 0 search calls, and `BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED`. This is neither 500 failed crawls nor proof that no fetch was attempted. Groningen is outside this group's 50 and is included solely to inspect a real retained capture shape. The capture schema defaults page outcomes to an empty list for compatibility (`backend/evaluation/research/schema.py:151-161`); blank outcomes cannot alone establish “never attempted.” Capture collection attempts a final outcome snapshot even on interruption (`backend/evaluation/research/live.py:243-264`).

**Equal-budget experiment needed before promotion:** baseline versus observation-ID/run-ID linkage on the same frozen bytes, timestamps, requests and selected candidates. Measure complete proof-to-run joins, content reproducibility, trace survival at every exit, resume stability and byte-equivalent claim values. Test interrupted writes, repeated cached pages and site-identity updates between runs. Any extra network call or admissions status upgrade is a regression. Our synthetic experiment establishes the gap; it does not measure downstream benefit yet.

## Secondary retrieval findings

Four full seed-name queries match extra identities: Sydney returns New South Wales ahead of the target; King Saud returns King Abdulaziz ahead; Abu Dhabi also returns Khalifa; Shenzhen also returns Southern University of Science and Technology. This comes from all-token substring search across name/country/city/aliases with curated-first lexical order (`backend/app/catalogue/retrieval.py:88-110`). Targets remain present in all four cases. A retrieval trace should retain query, matched identity and selection order so later missing-research diagnoses do not hide an upstream ambiguous selection. Exact-priority promotion needs a separate held-out fixed-budget ranking experiment; this audit does not change ranking.

## Completion and limitations

50 individual records covered; 266 actual query tests; 50 per-university actual route tests with mocked external seams; 100 paired discovery-loop status scenarios; four synthetic identity conditions; one trace handoff; three retained provenance artifacts inspected. Source facts were not refreshed, no admissions claims validated, and this diagnosed dataset cannot serve as held-out validation. All synthetic identity evidence exists only in a discarded in-memory database and the clearly labelled audit JSON.
