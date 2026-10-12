# G2: независимая проверка двух новых native-сценариев по исходникам

**READ_ONLY_SOURCE_REVIEW / NO_IMPORT / NO_TEST / NO_RUNTIME.** Root сообщил `71ebec12` и замороженный source во время static/focus. Git независимо не проверялся; фактические bytes десяти прочитанных файлов закреплены в [G2_NATIVE_CONTROL_SOURCE_PINS.json](G2_NATIVE_CONTROL_SOURCE_PINS.json). Этот отчёт расположен вне immutable sealed packets и не изменяет их.

**Вывод:** сценарии дают полезную сквозную проверку сохранения и восстановления, но новый Demo control содержит **два конкретных дефекта теста**, которые мешают его выполнению. Auth control не содержит выявленного блокера по прочитанным контрактам. Реальный PASS native-пары здесь не наблюдался.

## F1 — Demo ждёт endpoint без `/review`

[frontend/e2e/preparation.spec.ts](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/e2e/preparation.spec.ts:660) регистрирует `waitForResponse` для GET `/preparation/attempts/{savedAttemptId}`. Открытие `Open my exact review` передаёт сохранённый ref в `PreparationScreen.openLearningTarget`; `openReview` вызывает [api.preparationAttemptReview](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/api/client.ts:454), который обращается к `/preparation/attempts/{uuid}/review`. Такой же route объявлен в [backend/app/api/routes_preparation.py](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_preparation.py:560). Ответ нормального клика не соответствует predicate, поэтому ожидание не завершится успешно. Это подтверждённое несовпадение исходников; фактический browser timeout здесь не запускался.

Минимальная корректировка только predicate: добавить `/review`. Все проверки JSON receipt, `attempt.attempt_id` и `data-attempt-id` остаются.

## F2 — Demo выбирает последнюю попытку урока, но ожидает первоначальный UUID

[frontend/e2e/preparation.spec.ts](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/e2e/preparation.spec.ts:617) выбирает первую `.row`, содержащую текст `ielts-reading-1`. Далее [frontend/e2e/preparation.spec.ts](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/e2e/preparation.spec.ts:628) и строки 660–664 требуют **исходный `savedAttemptId`**, полученный в раннем serial control на строке 57.

Между ними предыдущий serial control [frontend/e2e/preparation.spec.ts](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/e2e/preparation.spec.ts:382) выбирает первый доступный lesson ref, отправляет новую реальную попытку (строки 400–404) и не переписывает глобальный исходный UUID. Для IELTS `_lesson_units` на [backend/app/api/routes_preparation.py](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_preparation.py:170) выбирает только Reading; его последовательность начинается с `ielts-reading-1` ([backend/app/preparation/learning_pack.py](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/preparation/learning_pack.py:470)). `build_learning_schedule` назначает первый unit Reading до следующих ([backend/app/domain/learning_schedule.py](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/domain/learning_schedule.py:59)). Следовательно, предыдущий control добавляет новую попытку того же lesson ID.

`progress` сортирует попытки по `created_at DESC, id DESC` ([backend/app/api/routes_preparation.py](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_preparation.py:637)); `SharedRoutePanel` использует этот порядок без фильтрации по исходному UUID (строки 384, 455–460). `.first()` выбирает более новую попытку. Текущий control может упасть уже на строке 628 до F1; принимать первый урок за identity попытки нельзя.

Минимальная корректировка: выбирать `.row` по полному `savedAttemptId`, сохранив существующие проверки original UUID. Reference text включает UUID на [frontend/src/screens/SharedRoutePanel.tsx](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/SharedRoutePanel.tsx:457), поэтому обычный locator `hasText` может привязаться к точной сохранённой записи даже при свёрнутом `details`. Это исправляет test selection, не меняет поведение приложения и не подменяет expected UUID последней попыткой.

## Exact textual patch для root после terminal cleanup

Preimage `frontend/e2e/preparation.spec.ts`: `c2e386d225e916f4c145da060ee01a43c6adca3b3f3c7aabdb48f18d9853e40e` (47832 bytes). Старые control/assertions и остальные source files сохраняются. **Никаких source proposal files, repo edits или новых тестов здесь не создано.**

```diff
-  await reviews.locator('.row').filter({ hasText: 'ielts-reading-1' }).first().getByRole('button', { name: 'Add own review', exact: true }).click();
+  await reviews.locator('.row').filter({ hasText: savedAttemptId }).getByRole('button', { name: 'Add own review', exact: true }).click();

-  const reviewReplyPromise = page.waitForResponse(reply => reply.request().method() === 'GET' && new URL(reply.url()).pathname.endsWith(`/preparation/attempts/${savedAttemptId}`));
+  const reviewReplyPromise = page.waitForResponse(reply => reply.request().method() === 'GET' && new URL(reply.url()).pathname.endsWith(`/preparation/attempts/${savedAttemptId}/review`));
```

Auth file preimage: `3ce4835ea7acf0ce36a63a842b23021fcd4b148045a4511c02afe71e3efa69a5` (40842 bytes). Этот отчёт не предлагает изменять Auth source.

## Что два сценария действительно проверяют

| Acceptance | Demo control | Auth control | Граница утверждения |
| --- | --- | --- | --- |
| Два явно выбранных own programmes | Считывает ID двух saved cards и проверяет ordered `requested_result_ids` (587–598, 626) | То же после sign-in (575–592, 611) | Eligibility/proof correctness не выводится из факта выбора; это отдельный G1 contract. |
| Явные личные даты/буферы/ёмкость | Через реальные поля UI, IELTS + SAT, SAT первым, 240 минут (601–620, 627) | IELTS, 180 минут (595–606) | Это пользовательские планы, а не опубликованные университетом требования. |
| Unsaved preview | POST preview `saved=false`, затем GET revision 0 (621–631) | `saved=false`, initial GET revision 0 (581–586, 607–611) | Preview не считается сохранением; полный неизменный baseline покрывают backend controls. |
| Реальный ACK | PUT UI → 200, own profile, revision 1, allocation digest = preview (632–637) | То же (612–616) | Frontend additionally binds UUID/body/order/source/legacy in `matchesSharedReceipt` ([frontend/src/screens/SharedRoutePanel.tsx](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/SharedRoutePanel.tsx:136)); native assertions не заменяют эти guards. |
| Original UUID replay | Повторяет **точное request `postDataJSON()`**, сравнивает весь ответ с исходным receipt (638–639) | То же (617–618) | Это нормальный accepted replay. Unknown outcome/retry branch отдельно покрыт FE unit controls (186–219), не этим native сценарием. |
| Reload persistence | Reload + current UI, API GET deep equality; historical revision UI; export current/history = exact receipt (640–650, 669–671) | Reload первого context; полностью новый signed-in context; deep GET + export equality (619–631, 646–648) | Demo history detail assert — label revision; exact whole history equality подтверждается экспортом. |
| Чистый браузер | Один серийный synthetic context, не fresh second context | `first` закрывается; `newSession(browser)` создаёт новый `browser.newContext()` без переноса cookies/storage, затем реальный sign-in (622–627; helpers 26–39) | Auth не доказывает внешнюю SSO/production payment/real-user journey. |
| Exact review / lesson | Own original review + data-attempt-id (660–664) после F1/F2 | Урок из сохранённого receipt; exact GET `version` и returned lesson id/version (633–640) | `PreparationScreen` проверяет own UUID/lesson/version, не latest lookup (212–247); новый native Demo сейчас блокирован дефектами теста. |
| Один бюджет | Два exam streams, каждый combined capacity row `allocated_minutes <=240` (627–629); legacy Save disabled | Legacy Save disabled; shared input 180 | Native не пересчитывает суммы из slots; literal conservation/capacity — pure/API gates. UI показывает `shared_weekly_minutes` и отключает legacy editor ([frontend/src/screens/SharedRoutePanel.tsx](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/SharedRoutePanel.tsx:546); PreparationScreen 312–327). |
| Existing records preserved | Export before/after equality для legacy study schedules, attempts, official academics (672–674) | То же (649–651) | Полезный контроль отсутствия скрытого изменения старого плана/практики/official scores. |
| Viewports | 320/768/1024/1440, no document horizontal overflow + отдельные PNG (651–659) | Project viewport; second-session PNG | Это layout/overflow control. Сам по себе не доказывает читабельность, hit targets/keyboard или отсутствие нижнего перекрытия. PNG root должен визуально проверить после реального прогона. |

## Остальная source coherence

- Оба новых control используют обычные clicks и реальные `page.request` к текущему API; в добавленных блоках нет request interception, mock helper или подмены ответа. Они опираются на ранее созданные synthetic account/profile/run/attempt в serial suite. Это допустимо для целого workflow, но отдельный запуск только нового test title без подготовки не является тем же gate.
- Wait predicates устанавливаются до соответствующих clicks. Сохранённый request replay использует request реального PUT. После reload UI читает server current; после второго sign-in Auth GET сравнивает immutable receipt целиком.
- Shared lesson button вызывает exact stored version ([frontend/src/api/client.ts](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/api/client.ts:448)), shared review вызывает UUID из ref ([frontend/src/screens/PreparationScreen.tsx](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/PreparationScreen.tsx:243)). В Auth текущий `.first()` lesson согласован с `.find()` первого lesson slot: view рисует slots в их сохранённом порядке; stream только IELTS. Выявленного противоречия здесь нет.
- Readiness/applicability остаются `not_assessed`/`unknown` в frontend preview guard ([frontend/src/screens/SharedRoutePanel.tsx](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/screens/SharedRoutePanel.tsx:110)), UI сообщает practice/plan ≠ readiness (SharedRoutePanel 547; PreparationScreen 254). Native happy path не является официальной оценкой экзамена или доказательством admissions applicability.
- Обновление viewport в `finally` и закрытие обоих Auth contexts в `finally` присутствуют. Layout capture alone не является manual visual acceptance.

## Что осталось для фактического acceptance

1. Root после terminal focus/owned cleanup в отдельной разрешённой test-only правке исправляет F1/F2, сохранив исходные UUID/receipt/assertions и first-failure evidence.
2. Root обновляет exact native source pins; любой browser run привязывается к новым preimages и полному synthetic serial setup. Здесь helpers или pin manifests не менялись.
3. Root запускает approved native Demo/Auth по очереди, сохраняет original terminal receipts и PNG, проверяет four-width screenshots. Только их реальные результаты смогут закрыть native acceptance.
4. Полнота настоящего учебного курса, unseen diagnostics, человеческая педагогическая review, платёжная production интеграция и live search quality этим bounded native review не подтверждаются.

**Результат этого агента:** два подтверждённых исходниками дефекта нового Demo test, source-only acceptance map, exact textual root repair. **NO_APP_EDIT / NO_IMPORT / NO_TEST_EXECUTION / NO_RUNTIME.**
