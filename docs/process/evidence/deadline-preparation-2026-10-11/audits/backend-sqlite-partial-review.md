# Backend receipt: SQLite подтверждён, PG_PENDING

**Статус: SQLITE_RECEIPT_VERIFIED / PG_PENDING.** 11.10.2026.
Reviewer прочитал только разрешённые сохранённые SQLite receipts после terminal
сигнала root. Текущую PostgreSQL-фазу, её логи и результаты reviewer не читал.
App, tests, БД, Git, providers и gates не запускались; source/helper не изменены.

Текущая фаза:
`evidence/backend-full/20261011T145907489813Z/sqlite`.
Полная metadata-привязка: [backend-sqlite-partial-receipt.json](backend-sqlite-partial-receipt.json).

## Фактический SQLite результат

- JUnit: **4773 testcases /4773 уникальных ключа; 0 failures, 0 errors, 0 skips**.
  Receipt pytest exit0, no timeout, modeFULL_NATIVE, selection `tests`,
  `--cov=app --cov-fail-under=92`. Raw summary:
  `4773 passed, 42 warnings in 545.06s (0:09:05)`; launcher duration548.841s.
- Coverage JSON: **15280/16002 statements =95.488063992001%**, выше неизменённого92.
- Correct final predecessor
  `exam-preparation-2026-10-11/evidence/backend-binding-final/20261011T134306725752Z/sqlite`:
  **4682 уникальных PASS, 0F/E/S; все ключи сохранены**.
- Разница ровно **91**:51 pure keys полностью совпали с pinned focused JUnit;
  40 API keys полностью совпали с AST-ожиданиями, включая обе native fixture
  labels sqlite/postgres и все term/invalid параметризации. Никаких иных добавленных
  или потерянных ключей нет. Это реальный native API40 результат внутри SQLite-фазы,
  не замена ещё идущего второго полного PG-прогона.

## Байты, guards, cleanup

- Все **25** файлов `evidence_hashes` существуют и совпадают по SHA256.
  Result SHA `4d314ffdeba940e676c85b613fcf7b3a971d7831ecae4cb35464ef8d50d214ef`;
  JUnit `3b59ae24177b2e54b7a03601fca94c57a1517192255a47816c6397ab788754dd`.
- Source-before и source-after содержат **601** идентичный consumed path,
  одинаковый JSON SHA `0a74726e1786830705563e144a4b52cb8981a10b1c39b802d8632ee5e51e2f47`.
  Все **563** required hashes совпали в обоих maps. Относительно predecessor595
  delta ровно соответствует native-binding:5 declared changes,6 additions,
  0 removals; старые test/fixture пути не изменены. Root объявил frozen source005ac46b;
  reviewer не выполнял Git и не независимо подтверждал commit identity.
- **13** guard receipts: outside_attempts пусты во всех; app_preimportedfalse и
  IPv6 trait restoredtrue. Главный процесс имеет driver guard installedtrue и
  **819 allowed private PG checks**;12 child receipts имеют stdlib guard armed,
  optional drivers deferred и0 PG checks. Это не утверждение, что libpq был
  установлен/вызван в каждом ребёнке.
- Сохранённые OS probes подтверждают6 AF_INET/AF_INET6 bind/connect/sendto refusals
  у parent и настоящего Bash/Python descendant; private probeSELECT1 PASS.
  Receipt: guard_startup_failures[], outside_attempts[], active_cluster_markers[],
  shutdown_confirmedtrue, runtime_removedtrue. Указанный runtime path также
  отсутствует при read-only filesystem проверке. Отдельные network/port probes
  reviewer не выполнял.

## Исправленный predecessor и ограничения

Root сначала указал `backend-full/20261011T124000847599Z`; его XML фактически
содержит4653 cases до29 evidence-binding controls. Неверный pointer сохранён
в metadata; он **не используется** как accepted4682 receipt. Root предоставил
исправленный `backend-binding-final/20261011T134306725752Z`, сравненный выше.

Reviewer написал API40 proposal и квалифицирует независимость: это независимый
просмотр чужого saved execution, не blind test-author-independent acceptance.
Completion IDs — детерминированные calendar/settings IDs, не credentials,
globally case-unique provenance, scores или подтверждение действий ученика.
Sequential revision controls не доказывают concurrent HTTP race. Profile HTTP
delete/FKoff PASS не равен новому account-delete HTTP E2E. Native synthetic/private
lab не означает production, deployment, live quality, целый курс или score growth.

**Итоговая backend приёмка остаётся PENDING** до terminal PostgreSQL receipt,
его exact JUnit/pins/coverage/guards/cleanup и согласованного итогового результата.
Frontend/E2E — отдельные gates; этот partial review их не принимает.
