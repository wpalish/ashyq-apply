# T09 / A1 — ashyq-qa TEST_CONTRACT_AMENDMENT output (сохранено диспетчером)

- ROLE: ashyq-qa, PHASE: TEST_CONTRACT_AMENDMENT
- INVOCATION_REF: agent_25707a0f-321b-4265-8b4b-5bbe132a9bc5 (real runtime agentId)
- STATUS: AMENDED
- CHECKED_SHA: febb6c3310b936171247bd4c007bd877b3047f4e (родитель амендта; ветка ai/c1/t09/qa-amend)
- AMEND_COMMIT_SHA: b0caa004b5351f84ee9ac07184d2486177a77d3f

## СУТЬ (согласованное диспетчером изменение тест-контракта, 2026-09-07)
drafts.test.tsx:472 — `toContainText('The database is unreachable')` → `toHaveTextContent('The database is unreachable')`. Matcher toContainText не существует в vitest 3.2.7/jest-dom (Playwright API) → тест непроходим при любой реализации; TS2551 в typecheck, падение build. Единственное реальное использование (второе grep-совпадение — docstring-комментарий в hydrationErrors.test.tsx:7, не вызов; оставлен как документация дефекта).

## GATES после амендта
- targeted: npx vitest run drafts/store/hydrationErrors → exit 0, 34/34 (drafts 14, hydrationErrors 2, store 18)
- typecheck → exit 0 (TS2551 исчез)
- полный unit: npm test -- --run → exit 0, 20 файлов, 180/180

## ИНТЕГРИТЕТ
diff ровно 1 файл, 1+/1-; store.tsx/caseDrafts.ts/production не затронуты; существующие коммиты не изменялись (амендт поверх febb6c33). Семантика 11-го теста сохранена: указатель выживает после 500, error содержит 'The database is unreachable' (substring semantics эквивалентна).

## НЕПРОВЕРЕННО
vite build не запускался (не входил в согласованную проверку) — остаётся VERIFY-гейту.

## NEXT
Финальный кандидат T09 = b0caa004 (цепочка febb6c33 + b0caa004, test-only amend). VERIFY_CANDIDATE: unit + typecheck + build.
