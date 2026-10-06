<!-- run 37304786857 (benchmark-capture, expert_paired, ABBA); rule DL-2; provider=exa_mcp decided_by=explicit input extra_args=--deadline-v2 base_args= -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 4/10 | 7/10 | 6/10 | 6/10 |
| claim_precision | 9/9 | 12/13 | 28/32 | 30/34 |
| claim_recall | 7/73 | 10/73 | 14/73 | 16/73 |
| wrong_scope_claim_rate | 0/9 | 1/13 | 4/32 | 4/34 |
| other_scope_claim_rate | 1/10 | 3/16 | 3/41 | 3/43 |
| partial_claim_rate | 0/10 | 0/16 | 6/41 | 6/43 |
| critical_field_coverage | 4/208 | 8/208 | 16/208 | 17/208 |
| unsupported_claim_rate | 0/4 | 0/4 | 6/27 | 6/28 |
| core questions answered | 3/60 | 6/60 | 9/60 | 9/60 |
| reads (all cases) | 297 | 302 | 297 | 312 |

**Stable gains** (6): ntu:scholarships.nanyang_global.applicability.nationality, ntu:scholarships.nanyang_global.bond, ntu:scholarships.nanyang_global.coverage.living, ntu:scholarships.nanyang_global.duration, ntu:scholarships.nanyang_global.exists, ntu:scholarships.nanyang_global.renewal
**Stable losses** (0): none
Unstable (0): none

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 0.923 | >= 0.95 | NO |
| off | wrong_scope_claim_rate | 0.077 | <= 0.03 | NO |
| off | cases_over_budget | 5 | == 0 | NO |
| on | claim_precision | 0.875 | >= 0.95 | NO |
| on | wrong_scope_claim_rate | 0.125 | <= 0.03 | NO |
| on | cases_over_budget | 5 | == 0 | NO |

## Wrong claims (on, every repetition)

- groningen `tuition`: ours {"amount": 19800.0, "currency": "EUR"} vs {"amount": 19800.0, "currency": "EUR"} (wrong_scope) ×2
- ntu `deadline`: ours "2027-01-20" vs "2027-01-20" (wrong_scope) ×6

## Known labels by outcome (on#1)

hit: 14, missed: 55, partial: 2, wrong_scope: 2

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| aalto | BLOCKED (22/22 failed) | 0/4 | 0/6 | 6 | 1 | 15.2 |
| delft | REACHED (0/35 failed) | 1/4 | 1/6 | 6 | 30 | 51.3 |
| groningen | PARTIALLY_BLOCKED (2/47 failed) | 2/14 | 2/6 | 7 | 53 | 96.8 |
| hku | PARTIALLY_BLOCKED (22/33 failed) | 0/4 | 0/6 | 6 | 19 | 54.2 |
| kaist | BLOCKED (9/9 failed) | 0/11 | 0/6 | 1 | 3 | 33.8 |
| ntu | REACHED (7/44 failed) | 7/19 | 4/6 | 4 | 34 | 80.8 |
| toronto | REACHED (31/34 failed) | 0/7 | 0/6 | 5 | 41 | 30.2 |
| ubc | PARTIALLY_BLOCKED (12/47 failed) | 3/4 | 1/6 | 7 | 45 | 78.0 |
| vienna | REACHED (8/40 failed) | 1/4 | 1/6 | 7 | 48 | 55.8 |
| warsaw | PARTIALLY_BLOCKED (1/19 failed) | 0/2 | 0/6 | 4 | 23 | 41.0 |
