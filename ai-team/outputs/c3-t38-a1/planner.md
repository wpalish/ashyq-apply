# T38 A1 — Planner contract (frozen)

- Invocation ref: agent_36b11deb-26e8-42d7-a858-c2452baf1943
- Docs baseline: 810bb0064f45045f5f657ac89e653d2e551e140f (identical doc text at main/edf546d — no doc changes in c3)
- STATUS: PLANNED
- Полный контракт (23 editа с источниками, honesty-констрейнты, QA-метод) — в invocation; ключевые точки:

## Verified facts
- README:23-24 «2 of 9» + :289 «one institution in ten» + :466 «1 of 10» → замена на 7/10 (2026-09-08, LIVE_DISCOVERY_REPORT.md:10-14; combined: 10 institutions, 7/10 program, 26/30 category, 0 material FP, 1319.9s).
- README verification table :329-347 fix-plan-era (547/89%/47 vitest/50 e2e); :347 Docker «written, never run» противоречит DOCKER_VERIFICATION.md (2026-09-06 реальный прогон) и gate 22.
- ONE-source: CI claims = c2 GitHub runs 34188244906, 34188286259, post-merge main 34189211422 (зелёные, 2026-09-08) + 34115345524 (2026-09-07); c3 = LOCAL 1402 passed / 0 skipped / cov 94.04% @ 810bb00 (integrator.md) — ВСЕГДА с меткой local+SHA+дата; FE gates skipped (0 diffs) — не PASS.
- RELEASE_CHECKLIST:14-19 CI-red заголовок → зелёный с 2026-09-07 + правило обновления при каждом merge; gate 2 PARTIAL→PASS (история красного сохранена); :52 gate 22 хвост «WRITTEN, NOT RUN» удалить; :58 gate 28 1/10→7/10; :130 gate 79 «ten institutions»→(ten then, nineteen since gate 89); :151 gate 89 supersession pointer; :171-184 summary PASS 91→92, PARTIAL 3→2; :201-203 item 5 done; :208-210 i18n «184 of 378 / seven components» → посчитанные 183 of 194 keys RU+KK, readers = shell+community screens.
- CURRENT_STATE: append-only секция «after campaigns c2 and c3 (2026-09-08)» — supersedes earlier «Still open» списки; таблица открытых пунктов (реестр 19→60 PARTIAL, i18n core, юрист gate 87, live ApiPay gate 94, деплой NOT DONE, T31 BLOCKED, T26 BLOCKED_SCOPE_CONTRACT, verify_compose live NOT_RUN owner-gate, T33-F1 owner decision); датированные исторические секции НЕ трогать.
- Registry = 19 (посчитано в institution_registry.json); i18n EN 194 / RU 183 / KK 183 (посчитано в i18n.ts).

## Binding honesty constraints
- Никаких «latest»/«not yet pushed» формулировок; «green since 2026-09-07» остаётся истинным до и после PR #10.
- c3-числа всегда LOCAL+SHA+дата; FE-числа = c2-замеры неизменённого фронта (с меткой).
- Unknown ≠ zero: непереведённые ключи = 11/локаль числом.

## QA method (worktree c3-t38-qa @ candidate)
1. diff hygiene: ровно 3 файла; 2. number-by-number cross-check против источников (каждый числовой токен); 3. stale-token sweep: «2 of 9», «1 of 10», «one institution in ten», present-tense «red since 2026-09-04», «written, never run», «WRITTEN, NOT RUN», «1110», «547 passed», «47 Vitest», «50 Playwright», «74 Playwright», «184 of 378», «89%» — вне исторических контекстов; 4. wording-stability: grep «latest», «not yet pushed», «unpublished» = 0; 5. handoff_check.py зелёный; 6. сам пересчитать registry/i18n ключи.

allowed_paths: README.md, RELEASE_CHECKLIST.md, docs/CURRENT_STATE.md ONLY. Non-goals: LIVE_DISCOVERY_REPORT/DOCKER_VERIFICATION = источники (не трогать); без кода/CI/HANDOFF; без ретро-правок истории; NOT_RUN ≠ PASS.
