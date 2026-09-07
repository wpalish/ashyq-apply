# T18 / A1 — ashyq-qa TEST_AUTHOR output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-qa, PHASE: TEST_AUTHOR
- INVOCATION_REF: agent_f9a36974-3d30-4749-bb3c-b70f382df2b5 (real runtime agentId)
- STATUS: TESTS_READY
- CHECKED_SHA: 1e9f841ba686d27fc28271f9592ad449c0b35004 (ветка ai/c1/t18/qa)
- QA_COMMIT_SHA: 18c4a901ad95fa59f9f83e3bbdae0e2d98436fea

## BASELINE: test_live_regressions + test_live_discovery = 171 passed, exit 0 (61+110)

## RED_EVIDENCE (11 failed / 176 passed, exit 1; assertion-уровень, не import/env)
- A1 (TestTheRunExplainsItsPages): test_a_read_page_leaves_its_page_type_on_the_run (page_types отбрасывается раннером); test_an_unreadable_page_is_named_as_unreadable (только prose-ошибка без категории); test_a_page_matching_no_pattern_is_reported_as_no_pattern_match (молчание)
- A2: test_a_classifier_rejected_page_is_named_as_such (NAVIGATION видна как prose, не категоризирована)
- B1: test_the_tenge_sign_is_read_as_kzt, test_the_kzt_code_is_read_as_kzt (parse_money → None), test_a_tuition_line_in_tenge_yields_a_tuition_claim (claims=[]), test_a_tenge_fees_page_yields_a_tuition_breakdown, test_a_kzt_code_fees_page_yields_a_tuition_breakdown (breakdown.items пуст)
- B2: test_ielts_before_overall_yields_the_band, test_a_programme_page_stating_ielts_6_5_overall_yields_the_claim (из claims только PROGRAM_EXISTS)
Логи: /tmp/qa_t18_combined.log, /tmp/qa_t18_new3.log

## GREEN_GUARDS (5 новых + 171 существующих)
C1 scholarship не tuition (2 теста); C2 IELTS без числа — нет claim; C3 нет паттерна → unresolved/error с причиной, никогда zero; existing currency vocabulary (USD/EUR) парсится; 171 существующих зелёные.

## CHANGED_FILES (test scope)
backend/tests/test_live_extraction.py (новый, 16 тестов); backend/tests/fixtures/qa_t18/ (8 синтетических HTML, помечены «QA SYNTHETIC FIXTURE (T18/L01)»). ruff чисто; production/canary не тронуты; реального HTTP нет.

## УТОЧНЕНИЯ КООРДИНАТОРУ (не блокеры)
1. A1/A2 требуют per-page категории (unreadable/classifier-rejected + page_type / no-pattern-match) в persisted-диагностике прогона — run.errors + run.unknowns (существующие JSON-колонки, доступны canary). Реализация умещается в runner.py + adapters/** в рамках WRITE_SCOPE.
2. Уточнение диагностики planner: unreadable/classifier-rejected на baseline НЕ полностью невидимы на уровне runner — попадают в run.errors как несортированный prose; невидимость возникает на уровне canary-отчёта (fetch-only счётчик) и из-за отсутствия категорий/page_types. Тесты закрепляют категоризацию.

## NEXT
Developer от 18c4a901: KZT/₸ в money-словарь, порядок слов _IELTS_OVERALL, per-page page_types/категории; затем VERIFY в отдельной worktree.
