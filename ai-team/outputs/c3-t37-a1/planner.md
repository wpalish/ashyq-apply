# T37 A1 — Planner contract (frozen)

- Invocation ref: agent_84cbdac2-75be-458c-b6f2-01b4a88866e6
- Baseline: edf546de9f998c0909337d0abe6f8e1c9c4a0be5
- STATUS: PLANNED
- Dispatcher ruling: выбран TARGETED delete (не blanket) — обосновано код-flow и принято полностью.

## Facts (baseline, file:line)

- Механика дубля CONFIRMED: _update_result (runner.py:1099-1120) при extra_claims (:1117-1118, truthiness) вызывает _store_claims/_store_conflicts БЕЗ очистки. _stage_funding (:616) вызывается на КАЖДУЮ строку через :813; _save коммитит каждые 4 строки (:816-817); повторный вход снова берёт ВСЕ строки (:619). Дублируются только SCHOLARSHIP_* (14 enum-значений, эмитит исключительно WebScholarshipAdapter) + funding ConflictRow. Verify-семейство ортогонально.
- Call sites extra_claims: ровно два — runner.py:813 (funding, НЕ защищён = S7) и :1072 (_persist_result retry-ветка — УЖЕ защищён _replace_evidence :1071, эталон). :889/:961/:1038 — без extra_claims, не трогаем.
- Пути re-entry: ДУБЛЬ воспроизводит POST /retry?stage=funding_discovery (routes_research.py:396-456; сбрасывает только funding_discovery+assessment :431-437, program_verification остаётся done → verify скипается, funding перезапускается по всем строкам) и resume после падения funding mid-stage (worker retry :327). НЕ воспроизводит: recheck_stale (:307-338) и полный retry — там перезапускается verify, _persist_result → _replace_evidence (:1071) сносит всё, funding пишет один раз (ВАЖНО для QA: использовать stage-retry, не recheck — иначе ложный GREEN).
- Магический сценарий blanket-замены РЕАЛЕН: verify-claims существуют при любом re-entry в funding — (а) stage-retry сохраняет их по задокументированному контракту роута (:406-407 «earlier ones keep their work», тест test_api.py:346-362); (б) recheck — записаны минуту раньше в том же run_to_decision (:590 → :1096). Blanket уничтожил бы их в обоих случаях.
- _replace_evidence (:1122-1137): ClaimRow по result_id с фильтром status != SUPERSEDED (:1131-1134) + ВСЕ ConflictRow (:1135-1137).
- T32: reextract (source_scanner.py:190-308) флипает live→SUPERSEDED по (run_id, source_url), аппендит через WebRequirementsAdapter (:263) — не создаёт SCHOLARSHIP_* live ни ConflictRow. user_decision/notes живут на ProgramResultRow (:140-143), _update_result переносит их в payload (:1107-1110) — фикс их не затрагивает.

## Frozen contract

- Фикс: в _update_result ветка `if extra_claims is not None:` (не truthiness — честная замена и при пустом новом наборе, зеркально reextract-семантике «нулевых страниц»): (1) delete ClaimRow где result_id==row.id AND claim_type IN FUNDING_CLAIM_TYPES AND status != SUPERSEDED.value; (2) delete ConflictRow где result_id==row.id AND claim_type IN FUNDING_CLAIM_TYPES (у ConflictRow нет status); (3) существующие _store_claims/_store_conflicts без изменений. FUNDING_CLAIM_TYPES — module-level константа (рядом :1306-1316): все 14 ClaimType с префиксом scholarship_ (явный список или frozenset из enum — эквивалентны).
- Против blanket: уничтожил бы verify-claims в (а) и (б). Против delete-по-типам-прохода: хвосты прошлого прохода при сузившемся наборе. Семантика: «funding повторно владеет всем семейством SCHOLARSHIP_*». Будущий funding-адаптер с типом без префикса = новая контрактовая сессия.
- RED TestFundingReEntry (test_pipeline.py): completed_run fixture; зафиксировать per-result счётчики; stage_state funding_discovery+assessment → "pending" (точно как routes_research.py:431-437; НЕ recheck_stale, НЕ полный сброс); user_decision/reason/notes/decided_at на одной строке (рецепт test_api.py:306-323); вставить одну SUPERSEDED ClaimRow (образец test_freshness_regressions.py:363-393); повторный run_to_decision(). Assertions: (1) ClaimRow по result_id не изменился (и сумма SCHOLARSHIP_*); (2) не-scholarship (verify-family) счётчики не изменились — guard против blanket-регрессии; (3) user_* на row и в payload сохранены; (4) SUPERSEDED-строка жива (status и payload["status"]); (5) ConflictRow не удвоился. Baseline: (1) и (5) красные.
- allowed_paths: runner.py ТОЛЬКО ветка extra_claims в _update_result (:1099-1120) + module-level константа; test_pipeline.py. Остальное (enums, routes_research, source_scanner, test_api, conftest) — ЗАПРЕЩЕНО без расширения.
- Non-goals: без изменений стадий/reextract/supersession/freshness; других веток _update_result/_persist_result/_replace_evidence; без schema; без чистки существующих прод-дублей (владельцу); run.claims_recorded семантика не трогается.
- SUPERSEDED_INTERPLAY: targeted delete несёт тот же фильтр != SUPERSEDED; reextract-продукция физически не пересекается (не SCHOLARSHIP_*, без ConflictRow).
- Гейт T32: test_source_scan.py + test_freshness_regressions.py + TestRetry (test_api.py:293-362) зелёные на candidate.
