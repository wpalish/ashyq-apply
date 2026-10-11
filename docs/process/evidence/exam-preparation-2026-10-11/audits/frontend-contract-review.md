# Независимый frontend/API contract review подготовки

**Вердикт: условно принять статический контракт; мобильный layout требует отдельного исправления/проверки перед mobile acceptance.** Подтверждённого blocker в новых ownership, UUID retry или entitlement правилах не найдено. Это review замороженного предложения, не подтверждение root-applied bytes, успешного native gate, full course, deployment либо search quality.

Reviewer не писал frontend/E2E; он автор backend foundation и участвовал в согласовании DTO. Поэтому проверка frontend независима от его автора, но backend contract здесь не является blind review. Source/proposals/Git не редактировались, тесты/серверы/браузер/сеть/провайдеры не запускались. Единственная запись — этот внешний отчёт. Root отдельно сообщил применение 30 файлов на `f0bf24b9` и native I001 findings с последующим import-only исправлением; результаты ниже привязаны к исходному immutable packet, не к ещё не проверенным форматированным applied bytes.

## Точные границы и pins

- Frontend `READY.json`: `bb27841114906893c7b8d6964fe2aa5281d7cc5a3f2ed85b5ac3f17eac239f9c`.
- `MANIFEST.json`: `7f11e84fc3eb8e2bf416a0dbbe9c144cbb198390f252c927d678f5a8ab7cc9ff`; независимо проверены **27/27** записей по размеру и SHA, расхождений нет.
- Frontend patch: `3540c12ab2a33114b95f62f45e44d10d8467525d54e7fa2c53b9a50c1f8025f6`.
- Agreed backend CONTRACT: `681cca32ae0ed6d96e0e149d379ec3916e65b639f55a29ad51c81bd0ad6c3809`.
- Root `e2e/preparation.spec.ts`: `b3e092f8409bca0da2b731642e82886c91dcc497ac51233494a79233f2bf2e09`.
- Root `e2e/auth-journey.spec.ts`: `c8867af545bcf6f8c8ef5394a3eac49b3e1b78ca47ea4d1955afc723a40d1999`.

Пути frontend ниже относительны `proposals/frontend/files/frontend/src`; пути E2E — `proposals/root/files/frontend/e2e`. Контекст Store/CSS/helpers прочитан из owned integration source; Git head reviewer не проверял.

## Проверено по коду

| Контракт | Конкретное доказательство |
| --- | --- |
| Unsaved/неподтверждённый owner | `screens/PreparationScreen.tsx:34–45`: отсутствующий identity/case не запускает запросы; loading скрывает старый child; key включает identity, profile ID и caseEpoch. Store switch-start увеличивает caseEpoch и loading до await (`source/frontend/src/lib/store.tsx:363–366`). |
| Поздние ответы | `PreparationScreen.tsx:80–121,129–155,158`: live owner + mounted, cleanup/active, lesson/progress intent и exact result ID; progress/attempts проверяются на свой profile. API owner checked до fetch и после response/body (`api/client.ts:135–179`). |
| UUID и дубли | `PreparationScreen.tsx:258–288`: payload захватывается один раз в pending ref до await; inFlight ref исключает вторую отправку до React commit. Retry использует тот же UUID/lesson/version/answers; receipt сверяется с этими полями и profile. |
| Ошибка сохранения | `PreparationScreen.tsx:290–315`: после ошибки нет saved/feedback; выбранные ответы заморожены для неизменного retry, явный restart создаёт новую lesson session. Нет обещания draft persistence после ухода/refresh. |
| Официальные результаты | Компонент вызывает только шесть preparation методов; не updateProfile/createProfile/startRun. Raw correct/total подписан practice only, completion — submitted, not mastered (`PreparationScreen.tsx:237–245,291,306–315`). |
| Entitlement отдельно от quota | `PreparationScreen.tsx:48–58,129–130,207,222`: используется серверный preparation access. Billing inclusion только из optional preparation_access собственного profile (`BillingScreen.tsx:34,76–83`), без вывода из CASE_FULL или cases left. Prep402 не classified как case purchase (`api/client.ts:80–89,93–123`; client control:55–64). |
| Evidence и будущие курсы | `PreparationScreen.tsx:175–234`: locked не раскрывает checks; исходные values/explanation/scope/excerpts/URL/status сохраняются; planned exams не имеют local practice кнопок. UI не вычисляет собственный числовой admission goal, IELTS band или SAT score. |
| Навигация/фокус | App entry, Home и Plan используют `#/preparation`; existing main focus contract сохраняется (`App.tsx:222–224,435,452`). Остальные research/documents действия остаются присутствующими. |

Native unit proposal содержит **32** явных cases (16 screen + 7 client + 4 Billing + 5 shell), reviewer прочитал все. Это статический count, **NOT_RUN**: они моделируют late A→B/owner/lesson, immutable retry, expiry/history, locked/waiver scopes и wrong-case response. Они не заменяют реальный backend/Playwright gate.

## Конкретная мобильная seam — требуется решение

**F-PREP-MOBILE:** `App.tsx:95–102` увеличивает PRIMARY_NAV до **6** элементов. Native неизменный `source/frontend/src/styles/unimatch.css:389–398` при width ≤900 делает fixed bottom nav с `repeat(5, minmax(0,1fr))` и прежним `.main` bottom reserve `4.5rem`. Шестая кнопка неизбежно уходит в отдельную вторую строку; узкий текст «Exam preparation» дополнительно переносится. Это подтверждённое несоответствие числа кнопок/grid, не доказанный screenshot/runtime clipping. Возможное закрытие нижних действий нужно измерить, а не объявлять состоявшимся.

Root уведомлён. Нужен сознательно выбранный layout для шести пунктов с соответствующим bottom/safe-area reserve и native mobile проверкой, что Submit/Restart/последние controls доступны при нижней прокрутке и не перекрыты fixed nav. Не заявлять mobile polish PASS из существующих jsdom cases.

## Root E2E и оставшиеся acceptance условия

Селекторы root соответствуют фактическим lesson titles, трём authored radio labels, nav-preparation, Programme evidence, practice-result/data-attempt-id и progress-summary. Demo сценарии проверяют Find→Save Delft→сохранённый IELTS writing, actual API submit/replay, неизменность полного academics, reload/history и own `study_attempts` export. Auth addition проверяет тот же сохранённый UUID из второго свежего browser context с тем же аккаунтом; это сильнее browser-only local state.

Не приписывать этим сценариям то, чего они не утверждают: в demo E2E `preparation.spec.ts:38–39` lesson response проверяется на ok, **JSON answer-key absence не проверяется**; `:29` writing проверяется на видимость, **отсутствие несоответствующего Reading goal не утверждается**. Это покрывается отдельными backend/domain controls после их реального запуска; при заявлении именно browser proof нужны соответствующие assertions. E2E сами по себе не доказывают чужой tenant, paid/exhausted term, вставочный API race или отказ сети; bounded unit/backend controls и root receipts должны быть приведены отдельно.

До итогового acceptance нужны exact applied source pins после native import formatting, type/lint/unit/build, native isolated API/migrated PG/backend coverage gate, demo/auth Playwright и mobile seam verification. Существующая stored-evidence/access view — снимок после GET, не обещание автоматического live-policy refresh. Ни одного дополнительного прогона/изменения reviewer не выполнял.
