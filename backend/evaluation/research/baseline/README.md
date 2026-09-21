# Provisional bounded baseline — 2026-09-20

**Not accepted ground truth: 0/10 human verified.** Twelve known draft labels out
of 160; six exact programme URLs adjudicable, four unknown. Site-type tags are
preparation hypotheses, not a validated stratified sample.

Production `backend/app` tree: `5c98f59a1f56eaa22e6cd76546ef3039e2e2eee5`, identical
to `main@b267b337`. PR #13 was open and was not merged. All ten institutions used
a fresh synthetic canary, database/cache, HTTP-only Fetcher, at most 60 Fetcher
calls and 90 seconds per case. These are budgeted failures as well as successes;
this is not an unrestricted production-quality measurement.

| Metric | Result | Interpretation |
|---|---|---|
| Exact programme-page recall | 1/6 | Only NTU matched an accepted draft URL |
| Exact programme-page precision | 1/7 | Returned distinct URLs on adjudicable cases |
| Candidate recall @5 / @10 / @20 | 1/6 each | Confirmation queue before catalogue walking |
| Claim precision / recall | 0/5 / 0/12 | Conservative literal value/scope/evidence matching |
| Claim adjudication | 5/13 | Remaining predictions lack matched labels/award identity |
| Scope-match failures | 5/5 | Includes missing or differently named scope; not five human-confirmed errors |
| Critical field coverage | 0/150 | Answered fields counted separately from correctness |
| Support adjudication | 0/13 | Unsupported-claim rate is unmeasured, not zero |
| Primary-source flag | 13/13 | Pipeline provenance flag, not proof of claim correctness |
| Scholarship applicability/coverage, freshness, conflict, human-review rate | null | Missing independent labels/adjudication |
| HTTP attempts / uncached PDFs | 520 / 2 | All ten cases measured; includes robots/retries |
| Browser / search / model / Jev calls or input tokens | 0 | Disabled or not used by this baseline |
| Latency p50 / p95 | 72.281 / 90.031 seconds | Includes time to failure; not time to useful result |
| Total measured case latency | 721.564 seconds | Excludes gaps between continuation batches |
| Monetary cost | null | Infrastructure cost unmeasured |

Warsaw, UBC and KAIST hit the wall-clock limit. Aalto and Toronto hit the Fetcher
call limit. The other five completed their bounded pipeline. Generic/open-day
URLs were returned for several institutions; Toronto's returned programme was
unrelated. The case records preserve these outputs rather than crediting a URL
solely because its domain is official.

The earlier uninstrumented ten-case run also returned programme recall 1/6 and
precision 1/7, with four timeouts and one page-limit error. It remains locally in
`artifacts/research-benchmark/20260919T225124Z`; its missing telemetry is not filled
from this repeat. Neither result is directly comparable to historical canary 7/10:
the matching criterion, adjudicable denominator and budgets differ.

## Reproduction and provenance

Run the offline command in the parent README. The regression test replays
`capture.json` into `metrics.json` exactly with sockets disabled. No live network
is needed. The corpus hash, pipeline SHA, capture segments, original capture hash,
mapping hash and budgets are in the artifact.

The instrumented parent stopped after the seventh case because the evaluation
schema was edited while it was running. Its six aggregated observations and the
completed Toronto checkpoint were preserved; HKU, NTU and KAIST were then run
separately with identical budgets and production tree. No quality-based selection
was performed. Segment hashes in `capture.json` record this assembly. Do not edit
evaluation source/schema files while a live batch is running.

Direct claim names and programme scope were normalized from saved raw claims
using the same `mapping.py` now used by the live harness. Award/document identity
is not guessed. Published quotes are shortened and marked truncated: they cannot
create automatic support. Publication was checked to preserve every reported
metric relative to the full captured excerpts. Full raw files remain local in
the ignored `artifacts/research-benchmark-instrumented` directory; reopen official
sources for human adjudication rather than treating compact excerpts as evidence.

## Remaining acceptance work

Use `../REVIEW.md`: establish four unresolved exact programme identities, finish
requirements/award/document labels and independent support/scope/currentness/
conflict adjudication, validate site strata, and obtain real review signatures for
all ten cases. Missing dates or eligibility must remain UNKNOWN. Increment the
dataset version and rerun strict scoring without `--allow-drafts` before accepting
V2-01. Only then begin V2-10, the provider-neutral SearchProvider abstraction.
