# T01 / A1 — ashyq-planner output (сохранено диспетчером дословно, оценка не менялась)

- ROLE: ashyq-planner
- INVOCATION_REF: agent_5ffbc4d0-8bfc-4130-b2f1-a00a93465754 (real runtime agentId)
- DISPATCHED: 2026-09-06 (local), profile=safe
- STATUS: PLANNED
- BASELINE_SHA: 85352b52211f0dd7f446b011d3f8c2c270089019

## ROOT_CAUSE
- backend/app/api/routes_account.py:203-204 — `if not settings.is_production: answer["reset_link"] = link` в `request_password_reset`; неаутентифицированный POST /api/auth/password/reset-request возвращает действительный single-use reset token (внутри link, построенного на строке 179) в non-production.
- backend/app/config.py:146-148 — is_production только для environment in ("production","prod"); docker-compose.yml:48 ставит UNIMATCH_ENVIRONMENT: staging, compose публикует API на 0.0.0.0:${API_PORT:-8099} (75-76) → staging получает token в теле.
- routes_account.py:143-147 — docstring документирует как намеренное dev-поведение.
- Существующие тесты зависят от утечки: backend/tests/test_account_flows.py:152-155 `_request_link` возвращает response.json()["reset_link"], используется на 157, 169, 187, 213, 230, 239.
- Frontend: frontend/src/api/client.ts:171 (`reset_link?: string` optional), frontend/src/AuthGate.tsx:104-105 (отображение "(development build: …)"). Поле optional — компиляция не сломается, ветка станет dead.
- Другие потребители app.mail: только routes_account.py (get_sender на 180).

## CONTRACT (кратко)
- reset-request: unauthenticated, 202 на всех путях успеха; 429 на лимите; тело всегда точно `{"detail": "..."}`; ключ reset_link (или любой ключ с token/link) никогда не присутствует ни в одном окружении.
- reset: без изменений — 200 + PrincipalView + новый session cookie; generic 400 unknown/expired/used; 400 inactive user; 403 без активного workspace. PasswordResetConfirmIn (token min_length 20) без изменений.
- Данные: secrets.token_urlsafe(32), хранение только хэша, TTL=settings.password_reset_ttl_minutes (60), максимум один live token, single-use через used_at, подтверждение отзывает ВСЕ AuthSession. Модель/миграции не меняются.
- Нейтральность: existing active / unknown email / malformed email / inactive — идентичное тело 202, набор ключей ровно {"detail"}.
- Rate limits без изменений: reset:{address}, reset:email:{email}.
- Наблюдение token ТОЛЬКО через (а) доставленное Message email, (б) ConsoleSender log в dev, (в) sender, внедрённый тестом. Никаких новых settings-полей/flags/debug-endpoints. Production-guards (config.py:195-199) не смягчать.
- Mail sink механика: monkeypatch.setattr("app.api.routes_account.get_sender", ...) — эффективная точка внедрения (binding на уровне модуля, вызов на строке 180). mail.py может добавить recording test sender (класс, реализующий EmailSender, собирающий Message в список) — in-scope, никогда не выбирается get_sender для prod.
- API-совместимость: удаление reset_link — breaking change только для dev-наблюдаемости; frontend-типизация optional.

## ACCEPTANCE (9 пунктов)
1. Матрица окружений {development, staging, production, testing} → тело ровно {"detail": ...}, "reset_link" not in body и нет ключей с token. Заменяет/усиливает test_production_never_returns_the_link_in_the_response (test_account_flows.py:253).
2. Sink-based happy path: recording sender → ровно одно Message на email пользователя с рабочим token; POST /api/auth/password/reset с ним → 200, /api/auth/me → 200.
3. Stranger: второй неавторизованный клиент запрашивает reset для email victim → 202 нейтральный, без ключей token; token только в письме victim.
4. Нейтральность: existing == unknown == malformed по телу/статусу/набору ключей; в unknown/malformed случаях sink пуст.
5. Single-use сохранён (test_a_token_works_once:169 переопределён на sink) — второй выкуп → 400.
6. Expiry сохранён (test_an_expired_token_is_refused:187 переопределён на sink).
7. Revocation сохранён (test_a_reset_ends_every_existing_session:230 переопределён на sink) — прежние сессии → 401.
8. Rate limit: per-email 429 после auth_rate_limit_per_minute reset-requests (в test_security.py, расширив его локальную fixture auth_client, чтобы также патчить routes_account.get_settings).
9. Полные backend gates: ruff check+format, mypy, pytest --cov-fail-under=92 (frontend не трогаем).

## WRITE_SCOPE (финальный)
- backend/app/api/routes_account.py — удалить 203-204, исправить docstring 143-147
- backend/app/mail.py — recording test sender (только класс)
- backend/app/config.py — ожидается no-op; держим зарезервированным
- backend/tests/test_account_flows.py — мигрировать _request_link + 5 тестов на sink; добавить acceptance 1-4
- backend/tests/test_security.py — добавить acceptance 1 (staging) и 8; расширить его fixture auth_client

## RESERVATIONS / DEPENDENCIES
- locks: auth-account, security-tests, backend-config — подтверждены, достаточны; пересечений нет (safe).
- Предшественников нет. conftest autouse `_reset_rate_limiter` — read-only, без изменений. CI Python 3.12.

## RISKS
- Атомарность выкупа token — H01, вне рамок T01.
- Раскрытие портов staging compose — S02/развертывание, вне T01.
- Frontend dead branch (AuthGate.tsx:104-105, client.ts:171) — опциональный cleanup, только по решению координатора.
- Ловушка fixture: auth_client в test_security.py:47-49 НЕ патчит routes_account.get_settings (в отличие от test_account_flows.py:51) — новые reset-тесты там должны расширить fixture, иначе реальные глобальные настройки.
- Planner не запускал git — QA обязана подтвердить SHA и RED-first на 85352b5.
- 6 существующих тестов читают reset_link — их поломка на 202-ответе после исправления это ожидаемый RED→GREEN сигнал, не регрессия; assertions не смягчать.

## NON-GOALS
Нет миграций, нет новых настроек, нет frontend правок, нет compose/Dockerfile правок, нет изменений ConsoleSender/SmtpSender, нет изменений лимитера/session, нет новых эндпоинтов.
