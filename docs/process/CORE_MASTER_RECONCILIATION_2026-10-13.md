# Сверка перед завершением ядра — 13 октября 2026

Baseline `892fc5e5ab8bf09a66234b4597280ba420ec9e88`, ветка `task/admissions-actions-today`, дерево чистое и source786 совпадает с последней root application. Общая native-run блокировка свободна. Alembic head `d7a61e902024`. Работа одним root, без помощников. Старые live/provider/model/security остановки сохраняются; разрешена обычная offline разработка по мастер-промпту владельца.

CLAUDE_CONTINUE в другой копии описывает снимок G3 `3e91d936` и отдельный product-completion `ecd10015`; это исторический обзор, не инструкция вернуться к старому API. Текущая цепочка уже содержит серверные G3 API и history. Старые gates не повторены для baseline: точный frontend после optional UI прошёл727, backend focused192 переносится по неизменным native597 зависимым путям, полный backend текущего API и законченные экраны pending.

## Выбор единой модели прогресса

| Система | Точный источник | Статус | Решение |
|---|---|---|---|
| G3 команды, case state, ревизии и receipts | baseline892fc5e5: backend/app/schemas/admissions_actions.py; models/admissions_actions.py; api/routes_admissions_actions.py | Существует и используется сервером; экранное подключение неполное | Единственный source of truth. Имеет личные задачи, события, CAS/UUID, собственную историю и работу с сохранёнными records после потери source |
| Браузерный G3 журнал | baseline892fc5e5: frontend/src/lib/admissionsActionsRecovery.ts | Реализован и проверен; Store/retention подключение pending | Переиспользовать только для восстановления исходных команд, cap64; не делать БД документов |
| document_progress/progress_id | origin/task/product-completion@ecd10015f5defa01f61004d5424e3c509846ce76: backend/app/api/routes_results.py:198; schemas/result.py:291 | Существует отдельно, не ancestor текущей ветки; общий предок1b2a5541 | Не сливать автоматически. PATCH хранит bool в result.payload, требует research full access; нет G3 event/revision/UUID semantics и ручной задачи без result. При обновлении payload отбрасываются неактуальные progress IDs |
| ApplicationNextAction | product-completion@ecd10015: frontend/src/components/ApplicationNextAction.tsx; lib/applicationPlan.ts | Отдельная проекция старой системы | Не вводить третью state machine. Вывод ближайших действий должен использовать нынешний G3 Today |
| Документы текущего UI | baseline892fc5e5: frontend/src/screens/DocumentsScreen.tsx | Галочки scoped localStorage по result/name | Требуется подключить G3 stable task IDs. Старые ticks импортируются только явно как self-report |
| Application/Today UI | baseline892fc5e5: backend/app/api/routes_admissions_actions.py; frontend/src/screens/ApprovedScreen.tsx/HomeScreen.tsx | Серверный API есть; полноценные формы/Today consumer отсутствуют | Реализовать после case/recovery bridge |
| Manual application target | baseline892fc5e5: schemas/admissions_actions.py:268 | Текущий target требует result_id; ручные задачи уже работают без research | Обнаружено расхождение с master requirement ручной заявки без research. Нужен следующий минимальный G3-compatible versioned contract increment; nullable ссылку нельзя подставить в frozenV1 молча |

G3 endpoints: POST commands; POST source preview; POST legacy import preview; GET current/events/one event; GET today. Export включён в own profile export, case cascade в существующую модель. Status self-report/submission declaration не означает official verification. Ни старая bool-галочка, ни approved не означают оффер.

## Первый минимальный schema increment

Сейчас RunView содержит окончательные counters/results и diagnostics, но отдельного programme observation нет. Поэтому найденную и прочитанную страницу нельзя честно показать отдельным итоговым ProgramResult с assessment.

Предлагается и реализуется отдельно: nullable JSON `research_runs.programme_observations`, максимум150 URL-observations (bounded cap соответствует50×3 страницы). Каждый stable observation — institution/domain + canonical final URL + requested degree, полный список до60 различных read-proofs: fetched timestamp, текстовый SHA256 и фактически классифицированные degree/subject/page type. Класс degree может оставатьсяunknown. Core requirements и admission compatibility явноunknown/not_assessed; никакого score, fees, funding или intake inference.

Принятие происходит сразу после нынешнего успешного Fetcher и same-site/page-type/profile predicate, до следующего необязательного await. Частичный observation сохраняется через существующие _check_cancelled/_save и heartbeat CAS в той же транзакции. Cancellation/LeaseLost/refusal не превращаются в success. Fetcher, запросы, flags и caps не расширяются. Durable accepted reads сохраняются после обычного timeout/ошибки enrichment; дальнейший отказ остаётся видимым.

Additive migration child отd7a61e902024. Старый nullable payload читается как[]; повреждённый payload — explicit observation unavailable. GET RunView добавляет два совместимых поля: bounded observations и состояние чтения. Нет новой document-progress системы, таблиц programme matches или worker bypass. Старый клиент может игнорировать поля. Downgrade удаляет только новый JSON столбец, сохраняет старые runs/claims/results.

Отдельно найдено: catalogue production wrapper использует300s, тогда как quality DoD измеряет120s на вуз. Первый publication increment не увеличивает таймер и не меняет сетевой порядок; соответствие общего production budget остаётся отдельным проверяемым вопросом, не заявляется автоматически.

## Приёмка первого increment

Offline фактический Fetcher-interface/classifier: валидная страница → задержанное enrichment → timeout, invalid/otherdegree/offsite, duplicate proof, plain success, cancellation/LeaseLost/typed refusal. Native DB: persisted observation перед delayed await, own GET после нового соединения, stale fenced attempt/cancel запрет записи, corruption explicit unavailable, migration roundtrip/ownership на SQLite и PostgreSQL. Никакой live/heldout оценки. Полный local regression после изменения executable — отдельно, реальные числа из receipts.
