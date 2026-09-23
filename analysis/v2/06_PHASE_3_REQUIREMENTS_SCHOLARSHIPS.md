# PHASE 3 — REQUIREMENTS, COSTS, SCHOLARSHIPS, DOCUMENTS

## Goal

Make the product answer not merely “this page mentions IELTS/scholarship”, but:

> Does this exact rule apply to this exact applicant/programme/intake?

# 1. Admissions requirements

For each requirement store:

```text
requirement_type
normalized_value
scope
hard/soft/action semantics
source ClaimVersion
```

Important scope questions:

```text
all applicants?
international applicants?
Kazakhstan applicants?
this qualification?
this degree?
this faculty?
this programme?
this intake?
this academic year?
```

A general rule and a programme-specific rule may both be true.

Do not label them conflict automatically.

# 2. Kazakhstan qualification rules

Do not create broad equivalence rules from memory or assumptions.

Build only from:
- university official country/credential pages;
- official government/credential authorities;
- human-reviewed evidence.

Represent distinctions such as:
- school qualification type;
- number of years;
- NIS / IB / A-level / ordinary school where evidence differentiates them;
- college/diploma pathway where evidence exists;
- direct entry vs foundation;
- subject prerequisites.

Unknown equivalence remains unknown.

# 3. IELTS / language requirements

Keep separate:
- accepted test type;
- overall minimum;
- subscore minimum;
- waiver conditions;
- scope.

Do not let a university-wide 6.5 silently override programme 7.0.

Do not infer that “English-taught” implies a particular IELTS score.

# 4. SAT / standardized tests

Store:
- required;
- optional;
- not considered / irrelevant;
- minimum if published;
- superscoring policy;
- programme/population scope.

Do not treat “test optional” as “SAT irrelevant” if a scholarship separately requires it.

# 5. Tuition and compulsory fees

Separate:
- tuition;
- registration/enrolment fee;
- student/service fee;
- insurance;
- housing;
- meals;
- books;
- other mandatory charges.

Each amount must carry:
- currency;
- academic year;
- applicable population if relevant;
- scope;
- source.

Do not compute a full annual cost from a partial fee table without making the partial basis explicit.

# 6. Scholarship decomposition

Never create one boolean `scholarship_match`.

Represent at minimum:

```text
opportunity_exists

international_eligible
citizenship_restrictions
residency_restrictions

degree_applicability
faculty_restrictions
programme_restrictions

award_current_for_intake
academic_year

application_mode:
  automatic
  separate_application
  nomination
  unknown

offer_required
financial_need_required

deadline
renewable
renewal_requirements
stackable

coverage:
  tuition
  mandatory_fees
  living
  housing
  travel
  insurance
  books

amount
duration
```

Each decision is supported separately.

# 7. Scholarship applicability engine

The roll-up must be deterministic.

Example conceptual rule:

```text
eligible =
  no confirmed disqualifying restriction
  AND required scope dimensions are supported

available_this_intake =
  opportunity_exists
  AND current_for_intake != NO
  AND applicant_eligible != NO
  AND deadline status does not prove closed
```

UNKNOWN must propagate honestly.

Do not change UNKNOWN to YES for convenience.

# 8. Scholarship search

Candidate generators:
- programme page links;
- university scholarship index;
- international funding page;
- faculty funding page;
- web search restricted to official domains;
- official government scholarship sources where relevant.

Scholarship index is discovery, not award proof.

Fetch exact award page before creating award-level decision claims.

# 9. Documents

Maintain separate document sets:

```text
UNIVERSITY ADMISSION
PROGRAMME-SPECIFIC
SCHOLARSHIP
APPLICANT ACTION
SCHOOL ACTION
RECOMMENDER ACTION
CERTIFICATION / TRANSLATION
```

A document may depend on another action:

```text
offer letter before scholarship submission
translation before notarization
credential evaluation before final review
```

Store source and scope for each required document.

# 10. Human escalation examples

Escalate when:
- wording is conditional and model/rules disagree;
- programme and general page disagree without clear scope;
- scholarship nationality wording is ambiguous;
- academic-year wording is unclear;
- PDF table cannot be parsed reliably;
- source blocks automated access;
- official page says contact admissions for country-specific assessment.

Return:
`NEEDS_OFFICIAL_CLARIFICATION`.

# Phase exit criteria

For benchmark cases:
- requirement scope is measured;
- wrong-scope rate reported;
- scholarship applicability has precision/recall;
- funding coverage is decomposed;
- required documents are evidence-backed;
- no decision-grade value relies solely on an aggregator.
