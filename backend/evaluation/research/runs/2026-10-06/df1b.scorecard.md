<!-- run 37510315899 (benchmark-capture, expert_paired, ABBA); rule DF-1; provider=exa_mcp decided_by=explicit input extra_args=--fee-year-columns base_args= -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 6/10 | 5/10 | 6/10 | 6/10 |
| claim_precision | 38/38 | 14/14 | 39/39 | 18/18 |
| claim_recall | 19/73 | 9/73 | 20/73 | 13/73 |
| wrong_scope_claim_rate | 0/38 | 0/14 | 0/39 | 0/18 |
| other_scope_claim_rate | 3/47 | 1/15 | 4/49 | 4/22 |
| partial_claim_rate | 6/47 | 0/15 | 6/49 | 0/22 |
| critical_field_coverage | 17/208 | 4/208 | 18/208 | 7/208 |
| unsupported_claim_rate | 6/30 | 0/6 | 6/30 | 0/6 |
| core questions answered | 9/60 | 3/60 | 10/60 | 6/60 |
| reads (all cases) | 334 | 303 | 328 | 308 |

**Stable gains** (1): delft:tuition
**Stable losses** (0): none
Unstable (7): ntu:deadline, ntu:scholarships.nanyang_global.applicability.nationality, ntu:scholarships.nanyang_global.bond, ntu:scholarships.nanyang_global.coverage.living, ntu:scholarships.nanyang_global.duration, ntu:scholarships.nanyang_global.exists, ntu:scholarships.nanyang_global.renewal

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
| aalto | BLOCKED (27/27 failed) | 0/4 | 0/6 | 6 | 1 | 15.5 |
| delft | REACHED (0/35 failed) | 2/4 | 2/6 | 6 | 29 | 42.8 |
| groningen | PARTIALLY_BLOCKED (2/47 failed) | 3/14 | 2/6 | 6 | 53 | 104.8 |
| hku | PARTIALLY_BLOCKED (12/33 failed) | 1/4 | 0/6 | 6 | 26 | 47.1 |
| kaist | PARTIALLY_BLOCKED (4/12 failed) | 0/11 | 0/6 | 1 | 14 | 32.9 |
| ntu | REACHED (7/54 failed) | 8/19 | 4/6 | 4 | 43 | 87.8 |
| toronto | REACHED (18/27 failed) | 0/7 | 0/6 | 6 | 30 | 27.8 |
| ubc | PARTIALLY_BLOCKED (11/51 failed) | 3/4 | 1/6 | 6 | 40 | 76.0 |
| vienna | REACHED (5/37 failed) | 1/4 | 1/6 | 6 | 44 | 49.2 |
| warsaw | PARTIALLY_BLOCKED (2/35 failed) | 2/2 | 0/6 | 6 | 48 | 73.7 |
