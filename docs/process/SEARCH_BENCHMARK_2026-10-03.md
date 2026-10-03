# Main search benchmark — 2026-10-03

Run: https://github.com/wpalish/ashyq-apply/actions/runs/37110018701
Source: `b672349e5bba2bd3cbfe8d8f155db74da11a492c`. Workflow succeeded; search acceptance fails.

Explicit provider: `exa`; decision: `explicit input and UNIMATCH_EXA_API_KEY`.
Budget:120s/case,60 noncached Fetcher.get responses/case; ten cases, HTTP-only.
56 instrumented provider invocations; no search failure/quota errors in child logs.
402 actual HTTP requests include robots and redirects; they are not402 budgeted pages.
Cost is unmeasured. Three cases reached the child wall-clock cutoff (~115s, within120s parent budget).

## Requested comparison

The old column is owner-supplied history for0f5b99d on2026-09-28; that artifact was not reverified.
Same requested120s/60read budgets, but provider, source and website conditions differ.
Do not infer that the workflow selection change caused the difference.

| Metric | Owner-supplied old | Main fresh capture |
|---|---:|---:|
| Claim recall | 13/62 | 6/62 |
| Claim precision | 20/21 | 11/12 |
| Programme page recall | 7/10 | 4/10 |
| Programme page precision | 7/21 | 4/16 |
| Award discovery | 0/3 | 0/3 |

Only12 of52 predictions have adjudicable known value/scope labels;11/12 is not a claim that every output is correct.
The single scored wrong-scope claim is retained in the original capture.

## Oracle: direct source access, separate from discovery

| Verdict | Source probes |
|---|---:|
| recovered | 19 |
| value_missing | 16 |
| fetch_failed | 35 |
| not_measured | 2 |
| text_missing | 2 |

The oracle has74 rows, including null/unknown labels and source alternatives; this denominator is not the62 known-fact recall denominator.
Two value_missing rows have null certified values (Groningen tuition, Vienna deadline); do not treat them as missing known facts.
35 fetch_failed rows include Aalto/HKU/KAIST unreadable robots and Toronto403 / Vienna and NTU404. No guard bypass.
Of16 value_missing rows,10 are NTU award/documents; five document keys are already addressed in PR41 ER11.
Groningen translation is already addressed in ER12. Validate those existing changes before adding a duplicate fix.

## Per-case measurements

| Case | Correct known facts | Programme hit | Search calls | HTTP requests | Seconds | Error |
|---|---:|---|---:|---:|---:|---|
| groningen | 0/11 | False | 0 | 77 | 115.0 | BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED |
| delft | 1/1 | True | 6 | 41 | 73.9 | — |
| aalto | 0/2 | False | 6 | 4 | 28.6 | — |
| vienna | 1/4 | True | 7 | 65 | 89.9 | — |
| warsaw | 0/2 | False | 6 | 73 | 115.0 | BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED |
| ubc | 3/3 | False | 6 | 54 | 115.0 | BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED |
| toronto | 0/4 | False | 6 | 30 | 34.1 | — |
| hku | 0/4 | True | 6 | 18 | 65.1 | — |
| ntu | 1/21 | True | 7 | 28 | 60.3 | — |
| kaist | 0/10 | False | 6 | 12 | 78.0 | — |

## Evidence and next step

Original JSON and case logs: `backend/evaluation/research/expert/data/runs.2026-10-03/main.37110018701`; SHA256 manifest alongside them.
No older300s capture rescored or relabelled. PR41 stays draft; no production deployment.
Next: owner completes public login for brief-profile acceptance; meanwhile verify existing PR41 recovery at the same120s/60read budget with explicit Exa.

## Same-budget PR41 capture (before ER15)

Run: https://github.com/wpalish/ashyq-apply/actions/runs/37111364718
Source: `1d8a4ea1e7d9c7ea16c3d74e1e598633db2d84d9`; explicitexa120s/60reads.
Claim recall13/62; precision28/38; programme recall3/10, precision3/13; awards1/3.
57 instrumented provider calls; no search errors in retained child logs.
Oracle:20 recovered,29 value_missing,21 fetch_failed,2 not_measured,2 text_missing.

This is NOT an isolated before/after effect estimate. Unlike main, this capture uses
`identity_bindings.2026-10-03.supplemental.json` (hash af48e733a7d4d30786c58667cd724402f233ae129003faa5902e3fc5de0572e5),
new mapping and admission-obligation code. The underlying signed gold remains unchanged.
Website accessibility also changed (KAIST source reads succeeded in this run).
Do not label all seven additional recall hits as newly extracted evidence.
No old capture was rescored. Both raw sets/configurations/checksums are retained independently.

Groningen, Warsaw and UBC again hit the child deadline. Groningen issued zero search calls
before its budget expired. Documents are collected after a programme decision; neither
this pre-decision capture nor its award-only oracle path exercises ER11 scholarship documents.
Five NTU document value_missing rows therefore cannot diagnose a broken document reader.
Overall acceptance still fails; PR41 stays draft.

## ER15 confirmation on fresh source

[Run37112534809](https://github.com/wpalish/ashyq-apply/actions/runs/37112534809),
sourceadf2f9f, explicitexa120s/60reads. Both Groningen secondary diploma completion
keys are now recovered by the live oracle. Blind search is still0/11 for Groningen,
115s child cutoff,77HTTP,0search calls. No search-quota failure.
This is a selected-case capture; the workflow's automatic0/62 score includes nine
unrun cases, so it is not a new ten-case result. The last full PR41 result remains13/62.
Only38 of105 predictions in that full PR41 run were adjudicable for precision.
Task3 still needs normal public sign-in; no profile run or19-institution coverage
measurement has been claimed, and no existing user/account data was deleted.
