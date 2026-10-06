<!-- run 37348468613 (benchmark-capture, expert_paired, ABBA); rule DOC-3; provider=exa_mcp decided_by=explicit input extra_args=--document-leads base_args=--with-documents 90 -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 1/10 | 2/10 | 2/10 | 2/10 |
| claim_precision | 26/26 | 26/26 | 26/26 | 26/26 |
| claim_recall | 11/73 | 11/73 | 11/73 | 11/73 |
| wrong_scope_claim_rate | 0/26 | 0/26 | 0/26 | 0/26 |
| other_scope_claim_rate | 3/35 | 3/35 | 3/35 | 3/35 |
| partial_claim_rate | 6/35 | 6/35 | 6/35 | 6/35 |
| critical_field_coverage | 13/208 | 13/208 | 13/208 | 13/208 |
| unsupported_claim_rate | 6/25 | 6/25 | 6/25 | 6/25 |
| core questions answered | 6/18 | 6/18 | 6/18 | 6/18 |
| reads (all cases) | 117 | 124 | 124 | 124 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (0): none

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 1.000 | >= 0.95 | yes |
| off | wrong_scope_claim_rate | 0.000 | <= 0.03 | yes |
| off | cases_over_budget | 2 | == 0 | NO |
| on | claim_precision | 1.000 | >= 0.95 | yes |
| on | wrong_scope_claim_rate | 0.000 | <= 0.03 | yes |
| on | cases_over_budget | 2 | == 0 | NO |

## Wrong claims (on, every repetition)

- none

## Known labels by outcome (on#1)

hit: 11, missed: 60, partial: 2

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| groningen | PARTIALLY_BLOCKED (3/51 failed) | 3/14 | 2/6 | 7 | 60 | 108.0 |
| ntu | REACHED (7/44 failed) | 8/19 | 4/6 | 4 | 34 | 73.0 |
| toronto | REACHED (18/27 failed) | 0/7 | 0/6 | 6 | 30 | 25.2 |
