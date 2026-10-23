# G3: finite review focused route repair1

**SOURCE_ONLY / finite route changes qualified / NOT_IMPORTED / NOT_RUN / не runtime acceptance.** Конкретного блокера в разрешённых изменениях не обнаружено.

Проверен [неизменный пакет](proposals/g3-api-focused-route-repair1/SEAL.json) SHA256 `b595e87d4f0a2d7b1cef2c11adae1131034f21b287438bfe031d31ac1f809d52`: **8/8** членов совпали по SHA256 и размерам. Полностью прочитаны diff, manifest/README/grant и обе изменяемые функции с native контекстом. Preimage `31c445bb51eabc2e51f3e9d5f4a8114a748432af33a4f9a6a3b0e03b5329d983` точно равен текущему primary route. Postimage `92e68f62a9af2ac5e8f474ac87de088bfca483e0b882e53d231b8a5b568d1c6e` (96 642 bytes). Literal inverse **трёх** замен manifest восстанавливает весь исходный route; полный unified diff точно совпадает с фактической парой файлов.

## Evidence join: явный исходный FROM

[Query](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-api-focused-route-repair1/postimages/backend/app/api/routes_admissions_actions.py:1183) теперь начинает evidence rows с `ProgramResultRow` и явно задаёт `ResearchRun.id == ProgramResultRow.run_id`. Это соответствует native FK в `models/research.py`. Прежний implicit join был неоднозначен при одновременно проецируемых run IDs из основного результата и двух aggregate subqueries.

Сохранены все columns, оба aggregate subquery и их filters/grouping, оба outer join, own profile filter, выбранные result IDs, approved/maybe filter, порядок по result ID, UTC-конверсия scalar metadata и возвращаемый source token. Ни locked branch, ни доказательства, ни правила доступа не расширены. Здесь соединение лишается неявного выбора источника JOIN; runtime compilation или фактическое закрытие 38 прежних отказов reviewer не выполнял. Число 38 в README — attribution до повторного прогона, не repaired PASS.

## Неожиданный SQL отказ: 503 после прежнего recovery

[SQLAlchemyError branch](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-api-focused-route-repair1/postimages/backend/app/api/routes_admissions_actions.py:1940) сохраняет `rollback()` и `_fresh_uuid_reconcile()` в прежнем порядке. Уже принятый собственный matching UUID возвращает исходный валидированный receipt. Если принятого UUID нет, неожиданный SQL/integrity/trigger отказ даёт fixed `write_unconfirmed` **503**, а не необоснованный `revision_conflict`.

Реальные expected revision/CAS mismatch продолжают давать explicit `ActionError('revision_conflict')` **409** в сохранённых выражениях на строках 1803/1853 postimage. Same UUID с другим intent по-прежнему даёт `uuid_conflict` 409 через native replay validator. Удаление ненужного `IntegrityError` import и exception binding не меняет остальные catch branches.

Fresh reconciliation сохраняет ownership/actor проверки и полную валидацию оригинального receipt. Native `ActionError` использует конечный фиксированный словарь, без SQL repr, raw inputs или сообщения драйвера. Новое сообщение 503 не возвращает caught exception и сохраняет original request/retry semantics.

## Неизменённые physical controls

Прочитаны [native write fence](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/preparation_transactions.py:22) и относящиеся concurrency controls:

- SQLite first actual `BEGIN IMMEDIATE`; PG asserted READ COMMITTED + `Profile FOR UPDATE`; plain actor/member check, затем existing legacy child lock. Никакого нового User/Org FK/lock, audit или mutex не добавлено. Dirty/nested session refusal находится вне rollback catches.
- [Absent/present real writers](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_admissions_actions_concurrency.py:847): два нативных writer вызова, equal UUID — точный один ACK, changed body — UUID conflict, distinct UUID same CAS — revision conflict; проверяются целая state/event sequence, отсутствие дублей, exact replay и native snapshot.
- [Physical race seam](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_preparation_write_concurrency.py:173): разные driver connections, незавершённый waiter, SQLite actual trace + независимый SQLITE_BUSY, PG `pg_locks`/blocking PID; это не только barrier/mock ответа.
- [Event trigger rollback](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_admissions_actions_concurrency.py:971): actual SQLite ABORT / PG 23514 после уже выполненного current INSERT/UPDATE, fixed503 без строки trigger, fresh-session whole-pair/native equality, затем тот же original UUID/body и exact ACK replay. Эти controls содержательно отличают неожиданный отказ от accepted concurrent conflict.

Пакет не меняет ни один из этих тестов или guards. Их прохождение после ремонта ещё требуется; чтение исходников не считается execution. Сохранённые в пакете Ruff/format-check logs сообщают PASS/«already formatted» только для external route; reviewer инструменты не запускал.

Grant `b786a779c02610a7077bb7c172d2de1ac3621baf928d9aaa7ce373b6f84ea60b` допускает также отдельные Today test corrections, но **этот** пакет содержит только route. Их проверка или выполнение здесь не заявлены. Приложение, конфигурация, native schema/domain/tests, original seals, Git, HANDOFF и helpers reviewer не изменял; AST/import/runtime/DB/browser/network не выполнялись. Root остаётся единственным application/runtime writer.
