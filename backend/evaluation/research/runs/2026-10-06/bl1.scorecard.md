<!-- run 37294928291 (benchmark-capture, expert_paired, ABBA); rule BL-1; provider=exa_mcp decided_by=explicit input extra_args=--shared-query-budget base_args= -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 5/10 | 5/10 | 6/10 | 5/10 |
| claim_precision | 34/35 | 13/14 | 34/35 | 11/12 |
| claim_recall | 17/73 | 11/73 | 17/73 | 10/73 |
| wrong_scope_claim_rate | 1/35 | 1/14 | 1/35 | 1/12 |
| other_scope_claim_rate | 3/44 | 3/17 | 3/44 | 3/15 |
| partial_claim_rate | 6/44 | 0/17 | 6/44 | 0/15 |
| critical_field_coverage | 16/208 | 6/208 | 16/208 | 8/208 |
| unsupported_claim_rate | 6/31 | 0/4 | 6/30 | 0/4 |
| core questions answered | 8/60 | 5/60 | 8/60 | 6/60 |
| reads (all cases) | 331 | 316 | 318 | 299 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (6): ntu:scholarships.nanyang_global.applicability.nationality, ntu:scholarships.nanyang_global.bond, ntu:scholarships.nanyang_global.coverage.living, ntu:scholarships.nanyang_global.duration, ntu:scholarships.nanyang_global.exists, ntu:scholarships.nanyang_global.renewal

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 0.929 | >= 0.95 | NO |
| off | wrong_scope_claim_rate | 0.071 | <= 0.03 | NO |
| off | cases_over_budget | 10 | == 0 | NO |
| on | claim_precision | 0.917 | >= 0.95 | NO |
| on | wrong_scope_claim_rate | 0.083 | <= 0.03 | NO |
| on | cases_over_budget | 0 | == 0 | yes |

## Wrong claims (on, every repetition)

- groningen `tuition`: ours {"amount": 19800.0, "currency": "EUR"} vs {"amount": 19800.0, "currency": "EUR"} (wrong_scope) ×2

## Known labels by outcome (on#1)

hit: 17, missed: 53, partial: 2, wrong_scope: 1

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| aalto | BLOCKED (27/27 failed) | 0/4 | 0/6 | 6 | 1 | 17.6 |
| delft | REACHED (0/35 failed) | 1/4 | 1/6 | 6 | 30 | 45.8 |
| groningen | PARTIALLY_BLOCKED (2/47 failed) | 2/14 | 2/6 | 6 | 53 | 106.4 |
| hku | PARTIALLY_BLOCKED (10/28 failed) | 1/4 | 0/6 | 6 | 25 | 42.3 |
| kaist | REACHED (3/12 failed) | 0/11 | 0/6 | 1 | 15 | 19.2 |
| ntu | REACHED (7/44 failed) | 7/19 | 3/6 | 4 | 34 | 70.8 |
| toronto | REACHED (18/27 failed) | 0/7 | 0/6 | 6 | 30 | 28.7 |
| ubc | PARTIALLY_BLOCKED (11/51 failed) | 3/4 | 1/6 | 6 | 40 | 70.5 |
| vienna | REACHED (5/37 failed) | 1/4 | 1/6 | 6 | 44 | 55.4 |
| warsaw | PARTIALLY_BLOCKED (2/34 failed) | 2/2 | 0/6 | 5 | 46 | 77.5 |
