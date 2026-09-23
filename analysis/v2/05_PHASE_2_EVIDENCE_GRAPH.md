# PHASE 2 — EVIDENCE GRAPH, SCOPE, VERSIONING

## Goal

Move from per-run facts to persistent, versioned, auditable admissions knowledge.

Do not build a vague "knowledge graph" abstraction first. Start with concrete normalized entities and provenance.

# Core entities

Recommended conceptual model:

```text
University
Campus
Faculty / School

Programme
ProgrammeAlias
ProgrammeVersion
Degree
Field
Intake

AdmissionRequirement
CountrySpecificRequirement
LanguageRequirement
StandardizedTestRequirement

Deadline
Tuition
Fee

Scholarship
ScholarshipEligibilityRule
ScholarshipCoverage

RequiredDocument
ApplicationPortal

SourcePage
SourceSnapshot

Claim
ClaimVersion
Conflict

Applicant
ResearchRun
HumanReview
```

You may adapt names to existing models. Avoid unnecessary duplicate domain concepts.

# SourcePage vs SourceSnapshot

`SourcePage` = canonical URL identity and current fetch metadata.

`SourceSnapshot` = content/version observed at a time.

Recommended fields:

```text
page_id
snapshot_id
canonical_url
final_url
page_title
page_type
content_hash
etag
last_modified
fetched_at
http_status
mime_type
language
raw_object_pointer (optional, policy-controlled)
normalized_text_hash
```

Do not necessarily store full page bodies forever. Store enough to reproduce evidence under the project's legal/storage policy.

# Claim scope

Existing Claim already carries programme/intake fields. Expand or normalize scope so decision-grade claims can distinguish:

```text
university scope
faculty scope
programme scope
degree scope
intake scope
academic-year scope
population scope
country/nationality scope
residency scope
```

Use explicit UNKNOWN/null semantics.

Do not encode critical scope only inside free-text `notes`.

# Programme versioning

Programme is a stable conceptual entity.

ProgrammeVersion represents a specific published version/cycle.

Example:

```text
Programme:
  University X — BSc Computer Science

Versions:
  2026/27
  2027/28
```

A URL may remain identical while requirements change.

Do not treat URL identity as programme-version identity.

# Alias/entity resolution

Maintain:
- canonical university;
- canonical programme;
- aliases;
- language aliases;
- former names;
- source URLs.

Entity resolution must be auditable.

If two pages may describe different programmes, keep them separate until proven equivalent.

Do not merge because names are merely similar.

# ClaimVersion

Never destructively overwrite a verified historical value.

Model:

```text
Claim
  logical subject/type

ClaimVersion
  normalized value
  scope
  snapshot
  valid_from
  valid_to / superseded_at
  verification
```

Current query returns latest applicable non-superseded version.

History remains available.

# Conflict model v2

Today differing normalized values can create a conflict.

Improve classification:

```text
TRUE_CONFLICT
MORE_SPECIFIC_SOURCE
DIFFERENT_POPULATION
DIFFERENT_PROGRAMME
DIFFERENT_DEGREE
DIFFERENT_INTAKE
DIFFERENT_ACADEMIC_YEAR
DIFFERENT_REQUIREMENT_TYPE
AMBIGUOUS
```

Important:

A more specific source may be preferred for assessment, but do not delete the broader claim.

# Freshness and recheck

Current freshness windows are a starting point.

Add claim/snapshot scheduling:

```text
next_recheck_at
last_checked_at
change_priority
risk_class
```

Suggested risk concept:
- deadline/intake: highest refresh frequency;
- scholarship availability: high;
- tuition/fees: medium-high;
- admissions policy: medium;
- evergreen descriptive metadata: lower.

Configuration should be versioned and testable.

# Change detection pipeline

```text
conditional GET
   ↓
HTTP says unchanged?
   ├ yes → update observed/check timestamp
   └ no
      ↓
content hash
      ↓
normalized content diff
      ↓
re-extract candidate claims
      ↓
compare claim set
      ↓
material change?
      ├ no
      └ yes → new ClaimVersion + review rules
```

Optional semantic change classifier is a later optimization, not the first source of truth.

# Evidence graph queries the product must support

Examples:

```text
Which evidence currently supports IELTS for programme P / intake I?

What changed since the last applicant run?

Which scholarships apply to Kazakhstani undergraduates in programme P?

Which claims are stale?

Which result rows depend on a changed claim?

Which claims are conflicting?

Which facts are still unknown for this programme?
```

# Migration discipline

If schema changes require Alembic:
- one head before;
- one head after;
- never edit a migration already on `main`;
- migration tests on PostgreSQL;
- backward compatibility where repository contracts require it.

# Phase exit criteria

- source/version entities persist without overwriting historical truth;
- scope is structured, not buried in prose;
- current claims can be queried by entity/intake/population;
- conflict reasons distinguish true conflict from different scope;
- change detection can create a new version;
- existing claim/provenance invariants remain green.
