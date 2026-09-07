# T04 / A1 — ashyq-developer output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-developer
- INVOCATION_REF: agent_496c44cd-bd67-4a6c-a6f2-727b762356b1 (real runtime agentId)
- STATUS: DONE
- QA_COMMIT_SHA: d45a9cb4712a2c304f6ae83bcbca97f8f6f11663
- CANDIDATE_COMMIT_SHA: 3bdc0702dd25e80db16916a00d4e5710dbd65381 (заморожен; push/amend нет)

## CHANGED_FILES
backend/app/schemas/result.py (CostBasis Literal + FundingGap.cost_basis default None + missing_categories default_factory=list); backend/app/domain/costs.py (_missing_core_categories/_cost_basis helpers; partial → computable=False, gap=None, gap_low/high=None, total_cost=known subtotal, warnings называют отсутствующие; known zero = известная категория; published total → прежние правила; unknown → basis=None); backend/tests/test_costs.py (fixture-миграции); frontend/src/types.ts (CostBasis + обязательные поля FundingGap); frontend/src/components/ResultDetail.tsx (partial-ветка: "Cost of attendance known so far", ≥ subtotal, чипы missing, lower-bound wording). runner/funding/scoring не тронуты.

## GATES (реальные)
- ruff format/check → 0 (153 files)
- mypy app tests → 0 (153 files)
- pytest tests/test_costs.py tests/test_funding_classification.py → 42 passed
- Де-рискинг read-only: test_pipeline+test_api → 94 passed; ranking/scoring/entitlements/profile_fields → 130 passed; test_frontend_contract → 24 passed
- Frontend: typecheck 0, lint 0, npm test 164 passed
- FULL SUITE (--cov-fail-under=92) НЕ запускался — heavy slot диспетчера, pending на VERIFY

## MIGRATION_NOTES (координатором утверждено)
Контракт сделал частичными fixture 6 тестов (не 3 из packet): мигрированы с сохранением структуры assertions, числа пересчитаны по полным fixture costs(tuition, mandatory_fees=2000, housing=12000, meals=6000): test_gap_is_cost_minus_aid, test_aid_exceeding_cost_reports_zero_and_says_so, test_a_percentage_of_tuition_award_is_resolved_against_tuition, test_need_based_aid_is_excluded_from_the_arithmetic, TestStacking x2 (числа: 12000→20000, award 30000→50000, 8000→16000, 20000→40000). test_an_award_with_no_published_amount_is_excluded_and_named НЕ мигрирован (partial-возврат после award-разрешения — warning "Mystery Grant" сохраняется). test_no_cost_data_means_no_gap и mixed-year refusal не тронуты (последнему поля добавлены аддитивно). QA RED-класс — ноль правок (нет в diff).

## RISKS для VERIFY/review
runner.py residual (subtotal в classify) — осознанный residual T05-T07; T09 e2e-ассерты tuition-only программ могут увидеть partial-отображение — проверить до merge; rollback-окно extra="forbid".

## NEXT
VERIFY_CANDIDATE: full pytest --cov-fail-under=92 + seed_demo порядок (Groningen #1, UBC OUT_OF_BUDGET) + reviewer/security на 3bdc0702.
