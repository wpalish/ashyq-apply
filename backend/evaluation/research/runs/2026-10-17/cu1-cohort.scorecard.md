# Scorecard — corpus 2026-10-17.draft10

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 6/10 | 5/10 | 6/10 | 6/10 |
| claim_precision | 27/27 | 25/25 | 28/28 | 27/27 |
| claim_recall | 15/82 | 13/82 | 16/82 | 15/82 |
| wrong_scope_claim_rate | 0/27 | 0/25 | 0/28 | 0/27 |
| other_scope_claim_rate | 4/31 | 2/27 | 4/32 | 4/31 |
| partial_claim_rate | 0/31 | 0/27 | 0/32 | 0/31 |
| critical_field_coverage | 12/231 | 10/231 | 12/231 | 12/231 |
| unsupported_claim_rate | 0/6 | 0/6 | 0/6 | 0/6 |
| core questions answered | 12/60 | 10/60 | 12/60 | 12/60 |
| known core answered | 7/27 | 5/27 | 7/27 | 7/27 |
| reads (all cases) | 357 | 355 | 349 | 355 |

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
| aalto | PARTIALLY_BLOCKED (31/33 failed) | 0/4 | 0/6 | 0/2 | 6 | 6 | 25.4 |
| delft | REACHED (0/41 failed) | 3/5 | 3/6 | 2/3 | 6 | 32 | 57.0 |
| groningen | unknown (0/0 failed) | 3/16 | 2/6 | 2/5 | 6 | 56 | 115.0 |
| hku | PARTIALLY_BLOCKED (12/36 failed) | 1/4 | 1/6 | 0/1 | 6 | 25 | 47.3 |
| kaist | PARTIALLY_BLOCKED (4/23 failed) | 0/11 | 0/6 | 0/3 | 6 | 34 | 78.6 |
| ntu | REACHED (3/41 failed) | 2/21 | 3/6 | 1/5 | 3 | 27 | 70.9 |
| toronto | REACHED (32/34 failed) | 0/7 | 0/6 | 0/2 | 6 | 41 | 49.7 |
| ubc | PARTIALLY_BLOCKED (7/56 failed) | 4/6 | 2/6 | 2/4 | 6 | 44 | 116.2 |
| vienna | REACHED (5/37 failed) | 1/4 | 1/6 | 0/0 | 6 | 45 | 57.6 |
| warsaw | PARTIALLY_BLOCKED (1/32 failed) | 2/4 | 0/6 | 0/2 | 6 | 39 | 72.8 |
