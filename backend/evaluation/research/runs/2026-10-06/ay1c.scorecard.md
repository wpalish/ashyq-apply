<!-- run 37332559615 (benchmark-capture, expert_paired, ABBA); rule AY-1; provider=exa_mcp decided_by=explicit input extra_args=--applicant-academic-year base_args=--tuition-row-year -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 5/10 | 6/10 | 5/10 | 5/10 |
| claim_precision | 36/37 | 15/16 | 20/20 | 17/17 |
| claim_recall | 18/73 | 10/73 | 13/73 | 12/73 |
| wrong_scope_claim_rate | 1/37 | 1/16 | 0/20 | 0/17 |
| other_scope_claim_rate | 3/46 | 3/19 | 3/23 | 3/20 |
| partial_claim_rate | 6/46 | 0/19 | 0/23 | 0/20 |
| critical_field_coverage | 17/208 | 6/208 | 9/208 | 6/208 |
| unsupported_claim_rate | 6/30 | 0/6 | 0/7 | 0/7 |
| core questions answered | 10/60 | 6/60 | 8/60 | 5/60 |
| reads (all cases) | 326 | 315 | 313 | 290 |

**Stable gains** (1): groningen:tuition
**Stable losses** (0): none
Unstable (7): ntu:deadline, ntu:scholarships.nanyang_global.applicability.nationality, ntu:scholarships.nanyang_global.bond, ntu:scholarships.nanyang_global.coverage.living, ntu:scholarships.nanyang_global.duration, ntu:scholarships.nanyang_global.exists, ntu:scholarships.nanyang_global.renewal

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 0.938 | >= 0.95 | NO |
| off | wrong_scope_claim_rate | 0.062 | <= 0.03 | NO |
| off | cases_over_budget | 9 | == 0 | NO |
| on | claim_precision | 1.000 | >= 0.95 | yes |
| on | wrong_scope_claim_rate | 0.000 | <= 0.03 | yes |
| on | cases_over_budget | 8 | == 0 | NO |

## Wrong claims (on, every repetition)

- none

## Known labels by outcome (on#1)

hit: 13, missed: 60

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| aalto | BLOCKED (27/27 failed) | 0/4 | 0/6 | 6 | 1 | 15.9 |
| delft | REACHED (0/34 failed) | 1/4 | 1/6 | 6 | 27 | 49.2 |
| groningen | PARTIALLY_BLOCKED (2/37 failed) | 3/14 | 2/6 | 4 | 42 | 72.5 |
| hku | PARTIALLY_BLOCKED (15/35 failed) | 1/4 | 0/6 | 7 | 25 | 41.3 |
| kaist | REACHED (3/12 failed) | 0/11 | 0/6 | 1 | 15 | 19.0 |
| ntu | REACHED (7/33 failed) | 2/19 | 2/6 | 3 | 22 | 35.1 |
| toronto | REACHED (18/27 failed) | 0/7 | 0/6 | 6 | 30 | 24.8 |
| ubc | PARTIALLY_BLOCKED (13/53 failed) | 3/4 | 1/6 | 7 | 43 | 72.1 |
| vienna | REACHED (8/40 failed) | 1/4 | 1/6 | 7 | 48 | 56.6 |
| warsaw | PARTIALLY_BLOCKED (2/40 failed) | 2/2 | 1/6 | 7 | 60 | 98.3 |
