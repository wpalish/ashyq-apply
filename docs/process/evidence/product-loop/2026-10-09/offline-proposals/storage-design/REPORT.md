# Долговечные отметки подготовки: минимальный следующий шаг

9 октября 2026. Только статический аудит текущего source. Код, API, БД, миграции, тесты и приложения не запускались; primary/Git/STOP не менялись. Runtime-сохранность после входа и с другого устройства здесь не подтверждается.

Сервер уже хранит **требования**, **выборы пользователя** и **заметки**. Выполненные пункты подготовки — пока только браузерные галочки. Минимальный следующий increment: сохранить эти самоотметки на сервере отдельно от доказательств требований, привязав их к текущему пользователю, кейсу, конкретному result и версии checklist. Общий planner, загрузка файлов и статус готовности заявки для этого не нужны.

## Что сейчас сохраняется

| Данные | Реальный контракт | Ограничение |
|---|---|---|
| Кейс и research run | ApplicantProfileRow.organization_id; ResearchRun.profile_id | Доступ ограничен организацией/workspace, а не индивидуальным автором кейса. |
| Programme result, checklist | ProgramResultRow хранит payload и отдельный checklist JSON; document stage записывает новый список и вызывает save | GET результатов читает checklist из payload. Это важный источник истины для будущей версии, не отдельная колонка сама по себе. |
| Choice/reason/notes | Decision и notes endpoints меняют row/payload, пишут AuditEvent, commit | Это server storage; retry переносит выборы и заметки. |
| Галочки документов | localStorage `ashyq.docsDone`; ключ `${result.id}::${d.name}` | Один origin-wide объект; нет user_id, checklist revision или item id. |
| Черновик профиля | localStorage envelope на case_key | Локальный несохранённый draft, не серверные отметки подготовки. |
| Активный кейс/run | sessionStorage per tab; switchCase загружает server case и последний run | Новое устройство не получает этот навигационный указатель автоматически. Это не потеря сохранённых server данных. |

Источники: [models/research.py](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/models/research.py:114), [models/applicant.py](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/models/applicant.py:25), [tenancy.py](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/api/tenancy.py:12), [results GET](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/api/routes_results.py:125), [decision/notes](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/api/routes_results.py:253), [runner retry carry-over](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/pipeline/runner.py:1630), [Documents local storage](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/frontend/src/screens/DocumentsScreen.tsx:24), [caseDrafts](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/frontend/src/lib/caseDrafts.ts:1), [switchCase](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/frontend/src/lib/store.tsx:555).

Отдельной сущности durable preparation task/progress и соответствующего endpoint в просмотренном app source не найдено. Существующие action lists — требования по участникам подготовки, не записи о выполненной работе. [DocumentItem / DocumentChecklist](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/schemas/result.py:259) не имеют item id, revision, completed или completed_by. `generated_at` — дата построения, не версия; [collect()](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/adapters/documents/web_documents.py:221) задаёт её заново.

## Конкретные риски текущего ключа

1. **Одинаковое имя означает одну галочку.** Название повторяется в admission/scholarship или у разных участников — оба пункта используют один result/name ключ. Счётчик завершённых пунктов тоже проверяет этот ключ. [DocumentsScreen:192](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/frontend/src/screens/DocumentsScreen.tsx:192), [DocumentsScreen:219](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/frontend/src/screens/DocumentsScreen.tsx:219); [actions population](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/adapters/documents/web_documents.py:764) объединяет admission и scholarship lists.
2. **Пересборка не проверяет смысл отметки.** Result id сохраняется при retry, checklist заменяется; изменившиеся deadline/format/translation/prompt/scope при прежнем имени наследуют старую галочку. Переименование или новый run/result, наоборот, теряют связь. [runner:1590](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/pipeline/runner.py:1590), [runner:1477](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/pipeline/runner.py:1477).
3. **Это не персональный account storage.** Documents не читает principal. Sign out вызывает logout/reload, не очищает docsDone. Во втором устройстве ключа нет; в общем браузере он остаётся. Если два пользователя той же организации открывают тот же result, они увидят общий локальный ключ. Утечка server данных между разными организациями этим аудитом не доказана. [App sign out](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/frontend/src/App.tsx:393), [logout](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/api/routes_auth.py:189), [organization ownership](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/api/tenancy.py:27).
4. **Два таба могут перезаписать карту.** done загружается один раз; каждый toggle записывает весь объект из собственного React state. Нет чтения свежей карты/storage-event merge. Удаление кейса на сервере также не удаляет этот браузерный ключ. [Documents:26–52](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/frontend/src/screens/DocumentsScreen.tsx:26), [profile deletion](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/api/routes_profile.py:377).

## Один bounded backend increment

Добавить **личные самоотметки пунктов существующего checklist** как отдельный progress resource. Ключ записи: authenticated user + result + checklist_revision + item_ref. Через result → run → profile проверяется case/organization; client не назначает user/organization. Это личные отметки аккаунта внутри доступного кейса. Existing workspace-wide choices/notes остаются в прежнем контракте; совместные отметки команды — отдельное будущее решение.

- Revision и item_ref выдаёт сервер для **точного API-visible checklist**. Нельзя строить их из названия или subset frontend полей: backend DocumentItem содержит source scope, которого сейчас нет в TypeScript interface. [backend scope](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/schemas/result.py:285), [frontend item shape](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/frontend/src/types.ts:311).
- Практичный первый контракт: deterministic revision по полному сериализованному checklist, исключая только generated_at, плюс identity programme/result. Любое другое изменение создаёт новую revision; никаких name/fuzzy переносов отметок. Внутри revision item_ref отличает actor group и конкретное вхождение — одинаковые имена не сливаются. Более умный перенос между revision/run не нужен для первого шага.
- GET progress рядом с result возвращает revision, текущие item refs и marks. PATCH одного item принимает **абсолютное** `done: true/false`, revision и версию записи для защиты от старого ответа/параллельного изменения. Повтор не инвертирует галочку. Несовпавшая checklist revision или конфликтующее старое изменение — явный conflict, без молчаливого переноса.
- Revision membership и запись проверяются в одной транзакции с актуальным result; worker не пишет progress и не смешивает его с payload/checklist evidence. Чтение/отметка ничего не fetch/collect/research/rerank. При отсутствии checklist нельзя создать произвольный пункт через этот endpoint.
- UI загружает progress для account/case/result/revision, сбрасывает предыдущий view при переключении и отбрасывает опоздавшие ответы. Сохранение получает отдельное pending/saved/error состояние. Старые origin-wide ticks нельзя автоматически назначать вошедшему пользователю; безопаснее потребовать повторную отметку, чем приписать чужую/старую готовность.
- Удаление user/case/result должно удалять progress по тем же явным privacy/cascade правилам; export должен включать допустимые самоотметки пользователя. Не менять source claim status, eligibility, checklist completeness или готовность заявки на основании галочки.

Новые места логично рядом с существующими [result routes](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/api/routes_results.py:310), [research models](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/models/research.py:114), [client API](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/frontend/src/api/client.ts:298) и DocumentsScreen. Это design recommendation; schema/migration/API patch не подготовлены.

## Acceptance для будущей реализации

| Проверяемый сценарий | Обязательный результат |
|---|---|
| Reload, logout/login того же пользователя; другой browser/device, выбран тот же кейс | Подтверждённо сохранённые marks восстанавливаются с сервера. Не обещать автоматический active-case pointer. |
| Чужая организация / guessed run/result / anonymous | Нет чтения/записи чужих marks; действуют native 401/404 boundary. |
| Два пользователя одной организации и один result | Личные marks изолированы по principal; нельзя передать чужой user_id в body. |
| Переключение case/programme + поздний GET/PATCH предыдущего | Не окрашивает текущий checklist и не сохраняет отметку на другой result. |
| Повторный сбор: только generated_at изменён / изменено требование или scope | В первом случае marks сохраняются; во втором нужна новая revision, старые marks не считаются текущими. Unreadable-source retention остаётся authoritative native behaviour. |
| Два одноимённых пункта разного actor/purpose | Отмечаются независимо; счётчик считает реальные item refs. |
| Два устройства, повтор/старая запись, ошибка сети | Повтор не toggle; конфликт/несохранённость видны; нет скрытого whole-map overwrite. |
| Все пункты ticked при partial/unresolved checklist | Только self-reported progress; unknowns и completeness не меняются. Нет “application/admission ready”. |
| Удаление user/case/result и export | Нет orphan marks; export/erase контракт включает progress без чужих данных. |

Эти условия ещё **NOT RUN**. Проверка owner isolation должна использовать реальную auth-enabled конфигурацию: [security.py:197](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/security.py:197) при auth-disabled возвращает development principal и не является доказательством двух пользовательских аккаунтов. Deploy/configuration, транзакционная реализация и device behaviour остаются неизвестными до отдельного разрешённого increment и native checks.
