# G2 recovery — FINAL V1, sealed design only

**DESIGN_ONLY / NOT_APPLIED / NOT_IMPORTED / NOT_RUN.** Root reconciled receipt is authoritative for the exact 15 frontend paths and preimages. Root reports terminal PASS for previous 624-source backend qualification and seed/head; this design does not create a fresh runtime qualification.

History: first mutable draft hash was recorded as fde0eb9202f4c8dd424dbaae0d2f22d6ebe46b65f0a04282c0838ab0096b2aec. Those earlier bytes were not preserved or independently validated. The current original draft 5da0c47e84e291bc30f689ea4733c54259d85f1ef4ec2c06476da5a7c0afc8fa is retained unchanged, with a byte-exact copy DESIGN_ONLY_AT_RECONCILIATION.md. This separate FINAL V1 replaces weaker draft wording with reconciled root resolutions; it does not rewrite that historical receipt.

# G2: ограниченное восстановление ввода и исходной команды

**12.10.2026 · EXTERNAL DESIGN ONLY · NOT_APPLIED / NOT_IMPORTED / NOT_RUN.** Root — единственный writer приложения, Git, HANDOFF, helpers и runtime. Root сообщает terminal seed/head gates и отсутствие активного runtime; полного terminal receipt этот документ не квалифицирует. Последний application HEAD `26766a3d` указан root, Git здесь не запрашивался. Это отдельный план закрытия [source boundary](G2_UNSAVED_NAVIGATION_SOURCE_BOUNDARY.md); исходный owner report остаётся неизменным. Новых application/source/test/helper bytes здесь нет. Source proposal допустим только после нового root write-ahead.

## 1. Предпочтительное решение и граница

Использовать **sessionStorage отдельно для каждого проверенного owner и сохранённого case**. Root согласовал этот вариант. Он сохраняет ввод и непримирённую команду при переходах App, case A → B → A и reload **в том же табе**. Это не cross-device sync и не обещание восстановления после закрытия таба, очистки origin data или отказа самого браузера.

Ключ: `ashyq.owner.<encodeURIComponent(exact_owner)>.ashyq.sharedRouteRecovery.v1.<encodeURIComponent(profile_id)>`. Exact owner берётся из владеющего React tree: строковый `DraftIdentityContext` → `auth:<scope>`; `null` запрещает любые операции. `undefined` допускается только при native binding **ровно `demo`**, после явного auth-disabled AuthGate. Не использовать anonymous/unbound fallback адаптера. Перед каждым read/write/remove проверять `currentApplicantOwner() === captured_expected_owner`; stale/transition/signed-out tree не выбирает другой namespace, не читает его и не очищает.

Session storage выбран вместо shared per-case localStorage слота: разные табы одного owner/case физически не перезаписывают черновики друг друга. Новый таб может получить opener-copy sessionStorage; это отдельная локальная копия, а не синхронизация. Точный скопированный pending UUID остаётся безопасным replay; изменение ввода требует нового явного preview/save. Никакого нового глобального registry/private cache или backend/wire изменения.

## 2. Envelope и строгий restore

Новый browser-only envelope `v=1` содержит exact owner/case binding, случайный `draft_id`, ограниченный monotonic `journal_revision`, `saved_at`, `draft_generation`, **известные поля G2 form draft**, несохранённые `manual_id` / `manual_review` и nullable pending `{original_body, state, submitted_generation}`. `original_body` — полный неизменный `SharedRouteWriteV1`, включая UUID, ordered input, expected revision, source/preview hashes, legacy anchor и planned_on. Восстановление никогда не собирает этот body заново из редактируемой формы.

Разрешены только personal planning inputs, ordered result IDs, exact lesson/version/own-attempt references, integer minutes, даты и reference hashes. **Не хранить** preview allocation, current/history response, G1 names/proofs/quotes, lesson body, answers, private keys, tokens, cookies или premium entitlement. Existing exact version dispatcher остаётся авторитетом для открытия учебного материала.

Parser для unknown storage проверяет version/owner/case, exact allowed keys, UUID/ID/hash shapes, конечные bounded числа и известные типы полей. Пределы массивов: current UI 2–20 выбранных IDs / максимум 2 экзамена / максимум 400 own reviews; incomplete form draft может оставаться неготовым к отправке. Ограничить raw JSON 1 MiB и строки фактическими UI/schema limits; сохранить отсутствие необязательных target keys, не расширять их `null` defaults. Malformed/unknown-version/foreign envelope не показывается, не отправляется, не переписывается и не удаляется автоматически; видна причина. Только явный exact current-own-case local reset может удалить неподдерживаемые bytes, после проверки binding и exact raw equality. Он не удаляет namespace другого owner или case. Новый parser — не TypeScript cast и не изменение server validation.

Восстановление выполняется только после native verified owner + hydrated own profile. Draft помечается «восстановлен в этом браузере, серверу не сохранён». Pending `sending` после reload становится `uncertain`, потому что crash/reload не доказывает отсутствие commit. Restore не вызывает PUT, POST preview, allocator, research или новую попытку. Разрешён обычный owned GET: matching receipt сравнивается существующим `matchesSharedReceipt` с исходным body/UUID. Если validated own current head **строго больше** `original.expected_revision + 1`, разрешён **один** existing free-history GET именно этой целевой revision, bounded текущим own head. Исторический ответ проходит `matchesSharedView(profile,target_revision)` и затем exact `matchesSharedReceipt(original_body)`. Он может снять только matching pending, не заменяет displayed current новым/старым планом и не переписывает draft. Foreign/malformed/missing/mismatching current/history не даёт success и не стирает команду; никакого scan всех revisions, latest-version substitution или повторного распределения. History/reconciliation сохраняют существующие owner/access rules и доступны без нового learning term. Новый preview — отдельное действие пользователя.

## 3. Запись, ACK и защита нового намерения

Сохранять edits синхронно по событиям, без позднего debounce: next draft вычисляется вне React state updater; storage side effects не помещаются в render/updater, который StrictMode может вызвать повторно. Перед API PUT записать pending exact body; reload между записью и фактической отправкой остаётся harmless uncertain, без автоматического retry.

Если первичная запись command journal не удалась, **не посылать новый PUT молча**. Сохранить original UUID/body в памяти, показать «команда не отправлена: browser recovery недоступен»; при повторе сначала попытаться записать тот же body. Такой `storage_blocked/not_sent` — browser-only состояние, не fake unknown commit. Если уже отправленный запрос имеет unknown outcome, неудача записи journal при следующем retry сохраняет **uncertain/unknown**, а не переводит его в not_sent: прежний commit мог состояться. Уже dispatched pending, у которого последующая запись state не удалась, остаётся recoverable по сохранённому исходному `sending` body.

ACK/reconciliation очищает pending только при совпадении **owner + case + draft_id + original UUID + canonical full body** с текущим прочитанным envelope. Старый ACK не удаляет другую/новую pending команду и не записывает поверх нового journal revision. Если форму изменили после submitted_generation, очистить только принятый pending, сохранить более новый draft и явно разделить accepted revision от unsaved edits. Ошибка cleanup storage не отменяет настоящий server ACK: показать предупреждение; повторный restore может снова безопасно reconcile тот же receipt. Unmount не удаляет envelope. Явный discard также compare-and-remove только своего текущего envelope; нет indiscriminate prefix erase.

Сохранить существующие generation/intent/owner/case fences, `matchesSharedPreview/Receipt/View`, UUID-body replay и отсутствие automatic new save. Journal не предоставляет premium/term authority. Истечение срока не стирает accepted history и не превращает pending в новый intent; восстановленная команда допускает только существующий безопасный original replay/GET reconciliation. Fresh new save продолжает требовать новый валидный preview и текущий доступ.

## 4. Навигация, Legal и auth

Root выбирает `onLeaveRisk` из SharedRoutePanel через PreparationScreen в App: наружу передаётся только boolean risk + регистрационный token, а не private form/body. **Каждый meaningful несохранённый draft ИЛИ unresolved pending ALWAYS требует предупреждения при nav/case/hash/beforeunload, даже если journal записан успешно.** Accepted server ACK без более новых edits не является unsaved risk. App проверяет ref до изменения screen/hash/case; Cancel сохраняет экран и case, прямой hash/Back отменяется history.replaceState к последнему принятому hash до unmount. Разрешённый уход сохраняет journal, не запускает server save. Security owner transition/unmount выполняется безусловно, без dialog и без stale private write.

**Root-approved узкая Legal поправка:** public branch AuthGate только `route.startsWith('#/legal') && !status?.authenticated`. До auth/при неизвестном status legal остаётся публичным. Authenticated owner остаётся в своей keyed private tree и открывает уже существующий App LegalScreen (App:451), поэтому App guard остаётся единственным private route decision. Ни auth protocol, ни legal text/access не меняются.

Existing AuthGate.test.tsx:113–117 требует legal draft **до authentication**, поэтому это условие сохраняет проверку. Теста, требующего public wrapper для authenticated owner, в прочитанном файле нет. Добавить authenticated mount-count/cancel/legal/back control; сохранить immediate public-legal и native owner-transition-unmount controls. Explicit user logout может предупреждать о стирании browser drafts через существующий UI; **mandatory cross-tab auth unmount обходить/отменять нельзя**.

## 5. Delete/logout и чужие данные

Ключ с `ashyq.owner.` уже попадает в existing `removeApplicantData` по обоим browser storages. Поэтому успешный native logout/account delete/owner replacement использует существующий ACK cleanup; failed auth call сохраняет данные/восстанавливает binding. Не заменять его новым широким storage clear.

После успешного `deleteProfile(caseKey)` добавить exact captured-owner/case recovery cleanup рядом со store:899, до generation-return. Late delete A ACK при активном B очищает только A; failed delete не очищает. Авторитетный case delete удаляет все записи recovery **этого** case в данном табе, а не только старый UUID. Late ordinary save ACK очищает лишь собственную matching intent — это другой контракт. Старая async запись после case delete отсекается existing caseEpoch/owner fences. Другой таб не трогаем; при его fresh own GET 404 показывается unavailable и не выполняется восстановленный write автоматически. Нельзя толковать generic foreign/unavailable 404 как право удалить иной namespace.

## 6. Конечный список будущих путей и meaningful acceptance

Источник потребует отдельного root write-ahead **после terminal текущего runtime**. Предложенный конечный frontend список:

| Путь | Назначение |
|---|---|
| `frontend/src/lib/sharedRouteRecovery.ts` (new) | Strict browser envelope, explicit owner key, synchronous read/write/compare-clear, storage outcome. |
| `frontend/src/screens/SharedRoutePanel.tsx` | Restore/edit/pending journal, exact ACK cleanup, risk callback; immutable DTO/response fences остаются. |
| `frontend/src/screens/PreparationScreen.tsx` | Передать stable owner/case scope и риск; не хранить private bytes в App. |
| `frontend/src/App.tsx` | Screen/case/hash leave guards и beforeunload. |
| `frontend/src/AuthGate.tsx` | Только narrow public-Legal condition; security owner unmount неизменен. |
| `frontend/src/lib/store.tsx` | Exact case delete ACK cleanup. |
| `frontend/src/lib/i18n.ts` | RU/EN/KK восстановление, unsaved risk, storage failure, not-sent. |
| `frontend/src/screens/SharedRoutePanel.test.tsx` | Pure helper parser/owner/case/storage/exact-match controls и UI unknown-save restore; same UUID/body, no automatic POST/PUT, bounded old-revision history reconciliation, newer edits survive old ACK. |
| `frontend/src/App.preparation.test.tsx` | Nav/case/Back/direct-hash Cancel before unmount; accepted leave restores case draft; genuine saved state not guarded. |
| `frontend/src/AuthGate.test.tsx` | Public legal before auth / authenticated child preserved / security unmount immediate. |
| `frontend/src/lib/storeIsolation.test.tsx` | Late A deletion ACK preserves B journal; failed delete preserves A. |
| `frontend/e2e/preparation.spec.ts` | Один sequential native Demo recovery scenario через настоящий owned API. |

Исторический кандидат содержал 12 frontend путей. FINAL V1 следует **ровно 15 paths из G2_RECOVERY_WRITE_AHEAD_RECONCILED_V1.json**, включая отдельный pure helper test, privacy test и Auth native control; helper controls могут жить в existing SharedRoutePanel.test.tsx без отдельного test файла. Existing native client privacy controls остаются неизменными; новые test fixtures должны включить auth/demo journal под covered prefix и проверить acknowledged logout через настоящую existing client функцию с synthetic transport. Если root предпочитает отдельный pure test или новый Auth E2E, сначала добавить соответствующий путь в явный allowlist. Отдельный **logout-specific** dialog из Settings также требует `SettingsScreen.tsx`; этот документ сам такого source разрешения не даёт. Никакого изменения backend/model/migration/wire/legacy calendar/research/content/helpers.

Meaningful unit controls: storage read/write throw; invalid version/shape/NaN/oversize/foreign owner or case; explicit demo vs unbound; captured A tree после binding B не читает/пишет/удаляет; two independent session stores same owner/case не перезаписываются; UUID/body V остаются после ACK U; newer generation draft сохраняется после matching ACK; sending→uncertain restore; fresh GET mismatch не очищает; no preview/PUT until explicit click; hash cancellation не размонтирует; auth event не задерживается unsaved dialog.

Native Demo: создать synthetic own case/selection, заполнить draft, preview, вызвать real local PUT и сделать **одно заранее согласованное loopback-only lost-response injection** после actual server ACK (real `route.fetch`, без fabricated receipt). Зафиксировать исходный request UUID/body и accepted receipt. UI unknown → leave Cancel → accepted Home → preparation → reload с native warning. Restore делает только GET, находит точный receipt и очищает только matching pending; revision/history одна, personal inputs/exact refs не заменены. Второй вариант no-commit abort-before-send требует явного Retry original и тот же UUID/body; отдельный новый runtime разрешается только root. Никаких provider calls или ослабления network guards. Namespace/logout/clean-browser controls не обещают cross-device draft sync.

## 7. Более простой вариант и ограничения

Самый малый вариант — тот же scoped session journal без нового registry/router/provider, плюс согласованная narrow Legal поправка и App callback/ref guards. Это предпочтительный путь root. Один shared localStorage case slot **не** подходит: same-case tabs могут перезаписать draft; предупреждение без journal **не** закрывает reload. Временный вариант только warning+in-memory допустим лишь как отдельно принятое ограничение, не как закрытый owner §8.

SessionStorage доступен JavaScript этого origin и не является шифрованным сейфом; права сервера и existing CSP/session isolation остаются отдельными границами. Local recovery не доказывает актуальность requirement/source, не grant-ит subscription и не улучшает live search quality. Все перечисленные tests/native scenarios сейчас **NOT_RUN**.

## Source pins

Пины прочитанных ordinary source и принятых контрактов добавлены ниже отдельно; приложение не импортировалось.

## FINAL V1 authoritative source allowlist

- `frontend/src/lib/sharedRouteRecovery.ts`
- `frontend/src/lib/sharedRouteRecovery.test.ts`
- `frontend/src/screens/SharedRoutePanel.tsx`
- `frontend/src/screens/SharedRoutePanel.test.tsx`
- `frontend/src/screens/PreparationScreen.tsx`
- `frontend/src/App.tsx`
- `frontend/src/App.preparation.test.tsx`
- `frontend/src/AuthGate.tsx`
- `frontend/src/AuthGate.test.tsx`
- `frontend/src/lib/store.tsx`
- `frontend/src/lib/storeIsolation.test.tsx`
- `frontend/src/lib/i18n.ts`
- `frontend/src/api/client.privacy.test.ts`
- `frontend/e2e/preparation.spec.ts`
- `frontend/e2e/auth-journey.spec.ts`

## Exact root resolutions

- Scoped per-tab sessionStorage owner/case journal, no crossdevice unsaved sync
- Strict whitelist personal inputs/references only, raw JSON1MiB, current server constraints not widened
- Before new PUT durable originalUUID/body; storagefailure not_sent and no send; same original explicit retry only
- Restore sending→uncertain, GET only; if currenthead advanced attempt original expectedrevision+1 ownedhistory GET and exactmatch only, no search/automatic PUT
- ACK clear exact current owner/case/journal/UUID/canonical body, preserve newer editeddraft; mismatch/failure visible and not optimistic
- All meaningful draft or pending guarded nav/case/hash and beforeunload; callback registrytoken+ref no privatebytes App, security ownerunmount unconditional
- PublicLegal !status?.authenticated, authenticated existing AppLegal; preauth legal remains public
- Successful own caseDelete ACK cleanup exact capturedowner/case only; faileddelete no clear; existing logout scoped cleanup unchanged
- Existing native assertions intact, append finite loopback-only real route.fetch lostACK after serverreceipt; no fabricated response/provider/useuserDB
- Root sole app/Git/helpers/runtime writer; agent sealed external proposal only; full624 backend/wire must carry only exact equality, newFEstatic/native required
- All meaningful draft OR pending ALWAYS guards nav/case/hash/beforeunload, even successful journal; no storagefailed-only exception
- Pending journal write failure before initialdispatch is not_sent; failed later retry of alreadydispatched unknown must preserve unknown outcome, not label never sent
- Invalid/foreign/unsupported stored envelope never automaticallyadopt/overwrite/remove; only explicit exact currentowncase localreset can retire it
- Root receipt15source preimages remainexact, sourceproposal not runtimequalification
