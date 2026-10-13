# G3: независимая проверка finite frontend repair2

**SOURCE_ONLY / F2–F4 source-qualified / NOT_IMPORTED / NOT_RUN / не runtime acceptance.** Конкретного блокера в разрешённых четырёхфайловых изменениях не обнаружено. Проверка не подтверждает готовность интерфейса или выполнение новых тестов.

## Неизменность и точный объём

Проверен [repair2 SEAL](proposals/g3-frontend-review-repair2/SEAL.json) SHA256 `4d044d79309af4a6e155d41bcf470bc42410594f82213577186c2a7d895b9194`: **18/18** членов совпали по SHA256 и размерам. Прочитаны полные четыре diff, изменённые функции/контролы с контекстом, grant, manifest, README и preservation record. Все четыре diff точно воспроизводятся из фактических preimage/postimage bytes.

Проверены также все **19** членов исходного foundation `e48a39997f0295d91710525fa3d4a0c873cf00e1397433ffc23b2b52de4c7b01` и **12** членов DELETE repair1 `2c7d73199aa4a691257d5d9a7af59797949e3f5de57f443b49db4c3a2e9e43bb`. Recovery preimages точно равны DELETE1; type preimages точно равны foundation. Полномочия `d9c29375c853ac2b371dda23c16a7b8fb749b8969dcf584e43155409b2c73461` не расширены.

| Postimage | SHA256 |
|---|---|
| `frontend/src/lib/admissionsActionsRecovery.ts` | `d9984a8787d63b83a36f8f7d517a243a1e3759f31ae0fa67d3eadec6a6fd97cf` |
| `frontend/src/lib/admissionsActionsRecovery.test.ts` | `d3cb0183605cdedc0c86cbbd725d7f6935ff3301d96e5d116fae130037d842ef` |
| `frontend/src/types/admissionsActions.ts` | `034d76ca8483553eac17039d36cd98363865ca97eafca9009c312edbaf5341dc` |
| `frontend/src/types/admissionsActions.test.ts` | `12478b6e9996d589cf36068e4e67c2a2642ae98be9ce72d026e04dfae5658e78` |

## Закрытие трёх подтверждённых source findings

### F2 — ACK replay: ранее проверенная запись и новое чтение bytes

[Acknowledged branch](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-frontend-review-repair2/postimages/frontend/src/lib/admissionsActionsRecovery.ts:452) после последних hash awaits выполняет обычное owner/case/generation-fenced чтение, отклоняет отсутствие bytes и непосредственно сравнивает полный parsed canonical entry с ранее проверенным entry. Порядок ключей JSON не влияет на равенство; изменение значения, extra поле и foreign header не принимаются. Malformed JSON даёт `invalid`; различие даёт `changed`. В этой ветви нет записи или стирания журнала.

Новые [контролы](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-frontend-review-repair2/postimages/frontend/src/lib/admissionsActionsRecovery.test.ts:490) изменяют actual local entry при третьем digest — после его исходной проверки, перед final replay read. Проверяются сохранение изменённых bytes/index и отсутствие любых recovery writes сверх deliberate test interleaving. Положительный контроль допускает семантически одинаковый JSON с другим порядком ключей. Отказ локального retirement не отменяет независимо известный серверный ACK; его отображение принадлежит будущему UI caller.

### F3 — enum без String coercion

Пять прежних `includes(String(value))` заменены явным `typeof ... === 'string'` и проверкой значения: personal responsible actor, command report state, correction prior kind, receipt report state и application status. Closed enum values сохранены. Array/object/boolean не преобразуются в допустимый текстовый enum.

Три новых command-контрола и девять rehashed receipt-контролов проверяют actual guard/ACK retirement. Receipt negatives заново вычисляют digest, поэтому проверяют типовую границу, а не только старую подпись; неизменённый scalar ACK того же pending intent затем остаётся положительным контролем.

### F4 — точный native head и personal source association

[sameNativeHead](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-frontend-review-repair2/postimages/frontend/src/types/admissionsActions.ts:349) сначала требует строгий native head и сравнивает origin/profile/schema/revision. Для G2 сравниваются UUID, snapshot/allocation digest и accepted_at. UUID case нормализуется, `Z` и `+00:00` сопоставляются; fractional seconds дополняются до шести цифр без округления. `.123456` и `.123457` остаются разными. Для legacy V1/V2 сравниваются **все** соответствующие fingerprints/digests. Исходное тело не переписывается. Это соответствует frozen native [G2/legacy head classes](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/admissions_actions.py:469), UUID/UTC parser и [receipt observation equality](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/admissions_actions.py:1346).

[Personal-create relation](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-frontend-review-repair2/postimages/frontend/src/types/admissionsActions.ts:480) требует `binding === null`, `binding_ref === null`, `origin === 'applicant_entered'`, как [native receipt validator](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/admissions_actions.py:1461). Это два разрешённых прямых отношения, не копия всей native validation в браузере.

Проверены семь rehashed wrong-G2-head случаев, legacy V1/V2 negative с положительным ACK, и настоящий UUID/UTC transport positive с микросекундами. [Bound positive fixture](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-frontend-review-repair2/postimages/frontend/src/lib/admissionsActionsRecovery.test.ts:563) вычисляет самостоятельный Node SHA256 по native wrapper `g3-checklist-binding-v1`/`value` с каноническим UTC. Negative копирует это валидное source binding в personal-create и повторно хеширует receipt; genuine bound intent сохраняет positive ACK. Это synthetic unit fixture, не прочитанный официальный источник и не подтверждённое исполнение backend.

Native schema pin: `61ca24cc599bd215ef43a05a6d3a9f8e9ecaad33bde419bffa9fbc837b8ab43f` (59 070 bytes), совпадает с packet manifest.

## Сохранение прежних защит и статус

- Literal inverse единственного F2 hunk восстанавливает **весь** DELETE1 helper. DELETE-only блок, ordinary fences, original request/body hashing, pending ACK path и legacy helper неизменны.
- Literal inverse пяти enum replacements, private comparator и двух F4 relations восстанавливает **весь** foundation type module.
- Оба полных прежних test-файла являются **точными byte prefixes** новых файлов. Никакие старые assertions, controls или fixtures не удалены и не ослаблены.
- Source arithmetic: **28** добавленных случаев; ожидаемый total **130** (forms 34 / transport 10 / recovery 86). **NOT_COLLECTED / NOT_RUN**, не PASS.

Подключение actual UI/Store, guards навигации/драфтов, явная политика retention при 64 intent entries, source-bound type/lint/tests и native browser acceptance остаются отдельной работой root. Source-only закрытие F2–F4 не является whole-product readiness, publication или deployment. Reviewer не изменял приложение, seals исходных пакетов, Git, HANDOFF, конфигурацию или helpers; AST, imports, format, runtime, DB, browser, сеть и provider/model вызовы не выполнялись.
