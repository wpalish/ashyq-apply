# Scorecard — corpus 2026-10-17.draft10

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 6/10 | 5/10 | 5/10 | 5/10 |
| claim_precision | 27/27 | 28/28 | 28/28 | 28/28 |
| claim_recall | 15/82 | 16/82 | 16/82 | 16/82 |
| wrong_scope_claim_rate | 0/27 | 0/28 | 0/28 | 0/28 |
| other_scope_claim_rate | 4/31 | 4/32 | 4/32 | 4/32 |
| partial_claim_rate | 0/31 | 0/32 | 0/32 | 0/32 |
| critical_field_coverage | 12/231 | 12/231 | 12/231 | 12/231 |
| unsupported_claim_rate | 0/6 | 0/6 | 0/6 | 0/6 |
| core questions answered | 12/60 | 12/60 | 11/60 | 12/60 |
| known core answered | 7/27 | 7/27 | 7/27 | 7/27 |
| reads (all cases) | 359 | 344 | 346 | 336 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (0): none

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

hit: 16, missed: 66

## Per case (on#1)

| case | access | hits | core | core known | queries | reads | s |
|---|---|---|---|---|---|---|---|
| aalto | PARTIALLY_BLOCKED (20/21 failed) | 0/4 | 0/6 | 0/2 | 6 | 4 | 22.7 |
| delft | REACHED (1/41 failed) | 3/5 | 3/6 | 2/3 | 6 | 32 | 54.7 |
| groningen | PARTIALLY_BLOCKED (2/49 failed) | 3/16 | 2/6 | 2/5 | 6 | 59 | 109.8 |
| hku | PARTIALLY_BLOCKED (9/28 failed) | 1/4 | 0/6 | 0/1 | 6 | 26 | 57.2 |
| kaist | PARTIALLY_BLOCKED (5/23 failed) | 0/11 | 0/6 | 0/3 | 6 | 33 | 61.3 |
| ntu | REACHED (3/41 failed) | 2/21 | 3/6 | 1/5 | 3 | 27 | 60.0 |
| toronto | REACHED (19/25 failed) | 0/7 | 0/6 | 0/2 | 6 | 29 | 30.4 |
| ubc | unknown (0/0 failed) | 4/6 | 2/6 | 2/4 | 6 | 47 | 115.0 |
| vienna | REACHED (6/37 failed) | 1/4 | 1/6 | 0/0 | 6 | 45 | 52.4 |
| warsaw | PARTIALLY_BLOCKED (1/32 failed) | 2/4 | 0/6 | 0/2 | 6 | 44 | 69.1 |
