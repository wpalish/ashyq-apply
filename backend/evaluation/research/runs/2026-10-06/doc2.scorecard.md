<!-- run 37344242698 (benchmark-capture, expert_paired, ABBA); rule DOC-2; provider=exa_mcp decided_by=explicit input extra_args=--document-rules-v2 base_args=--with-documents 90 -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 2/10 | 1/10 | 1/10 | 1/10 |
| claim_precision | 5/5 | 5/5 | 5/5 | 5/5 |
| claim_recall | 4/73 | 4/73 | 4/73 | 4/73 |
| wrong_scope_claim_rate | 0/5 | 0/5 | 0/5 | 0/5 |
| other_scope_claim_rate | 3/8 | 3/8 | 3/8 | 3/8 |
| partial_claim_rate | 0/8 | 0/8 | 0/8 | 0/8 |
| critical_field_coverage | 2/208 | 2/208 | 2/208 | 2/208 |
| unsupported_claim_rate | 0/1 | 0/1 | 0/1 | 0/1 |
| core questions answered | 2/18 | 2/18 | 2/18 | 2/18 |
| reads (all cases) | 86 | 74 | 74 | 74 |

**Stable gains** (0): none
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

hit: 4, missed: 69

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| groningen | PARTIALLY_BLOCKED (2/37 failed) | 3/14 | 2/6 | 4 | 42 | 72.8 |
| ntu | REACHED (7/27 failed) | 1/19 | 0/6 | 2 | 19 | 30.6 |
| toronto | REACHED (11/11 failed) | 0/7 | 0/6 | 5 | 13 | 12.8 |
