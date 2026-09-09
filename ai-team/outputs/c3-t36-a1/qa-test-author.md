# T36 / A1 — ashyq-qa TEST_AUTHOR output

- ROLE: ashyq-qa, PHASE: TEST_AUTHOR
- STATUS: TESTS_READY
- CHECKED_SHA: edf546de9f998c0909337d0abe6f8e1c9c4a0be5 (подтверждён `git rev-parse HEAD`, ветка ai/c3/t36/qa, дерево чистое до записи)
- QA_COMMIT_SHA: 054331fa50a8069e0ff7d9d9b43ed6096b1169b7 (только 2 тестовых файла, production-код не тронут, push нет)
- CONTRACT: фиксированный контракт planner ещё не существовал (параллельный запуск); тесты написаны по карточке мастера §5-T36 (ai-team/reference/MASTER_C3_PROMPT_RU.md): последний XFF hop при trust_proxy_headers=true; compose ports → expose; verify_compose.sh получает проверку (проверку добавляет developer, QA-тест фиксирует состояние compose как контракт)

## FILES_CREATED_OR_MODIFIED (test scope only)
- `backend/tests/test_security.py` (+118): новый класс `TestForwardedAddressSemantics` после `TestAbuseLimits`; TestAbuseLimits и остальные существующие тесты не изменены
- `backend/tests/test_compose_publishes_no_api_port.py` (новый, 89 строк): статическая инспекция docker-compose.yml через yaml (yaml 6.0.3 есть в venv; types-PyYAML в requirements-dev нет и dependency-файлы вне моего scope — на импорте `# type: ignore[import-untyped]`)

## RED_RESULTS (baseline edf546d, реальные assertion-отказы, не import/environment errors)

Команда: `./.venv/bin/python -m pytest tests/test_security.py::TestForwardedAddressSemantics tests/test_compose_publishes_no_api_port.py` → exit 1, **3 failed, 3 passed in 11.77s** (повторный прогон — идентичный набор отказов, флейка нет)

1. **RED-A** `test_the_last_forwarded_hop_is_the_limiting_address` — FAIL на последнем hop-зонде:
   `E assert 401 == 429` — «with trust_proxy_headers=true the limit must be charged to the last XFF hop: 5.6.7.8 is already exhausted by the spoofed pair».
   Сценарий: 20 логинов с XFF «1.2.3.4, 5.6.7.8» (разные email, чтобы per-email бакет не маскировал) → 21-й с тем же XFF → 429; затем зонд только с «5.6.7.8» → baseline даёт 401 (свежий бакет). На baseline бакет пары уходит спуфнутому ПЕРВОМУ hop «1.2.3.4» (main.py:158-161 `forwarded.split(",")[0].strip()`).
   Второй зонд (XFF только «1.2.3.4» должен быть 401, не 429) на baseline не достигается — pytest останавливается на первом отказе; по коду baseline бакет «auth:1.2.3.4» выжжен парой, так что зонд получил бы 429 ≠ 401 (вывод из чтения кода, отдельным прогоном не подтверждён). После фикса оба зонда работают: пара выжигает «5.6.7.8», «1.2.3.4» остаётся свежим.
2. **compose RED-1** `test_the_api_service_does_not_publish_its_port_to_the_host` — FAIL:
   `E assert not ['${API_PORT:-8099}:8099']` — api публикует 8099 на все интерфейсы при UNIMATCH_TRUST_PROXY_HEADERS=true в общем env-якоре стека.
3. **compose RED-2** `test_the_api_port_stays_reachable_on_the_compose_network` — FAIL:
   `E assert '8099' in set()` — expose отсутствует; после фикса ports→expose тест требует «8099» в expose, чтобы nginx (web) сохранял доступ по compose-сети.

## GREEN_RESULTS (на baseline, классифицированы честно — это coverage, не выдуманный RED)

- **RED-B** `test_xff_is_ignored_when_proxy_headers_are_not_trusted` — PASS на baseline (ожидаемо по packet): trust_proxy_headers=False → ротация XFF не открывает свежий бакет, бакет = socket peer. Защищает требуемое поведение (б): при неверном «фиксе», снова начавшем доверять XFF без настройки, тест падает.
- **RED-C** `test_empty_or_absent_forwarded_for_charges_the_socket_peer` — PASS на baseline: пустой/пробельный/отсутствующий XFF — один бакет пира.
- `test_verify_compose_script_is_present_for_release_gating` — PASS: scripts/verify_compose.sh существует. Его текущие проверки (для developer): состояние сервисов, migrate exit 0, health API, регистрация, демо-run через worker, отдача фронтенда web. Проверки публикации 8099 НЕТ — developer добавляет её по карточке мастера (п.3 дизайна); QA-тест фиксирует состояние compose, содержимое скрипта не ослабляет и не фиксирует.

Существующий suite: `./.venv/bin/python -m pytest tests/test_security.py` → exit 1, **1 failed, 24 passed** — единственный отказ это мой RED-A; все прежние тесты, включая TestAbuseLimits (per-proxy budget, ротация адресов, per-email limit, Retry-After), зелёные без изменений. Замечание: `test_an_email_cannot_be_pounded_from_a_fresh_address_each_time` и reset-тесты используют одно-hop XFF → для них первый hop == последний, семантика фикса их не задевает.

## Parser validation (диагностика, не доказательство фикса)

Хелпер `_publishes_api_port_publicly` проверен на 9 случаях (exit 0, «PARSER_VALIDATION: PASS»): «${API_PORT:-8099}:8099»→public, «8099:8099»→public, «0.0.0.0:…»→public, «127.0.0.1:8099:8099»→loopback (разрешено, соответствует закомментированному варианту из карточки), dict-формы c/без published и с host_ip, чужой порт 8080→False. Это валидация логики теста: RED вызван реальным состоянием compose, а фиксированное состояние (ports→expose) даст GREEN без ложного PASS на wildcard-публикации.

## COMMANDS / EXIT_CODES
- `git rev-parse HEAD` → edf546de9f998c0909337d0abe6f8e1c9c4a0be5; `git status --porcelain` → пусто (до работы и после commit)
- pytest новых тестов → exit 1 (3 failed, 3 passed); pytest tests/test_security.py → exit 1 (1 failed, 24 passed)
- `ruff check` обоих файлов → exit 0; `ruff format` → применён к новым файлам; `mypy` обоих файлов → exit 0 (в mypy.ini files=app, тесты проверены явным запуском)

## ENVIRONMENT
Python 3.12 venv backend/.venv (проризионирован), SQLite per-test (auth_client), Docker daemon не использовался (compose-тест статический), PostgreSQL/pgserver не запускались, сеть не использовалась. Параллельные T33/T34/T35/T37 не затронуты: изменения только в двух моих тестовых файлах.

## LOGS / ARTIFACTS
- /Users/wpalish/ashyq-apply/ai-team/outputs/c3-t36-a1/logs/qa_t36_red_new_tests.log
- /Users/wpalish/ashyq-apply/ai-team/outputs/c3-t36-a1/logs/qa_t36_security_full.log
- /Users/wpalish/ashyq-apply/ai-team/outputs/c3-t36-a1/logs/qa_t36_lint.log

## UNTESTED_RISKS
- Полный gate (pytest --cov=app --cov-fail-under=92, mypy app, frontend) на этой фазе не запускался — только затронутые файлы и tests/test_security.py.
- Семантика «ровно один доверенный прокси»: цепочка из двух прокси при фиксе будет лимитировать внутренний прокси — это принятый дизайн карточки (опциональный `trusted_proxy_hops` — решение planner/developer).
- Первая-guard ветка RED-A (зонд «1.2.3.4» → 401) на baseline косвенно выведена из кода, не подтверждена отдельным прогоном; после фикса она начнёт выполняться и защищать контракт.
- nginx в стеке должен перезаписывать (а не дополнять) XFF; если бы он дополнял, последний hop — реальный клиент — контракт карточки это и фиксирует.

## NEXT_ACTION
Developer ветвится от QA commit 054331f (или от кандидата T34 с последующим merge по сериализации config.py): (1) main.py client_address — последний hop при trust_proxy_headers=true; (2) docker-compose.yml api: ports → expose [«8099»]; (3) verify_compose.sh — проверка отсутствия публикации 8099; затем VERIFY_CANDIDATE в отдельной worktree — мои 3 RED должны стать GREEN, 24 существующих + RED-B/RED-C остаться зелёными.
