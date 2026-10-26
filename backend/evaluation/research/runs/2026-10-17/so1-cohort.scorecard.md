# Scorecard — corpus 2026-10-17.draft10

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 7/10 | 7/10 | 5/10 | 6/10 |
| claim_precision | 24/24 | 28/28 | 27/27 | 27/27 |
| claim_recall | 12/82 | 16/82 | 15/82 | 15/82 |
| wrong_scope_claim_rate | 0/24 | 0/28 | 0/27 | 0/27 |
| other_scope_claim_rate | 2/26 | 4/32 | 4/31 | 4/31 |
| partial_claim_rate | 0/26 | 0/32 | 0/31 | 0/31 |
| critical_field_coverage | 10/231 | 12/231 | 12/231 | 12/231 |
| unsupported_claim_rate | 0/6 | 0/6 | 0/6 | 0/6 |
| core questions answered | 9/60 | 11/60 | 11/60 | 11/60 |
| known core answered | 5/27 | 7/27 | 7/27 | 7/27 |
| reads (all cases) | 353 | 357 | 306 | 318 |

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
| aalto | PARTIALLY_BLOCKED (20/22 failed) | 0/4 | 0/6 | 0/2 | 6 | 6 | 27.6 |
| delft | REACHED (0/38 failed) | 3/5 | 3/6 | 2/3 | 6 | 29 | 56.0 |
| groningen | unknown (0/0 failed) | 3/16 | 2/6 | 2/5 | 6 | 55 | 115.0 |
| hku | PARTIALLY_BLOCKED (13/25 failed) | 0/4 | 0/6 | 0/1 | 6 | 18 | 50.0 |
| kaist | PARTIALLY_BLOCKED (4/23 failed) | 0/11 | 0/6 | 0/3 | 6 | 35 | 70.7 |
| ntu | REACHED (3/38 failed) | 2/21 | 3/6 | 1/5 | 3 | 26 | 69.7 |
| toronto | REACHED (22/23 failed) | 0/7 | 0/6 | 0/2 | 6 | 29 | 34.3 |
| ubc | REACHED (4/38 failed) | 4/6 | 2/6 | 2/4 | 6 | 32 | 61.7 |
| vienna | REACHED (5/33 failed) | 1/4 | 1/6 | 0/0 | 6 | 40 | 52.8 |
| warsaw | PARTIALLY_BLOCKED (1/28 failed) | 2/4 | 0/6 | 0/2 | 6 | 36 | 66.7 |
