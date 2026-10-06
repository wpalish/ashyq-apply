<!-- run 37313336309 (benchmark-capture, expert_paired, ABBA); rule DL-2; provider=exa_mcp decided_by=explicit input extra_args=--deadline-v2 base_args= -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 5/10 | 6/10 | 6/10 | 6/10 |
| claim_precision | 33/34 | 34/35 | 17/18 | 33/34 |
| claim_recall | 16/73 | 17/73 | 11/73 | 16/73 |
| wrong_scope_claim_rate | 1/34 | 1/35 | 1/18 | 1/34 |
| other_scope_claim_rate | 3/43 | 3/44 | 3/21 | 3/43 |
| partial_claim_rate | 6/43 | 6/44 | 0/21 | 6/43 |
| critical_field_coverage | 14/208 | 16/208 | 9/208 | 14/208 |
| unsupported_claim_rate | 6/30 | 6/30 | 0/6 | 6/30 |
| core questions answered | 8/60 | 9/60 | 7/60 | 8/60 |
| reads (all cases) | 323 | 328 | 288 | 321 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (2): hku:programme.exists, ntu:deadline

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 0.971 | >= 0.95 | yes |
| off | wrong_scope_claim_rate | 0.029 | <= 0.03 | yes |
| off | cases_over_budget | 6 | == 0 | NO |
| on | claim_precision | 0.944 | >= 0.95 | NO |
| on | wrong_scope_claim_rate | 0.056 | <= 0.03 | NO |
| on | cases_over_budget | 6 | == 0 | NO |

## Wrong claims (on, every repetition)

- groningen `tuition`: ours {"amount": 19800.0, "currency": "EUR"} vs {"amount": 19800.0, "currency": "EUR"} (wrong_scope) ×2

## Known labels by outcome (on#1)

hit: 11, missed: 61, wrong_scope: 1

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| aalto | BLOCKED (27/27 failed) | 0/4 | 0/6 | 6 | 1 | 25.2 |
| delft | REACHED (0/22 failed) | 1/4 | 1/6 | 4 | 17 | 25.0 |
| groningen | PARTIALLY_BLOCKED (2/47 failed) | 2/14 | 2/6 | 5 | 54 | 87.5 |
| hku | PARTIALLY_BLOCKED (5/15 failed) | 0/4 | 0/6 | 4 | 12 | 15.0 |
| kaist | REACHED (3/12 failed) | 0/11 | 0/6 | 1 | 15 | 19.3 |
| ntu | REACHED (7/36 failed) | 2/19 | 2/6 | 4 | 23 | 48.0 |
| toronto | REACHED (18/27 failed) | 0/7 | 0/6 | 6 | 30 | 25.0 |
| ubc | PARTIALLY_BLOCKED (9/52 failed) | 3/4 | 1/6 | 7 | 47 | 76.9 |
| vienna | REACHED (5/37 failed) | 1/4 | 1/6 | 7 | 44 | 71.3 |
| warsaw | PARTIALLY_BLOCKED (2/31 failed) | 2/2 | 0/6 | 6 | 45 | 67.0 |
