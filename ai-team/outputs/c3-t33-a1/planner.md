# T33 A1 — Planner contract (frozen)

- Invocation ref: agent_c65bf3c3-4cc7-4357-b107-ab3ba1ad53d1
- Baseline: edf546de9f998c0909337d0abe6f8e1c9c4a0be5
- STATUS: PLANNED
- Dispatcher rulings: PD-1 (200+trim, НЕ 402 — 402 ломает верх воронки через setPaywall/PaymentModal), PD-2 (counts.claims/conflicts остаются в free-экспорте), PD-3 (decision/notes разрешены за пределами free_shortlist cut, 200+trim) — ПРИНЯТЫ. PD-4 (один entitlement на профиль открывает весь экспорт — существующий ключ has_full_access) — сохраняем.

## Facts (baseline, file:line)

- S1 CONFIRMED: set_decision routes_results.py:256-299 (guard только owned_run :271, полный result :299 из row.payload :276); set_notes :306-340 (owned_run :320, полный result :340). ProgramResult несёт scholarships/costs/funding_gap/conflicts/claims/requirement_checks/checklist/source_urls (schemas/result.py:280-357). Контраст: list/get/refresh/claims/conflicts/questions/deadlines/export/shortlist — все require_full_access. Два write-маршрута — единственные дыры S1.
- S2 CONFIRMED: export_profile routes_profile.py:248-355 — только owned_profile :261; results с **result.payload (:313) + checklist (:312); claims **c.payload :317-326; conflicts :327-330; note :350-354 обещает «every claim and conflict».
- free_view entitlements.py:76-98 (идемпотентна); access_for_run paywall.py:18-25; has_full_access entitlements.py:17-36. routes_results уже импортирует оба (:15, :31).
- FRONTEND: decide/saveNotes заменяют строку состояния телом ответа (store.tsx:706-718, :251-259); ShortlistScreen читает r.funding_gap (:66, :149). После фикса ответ = та же free_view-форма, что список уже отдаёт — UI не ломается, типы не меняются. Сегодня клик decision у free-пользователя реально апгрейдит строку до полного платного материала в UI.

## Frozen contract (essentials)

- set_decision/set_notes: заменить owned_run на `_profile_id, allowed = access_for_run(...)`; записи ДО прогноза без изменений (payload полн+решение); вернуть `result if allowed else free_view(result)` (поля применить ДО проекции); 200 всегда; payments_enabled=False → поведение байт-в-байт как baseline.
- export_profile: `has_full_access(session, principal.organization_id, profile_id)` напрямую; allowed → вывод НЕИЗМЕНЕН; без прав → results = `{**free_view(ProgramResult.model_validate(payload)).model_dump(mode="json"), "paid_content_withheld": True}`; claims: [], conflicts: []; counts остаются; note честный (без обещания каждого claim; разработчик выбирает формулировку).
- Surface-scan: НОВЫЙ backend/tests/test_paywall_surface.py; обход app.routes (префиксы ^/api/runs/{run_id} и ^/api/profiles/{profile_id}, GET/POST/PATCH/PUT не-204); ИНВЕНТАРЬ-равенство с замороженным списком из 17 маршрутов (новый маршрут без внесения в список = fail → принудительное решение); материальный словарь (recursive flags): непустые массивы под claims/conflicts/scholarships/requirement_checks/missing_prerequisites/hard_filter_failures/unresolved/source_urls/eligibility_checks; непустые funding_gap/checklist; verification_completeness != 0; непустые career_notes/post_study_work/work_during_study; admission_deadline_raw; любой dict с ключом claim_type. Не-материальные: counts-массивы summary, coverage-скаляр, метаданные, paid_content_withheld, admission_deadline (не _raw).
- Ожидание baseline: scan RED ровно на 3 параметрах (decision/notes/export) — список = инвентарь утечек; лишний параметр = новая утечка → эскалация.
- Byte-identity метод: canonical(json.dumps(sort_keys, separators)) равенство free_view(model_validate(R)).model_dump() == R.
- RED-1..3 (test_paywall.py): decision/notes/export для free-орг; GREEN-guard: _unlock() → полные ответы; посев материала при необходимости — тестовыми данными через row.payload (схемные значения), не продакшн-код.
- allowed_paths QA: test_paywall.py + новый test_paywall_surface.py (test_billing_api.py только при необходимости). Developer: routes_results.py (тела set_decision/set_notes), routes_profile.py (тело export_profile + импорты). payments/entitlements.py НЕ трогать (резерв T34); config.py НЕ трогать; test_frontend_contract.py не меняется (типы не меняются).
- Non-goals: без изменений схемы/types.ts/фронтенда; без новой entitlement-логики; get_result остаётся 402; summary остаётся открытым; без conftest.py; без миграций.
