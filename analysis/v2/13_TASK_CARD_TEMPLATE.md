# TASK CARD TEMPLATE — ASHYQ Apply v2

Copy this block for every implementation task.

## ID
`V2-XX`

## Title
Short behaviour-oriented title.

## Status
`not-started | in-progress | blocked | ready-for-review | merged`

## Dependency
List required merged tasks/PRs.

## Why this task exists
Describe the measured product problem, not the technology you want to use.

## Baseline
Provide current metric/test/failure.

Example:

```text
programme recall: 7/10 on dataset X
exact failure cases: A, B, C
SHA:
dataset version:
```

## Goal
One measurable outcome.

## Non-goals
List adjacent work that must not be pulled into the task.

## Allowed paths
Specify expected files/modules.

## Forbidden / owner-checkpoint paths
List things requiring explicit decision.

## Contract changes
Expected schema/config/API changes.

## Test-first cases
1.
2.
3.

## Implementation notes
Only constraints that are already decided.

Do not prescribe a model if the task is meant to benchmark models.

## Acceptance criteria
- [ ]
- [ ]
- [ ]

## Metrics
Before:
After:

## Privacy/security review
Data classes leaving service:
Provider:
Retention/policy reference:
PII:
Network-policy impact:

## Migration
`none` or revision plan.

## Rollback/fallback
How to disable the new path.

## Commands / gates
Use current repo commands.

## Live canary
If required, exact bounded command and artifact path.

## Completion packet
- commit SHA(s);
- test output;
- metric artifact;
- screenshots if UI;
- known limitations;
- next exact step.

# Example acceptance language

Good:

> On benchmark v2.1, exact programme recall@20 rises from 78% to >=90% while exact programme precision remains >=99%, with no more than 25 fetched pages/university median.

Bad:

> Make discovery much smarter using AI.
