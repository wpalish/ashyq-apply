# Scorecard — corpus 2026-10-17.draft10

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 6/10 | 7/10 | 7/10 | 6/10 |
| claim_precision | 25/25 | 27/27 | 27/27 | 27/27 |
| claim_recall | 13/82 | 15/82 | 15/82 | 15/82 |
| wrong_scope_claim_rate | 0/25 | 0/27 | 0/27 | 0/27 |
| other_scope_claim_rate | 2/27 | 4/31 | 4/31 | 4/31 |
| partial_claim_rate | 0/27 | 0/31 | 0/31 | 0/31 |
| critical_field_coverage | 10/231 | 12/231 | 12/231 | 12/231 |
| unsupported_claim_rate | 0/6 | 0/6 | 0/7 | 0/7 |
| core questions answered | 9/60 | 11/60 | 11/60 | 11/60 |
| known core answered | 5/27 | 7/27 | 7/27 | 7/27 |
| reads (all cases) | 329 | 341 | 330 | 336 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (1): hku:programme.exists

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 1.000 | >= 0.95 | yes |
| off | wrong_scope_claim_rate | 0.000 | <= 0.03 | yes |
| off | cases_over_budget | 0 | == 0 | yes |
| on | claim_precision | 1.000 | >= 0.95 | yes |
| on | wrong_scope_claim_rate | 0.000 | <= 0.03 | yes |
| on | cases_over_budget | 0 | == 0 | yes |

## Wrong claims (on, every repetition)

- none

## Known labels by outcome (on#1)

hit: 15, missed: 67

## Per case (on#1)

| case | access | hits | core | core known | queries | reads | s |
|---|---|---|---|---|---|---|---|
| aalto | PARTIALLY_BLOCKED (30/33 failed) | 0/4 | 0/6 | 0/2 | 6 | 8 | 27.1 |
| delft | REACHED (1/41 failed) | 3/5 | 3/6 | 2/3 | 6 | 34 | 63.9 |
| groningen | PARTIALLY_BLOCKED (2/49 failed) | 3/16 | 2/6 | 2/5 | 6 | 57 | 108.1 |
| hku | PARTIALLY_BLOCKED (18/33 failed) | 0/4 | 0/6 | 0/1 | 6 | 24 | 57.1 |
| kaist | PARTIALLY_BLOCKED (19/26 failed) | 0/11 | 0/6 | 0/3 | 6 | 20 | 103.2 |
| ntu | REACHED (3/41 failed) | 2/21 | 3/6 | 1/5 | 3 | 27 | 66.1 |
| toronto | PARTIALLY_BLOCKED (17/28 failed) | 0/7 | 0/6 | 0/2 | 6 | 30 | 33.6 |
| ubc | PARTIALLY_BLOCKED (7/56 failed) | 4/6 | 2/6 | 2/4 | 6 | 46 | 91.4 |
| vienna | REACHED (5/37 failed) | 1/4 | 1/6 | 0/0 | 6 | 41 | 55.2 |
| warsaw | PARTIALLY_BLOCKED (1/32 failed) | 2/4 | 0/6 | 0/2 | 6 | 43 | 75.2 |
