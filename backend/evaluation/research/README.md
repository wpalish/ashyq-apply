# V2-01 research benchmark

This is evaluation tooling, excluded from production containers. The live runner
uses the existing production registry, Fetcher and ResearchRunner. It never loads
ground truth. Ranking, discovery, verification and network policy are unchanged.

Certified corpus: [acceptance record](ACCEPTANCE.md). Latest source annotations:
[draft7](REVIEW_DRAFT7.md), [version comparison](VERSIONS.md),
[human review worksheet](REVIEW_WORKSHEET_DRAFT7.md).

## Current acceptance status

**ACCEPTED.** `ground_truth.reviewed.json` was signed by Диас on 2026-09-21: 10/10
cases `human_verified`, and it scores under the strict command with no `--allow-drafts`
and `provisional: false`. See the [acceptance record](ACCEPTANCE.md).

What is certified is the *source annotation* — 62 known labels of 220 and ten programme
identities — not the 158 fields that remain UNKNOWN and not the pipeline's output. The
baseline it produces is deliberately unflattering: programme-page recall **1/10**, claim
precision **0/5**, every produced claim out of scope, critical-field coverage **0/210**.
That is the "before" number architecture work must beat; it is not a product result and
must not be quoted as one. Every `draft*` version remains provisional and the strict
scorer still refuses it.

The source pack is in `analysis/v2`; its original `00_START_HERE.md` became README.md.
The manifest preserves original archive names. AGENTS, the original task brief,
and the single `docs/process/HANDOFF.md` remain the relay system.

## Offline output replay

From `backend`, with the project Python environment:

```sh
python -m evaluation.research --dataset evaluation/research/data/ground_truth.json --capture evaluation/research/baseline/capture.json --out ../artifacts/replayed-metrics.json --allow-drafts
python -m pytest tests/test_research_benchmark.py
```

This deterministically scores captured **pipeline outputs**. It does not replay
HTML through discovery; it cannot estimate how a new discovery algorithm would
perform from old output alone. New implementations need fresh bounded captures
or a separately assembled source-response replay corpus. Tests prevent socket use
in offline scoring. No web tools, paid provider or LLM are used by the offline CLI.

The committed baseline includes compact observations, metrics and a limitations
report. Published excerpts are deliberately shortened and flagged; they cannot
automatically establish claim support. Full raw captures remain in the local,
ignored `artifacts/` directory. Read official sources for new evidence adjudication.
The [review queue](REVIEW.md) lists the unfinished cases.

## Live capture

```sh
python -m evaluation.research.live --live --seconds-per-case 90 --max-pages 60 --out ../artifacts/research-benchmark
```

Ten institutions, sequentially, one fresh subprocess and temporary database/cache
per institution. Optional `--case groningen` selects one. HTTP-only baseline:
browser disabled explicitly, production robots/PII/egress protections retained.
No applicant records are read: the existing canary creates a synthetic profile.
Budgets bound Fetcher.get calls (including cache hits), **not actual wire requests**;
each call may include robots, redirects/retries. A hard subprocess timeout bounds
the whole case, including blocking parsers in main while PR #13 remains open.
Timeouts are failures, remain in recall denominators and do not count as abstention
success. Missing telemetry remains null. Instrumented captures count HTTP request
attempts at Fetcher's pinned request constructor (including robots and retries),
and successful uncached PDF responses separately. Checkpoints preserve counts at
timeouts. These count attempts, not proven server receipts. Output persists per case.

Capture does not receive expected URLs, labels or evidence. The cohort contains
only IDs and registry domain selectors. No university-specific fixes are introduced.
Read the per-case errors before interpreting metrics; truncated runs are not
unrestricted pipeline quality. The budget and HTTP-only setting must match when
comparing future runs. No provider fees are incurred by this harness.

## Label and review procedure

1. Choose university × degree × field × intake and assign a stable case ID.
2. Read current official pages, including the exact programme and population.
   A search snippet, homepage or related programme is not an exact-match label.
3. Enter only minimal evidence, URL, scope and access date. Unknown scope stays null.
   `labels[].key` identifies independent facts: `country_credential`, `ielts.overall`,
   `ielts.subscores`, `sat.policy`, `sat.minimum`, `deadline`, `tuition`, `mandatory_fees`,
   `intake`, `documents.admission.<document>`, `documents.programme.<document>` and
   `documents.scholarship.<document>`. Values are normalized JSON; money includes
   currency, period/year in evidence scope. Never conflate a 2026 quote with 2027.
4. For each award use stable `scholarships.<award>.exists`, `.applicability.<dimension>`
   (nationality, international, degree, programme, intake, offer, need, nomination,
   application mode), `.coverage.<category>` (tuition, fees, living, housing, travel,
   insurance), `.amount`, `.deadline`, `.duration`, `.renewal`. No one match boolean.
5. `unknown` is not a negative; `not_applicable` requires an explanatory note.
6. A real human opens the evidence, checks values/scope and signs `reviewer` and
   `verified_on`, then changes status to `human_verified`. AI preparation is recorded
   in `prepared_by`; do not fabricate a human signoff. Increment dataset version in
   the dataset and every case. Commit a review note explaining changed evidence.
7. Preserve old artifacts with their dataset hash. Do not edit a label to improve
   pipeline scores. Grow to 50 development and a separately versioned 100+ held-out
   validation set. Validation errors are not tuning data during final evaluation.

## Metric definitions and limits

Every rate includes numerator/denominator. Empty denominator is null. There is no
combined accuracy score. Exact duplicate predictions/URLs cannot inflate credit.
Queries and path case are preserved in URL identity; fragments/trailing slash removed.

Programme recall is cases with an exact accepted URL / cases with known programme
URLs. Precision is accepted distinct returned URLs / adjudicable returned URLs.
Unknown exact-URL cases are unadjudicated. `recall_at_5/10/20` requires an actual
ranked candidate list; it is null when unavailable. Instrumented captures observe
the programme confirmation queue before catalogue walking. These ranks are not
final result ranks or a measure of all retrieval stages. Report their measured
denominator; a timeout before this stage leaves the rank list unmeasured.

Claims require exact normalized value, compatible evidence scope and supporting
official evidence. Human-adjudicated `supported` can establish support; otherwise
the same source URL and an excerpt contained in the label evidence are required.
Evidence comparison is conservative and exact, not semantic equivalence. Missing
scope fails precision and contributes to the conservative scope-failure rate.
Claim recall counts distinct correct labelled keys; precision includes only known
labels. `claim_adjudication_rate` exposes unlabelled predictions. Unsupported rate
excludes unadjudicated support, with `support_adjudication_rate` alongside it.
Never advertise subset precision without these adjudication rates.

Critical coverage counts answered applicable fields even if answers are wrong;
recall separately counts correct answerable fields. UNKNOWN does not count answered.
Scholarship metrics use the independent key dimensions above. Freshness/conflict
metrics require explicit adjudication and remain null otherwise. Per-case country
and site-type records expose subgroup errors. Operations preserve missing measurements
and show measured-case counts; latency p50/p95 use nearest rank. Budget timeout latency
is time-to-failure, not time-to-useful-result.

## Next work

Explicit offline award/document identity mapping is documented in [MAPPING.md](MAPPING.md).
It produces separate replay artifacts and never injects registry identities into
production or the live runner. Compound-to-atomic label alignment remains review work.

The latest annotation candidate is [draft3](REVIEW_DRAFT3.md): 52 known fields and
eight exact programme identities, with no human signoffs. Seven draft2 document
records were losslessly projected into thirteen fields; no new source facts are
claimed. It has a separate report over the frozen capture; older versions remain unchanged.
See [the version comparison](VERSIONS.md) for the changing denominators.

Finish human review, detailed labels, award/document identity mapping and evidence
adjudication before accepting V2-01. The next roadmap task **after acceptance**
is V2-10: provider-neutral SearchProvider with a fake adapter and benchmark comparison.
No Jev or discovery improvement belongs in this task.
