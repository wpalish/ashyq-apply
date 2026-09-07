# T10 / A1 — ashyq-developer output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-developer
- INVOCATION_REF: agent_1cf00afc-992f-4af4-84fe-7eef013ed78f (real runtime agentId)
- STATUS: IMPLEMENTED
- QA_COMMIT_SHA: e47cfd2f982e8f3820825833b866bea67f56bfbe
- CANDIDATE_COMMIT_SHA: df1ad1194abcd7812eb9bf7d66e417b3d211c157 (заморожен; не push)

## CHANGED_FILES (только production scope; test_worker.py 0 изменений тела; models/jobs.py без изменений; без миграций)
backend/app/jobs/store.py; backend/app/pipeline/runner.py; backend/app/jobs/worker.py

## GATES (реальные)
- ruff format/check → 0
- mypy app tests → 0 (153 files)
- pytest tests/test_worker.py → 35 passed (27 существующих + 8 QA RED→GREEN)
- pytest tests/test_jobs.py → 30 passed на реальном PG (pgserver)
- Доп. проверка (full suite НЕ запускался): test_pipeline/test_diagnostics/test_citizenship_and_dates/test_profile_fields_are_used/test_live_regressions → 152 passed

## FENCE_COVERAGE (каждая запись условная — один UPDATE с проверкой rowcount/RETURNING; никаких blind-PK после простого SELECT)
- claim без изменений; lease token = attempts возвращённой job (как в замороженном тест-контракте)
- heartbeat/complete/mark_cancelled: UPDATE WHERE id + status='running' + worker_id + attempts(token); fenced → 0 строк, колонки не меняются; mark_cancelled возвращает bool
- fail: один условный UPDATE (retry-vs-dead в SQL case, константный backoff); fenced → read-only текущий статус, ничего не пишет (включая last_error)
- cancel (API): условный UPDATE WHERE status NOT IN terminal RETURNING
- reap_expired: условный take-away UPDATE RETURNING (id, attempts, max_attempts); retry-vs-dead из RETURNED; финальная запись ограничена маркером take-away
- _fenced_out удалён; owns() — read-only fast-fail
- runner._save(): renew-or-lose (fenced heartbeat ВНУТРИ транзакции бизнес-записей); 0 строк → rollback + LeaseLost
- _check_cancelled: scalar SELECT run.cancelled — session.refresh удалён (счётчики сохраняются)
- run_to_decision: except LeaseLost: raise перед RunCancelled/except Exception; finally не пишет БД
- worker: LeaseLost handler — только лог; dispatch уважает complete()→False → rollback (отбрасывает audit и recheck enqueue; payment_reconcile ветка так же); _beat fenced токеном, считанным раз за попытку

## CONTRACT_DEVIATIONS
Нет относительно замороженного тест-контракта (имя параметра, семантика fenced-write, fenced-fail-return, источник токена claim() — как в QA). Внутренние реализации (reaper take-away маркер; mark_cancelled bool вместо None) — не наблюдаемы тестами.

## NEXT
VERIFY_CANDIDATE на df1ad119; полный suite --cov-fail-under=92 — сериализует диспетчер (heavy slot).
