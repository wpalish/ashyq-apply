# Проверка исправлений assertions: learning-path sidecar

Дата: 12.10.2026. Статус: **READ-ONLY SOURCE REVIEW; повторные runtime gates этим review не подтверждены.**

Проверен текущий замороженный исходник `work/unimatch-calendar-materials`. Родитель сообщил test-only исправления `57487813` и последующую замену одного ключа `9d3315e8`; идентичность коммитов через Git здесь не проверялась. Исходники, Git и активные прогоны не изменялись; тесты, серверы, модели и провайдеры не запускались.

## 1. Исходный terminal receipt

Сохранённый [pytest.log](../execution/evidence/backend-full-final1/20261011T213948955124Z/sqlite/pytest.log) заканчивается:

```text
FAILED tests/test_learning_schedule_api.py::test_export_omits_null_sidecar_and_preserves_exact_saved_snapshot[sqlite]
FAILED tests/test_learning_schedule_api.py::test_two_http_writers_share_real_cas_and_preserve_other_json[sqlite-learning]
FAILED tests/test_learning_schedule_api.py::test_two_http_writers_share_real_cas_and_preserve_other_json[postgres-learning]
3 failed, 4911 passed, 42 warnings in 588.75s (0:09:48)
```

Название каталога `sqlite` не означает, что все случаи использовали только SQLite: лог явно содержит упавший вариант `[postgres-learning]` и PostgreSQL migration setup.

Первое падение показывает точную разницу `updated_at`: экспорт вернул `2026-10-11T21:43:30.383828`, а helper ожидал `2026-10-11T21:43:30.383828+00:00` (лог:72–79). Два остальных падения сравнивали сохранённый `learning_path` с обогащённым ответом PUT; лог показывает несовпадение `schedule` (105–149), но не полный поключевой diff. Объяснение разницы ниже основано на исходниках, а не на отсутствующем полном diff.

## 2. Native wire timestamp и сохранение JSON

**Исправление корректно.** [Helper:292](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_learning_schedule_api.py:292) сохраняет отдельно:

- `created_at` и `updated_at`, нормализованные через `ensure_utc`, для точной проверки неизменности строки БД;
- `updated_at_wire = row.updated_at.isoformat()` для точного сравнения существующего экспортного контракта.

[Export route:324](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_profile.py:324) возвращает именно `item.updated_at.isoformat()` и сырой сохранённый `item.learning_path`. При SQL NULL поле sidecar опускается. Исправленные assertions [323](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_learning_schedule_api.py:323) и [368](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_learning_schedule_api.py:368) проверяют эту форму целиком, а не допускают произвольный timestamp или подмножество JSON.

Сохранены проверки: ровно три ключа legacy export при NULL, точный заполненный sidecar, revision/settings, exact attempt receipt и profile, counts, отсутствие изменения БД после GET/export, неизменность остальных входных данных. Это исправление ожидаемого wire representation; оно не меняет production serialization и не ослабляет проверку сохранности данных.

## 3. Raw snapshot и текущая проекция — разные точные assertions

**Исправление соответствует контракту.** [Preview:328](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_preparation.py:328) и [Save:397](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_preparation.py:397) конструируют snapshot одинаковым pure builder. Save хранит `snapshot.model_dump(mode="json")`, затем возвращает `_learning_view`.

[LearningTask:79](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/learning_schedule.py:79) по умолчанию имеет `submitted_attempt_id = None`. [Current view:203](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_preparation.py:203) строит отдельную модель и обновляет отображаемые `as_of`, baseline age, overdue/remaining и найденный receipt UUID для точного `(profile, lesson_id, content_version)`; сохранённый JSON этим GET не перестраивается.

В corrected CAS test [529](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_learning_schedule_api.py:529) теперь раздельно проверяются:

1. `after["learning_path"] == proposed["learning_path"]` — целиком правильный raw snapshot;
2. `outcomes[winner][1]["learning_path"] == current["learning_path"]` — целиком правильный текущий DTO при фиксированном route clock;
3. непустой набор именно нужных lesson/version tasks и точный `submitted_attempt_id == payload["attempt_id"]` у каждого;
4. draft и legacy settings отдельно, а также `needs_review is False`.

Это сохраняет точность обеих сторон контракта вместо ошибочного требования, чтобы stored JSON и derived DTO совпадали.

## 4. Ключ `version` в входном attempt

**Одноключевое исправление корректно.** На [test:540](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_learning_schedule_api.py:540) сравнивается `task["learning_ref"]["content_version"] == payload["version"]`.

- [StudyAttemptIn:91](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/preparation.py:91) принимает `version`.
- [body helper:141](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_preparation_api.py:141) формирует `version`, а не `content_version`.
- LearningRef и stored StudyAttempt используют внутреннее имя `content_version`; граница этих двух представлений уже существует в API.

Здесь нет `.get(...)`, fallback или пропуска проверки exact version. Сообщённое родителем падение diagnostic5 самостоятельно не воспроизводилось и его лог в этом review не читался.

## 5. CAS и guards сохранены

Проверяемый тест [438](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_learning_schedule_api.py:438) по-прежнему использует два HTTP клиента и две реальные DB connections, barrier перед SQL UPDATE после обоих prechecks, явный winner и ограниченные ожидания. Listener снимается в `finally`. SQL UPDATE не подменяется.

Сохранены строгие assertions: winner `200`, loser `409`, обе роли ровно один раз, две connections, та же row identity/created_at, revision ровно `+1`, response revision совпадает с БД, winning JSON не потерян, соседний JSON сохранён. При legacy winner сохранён старый sidecar и выставлен `needs_review`; при learning winner сохранены legacy ticks. Export/deletion тесты и case ownership checks не отключались.

## Вывод

**В проверенных test-only исправлениях новых blockers не обнаружено.** Они адресуют ошибочные ожидания тестов и соответствуют текущим storage/API contracts, сохраняя meaningful проверки export preservation и shared CAS. Этот вывод ограничен статической проверкой и исходным full-final1 receipt.

По последнему сообщению родителя `diagnostic6 → full2` активны на замороженном исходнике. Их успех, frontend gates, release, deployment и live search-quality этим документом не подтверждаются. Для runtime вывода нужен terminal receipt соответствующего свежего прогона. Все действующие STOPs сохраняются.
