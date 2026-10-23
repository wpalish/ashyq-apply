# Frontend learning path — interface и native-controls static review

**QUALIFIED_STATIC_ACCEPT: подтверждённого блокера нет.** Проверен замороженный external UI packet (10 paths), final backend contract и текущие root native controls. Reviewer не запускал приложение, тесты, браузер, DB, сеть или providers и не менял primary/proposals. Это разрешение статической части интеграции, без runtime PASS.

## Seal и границы

- UI READY: `ba47653207f872a2868307abeedb716d5b974389acd55a080ddca248cd48a1a8`.
- MANIFEST: `a38c543e38976434476950dfdcdbab8fe219898d6d0633204cb98d9d0434739c`: все **81 entry** независимо совпали по SHA256 и размеру.
- Patch: `a1700dd9787860857cab5d4165a712deea1ddebffe68d512c67890f6b00b6607`.
- Final backend contract: `fa13b5868a1af9987ccbf398e51d924508f6a5e6af5989bbacbc685ba16a32df`, совпадает с `BACKEND_CONTRACT_FINAL.md`. Ранние снимки контрактов сохранены как история, а не authority.
- [Seal/current pins](frontend-learning-path-review-seal.json). Все 10 current source application preimages совпали / новые пути отсутствуют. Старый auth input pin UI относится к исходным 7 сценариям: root append сверён отдельно.

## Совместимость production paths

- **DTO/API** — `types.ts:754–806`, `client.ts:425–446`: legacy choice question/answer/feedback не получают null/tag поля; short union отдельный. No-argument catalogue/progress URL остаётся legacy, opt-in использует `catalogue_version`; lesson берёт собственный summary version. Review GET адресуется client UUID. Submit JSON не нормализует текст.
- **Exact catalogue и порядок** — `PreparationScreen.tsx:113–120,147–158,203–209,285–294`: экран требует pack version, per-lesson version и version-qualified completions; порядок берётся из track.lesson_ids. Полученный lesson ID/version проверяется до формы. Старый starter в pack остаётся starter-v1. Next lesson появляется только после accepted receipt и использует exact summary version.
- **Submission/receipt** — `:346–384,386–407`: один immutable payload/UUID сохраняется до успешной квитанции или явного нового intent; synchronous inFlight исключает двойную отправку. Поля блокируются во время запроса и после ошибки, retry повторяет payload. Сравнение receipt проверяет profile, lesson, version, client UUID, количество/порядок question IDs и исходное choice/text value. Case/whitespace/final stop не меняются UI. Feedback private fields читаются из accepted receipt; клиент не содержит grader/variant matcher.
- **Ownership/late responses** — `:38–50,90–107,129–198,348–359`: render-time caseLoading gate и key из identity/profile/caseEpoch сбрасывают форму/history на switch-start; mount/owner сверяются перед применением ответов. Lesson/review/progress intent исключают старые selection responses. Выбор нового mode/lesson и закрытие review инвалидируют pending review. Native selector client UUID согласован с review endpoint.
- **Сохранённая работа после expiry** — `:182–198,307–331,421–434`: review не зависит от learning access, но проверяет profile, client UUID, DB ID, lesson ID/version и returned exact public lesson. `lesson:null` показывает явное отсутствие original text и stored IDs; никакой current-version lesson fetch/regrade не выполняется. Incorrect feedback сортируется первым в копии массива. Raw history/correctness явно не называется mastery/official score/readiness.
- **Календарь/Academics/quota**: новых write calls, automatic task completion, baseline/official score mutation нет. StudySchedulePanel byte-exact. Доступ получен из preparationAccess, не research quota/full_access. Expired term оставляет history доступным; server402 остаётся authority для нового submit/lesson.

## TeachingText и новый native delta

`TeachingText.tsx:4–17,25–29,34–77` — bounded escaped React renderer, без HTML parser, dangerouslySetInnerHTML, исполнения ссылок или grade data. Сохраняет paragraph/list text; semantic table использует thead/th scope=col/tbody/td. Table wrapper `:53` имеет `role=region`, `aria-label=Lesson table 1`, `tabIndex=0`; CSS `unimatch.css:316–322` ограничивает inline size и предоставляет внутренний horizontal scroll. Unsupported syntax остаётся текстом; это finite subset, не полный Markdown engine.

Новый current `learning-path.spec.ts:87–96` отличается от первого review ровно 10 appended lines: normal Start quadratic click, real heading, semantic table/region visibility, focus/focused assertion, document overflow и screenshot при конечной ширине **320**. Текущий SHA256 `1f9e159319c4f94e6557f89019fefa10231e8db3506c1bd392656d0db7e46e7e`. Предыдущий native review `515bb5…` сохранён отдельно; его runtime статус не переносится. Selectors совпадают с renderer. Контроль не проверяет фактическую прокрутку table с клавиатуры или физический notch/zoom; это не требуется для данного bounded static verdict.

Остальные native selectors согласованы: Answer1..5, next-lesson ID/version, client UUID review-attempt/saved-attempt-review и ошибочный feedback first. Auth current hash `4591986814ac67f16d2b2c4900db4663164329b1fe4c268602b84fbcc88d97cf` неизменён. Независимо повторено: 8 481 байт / 157 строк / первые 7 test declarations из именованного c8bd7204 полностью сохранены как prefix.

## Сохранность контролей и saved receipts

- Старый PreparationScreen file восстанавливается **байт-в-байт** при отмене трёх объявленных изменений: fixture import, default mock на opt-in learningCatalogue и один более точный assert query version. Все 19 прежних test declarations сохранены; это явная адаптация контракта, не заявление об абсолютно неизменённом файле.
- client.preparation.test, StudySchedulePanel production/test и preparation.spec.ts byte-exact против packet originals/current source.
- Сохранённый author accepted JUnit содержит **68 уникальных tests, 0 failures/errors/skips**; type/lint/build receipts имеют exit0 и exact source-before=after. Это selected mocked offline author results; whole integrated frontend/native E2E/runtime результатов reviewer не создавал и не приписывает.

## Остаточные gates

Root должен применить exact packet и выполнить whole frontend static/tests/build, full backend SQLite/private PG с обычным coverage floor, serial owned native Demo/Auth и проверить реальные API/UUID/history/table/screenshot/cleanup/source pins. Последовательный HTTP replay не доказывает concurrent insertion race. Native authored specs не доказывают network isolation/provider-none сами по себе; это отдельные launcher/runtime receipts. Physical safe area, viewport<320, text zoom, педагогическая эффективность, calibrated difficulty, score conversion и production/deployment не заявляются.

Reviewer — автор backend contract/implementation proposal, но не UI/native-controls автор. Это независимая проверка frontend seams с открытой квалификацией; отдельный backend content/compatibility review выполнен другим агентом. Sealed UI и primary не изменены.
