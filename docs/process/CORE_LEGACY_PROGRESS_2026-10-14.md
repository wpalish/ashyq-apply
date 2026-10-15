# Unimatch — закрытие N01/N02 и оставшаяся очередь

> 15 October update: N10/N11 adjacent profile lifecycle failures were independently reproduced and repaired on executable9ca4d307. Current FE944 and real nativeDemo7/Auth7 qualify those transitions. See [N10/N11 qualification](PROFILE_LIFECYCLE_N10_N11_2026-10-15.md). Earlier gate records below keep their original scope; complete product/release acceptance remains OPEN.


14 октября 2026. Исправленный executable **e58e541588d778835009b57b672e9c0ac367a333**. Root работает один, source6paths; старые API/backend/migrations без изменения.

## Пользовательский результат

Конвертация GPA, чтение транскрипта и предложения больше не применяют ответ к другому делу или прежнему GPA. Проверка анкеты относится только к текущему вводу; старая ошибка не стирает новый успешный отчёт. Возврат A→B→A и GPA edit→revert проверяют поколение, а не только совпадение ID/значения. Просмотр методов связан с текущей шкалой. Пользовательские предложения применяются явно; сохраняются нормализация, newer typing и подтверждённое сохранение.

Reuse: существующий synchronous currentAdmissionsCase, Store/normalized profile save. Change: единый in-memory setter/currentProfileDraft с semantic/GPA generations, request serial/input fingerprints и guards для success/failure/cleanup. Это клиентский контракт, без новой схемы БД/транспортных DTO/библиотек.

## Реальные проверки и границы

- OFF на старом коде: 20 deferred scenarios, 1 PASS / 19 material FAIL. Это 19 сценариев двух причин, не 19 новых багов. Первая ошибка среды127 (не было node_modules в primary) сохранена; reused existing installed dependency tree, без установки или сети.
- После исправления: первоначальные20 PASS, затем дополнительный контроль accepted transcript/edit→revert in one batch. Финальный общий frontend: **878 PASS /87 files**, types/build PASS, lint0errors/9старыхwarnings. Первая полная проверка с11новыми warnings сохранена; исправлены зависимости/hooks без suppressions; финальная9.
- Настоящий локальный сервер/браузер: **Demo1 PASS + Auth1 PASS**, тот же полный native admission путь, две программы, ручные и связанные записи, Today/history, reload/second login/second browser, widths320/768/1024/1440, export/delete. 489 consumed files exact primary/lab/before/after, собственные порты5261/8171 очищены, после удаления все проверенные case-owned tables0. Это SQLite native путь; новых PostgreSQL гонок не запускали.
- Прежний полный backend5840на каждой БД/94.23% переносится только потому, что все645 consumed files совпадают побайтово. Это **не новый backend прогон**. Прежние8 native stories относятся к старому frontend source; текущих свежих native stories здесь2.
- Raw JUnit/logs содержат intentional error/React fixture traces. Повторяющиеся20 currentAdmissionsCase TypeError/12 read-hook frames уже были в старом857логe; это не вызвано incrementB. Внешний аудит exports/test-fixture contracts остаётся открытым. Raw whitespace не исправляется: source/HANDOFF whitespace PASS, proof originals unchanged.

Доказательства: `evidence/core-legacy-races-2026-10-14/checkpoint-b1` и `checkpoint-b2`, SHA/size INDEX и внешние оригиналы. Все first failures сохранены. Hosted CI NOT_RUN, live/model/provider calls отсутствуют, production unchanged.

## Что остаётся

N01/N02 — implemented/locally verified/integrated locally. N03–N09 остаются открыты. Следующий один шаг: C, спроектировать атомарную revision/precondition всех writers ApplicantProfileRow, включая rerank persist_profile, совместимость клиентов и сохранение original creation intent/unknown ACK. До source — complete writer matrix, protocol/preimages/finite grant и tests-first двух реальных Session на SQLite/PostgreSQL.

После C: D results writers/notes drafts; E mutation freshness/deadlines/export errors; F scholarship exact result+award и recovery/history; G remaining semantic ranges. Every-line audit NOT_COMPLETE. Поиск NOT_MEASURED; лимит300vs120 не принят; old STOP/security refusal/CLOSED_UNSCORED/heldout150 неизменны. Fresh evaluation/main/release/operator/backup/ingress/published signed-in smoke не приняты. Полный продукт к выпуску не объявлен готовым.


## Более поздний checkpoint C1 — незавершённая интеграция

На обеих реальных БД воспроизведена N09: два клиента с исходнымP0 получали200, второй стирал первое изменение. Добавлены serverrevision, обязательный expected header, атомарный UPDATE и тот же precondition для explicit persisted rerank. После исправления4/4 native scenarios проходят (2каждойБД), static417PASS/heada1. **Клиент ещё не подключён:** его PUT не отправляет новый header, toDraft пока не удаляетrevision; сохранение существующего дела на нынешнем task source получает428/422. Поэтому N09 не закрыта, текущий полный backend/UI acceptance отсутствует. Не использовать прежние B878/native2 как подтверждение нового API контракта. Production/main не менялись. Точный остаток и следующая finite C2 spec находятся в HANDOFF§5; creation/replay/merge остаются design only.


## C2 — connected command protocol, focused qualification

2026-10-14T15:23:07.510436+00:00. Existing profile Save now sends captured revision and excludes server metadata from draft/validation. Unknown response retains original command in owner/tab journal16; explicit retry reuses UUID/body/revision. Create replays its original accepted profile and deleted replay refuses410. Conflict GET preserves newer typing; three-way comparison changes only local draft, then explicit Save creates new UUID at reviewedrevision. Original conflict remains recorded as conflict, never ACK. Save/startRun/persistedrerank share the path; failed/conflicted/unknown save cannot launch research.

Fresh frontend897PASS, types/build/lint0errors/9existingwarnings; focused backend19PASS across actualSQLite/privatePG, including simultaneous SQL-entry barriers and immutable replay; exact650server consumerpaths/guardoutside0/cleanupPASS. Ruff/format/mypy419PASS. Fullbackend, authenticated actor/namespace erasure/migration proof and current coupled browser scenarios remain pending, so N09 and product acceptance remain OPEN. All first failures retained in checkpoint-c2; old read-hook mocked fixture traces remain open. No main/production/search quality change.


## C3 — current coupled qualification

2026-10-14T16:22:25.967071+00:00. Real cookie-principal tests found and repaired own-target404 order and account command-namespace erasure on SQLiteFK-off. Guarded migration/legacyroundtrip passonbothDB. Actual browserdrop committed201 proved realnetworkerror becomesApiError0; correctedunknown classification and truthful restoredSaved indicator. Full existingfrontend902PASS, types/lint/build and backendstatic420PASS. RealDemo4/Auth4 stories pass completecore and two-context independent/samefield conflict/newertyping + originalcreateUUID/body replay after lostACK/reload; 501primary/lab/before/after consumers exact, ownports clear. All originalfailures preserved. Current fullbackend92 gatepending; N09 stillOPEN until it, N03-N08/F/G/search/launch unchanged.


## Current final C qualification

Executable5364dab9. Full5871 eachDB/94.19%; frontend905/types/lint/build, backendstatic420; nativeDemo4/Auth4 on501 exactconsumers/ownports clear. ProfileN09 locallyqualified; fullreport CORE_PROFILE_PROTOCOL_ACCEPTANCE_2026-10-14.md and current hash-indexed archive. N03-N08/F/G/search/launch remainOPEN; D/E drafts not applied. All STOPs untouched.
