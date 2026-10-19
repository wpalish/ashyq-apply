# Search volume ledger, 2026-10-19: what one run, one applicant and one KB refresh cost in provider queries

Free-search map, ticket 02 ([map](wayfinder/free-search/map.md),
[ticket](wayfinder/free-search/issues/02-query-volume-and-free-tier-arithmetic.md)). Offline only: no run was
started and no provider was called. Sources: `STAGE_SUMMARY_DEV_2026-10-19.md` (the base3 paired runs of the four
development sets, pipeline `1093faaa`, aggregates only) and
[the provider survey](wayfinder/free-search/assets/provider-survey-2026-10-19.md). No heldout or dev5 number is used.

**The short answer.** A four-set paired run sends about **820** provider queries, not the 600–700 the map estimated.
The map's figure counted discovery queries only (660). Topic, scholarship and identity queries add about 160. One
applicant's research of ten universities costs **≤ 60** queries (about 47 at the measured mean). A KB refresh costs
**0**. The free allowances together, about 4 500 keyed queries a month, buy **≈ 5 four-set paired runs or ≈ 75–95
applicant researches a month**. The map's "≈ 7 paired runs" also rested on the 600–700 figure. Since
`--max-search-queries` landed, no provider run can start without naming its cap.

## 1. Per case and per column (base3; columns `off#1 / off#2 / on#1 / on#2`)

| set | cases | `discovery_queries` per column | `search_calls_total` per column | queries per case: mean / max | non-discovery queries per column |
|---|---:|---|---|---|---:|
| cohort | 10 | 36 / 39 / 33 / 36 | 39 / 39 / 40 / 39 | 3.9 / 6 | ≈ 3 |
| dev2 | 10 | 36 / 36 / 36 / 36 | 52 / 51 / 51 / 51 | 5.1 / 6 | ≈ 15 |
| dev3 | 15 | 54 / 63 / 57 / 60 | 72 / 71 / 72 / 71 | 4.8 / 6 | ≈ 13 |
| dev4 | 9 | 36 / 36 / 33 / 33 | 43 / 43 / 43 / 43 | 4.8 / 5 | ≈ 9 |

The non-discovery queries are `search_calls_total − discovery_queries`: topic search, scholarship and award queries
(SQ-1 among them) and identity recovery. The stage summary does not split them further.

**The six discovery families: how often each was sent.** The table gives the mean per column. The share is that mean
divided by the number of cases. `admissions` is a seventh label the trace records, sent at most once per set.

| family | cohort | dev2 | dev3 | dev4 |
|---|---|---|---|---|
| field_and_degree | 9.0 (90 %) | 10.0 (100 %) | 15.0 (100 %) | 9.0 (100 %) |
| natural_language | 9.0 (90 %) | 10.0 (100 %) | 15.0 (100 %) | 9.0 (100 %) |
| local_language | 7.0 (70 %) | 7.0 (70 %) | 10.0 (67 %) | 9.0 (100 %) |
| programmes | 4.25 (43 %) | 5.0 (50 %) | 9.0 (60 %) | 2.5 (28 %) |
| courses | 3.0 (30 %) | 2.0 (20 %) | 4.5 (30 %) | 2.5 (28 %) |
| undergraduate | 3.0 (30 %) | 2.0 (20 %) | 4.5 (30 %) | 2.5 (28 %) |
| admissions | 0.75 | 0 | 0.5 | 0 |

The first two families go out for nearly every case. The local-language family goes out wherever the country has a
local language. The last three are sent only while the six-query budget still has room.

## 2. Per run

| run shape | captures | queries (measured) | ceiling the cap plans for (6 per case per capture) |
|---|---:|---:|---:|
| one set, paired (4 columns), cohort | 40 | 157 | 240 (+1 Serper pre-flight) |
| one set, paired, dev2 | 40 | 205 | 240 (+1) |
| one set, paired, dev3 | 60 | 286 | 360 (+1) |
| one set, paired, dev4 | 36 | 172 | 216 (+1) |
| **all four sets, paired** | 176 | **820** (4.66 per case per column) | 1 056 (+4) |
| benchmark / expert_baseline, cohort, one column | 10 | ≈ 39 | 60 |

**The old loop, reconciled.** About 50 000 credits over about 170 runs is about 294 queries per run. That matches one
dev3 paired run (286), or a cohort run plus a dev4 run (157 + 172 = 329). It does not match a four-set run (820). The
loop mostly ran one or two sets per run, and the credit total fits that. This reconciliation is arithmetic only. The
run-by-run counts were not reread.

## 3. Per applicant research in the product

| path | queries per university | per research of ten | per research of twenty |
|---|---|---:|---:|
| live web pipeline, brief's ceiling | ≤ 6 | ≤ 60 | ≤ 120 |
| live web pipeline, measured mean (dev sets: 3.9–5.1) | ≈ 4.7 | ≈ 47 | ≈ 94 |
| **knowledge base** (the product's default since 2026-10-19; offline fetcher, no discovery) | 0 | 0 | 0 |

Ten is the map's working shortlist (`MAX_TARGET_UNIVERSITIES = 10` in `app/domain/social.py`). Twenty is shown for a
demo-sized list. A university answered from the KB costs no query, so live search is spent only on universities
missing from the KB.

## 4. Per KB refresh

**0 queries.** Ticket 07 re-reads the KB's 312 evidence URLs (154 hosts) through `Fetcher` and does not search. Its
cost is 312 HTTP reads, bounded by robots and crawl delay. A free allowance is not touched.

## 5. Allowances: what each one buys a month

| allowance (survey 2026-10-19) | queries a month | four-set paired runs (820) | one-set paired runs (157–286) | applicant researches (60 ceiling / 47 mean) | KB refreshes |
|---|---:|---:|---:|---:|---|
| Exa, $10 credit, instant search at $4 per 1 000 | ≤ 2 500 (fewer: the adapter asks for `highlights`, which Exa bills as contents. Read the real cost per query off the dashboard after 03's replay) | ≤ 3.0 | 8.7–15.9 | ≤ 41 / 53 | unlimited (0 needed) |
| Brave, $5 credit at $5 per 1 000 (card and attribution reported by third parties) | ≈ 1 000 | 1.2 | 3.5–6.4 | 16 / 21 | unlimited |
| Tavily, 1 000 credits at 1 per basic search | 1 000 | 1.2 | 3.5–6.4 | 16 / 21 | unlimited |
| Exa MCP, keyless, ≈ 50 a day per IP | ≈ 1 500, but **≤ 50 in any day** | 0 within a day | 0 within a day (one cohort run is 157) | ≈ 1 a day | unlimited |
| **keyed total (Exa + Brave + Tavily)** | **≈ 4 500** | **≈ 5.5** | 16–29 | **≈ 75 / 96** | unlimited |

The map's "≈ 5 000 queries ≈ 7 paired runs" therefore becomes **≈ 4 500 keyed queries ≈ 5 four-set paired runs**.
The keyless MCP cannot carry a paired run, because its daily limit is below one cohort run. The conclusion does not
change: the old benchmark cadence cannot be free, and a modest product can.

## 6. Quota-exhaustion codes: confirmed, not changed

Every adapter maps any non-200 answer to `SearchUnavailable` with the status and never retries it. The product shows
`search_failure_diagnostic` as "Search service unavailable (<provider>; HTTP n)" and does not guess.

| provider | code seen when spent | mapped to `SearchUnavailable` | test |
|---|---|---|---|
| Serper | HTTP 400 "Not enough credits" (2026-10-19) | yes, with a capped, key-masked body excerpt | `test_serper_provider.py::test_any_non_200_is_unavailable_without_retry[400]`; `test_search_outage_visibility.py` |
| Exa | HTTP 402 (2025-09-24, run 48) | yes | `test_exa_provider.py::…test_every_error_status_becomes_search_unavailable[402]` |
| Tavily | HTTP 432 (2025-09-25, runs 68–69) | yes (any non-200) | `test_tavily_provider.py::test_any_non_200_is_unavailable_without_retry[432]`, with 432 named in the test since this ticket |
| Brave | HTTP 429 / 402 | yes | `test_brave_provider.py::test_any_non_200_is_unavailable_without_retry[402, 429]` |
| Exa MCP | rate-limit flag in the result `_meta`; HTTP 429 | yes, `SearchFailureReason.RATE_LIMITED`; SR-1 retries once | `test_exa_mcp.py::test_the_rate_limit_is_named_not_malformed`, `…test_http_failure_is_safe_and_never_retried_or_redirected[429]` |

## 7. The guard: a free allowance or a paid key cannot be spent by accident

- **`evaluation.research.live --max-search-queries N`** is the run's hard cap. It is required for every provider
  except `none`, `fake` and `recorded`, because those three send no query anywhere. A provider the harness has never
  seen is capped too. Without the flag the run exits with status 2 before git, the capture directory or any child.
- **The run refuses to start** when its plan (6 per case) exceeds what the cap leaves.
- **Every query reserves one unit** of a ledger file (`--search-ledger`, by default `search_ledger.json` in the
  capture directory) before it is sent. The file is updated under an OS file lock, so the four captures per
  university, five universities at a time, of a paired run share one count. The (N+1)th query is refused locally with
  `SearchUnavailable` and no request is sent. The case records `telemetry.search_cap_refusals`, a strict case's budget
  records `stop_reason = search_budget_exhausted`, and the parent attempts no further case.
  `capture.json.config.search_query_cap` holds `max_search_queries`, `used`, `refused`, `stop_reason` and
  `remaining_case_ids`. A later capture cannot raise the cap the ledger was opened with.
- **The scorecard** marks a repetition with any cap refusal unhealthy (`search_health.cap_refused`, the failed
  `search_provider_healthy` target and a "not a valid measurement" banner). The cases after the cap ran without
  search.
- **The workflow** (`benchmark-capture.yml`) has a `max_search_queries` input. It is a separate input because
  `extra_args` reaches only the paired run's "on" arm. The "Search query cap" step runs after the search layer is
  chosen, in the `benchmark`, `expert_baseline` and `expert_paired` modes. It fails the job with a clear message when
  a provider other than `none` or `recorded` has no cap, or when the plan exceeds the cap: 6 × cases × captures (4
  for `expert_paired`, or 1 for its W4 record run `columns=1`, see `RECORD_RUN_2026-10-19.md`), plus 1 for the Serper pre-flight. The step writes the cap and the plan to `out/config.txt`
  and passes `--max-search-queries N --search-ledger out/search_ledger.json` to every capture and to the pre-flight.
  The pre-flight's one query is charged to the same ledger. Keys are never printed: the step reads only the
  provider's name.
- **Not covered:** `expert_actions` runs plans through `expert.controller`, which keeps its own per-plan
  `max_search_queries`. `query_probe` keeps its own cap of 300 queries.

## 8. The trap

A free allowance resets on the 1st of the month. A run started on the 31st can straddle the reset. Its first half
spends the old month's remainder and its second half spends the new month's credit, so the dashboard's monthly
figure no longer matches the run. Set the cap from what is left today and do not count on the reset.
