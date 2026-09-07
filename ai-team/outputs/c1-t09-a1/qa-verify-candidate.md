# T09 / A1 — ashyq-qa VERIFY_CANDIDATE output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-qa, PHASE: VERIFY_CANDIDATE
- INVOCATION_REF: agent_42d319dc-dc31-4b45-b1db-c6a1966406a4 (real runtime agentId)
- STATUS: VERIFIED_PASS
- CHECKED_SHA: b0caa004b5351f84ee9ac07184d2486177a77d3f (chain f7f14b28 → bb137d7 QA → febb6c33 dev → b0caa004 test-only amend; ветка ai/c1/t09/verify, чисто)

## COMMANDS_AND_RESULTS
1. rev-parse/log/status → b0caa004, chain корректна, чисто
2. git diff f7f14b28..HEAD --stat → ровно 5 ожидаемых файлов (store.tsx, caseDrafts.ts new, hydrationErrors.test.tsx new, store.test.tsx, drafts.test.tsx)
3. diff febb6c33..b0caa004 → ровно 1 файл, 1+/1-, только matcher
4. diff bb137d7..HEAD -- store.test.tsx → ровно 2 задокументированных assert-сайта + гигиена
5a. vitest run store+drafts+hydrationErrors --reporter=verbose → 34/34 (11 QA RED→GREEN + guards)
5b. npm test -- --run → 180/180, 20 файлов
5c. typecheck → 0; 5d. lint → 0; 5e. build → 0 (647ms)
e2e/playwright → NOT_RUN (env-dependent, отложенный gate; НЕ запускать)

## ADVERSARIAL_FINDINGS (контракт A-F)
(i) Hydration ждёт ОБА запроса — PASS (Promise.all + finally; hydrationPassRef против StrictMode)
(ii) 404 vs transient — PASS (404 → очистка указателей+слота; остальное → fail(e) с сохранением; fail не бросает)
(iii) Generation guard отбрасывает ЦЕЛИКОМ — PASS (единый opGenRef; проверки после каждого await; записи между проверкой и группой нет)
(iv) Валидация envelope — PASS (parseEnvelope caseDrafts.ts:123: v/case_key/saved_at/base_updated_at/draft-object; чужой case_key → null БЕЗ удаления чужого слота)
(v) Legacy миграция однократна, удаляет legacy-ключи — PASS (неатрибутированный bare-draft удаляется — утверждённое отклонение #3; TOCTOU между вкладками — «последний побеждает», задокументировано)
(vi) StrictMode double-mount — PASS (прерванный проход не ставит hydrated; autosave gated hydrated && activeCaseKey)
Парити-наблюдение (не блокер): после hydration dirty=false → следующий autosave-тик чистит слот — идентично baseline !dirty-очистке, не потеря данных.

## SCOPE_ASSESSMENT
Ослаблений нет: amend — ровно 1 строка с эквивалентной substring-семантикой; store.test.tsx миграция — усиление по замороженному контракту B; hydrationErrors.test.tsx — аддитивные guard'ы; тесты на реальном StoreProvider, моки только api.

## UNTESTED_RISKS
E2E NOT_RUN (acceptance 11-13); behavior changes не проверены в реальном браузере; legacy-adoption TOCTOU; серверный конфликт-UX вне scope.

## NEXT
b0caa004 → reviewer (+security) на замороженный SHA; deferred e2e запланировать отдельно.
