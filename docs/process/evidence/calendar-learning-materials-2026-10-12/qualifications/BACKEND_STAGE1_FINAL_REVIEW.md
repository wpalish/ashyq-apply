# Backend stage 1 — final read-only review

Дата: 12 октября 2026. Reviewer: `/root/open_search_solutions`.

## Вывод

**Новых конкретных дефектов, требующих исправления, в проверенных backend-контрактах не обнаружено.** Предыдущие замечания об очередности ранних разборов, типе активности и недатированных review refs устранены в прочитанных байтах.

Это результат чтения исходников, а не подтверждение прохождения gates, миграции на сервере, деплоя, полноты курсов или официальной готовности абитуриента. Проверки выполнения оставлены root. Новые providers/models, runtime/tests, security collector, frozen pilot и labels не запускались и не читались. Исходники, Git и HANDOFF reviewer не менял.

## Точная версия проверки

Checkout: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials`.

Начальная база: `6cfa837823e5e5190dbd3918afefaa0ee3c329dc`; во время review root закоммитил реализацию в `8a89a3049fe383c3cf8fccae96149653ea8d123c`. Затем отдельно прочитаны две незакоммиченные поправки GET в `routes_preparation.py`: актуализация `diagnostic_required` и выбор последнего своего submitted attempt точной версии. Они входят в итоговый hash ниже. Изменения frontend не относятся к этому отчёту.

SHA256 проверенных файлов:

| Путь относительно checkout | SHA256 |
| --- | --- |
| `backend/app/schemas/learning_schedule.py` | `a5c26ea689d67aa68cf46936adc5057c854613a99691259282ba5ca64ea684b6` |
| `backend/app/domain/learning_schedule.py` | `f5fb507796e5c7f6d4704ffff6f218fb8a59a35b79bf1fc659212544628e2e62` |
| `backend/app/api/routes_preparation.py` | `11c77dd288e5f00bb7159447833981de1aca446f0e47726a116aec405d1645f2` |
| `backend/app/models/study_schedule.py` | `087ccef37010f3eeddce5329856832de1d4aeea796cba48a52e439cf0ca03626` |
| `backend/migrations/versions/b5c81d9e2022_learning_calendar.py` | `2c9e19365c4ca2835b48094191916667360fe2af94142148c36f60f9e921cad9` |
| `backend/app/api/routes_profile.py` | `d9bd87d528f7c8545c3b6e1875d7924f09bb4bb2e63f5cf18db022e0fe0c235a` |
| `backend/app/models/applicant.py` | `54086f053fbf2db1b4a1471b9dac5595191f425ae2d6c6fe61d7744f1397caeb` |
| `backend/app/payments/preparation.py` | `ab44ed538177c2ac765cd86ec326bb53c196c01927dc04565a9911fe50150a26` |

## Проверенные контракты

### 1. Точные версии и порядок материалов

- `routes_preparation.py:170–193` строит units из фактического `pack_catalogue()`, сохраняя `item.id` и `item.version`; starter content version не подменяется версией learning pack.
- PUT сверяет catalogue version, полный список server-selected units и structural fingerprint с текущим legacy calendar. Затем каждый review проверяется по своему case, client attempt UUID, lesson id, content version и canonical ref id.
- `learning_schedule.py:59–89` распределяет ordered units по skill. После их выделения ранний существующий разбор выбирается из всех подходящих review units, даже когда последняя lesson не submitted; виды активности теперь явно `skill`/`review`.
- `learning_schedule.py:93–110` явно возвращает недостаток capacity для lessons и reviews. Даты и минуты остаются внутри старого finite schedule; диагностические/mock placeholders не выдаются за реализованные уроки.
- Lesson refs проверяются exact dispatch на чтении; отсутствующая версия получает `version_unavailable`, не заменяясь новым материалом. Сохранённый review продолжает ссылаться на свой original receipt.

### 2. Смена дня и GET

- `routes_preparation.py:203–212` валидирует JSON sidecar в отдельную response model и берёт сохранённый `snapshot.schedule`. GET не вызывает новый learning schedule builder и не заменяет draft, task IDs, даты, минуты или refs.
- Проверенная поздняя поправка `:208–210` берёт только `diagnostic_required` из pure legacy builder на текущую дату; результат этого builder не присваивается сохранённому календарю.
- GET обновляет `as_of`, overdue, remaining workload, availability и submitted evidence. `:224–239` выбирает последний accepted UUID только для своего exact lesson/version. Пин существующего `AttemptReviewRef` при этом не меняется на новую попытку.
- В GET и preview нет commit/update/add schedule row. Обновление response model не присваивается `row.learning_path`.

### 3. Shared revision и legacy compatibility

- Старый PUT (`routes_preparation.py:151–161`) и новый PUT используют один `StudyScheduleRow.revision` и SQL `UPDATE ... WHERE profile_id AND revision = expected_revision`.
- Устаревшая запись даёт 409; новая запись sidecar увеличивает revision и не переписывает `row.settings`. Старые self-reported checkmarks остаются в legacy settings/snapshot; они не импортируются как выполнение v2 lessons.
- Structural fingerprint исключает `completed_task_ids`, нормализует порядок study weekdays. Structural legacy edit делает `needs_review`; self-tick структурный fingerprint не меняет.
- Старые `domain/study_schedule.py`, `schemas/study_schedule.py`, `preparation/learning_pack.py`, `models/applicant.py` и preparation entitlement не имеют изменений относительно `6cfa8378`. Старые schedule/attempt/review handlers сохранены; новые endpoints добавлены отдельно.
- Общий revision намеренно меняется и в ответе legacy API после v2 save. Это обеспечивает CAS между двумя редакторами, а не меняет old task IDs/settings/receipts.

### 4. Foreign review и окончание подписки

- Каждый новый endpoint начинает с существующего `owned_profile`; чужой tenant и отсутствующий case получают одинаковый 404.
- Review lookup дополнительно ограничен конкретным `StudyAttempt.profile_id`, поэтому UUID другой case не принимается даже при наличии соответствующего урока. GET evidence projection также case-scoped и не загружает answers/feedback.
- Preview/save проходят существующий `_require_access`; GET сохранённого календаря не блокирует историю после окончания term. Exact owned review endpoint и idempotent replay прежнего UUID не изменены.
- Calendar save не создаёт attempts, не расходует research quota, не меняет subscriptions и не устанавливает official score/readiness.

### 5. Migration, export, delete

- `b5c81d9e2022_learning_calendar.py:10–21` продолжает `a9e5c14d2021`, добавляет один nullable JSON column без backfill/default и при downgrade удаляет только этот column. Runtime migration не выполнялась reviewer.
- `routes_profile.py:324–332` экспортирует исходный sidecar вместе с owned schedule; при SQL NULL новый ключ не добавляется в старый export item. Экспорт не реконструирует календарь из обновлённого каталога.
- Sidecar находится внутри существующего owned `StudyScheduleRow` с FK CASCADE. `models/applicant.py:50–52` сохраняет ORM `all, delete-orphan`; `routes_profile.py:411–426` удаляет весь owned profile. Отдельных таблиц refs, которым требовался бы новый deletion path, не добавлено.

## Граница доказательства

Прочитаны исходники новых focused tests и существующих legacy контрактов. Никаких результатов тестов этот reviewer не производил. Успешность concurrency, clock advance и migration round trip следует подтверждать root-owned gates на тех же конечных байтах; данный отчёт не подменяет такие receipts.
