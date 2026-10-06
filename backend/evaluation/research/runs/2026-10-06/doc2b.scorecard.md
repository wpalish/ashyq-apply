<!-- run 37354873961 (benchmark-capture, expert_paired, ABBA); rule DOC-2; provider=exa_mcp decided_by=explicit input extra_args=--document-rules-v2 base_args=--with-documents 90 --document-leads -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 1/10 | 1/10 | 1/10 | 1/10 |
| claim_precision | 17/17 | 17/17 | 23/23 | 23/23 |
| claim_recall | 6/73 | 6/73 | 8/73 | 8/73 |
| wrong_scope_claim_rate | 0/17 | 0/17 | 0/23 | 0/23 |
| other_scope_claim_rate | 3/20 | 3/20 | 3/26 | 3/26 |
| partial_claim_rate | 0/20 | 0/20 | 0/26 | 0/26 |
| critical_field_coverage | 4/208 | 4/208 | 6/208 | 6/208 |
| unsupported_claim_rate | 0/1 | 0/1 | 0/9 | 0/9 |
| core questions answered | 2/18 | 2/18 | 2/18 | 2/18 |
| reads (all cases) | 74 | 74 | 74 | 74 |

**Stable gains** (2): groningen:documents.admission.secondary_diploma.completed, groningen:documents.admission.secondary_diploma.not_completed
**Stable losses** (0): none
Unstable (0): none

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

hit: 8, missed: 65

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| groningen | PARTIALLY_BLOCKED (2/37 failed) | 7/14 | 2/6 | 5 | 42 | 73.2 |
| ntu | REACHED (7/27 failed) | 1/19 | 0/6 | 2 | 19 | 30.7 |
| toronto | REACHED (11/11 failed) | 0/7 | 0/6 | 4 | 13 | 12.7 |
