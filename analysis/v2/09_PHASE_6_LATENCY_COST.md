# PHASE 6 — LATENCY, CACHING AND COST

## Problem

Cold live university research can take minutes. A consumer should not wait for an entire deep crawl before receiving value.

The long-term fix is **reuse**, not merely more concurrency.

# 1. Cache layers

Recommended:

```text
L1 request-local
L2 HTTP/source cache
L3 SourcePage / SourceSnapshot evidence store
L4 normalized Programme/Requirement/Scholarship graph
```

A programme already verified recently should not be recrawled for every applicant.

# 2. Stale-while-revalidate

If evidence is inside a safe usability window:

```text
return cached verified result
+
mark refresh in background if approaching stale
```

If decision-critical evidence is stale beyond policy:
- label stale;
- refresh before hard decision where feasible;
- do not silently present as current.

# 3. Progressive result UX/API

Research state should expose:

```text
candidate_found
programme_verified
requirements_verified
costs_verified
funding_verified
documents_verified
complete
needs_clarification
```

A shortlist row can appear before every secondary field is complete if its uncertainty is visible.

# 4. Parallelism

Parallelize across universities subject to:
- global worker capacity;
- per-host politeness;
- browser limits;
- search/API quotas;
- database contention.

Do not increase concurrency by violating university-site politeness.

# 5. Tool escalation ladder

Prefer cheap path first:

```text
cache
→ HTTP
→ site/search retrieval
→ PDF parser
→ browser
→ OCR / generative extraction
→ human
```

This is a default policy, not absolute. Benchmark can justify exceptions.

# 6. Cost telemetry

For each ResearchRun record:

```text
search_requests by provider
HTTP requests
browser renders
PDF parses
OCR calls
embedding calls/tokens
reranker calls
Jev input tokens/calls
LLM tokens/calls
storage bytes
wall clock
human review minutes
```

No architecture can be optimized without this.

# 7. Shared knowledge economics

Measure:

```text
cache hit rate
source reuse rate
programme reuse rate
claims reused per new applicant
```

Expected product direction:

```text
first applicant for University X:
expensive evidence research

next 100 applicants:
cheap private assessment + selective revalidation
```

# 8. Suggested UX latency targets

These are product targets, not promises:

```text
profile/local normalization:     < 1–3 s
cached shortlist:                < 5–15 s
first progressive fresh result:  < 30 s
ordinary refresh:                < 1–2 min
hard browser/PDF case:           may take longer, shown progressively
```

Do not hide slow research behind a spinner.

# 9. Search/model budgeting

Every stage has a bounded budget:
- max search queries/university;
- max candidate URLs;
- max HTTP pages;
- max browser renders;
- max model calls;
- max wall-clock;
- max retries.

If budget exhausts:

```text
SEARCH_BUDGET_EXHAUSTED
NEEDS_CLARIFICATION
```

not uncontrolled crawl.

# 10. Human review is expensive

Track human cost separately.

The system should prioritize automation for frequent, well-labelled error classes.

Do not use expensive human review to hide poor programme discovery metrics.

# Exit criteria

- repeated applicant research demonstrably reuses evidence;
- per-run cost can be calculated;
- progressive statuses exist;
- browser is a fallback rather than default;
- stale-while-revalidate semantics are explicit;
- latency/cost benchmarks accompany discovery-quality benchmarks.
