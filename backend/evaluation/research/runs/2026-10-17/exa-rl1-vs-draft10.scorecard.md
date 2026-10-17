# Scorecard — corpus 2026-10-17.draft10

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 5/10 | 5/10 | 6/10 | 5/10 |
| claim_precision | 41/41 | 41/41 | 46/46 | 44/44 |
| claim_recall | 20/82 | 21/82 | 23/82 | 23/82 |
| wrong_scope_claim_rate | 0/41 | 0/41 | 0/46 | 0/44 |
| other_scope_claim_rate | 4/51 | 4/51 | 4/56 | 4/54 |
| partial_claim_rate | 6/51 | 6/51 | 6/56 | 6/54 |
| critical_field_coverage | 19/231 | 19/231 | 22/231 | 22/231 |
| unsupported_claim_rate | 6/30 | 6/30 | 6/30 | 6/30 |
| core questions answered | 10/60 | 10/60 | 12/60 | 12/60 |
| known core answered | 7/27 | 7/27 | 9/27 | 9/27 |
| reads (all cases) | 355 | 327 | 372 | 347 |

**Stable gains** (2): delft:ielts.overall, ubc:deadline
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

hit: 23, missed: 57, partial: 2

## Per case (on#1)

| case | access | hits | core | core known | queries | reads | s |
|---|---|---|---|---|---|---|---|
| aalto | PARTIALLY_BLOCKED (26/27 failed) | 0/4 | 0/6 | 0/2 | 6 | 4 | 24.7 |
| delft | REACHED (0/41 failed) | 3/5 | 3/6 | 2/3 | 6 | 33 | 50.9 |
| groningen | PARTIALLY_BLOCKED (2/49 failed) | 3/16 | 2/6 | 2/5 | 6 | 57 | 100.7 |
| hku | PARTIALLY_BLOCKED (14/33 failed) | 1/4 | 0/6 | 0/1 | 6 | 25 | 37.2 |
| kaist | REACHED (3/23 failed) | 0/11 | 0/6 | 0/3 | 6 | 34 | 50.9 |
| ntu | REACHED (7/60 failed) | 9/21 | 4/6 | 3/5 | 4 | 47 | 94.1 |
| toronto | REACHED (17/28 failed) | 0/7 | 0/6 | 0/2 | 6 | 30 | 27.6 |
| ubc | PARTIALLY_BLOCKED (7/56 failed) | 4/6 | 2/6 | 2/4 | 6 | 48 | 84.0 |
| vienna | REACHED (5/37 failed) | 1/4 | 1/6 | 0/0 | 6 | 45 | 56.2 |
| warsaw | PARTIALLY_BLOCKED (2/35 failed) | 2/4 | 0/6 | 0/2 | 6 | 49 | 78.5 |
