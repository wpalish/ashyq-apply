<!-- run 37460377009 (benchmark-capture, expert_paired, ABBA); rule SR-1; provider=exa_mcp decided_by=explicit input extra_args=--search-rate-limit-retry base_args= -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 6/10 | 6/10 | 6/10 | 6/10 |
| claim_precision | 20/20 | 17/17 | 17/17 | 17/17 |
| claim_recall | 13/73 | 12/73 | 12/73 | 12/73 |
| wrong_scope_claim_rate | 0/20 | 0/17 | 0/17 | 0/17 |
| other_scope_claim_rate | 3/23 | 3/20 | 3/20 | 3/20 |
| partial_claim_rate | 0/23 | 0/20 | 0/20 | 0/20 |
| critical_field_coverage | 9/208 | 6/208 | 6/208 | 6/208 |
| unsupported_claim_rate | 0/6 | 0/6 | 0/6 | 0/6 |
| core questions answered | 7/60 | 5/60 | 5/60 | 5/60 |
| reads (all cases) | 316 | 313 | 313 | 313 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (1): ntu:deadline

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

hit: 12, missed: 61

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| aalto | PARTIALLY_BLOCKED (26/27 failed) | 0/4 | 0/6 | 6 | 4 | 25.5 |
| delft | REACHED (0/35 failed) | 1/4 | 1/6 | 6 | 30 | 51.3 |
| groningen | PARTIALLY_BLOCKED (2/47 failed) | 3/14 | 2/6 | 6 | 53 | 96.7 |
| hku | PARTIALLY_BLOCKED (13/33 failed) | 1/4 | 0/6 | 6 | 25 | 41.9 |
| kaist | REACHED (3/12 failed) | 0/11 | 0/6 | 1 | 15 | 20.2 |
| ntu | REACHED (7/27 failed) | 1/19 | 0/6 | 1 | 19 | 30.8 |
| toronto | REACHED (18/27 failed) | 0/7 | 0/6 | 6 | 30 | 31.5 |
| ubc | PARTIALLY_BLOCKED (7/50 failed) | 3/4 | 1/6 | 6 | 44 | 73.5 |
| vienna | REACHED (5/37 failed) | 1/4 | 1/6 | 6 | 44 | 54.8 |
| warsaw | PARTIALLY_BLOCKED (2/35 failed) | 2/2 | 0/6 | 6 | 49 | 76.4 |
