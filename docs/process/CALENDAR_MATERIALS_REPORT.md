# Unimatch — календарь с точными материалами

Дата: 12 октября 2026, Asia/Almaty. **Первый этап принят локально: календарь с точными уроками и собственными разборами. Полный продукт ещё не готов.**

Изменения опубликованы для проверки: [Draft PR #85](https://github.com/wpalish/ashyq-apply/pull/85), зависимый от PR #84. В main и production этот этап ещё не принят. Проверки GitHub для этого PR не запускались.

## 1. Исходная проблема и граница этапа

В базе PR #84 уже были девять оригинальных учебных занятий и 39 вопросов. Датированный календарь связывал задачи только с тремя starter IDs без полной идентичности версии. Остальные занятия и собственные разборы не были связаны с датами.

Этот этап связывает имеющиеся материалы и сохранённые попытки с календарём. Он не создаёт полный IELTS/SAT курс, официальную диагностику или общий маршрут заявок. Оценки практики не меняют официальные баллы профиля и не подтверждают освоение навыка.

База: `task/preparation-learning-path @ 2c645c8a2bc0257271116d7e7cac929b29406b44`, dependent Draft PR #84. Исполняемый application source этапа: `task/calendar-learning-materials @ 9d3315e8cf2dcca93e01de8aa1fd6c7abbbbe557` (application bytes сохранены; итоговый source/test HEAD: 6a66da456f14d964ec16091f321fb7f23a74077f). Основная рабочая копия, main и production не менялись.

## 2. Новое поведение

1. В сохранённом учебном плане пользователь открывает **учебный календарь**.
2. Отдельно просматривает обновлённый маршрут. Просмотр не записывает его на сервер.
3. Явно сохраняет выбранный маршрут. Общая revision защищает и прежние настройки, и новый маршрут от одновременной перезаписи.
4. Датированная задача открывает `lesson_id + exact content_version`. Если эта версия отсутствует, задача показывает причину и не открывает другую версию.
5. После серверного подтверждения отправки виден отдельный статус сохранённой попытки; кнопка открывает её собственный разбор по UUID.
6. Разбор не зависит от последних 20 попыток в кратком списке. Собственная история доступна после окончания подписки; новый урок и изменение плана требуют разрешённого доступа.
7. Перезагрузка читает сохранённые даты и ссылки. Смена дня обновляет возраст исходной оценки и просроченность, сохраняя исходный draft и даты.

Прежние настройки, fingerprint, идентификаторы задач и self-reported отметки `schedule-v1` сохранены. Новый маршрут хранится отдельно в nullable JSON той же case-owned строки, с общей revision. Он не превращает прежние отметки в оценённое выполнение.

## 3. Распределение и ограничения материалов

- Используются порядок существующих треков и прежние дневные/недельные лимиты, сроки экзамена и буферы.
- Минимум 20 минут на занятие — **плановое выделение времени**, не обещание длительности изучения или роста балла.
- Работа, не помещающаяся в сроки, остаётся явно нераспределённой.
- Разборы собственных выбранных попыток получают даты там, где есть место. Новая попытка сама не перестраивает маршрут; пользователь может просмотреть и сохранить новую версию.
- В IELTS доступны существующие Reading материалы. Listening/Writing/Speaking и reserved assessment/resource targets честно показывают отсутствие реализации.
- `submitted_attempt_id` показывает последнюю сохранённую собственную попытку точной версии; ранее выбранный UUID разбора остаётся закреплённым в плане.

## 4. Изменения в коде

Backend: отдельные schemas/domain `learning_schedule.py`; additive migration `b5c81d9e2022`; nullable `StudyScheduleRow.learning_path`; owned GET, preview POST и CAS PUT `/api/profiles/{id}/preparation/schedule/learning-path`; conditional sidecar в экспорте. Имеющийся `study_schedule.py`, учебный контент и ключи не переписаны.

Frontend: typed client/types; `LearningSchedulePanel`; exact-version уроки и UUID review в `PreparationScreen`; подключение к `StudySchedulePanel`; EN/RU/KK тексты нового календаря. Ошибка свежего чтения и mismatch revision блокируют устаревшие действия; поздние ответы сохраняют существующие case/epoch fences.

Новые проверки: exact versions/даты/лимиты, read-only preview, CAS, ownership, expiry, история за пределами limit20, migration upgrade/rollback с прежними данными, export/delete с соседним case, два реальных конкурирующих HTTP writers, missing version и отдельная submission evidence. Native Demo/Auth сценарии проходят через настоящий API без подмены ответов.

## 5. Проверка и доказательства

| Проверка | Текущее состояние |
|---|---|
| Фокусная диагностика final6 | 122 PASS с SQLite/PG controls; отдельный результат, не full gate |
| Static final8: Ruff/format/mypy/types/lint/frontend tests/build | 7 PASS; frontend 518 тестов; источник неизменен |
| Полный SQLite/PostgreSQL, coverage floor 92 | 4914 PASS на каждой базе; одинаковые 4914 уникальных JUnit IDs; coverage 95.57135% / 95.56528%; 42 warnings на каждой базе |
| Изолированная новая миграция и seed | PASS; Groningen первый, UBC OUT_OF_BUDGET; одна Alembic head b5c81d9e2022; upgrade/rollback с прежними данными — PASS на обеих базах |
| Native Demo | 99 PASS, 1 прежний intentional skip; настоящий API; opt-in/save/exact lesson/attempt/reload/own review на desktop и mobile |
| Native Auth, reload и второй чистый браузер | 9 PASS; реальный вход и восстановление своего календаря/UUID разбора без прежних cookies/localStorage |
| Скриншоты 320/768/1024/1440 и визуальная читаемость | Четыре точных PNG сохранены; даты, текст задач и действия проверены визуально; ширина страниц в пределах viewport |
| Main/production/hosted CI/live search/pedagogical validation | Не проверено этим этапом; Docker отсутствует — containers NOT_RUN |

Для финальной версии тестового начала весь 609-file manifest принятого backend full2 совпадает без единого изменения; этот результат переносится по точным байтам, а frontend/static/native проверяются свежими прогонами. Исходники не меняются во время frozen runtime. Сырые первые ошибки сохранены отдельно: первоначальные ошибки HTTP-кода и слишком длинного тестового окна; неуместное ожидание доступного Preview при expiry; unsupported Testing Library option; тест, который не обновлял revision родителя после save ACK. Сохранён первый Native Demo: прежние console/geometry проверки не ослаблены; source unchanged и собственные порты освобождены. Затем сохранена отдельная ошибка начала нового serial теста после намеренного 409/dirty form; исправлены только reload и дополнительные проверки восстановления 240 минут. Первая Auth попытка сохранила 8 PASS / 1 FAIL: новый тест требовал синхронное изменение controlled checkbox; он исправлен на обычный клик, реальный ACK и явную проверку checked. Настройка внешнего Vite разрешает только frontend и два точных пакета шрифтов, сохраняя fs deny и loopback-only сеть. Это объявленная правка тела раннера, а не application change. Также сохранены full-final1 с тремя ошибочными новыми assertions (wire timestamp/raw-vs-projected state) и diagnostic5 с неверным именем поля version. Final6 проверяет точный DB wire timestamp, отдельно raw snapshot и enriched API receipt с exact own UUID; старые assertions, network guards и coverage floor не ослаблены.

Первоначальная ошибка внешней обёртки из-за запуска не тем Python также сохранена; очистка подтверждена только для её собственного кластера. Процессы других задач не принимались и не останавливались.

Сырые результаты, JUnit, manifests, первые ошибки и снимки сохранены в конечном архиве `docs/process/evidence/calendar-learning-materials-2026-10-12`; `INDEX.json` содержит размер и SHA256 каждого из 584 оригиналов (187 659 586 байт). Базы, cookies, auth state, зависимости и traces в Git не копируются. Lint завершён с 4 warnings / 0 errors; build предупреждает о chunk 526.62 kB — производительность production этим этапом не измерена.

## 6. Что остаётся до единой платформы

Следующий этап: общий multi-programme graph проверенных требований, альтернатив и действий с одним бюджетом подготовки. Далее — server-backed задачи документов, отдельные application statuses/receipts и Today projection; reviewed syllabus/full courses/independent diagnostics и private portfolio по отдельным контрактам.

Публикация полного продукта требует принятия dependent chain, реальных operator/subscription/legal фактов, отдельно разрешённой свежей проверки поискового качества и опубликованного сценария вошедшего пользователя. Старые provider/model/quota/security STOP и UNSCORED результаты остаются в силе. Этот отчёт не утверждает, что поисковик или весь продукт завершён.

## 7. Снимки и точные receipts

- [Мобильный календарь, 320](evidence/calendar-learning-materials-2026-10-12/execution/evidence/e2e/20261011T223732Z-auth/docs/screenshots/auth-learning-calendar-second-session-320.png)
- [768](evidence/calendar-learning-materials-2026-10-12/execution/evidence/e2e/20261011T223732Z-auth/docs/screenshots/auth-learning-calendar-second-session-768.png), [1024](evidence/calendar-learning-materials-2026-10-12/execution/evidence/e2e/20261011T223732Z-auth/docs/screenshots/auth-learning-calendar-second-session-1024.png), [1440](evidence/calendar-learning-materials-2026-10-12/execution/evidence/e2e/20261011T223732Z-auth/docs/screenshots/auth-learning-calendar-second-session-1440.png)
- [Сохранённый собственный разбор](evidence/calendar-learning-materials-2026-10-12/execution/evidence/e2e/20261011T223151Z-demo/docs/screenshots/learning-calendar-exact-review.png)
- [Конечный native receipt](evidence/calendar-learning-materials-2026-10-12/execution/NATIVE_FINAL_VERIFICATION.json), [qualification переноса неизменных gates](evidence/calendar-learning-materials-2026-10-12/execution/FINAL_CARRY_QUALIFICATION.json), [полный backend](evidence/calendar-learning-materials-2026-10-12/execution/FULL_TERMINAL_VERIFICATION.json), [индекс оригиналов](evidence/calendar-learning-materials-2026-10-12/INDEX.json).

G1 для нескольких программ подготовлен и независимо прочитан как внешний пакет; **NOT_APPLIED / NOT_RUN**. Он сохраняет оригинальные требования, ссылки и scope отдельно по программе. Общие числовые цели, подтверждённые альтернативы/waiver, сохранённый граф и распределение общей нагрузки потребуют последующих проверенных этапов.
