# PHASE 0 — BENCHMARK AND MEASUREMENT

## Objective

Before changing discovery or introducing Jev/LLMs, create a benchmark that can answer:

> Did this change materially improve ASHYQ Apply?

Without this phase, architecture decisions are opinions.

# Dataset structure

## Development benchmark

Target: **50 universities**.

Choose deliberately varied sites, including:
- simple static HTML;
- large sitemap;
- JS catalogue;
- internal JSON/API catalogue;
- faculty subdomains;
- multilingual sites;
- PDF-heavy admissions;
- country-specific requirement pages;
- programme pages with unusual names;
- sites with WAF/robots limitations;
- universities frequently considered by Kazakhstan applicants.

Do not choose only universities that already work.

## Validation benchmark

Target: **100+ universities**, held out from implementation tuning.

Do not inspect/fix individual validation failures while calculating final validation metrics. Move a site into development set only through an explicit dataset-version change.

# Ground-truth unit

Prefer:

```text
University × requested field × degree × intake
```

Example:

```text
University of X
Bachelor
Computer Science
Fall 2027
Applicant origin context: Kazakhstan only where a country rule is being labelled
```

# Required labels

For each case manually record:

```yaml
university:
  canonical_name:
  canonical_domain:

request:
  degree:
  field:
  intake:

programme:
  exists: true|false|unknown
  canonical_name:
  exact_url:
  acceptable_aliases:
  evidence_excerpt:
  evidence_url:

requirements:
  kazakhstan_qualification:
    status:
    normalized:
    scope:
    evidence_url:
    excerpt:
  ielts:
    overall:
    subscores:
    scope:
    evidence_url:
    excerpt:
  sat:
    policy:
    minimum:
    scope:
    evidence_url:
    excerpt:
  deadline:
    normalized:
    raw:
    scope:
    evidence_url:
    excerpt:

costs:
  tuition:
  mandatory_fees:
  academic_year:
  evidence_url:
  excerpt:

scholarships:
  - name:
    evidence_url:
    international:
    kazakhstan:
    degree:
    programme:
    intake:
    application_mode:
    nomination:
    offer_required:
    need_required:
    coverage:
      tuition:
      living:
      housing:
      travel:
      insurance:
    amount:
    deadline:

documents:
  admission: []
  programme_specific: []
  scholarship: []
```

A label may explicitly be `unknown`.

# Dataset provenance

Each ground-truth row must contain:
- verifier/reviewer;
- verified date;
- source URLs;
- excerpts;
- notes;
- dataset version.

Do not paste entire copyrighted pages. Store only the minimum evidence excerpt needed.

# Metrics

## Discovery

```text
PROGRAMME_PAGE_RECALL
PROGRAMME_PAGE_PRECISION
RECALL@5
RECALL@10
RECALL@20
```

A correct university homepage is not a correct programme URL.

## Claims

```text
CLAIM_PRECISION
CLAIM_RECALL
UNSUPPORTED_CLAIM_RATE
WRONG_SCOPE_CLAIM_RATE
```

## Scholarship

```text
SCHOLARSHIP_DISCOVERY_RECALL
SCHOLARSHIP_APPLICABILITY_PRECISION
SCHOLARSHIP_APPLICABILITY_RECALL
SCHOLARSHIP_COVERAGE_PRECISION
```

## Evidence quality

```text
PRIMARY_SOURCE_RATE
VERBATIM_EVIDENCE_RATE
CURRENT_EVIDENCE_RATE
CONFLICT_VISIBILITY_RATE
```

## Operations

```text
COST_PER_UNIVERSITY
COST_PER_VERIFIED_PROGRAMME
WALL_CLOCK
P50 / P95 LATENCY
HTTP_FETCHES
BROWSER_FETCHES
PDF_FETCHES
SEARCH_REQUESTS
MODEL_INPUT_TOKENS
JEV_INPUT_TOKENS
HUMAN_REVIEW_RATE
```

# Coverage must be separate from correctness

Never calculate a single “accuracy” that rewards returning UNKNOWN.

For each critical field report:

```text
coverage = answered / applicable
precision = correct answered / answered
recall = correct answered / ground_truth_answerable
```

Example:

```text
coverage: 40%
precision: 100%
```

is not production-ready simply because precision is perfect.

# Benchmark runner requirements

Create a deterministic offline benchmark runner that can consume previously captured fixtures/snapshots.

Live benchmark commands must:
- be explicit;
- be bounded;
- write timestamped artifacts;
- not run in normal CI;
- respect production fetch policy.

Normal unit/CI tests:
- no real internet;
- no live Jev;
- no live LLM;
- no live paid search API.

# Regression corpus

Every serious live failure becomes a compact fixture/regression case.

Examples:
- programme page classified as catalogue;
- MSc selected for Bachelor;
- scholarship page selected as programme;
- PDF parser failure;
- same-domain spoof;
- departmental subdomain missed;
- country requirement wrongly applied globally.

Do not “fix the university” by hard-coding its exact URL unless the registry/manual-seed contract explicitly calls for a verified seed.

Prefer general fixes.

# Minimum Phase-0 exit criteria

- benchmark schema committed;
- at least 10 manually verified cases populated;
- current pipeline can be scored against them;
- metrics separate precision and coverage;
- costs/latency can be recorded;
- no live provider dependency in CI;
- roadmap to 50-dev / 100-validation recorded.

Do not promote a new AI architecture before this exists.
