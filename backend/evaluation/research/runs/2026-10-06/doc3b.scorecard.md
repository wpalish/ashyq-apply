<!-- run 37351314325 (benchmark-capture, expert_paired, ABBA); rule DOC-3; provider=exa_mcp decided_by=explicit input extra_args=--document-leads base_args=--with-documents 90 -->
# Scorecard — corpus 2026-10-05.reviewed9

| metric | off#1 | off#2 | on#1 | on#2 |
|---|---|---|---|---|
| programme_page_recall | 1/10 | 2/10 | 1/10 | 2/10 |
| claim_precision | 20/20 | 23/23 | 23/23 | 35/35 |
| claim_recall | 7/73 | 10/73 | 10/73 | 12/73 |
| wrong_scope_claim_rate | 0/20 | 0/23 | 0/23 | 0/35 |
| other_scope_claim_rate | 1/27 | 3/32 | 3/32 | 3/44 |
| partial_claim_rate | 6/27 | 6/32 | 6/32 | 6/44 |
| critical_field_coverage | 11/208 | 13/208 | 13/208 | 15/208 |
| unsupported_claim_rate | 6/25 | 6/25 | 6/25 | 6/25 |
| core questions answered | 3/18 | 5/18 | 5/18 | 5/18 |
| reads (all cases) | 111 | 123 | 123 | 123 |

**Stable gains** (0): none
**Stable losses** (0): none
Unstable (2): groningen:documents.admission.transcript.completed, groningen:documents.admission.transcript.not_completed

## Targets (worst repetition)

| arm | metric | worst | target | met |
|---|---|---|---|---|
| off | claim_precision | 1.000 | >= 0.95 | yes |
| off | wrong_scope_claim_rate | 0.000 | <= 0.03 | yes |
| off | cases_over_budget | 1 | == 0 | NO |
| on | claim_precision | 1.000 | >= 0.95 | yes |
| on | wrong_scope_claim_rate | 0.000 | <= 0.03 | yes |
| on | cases_over_budget | 2 | == 0 | NO |

## Wrong claims (on, every repetition)

- none

## Known labels by outcome (on#1)

hit: 10, missed: 61, partial: 2

## Per case (on#1)

| case | access | hits | core | queries | reads | s |
|---|---|---|---|---|---|---|
| groningen | unknown (0/0 failed) | 3/14 | 2/6 | 7 | 60 | 115.0 |
| ntu | REACHED (7/44 failed) | 7/19 | 3/6 | 4 | 33 | 70.0 |
| toronto | REACHED (18/27 failed) | 0/7 | 0/6 | 6 | 30 | 24.4 |
