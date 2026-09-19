# PHASE 5 — PRIVACY, SECURITY, PROVIDER GOVERNANCE

## Goal

Increase discovery recall without turning applicant data into search-engine/provider payloads.

This file is engineering guidance, not legal advice. Production compliance decisions require appropriate legal review.

# 1. Data classification

Create explicit classes:

```text
PUBLIC_DISCOVERY_INTENT
NON_SENSITIVE_PROFILE_PREFERENCES
APPLICANT_PII
ACADEMIC_PERSONAL_DATA
FINANCIAL_PERSONAL_DATA
UPLOADED_DOCUMENT_CONTENT
SECRETS/CREDENTIALS
```

Every outbound provider adapter declares what classes it may receive.

# 2. Search queries

Default external search payload is `PUBLIC_DISCOVERY_INTENT`.

Normally acceptable:

```text
university domain
field
degree
programme terminology
international admissions
country name when finding country-specific public rules
intake/year
```

Normally prohibited:

```text
name
email
phone
passport
transcript content
family income
family contribution
exact personal budget
private notes
uploaded documents
```

Exact scores/GPA should not be sent to search merely to find programme pages.

# 3. Model providers

Maintain a provider registry with:

```text
provider
purpose
approved data classes
training policy
retention policy
ZDR option
region/data-location notes
DPA status
contract version/date reviewed
owner approval
```

Do not hard-code legal claims into comments forever. Policies change.

# 4. Separation architecture

```text
PUBLIC DISCOVERY SERVICE
    |
    | generic intent
    v
OFFICIAL SOURCE EVIDENCE

PRIVATE ASSESSMENT SERVICE
    |
    | local/private applicant profile
    v
eligibility / funding / ranking
```

This boundary should be visible in code.

Add tests that fail if forbidden profile fields enter external-search request construction.

# 5. Kazakhstan data location

The product targets Kazakhstan and may be subject to local personal-data localization/cross-border-transfer requirements.

Engineering direction:
- architect primary applicant datastore so Kazakhstan hosting is possible;
- minimize cross-border personal-data transfer;
- maintain provider/data-flow inventory;
- obtain legal review before production.

Do not claim compliance merely from choosing a cloud region.

# 6. Existing network invariants

Do not weaken existing:
- Fetcher SSRF protections;
- redirect checks;
- PII guard;
- robots handling;
- rate limiting;
- official-domain checks;
- content-size limits;
- browser request gating.

New search/internal-API/browser adapters must go through the same security architecture or an explicitly reviewed equivalent.

# 7. Prompt injection / hostile pages

University pages are untrusted input.

Never let page text:
- redefine system instructions;
- enable tools;
- alter provider permissions;
- request secrets;
- change network policy;
- change acceptance thresholds.

Models receive page content as data, not instructions.

Use strict schemas and small context windows where possible.

# 8. Raw page storage

Decide explicitly:
- which bodies are cached;
- for how long;
- whether object storage is used;
- whether copyright-sensitive full bodies need retention;
- whether minimal normalized excerpts are enough.

Never store more than needed “because it may be useful later”.

# 9. Logs

Do not log:
- secrets;
- full uploaded documents;
- unredacted PII;
- provider auth headers.

Usage/cost telemetry should reference stable internal IDs.

# 10. Security gates for new providers

Before enabling production provider:
- secret not committed;
- timeout;
- retry budget;
- circuit breaker/fail-closed semantics;
- rate limit;
- redacted logging;
- request-size cap;
- response-size cap;
- data-policy record;
- mock tests;
- failure-path tests.

# 11. Human review privacy

Reviewer UI must expose only data necessary for the claim under review.

Where possible, reviewer sees:
- programme context;
- source;
- claim;
- applicant category needed for scope;

not unrelated applicant details.

# Exit criteria

- search queries demonstrably exclude unnecessary PII;
- provider data-class policy exists;
- new adapters preserve network invariants;
- hostile-page prompt injection cannot change tool/security policy;
- logs are redacted;
- cross-border provider usage is visible/auditable.
