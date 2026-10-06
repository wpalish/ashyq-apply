<!-- run 37318266068 (benchmark-capture, expert_paired, ABBA); rule TY-1; provider=exa_mcp decided_by=explicit input extra_args=--tuition-row-year base_args= -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 4/10 | 7/10 | 5/10 | 6/10 |
| claim_precision | 29/30 | 12/13 | 29/30 | 15/16 |
| claim_recall | 15/73 | 10/73 | 15/73 | 10/73 |
| wrong_scope_claim_rate | 1/30 | 1/13 | 1/30 | 1/16 |
| other_scope_claim_rate | 3/39 | 3/16 | 3/39 | 3/19 |
| partial_claim_rate | 6/39 | 0/16 | 6/39 | 0/19 |
| critical_field_coverage | 14/208 | 6/208 | 16/208 | 6/208 |
| unsupported_claim_rate | 6/28 | 0/4 | 6/28 | 0/7 |
| core questions answered | 8/60 | 5/60 | 9/60 | 5/60 |
| reads (all cases) | 312 | 301 | 315 | 303 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (7): ntu:scholarships.nanyang_global.applicability.nationality, ntu:scholarships.nanyang_global.bond, ntu:scholarships.nanyang_global.coverage.living, ntu:scholarships.nanyang_global.duration, ntu:scholarships.nanyang_global.exists, ntu:scholarships.nanyang_global.renewal, ubc:programme.exists

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 0.923 | >= 0.95 | NO |
| off | wrong_scope_claim_rate | 0.077 | <= 0.03 | NO |
| off | cases_over_budget | 6 | == 0 | NO |
| on | claim_precision | 0.938 | >= 0.95 | NO |
| on | wrong_scope_claim_rate | 0.062 | <= 0.03 | NO |
| on | cases_over_budget | 6 | == 0 | NO |

## Wrong claims (on, every repetition)

- groningen `tuition`: ours {"amount": 19800.0, "currency": "EUR"} vs {"amount": 19800.0, "currency": "EUR"} (wrong_scope) ×2

## Known labels by outcome (on#1)

hit: 15, missed: 55, partial: 2, wrong_scope: 1

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| aalto | PARTIALLY_BLOCKED (26/27 failed) | 0/4 | 0/6 | 6 | 4 | 23.1 |
| delft | REACHED (0/35 failed) | 1/4 | 1/6 | 6 | 30 | 45.0 |
| groningen | PARTIALLY_BLOCKED (2/47 failed) | 2/14 | 2/6 | 7 | 53 | 90.1 |
| hku | PARTIALLY_BLOCKED (21/33 failed) | 0/4 | 0/6 | 6 | 20 | 53.4 |
| kaist | BLOCKED (9/9 failed) | 0/11 | 0/6 | 1 | 3 | 37.1 |
| ntu | REACHED (7/44 failed) | 7/19 | 3/6 | 4 | 33 | 76.1 |
| toronto | REACHED (18/27 failed) | 0/7 | 0/6 | 6 | 29 | 25.5 |
| ubc | PARTIALLY_BLOCKED (7/38 failed) | 2/4 | 1/6 | 4 | 35 | 62.9 |
| vienna | REACHED (7/41 failed) | 1/4 | 1/6 | 7 | 48 | 60.9 |
| warsaw | PARTIALLY_BLOCKED (2/40 failed) | 2/2 | 1/6 | 7 | 60 | 103.1 |
