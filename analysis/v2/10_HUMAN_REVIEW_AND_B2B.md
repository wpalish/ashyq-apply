# HUMAN REVIEW AND B2B WORKSPACE

## Human review purpose

Human review is a reliability layer and a data-generation loop.

It is not a place where counselors silently repair arbitrary output without trace.

# Review queue item

Show:

```text
entity
candidate claim
normalized value
source excerpt
source URL
page type
scope
freshness
competing claims
deterministic verifier result
semantic model result/probabilities
reason for escalation
```

Actions:

```text
ACCEPT
REJECT
WRONG_SCOPE
TRUE_CONFLICT
NEEDS_MORE_RESEARCH
NEEDS_OFFICIAL_CLARIFICATION
```

Require reviewer note for sensitive overrides.

# Audit trail

Store:
- reviewer ID;
- timestamp;
- prior state;
- action;
- note;
- evidence version;
- model/version if model contributed.

Never mutate benchmark labels silently.

# Learning loop

Reviewed examples can become:
- benchmark additions;
- regression tests;
- hard negatives for retrieval;
- threshold-calibration data;
- future classifier training data.

Dataset updates must be versioned.

# Counselor/B2B product

Only prioritize after research-quality gates are credible.

Useful first B2B features:

```text
organization / tenant
applicant cases
research status
evidence review queue
shortlist review
deadline overview
usage/quota
export
audit log
```

Do not begin with a full CRM.

# API product

Potential future API surfaces:

```text
/programmes/search
/programmes/{id}
/requirements
/scholarships
/eligibility/evaluate
/evidence
/changes
```

An API answer must preserve the same evidence contract as the UI.

Never offer “verified” API data that bypasses internal verification just because B2B clients want lower latency.

# Direct applications

Do not implement universal submission until separately approved.

Application rails introduce:
- institution-specific forms;
- applicant attestations;
- document custody;
- payments;
- recommendation workflows;
- legal/compliance obligations;
- far higher operational risk.

Research intelligence is the current moat priority.
