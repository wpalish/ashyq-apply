# T04 / A1 — ashyq-qa VERIFY_CANDIDATE output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-qa, PHASE: VERIFY_CANDIDATE (новый независимый вызов)
- INVOCATION_REF: agent_748d4ad4-bcfb-4663-ae25-9801aaef1680 (real runtime agentId)
- STATUS: VERIFIED_PASS
- CHECKED_SHA: 3bdc0702dd25e80db16916a00d4e5710dbd65381 (ветка ai/c1/t04/verify, дерево чистое; d45a9cb4 и f7f14b28 — предки)

## COMMANDS_AND_RESULTS
1. rev-parse/status/merge-base → OK; diff-tree → ровно 5 файлов (costs.py, result.py, test_costs.py, ResultDetail.tsx, types.ts)
2. Target pytest test_costs+test_funding_classification → exit 0, 42 passed, 4 QA RED→GREEN (QA RED-класс 0 изменений против QA-коммита)
3. mypy app tests → 0 (153 files)
4. ruff check + format --check → 0
5. FULL suite pytest --cov=app --cov-fail-under=92 → exit 0, coverage 92.91%, collected 1126 == 1126 точек, ноль F/E (нюанс: финальная строка "N passed" не печатается при pytest-cov в этом окружении — воспроизведено на probe)
6. alembic upgrade head (UNIMATCH_DEMO_MODE=true) → 0; seed_demo → Groningen #1 (score 0.79, published_total, computable=True, gap 1848 USD); UBC OUT_OF_BUDGET верифицирован в payload БД (gap 21470.59)
7. Frontend: npm ci 0, typecheck 0, lint 0, test 164 passed/18 files, build 0
8. Де-рискинг: test_frontend_contract 24 passed; test_pipeline+test_api 97 passed

## ADVERSARIAL_FINDINGS
(i) Published total не съедается: total задан → published_total при любом items; partial недостижим (проверено скриптом: total + пустой items + award → computable=True, gap=20000)
(ii) Known-zero: meals=Money(0) при полном наборе → itemised_complete; отсутствие ключа → partial
(iii) Consumers целы: ranking_v2:447, routes_results:85 (sort→inf), tabular:112-116, scoring:128 гейтят computable; backend-consumers не читают новые поля; frontend — только ResultDetail:251-267; остальные экраны → "not computable"
(iv) Legacy round-trip честный (дефолты + наличие ключей в model_dump; независимый JSON round-trip — то же)
Edge: partial+mixed-years, partial CAD (subtotal 29411.76), gap_low/high=None, range-costs на partial. Rollback-окно подтверждено (старая схема отвергает новый payload — принятый риск контракта).

## SCOPE_ASSESSMENT
Ослаблений тестов нет: 6 мигрированных тестов сохраняют структуру assertions; числа пересчитаны арифметически точно (+20000 полный basis); stackable-ассерты без изменений; QA RED-класс дословно без правок (diff QA-коммита к candidate — единственная import-строка). test_funding_classification/runner/funding/scoring/схема БД не тронуты.

## UNTESTED_RISKS
Rollback-окно однонаправленное (деплой-учёт); residual runner.py:579 → T05-T07; T09 e2e на tuition-only — проверить до merge; pytest-cov summary-строка не печатается в этом окружении (учесть при чтении логов).

## NEXT
3bdc0702 → reviewer/security на замороженный SHA; интеграция/push — вне роли QA.
