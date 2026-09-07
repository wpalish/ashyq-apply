# T09 / A1 — ashyq-developer output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-developer
- INVOCATION_REF: agent_924bc3b2-4e00-4b16-91c3-ceaf2f323763 (real runtime agentId)
- STATUS: DONE_WITH_BLOCKER (реализация завершена; 10/11 QA RED→GREEN; 1 QA-тест дефектен сам)
- QA_COMMIT_SHA: bb137d73c90286ec3c3d8aa1217c97461dedbfd7
- CANDIDATE_COMMIT_SHA: febb6c3310b936171247bd4c007bd877b3047f4e (заморожен; финальный кандидат после амендмента = b0caa004b5351f84ee9ac07184d2486177a77d3f, test-only)

## CHANGED_FILES
A frontend/src/lib/caseDrafts.ts (новый модуль персистенции/валидации — разрешён контрактом); A frontend/src/lib/hydrationErrors.test.tsx (2 аддитивных теста); M frontend/src/lib/store.tsx; M frontend/src/lib/store.test.tsx. App.tsx/types.ts/ResultDetail/api/client/backend/polling не тронуты.

## GATES (реальные)
- typecheck: exit 2 на QA-строке 472 (TS2551 toContainText) — pre-existing на QA-коммите (подтверждено на чистом baseline через stash)
- lint: 0
- targeted: 33 passed / 1 failed (дефектный matcher); full unit: 179/1
- build: exit 1 на той же строке
- После амендмента b0caa004 (QA-вызов): targeted 34/34, typecheck 0, full unit 180/180

## QA RED→GREEN
10/11 зелёные (FE01 remount; FE02 слот+hydrated x2; FE03 изоляция A/B, round-trip, late-response, unknown-v, чужой case_key, битый JSON; 404; run-pointer; StrictMode). 11-й (500 → указатель + ошибка): поведенческий ассерт зелёный, строка 472 падала на несуществующем matcher'е toContainText (Playwright API; в jest-dom — toHaveTextContent). Исправлен QA-амендментом b0caa004 (согласованное диспетчером изменение тест-контракта).

## CONTRACT_DEVIATIONS (координатором утверждено)
1. store.test.tsx — 2 ассерта обновлены под замороженный контракт B (per-tab sessionStorage): 'carries a session stored under the old name across, once' и 'joins the run already in flight' кодировали старый глобальный localStorage-указатель; теперь ассертят sessionStorage + отсутствие глобальной копии (усиление). + sessionStorage.clear() в beforeEach. Основание: контракт B + planner WRITE_SCOPE включает store.test.tsx. УТВЕРЖДЕНО.
2. newCase() также инкрементирует generation (сверх 4 из п. D) — медленный switchCase не может лечь поверх свежего пустого кейса.
3. Legacy bare-draft без атрибуции удаляется при миграции (был невосстановим).
4. 404 профиля очищает и run-указатель (как baseline).
5. e2e: NOT_RUN — отложенный gate (решение координатора).

## REMAINING_RISKS
Две вкладки на одном сохранённом кейсе — последний autosave выигрывает (принято); новая вкладка не открывает «последний кейс» (принятое behavior change); осиротевшие envelopes невидимы (non-goal); правки demo-профиля до New case не персистятся (как baseline).

## NEXT
VERIFY_CANDIDATE на b0caa004 (или febb6c33+b0caa004 цепочка) в чистой worktree: targeted+full unit+typecheck+build; затем reviewer/security.
