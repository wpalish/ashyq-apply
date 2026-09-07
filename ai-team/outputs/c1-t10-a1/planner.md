# T10 / A1 — ashyq-planner output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-planner
- INVOCATION_REF: agent_5bfbc55c-34a2-434b-845d-23cb3de20910 (real runtime agentId)
- STATUS: PLANNED (CONFIRMED)
- BASELINE_SHA: f7f14b28c43afe20df01ad38a26964c397f393fc (диспетчер подтверждает: worktree c1-t10-qa создан от этого SHA; planner без Bash проверял содержимое)
- FINDING_IDS: J02 — частично устарел (job-уровень частично исправлен), НО главный дефект жив: stale worker пишет terminal run state из exception handler

## ROOT_CAUSE
1. runner.py:273-280: `except Exception` в run_to_decision перехватывает LeaseLost (65-71; raised _check_cancelled 167-168) и пишет run.stage=FAILED, run.errors, run_failed audit, commit (279, _save 134-151). Существующий тест test_worker.py:329-349 ассертит только stage != "awaiting_user_decision" — проходит даже при stage="failed".
2. store.py:81-97 _fenced_out: session.get + мутации ORM flush-атся как UPDATE по PK (lost update) против reaper/нового владельца; fail (243-271), mark_cancelled (273-284), cancel (286-302) — check-then-act.
3. Нет attempt-токена: ограждение только (status='running', worker_id=me) (models/jobs.py:63-73; attempts инкрементится store.py:192 но не используется). worker_concurrency=2 (config.py:56) + self-reap loop (worker.py:55-74,103) — та же job может быть re-claimed тем же hostname:pid, обе попытки с одинаковым worker_id → owns()/complete/fail/heartbeat старой попытки проходят.
4. worker.py:239-249: возвращаемое значение store.complete() игнорируется; fenced worker всё равно пишет AuditEvent job_completed и commit-ит артефакты.
5. store.py:311-350 reap_expired: plain SELECT затем мутация — lost update против heartbeat (207-218) → двойное выполнение.
6. Смежный дефект той же контрольной точки: _check_cancelled (runner.py:155) session.refresh(self.run) молча отбрасывает незакоммиченные инкременты счётчиков (413-420, 540-541, 692 против _save каждый 4-й ряд 694-695 в _stage_funding) — исправить в том же рефакторинге.

## CONTRACT (кратко; полный в отчёте)
- Токен лизинга = job.attempts на момент claim; claim() возвращает его (RETURNING id, attempts). JobStore говорит от имени (worker_id, lease_token). БЕЗ новой колонки и миграций (UUID lease_token потребовал бы Alembic — сериализуемый ресурс; attempts-дизайн предпочтителен).
- Каждая ограждённая запись = одиночный условный UPDATE ... WHERE id=:id AND worker_id=:w AND attempts=:t (+ статусный предикат) с проверкой rowcount/RETURNING; check и запись атомарны; 0 строк = fenced, никаких изменений колонок (включая last_error, finished_at). Никаких blind-PK UPDATE после обычного SELECT.
- runner._save() становится write-boundary fence: атомарный renew-or-lose UPDATE jobs в той же транзакции что бизнес-записи, перед коммитом; 0 строк → rollback, LeaseLost, никаких бизнес-записей. _check_cancelled — fast-fail; гарантия — fence при записи. Проверка отмены — scalar SELECT, никакого refresh(self.run) при pending-мутациях.
- LeaseLost — control flow: `except LeaseLost: raise` ПЕРЕД except Exception; в worker — лог+rollback, БЕЗ записей (fail() на worker.py:134-139 удалить/доказать no-op). finally не трогает БД.
- Under fence: переходы статуса (complete/fail/mark_cancelled), progress (счётчики, stage_state, stage, heartbeat_at, worker_id), heartbeat/lease, recheck-enqueue (в dispatch-транзакции), артефакты (ProgramResultRow, ClaimRow, ConflictRow, checklists), audit events.
- complete: только (running, владелец, токен) иначе False, вызывающий пропускает audit+rollback. fail: retry→queued+backoff, exhausted→dead; fenced fail не пишет last_error. mark_cancelled: только владелец+токен. cancel (API, без токена): условный UPDATE cancel_requested WHERE status IN (queued,running) RETURNING. reap_expired: условный UPDATE ... WHERE status='running' AND lease_expires_at < now RETURNING attempts/max_attempts; retry-vs-dead из возвращённого; 0 строк → skip. heartbeat: +предикат токена; False останавливает _beat.
- Invariants: TERMINAL final; attempts +1 ровно на claim; complete job+артефакты — одна транзакция; fenced worker — НОЛЬ DB-записей из любого handler'а.
- Совместимость: публичный интерфейс JobStore сохранён (token — опциональный параметр, None = системная семантика API-вызовов). JobStatus/TERMINAL_STATUSES без изменений. API/фронтенд-формы без изменений.

## ACCEPTANCE (кратко)
1. Runner exception handler regression (RED на baseline): takeover mid-run → run.stage не изменился (не "failed"), errors не изменены, нет run_failed audit, закоммиченные артефакты сохранены.
2. Two-session PostgreSQL proof (pgserver embedded, conftest.py:36-104; SQLite недостаточно): takeover; same-worker_id reclaim t1 vs t2 → t1 отклонено (ключевое, worker_id-fence не может пройти); heartbeat-vs-reap; cancel-переходы; fail retry/exhausted; atomicity complete+артефакты; reap условность.
3. Cancel/complete/fail/reap state machine assertions в реальной PG.
4. Не-разрушительный checkpoint: инкременты счётчиков переживают контрольные точки (регрессия refresh-discard, root cause #6).
5. test_worker.py (вкл. TestLeaseFencing), test_pipeline.py, test_jobs.py остаются зелёными на сохранённом поведении.

## WRITE_SCOPE
- backend/app/pipeline/runner.py, backend/app/jobs/store.py, backend/app/jobs/worker.py, backend/app/models/jobs.py (вероятно без изменений), backend/tests/test_worker.py (two-session PG расширяют TestLeaseFencing), backend/tests/test_pipeline.py.
- conftest.py НЕ в scope (pg fixtures достаточны); вне scope: payment_reconcile.py, routes_research.py, pipeline/state.py, migrations/.

## RESERVATIONS / RISKS
- Локи: runner, job-store, worker, worker-tests. Файловых пересечений с T04/T09 нет; semantic-only: runner вызывает compute_funding_gap/total_cost (T04 меняет поведение, не сигнатуры — обнаружится тестами).
- runner.py и test_pipeline.py — сериализуемые ресурсы TEAM_RULES: параллельные писатели исключены диспетчером.
- pgserver env-зависим: если PG fixture skip на машине → two-session acceptance невыполним → эскалация BLOCKED, не мириться с SQLite-only.
- expire_on_commit=True + autoflush=False — учитывать в identity-map/транзакционных границах; QA тестирует окно check-then-act между двумя сессиями.
- РЕШЕНИЕ ДИСПЕТЧЕРА: attempts-token дизайн (без миграций) — УТВЕРЖДЁН; отклонение от него = запрос расширения с обоснованием миграции.

## NON-GOALS
T11/T13 (зависят от T10, неактивны), J01 TTL scheduling (T13), payment_reconcile, миграции без одобрения.
