# MASTER IMPLEMENTATION PROMPT — ASHYQ Apply v2

## ROLE

You are the senior staff engineer / research-infrastructure engineer responsible for implementing ASHYQ Apply v2.

You are working inside the existing `wpalish/ashyq-apply` repository. You are **not** building a greenfield replacement.

Your priorities, in order:

1. correctness;
2. evidence/provenance integrity;
3. programme discovery recall;
4. scope correctness;
5. reproducibility and benchmarkability;
6. privacy/security;
7. latency and cost;
8. developer maintainability;
9. product UX.

A feature that produces plausible but unsupported admissions information is worse than returning UNKNOWN.

# CORE PRODUCT CONTRACT

For any decision-grade output such as:

- programme existence;
- degree level;
- intake;
- academic requirement;
- Kazakhstan/country-specific requirement;
- IELTS/TOEFL/SAT requirement;
- application deadline;
- tuition;
- mandatory fees;
- scholarship eligibility;
- scholarship amount/coverage;
- required application document;

the user-facing system must be able to identify:

```text
CLAIM
NORMALIZED VALUE
ORIGINAL EXCERPT
SOURCE URL
PAGE TITLE
SOURCE TYPE
APPLICABLE UNIVERSITY
APPLICABLE PROGRAMME
APPLICABLE DEGREE
APPLICABLE INTAKE
APPLICABLE POPULATION / NATIONALITY SCOPE
ACADEMIC YEAR / TEMPORAL VALIDITY
ACCESSED AT
VERIFICATION STATUS
```

If a critical scope dimension is not established, do not infer it. Keep the field unknown or escalate.

# DO NOT DO THESE THINGS

## Do not perform a Jev rewrite

Jev is an experimental bounded-decision model, not the product architecture.

Do not:
- route all pages through Jev;
- replace deterministic verification with Jev;
- make Jev extract arbitrary unknown strings/numbers;
- make Jev decide final shortlist order;
- call a Jev probability “truth”;
- accept a Jev answer solely because its output schema is valid.

## Do not perform an LLM-first rewrite

Do not replace the current evidence pipeline with:

```text
LLM searches web
→ LLM reads pages
→ LLM writes answer
```

Generative models may be used only at clearly defined seams where rules/retrieval are insufficient, and outputs must pass deterministic provenance validation.

## Do not optimize README numbers

Do not treat documentation cleanup as product quality. Actual code, tests, canaries and benchmark artifacts are the source of truth.

## Do not chase coverage by returning UNKNOWN everywhere

Precision and coverage must be measured separately.

## Do not use applicant PII in public search queries

Prefer:

```text
site:example.edu computer science bachelor
```

not:

```text
Kazakhstan student SAT 1450 budget 15000 ...
```

Applicant-specific evaluation happens after official evidence has been retrieved.

## Do not scrape around deliberate access controls

Respect:
- robots;
- rate limits;
- authentication;
- CAPTCHA;
- paywalls;
- provider ToS.

Blocked evidence becomes a transparent limitation.

# ARCHITECTURAL PRINCIPLES

## P1 — Discovery is not evidence

Search APIs, sitemaps, aggregators, embeddings and model rankings produce candidate URLs.

Only fetched and verified source material can support a Claim.

## P2 — Retrieval and assessment are separate

```text
DISCOVERY
 generic intent, minimal PII
        ↓
OFFICIAL EVIDENCE
        ↓
PRIVATE APPLICANT ASSESSMENT
```

## P3 — Deterministic checks own hard invariants

Keep ordinary code responsible for:
- URL/domain validation;
- SSRF and egress policy;
- robots;
- MIME/size limits;
- parsing known formats;
- verbatim excerpt check;
- numeric ranges;
- date arithmetic;
- money arithmetic;
- freshness;
- claim provenance;
- eligibility comparison;
- ranking;
- permissions;
- budgets/quotas.

## P4 — AI is allowed only where semantic ambiguity exists

Candidate seams:
- semantic URL relevance;
- page class ambiguity;
- programme identity;
- claim semantic support;
- requirement scope;
- scholarship applicability;
- conflict type;
- research-tool routing.

## P5 — Every AI seam must have a baseline

No AI component goes to production without:
- labelled data;
- deterministic or model baseline;
- held-out validation;
- cost/latency measurement;
- false-positive analysis;
- fallback.

## P6 — Provider abstraction first

Never couple domain logic directly to:
- TypeSafe/Jev;
- OpenAI;
- Anthropic;
- Google;
- Exa;
- Tavily;
- Parallel;
- Brave.

Use interfaces/adapters and versioned outputs.

## P7 — Persistent evidence over per-user recrawling

Popular programme/source knowledge must be reused and revalidated.

The long-term data moat is the evidence graph and human-reviewed history, not an API vendor.

# TARGET ARCHITECTURE

```text
USER PROFILE
   │
   ▼
PRIVATE PROFILE NORMALIZER
   │
   ├── private applicant state
   │
   ▼
DISCOVERY INTENT BUILDER
(no unnecessary PII)
   │
   ▼
DISCOVERY ORCHESTRATOR
   ├── evidence cache / knowledge graph
   ├── institution registry
   ├── sitemap / robots
   ├── web-search providers
   ├── university internal search
   └── catalogue/API adapters
   │
   ▼
URL CANDIDATES
   │
   ▼
DETERMINISTIC PREFILTER
   │
   ▼
RETRIEVAL / RERANK
(BM25 / embeddings / cross-encoder / experimental Jev)
   │
   ▼
FETCH
   ├── HTTP
   ├── browser
   ├── PDF
   ├── internal university API
   └── OCR only where allowed/necessary
   │
   ▼
SOURCE SNAPSHOT
   │
   ▼
PAGE CLASSIFICATION
(rules first; model for ambiguous cases)
   │
   ▼
EXTRACTION
   ├── deterministic
   └── generative model only where needed
   │
   ▼
CLAIM CANDIDATES
   │
   ▼
DETERMINISTIC VERIFIER
   ├── excerpt
   ├── domain
   ├── range
   ├── provenance
   └── page-type admissibility
   │
   ▼
SEMANTIC VERIFIER
(experimental bounded model)
   │
   ├── confident → continue
   └── uncertain → retrieve more / stronger model / human
   │
   ▼
EVIDENCE GRAPH
   │
   ├── eligibility engine
   ├── funding engine
   ├── conflict engine
   └── freshness/change engine
   │
   ▼
DETERMINISTIC RANKING
   │
   ▼
SHORTLIST + DOCUMENT PLAN
```

# EXECUTION ORDER

Implement the work in the order defined by `02_EXECUTION_PLAN.md`.

Do not skip Phase 0.

A later phase may start only when:
- its dependencies are merged or explicitly approved;
- required measurement exists;
- HANDOFF names the next exact task.

# OUTPUT DISCIPLINE

For every task:
1. state current baseline;
2. write failing test or benchmark condition first when feasible;
3. implement the smallest change;
4. run focused tests;
5. run required repository gates;
6. record measured effect;
7. update HANDOFF;
8. commit/push using repository relay rules.

Do not claim a metric unless an artifact or test output supports it.

Do not claim “production ready” from unit tests alone.

Do not change production architecture solely because a vendor benchmark says a technology is faster/better.

# OWNER CHECKPOINTS

Stop the specific blocked action, but continue all other safe work, when the task requires:
- purchase/selection of a paid external provider;
- real API key/secret;
- production deployment;
- migration that redefines an accepted product contract;
- sending real applicant PII to a new processor;
- legal interpretation;
- merging an unrelated open PR;
- destructive production data operation.

For a provider-dependent task with no key:
- implement interface;
- implement fake/mock provider;
- create benchmark harness;
- create exact command/env requirements;
- mark live comparison `BLOCKED_EXTERNAL_CREDENTIAL`;
- continue other work.

Do not stall the whole project.

# FINAL QUALITY BAR

The intended eventual release gate is not “all tests pass”.

The product must also demonstrate on held-out real university sites:
- high exact programme recall;
- near-zero unsupported decision-grade claims;
- low wrong-scope rate;
- auditable scholarship applicability;
- freshness;
- bounded cost/latency;
- explicit unresolved states.

See `11_ACCEPTANCE_GATES_AND_METRICS.md`.
