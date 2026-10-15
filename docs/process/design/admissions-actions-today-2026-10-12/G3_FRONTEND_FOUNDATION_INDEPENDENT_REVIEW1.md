# G3 frontend foundation: независимое чтение исходников

Статус: **COMPLETE SOURCE REVIEW — FOUR FINITE FINDINGS — NOT_IMPORTED / NOT_RUN / NOT_ACCEPTED**.

Проверен только первоначальный неизменный пакет `proposals/g3-frontend-foundation1`. Это заключение по предложенным исходникам. Оно не подтверждает применение пакета, прохождение TypeScript/Vitest/нативного браузера, готовность экранов или выпуск продукта. Первоначальные файлы и seals не изменялись. Более поздний отдельный ремонт удаления в этот отчёт не включён.

## 1. Граница и целостность

Авторитетный grant: [G3_FRONTEND_FOUNDATION_SOURCE_GRANT.json](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/G3_FRONTEND_FOUNDATION_SOURCE_GRANT.json), SHA-256 `c124334f58ace1eb942b1d36cb542aa682f126197f12869d112d7a935a069e68`.

Исходный [SEAL.json](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-frontend-foundation1/SEAL.json), SHA-256 `e48a39997f0295d91710525fa3d4a0c873cf00e1397433ffc23b2b52de4c7b01`: все **19 из 19** объявленных членов сверены по полным байтам, размеру и SHA-256. Полностью прочитаны шесть postimages, три новых тестовых файла, additive diff клиента и README. Нативные зависимости проверялись чтением текста и конечных metadata; приложение, тесты и предложенные файлы не импортировались и не исполнялись. AST, форматирование, lint, DB, браузер, Git, сеть и остановленные процессы не запускались.

| Postimage | Строк | SHA-256 |
|---|---:|---|
| frontend/src/types/admissionsActions.ts | 464 | `e074818ed5b0943bfee10aa97aba7567bc4b4e6a3dbb25c1c96901b65f37cd07` |
| frontend/src/api/client.ts | 626 | `c385422b02ffc3816bfb251834a002abe9f6719714653342bc31c45bde6c71a8` |
| frontend/src/lib/admissionsActionsRecovery.ts | 538 | `b95410e93644b93506e2891565b80ebf341ebb78d3c65cf18022f7c85a2e4f6c` |
| frontend/src/lib/admissionsActionsRecovery.test.ts | 372 | `fa441aaa3b641bb413e10662a84ea98cb59c3a434d7924832148cb4f7e84b6ef` |
| frontend/src/api/client.admissionsActions.test.ts | 82 | `cdae06735b638875077b08e36f1484ef76e4903f3e90d294b81d645375c7a92f` |
| frontend/src/types/admissionsActions.test.ts | 95 | `f54f3a02bd363e13ed277c83e4defd6603b82815e6fc0e335315f351ec477659` |

Контракт API сверялся с неизменными wire1 / API source1 и текущими нативными схемой, domain, клиентом, `applicantStorage` и Store. Полные SHA прочитанных зависимостей записаны в companion review seal. Статус других локальных gates не переносится на этот пакет.

## 2. Подтверждённые чтением дефекты

### F1 — P1: поздний успешный DELETE A после переключения на B не выводит журнал A из обращения

Путь: [admissionsActionsRecovery.ts:473](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-frontend-foundation1/postimages/frontend/src/lib/admissionsActionsRecovery.ts:473). `acknowledgeAdmissionsCaseDeletion` вызывает `active(binding)` в строке 477. `identityFailure` в строках 120–125 требует, чтобы активные `profile_id` и `case_epoch` всё ещё принадлежали A. `ownFamilyKeys` и повторные проверки при очистке используют ту же активную анкету.

Нативный сценарий разрешён: [store.tsx:890](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/lib/store.tsx:890) захватывает A, ожидает настоящий `api.deleteProfile(A)`, снова проверяет владельца, очищает именно A и лишь в строке 904 проверяет устаревшую операцию. [switchCase:364](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/lib/store.tsx:364) меняет epoch/generation и не отменяет уже посланный DELETE. Поэтому одна и та же авторизованная сессия может активировать B до получения успешного ответа A. Новая функция возвращает `case`, не устанавливает tombstone и оставляет A доступным для последующего восстановления. README допускает очистку только «before the store changes its case epoch», что не покрывает уже существующую нативную гонку.

Минимальное исправление: отдельный authority check **только для подтверждённого удаления**: текущий нативный owner/scope, совпавший captured `acknowledgedProfileId`, точная собственная family и её captured generation/fence. Не требовать, чтобы текущая активная анкета/epoch оставались A; обычные read/journal/retry/command-ACK проверки активной анкеты оставить без ослабления. Для удаления нужен собственный bounded scan с такими же проверками вокруг I/O. Tombstone должен побеждать позднюю alive-инициализацию. Повреждение, race или отказ очистки сохраняют `residual_unknown`, B и чужие family не трогаются.

Нужный контроль: journal A и B → начать DELETE A → активировать B → получить настоящий успешный ACK A → tombstone/retirement только A, байты B неизменны. Дополнительно отказ DELETE, смена owner, ошибочный ACK case, чужой/заменённый generation не дают полномочий на очистку. Текущие тесты строк 215–256 и 348–356 покрывают удаление при всё ещё активном A, но не этот сценарий. Runtime-воспроизведение не выполнялось.

### F2 — P2: повторное подтверждение возвращает проверенный entry вместе с уже изменившимися raw bytes

Путь: [admissionsActionsRecovery.ts:452](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-frontend-foundation1/postimages/frontend/src/lib/admissionsActionsRecovery.ts:452). `inspectCase` проверяет entry в строке 438, затем выполняются два асинхронных hash-ожидания. В ветке уже acknowledged entry строки 452–455 сравнивают ACK ref, повторно читают raw и проверяют только `raw !== null`. `readRaw` проверяет owner/family, но не структуру новых байтов. После same-owner изменения raw во время этих ожиданий функция может вернуть `{ok:true, entry:<старый проверенный>, raw:<новый повреждённый>}`. Это нарушает заявленный unchanged-byte refusal; серверное подтверждение при этом может оставаться достоверно известным.

Минимальное исправление: после финального read повторно parse/canonical-compare **полного** raw entry с проверенным entry, как уже делает pending ветка в строке 461. `null` или изменённая семантика → `changed`, malformed → `invalid`; никаких переписываний повреждённых данных. Локальный отказ не должен отменять отдельно известный реальный ACK сервера.

Нужный контроль: сначала корректно acknowledged entry; во время проверки повторного ACK same-owner storage меняет его raw на malformed или другой entry; replay обязан отказать, сохранить новые байты и не сообщать локальный verified-success. Положительный неизменный replay строки 106 остаётся. Новое runtime-исполнение не выполнялось.

### F3 — P2: строгий wire guard допускает singleton JSON arrays вместо enum strings

Пути: [admissionsActions.ts:298](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-frontend-foundation1/postimages/frontend/src/types/admissionsActions.ts:298), строки 358, 390, 406.

`includes(String(value))` принимает, например, `responsible_actor: ["applicant"]`, `report.state: ["prepared_reported"]`, а в receipt `status: ["planning"]`. JavaScript преобразует одноэлементный массив в строку, однако исходный массив остаётся в объекте. `journalAdmissionsAction` доверяет этому type predicate и может записать массив как будто это строго типизированная команда. Нативные `ResponsibleActor`, `ReportState` и `ApplicationStatus` — Literal string enums, поэтому такой JSON не соответствует закрытому контракту; серверное принятие этих массивов не утверждается.

Минимальное исправление: перед finite enum membership проверять `typeof value === "string"`, либо использовать только прямые literal comparisons. Не нормализовать и не исправлять пользовательские значения. Аналогичную enum coercion в receipt guard устранить тем же способом. `prior_declaration.kind` отдельно уже проходит строгий `event` guard, поэтому его текущий String вызов не считается самостоятельным обходом.

Нужные controls: массив, объект и boolean вместо каждой затронутой enum строки не проходят shape/request guard и journal; правильные scalar строки, Unicode и исходные пробелы личного текста сохраняются. Текущие новые form tests проверяют CAS coercion/extra fields, но не эти enum arrays. Runtime не запускался.

### F4 — P2: rehashed shape-valid ACK может содержать delta, не соответствующий исходной команде

Путь: [admissionsActions.ts:421](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-frontend-foundation1/postimages/frontend/src/types/admissionsActions.ts:421), recovery строки 404–449. Проверены два точных несовпадения:

1. `select_active_preparation`: строки 448–450 проверяют нулевые apps/tasks и event ref, но не равенство `delta.active_preparation.observed_head` и `request.observed_head`. В delta можно заменить один валидный собственный native head другим, сохранить event и заново вычислить self-hash. Нативный [validate_receipt_delta:1350](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/admissions_actions.py:1350) такой ACK запрещает.
2. `create_personal_task`: общий `taskRecord` допускает источник с binding, а command-specific строки 455–460 возвращают true после проверки количества. Можно скопировать валидный ранее принятый binding/binding_ref/source origin в личный create-task ACK, сохранить точные own latest refs и пересчитать outer self-hash. Нативная [схема:1461](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/admissions_actions.py:1461) требует именно `binding=null`, `binding_ref=null`, `origin=applicant_entered`.

Recovery проверяет hash предоставленного ACK, но hash не доказывает эти command→delta отношения. Поэтому такого self-consistent corrupt input достаточно для локального acknowledged ref. Это дефект клиентской проверки испорченного входа, **не утверждение**, что текущий backend выдаёт такие ACK, и не объявление SHA подписью сервера. Helper не сохраняет или применяет полный delta к текущему состоянию — это ограничивает последствия, но не делает ошибочную локальную retirement проверку верной.

Минимальное исправление: сохранить закрытую форму и добавить exact relation для этих двух случаев, сравнивая typed native UTC/UUID в канонической семантике, без изменения исходного отправленного тела. Нужны rehashed adversarial controls: изменённый selected head и personal create с copied-valid binding должны отказать и оставить pending journal; настоящий bind-source и настоящий selector с эквивалентными Z/UTC microseconds должны по-прежнему пройти. Исходные тесты ACK corruption строк 108–121 не пересчитывают hash и потому не проверяют эти semantic mismatches. Runtime не запускался.

## 3. Что подтверждается исходниками, с пределами доказательства

| Область | Наблюдение | Предел |
|---|---|---|
| Закрытый transport | Названы ровно 12 команд; нет `replace_state`, произвольного snapshot-command или selector clear/none. 7 новых методов повторяют wire URL/verb/body; history cursor 0 передаётся строкой, identifiers/timezone кодируются. | TypeScript compilation и реальный HTTP ещё не проверялись этим review. |
| Текущий клиент | Diff содержит только type import и 7 методов. Старые request/auth/download/legacy/G2 тела не изменены. Новый transport использует credentials, native errors и owner проверки перед запросом/после headers и успешного body. | На экранах дополнительно нужны profile/epoch/request-generation checks; transport owner fence сам по себе не является case fence. |
| Ревизии | Writable expected max2147483646 отделён от readable saved/head max2147483647; строгие integer/boolean/extra-field проверки присутствуют. | F3 мешает считать все scalar enums строго закрытыми. |
| Digests | Known typed UTC canonicalized к `+00:00`, nonzero microseconds дополнены до 6 цифр; UUID только для сравнения приводится к native lowercase. Local dates/times, Unicode/notes и исходный отправленный JSON сохраняются. Digest wrappers/keys совпадают с нативными request/receipt. | Прочитанные synthetic select-plan controls подписаны Node SHA над явной Python-канонической формой; это источник теста, а не исполненный межъязыковой результат. F4 отдельно о semantics. |
| Owner/case lifetimes | Owner включает auth user+org или явно связанный demo; нет anonymous adoption. Family разделена по exact encoded case; random generation и case_epoch защищают owner/case ABA; tombstone отдельный. | F1 — исключение на нативном позднем DELETE; обычные guards сохранять. |
| Journal и retry | Сохраняется только личный command input + refs/digests/CAS/UUID/status; journal должен успешно завершиться до caller dispatch; hydration не отправляет запросы; explicit retry возвращает исходные UUID/body, без нового preview/revision. | Caller обязан не посылать после storage/index отказа, сохранять известный ACK отдельно от местной cleanup ошибки и показывать guard/error. Экраны не часть этого пакета. |
| Локальный индекс | Advisory descriptor index, отдельные UUID entries; exact bounded scan/hashes/readback; повреждения/index loss не сбрасываются, reconciliation только явно. Соседние UUID не стираются при ACK. | `localStorage` не объявлен atomic CAS или межустройственной синхронизацией. F2 — недостаточная финальная проверка в ACK replay. |
| Privacy/legacy | Нет material/current/Today/full ACK/actor/auth keys/private attachment snapshots. ACK ref имеет 4 reference поля. Legacy candidates — только literal true, исторические time/version unknown; source-bound mapping требует разрешённого API preview. ACK не меняет raw `docsDone`/false-to-true/чужие ключи. | Raw legacy mark attribution не доказательство официальной готовности; это будущий explicit matching/import UI. |
| Today/source DTO | В типах отдельно self-report/official not_performed, source stale/locked/unknown, date uncertainty, mixed reads, один selected plan, personal minutes not_estimated/readiness not_assessed. | Foundation не реализует экраны, source href display, selection/rebind UX или Today→lesson/review navigation. |

## 4. Прочитанные тесты: смысл и недостающие проверки

Manifest сообщает **87 proposed cases** (31 forms + 10 transport + 46 recovery), подсчитанных автором по тексту. Это не результат test collection и не PASS. Во всех трёх новых файлах controls прочитаны целиком; старые тестовые файлы в allowlist не входят и их assertions этим пакетом не меняются.

Содержательные имеющиеся controls:

- все 12 positive commands и закрытые negative command families, exact limits/duplicates/Unicode/confirmations/личные даты;
- direct immutable command JSON, owner change до HTTP/после response headers/после body; fixed error propagation и неизвестный network outcome без автоматического повторения;
- original UUID/body через journal/retry и caller edits; owner/case/epoch/ABA fences и асинхронные hashes;
- foreign/corrupt/extra/oversized entries/indexes; missing-index reconciliation; sibling insertion during index write без ложной atomic CAS;
- storage quota/read errors сохраняют исходные bytes, no dispatch success;
- matching active-case DELETE tombstone, malformed residuals, late write/alive initializer; literal legacy marks и сохранение raw после import;
- UTC Z/short fraction/microseconds, uppercase original UUID, reference-only ACK persistence, exact family delimiter и clone before caller mutation.

Конкретные незакрытые controls — F1–F4 выше. Никаких runtime статусов или исправлений в первоначальном пакете не подразумевается.

## 5. Обязательная поздняя UI интеграция: finite journal retention

`G3_RECOVERY_ENTRIES_MAX=64`, per-entry256KiB, index128KiB. **Acknowledged entry сохраняет исходный personal intent/body и занимает один из 64 UUID slots**. В строках recovery 357–358 новый journal при заполнении отказывает; автоматического удаления acknowledged entries нет. README честно называет отдельный explicit retention UX, и это не дефект backend/domain лимита.

До выпуска экранов нужно явно решить управляемую пользователем retirement/retention подтверждённых local entries: сохранить неизвестные/pending UUID и исходный body, не стирать новый intent или соседнюю анкету, не объявлять cleanup atomic/полным и не удалять историю сервера. При storage/refusal нельзя ни автоматически POST, ни молча выкидывать старые подтверждения, ни предлагать удалить всю анкету как нормальный способ продолжить работу. Нужен осмысленный cap64→следующий запрос control после выбранной пользователем cleanup, включая отказ storage и concurrent newer pending.

Дополнительная уже заявленная граница: legacy snapshot helper отказывает при >50 literal true candidates (raw map≤4000), без усечения. Будущий UI должен показывать этот отказ и выбирать bounded reviewed import без переписывания raw marks. В foundation нет cross-device draft sync, logout или deletion UI, unsaved-leave guard, automatic retry или полноценной проверки href перед отображением — их готовность этим чтением не устанавливается.

## 6. Решение и следующий конечный шаг

Первый foundation пакет целостен и соответствует шестипутевому объёму, но **принятие отложено из-за четырёх конкретных source findings**. Parent получил точные места и минимальные remedies; автору отдельно поручен только finite deletion repair. Новые изменения должны сохранять этот первоначальный seal и применяться исключительно root после разрешённого review.

Нужны отдельные narrow fixes/controls F1–F4, затем root native static/Vitest и позже screen/native acceptance. Этот review не создаёт новый дизайн freeze, не меняет существующие STOPs и не подменяет execution gates. Полный продукт, официальная отправка заявок, подтверждение университетом, обучение/оценки, production release и live search quality остаются отдельными результатами.
