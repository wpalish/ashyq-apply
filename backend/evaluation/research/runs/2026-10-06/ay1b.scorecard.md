<!-- run 37324275471 (benchmark-capture, expert_paired, ABBA); rule AY-1; provider=exa_mcp decided_by=explicit input extra_args=--applicant-academic-year base_args=--tuition-row-year -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 6/10 | 6/10 | 6/10 | 5/10 |
| claim_precision | 13/14 | 13/14 | 12/13 | 13/14 |
| claim_recall | 11/73 | 11/73 | 11/73 | 11/73 |
| wrong_scope_claim_rate | 1/14 | 1/14 | 1/13 | 1/14 |
| other_scope_claim_rate | 3/17 | 3/17 | 3/16 | 3/17 |
| partial_claim_rate | 0/17 | 0/17 | 0/16 | 0/17 |
| critical_field_coverage | 6/208 | 6/208 | 6/208 | 6/208 |
| unsupported_claim_rate | 0/4 | 0/4 | 0/4 | 0/4 |
| core questions answered | 6/60 | 6/60 | 5/60 | 6/60 |
| reads (all cases) | 338 | 325 | 313 | 330 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (0): none

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 0.929 | >= 0.95 | NO |
| off | wrong_scope_claim_rate | 0.071 | <= 0.03 | NO |
| off | cases_over_budget | 9 | == 0 | NO |
| on | claim_precision | 0.923 | >= 0.95 | NO |
| on | wrong_scope_claim_rate | 0.077 | <= 0.03 | NO |
| on | cases_over_budget | 8 | == 0 | NO |

## Wrong claims (on, every repetition)

- groningen `tuition`: ours {"amount": 19800.0, "currency": "EUR"} vs {"amount": 19800.0, "currency": "EUR"} (wrong_scope) ×2

## Known labels by outcome (on#1)

hit: 11, missed: 61, wrong_scope: 1

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| aalto | BLOCKED (27/27 failed) | 0/4 | 0/6 | 6 | 1 | 26.0 |
| delft | REACHED (0/22 failed) | 1/4 | 1/6 | 5 | 17 | 25.2 |
| groningen | PARTIALLY_BLOCKED (3/51 failed) | 2/14 | 2/6 | 7 | 60 | 107.9 |
| hku | PARTIALLY_BLOCKED (16/35 failed) | 1/4 | 0/6 | 7 | 25 | 47.0 |
| kaist | REACHED (3/12 failed) | 0/11 | 0/6 | 1 | 15 | 20.0 |
| ntu | REACHED (7/27 failed) | 1/19 | 0/6 | 1 | 19 | 30.5 |
| toronto | REACHED (32/34 failed) | 0/7 | 0/6 | 6 | 39 | 32.5 |
| ubc | PARTIALLY_BLOCKED (7/45 failed) | 3/4 | 1/6 | 5 | 44 | 71.0 |
| vienna | REACHED (8/40 failed) | 1/4 | 1/6 | 7 | 48 | 60.7 |
| warsaw | PARTIALLY_BLOCKED (2/34 failed) | 2/2 | 0/6 | 6 | 45 | 70.3 |
