# Scorecard — corpus 2026-10-17.heldout-reviewed1

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 0/9 | 1/9 | 0/9 | 0/9 |
| claim_precision | 0/3 | 0/3 | 0/3 | 0/3 |
| claim_recall | 0/25 | 0/25 | 0/25 | 0/25 |
| wrong_scope_claim_rate | 3/3 | 3/3 | 3/3 | 3/3 |
| other_scope_claim_rate | 0/3 | 0/3 | 0/3 | 0/3 |
| partial_claim_rate | 0/3 | 0/3 | 0/3 | 0/3 |
| critical_field_coverage | 8/47 | 8/47 | 8/47 | 8/47 |
| unsupported_claim_rate | 0/0 | 0/0 | 0/0 | 0/0 |
| core questions answered | 11/54 | 11/54 | 11/54 | 11/54 |
| known core answered | 0/23 | 0/23 | 0/23 | 0/23 |
| reads (all cases) | 312 | 313 | 321 | 309 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (0): none

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 0.000 | >= 0.95 | NO |
| off | wrong_scope_claim_rate | 1.000 | <= 0.03 | NO |
| off | cases_over_budget | 0 | == 0 | yes |
| on | claim_precision | 0.000 | >= 0.95 | NO |
| on | wrong_scope_claim_rate | 1.000 | <= 0.03 | NO |
| on | cases_over_budget | 0 | == 0 | yes |

## Wrong claims (on, every repetition)

- nu `ielts.overall`: ours 5.5 vs 6.0 (wrong_value) ×2
- nu `ielts.subscores`: ours {"writing": 6.0, "speaking": 5.5} vs {"listening": 5.5, "reading": 5.5, "speaking": 5.5, "writing": 6.0} (wrong_value) ×2
- tartu `ielts.overall`: ours 6.0 vs 6.0 (wrong_scope) ×2

## Known labels by outcome (on#1)

missed: 22, wrong_scope: 1, wrong_value: 2

## Per case (on#1)

| case | access | hits | core | core known | queries | reads | s | 1st query s |
|---|---|---|---|---|---|---|---|---|
| charles | REACHED (3/27 failed) | 0/3 | 2/6 | 0/3 | 6 | 35 | 58.0 | 15.8 |
| masaryk | REACHED (1/34 failed) | 0/3 | 0/6 | 0/3 | 6 | 27 | 76.8 | 20.6 |
| metu | REACHED (3/18 failed) | 0/2 | 0/6 | 0/2 | 6 | 28 | 89.6 | 12.1 |
| nu | REACHED (0/15 failed) | 0/5 | 4/6 | 0/4 | 4 | 31 | 94.9 | 18.2 |
| polimi | REACHED (1/38 failed) | 0/1 | 0/6 | 0/1 | 6 | 40 | 69.8 | 31.1 |
| sabanci | REACHED (3/45 failed) | 0/4 | 3/6 | 0/4 | 5 | 44 | 56.3 | 28.4 |
| tartu | PARTIALLY_BLOCKED (3/35 failed) | 0/4 | 1/6 | 0/3 | 4 | 42 | 83.7 | 28.3 |
| tum | REACHED (0/35 failed) | 0/2 | 0/6 | 0/2 | 6 | 39 | 62.1 | 34.0 |
| vilnius | REACHED (1/41 failed) | 0/1 | 1/6 | 0/1 | 6 | 35 | 52.8 | 26.6 |
