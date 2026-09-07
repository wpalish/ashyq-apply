# T01 / A1 — ashyq-qa TEST_AUTHOR output (сохранено диспетчером дословно, оценка не менялась)

- ROLE: ashyq-qa, PHASE: TEST_AUTHOR
- INVOCATION_REF: agent_8d498240-020c-4819-b99b-58a13842503d (real runtime agentId)
- STATUS: TESTS_READY
- CHECKED_SHA: 85352b52211f0dd7f446b011d3f8c2c270089019 (baseline подтверждён git rev-parse, ветка ai/c1/t01/qa)
- QA_COMMIT_SHA: 7083f17ce9ff6b198461fdf1cf9f5f973bcb13f2

## RED_EVIDENCE (реальные команды, exit codes)
- `./.venv/bin/python -m pytest tests/test_account_flows.py tests/test_security.py -q` на чистом baseline: exit 0, 40 passed (утечка существует, старые тесты зелёные)
- После добавления новых тестов: exit 1, **7 failed, 45 passed in 13.81s**
- Только новые классы: 7 failed
- ruff format + check: exit 0

## RED (7 тестов, все на реальном assertion дефекта, без ошибок импорта)
1-3. TestResetTokenNeverLeavesTheMailbox::test_no_environment_puts_the_token_in_the_response[development|staging|testing]
4. test_the_letter_delivers_a_working_token
5. test_a_stranger_gets_no_token_in_the_answer
6. test_every_address_shape_gets_the_same_neutral_answer
7. test_security.py::TestResetRequestSafety::test_staging_gets_the_same_silent_answer_as_production

Типичный отказ: `AssertionError: assert {'detail', 'reset_link'} == {'detail'}`

## GREEN на baseline (5 новых guard-тестов)
matrix [production], test_a_token_from_the_letter_works_exactly_once, test_an_expired_letter_is_refused, test_a_reset_from_the_letter_ends_every_existing_session, test_reset_requests_for_one_email_hit_the_per_email_limit

## Regression surface — расхождение с packet
Packet предсказывал падение 6 существующих _request_link-зависимых тестов на baseline; фактически они проходят на baseline (утечка существует). Упадут ПОСЛЕ исправления до миграции на sink. QA их не трогал, assertions не ослаблены.

## CHANGED_FILES (только test scope)
- backend/tests/test_account_flows.py (+201): fixture mail_sink, RecordingSender(EmailSender) через monkeypatch.setattr(routes_account, "get_sender", ...), helper reset_token_from_letter, класс TestResetTokenNeverLeavesTheMailbox (12 тестов)
- backend/tests/test_security.py (+56): fixture auth_client дополнительно патчит routes_account.get_settings (ловушка planner закрыта; 40/40 прежних не сломались), класс TestResetRequestSafety

Production-код не тронут (git show --stat: только 2 тестовых файла).

## Примечание для developer
Официальный recording sender нужно добавить в app/mail.py по контракту; сейчас sink — test-helper RecordingSender внутри тестового файла.

## ENVIRONMENT
Python 3.12.13, backend/.venv, SQLite per-test (tmp_path), Docker/PostgreSQL/pgserver не требовались. Логи: /tmp/qa_t01_red_full.log, /tmp/qa_t01_red_counts.log, /tmp/qa_t01_red_newonly.log

## UNTESTED_RISKS
H01 (атомарность выкупа) вне T01; staging compose порты — S02; полный gate (pytest --cov-fail-under=92, mypy, frontend) на этой фазе не запускался.

## NEXT_ACTION
Developer начинает от QA commit 7083f17c, удаляет утечку (routes_account.py:203-204 + docstring), мигрирует 6 leak-зависимых тестов на sink, добавляет recording sender в app/mail.py; затем VERIFY_CANDIDATE в отдельной worktree.
