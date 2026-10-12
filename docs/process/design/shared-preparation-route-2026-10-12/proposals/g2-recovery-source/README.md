# G2 — восстановление исходного намерения и браузерного черновика

**SEALED EXTERNAL SOURCE PROPOSAL · NOT APPLIED · NOT IMPORTED · NOT RUN**

Пакет содержит ровно 15 разрешённых frontend postimages, 13 точных preimages и 15 diff. Основной агент применяет их после проверки hash/preimage, связывает разрешённый runner и запускает свежие проверки. Этот пакет сам по себе не означает интеграцию, развёртывание или готовность продукта.

## Что предлагается

- Версионированный журнал в `sessionStorage` отдельно для конкретного проверенного owner и case. В нём только личный ввод, точные IDs/versions и исходный `SharedRouteWriteV1`; серверные allocation, quotes, lesson bodies, keys или auth tokens не записываются. Raw JSON ограничен 1 MiB, ключи и типы проверяются; неизвестные/чужие bytes не принимаются и не перезаписываются.
- До нового PUT записывается исходный UUID и полный body. Отказ записи означает «не отправлен», без запроса. Отказ журнала при повторе ранее отправленного неизвестного запроса сохраняет неизвестность.
- Reload/route/case restore не вызывает preview/PUT. `sending` становится `uncertain`. Точный own current GET либо один own history GET `expected_revision + 1` при более позднем head может reconcile только точное совпадение. Текущий head остаётся текущим; история не подменяет его.
- Matching ACK и состояние локальной очистки разделены. Настоящее подтверждение сервера показывается даже при отказе очистки и последующего GET; не предлагается повторить уже известный тот же ACK UUID. Более новый ввод, manual ID/review и значения отключённого экзамена остаются несохранёнными.
- Любой meaningful unsaved ввод или pending защищает main navigation, смену case, создание case, прямой hash и beforeunload. Cancel сохраняет страницу. Предупреждение действует и при исправном журнале. Security owner unmount остаётся немедленным. Authenticated Legal использует прежний private App; публичный Legal до входа сохранён.
- После actual logout ACK, внутреннего existing API operation fence и текущего signed-out binding App снимает только свои boolean risk tokens перед reload; failed/stale/logout-after-unmount этого не делает. Existing client owner/privacy cleanup остаётся byte-exact и удаляет scoped journal после ACK.
- Successful own case-delete ACK очищает журнал только захваченного case; поздний ACK A не очищает B, failed delete не очищает A.
- После подтверждённого 402 и вновь разрешённого доступа форма сохраняется. Старый preview сбрасывается; пользователь получает новый explicit preview, явно выбирает reviewed new intent через exact journal CAS и затем нажимает Save. Новый UUID появляется только на этом Save; исходный body сохраняется до выбора. Доступ/подписка не изменяются.

## Состав

Application (7): `lib/sharedRouteRecovery.ts`, `screens/SharedRoutePanel.tsx`, `screens/PreparationScreen.tsx`, `App.tsx`, `AuthGate.tsx`, `lib/store.tsx`, `lib/i18n.ts`.

Controls (8): новый `lib/sharedRouteRecovery.test.ts`; existing `screens/SharedRoutePanel.test.tsx`, `App.preparation.test.tsx`, `AuthGate.test.tsx`, `lib/storeIsolation.test.tsx`, `api/client.privacy.test.ts`, `e2e/preparation.spec.ts`, `e2e/auth-journey.spec.ts`.

Backend/wire/client/types/model/migration/helpers/legacy schedule/content/official scores не входят в пакет. `matchesSharedPreview`, `matchesSharedReceipt`, `matchesSharedView` и `buildInput` остаются точными прежними bytes — SHA указан в SOURCE_ONLY_REVIEW.json.

## Meaningful acceptance controls — ещё не запускались

- Helper: explicit auth/demo vs unbound/stale scope; whitelist/raw size/nonfinite/bad refs; original command preservation; failed storage; bounded journal revision; newer draft / different UUID / raw CAS; manual/disabled-exam false-clean; physical separate tab stores.
- Panel: partial input after unmount; same original UUID retry; sending restore; exact older revision reconciliation only; mismatching history retained; initial not-sent vs previously sent unknown; real synthetic PUT200 + failed cleanup + GET503 still accepted; newer input and omitted fields dirty; invalid bytes explicit reset; 402 → allowed → fresh preview → reviewed intent → new explicit save; A→B→A journals stay distinct.
- App: Cancel for nav/case/new case/hash/logout, accepted navigation restore, beforeunload and failure risk. AuthGate: same private tree on authenticated Legal and unconditional security unmount. Existing native client privacy tests cover successful/failed/stale logout/account-deletion cleanup, and existing store test gains case-specific journal assertions.
- Demo native adds exactly one loopback lost-browser-ACK fault: `route.fetch` obtains the real own synthetic API receipt, attaches exact original body/real status/receipt before abort, then unknown input → Cancel → accepted Home → same-tab reload → Prep GET reconcile. Original request executes once; no extra POST preview/PUT on restore. Newer 260-minute browser input remains while accepted server budget is 250. Own history/export/exact attempt ref, one budget and legacy/profile preservation are asserted.
- Auth native appends one synthetic-owner control: guarded authenticated Legal preserves personal input; separate clean browser has no unsaved journal while server revision remains readable; successful native logout ACK clears journal, cancelled logout makes no request. No fake server receipts or provider calls.

There are 38 additional source test declarations (36 unit and 2 native). Parameter expansion predicts 50 additional unit cases and 2 native scenarios; **these are source counts, not collected tests or PASS**. Existing tests gain additional journal assertions. All 533 original assertion-line occurrences are retained; both existing native files are byte-exact prefixes. Source-only preservation does not replace runtime acceptance.

## Immutable preview1 corrections

Preview1 is preserved unchanged, SHA `7b5e081b4c74e0d18c096a8f4acc096c91541cc22faffcc9feddb0a610f3b6aa`. Final15 incorporates peer/root F1 false-clean, F2 known ACK/cleanup and root F3 renewed-access correction. The peer report is pinned as an external dependency, never a mutable packet member.

The initial unsealed design raced a metadata read. Historical fde0… bytes were not preserved or independently verified; current 5da0… design and byte-exact copy remain unchanged. Separate sealed FINAL V1 and reconciled root receipt are the authority. No old receipt is rewritten.

## Required next gates / limits

1. Root verifies SEAL members, 15 preimages/new absence and accepted corrections; applies alone and preserves first failures.
2. Fresh bounded static/type/lint/meaningful unit gate and serial native Demo/Auth recovery controls under existing guards. Formatting, lint, typing, collection and native assertions are **NOT RUN** by this author.
3. Earlier full backend SQLite/PG qualification may carry only after actual byte equality of its consumed backend/wire inputs; this source packet makes no full, native, deployment or project-ready claim.

New native screenshots: `g2-recovery-lost-ack.png`, `auth-g2-recovery-private-draft.png` (and existing helper mobile namespace). New native attachment: `g2-recovery-forwarded-native-ack.json`. Existing viewport/exact-material/replay tests remain intact.

## Deliberate boundaries

Per-tab recovery is not cross-device sync or guaranteed recovery after tab closure, data purge or unavailable browser storage. No automatic retries/new saves, lessons/authenticated answers/quotes in storage, public/private portfolio scope, provider spending, stopped collector/model workflow, main merge, deploy or curriculum-completeness claim is introduced. Settings-specific logout-confirm UX is outside this15 allowance; native client cleanup itself is covered. Translation proposals have not received human signoff.

The React source checklist used `vercel:react-best-practices` storage schema, effect cleanup and event/closure rules. It introduced no dependency/optional refactor. No network or runtime was needed for the source review.
