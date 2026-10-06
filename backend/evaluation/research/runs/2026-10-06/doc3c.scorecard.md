<!-- run 37353500432 (benchmark-capture, expert_paired, ABBA); rule DOC-3; provider=exa_mcp decided_by=explicit input extra_args=--document-leads base_args=--with-documents 90 -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 1/10 | 1/10 | 2/10 | 1/10 |
| claim_precision | 5/5 | 5/5 | 17/17 | 17/17 |
| claim_recall | 4/73 | 4/73 | 6/73 | 6/73 |
| wrong_scope_claim_rate | 0/5 | 0/5 | 0/17 | 0/17 |
| other_scope_claim_rate | 3/8 | 3/8 | 3/20 | 3/20 |
| partial_claim_rate | 0/8 | 0/8 | 0/20 | 0/20 |
| critical_field_coverage | 2/208 | 2/208 | 4/208 | 4/208 |
| unsupported_claim_rate | 0/1 | 0/1 | 0/1 | 0/1 |
| core questions answered | 2/18 | 2/18 | 2/18 | 2/18 |
| reads (all cases) | 89 | 74 | 85 | 74 |

**Stable gains** (2): groningen:documents.admission.transcript.completed, groningen:documents.admission.transcript.not_completed
**Stable losses** (0): none
Unstable (0): none

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 1.000 | >= 0.95 | yes |
| off | wrong_scope_claim_rate | 0.000 | <= 0.03 | yes |
| off | cases_over_budget | 1 | == 0 | NO |
| on | claim_precision | 1.000 | >= 0.95 | yes |
| on | wrong_scope_claim_rate | 0.000 | <= 0.03 | yes |
| on | cases_over_budget | 1 | == 0 | NO |

## Wrong claims (on, every repetition)

- none

## Known labels by outcome (on#1)

hit: 6, missed: 67

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| groningen | PARTIALLY_BLOCKED (2/47 failed) | 5/14 | 2/6 | 7 | 53 | 109.3 |
| ntu | REACHED (7/27 failed) | 1/19 | 0/6 | 2 | 19 | 28.6 |
| toronto | REACHED (11/11 failed) | 0/7 | 0/6 | 5 | 13 | 12.8 |
