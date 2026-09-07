# T09 / A2 — developer + QA verify outputs (сохранено диспетчером; сокращено без изменения оценки)

## ashyq-developer A2 — INVOCATION_REF: agent_be9089d9-d877-4e3e-9c21-3ac5fc7615d7
- STATUS: IMPLEMENTED; QA_A2_COMMIT start: cdb4403d13aef4a0eb9b6351079683a94d839436
- CANDIDATE_A2_COMMIT_SHA: 7fb0d3270de24f79adfea6a315ee80092a298bc0 (заморожен; не push/amend)
- CHANGED_FILES: ровно frontend/src/lib/store.tsx (+6/-2): ветка очистки autosave `else if (!(isLocalCaseKey(activeCaseKey) && draftRestored)) clearDraftSlot(activeCaseKey);` (store.tsx:232) + draftRestored в deps (235) + 4 строки комментария
- ROOT_CAUSE_FIXED: reviewer finding 3 — при hydration local-case baseline=envelope → dirty=false → autosave-тик делал clearDraftSlot → второй reload давал blank
- Очистки не тронуты: retire при save (509)/create (600), discard (238), deleteEverything (746), 404-hydration (357); hydration/generation/валидация/caseDrafts.ts — без изменений
- GATES: RED до фикса (тест A 'keeps a restored local-case draft across a second reload': expected Georgia, received ''); после фикса target 36/36 (тест A GREEN), полный vitest 182/182, typecheck 0, lint 0, build 0
- CONTRACT_DEVIATION (в духе решения диспетчера): «одна строка» → два места того же эффекта (guard + deps — иначе react-hooks/exhaustive-deps красный и stale-closure)
- Прочее: commit с auto-detected identity (информационное); pre-existing наблюдение: discard на local-case с dirty=true «не держится» (autosave перезаписывает слот) — вне findings 1-4

## ashyq-qa VERIFY_A2 — INVOCATION_REF: agent_be216803-cdd5-45d4-a970-4b6dde16d605
- STATUS: VERIFIED_PASS на 7fb0d3270de24f79adfea6a315ee80092a298bc0 (ветка ai/c1/t09/verify-a2, чисто; chain подтверждена git log -7; транзитный git-глюк merge-base разрешён повтором)
- DIFF: cdb4403..HEAD ровно store.tsx +6/-2, как заявлено; тестовые файлы и caseDrafts.ts не тронуты
- FIX_SEMANTICS: (a) retire при save/create не нарушен (store.tsx:503-509, 596-600; после save activeCaseKey → server id, guard больше не срабатывает); (b) discardDraft очищает (237-241) и идемпотентен; (c) deleteEverything очищает (746); (d) 404-очистка не затронута (352-357); (e) новый путь «слот не очищается» только для local-case restored (принято координатором, задокументировано в коде 228-231); после SAVE слот уходит — подтверждено тестом 'retires the slot on a successful retry'
- COMMANDS: target 36/36 (drafts 16, hydrationErrors 2, store 18) exit 0; полный 182/182 exit 0; typecheck 0; lint 0; build 0 (487ms); e2e NOT_RUN (deferred)
- SCOPE: тесты НЕ ослаблены (git diff cdb4403..HEAD по тестам пуст); RED-логика теста A подтверждена чтением git show b0caa004:store.tsx (безусловный else clearDraftSlot)
- UNTESTED_RISKS: e2e 11-13; manual-return-to-baseline local-case (принято); reviewer finding 5 (backlog); TOCTOU adopt/polling вне scope
