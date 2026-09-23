# EXECUTION PLAN — task graph

This is the recommended task order. The AI agent must convert each row into a repository task/branch compatible with the existing relay process.

Do not execute all tasks in one branch.

## PHASE 0 — Establish truth and measurement

### V2-00 — Reconcile current repository state
**Goal:** know what is actually on `main`.

Tasks:
- run handoff reconciliation;
- inspect open PRs;
- verify current CI definitions;
- verify migrations/head;
- verify live/demo configuration;
- identify stale documentation;
- do not merge unrelated branches automatically.

Deliverable:
- current-state note with commit SHA and evidence;
- HANDOFF updated.

### V2-01 — Benchmark data model and metrics
Read: `03_PHASE_0_BENCHMARK.md`

### V2-02 — Build 50-university development corpus
Human-verified ground truth. It may start with 10–15 universities and expand incrementally, but the schema must support 50 from day one.

### V2-03 — Baseline current discovery/extraction
Run current system against benchmark under bounded canary rules.

## PHASE 1 — Programme discovery

Read: `04_PHASE_1_DISCOVERY_ENGINE.md`

### V2-10 — Search provider interface
No provider lock-in.

### V2-11 — Generic-intent query generator
No unnecessary applicant PII.

### V2-12 — Field/degree ontology
Aliases and semantic neighbourhood, with false-friend relationships.

### V2-13 — Hybrid candidate retrieval
Rules + BM25/embedding layer.

### V2-14 — Reranker benchmark
Current scorer vs cross-encoder vs optional Jev/LLM.

### V2-15 — University internal-search adapters
Detect/support common public search/catalogue surfaces.

### V2-16 — Discovery fusion and provenance
Merge search/sitemap/registry/site-search results with source attribution.

### V2-17 — Programme identity verification v2
Verify university + programme + degree + field + active status + intake scope independently.

## PHASE 2 — Evidence graph and scope

Read: `05_PHASE_2_EVIDENCE_GRAPH.md`

### V2-20 — SourceSnapshot / ClaimVersion schema
Version evidence, do not overwrite history.

### V2-21 — Scope model
Programme / degree / intake / population / nationality / academic year.

### V2-22 — Entity resolution
University, programme, alias, version, intake canonical IDs.

### V2-23 — Conflict model v2
Separate contradiction from different-scope facts.

### V2-24 — Change detection
ETag/Last-Modified → hash → semantic/material diff.

## PHASE 3 — Requirements, costs, scholarships and documents

Read: `06_PHASE_3_REQUIREMENTS_SCHOLARSHIPS.md`

### V2-30 — Requirements scope verification
### V2-31 — Kazakhstan credential rule representation
Start with a narrow validated dataset; do not invent nationwide equivalences.
### V2-32 — Tuition + compulsory fee model
### V2-33 — Scholarship rule decomposition
### V2-34 — Scholarship applicability engine
### V2-35 — Document requirement graph
Admission and scholarship documents remain distinct.

## PHASE 4 — Jev / model experiments

Read: `07_PHASE_4_JEV_EXPERIMENTS.md`

### V2-40 — AI decision provider interface
### V2-41 — Jev page classifier experiment
### V2-42 — Jev programme-link reranker experiment
### V2-43 — Jev claim semantic verifier experiment
### V2-44 — Jev scholarship decomposition experiment
### V2-45 — Jev tool-router shadow experiment
### V2-46 — Deployment decision record

No Jev component is promoted merely because the experiment runs.

## PHASE 5 — Privacy, security, latency and operations

Read:
- `08_PHASE_5_PRIVACY_SECURITY.md`
- `09_PHASE_6_LATENCY_COST.md`

### V2-50 — PII/data-flow inventory
### V2-51 — Provider data-policy registry
### V2-52 — Search/assessment privacy separation enforcement
### V2-53 — Evidence-cache / stale-while-revalidate
### V2-54 — Progressive result API
### V2-55 — recheck scheduler and priority queue
### V2-56 — cost telemetry per research run

## PHASE 6 — Human review

### V2-60 — Review queue
### V2-61 — Evidence comparison UI/API
### V2-62 — Review labels become benchmark examples
### V2-63 — reviewer audit trail

Human review must be designed as a correctness mechanism, not as a hidden manual patch.

## PHASE 7 — B2B/API expansion

Only after quality gates are met.

### V2-70 — Counselor research workspace
### V2-71 — organization review permissions
### V2-72 — evidence/research API
### V2-73 — usage/credits model

Do not build direct-application rails in this phase unless separately approved.

# Milestone mapping

## ~30 days
Focus on:
- V2-00 through V2-17;
- event-loop/crawler reliability blockers;
- benchmark;
- search provider abstraction;
- programme discovery.

## ~90 days
Focus on:
- V2-20 through V2-46;
- evidence graph;
- scope;
- scholarship intelligence;
- human review v1;
- Jev experiments.

## ~365 days
Focus on:
- scaled evidence graph;
- Central Asia qualification depth;
- automatic change detection;
- counselor SaaS/API;
- direct university feeds where available.

The agent must optimize for completed validated slices, not calendar promises.
