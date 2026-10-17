# Scorecard — corpus 2026-10-17.draft10

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 6/10 | 6/10 | 7/10 | 7/10 |
| claim_precision | 28/30 | 19/19 | 27/27 | 27/27 |
| claim_recall | 16/82 | 11/82 | 15/82 | 15/82 |
| wrong_scope_claim_rate | 2/30 | 0/19 | 0/27 | 0/27 |
| other_scope_claim_rate | 4/34 | 4/23 | 4/31 | 4/31 |
| partial_claim_rate | 0/34 | 0/23 | 0/31 | 0/31 |
| critical_field_coverage | 12/231 | 9/231 | 12/231 | 12/231 |
| unsupported_claim_rate | 0/6 | 0/2 | 0/6 | 0/6 |
| core questions answered | 11/60 | 9/60 | 11/60 | 11/60 |
| known core answered | 7/27 | 5/27 | 7/27 | 7/27 |
| reads (all cases) | 338 | 336 | 341 | 328 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (1): hku:programme.exists

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 0.933 | >= 0.95 | NO |
| off | wrong_scope_claim_rate | 0.067 | <= 0.03 | NO |
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
| aalto | PARTIALLY_BLOCKED (31/33 failed) | 0/4 | 0/6 | 0/2 | 6 | 7 | 27.1 |
| delft | REACHED (0/40 failed) | 3/5 | 3/6 | 2/3 | 6 | 30 | 55.0 |
| groningen | PARTIALLY_BLOCKED (2/49 failed) | 3/16 | 2/6 | 2/5 | 6 | 59 | 105.5 |
| hku | PARTIALLY_BLOCKED (25/38 failed) | 0/4 | 0/6 | 0/1 | 6 | 22 | 74.1 |
| kaist | PARTIALLY_BLOCKED (18/26 failed) | 0/11 | 0/6 | 0/3 | 6 | 20 | 89.4 |
| ntu | REACHED (3/41 failed) | 2/21 | 3/6 | 1/5 | 3 | 27 | 71.2 |
| toronto | REACHED (31/34 failed) | 0/7 | 0/6 | 0/2 | 6 | 41 | 42.5 |
| ubc | unknown (0/0 failed) | 4/6 | 2/6 | 2/4 | 6 | 46 | 115.0 |
| vienna | REACHED (5/37 failed) | 1/4 | 1/6 | 0/0 | 6 | 45 | 58.9 |
| warsaw | PARTIALLY_BLOCKED (1/32 failed) | 2/4 | 0/6 | 0/2 | 6 | 44 | 76.0 |
