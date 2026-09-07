# T10 / A1 — ashyq-qa TEST_AUTHOR output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-qa, PHASE: TEST_AUTHOR
- INVOCATION_REF: agent_14ab3b13-5072-4b84-8dfe-fc9ccdc41650 (real runtime agentId)
- STATUS: TESTS_READY (RED подтверждён: 8/8 новых RED, 27/27 существующих green)
- CHECKED_SHA: f7f14b28c43afe20df01ad38a26964c397f393fc (ветка ai/c1/t10/qa)
- QA_COMMIT_SHA: e47cfd2f982e8f3820825833b866bea67f56bfbe

## PG_STATUS: pgserver работает — встроенный PostgreSQL (per-test DB + миграции через conftest pg_engine); test_jobs.py 30 passed на реальном PG. Важно: TestLeaseFencing в test_worker.py — НЕ PG-тест (bound_db на SQLite), зелёный 4/4; PG-доказательства — в новых two-session тестах.

## RED_EVIDENCE (assertion-level, baseline реально портит состояние)
1. TestStaleWorkerRunState::test_a_mid_run_takeover_does_not_write_terminal_run_state — exit 1: stage стал 'failed' вместо 'program_verification' (LeaseLost ловится except Exception, runner.py:273-280: stage=failed + errors + audit run_failed). Также errors/finished_at/audit пишутся stale-попыткой.
2. TestStaleDispatchCommit::test_a_stale_worker_writes_no_completion_audit — exit 1 на реальном PG: stale worker игнорирует complete()→False и пишет job_completed audit (worker.py:239-249); takeover через reaper + re-claim.
3. TestCheckpointKeepsPendingCounters::test_pending_counter_increments_survive_a_checkpoint — exit 1: assert 0 == 7; session.refresh(self.run) в _check_cancelled (runner.py:155) отбрасывает pending инкременты.

## RED (contract-field-level, TypeError: unexpected keyword 'lease_token')
5 тестов TestFencedWritesTwoSessionPostgreSQL: same_worker_reclaim_fences_first_attempt; takeover_leaves_outcome_to_new_owner; renewed_lease_survives_reaper; finished_reap_refuses_dead_worker_heartbeat; fenced_terminal_writes_change_nothing. Двухсессионная настройка на PG работает до TypeError: claim t1 → reaper → re-claim → attempts == t1+1 проходит.

## GREEN_GUARDS
test_worker.py полный: 27 passed / 8 failed (все 8 — новые); TestLeaseFencing 4/4 green; test_jobs.py 30/30 на PG.

## CHANGED_FILES
backend/tests/test_worker.py — только добавления (+440, 0 удалений), ruff clean. Классы: TestStaleWorkerRunState, TestCheckpointKeepsPendingCounters, TestFencedWritesTwoSessionPostgreSQL (+fixture pg_factory, reaper helper), TestStaleDispatchCommit. Production/conftest/другие тесты не тронуты.

## КОНТРАКТНОЕ API (закреплено в docstring тестов; заморожено как тестовый контракт)
lease token = job.attempts на момент claim, возвращается claim(); fenced методы complete/heartbeat/fail/mark_cancelled принимают опциональный lease_token=; fenced write = 0 изменённых строк (никаких статус/last_error/finished_at/worker_id изменений); fenced fail возвращает текущий статус. Иное имя параметра = механическое изменение, требует согласования изменения тестового контракта СНАЧАЛА.

## LOGS
outputs/c1-t10-a1/qa-logs/: qa_t10_stale_run.log, qa_t10_checkpoint.log, qa_t10_pg_fenced.log, qa_t10_dispatch.log, qa_t10_full.log

## UNTESTED_RISKS
Полный suite/test_pipeline.py намеренно не запускались; RunCancelled-путь для потерянного лиза не покрыт; параллельность моделирована детерминированной последовательностью reaper+re-claim; mark_cancelled без возвращаемого значения — fenced-ness по состоянию БД.

## NEXT
Developer от e47cfd2; тесты должны стать зелёными без изменения сигнатур тестового контракта; test_worker + test_pipeline + test_jobs зелёные; VERIFY в новом worktree.
