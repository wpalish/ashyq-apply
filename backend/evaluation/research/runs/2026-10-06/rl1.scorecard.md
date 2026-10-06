# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 5/10 | 5/10 | 6/10 | 5/10 |
| claim_precision | 38/38 | 38/38 | 43/43 | 41/41 |
| claim_recall | 19/73 | 20/73 | 22/73 | 22/73 |
| wrong_scope_claim_rate | 0/38 | 0/38 | 0/43 | 0/41 |
| other_scope_claim_rate | 4/48 | 4/48 | 4/53 | 4/51 |
| partial_claim_rate | 6/48 | 6/48 | 6/53 | 6/51 |
| critical_field_coverage | 18/208 | 18/208 | 21/208 | 21/208 |
| unsupported_claim_rate | 6/30 | 6/30 | 6/30 | 6/30 |
| core questions answered | 10/60 | 10/60 | 12/60 | 12/60 |
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

hit: 22, missed: 49, partial: 2

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| aalto | PARTIALLY_BLOCKED (26/27 failed) | 0/4 | 0/6 | 6 | 4 | 24.7 |
| delft | REACHED (0/41 failed) | 3/4 | 3/6 | 6 | 33 | 50.9 |
| groningen | PARTIALLY_BLOCKED (2/49 failed) | 3/14 | 2/6 | 6 | 57 | 100.7 |
| hku | PARTIALLY_BLOCKED (14/33 failed) | 1/4 | 0/6 | 6 | 25 | 37.2 |
| kaist | REACHED (3/23 failed) | 0/11 | 0/6 | 6 | 34 | 50.9 |
| ntu | REACHED (7/60 failed) | 8/19 | 4/6 | 4 | 47 | 94.1 |
| toronto | REACHED (17/28 failed) | 0/7 | 0/6 | 6 | 30 | 27.6 |
| ubc | PARTIALLY_BLOCKED (7/56 failed) | 4/4 | 2/6 | 6 | 48 | 84.0 |
| vienna | REACHED (5/37 failed) | 1/4 | 1/6 | 6 | 45 | 56.2 |
| warsaw | PARTIALLY_BLOCKED (2/35 failed) | 2/2 | 0/6 | 6 | 49 | 78.5 |
