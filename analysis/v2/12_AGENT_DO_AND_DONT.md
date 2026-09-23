# AI ENGINEER — DO / DON'T

This file is intentionally repetitive. It prevents common autonomous-agent failure modes.

# DO

## Before coding
- fetch/prune;
- run handoff check;
- read current handoff;
- inspect current branch/PR state;
- establish baseline;
- identify exact acceptance test.

## While coding
- change the smallest coherent surface;
- add regression tests;
- preserve existing contracts;
- write provider abstractions;
- record telemetry;
- prefer general fixes over per-university hacks;
- keep UNKNOWN;
- keep evidence and scope;
- version model prompts/questions;
- fail closed on provider failure where correctness is at risk.

## After coding
- run focused tests;
- run required gates;
- record real numbers;
- update HANDOFF;
- commit/push small steps.

# DON'T

## Do not invent evidence
Never write fixture content pretending it came from a real live site unless clearly marked synthetic.

## Do not hard-code benchmark answers into production
The benchmark must test the system, not become a lookup table.

## Do not lower tests/coverage
No deleted assertion just to get green.

## Do not silently broaden official domains
A domain-name similarity is not ownership.

## Do not use web search as evidence
Search result snippets are discovery hints.

## Do not bypass access restrictions
No CAPTCHA bypass, stealth browser, credential guessing, proxy rotation for circumventing blocks, or robots evasion.

## Do not send the whole applicant profile to providers
Use the minimum data needed for the operation.

## Do not create hidden fallbacks
Bad:
```python
if no_tuition_found:
    tuition = 20000
```

Correct:
```text
tuition = UNKNOWN
```

## Do not equate model confidence with factual confidence
Probabilities are model outputs requiring calibration.

## Do not make one scholarship-match score
Keep eligibility dimensions separate.

## Do not let an LLM/Jev call ranking functions
Models may contribute evidence interpretation, not business-policy ranking.

## Do not store model prose as verified Claim
Only normalized claims that pass evidence/provenance rules qualify.

## Do not merge programmes by name similarity alone
“Computing” and “Computer Engineering” may be different.

## Do not erase historical values
Supersede/version them.

## Do not make live internet part of CI
Use fixtures. Run explicit canaries separately.

## Do not select a paid vendor autonomously
Implement the adapter/harness; record owner checkpoint for commercial choice/credentials.

## Do not deploy to production autonomously
Prepare release evidence; require owner-controlled deployment unless repository policy explicitly authorizes it.

## Do not start mobile/direct-application/essay-AI work
Not until research-core gates are satisfied and owner creates a separate task.

# WHEN UNCERTAIN

Prefer, in order:

```text
structured UNKNOWN
retrieve more official evidence
use bounded semantic classification
use stronger model
human review
official clarification
```

Not:

```text
guess
```
