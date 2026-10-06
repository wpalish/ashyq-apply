<!-- run 37434994035 (benchmark-capture, expert_paired, ABBA); rule EU-1; provider=exa_mcp decided_by=explicit input extra_args=--euro-grouping base_args= -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 4/10 | 4/10 | 5/10 | 5/10 |
| claim_precision | 17/17 | 16/16 | 17/17 | 15/15 |
| claim_recall | 12/73 | 11/73 | 12/73 | 10/73 |
| wrong_scope_claim_rate | 0/17 | 0/16 | 0/17 | 0/15 |
| other_scope_claim_rate | 3/20 | 3/19 | 3/20 | 3/18 |
| partial_claim_rate | 0/20 | 0/19 | 0/20 | 0/18 |
| critical_field_coverage | 6/208 | 6/208 | 6/208 | 5/208 |
| unsupported_claim_rate | 0/6 | 0/6 | 0/6 | 0/5 |
| core questions answered | 5/60 | 5/60 | 5/60 | 5/60 |
| reads (all cases) | 320 | 317 | 318 | 320 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (0): none

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 1.000 | >= 0.95 | yes |
| off | wrong_scope_claim_rate | 0.000 | <= 0.03 | yes |
| off | cases_over_budget | 8 | == 0 | NO |
| on | claim_precision | 1.000 | >= 0.95 | yes |
| on | wrong_scope_claim_rate | 0.000 | <= 0.03 | yes |
| on | cases_over_budget | 7 | == 0 | NO |

## Wrong claims (on, every repetition)

- none

## Known labels by outcome (on#1)

hit: 12, missed: 61

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| aalto | BLOCKED (27/27 failed) | 0/4 | 0/6 | 6 | 1 | 13.9 |
| delft | REACHED (0/35 failed) | 1/4 | 1/6 | 6 | 29 | 45.8 |
| groningen | PARTIALLY_BLOCKED (3/51 failed) | 3/14 | 2/6 | 7 | 60 | 112.0 |
| hku | PARTIALLY_BLOCKED (15/35 failed) | 1/4 | 0/6 | 7 | 25 | 48.3 |
| kaist | REACHED (3/12 failed) | 0/11 | 0/6 | 1 | 15 | 19.9 |
| ntu | REACHED (7/27 failed) | 1/19 | 0/6 | 1 | 19 | 31.9 |
| toronto | REACHED (18/27 failed) | 0/7 | 0/6 | 6 | 30 | 25.4 |
| ubc | PARTIALLY_BLOCKED (13/53 failed) | 3/4 | 1/6 | 7 | 43 | 71.2 |
| vienna | REACHED (8/40 failed) | 1/4 | 1/6 | 7 | 47 | 60.1 |
| warsaw | unknown (0/0 failed) | 2/2 | 0/6 | 6 | 49 | 115.0 |
