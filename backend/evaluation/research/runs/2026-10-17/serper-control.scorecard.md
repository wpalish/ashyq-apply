# Scorecard — corpus 2026-10-17.draft10

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 6/10 | 6/10 | 6/10 | 6/10 |
| claim_precision | 27/29 | 19/19 | 27/29 | 27/29 |
| claim_recall | 15/82 | 11/82 | 15/82 | 15/82 |
| wrong_scope_claim_rate | 2/29 | 0/19 | 2/29 | 2/29 |
| other_scope_claim_rate | 4/33 | 4/23 | 4/33 | 4/33 |
| partial_claim_rate | 0/33 | 0/23 | 0/33 | 0/33 |
| critical_field_coverage | 12/231 | 9/231 | 12/231 | 12/231 |
| unsupported_claim_rate | 0/6 | 0/2 | 0/6 | 0/6 |
| core questions answered | 12/60 | 10/60 | 12/60 | 12/60 |
| known core answered | 7/27 | 5/27 | 7/27 | 7/27 |
| reads (all cases) | 355 | 348 | 353 | 358 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (0): none

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 0.931 | >= 0.95 | NO |
| off | wrong_scope_claim_rate | 0.069 | <= 0.03 | NO |
| off | cases_over_budget | 0 | == 0 | yes |
| on | claim_precision | 0.931 | >= 0.95 | NO |
| on | wrong_scope_claim_rate | 0.069 | <= 0.03 | NO |
| on | cases_over_budget | 0 | == 0 | yes |

## Wrong claims (on, every repetition)

- ubc `deadline`: ours "2026-11-15" vs "2027-01-15" (wrong_value) ×4

## Known labels by outcome (on#1)

hit: 15, missed: 67

## Per case (on#1)

| case | access | hits | core | core known | queries | reads | s |
|---|---|---|---|---|---|---|---|
| aalto | PARTIALLY_BLOCKED (31/33 failed) | 0/4 | 0/6 | 0/2 | 6 | 6 | 28.6 |
| delft | REACHED (0/41 failed) | 3/5 | 3/6 | 2/3 | 6 | 32 | 53.5 |
| groningen | PARTIALLY_BLOCKED (2/50 failed) | 3/16 | 2/6 | 2/5 | 6 | 60 | 105.8 |
| hku | PARTIALLY_BLOCKED (9/31 failed) | 0/4 | 1/6 | 0/1 | 6 | 27 | 49.7 |
| kaist | PARTIALLY_BLOCKED (4/23 failed) | 0/11 | 0/6 | 0/3 | 6 | 35 | 68.1 |
| ntu | REACHED (3/41 failed) | 2/21 | 3/6 | 1/5 | 3 | 27 | 54.5 |
| toronto | REACHED (31/34 failed) | 0/7 | 0/6 | 0/2 | 6 | 41 | 43.9 |
| ubc | unknown (0/0 failed) | 4/6 | 2/6 | 2/4 | 6 | 39 | 115.6 |
| vienna | REACHED (5/37 failed) | 1/4 | 1/6 | 0/0 | 6 | 43 | 52.0 |
| warsaw | PARTIALLY_BLOCKED (1/32 failed) | 2/4 | 0/6 | 0/2 | 6 | 43 | 71.9 |
