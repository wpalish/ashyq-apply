# Финальная приёмка сохранённых backend receipts

**11.10.2026 — QUALIFIED_FULL_NATIVE_BACKEND_RECEIPTS_ACCEPTED.**
SQLite и private Unix PostgreSQL завершились PASS. Это закрывает backend gate
для зафиксированных байтов; serialized seed и native E2E root ещё выполняет
отдельно. Предыдущий SQLite partial/PG_PENDING сохранён как промежуточный снимок.

Reviewer независимо проверил terminal result, raw summaries, XML/JSON coverage,
JUnit identifiers, source maps, guards, cleanup и hashes. Reviewer не запускал
app/tests/БД/Git/browser/providers и не менял source/helper. Reviewer написал
API40 proposal: это независимый просмотр чужого исполнения, не blind acceptance
независимым от автора тестов человеком.

Run: `evidence/backend-full/20261011T145907489813Z`.
Metadata, все61 проверенных artifact hashes и точные новые IDs:
[backend-terminal-pins.json](backend-terminal-pins.json), SHA256
`6f48441eb60431acf436ae91bf15bb2ea85d0372ba3d010d0bf6c46303c21e75`.

## Фактические результаты

| Полная native фаза | JUnit, уникальные cases | F / E / skips | Coverage statements | Raw pytest duration |
| --- | ---: | ---: | ---: | ---: |
| SQLite | 4773 /4773 | 0 /0 /0 | 15280/16002 = **95.488063992001%** | 545.06s |
| PostgreSQL | 4773 /4773 | 0 /0 /0 | 15279/16002 = **95.48181477315336%** | 547.20s |

В каждой raw summary42 warnings. Launcher durations548.841s/550.927s — другая
граница измерения, не противоречие pytest duration. Оба receipts: pytest exit0,
no timeout, `FULL_NATIVE`, весь `tests`, `--cov=app --cov-fail-under=92` без
понижения порога. Coverage JSON и XML совпадают по numerator/denominator и с
receipt percentage. Overall resultPASS и embedded phase objects точно равны
отдельным phase result.json. Conditional fallback `postgres_if_not_started=NOT_RUN`
в overall — не фактический PG status: PG phase реально присутствует и проверена.

## Точное сохранение tests и source

Принятый final predecessor:
`exam-preparation-2026-10-11/evidence/backend-binding-final/20261011T134306725752Z`.
В обеих его фазах4682 уникальных PASS без F/E/skips. **Все4682 ключа и старые
test/fixture bytes сохранены**, разница ровно91: **51 pure** совпали с pinned
focused JUnit, **40 API** — с полным AST expected set, включая fixture SQLite/PG
и все explicit parameters. Иных новых/потерянных keys нет. Между текущими фазами
JUnit key sets идентичны. Это4773 разных case keys, повторно исполненных в двух
database phases, а не9546 разных проверок.

Все четыре before/after maps текущих фаз содержат601 path и идентичны, общий SHA
`0a74726e1786830705563e144a4b52cb8981a10b1c39b802d8632ee5e51e2f47`.
**563 required source hashes** совпали в каждом map. От predecessor595 delta
точно соответствует native-binding:5 declared changes,6 additions,0 removals.
Schema/planner остались reviewed259a752f/a3cf27e1; final native pure-test hash
02ec1c66 отражён в expected map после root native import/format; API52204a8c
совпадает с reviewed proposal. Actual native execution связан с этими final
hashes; isolated receipt не используется вместо native gate.

Root объявил frozen source005ac46b. Reviewer подтверждает content binding и не
выполнял Git для независимого подтверждения commit identity. Первоначально root
указал более ранний `backend-full/20261011T124000847599Z` с4653 cases; ошибочный
pointer и его исправление сохранены, старый receipt не перенесён на final4682.

## Изоляция и cleanup

- Все25 `evidence_hashes` каждой фазы совпали; отсутствующих файлов нет.
- По13 guard receipts; outside_attempts[] и startup failures[] в обеих фазах,
  app_preimportedfalse, IPv6 trait restoredtrue. Main process driver guard
  installedtrue:819/820 разрешённых private PG checks. Двенадцать children
  stdlib-armed/optional-driver-deferred,0 PG calls; не заявляется вызов libpq
  guard в каждом ребёнке.
- Saved OS probes: parent и настоящий Bash/Python descendant подтвердили
  AF_INET/AF_INET6 bind/connect/sendto refusal, private `SELECT1` PASS.
  Reviewer не совершал новых network/port/database probes.
- shutdown_confirmedtrue, runtime_removedtrue, active_cluster_markers[] в обеих
  фазах; оба указанных runtime paths отсутствовали при read-only проверке.

## Границы заключения

Проверены native ownership404, term/quota separation, retained expired history,
actual revision create/update/stale409, unknown/future422, exact export,
unchanged academics/profile.updated_at/research/payment state, profile HTTP
delete при SQLite FKoff, реальные migrations и finite planner controls.
Sequential revisions не доказывают concurrent HTTP race; profile HTTP deletion
не равен новому account-delete HTTP E2E. Calendar IDs не credentials, не globally
case-unique provenance и не подтверждение score/действия ученика.

Нужны отдельные actual serialized seed и native E2E receipts. Этот review не
принимает frontend/browser flow, deployment, real paid account, booking,
institutional certificate receipt, score growth или полный IELTS/SAT course.
Native historical offline regression replay не измеряет current search quality:
**NOT_MEASURED; GLOBAL_PROVIDER_STOP / UNSCORED остаётся закрытым**.
