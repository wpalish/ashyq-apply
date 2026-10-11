# Персональный календарь: ограниченный статический review

11.10.2026. **В прочитанном снимке нет подтверждённого блокера для интеграции
ограниченного календаря. Это не runtime PASS и не приёмка полного курса.**

Reviewer независимо от автора прочитал целиком предложенные schema/planner/pure
tests, а также новые native model/migration/API/CAS/export/cascade и существующие
tenancy, learning access, account-deletion и fixture seams. Reviewer сам написал
отдельную API-test proposal; её тесты не являются независимым исполнением.
Приложение, тесты, БД, Git и providers reviewer не запускал; source не изменён.

## Привязка к байтам

Финальный прочитанный schema: `259a752f19438af1ce7e72e1659844e314cca3c532ac30e0143649855b63218f`.
Planner: `a3cf27e10590be233df29b367b811a93cf7942e9776cdee59465a3aef464cb83`.
Pure tests: `d2e5338a895f03daf79bea508febea72d458191a613df824bf9188c938e966e5`.
API tests: `52204a8c5c897b3a327d1f74a6e8225a84614c89e519c31ef31a124650b7b194`.
Полные content pins: [backend-schedule-pins.json](backend-schedule-pins.json).
Все девять native dependency pins совпали с исходным API-test checkpoint.
Root должен отдельно связать receipt с итоговыми интегрированными байтами;
эта проверка не утверждает какой-либо Git HEAD или состояние deployment.

## Проверенные контракты

- `ScheduleSettings._settings`, schema:84–138: личные target/baseline keys,
  диапазоны, конечные числа, связанная baseline date, последовательность дат,
  горизонт365 и обе границы календарной арифметики. Schema:142–144 ограничивает
  revision для следующего SQL Integer. `build_schedule`:45–46 отклоняет будущий
  diagnostic относительно переданного локального today.
- `build_schedule`:52–109: результат, доставка и safety представлены как
  **введённые пользователем предположения**. `within_entered_buffers` не означает
  официальный deadline/доставку/готовность. `readiness` всегда `not_assessed`;
  нет часов→score conversion, admissions probability или новых Claim/RequirementCheck.
- Planner:120–126: исправленная нагрузка распределяется по номинальным выбранным
  weekdays. Неполная неделя и день экзамена оставляют неиспользованный резерв,
  не превращают короткий последний день в искусственный180-minute mock.
  Planner:195–202 требует полный180-minute резерв и предшествующее покрытие навыков;
  внешняя длительность/assessor всё равно требуют подтверждения.
- Planner:111–119,136–142,171–178,284–300: прошедшие задачи сохраняются;
  today/checkmarks не входят в structure fingerprint. Возраст baseline меняет
  diagnostic/status, а дата reassessment фиксирована по baseline+31. Неизвестные
  либо структурно устаревшие completion IDs отклоняются; changing settings требует
  явного сброса отмеченных задач.
- Planner:22–25,89–95,218–234: только три реальные starter links и только для
  соответствующего навыка; IELTS Writing/Listening/Speaking не выдаются за Reading.
  Повторная сдача появляется только после ввода retake date и остаётся неподтверждённым
  бронированием/правом сдачи. Календарь не устанавливает optional/waiver/official minima.

## Persistence/API

`routes_preparation.py`:49–110: GET/PUT сначала проверяют owned profile. GET доступен
после истечения term и пересчитывает только view; PUT требует separate preparation
access. ACTIVE/EXHAUSTED учитываются только внутри начавшегося term, quota0 не
снимает доступ; helper не тратит и не изменяет quota/status.

Первое сохранение использует unique profile и rollback/409 при коллизии. Обновление
использует SQL predicate по ожидаемой revision и increment, с rollback/409 при
отсутствии совпадения. Последовательные controls не доказывают concurrent HTTP race.
Проекция не пишет academics, profile.updated_at, research или score.

`StudyScheduleRow` и миграция `a9e5c14d2021` после `f1a2b3c4d511` согласованы:
JSON settings, unique profile, positive revision, FK CASCADE. Applicant ORM relation
использует `all, delete-orphan`, `passive_deletes=False`, поэтому существующий
`delete_account` explicit `session.delete(profile)` также включает календарь при
SQLite FKoff. Owned export включает settings/revision/timestamp/count. Account HTTP
deletion с новым календарём пока не доказано отдельным исполнением.

## Подготовленные проверки и остаточная приёмка

AST: **20 pure test functions /51 ожидаемый case**; API proposal:
**12 functions /40 ожидаемых SQLite+PG cases /81 assertion nodes**. Reviewer не
собирал и не запускал их. Native fixtures сохраняют миграции, synthetic identities,
private Unix PostgreSQL и outbound refusal; TestClient без lifespan.

После author READY отдельно проверены все21 manifest entries: bytes/hash совпали;
manifest SHA256 `34dc55f42b11655f69ddbc949794e128e96c507f8ef8241f928109b2aec19648`.
Сохранённый `focused-sealed.xml` действительно содержит **51 уникальный case,
0 failures/errors/skips**, log сообщает51 PASS за0.09s; receipt exit0 и tested pins
совпадают с прочитанными тремя файлами. Сохранённые Ruff/format/mypy receipts
exit0 относятся только к этим трём файлам в isolated staging. Это подтверждение
чужого сохранённого focused запуска, не запуск reviewer и не native/API/PG/full
gate. Initial50PASS/1FAIL и import-only repair сохранены; exact initial pre-format
source bytes автор не сохранил, что явно указано в receipt и ограничивает carry.

До итоговой приёмки нужны actual native static gates, full SQLite+private PG
coverage≥92, receipts source-before/after и guard/cleanup, frontend/native E2E
сохранение→reload→отметка→изменение структуры/reset, stale revision и смена кейса.
Необходим отдельный просмотр UI response fencing и честности отображения буферов.
Этот review не проверял UI. Подтверждение места, retake rules, recipient deadline,
официальной доставки и достижимости балла остаётся вне календаря; текущие
официальные ограничения описаны в [official-timing.md](official-timing.md).

Ранняя draft-заметка о subtraction underflow закрыта: прочитанная schema130–138
явно проверяет обе арифметические границы, pure tests содержат ancient/far-future
controls. Полное расписание является одним активным личным планом, не полным
IELTS/SAT course, сертификатом, score forecast или доказательством production.
