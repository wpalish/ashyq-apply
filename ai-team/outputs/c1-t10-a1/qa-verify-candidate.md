# T10 / A1 — ashyq-qa VERIFY_CANDIDATE output (сохранено диспетчером; сокращено без изменения оценки)

- ROLE: ashyq-qa, PHASE: VERIFY_CANDIDATE
- INVOCATION_REF: agent_f58b2399-ac7b-4682-a1f9-81580bd90459 (real runtime agentId)
- STATUS: VERIFIED_PASS
- CHECKED_SHA: df1ad1194abcd7812eb9bf7d66e417b3d211c157 (ветка ai/c1/t10/verify, чисто; предки e47cfd2 и f7f14b28)

## COMMANDS_AND_RESULTS
1. diff-tree → ровно store.py, worker.py, runner.py; models/jobs.py и тесты ОТСУТСТВУЮТ в candidate
2. git diff e47cfd2..HEAD -- tests/test_worker.py → ПУСТО (QA-тела byte-identical)
3. test_worker.py → 35 passed (27+8; -k по 4 новым классам: 8 passed, 27 deselected)
4. test_jobs.py → 30 passed на реальном PG (pg_engine fixture: pgserver per-test CREATE DATABASE + migrate)
5. mypy → 0 (153 files); ruff check/format → 0
6. FULL suite --cov-fail-under=92 → exit 0, coverage 92.81% ≥ 92; 1130 точек, 0 F/E/s (итоговая строка не печатается из-за -q + coverage — счёт по маркерам)

## ADVERSARIAL_FINDINGS (probe v6, реальный PG, 38/38 проверок exit 0; лог outputs/c1-t10-a1/qa-logs/verify_t10_probe_out.log)
1. Two-session same worker_id (ключевой J02): claim t1 → reap → re-claim ТЕМ ЖЕ worker_id → t2; stale t1: complete/heartbeat/mark_cancelled → False, fail → read-only 'running'; status=running, attempts=2, last_error=reaper-заметка (STALE не записан), finished_at=NULL; t2 complete → succeeded.
2. LeaseLost mid-run на PG (полный pipeline, takeover в _stage_verify): jobs_failed=0, stage=program_verification (не failed), errors=[], finished_at=NULL, run_failed audit=0, артефакты 3==3, last_error чист. Дефект runner.py:273-280 закрыт.
3. reap vs heartbeat: продлённый lease → reap []; завершённый → heartbeat False, reap пропускает; реальное истечение → queued+backoff, attempts не инкрементится.
4. cancel API без токена: queued→cancelled; running→flag; terminal→no-op.
5. Positive control (нет over-fencing): владелец+токен пишет нормально.
6. RESIDUAL (не блокер): takeover+re-claim тем же worker_id между commit claim_one() и чтением токена в execute() → stale task прочитал НОВЫЙ токен и завершил job. Достижимо только при паузе claim→execute > полного lease (120с default). Рекомендация follow-up: прокидывать токен из claim_one() в execute() (worker.py:122-131), не перечитывать store.get(job_id).attempts.
7. Grep blind-PK: все update(Job) в store.py условные с RETURNING/rowcount; runner/worker прямых UPDATE не имеют.

## SCOPE_ASSESSMENT
Ослаблений нет: test_worker.py идентичен QA-коммиту; coverage 92 не понижен. Отклонение — mark_cancelled bool (согласовано; QA-тесты значение не ассертят).

## BLOCKERS: нет.
## UNTESTED_RISKS: окно token re-read (теоретическая); RunCancelled+LeaseLost одновременно (fence по коду); payment_reconcile-ветка на PG в пробах не гонялась (unit-покрытие есть); frontend/E2E вне T10.

## NEXT
df1ad119 → reviewer/integrator. Residual пробы 6 — кандидат на follow-up planner'у.
