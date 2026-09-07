# T09 / A1 — ashyq-planner output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-planner
- INVOCATION_REF: agent_038babc3-f6ee-4ac1-b20f-4ebff7f9923d (real runtime agentId)
- STATUS: PLANNED
- BASELINE_SHA: f7f14b28c43afe20df01ad38a26964c397f393fc (подтверждён по ref-файлам worktree c1-t09-qa)
- FINDING_IDS: FE01, FE02, FE03 — все три АКТУАЛЬНЫ на baseline

## ROOT_CAUSE
- FE01: store.tsx:294-333 hydration читает DRAFT_KEY только при profileId; newCase() (486-499) очищает PROFILE_KEY → reload нового кейса теряет draft (persisted лежит в localStorage, не читается, затем уничтожается FE02).
- FE02: autosave store.tsx:232-238 без гейта hydrated; при монтировании dirty=false → через 600 мс writeLocal(DRAFT_KEY, null) стирает слот до возврата медленного getProfile (297); hydrated выставляется только от run-промиса (332) — profile-запрос не входит.
- FE03: единый глобальный слот DRAFT_KEY (24) + глобальные указатели (28-29); две вкладки перезаписывают слот; hydration (296-316) накладывает envelope на любой кейс без проверки принадлежности (кросс-кейс overlay, Save пишет чужой контент); switchCase (454-484) без generation/AbortController — поздний ответ A перезаписывает B; payload не валидируется (308 голый JSON.parse); catch (319-323) трактует любую ошибку как «профиль удалён».
- Код сдвинулся на ~14 строк после аудита; блоки MASTER 207-218, 274-312 соответствуют store.tsx:209-218, 288-333.

## CONTRACT (кратко; полный в отчёте)
- A. Состояния: hydration pending→ready|failed_transient (settle ОБЕИХ попыток — profile и run); 404 доказывает отсутствие кейса (очистить указатель), transient сохраняет указатели, 401 — существующий reload-путь. draft: clean|editing|restored. save: idle|saving|failed. hydrated=true — только когда ни один initial-запрос не в полёте.
- B. Изоляция: envelope {v:1, case_key, saved_at, base_updated_at?, draft} в per-case слотах localStorage; case_key = profile id или локальный draft id для нового; envelope применяется только при совпадении case_key. Указатель активного кейса/run — per-tab (sessionStorage); глобальный запрещён. Migration: legacy-слоты читаются один раз и удаляются. Две вкладки на одном кейсе: последний autosave выигрывает (задокументировано). Logout: чужие envelopes не отображаются; recovery осиротевших — non-goal.
- C. Hydration race: до settle initial hydration autosave НЕ пишет/не чистит никакие draft-слоты; restore решается ровно один раз из storage; корректность при remount и React StrictMode (двойной invoke — то же финальное состояние).
- D. Stale guard: монотонный generation (или AbortController) для initial hydration, switchCase, завершений saveProfile/startRun; устаревший ответ отбрасывается ЦЕЛИКОМ. Polling не входит (store.tsx:356-418 не трогать).
- E. Валидация envelope: v известен, case_key совпадает, draft ожидаемой формы; невалидный/чужой → fallback без падения, повреждённый удаляется; молчаливый cast запрещён.
- F. Backend не меняется; Store-интерфейс совместимо/аддитивно; правки App.tsx за пределами минимального — запрос расширения ДО реализации.

## ACCEPTANCE (кратко)
Unit (vitest/jsdom, обязателен): 1) FE01 reload нового кейса восстанавливает edits, draftRestored=true; 2) FE02 медленный getProfile + прогоревший autosave-таймер → слот не очищен, edits восстановлены; 3) hydrated false до settle обоих; 4) FE03a envelope A не применяется к кейсу B; 5) FE03b switch A→B с поздним A → финал = B; 6) reload сохранённого с dirty draft → draft восстановлен, savedProfile нетронут; 7) corrupt envelope → fallback без throw; 8) save failure → dirty, envelope жив, error; 9) 404 → новый кейс, 500/сеть → указатели сохранены; 10) StrictMode double-mount.
E2E (env-dependent, NOT_RUN ≠ PASS): 11) reload-восстановление; 12) две страницы — изоляция; 13) switch с задержкой.

## WRITE_SCOPE
- frontend/src/lib/store.tsx (SHARED, сериализован за T09), frontend/src/lib/*Draft*.ts (допускается новый модуль персистенции/валидации), frontend/src/lib/*.test.tsx (store.test.tsx + новые), frontend/src/screens/ProfileScreen.tsx (минимальное отображение состояния), frontend/e2e/profile-persistence.spec.ts + helpers.ts.
- НЕ в scope: App.tsx, types.ts (T04), ResultDetail.tsx (T04), api/client.ts, backend.

## RESERVATIONS / RISKS
- Локи: frontend-store, profile-ui, frontend-e2e. Пересечений записи с T04/T10 нет.
- Читает types.ts (StoredProfile) — если T04 изменит StoredProfile, возможен rebase-конфликт (объединит интегратор).
- e2e env-dependent (браузеры Playwright, backend webServer 8099+Vite 5173; Docker отсутствует) — задача не release-ready на unit-only.
- Behavior changes приняты в контракте: per-tab указатель убирает восстановление «последнего кейса» после закрытия браузера; осиротевшие envelopes невидимы после logout — задокументировать в PR.
- store.tsx — сериализуемый ресурс: другие задачи в него не пишут.

## NON-GOALS
Polling, backend tenant-изоляция (T10), server-conflict UX, recovery осиротевших drafts, новые архитектурные компоненты.
