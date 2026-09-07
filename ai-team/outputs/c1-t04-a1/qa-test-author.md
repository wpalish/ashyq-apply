# T04 / A1 — ashyq-qa TEST_AUTHOR output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-qa, PHASE: TEST_AUTHOR
- INVOCATION_REF: agent_3e981036-d921-46f4-9025-120a6e56fa3b (real runtime agentId)
- STATUS: TESTS_READY
- CHECKED_SHA: f7f14b28c43afe20df01ad38a26964c397f393fc (ветка ai/c1/t04/qa)
- QA_COMMIT_SHA: d45a9cb4712a2c304f6ae83bcbca97f8f6f11663

## REPRODUCED_BUGS (прямое воспроизведение до написания тестов)
compute_funding_gap(costs(tuition=10000), [award(10000, FULL_TUITION)]) → computable=True, gap=0 USD, warnings=[]; FundingGap не имеет cost_basis/missing_categories. Поведенческое воспроизведение, не env-ошибка.

## RED_EVIDENCE
- pytest tests/test_costs.py tests/test_funding_classification.py -q → exit 1: 4 failed, 38 passed
- pytest tests/test_costs.py::TestPartialCostIsNotFullCost -v → exit 1, 4 failed

RED-тесты (TestPartialCostIsNotFullCost, backend/tests/test_costs.py):
1. test_tuition_only_costs_with_a_matching_award_do_not_report_a_zero_gap — assertion-level (assert True is False на computable is False)
2. test_an_explicit_zero_is_known_but_a_missing_key_is_not — contract-field-level (AttributeError cost_basis)
3. test_a_published_total_keeps_the_old_rules_even_with_partial_itemisation — contract-field-level
4. test_a_legacy_funding_gap_payload_validates_with_defaults — contract-field-level (допустимый RED по контракту)

## Кодифицированные assertions
F01-сценарий: computable=False, gap None, gap_low/high None, basis=="itemised_partial", {mandatory_fees,housing,meals} ⊆ missing_categories, total_cost.amount==10000, warnings называют housing/meals. Known zero meals=0 → complete/missing=[]; без ключа meals → partial/missing=["meals"]/subtotal 54000. Published total → published_total, прежняя арифметика (gap 19000). Legacy dict → дефолты, model_dump содержит оба поля.

## GREEN_GUARDS
Новых зелёных на baseline нет. Существующие 38 (test_costs без изменений + test_funding_classification целиком) — зелёные отдельным прогоном exit 0. Fixture-миграция 3 тестов — работа developer'а по контракту.

## CHANGED_FILES / ENV
backend/tests/test_costs.py — единственный файл (git show --stat). ruff format/check exit 0. Logs: outputs/c1-t04-a1/qa_test_author_red_full.log, t04_qa_red.log, t04_qa_preexisting.log.

## UNTESTED_RISKS
warnings-текст толерантный; consumers (ranking_v2, routes_results, tabular, types.ts) и classify-путь — вне scope (T05-T07); полный suite — heavy slot диспетчера.

## NEXT
Developer от d45a9cb4; затем VERIFY_CANDIDATE в новой worktree.
