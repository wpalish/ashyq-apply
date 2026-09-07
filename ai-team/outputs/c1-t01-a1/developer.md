# T01 / A1 — ashyq-developer output (сохранено диспетчером дословно, оценка не менялась)

- ROLE: ashyq-developer
- INVOCATION_REF: agent_d55c6320-2ba5-4050-a78f-303d3ccb3110 (real runtime agentId)
- STATUS: IMPLEMENTED
- QA_COMMIT_SHA (start): 7083f17ce9ff6b198461fdf1cf9f5f973bcb13f2
- CANDIDATE_COMMIT_SHA: f7f14b28c43afe20df01ad38a26964c397f393fc (ветка ai/c1/t01/dev, parent 7083f17c, не отправлен, дерево чистое)

## CHANGED_FILES (git diff-tree)
- backend/app/api/routes_account.py
- backend/app/mail.py
- backend/tests/test_account_flows.py
- backend/app/config.py — НЕ изменён (no-op по контракту); backend/tests/test_security.py — НЕ изменён

## FIX
1. routes_account.py: удалено `if not settings.is_production: answer["reset_link"] = link` (203-204); ответ всегда ровно {"detail": ...}; docstring (143-147) переписан; точка внедрения get_sender и семантика single-use/TTL/revocation не изменены.
2. mail.py: добавлен RecordingSender(EmailSender) — собирает Message в self.messages; get_sender никогда его не возвращает; интерфейс EmailSender не изменён.
3. test_account_flows.py: мигрированы 5 leak-зависимых тестов + helper _request_link → _request_token (token из письма sink); planner называл 6 мест — фактически 5 вызовов + определение (проверено git show 85352b5).

## QA ASSERTIONS
Ноль изменений в телах тестов TestResetTokenNeverLeavesTheMailbox / TestResetRequestSafety. Механика: (a) import EmailSender → RecordingSender; (b) локальный тестовый RecordingSender удалён в пользу официального app.mail.RecordingSender (идентичное поведение — то самое перемещение, которое QA предусматривал); (c) обновлён docstring fixture mail_sink. Assertions/покрытие не ослаблены.

## GATES (реальные запуски в c1-t01-dev/backend)
- ruff format app tests → exit 0; ruff check app tests → exit 0
- mypy app tests → exit 0 (153 файлов)
- pytest --cov=app --cov-fail-under=92 → exit 0, 1122 passed, 0 failed, coverage 92.91% (порог не изменён)
- Целевой запуск test_account_flows + test_security → 52 passed (7 QA RED→GREEN)

## COVERAGE NOTE
app/mail.py: не покрыты только строки SmtpSender (55, 58-67 — pre-existing); RecordingSender полностью покрыт.

## COORDINATOR NOTE
AGENTS.md HANDOFF-правило не выполнялось (docs/process/HANDOFF.md вне write scope задачи) — координатор решает, кто фиксирует в HANDOFF/ledger.

## RISKS (вне T01)
H01 атомарность выкупа; S02 staging compose порты; frontend dead-код AuthGate/client.ts.

## NEXT
VERIFY_CANDIDATE в отдельной worktree на f7f14b2, затем review.
