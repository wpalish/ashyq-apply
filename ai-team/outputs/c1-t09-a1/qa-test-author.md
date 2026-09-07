# T09 / A1 — ashyq-qa TEST_AUTHOR output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-qa, PHASE: TEST_AUTHOR
- INVOCATION_REF: agent_a10293ed-58d3-4345-8e15-8195c87b9263 (real runtime agentId)
- STATUS: TESTS_READY (RED подтверждён)
- CHECKED_SHA: f7f14b28c43afe20df01ad38a26964c397f393fc (ветка ai/c1/t09/qa)
- QA_COMMIT_SHA: bb137d73c90286ec3c3d8aa1217c97461dedbfd7

## BASELINE_UNIT_RUN
npx vitest run (до правок): 18 файлов / 164 теста passed, exit 0; store.test.tsx изолированно 18/18.

## RED_EVIDENCE
- npx vitest run src/lib/drafts.test.tsx --reporter=verbose → exit 1
- полный прогон: 167 passed / 11 failed — падает только новый файл
- 11 RED, все AssertionError по контрактным ассертам, ноль импорт/env-сбоев; файл frontend/src/lib/drafts.test.tsx (517 строк, новый):
  - FE01 (1): restores edits + draftRestored после remount (199 — baseline теряет draft нового кейса)
  - FE02 (2): не стирает draft-слот при медленном getProfile (226); hydrated=false до settle profile-запроса (246)
  - FE03 (5): envelope A не применяется к B (296); round trip A→B→A сохраняет edits A (319); поздний A отброшен, финал B (353); неизвестная v → fallback + слот удалён (388); чужой case_key не применяется (421)
  - Error semantics (2): 500 сохраняет указатель (471 — baseline очищает); transient getRun сохраняет run-указатель (484)
  - StrictMode (1): слот не стёрт при двойном монтировании (510)

## GREEN_GUARDS (3, зелёные на baseline)
hydrated=false до settle обоих при обоих указателях; битый JSON → fallback + слот удалён; 404 → указатель забыт без error.

## CHANGED_FILES / МЕТОДОЛОГИЯ
Только drafts.test.tsx (git show --stat). Изоляция от формата хранения: seed legacy-указателей ashxq.activeProfile/activeRun + обнаружение draft-слотов по содержимому; fake timers детерминированы; API-задержки — deferred-промисы. store.tsx/store.test.tsx/production не тронуты.

## DEFERRED
e2e (playwright acceptance 11-13) не писались/не запускались — отложенный gate, NOT_RUN ≠ PASS (браузеры/env-dependent).

## NEXT
Developer от bb137d7; VERIFY_CANDIDATE в новой worktree.
