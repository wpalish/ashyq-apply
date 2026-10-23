# Stage 1: квалификация backend, static и миграции

12.10.2026. **Сохранённые receipts подтверждают backend/static проверки первого этапа. Завершение native сценариев и готовность продукта этим заключением не подтверждены.**

## Проверенная версия и способ проверки

- Source pin из [FULL_TERMINAL_VERIFICATION.json](../execution/FULL_TERMINAL_VERIFICATION.json): `9d3315e8cf2dcca93e01de8aa1fd6c7abbbbe557`.
- Прочитаны конечные result/log/JUnit/coverage/source-manifest файлы. XML/JSON и SHA256 обработаны только стандартной библиотекой; app/runtime модули не импортировались, проверки и миграции заново не запускались.
- Полный result SHA256 независимо совпал: `361de639c6e401d82b8fd90a79239eb798f7e5d8ff8456d6810f7dfbfb7add56`.
- Для обеих backend фаз совпали записанные SHA256 `pytest.log`, `junit.xml`, `coverage.json`, `source-before.json`, `source-after.json`; before/after manifests равны. Девять файлов schemas/builder/routes/models/migration/entitlement/API tests в `execution/source` совпадают с manifest прогона. Идентичность Git HEAD отдельно не проверялась.
- Исходники, Git, данные и настройки не изменялись. Collector/controller, labels, private runtime DB, auth и trace не читались и не запускались; STOPs сохранены.

## Конечные результаты

| Проверка | Реальный receipt | Итог |
| --- | --- | --- |
| Full backend, SQLite phase | [result.json](../execution/evidence/backend-full-final2/20261011T215427507540Z/result.json), [SQLite pytest.log](../execution/evidence/backend-full-final2/20261011T215427507540Z/sqlite/pytest.log) | 4914 passed; 0 failures/errors/skips; 95.57135046473483% coverage |
| Full backend, PostgreSQL phase | Тот же result, [PostgreSQL pytest.log](../execution/evidence/backend-full-final2/20261011T215427507540Z/postgres/pytest.log) | 4914 passed; 0 failures/errors/skips; 95.56527549966587% coverage |
| Static/frontend final6 | [result.json](../execution/evidence/static-frontend-final6/result.json), [frontend-junit.xml](../execution/evidence/static-frontend-final6/frontend-junit.xml) | Все 7 команд exit 0: ruff, format, mypy, typecheck, lint, unit, build. JUnit: 518 тестов, 0 failures/errors/skips; source before/after равны |
| Focused diagnostic final6 | [result.json](../execution/evidence/focused-final6/20261011T215408172124Z/result.json), [pytest.log](../execution/evidence/focused-final6/20261011T215408172124Z/sqlite/pytest.log) | 122 passed; 0 failures/errors/skips. Diagnostic не выдаётся за full gate или coverage proof |
| Synthetic demo seed | [result.json](../execution/evidence/demo-seed-qualified/result.json), [migration.log](../execution/evidence/demo-seed-qualified/migration.log) | Migration/seed/query exit 0; `order_and_bucket_pass=true`; synthetic DB, providers none, external network OS_DENIED |

Обе backend JUnit независимо разобраны: в каждой **4914 уникальных `(classname, name)`**, множества идентичны. Это повтор одного набора, не 9828 разных тестов. Обе coverage JSON выше сохранённого gate `--cov-fail-under=92`; в каждом логе остаётся 42 warnings. Focused JUnit также независимо разобрана: 122 уникальных случая. Ни один из этих offline результатов не измеряет текущую точность поиска.

Build завершён, но [build.log](../execution/evidence/static-frontend-final6/build.log) сохраняет предупреждение о JS chunk 526.62 kB (gzip 152.81 kB). Это не падение gate; performance native/production этим логом не измерена.

## Подтверждённые контракты первого этапа

На совпадающих с receipt исходниках и успешных API/domain тестах подтверждена следующая ограниченная функция: **явно сохранить в своём календаре версии уроков и ссылки на собственные попытки; читать этот план, не теряя прежний календарь и историю**.

1. **Opt-in и старые данные.** Отдельные GET/preview/PUT learning-path; preview без записи, SQL NULL означает отсутствие сохранённого нового пути. Legacy settings/checkmarks остаются самостоятельными; отметка пользователя не превращается в assessment/mastery. См. [API:268](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/source/backend/app/api/routes_preparation.py:268), [strict schema:54](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/source/backend/app/schemas/learning_schedule.py:54).
2. **Точная версия и own receipt.** Lesson refs хранят lesson ID/content version; review refs — исходный client attempt UUID, lesson/version конкретного case. Чужие или подменённые refs отвергаются. История точной старой попытки доступна напрямую, в том числе вне progress limit 20 и после окончания term. Другая версия урока не подставляется.
3. **GET при смене дня.** Сохранённые draft/task IDs/dates/refs не перестраиваются; текущие baseline age, overdue, remaining и submission projection обновляются без записи. Последняя собственная submission точного lesson/version не меняет pin исторического review.
4. **Shared CAS.** Legacy и learning PUT используют одну revision. Подтверждены обе стороны настоящей гонки двух HTTP writers на SQLite и PostgreSQL: один 200, один 409, revision ровно +1, соседний JSON и данные не потеряны. См. [API test:438](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/source/backend/tests/test_learning_schedule_api.py:438).
5. **Export/delete.** Экспорт отдаёт raw сохранённый sidecar; при NULL прежняя форма export не дополнена пустым ключом. Проверены точные JSON/timestamp/attempt receipts, отсутствие записей от чтения, удаление case вместе с календарём/attempts и сохранность другого собственного case. См. [tests:323](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/source/backend/tests/test_learning_schedule_api.py:323).
6. **Миграция.** AST чтение всех 22 revision файлов дало ровно один head `b5c81d9e2022`, без отсутствующих parents. Новый parent — `a9e5c14d2021`. [Migration:16](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/source/backend/migrations/versions/b5c81d9e2022_learning_calendar.py:16) добавляет один nullable JSON column без default/backfill; downgrade удаляет только его. Full JUnit содержит успешные migration round-trip случаи обоих drivers. Synthetic seed log фиксирует upgrade до нового head; это не миграция production.

Все 26 параметризованных случаев `test_learning_schedule_api` присутствуют и успешны в каждой full JUnit, включая clock advance, unavailable saved version, latest exact receipt, nullable migration, export/delete и обе CAS стороны. Исправления test expectations отдельно объяснены в [TEST_ASSERTION_REPAIR_REVIEW.md](TEST_ASSERTION_REPAIR_REVIEW.md); первый RED receipt сохранён, а не переименован в PASS.

## Что ещё не закрыто

- **Native Demo:** на момент назначения reviewer родитель сообщил сохранённый первый RED; исправление font harness проверяется отдельно. Этот reviewer не читал native traces и не присваивает будущему повтору PASS. Для принятия первого этапа нужен новый конечный native receipt на тех же source bytes с подтверждённым opt-in/save/reload/lesson/own-review/expired-read сценарием и совместимостью legacy пути.
- **Native Auth:** `NOT_RUN` по текущему сообщению родителя; 518 jsdom тестов и backend API receipts не заменяют browser сценарий вошедшего пользователя.
- **Содержание и диагностика:** текущий [catalogue notice:520](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/source/backend/app/preparation/learning_pack.py:520) прямо оставляет pedagogy/learner validation pending. Pack добавляет шесть уроков с пятью заданиями в каждом к starter lessons; повтор знакомых заданий — review. [Builder:54](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/source/backend/app/domain/learning_schedule.py:54) выдаёт diagnostic/mock как `not_implemented`; [schema:90](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/source/backend/app/schemas/learning_schedule.py:90) сохраняет `readiness=not_assessed`. Это ограниченный practice/calendar этап, не доказанный полный IELTS/SAT курс, официальная оценка или готовность к поступлению.
- **Следующий этап:** multi-programme graph, доказанные waivers/alternatives и общая exam workload остаются отдельной архитектурной работой, описанной в [NEXT_MULTI_PROGRAMME_GRAPH_PLAN.md](../NEXT_MULTI_PROGRAMME_GRAPH_PLAN.md). Они не покрываются статусом этого этапа.
- **Продукт/release:** current live search quality остаётся `NOT_MEASURED`, frozen evaluation — `UNSCORED`; provider STOP не снят. Containers `NOT_RUN`, primary integration/deployment/production migration/live user journey этим пакетом не подтверждены. Нужные release и native проверки должны иметь собственные конечные receipts; готовность всего Unimatch не выводится из backend/static PASS.

## Заключение

**Backend/static/migration часть Stage 1 имеет достаточные сохранённые инженерные receipts для своей заявленной функции. Полный Stage 1 acceptance остаётся открытым по native Demo/Auth; общий продукт, поиск и release не объявлены готовыми.** Новых backend contract blockers в рассмотренной границе не обнаружено. Дополнительных прогонов или source правок для этого заключения reviewer не выполнял.
