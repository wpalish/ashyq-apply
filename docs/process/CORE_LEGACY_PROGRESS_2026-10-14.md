# Unimatch — закрытие N01/N02 и оставшаяся очередь

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
