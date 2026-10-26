# Scorecard — corpus 2026-10-17.draft10

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 6/10 | 7/10 | 7/10 | 6/10 |
| claim_precision | 27/27 | 27/27 | 28/28 | 27/27 |
| claim_recall | 15/82 | 15/82 | 16/82 | 15/82 |
| wrong_scope_claim_rate | 0/27 | 0/27 | 0/28 | 0/27 |
| other_scope_claim_rate | 4/31 | 4/31 | 4/32 | 4/31 |
| partial_claim_rate | 0/31 | 0/31 | 0/32 | 0/31 |
| critical_field_coverage | 12/231 | 12/231 | 12/231 | 12/231 |
| unsupported_claim_rate | 0/6 | 0/6 | 0/6 | 0/6 |
| core questions answered | 11/60 | 12/60 | 12/60 | 12/60 |
| known core answered | 7/27 | 7/27 | 7/27 | 7/27 |
| reads (all cases) | 353 | 358 | 362 | 352 |

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

hit: 16, missed: 66

## Per case (on#1)

| case | access | hits | core | core known | queries | reads | s |
|---|---|---|---|---|---|---|---|
| aalto | PARTIALLY_BLOCKED (31/33 failed) | 0/4 | 0/6 | 0/2 | 6 | 6 | 26.5 |
| delft | REACHED (0/41 failed) | 3/5 | 3/6 | 2/3 | 6 | 32 | 58.8 |
| groningen | PARTIALLY_BLOCKED (2/49 failed) | 3/16 | 2/6 | 2/5 | 6 | 58 | 113.0 |
| hku | PARTIALLY_BLOCKED (12/36 failed) | 1/4 | 1/6 | 0/1 | 6 | 25 | 52.7 |
| kaist | PARTIALLY_BLOCKED (4/23 failed) | 0/11 | 0/6 | 0/3 | 6 | 34 | 76.2 |
| ntu | REACHED (3/41 failed) | 2/21 | 3/6 | 1/5 | 3 | 27 | 59.5 |
| toronto | REACHED (33/34 failed) | 0/7 | 0/6 | 0/2 | 6 | 41 | 47.6 |
| ubc | PARTIALLY_BLOCKED (7/57 failed) | 4/6 | 2/6 | 2/4 | 6 | 48 | 115.8 |
| vienna | REACHED (5/37 failed) | 1/4 | 1/6 | 0/0 | 6 | 47 | 57.7 |
| warsaw | PARTIALLY_BLOCKED (1/32 failed) | 2/4 | 0/6 | 0/2 | 6 | 44 | 81.9 |
