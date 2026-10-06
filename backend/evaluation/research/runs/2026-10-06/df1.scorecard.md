<!-- run 37500440224 (benchmark-capture, expert_paired, ABBA); rule DF-1; provider=exa_mcp decided_by=explicit input extra_args=--fee-year-columns base_args= -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 7/10 | 7/10 | 7/10 | 7/10 |
| claim_precision | 37/37 | 16/16 | 37/38 | 16/17 |
| claim_recall | 18/73 | 11/73 | 18/73 | 11/73 |
| wrong_scope_claim_rate | 0/37 | 0/16 | 1/38 | 1/17 |
| other_scope_claim_rate | 3/46 | 3/19 | 4/48 | 4/21 |
| partial_claim_rate | 6/46 | 0/19 | 6/48 | 0/21 |
| critical_field_coverage | 17/208 | 6/208 | 18/208 | 7/208 |
| unsupported_claim_rate | 6/31 | 0/7 | 6/31 | 0/7 |
| core questions answered | 9/60 | 5/60 | 10/60 | 6/60 |
| reads (all cases) | 328 | 303 | 333 | 303 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (7): ntu:deadline, ntu:scholarships.nanyang_global.applicability.nationality, ntu:scholarships.nanyang_global.bond, ntu:scholarships.nanyang_global.coverage.living, ntu:scholarships.nanyang_global.duration, ntu:scholarships.nanyang_global.exists, ntu:scholarships.nanyang_global.renewal

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 1.000 | >= 0.95 | yes |
| off | wrong_scope_claim_rate | 0.000 | <= 0.03 | yes |
| off | cases_over_budget | 0 | == 0 | yes |
| on | claim_precision | 0.941 | >= 0.95 | NO |
| on | wrong_scope_claim_rate | 0.059 | <= 0.03 | NO |
| on | cases_over_budget | 0 | == 0 | yes |

## Wrong claims (on, every repetition)

- delft `tuition`: ours {"amount": 19906.0, "currency": "EUR"} vs {"amount": 20563.0, "currency": "EUR"} (wrong_value) ×2

## Known labels by outcome (on#1)

hit: 18, missed: 52, partial: 2, wrong_value: 1

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| aalto | PARTIALLY_BLOCKED (26/27 failed) | 0/4 | 0/6 | 6 | 4 | 19.8 |
| delft | REACHED (0/35 failed) | 1/4 | 2/6 | 6 | 30 | 46.5 |
| groningen | PARTIALLY_BLOCKED (2/47 failed) | 3/14 | 2/6 | 6 | 53 | 99.5 |
| hku | PARTIALLY_BLOCKED (21/33 failed) | 0/4 | 0/6 | 6 | 20 | 48.6 |
| kaist | PARTIALLY_BLOCKED (4/12 failed) | 0/11 | 0/6 | 1 | 14 | 28.5 |
| ntu | REACHED (7/54 failed) | 8/19 | 4/6 | 4 | 44 | 89.7 |
| toronto | REACHED (18/27 failed) | 0/7 | 0/6 | 6 | 29 | 24.7 |
| ubc | PARTIALLY_BLOCKED (7/50 failed) | 3/4 | 1/6 | 6 | 45 | 77.5 |
| vienna | REACHED (5/37 failed) | 1/4 | 1/6 | 6 | 45 | 55.2 |
| warsaw | PARTIALLY_BLOCKED (2/35 failed) | 2/2 | 0/6 | 6 | 49 | 76.2 |
