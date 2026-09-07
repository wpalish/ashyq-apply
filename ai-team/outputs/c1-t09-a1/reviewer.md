# T09 / A1 — ashyq-reviewer output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-reviewer
- INVOCATION_REF: agent_2a87c91e-3b35-4ef0-9033-182ec673b3a2 (real runtime agentId)
- VERDICT: CHANGES_REQUESTED (на b0caa004b5351f84ee9ac07184d2486177a77d3f; одобрение аннулируется любой правкой)
- Ограничение метода: нет Bash; SHA по ref-файлам; соответствие diff — по qa-verify артефакту + прямому чтению всех 5 файлов candidate.

## CONTRACT_COMPLIANCE (A-F): выполнено
A hydrated после settle обоих (store.tsx:383-385 + hydrationPassRef); B per-case слоты + per-tab, чужой слот не удаляется (caseDrafts.ts:157); C autosave дважды gated (store.tsx:225); D единый opGenRef, проверка gen вплотную к синхронной записи, второй await в switchCase повторно проверяется (546), ответ отбрасывается целиком; E parseEnvelope строгий (123-134); F backend/types/api не тронуты. StrictMode идемпотентен; saveProfile||switchCase корректно; утечек между кейсами нет.

## FINDINGS
1. [Medium, test-only, blocking для приёма] Acceptance #8 (save failure → dirty, envelope жив, error) НЕ покрыт тестом вообще — saveProfile ни в одном тесте (grep 0). Код фейл-пути выглядит корректно, но не доказан.
2. [Medium, vacuous assertion] 404-«забыть указатель» не закреплён: drafts.test.tsx:457 и store.test.tsx:90 ассертят только localStorage.getItem('ashyq.activeProfile')===null — это гарантирует сам adopt-механизм (caseDrafts.ts:95-97), независимо от ветки 404. Сохранение в sessionStorage после 404 не ассерчено (хелпер pointerSurvives используется только в 500-тесте). На baseline тест был осмысленным; после миграции стал vacuous.
3. [Medium, решение координатора] Local-case: draft переживает ровно ОДИН reload — после восстановления baseline=envelope (store.tsx:316-319) → dirty=false → следующий autosave-тик делает clearDraftSlot (226-229). Второй reload → blank. Baseline-parity (у baseline терялось на первом), acceptance #1 в единственном числе — контракт формально не нарушен; наблюдение qa-verify «не потеря данных» для local-case неверно. Минимальный фикс: не очищать local-case слот пока draftRestored — одна строка в autosave.
4. [Low, test strength] store.test.tsx:296 ассертит удаление ashyq.unsavedDraft (миграция удаляет его до discard) — per-case слот после discard не ассерчен; vacuous-дрейф.
5. [Low, frontend state risk] Валидация envelope не ограничивает глубину/размер draft; crafted deep draft → RangeError в JSON.stringify рендера (store.tsx:214) до ручной очистки. Prototype pollution НЕ эксплуатируема (JSON.parse own-property + spread-слияния). Требует same-origin записи — низкий риск.
6. [Info] Ограничение ревью без Bash.

## TEST_ASSESSMENT
Миграция store.test.tsx чистая (ровно 2 документированных сайта + гигиена; усиление). ACCEPTANCE_COVERAGE: 1✓ 2✓ 3✓ 4✓ 5✓ 6✓ 7✓ 8✗ 9 частично (404 vacuous) 10✓; e2e 11-13 NOT_RUN.

## SCOPE: creep нет; отклонения #2-4 задокументированы и утверждены.

## RISKS_LEFT
- Условие release-readiness: e2e 11-13 NOT_RUN (TEAM_RULES: full gate недоступен → не release-ready).
- Behavior changes не проверены в реальном браузере; rollback на старый билд после adopt — одноразовая потеря «последнего кейса».
- Вне контракта (наблюдение): deleteEverything без gen-инкремента — поздний switchCase может «воскресить» удалённый кейс; polling без gen (прямое указание контракта D).

## NEXT_ACTION координатору
(1) Тест-контракт амендмент: тест saveProfile-фейла (#8), усилить 404-ассерты до pointerSurvives/sessionStorage-null (drafts.test.tsx:457, store.test.tsx:90); (2) решение по finding 3 (чинить local-case или документировать); (3) новый candidate → повторный VERIFY → повторный review; (4) e2e 11-13 обязательный gate перед release. Production-код по findings 1-2, 4-5 правок не требует.

## РЕШЕНИЕ ДИСПЕТЧЕРА (2026-09-07)
Finding 3: ЧИНИТЬ (одна строка в autosave — local-case слот не очищается пока draftRestored; очистка при save/discard). Обоснование: FE01 «новый draft переживает reload» в пользовательском смысле должен быть идемпотентным по reload'ам; фикс мал и в scope store.tsx. Findings 1-2, 4: QA test-contract amendment A2. Finding 5: backlog (низкий риск). Порядок A2: QA пишет тесты (включая two-reloads RED) → developer применяет фикс → новый candidate → VERIFY → re-review + security.
