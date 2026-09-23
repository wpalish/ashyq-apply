# PHASE 4 — JEV / BOUNDED MODEL EXPERIMENTS

## Important premise

Jev is not a factual oracle.

A typed answer being schema-valid does **not** imply:
- factual correctness;
- correct scope;
- no false positive;
- no false negative.

Therefore every Jev component starts as:
`EXPERIMENTAL / SHADOW`.

No production replacement before benchmark evidence.

# Provider architecture

Define a bounded-decision interface independent of TypeSafe.

Concept:

```python
class DecisionModel(Protocol):
    async def choose(...): ...
    async def boolean(...): ...
    async def score(...): ...
```

Store with every model decision:
- provider;
- model;
- model/version identifier where available;
- input schema version;
- question id/version;
- probabilities/confidence;
- timestamp;
- latency;
- token/usage cost if available.

Domain logic must not import a provider SDK.

# Experiment 1 — Page classifier

## Input
Use bounded page evidence:
- URL;
- title;
- H1/H2;
- breadcrumb;
- selected main-content text;
- simple structural signals.

## Allowed answers

```text
PROGRAM_DETAIL
INTAKE_SPECIFIC_PROGRAM
PROGRAM_CATALOG
GENERAL_ADMISSIONS
COUNTRY_REQUIREMENTS
SCHOLARSHIP_AWARD
SCHOLARSHIP_INDEX
COST_PAGE
DOCUMENT_CHECKLIST
MARKETING_PAGE
RESEARCH_PAGE
NEWS
EVENT
OTHER
INSUFFICIENT_EVIDENCE
```

## Baseline
Current rule classifier.

## Success
- better macro-F1 on held-out pages;
- no meaningful programme-precision regression;
- acceptable latency/cost.

## Failure
If it mainly converts UNKNOWN into confident wrong labels, reject deployment.

# Experiment 2 — Programme-link reranker

## Input

For each candidate link:
- target field;
- target degree;
- university;
- URL;
- anchor;
- page title/snippet if available.

Do not send thousands of links in one high-cardinality choice.

Recommended:

```text
rules/lexical → top 100
embedding/BM25 → top 30–50
Jev/cross-encoder → final ranking
```

## Baselines
- existing scorer;
- BM25;
- embedding cosine;
- cross-encoder.

## Metric
Recall@10 / Recall@20 for exact programme page.

Cost/fetch reduction is a secondary metric.

# Experiment 3 — Claim semantic verifier

## Input

```text
candidate claim
normalized value
verbatim excerpt
page type
expected programme
expected degree
expected intake
expected population
```

## Allowed answers

```text
SUPPORTED
CONTRADICTED
NOT_MENTIONED
AMBIGUOUS
WRONG_SCOPE
```

## Mandatory ordering

```text
DETERMINISTIC PROVENANCE CHECK
↓
SEMANTIC MODEL
↓
ACCEPT / SEARCH_MORE / REVIEW
```

Never replace:
- excerpt check;
- domain check;
- range check;
- provenance.

## Thresholds
Do not choose 0.90/0.95 arbitrarily.
Calibrate on held-out labels by error consequence.

# Experiment 4 — Scholarship applicability

Run parallel independent questions.

## Eligibility questions

```text
international students eligible?
Kazakhstan eligible?
undergraduate eligible?
faculty eligible?
exact programme eligible?
target intake eligible?
target academic year valid?
separate application required?
nomination required?
offer required first?
financial need required?
```

## Coverage questions

```text
tuition?
mandatory fees?
living allowance?
housing?
travel?
insurance?
books?
```

Do not ask:
`Does this scholarship match?`

## Baseline
Current rules + generative structured extraction if present.

## Metrics
Per-field precision/recall plus final deterministic applicability.

# Experiment 5 — Tool router

Initial mode: shadow only.

Allowed next actions:

```text
HTTP_FETCH
BROWSER
PDF
SITE_SEARCH
WEB_SEARCH
CATALOG_WALK
OCR
LLM_EXTRACTION
SEARCH_MORE
STOP
HUMAN_REVIEW
```

The model proposes. Application policy decides if action is allowed.

Never let model bypass:
- robots;
- egress;
- rate limits;
- provider budgets;
- privacy.

Metric:
- did suggested next action produce needed evidence more efficiently than baseline policy?

# Jev should NOT be used for

- fetching;
- public web search;
- robots;
- sitemap XML;
- arbitrary text generation;
- translation;
- free-form explanation;
- extracting unknown arbitrary strings by itself;
- parsing exact money/date values where deterministic parsing works;
- ranking formula;
- eligibility/funding arithmetic;
- provenance enforcement.

# Promotion process

For each experiment write an ADR/experiment report:

```text
problem
baseline
dataset version
model/version
questions/schema
thresholds
precision/recall
false positives
false negatives
coverage
latency
cost
failure examples
fallback
privacy
vendor risk
decision
```

Possible decisions:

```text
PROMOTE
PROMOTE AS FALLBACK
KEEP SHADOW
REJECT
RETEST LATER
```

Do not say "Jev is better" without a dataset/version and metric.
