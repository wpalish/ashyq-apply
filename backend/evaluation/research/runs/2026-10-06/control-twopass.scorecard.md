# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 6/10 | 5/10 | 6/10 | 5/10 |
| claim_precision | 39/39 | 38/38 | 39/39 | 38/38 |
| claim_recall | 20/73 | 20/73 | 20/73 | 20/73 |
| wrong_scope_claim_rate | 0/39 | 0/38 | 0/39 | 0/38 |
| other_scope_claim_rate | 4/49 | 4/48 | 4/49 | 4/48 |
| partial_claim_rate | 6/49 | 6/48 | 6/49 | 6/48 |
| critical_field_coverage | 18/208 | 18/208 | 18/208 | 18/208 |
| unsupported_claim_rate | 6/30 | 6/31 | 6/30 | 6/31 |
| core questions answered | 10/60 | 10/60 | 10/60 | 10/60 |
| reads (all cases) | 356 | 322 | 356 | 331 |

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

hit: 20, missed: 51, partial: 2

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| aalto | PARTIALLY_BLOCKED (26/27 failed) | 0/4 | 0/6 | 6 | 4 | 24.7 |
| delft | REACHED (0/35 failed) | 2/4 | 2/6 | 6 | 29 | 49.0 |
| groningen | PARTIALLY_BLOCKED (2/47 failed) | 3/14 | 2/6 | 6 | 53 | 99.1 |
| hku | PARTIALLY_BLOCKED (12/33 failed) | 1/4 | 0/6 | 6 | 26 | 46.6 |
| kaist | REACHED (7/25 failed) | 0/11 | 0/6 | 6 | 34 | 70.3 |
| ntu | REACHED (7/54 failed) | 8/19 | 4/6 | 4 | 43 | 81.2 |
| toronto | REACHED (17/27 failed) | 0/7 | 0/6 | 6 | 29 | 28.6 |
| ubc | PARTIALLY_BLOCKED (7/50 failed) | 3/4 | 1/6 | 6 | 44 | 90.3 |
| vienna | REACHED (5/37 failed) | 1/4 | 1/6 | 6 | 45 | 53.5 |
| warsaw | PARTIALLY_BLOCKED (2/35 failed) | 2/2 | 0/6 | 6 | 49 | 79.1 |
