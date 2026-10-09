# Recall90 implementation and acceptance

Owner authorization: implement the approved plan, with loop engineering and
independent adversarial review. Branch `task/recall90` depends on unmerged
`task/product-security-privacy@ea4a13ed`; this is an explicit predecessor
exception, not a claim that the stack is merged or deployed.

## Objective and scope

At least 90% recall and 95% precision for automatic core admission decisions
for Kazakhstan applicants to English-taught bachelor's programmes across
Computer Science, Business Administration and Mechanical Engineering.
Ordinary Kazakhstan school certificates and NIS are separate requested routes.
Documents remain outside the six-group quality target. A retrieval hit, a
synthetic fixture or historical selected-answer precision cannot prove it.

Six decision groups: English options/minima/subscores/waivers; academic
credentials/subjects/grades/routes; current programme/population deadline;
tuition amount/currency/period/year/category; a concrete scholarship offer;
scholarship applicability and conditions. Programme identity, campus, degree
and English instruction are separate gates. A contract lists every required
component; one IELTS or GPA value does not close its entire group.

## Current implementation

- `evaluation/research/decision_metrics.py`: separate strict scorer, independent
  contract/review sidecars, missing-case denominator, all emitted unique
  decisions in precision, scope/currentness/conditions/conflict checks,
  subject aggregates and university cluster bootstrap intervals. Citation
  variants cannot multiply a correct answer. Historical scorer is unchanged.
  `release_eligible` deliberately remains false: sampling/budgets/deployment
  are not certified by this module.
- `WebRequirementsAdapter(..., question_frontier=True)`: official navigation
  before extraction classifier rejection, academic questions independent of
  IELTS, bounded multiple topic candidates and graduate/exchange exclusion.
  `UNIMATCH_RESEARCH_QUESTION_FRONTIER=false` is the default; the actual runner
  passes the option when enabled. Existing Fetcher protections remain in force.
- `app/research/contracts.py`: explicit question states, public scope, evidence
  coordinates, policy conditions/exceptions/dependencies and decision answers.
- `app/research/evidence.py`: source-hash authentication, institution/cycle
  cache, local scope projection, currentness and dependency DAG checks.
  Projection requires an explicit deterministic entailment callback plus
  local condition/exception evaluation. A cache record or authentic quote
  alone is never a verified answer.
- `app/research/compiler.py`, `session.py`, `questions.py`: observed native HTML
  feeds a versioned deterministic compiler and six-group projection. Source
  scope comes from the page; institution authority comes from the curated
  registry or native persisted site identity, including original/final hosts.
  Source changes invalidate replay proof; public source cache is reusable
  without applicant data. Mixed certificates, unresolved campus/country
  restrictions and incomplete band minima cannot become complete answers.
  Projection overflow is unavailable, never an answer from a truncated set.
  Supported grammars cover selected IELTS, academic, deadline and tuition
  rules. English options/waivers and both scholarship groups remain pending;
  this compiler alone cannot achieve the six-group 90% target. PDFs/OCR and
  broader native/semantic policy grammars remain necessary.
- Default-off `UNIMATCH_RESEARCH_STAGED`: additive start modes `fast` and
  `fast_then_deep`, response phase/preliminary/question states, existing Worker
  deep job and durable cumulative ledger. Read/query reservations commit under
  ownership fences before native dispatch; real operations have timeouts.
  Deep refinement preserves applicant decisions/notes. Frontier rollout is a
  separate flag and must be explicitly frozen for each experiment variant.
- `app/research/semantic.py`: bounded public-only proposal and independent
  exception-critic interfaces, pre-dispatch cumulative reservations, failure
  accounting, nullable actual cost and final deterministic proof gate. No live
  semantic provider has been integrated or tested yet.

## Required remaining implementation and validation

1. Expand the bounded native compiler and applicant projection to all decision
   groups and source formats, preserving conditions/exceptions and source scope.
   Cache cold build and warm reuse costs separately; bind compiler/model/prompt
   versions and invalidate every dependent rule when its source changes.
2. Complete full backend/frontend/demo/E2E acceptance for the implemented
   default-off staged runtime, including real journey and race verification.
3. Implement reproducible A/B/C/D experiments: existing algorithm with strict
   scoring, question frontier, shared evidence, semantic fallback. Use paired
   ABBA ordering and equal budgets, frozen source/provider/model/prompts/cache.
   Diagnostics distinguish access, navigation, extraction, representation and
   applicability; counterfactual oracle access is never automatic recall.
4. Measure tiers per university: 120s/6 queries/60 reads; 300s/12/120;
   900s/24/240; 1800s/24/240. Semantic research caps: 12 calls, 200k input and
   20k output tokens, counting the critic and failed attempts. Unknown monetary
   cost is null. Choose the cheapest development tier satisfying the gates,
   otherwise record NO_GO. Do not retroactively change budgets for failed runs.
5. Independent custodian preregisters 30 development and 60 different sealed
   validation universities, stratified by geography/site format, with all three
   directions and both qualification routes, including absent programmes and
   access failures. Existing exposed cohorts are diagnostic only. Freeze all
   configuration before the holdout; no tuning against sealed validation.
6. Pass recall/precision thresholds pooled and for each subject; publish
   university-cluster intervals, usable coverage, unknown/not-published/NA and
   unavailable cases. Do not treat profiles within a university as independent
   samples or promise every individual university meets the aggregate target.
7. Run required lint/type/backend coverage and applicable frontend/demo/E2E
   checks, finish independent adversarial review, open/update the dependent PR,
   push final handoff. An engineering checkpoint is not final product acceptance.

The immutable stopped historical collection (STOP SHA prefix `65b5`) remains
UNSCORED and must never be resumed/relabelled as a fresh successful experiment.
Fresh provider access and independently reviewed gold are required for new live
quality claims. APIs, rendered pages, PDFs/OCR, local-language discovery and
licensed official data may be compared as separately controlled sources;
Fetcher, robots, privacy and network policy are not bypassed by this work.

## Loop record

First offline loop implemented the strict scorer, question frontier and evidence
interfaces. Root's first aggregate check passed 51 tests. Independent review
then reproduced forged values with authentic quotes, unresolved conditions,
unspecified-campus leakage, cyclic/cross-group dependency errors, declared
conflicts counted as correct, and citation-variant precision inflation.

The next loop added mandatory deterministic proof/local applicability, exact
scope projection, DAG resolution across groups, unique-answer scoring and
declared-conflict rejection. A real native demo pipeline with the frontier
option both off and on is included. Root's subsequent aggregate check passed
63 tests; broader regression/static checks are recorded in HANDOFF when they
finish. These counts are offline engineering evidence, not live quality.


Latest checkpoint: root144tests passed in15.07s (one existing dependency
deprecation warning), Ruff passed; full format377 and mypy375 source files
passed before the final bounded-projection changes, then changed-file mypy
passed. Previously broader154tests passed in115.44s. Staging20tests exercise
cumulative caps, recovery clocks and phase idempotency; native runtime/API15
tests additionally exercise real SQL/Worker/Fetcher flow, durable reservation,
timeouts, stale leases, unique deep queue and preserved user decisions.
Independent review reproduced wrong-institution/campus, mixed certificate and
partial IELTS-band errors; fixes have dedicated offline regressions. Cache
starvation and policy-work overflow regressions also pass. Experiment manifest5tests
exercise all3directions/bothroutes, disjoint60-university validation, ABBA/cache
isolation and missing/over-cap telemetry. No custodian-signed real cohort,
accepted live experiment, staged production journey or90% result exists yet.
GitHub checks did not start because the account payment/spending limit blocked
Actions; this is NOT_RUN, not a successful cloud check or product-test failure.
