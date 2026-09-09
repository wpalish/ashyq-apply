# Мастер-промпт c3: кампания безопасности ASHYQ Apply
### Закрытие всех P0-дыр, подтверждённых на HEAD `edf546d` (2026-09-08)

> Передай этот документ диспетчеру целиком (новая сессия, репозиторий на `main`).
> Карточки T33–T38 в §5 готовы к переносу в `ai-team/TASKS.md` без правок.
> Каждая находка проверена чтением кода на `edf546d` — строки указаны по этому SHA.

---

## 1. Роль и результат

Ты — главный диспетчер команды ASHYQ Apply (campaign **c3**). Кампания c2 закрыла
ядро поиска (recall 7/10, source_scan, claim_verifier); **безопасность в c2 не
трогалась вообще**. c3 закрывает все P0-находки внешнего аудита: обход paywall,
fail-open платежей, SMTP без верификации, спуфинг rate-limiter — и два хвостовых
дефекта корректности/документации.

Результат кампании — не «код написан», а: каждый пункт acceptance воспроизведён
командой с кодом выхода, полный suite зелёный на SQLite **и** PostgreSQL,
coverage ≥ 92, CI на обоих PR-матрицах зелёный, HANDOFF обновлён.

## 2. Контекст (проверь, не доверяй)

- HEAD на момент карточек: `edf546d` (merge PR #9). Подтверди `git rev-parse HEAD`.
- Baseline: backend pytest проходит (1096 тест-функций, SQLite; PG-ветка — в CI),
  ruff/mypy — чисто на **пиннах** репозитория, vitest 182+, CI зелёный (runs #79–83).
- Служебный вход для каждой карточки — `ai-team/reference/INDEPENDENT_AUDIT_2026-09-06.md`
  плюс этот документ. Находки ниже — **подтверждены на edf546d построчно**;
  уже исправленное не ломай: докажи regression-тестом и пометь `already_fixed_verified`.

## 3. Непереговорные правила (сверх TEAM_RULES)

1. Не ослабляй: auth, CSRF/CORS/CSP, SSRF-контролы, scrypt-стоимость, tenancy,
   coverage-floor 92, идемпотентность джоб. Unknown ≠ zero.
2. Не отключай paywall «чтобы не мешал тестам». Если тесту нужна free-организация —
   `payments_enabled=True` в фикстуре + отсутствие Entitlement, как в существующих
   `test_paywall.py`.
3. Не добавляй новых зависимостей без доказанной необходимости (smtplib/ssl — stdlib).
4. Каждый fix — сначала RED-тест на текущем HEAD (коммит RED, лог в packet),
   потом реализация. Тесты пишутся QA-ролью до developer-роли.
5. Секретов в git не появляется: тестовые ключи — генерируемые, `SecretStr`-пути
   не логируются, в acceptance-пакетах — маскированные значения.
6. Не трогай файлы чужих резервов. Пересечение — через диспетчера, не молча.
7. `main` не трогается; работа в `ai/c3/<task>/{qa,dev}`-worktrees от одного frozen SHA.

## 4. Подтверждённые находки (HEAD `edf546d`)

| ID | Находка | Где (file:line) | Серьёзность |
|---|---|---|---|
| **S1** | Paywall-обход: `set_decision` и `set_notes` возвращают полный `ProgramResult` (claims, scholarships, funding gap) без entitlement-проверки | `backend/app/api/routes_results.py:257` (set_decision), `:307` (set_notes) | P0, монетизация |
| **S2** | Paywall-обход: GDPR-экспорт отдаёт ВСЕ results с payload, claims, conflicts без paywall-проверки | `backend/app/api/routes_profile.py:249` (export_profile) | P0, монетизация |
| **S3** | ApiPay webhook fail-open: `hmac.new(b"")` валиден при пустом секрете; `validate_runtime()` не проверяет платёжные секреты; typo в `payments_provider` молча включает FakeProvider | `backend/app/payments/apipay.py:161` (verify_webhook), `backend/app/config.py` (validate_runtime, ~:190), `backend/app/payments/provider.py:65` (get_provider) | P0, деньги |
| **S4** | SMTP STARTTLS без проверки сертификата — MITM перехватывает reset-токен | `backend/app/mail.py:64` | P0, auth |
| **S5** | `needs_rehash` — мёртвый код: scrypt-апгрейд при логине не происходит | `backend/app/security.py:62` (никем не вызывается; `routes_auth.py` login ~:126) | P1, auth |
| **S6** | Rate-limiter спуфится: `client_address` берёт **первый** hop X-Forwarded-For, а nginx (compose) аппендит реальный IP в конец; при этом compose публикует порт 8099 наружу с `UNIMATCH_TRUST_PROXY_HEADERS=true` — противоречие собственному комментарию | `backend/app/main.py:159`, `docker-compose.yml` (api.ports), `frontend/nginx.conf` (`$proxy_add_x_forwarded_for`) | P0, abuse |
| **S7** | Дубли claims при повторном входе в funding-стадию: `_update_result` аппендит `extra_claims` без `_replace_evidence` | `backend/app/pipeline/runner.py:1099–1101` | P1, данные |
| **S8** | README/RELEASE_CHECKLIST протухли: «recall 2 of 9» (реально 7/10 от T30), «CI red since 09-04» (CI зелёный с 09-07), verification-таблица с разными числами | `README.md:23`, `RELEASE_CHECKLIST.md` | P2, доверие |

---

## 5. Карточки задач (перенести в `ai-team/TASKS.md`)

---

### T33 — Целостность paywall: три обходных эндпоинта (S1+S2)

Приоритет: **P0**. Findings: S1, S2 внешнего аудита 2026-09-08. Статус: BACKLOG.

## Зависимости
Нет. Файлы не пересекаются с T34–T37.

## Обязательные отдельные вызовы
- ashyq-planner, ashyq-qa, ashyq-developer, ashyq-reviewer, **ashyq-security** (обязателен: монетизация)

## Резервы
- `paywall-contract` (routes_results.py, routes_profile.py, payments/entitlements.py)

## Начальный допустимый scope
- `backend/app/api/routes_results.py` (set_decision, set_notes)
- `backend/app/api/routes_profile.py` (export_profile)
- `backend/tests/test_paywall.py`, `backend/tests/test_billing_api.py`
- `backend/tests/test_frontend_contract.py` (если типы ответов меняются — нет, менять нельзя)

## Дизайн исправления (обсуди в contract; это исходная позиция)
1. **`set_decision` / `set_notes`**: решения/заметки остаются ДОСТУПНЫМИ free-пользователю
   на видимых строках (это верх воронки, ведущая к оплате), но ответ обязан
   использовать существующую проекцию:
   ```python
   _profile_id, allowed = access_for_run(session, run_id, principal)
   ...
   return result if allowed else free_view(result)
   ```
   `free_view()` уже существует (`payments/entitlements.py:76`) и делает ровно то,
   что нужно: срезает claims/scholarships/funding_gap/checklist. Никакой новой логики обрезания.
2. **`export_profile`**: data-portability остаётся для ВСЕГО, что принадлежит пользователю
   (профиль, метаданные прогонов, его решения/заметки, audit), но claims, conflicts
   и полные result-payload попадают в экспорт **только при** `has_full_access`.
   Каждая result-строка при отсутствии доступа — те же поля, что даёт `free_view`
   (id, university, program, degree, score, решение), плюс явное поле
   `"paid_content_withheld": true`. Текст `"note"` в ответе обновить: он сейчас
   обещает «every claim and conflict» — после фикса обязан говорить правду о том,
   что включено и почему.
3. **Surface-scan тест** (главная страховка, чтобы это не повторилось):
   параметризованный тест перебирает ВСЕ маршруты `app.routes`, отдающие
   `ProgramResult`/claims/conflicts (или dict с payload), и для каждого утверждает:
   free-организация (payments_enabled=True, без Entitlement) не получает ни одного
   claim_type с материальным значением, ни `scholarships != []`, ни `funding_gap`,
   ни `checklist`. Паттерн уже есть в tenancy-тестах (`test_security.py`,
   «another tenant gets 404») — воспроизведи его стиль.

## Acceptance
- [ ] RED на `edf546d`: free-орг через `set_decision`/`set_notes`/`export_profile`
      получает claims/scholarships/funding_gap (тесты фиксируют текущую дыру)
- [ ] После фикса: `set_decision`/`set_notes` на видимой строке → 200,
      payload идентичен проекции `free_view` (побайтовое сравнение полей)
- [ ] После фикса: `export_profile` без entitlement содержит профиль/решения/audit
      и НЕ содержит ни одного claim/conflict/checklist; с entitlement — полный
- [ ] Surface-scan: перебор всех маршрутов не находит новых утечек paid-контента
- [ ] Покупка кейса (существующий флоу в test_paywall.py) открывает полные ответы
      на тех же эндпоинтах — регрессии оплаты нет
- [ ] Полный suite зелёный, coverage ≥ 92

---

### T34 — Payments fail-closed: секреты, провайдер, webhook (S3)

Приоритет: **P0**. Статус: BACKLOG.

## Зависимости
Нет по файлам с T33; **конфликт с T36 по `config.py`** → сериализовать: T34 → T36
(или диспетчер делит блоки: T34 владеет payments-блоком настроек, T36 — proxy-блоком;
решение записать в ledger до старта обоих).

## Обязательные отдельные вызовы
- ashyq-planner, ashyq-qa, ashyq-developer, ashyq-reviewer, **ashyq-security**

## Резервы
- `payments-contract` (config.py payments-блок, payments/**, routes_webhooks.py)

## Начальный допустимый scope
- `backend/app/config.py` (validate_runtime + payments-настройки)
- `backend/app/payments/provider.py`, `backend/app/payments/apipay.py`
- `backend/app/payments/fake.py` (только если нужен флаг для теста)
- `backend/tests/test_payments_config.py`, `test_payment_webhook.py`, `test_apipay_adapter.py`

## Дизайн исправления
1. **`validate_runtime()`** (config.py, добавить до существующих проверок):
   ```python
   if self.payments_provider not in {"fake", "apipay"}:
       raise RuntimeError("UNIMATCH_PAYMENTS_PROVIDER must be 'fake' or 'apipay'.")
   if self.payments_provider == "apipay":
       if len(self.apipay_api_key.get_secret_value()) < 20:
           raise RuntimeError("UNIMATCH_APIPAY_API_KEY is required (>=20 chars) when provider is apipay.")
       if len(self.apipay_webhook_secret.get_secret_value()) < 32:
           raise RuntimeError("UNIMATCH_APIPAY_WEBHOOK_SECRET is required (>=32 chars) when provider is apipay.")
   if self.is_production and self.payments_enabled and self.payments_provider == "fake":
       raise RuntimeError("Production cannot take payments through the fake provider.")
   ```
2. **`ApiPayProvider.__init__`** (apipay.py): `raise ValueError` при пустых
   `api_key`/`webhook_secret` — защита даже если validate_runtime обойдён (другой процесс).
3. **`verify_webhook`**: пустой `self._secret` → `return False` без вычисления HMAC.
4. **`get_provider()`** (provider.py): ветка `payments_provider == "apipay"` остаётся,
   любое иное значение уже отсечено валидацией; для читаемости добавить комментарий
   и `assert`-подобную защиту на случай вызова до validate_runtime.
5. Тесты: (а) пустой секрет → webhook 401 при корректной подписи с ключом `b""`
   (это и есть эксплойт — тест ДОЛЖЕН быть RED на baseline); (б) typo
   `payments_provider="apipy"` → RuntimeError при старте; (в) production + fake +
   payments_enabled → RuntimeError; (г) все существующие payment-тесты живы.

## Acceptance
- [ ] RED на `edf546d`: подпись, вычисленная с ключом `b""`, принимается вебхуком
- [ ] После фикса: пустой секрет → отказ всегда; секрет ≥32 симв. Required при apipay
- [ ] typo провайдера и production+fake+enabled → отказ старта с понятным сообщением
- [ ] Существующие тесты платежей/вебхуков/реконсайлера зелёные без ослабления
- [ ] Полный suite зелёный, coverage ≥ 92

---

### T35 — SMTP TLS-верификация + scrypt-рехеширование при логине (S4+S5)

Приоритет: **P0** (TLS) / **P1** (rehash). Статус: BACKLOG.

## Зависимости
Нет (mail.py и routes_auth.py никем в c3 больше не трогаются).

## Обязательные отдельные вызовы
- ashyq-planner, ashyq-qa, ashyq-developer, ashyq-reviewer, **ashyq-security**

## Резервы
- `auth-flows` (mail.py, security.py, routes_auth.py, routes_account.py)

## Начальный допустимый scope
- `backend/app/mail.py`, `backend/app/config.py` (одна настройка: `smtp_tls_verify: bool = True`)
- `backend/app/api/routes_auth.py` (login: rehash), `backend/app/security.py` (только если нужен хелпер)
- `backend/tests/test_account_flows.py`, `backend/tests/test_logging_and_correlation.py`

## Дизайн исправления
1. **SMTP** (mail.py): `SmtpSender.send`:
   ```python
   import ssl
   ctx = ssl.create_default_context()
   if not self.settings.smtp_tls_verify:
       ctx.check_hostname = False
       ctx.verify_mode = ssl.CERT_NONE
   ...
   with smtplib.SMTP(...) as smtp:
       smtp.starttls(context=ctx)
   ```
   Настройка `smtp_tls_verify` (default True) — для self-hosted релея без валидного
   сертификата; в production она должна оставаться True (добавить в validate_runtime
   предупреждение-отказ при `is_production and not smtp_tls_verify`).
   Тест: замокать `smtplib.SMTP` и утвердить, что `starttls` вызван с контекстом,
   у которого `check_hostname is True` и `verify_mode == ssl.CERT_REQUIRED`.
2. **Rehash** (routes_auth.py, login, после `verify_password` успеха):
   ```python
   if needs_rehash(user.password_hash):
       user.password_hash = hash_password(payload.password)
       session.add(AuditEvent(..., action="password_rehashed", ...))
   ```
   Тест: зарегистрировать пользователя с `hash_password(pwd, n=2**14)`, залогинить,
   утвердить: хеш изменился, префикс `scrypt$131072$`, audit-событие записано,
   повторный логин не пишет второе событие. Тест на производительность не нужен —
   scrypt-cost в фикстурах уже занижен конфигом тестов.

## Acceptance
- [ ] RED на `edf546d`: starttls вызывается без SSL-контекста (замоканный SMTP ловит это)
- [ ] После фикса: контекст по умолчанию строгий; отказ production при отключённой верификации
- [ ] Логин пользователя со старым scrypt-хешем апгрейдит его и пишет audit-событие
      ровно один раз; тест RED на baseline (сейчас хеш не меняется)
- [ ] Полный suite зелёный, coverage ≥ 92

---

### T36 — Доверенный прокси: последний hop + непубликованный API-порт (S6)

Приоритет: **P0**. Статус: BACKLOG.

## Зависимости
**После T34** (общий `config.py`; если диспетчер разделил блоки — можно параллельно,
что зафиксировать в ledger).

## Обязательные отдельные вызовы
- ashyq-planner, ashyq-qa, ashyq-developer, ashyq-reviewer, **ashyq-security**

## Резервы
- `runtime-config` (main.py, docker-compose.yml, scripts/verify_compose.sh)

## Начальный допустимый scope
- `backend/app/main.py` (client_address), `backend/app/config.py` (proxy-блок)
- `docker-compose.yml` (сервис api), `scripts/verify_compose.sh`
- `backend/tests/test_security.py` (или новый `test_client_address.py`)

## Дизайн исправления
1. **`client_address`** (main.py:152): при `trust_proxy_headers=True` брать hop
   **справа**: с одним доверенным прокси (nginx в стеке) последняя запись —
   реальный клиент, всё левее — клиентский спуф:
   ```python
   if settings.trust_proxy_headers:
       hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
       if hops:
           return hops[-1]   # ровно один доверенный прокси в стеке
   ```
   Если planner считает нужным обобщить (`trusted_proxy_hops: int = 1`, брать
   `hops[-trusted_proxy_hops]` с защитой от отрицательных) — допустимо, но
   значение по умолчанию обязано давать именно последний hop.
2. **compose**: у сервиса `api` заменить `ports: "${API_PORT:-8099}:8099"` на
   `expose: ["8099"]` (инспекция — через `docker compose exec` или ssh-туннель;
   комментарий в файле обновить). Если владельцу нужен локальный доступ к
   `/docs` — закомментированная строка `# - "127.0.0.1:8099:8099"` с пояснением,
   что публикация на всех интерфейсах + trust_proxy_headers = спуфинг лимитеров.
3. **verify_compose.sh**: добавить проверку `docker compose config` не содержит
   публикации 8099 на 0.0.0.0.
4. Тесты: (а) RED: запрос с `X-Forwarded-For: 1.2.3.4, 5.6.7.8` при
   trust_proxy_headers=True списывает лимит на `5.6.7.8`, не на `1.2.3.4`;
   (б) trust=False → любые XFF игнорируются, адрес = socket peer; (в) пустой
   XFF → peer. Существующие `TestAbuseLimits` не ослаблять.

## Acceptance
- [ ] RED на `edf546d`: спуфнутый первый hop получает собственный лимит-бакет
- [ ] После фикса: последний hop; при одном nginx в цепи адрес клиента корректен
- [ ] compose не публикует 8099 наружу; verify_compose.sh это проверяет
- [ ] Существующие abuse-limit тесты зелёные без ослабления
- [ ] Полный suite зелёный, coverage ≥ 92

---

### T37 — Дубли claims при повторном входе в funding-стадию (S7)

Приоритет: **P1**. Статус: BACKLOG.

## Зависимости
Нет по файлам (runner.py в c3 больше никто не трогает). Может идти параллельно T33–T36.

## Обязательные отдельные вызовы
- ashyq-planner, ashyq-qa, ashyq-developer, ashyq-reviewer (security — опционален)

## Резервы
- `pipeline-runner` (pipeline/runner.py, tests/test_pipeline.py)

## Начальный допустимый scope
- `backend/app/pipeline/runner.py` (`_update_result`, только ветка extra_claims)
- `backend/tests/test_pipeline.py`

## Дизайн исправления
`_update_result` (runner.py:1099): при `extra_claims is not None` сначала
`self._replace_evidence(row.id)` (метод уже существует, :1122), затем
`_store_claims`/`_store_conflicts`. Учесть: `_replace_evidence` сносит claims и
verify-стадии — проверить, что funding-путь не вызывается с уже заполненным
verify-набором в том же прогоне (если вызывает — заменить на точечный delete по
`claim_type IN funding-типы` + конфликт-ветка; решение фиксирует planner в contract).
Тест RED: прогнать funding-стадию дважды (существующий паттерн `TestRetry` /
recheck-рецепты), assert: `ClaimRow` по `result_id` не удвоился, решения
пользователя сохранились, `SUPERSEDED`-механика T32 не пострадала.

## Acceptance
- [ ] RED на `edf546d`: повторный вход в funding удваивает claims по result_id
- [ ] После фикса: ровно один набор funding-claims; user_decision/notes сохранены
- [ ] reextract_page (T32) и TestRetry зелёные — регрессий свежести нет
- [ ] Полный suite зелёный, coverage ≥ 92

---

### T38 — Правдивые документы после c2 (S8)

Приоритет: **P2**. Статус: BACKLOG.

## Зависимости
После T33–T37 (числа для таблиц берутся из их acceptance-пакетов).

## Обязательные отдельные вызовы
- ashyq-planner, ashyq-developer, ashyq-reviewer (QA-роль опциональна: проверок кода нет)

## Резервы
- `docs-truth` (README.md, RELEASE_CHECKLIST.md, docs/CURRENT_STATE.md)

## Начальный допустимый scope
- `README.md`, `RELEASE_CHECKLIST.md`, `docs/CURRENT_STATE.md`

## Дизайн исправления
1. README:23 — «live programme-page recall (2 of 9 canary institutions)» заменить
   на факт T30: «7 of 10 canary institutions (2026-09-08), see docs/LIVE_DISCOVERY_REPORT.md».
2. Verification-таблица README: числа из ОДНОГО источника — последний зелёный CI-run
   на merge-коммите; удалить строку-противоречие про Docker («written, never run» —
   противоречит DOCKER_VERIFICATION.md и gate 22).
3. RELEASE_CHECKLIST: заголовок «CI on main is red since 2026-09-04» заменить на
   текущее состояние (зелёный с #79–83; зафиксировать правило: статус CI обновляется
   при каждом слиянии, красный main — hotfix выше фич по приоритету).
4. CURRENT_STATE: добавить секцию «after c2/c3» с одной таблицей: что открыто
   (реестр 19, i18n ядра, юрист, деплой, T31 blocked).

## Acceptance
- [ ] Ни одно число в README/RELEASE_CHECKLIST не противоречит acceptance-пакетам c2/c3
- [ ] Каждое изменённое утверждение имеет ссылку на источник (отчёт/CI-run/пакет)
- [ ] `python3 scripts/handoff_check.py` и линт доков (если есть) зелёные

---

## 6. Оркестрация c3

```
Старт (замороженный SHA edf546d+):
  T33 (paywall)      ─┐
  T34 (payments)     ─┼─ параллельно: файлы дизъюнктны, КРОМЕ config.py у T34/T36
  T35 (smtp+rehash)  ─┤   → T34 и T36 сериализованы (T34 первым) ИЛИ разделение
  T37 (funding dup)  ─┘     блоков config.py записано в ledger ДО старта
После T33–T37:
  T38 (docs) — берёт числа из acceptance-пакетов
Интеграция: единый integrator-slot, ai/c3/integration → PR #10 → оба матричных прогона
```

Резервы (координационные): `paywall-contract`, `payments-contract`, `auth-flows`,
`runtime-config`, `pipeline-runner`, `docs-truth`. Контрактные файлы
(`backend/app/schemas/**`, `frontend/src/types.ts`, миграции) в c3 НЕ редактируются —
если QA/developer понадобится (не должно), это через диспетчера к владельцу.

Frontend: изменений нет. `free_view`-проекция и `payment_required`-402 уже
отрендерены PaywallNotice/PaymentModal; ответ 200-with-trimmed-payload на
decision/notes фронт не отличает от текущего (он уже получает полный payload
и не читает claims из него — проверить в QA-контракте T33, что ShortlistScreen
не ломается: если он читает `funding_gap` из ответа decision — это единственное
место, требующее同步; тогда решение диспетчера: 402 вместо trim для decision,
что тоже допустимо по продукту).

## 7. Гейты кампании (Definition of Done c3)

1. Каждый acceptance-пункт каждой карточки: выполнен с командой и кодом выхода
   в acceptance-packet, либо `already_fixed_verified` с тестом, либо `NOT_RUN`
   с причиной в residual_risks (NOT_RUN ≠ PASS).
2. Полный backend suite зелёный на SQLite и PostgreSQL (CI обе матрицы).
3. coverage ≥ 92; ruff/mypy/tsc/eslint чисты на пинах репозитория.
4. e2e (включая e2e:auth) зелёные в CI.
5. НОВЫЙ security-scan: surface-тест из T33 прогнан и зелёный; все RED-тесты
   кампании воспроизводимы реверсом (checkout baseline → тест красный).
6. HANDOFF.md обновлён; ledger закрыт; релиз-чеклист дополнен гейтами c3
   (по одному на карточку: «paywall целостен», «payments fail-closed», ...).
7. Внешние решения НЕ требуются: кампания не включает деплой, реальный ApiPay,
   реестр вузов и i18n — это c4+.

## 8. Что остаётся владельцу после c3 (вне скоупа, не делать)

- Деплой на Fly (всё готово: fly.toml, образы, compose проверен) — нужен твой запуск.
- Юрист: privacy/terms (ru/kk/en).
- Реестр 19→60: 41 кандидатура с официальными seed-URL или разрешение команде
  сгенерировать и прогнать канары батчами (по правилу T30: ≥2 категории на вуз).
- T31 (LLM T2 shadow): выбор провайдера + секреты вне git + data-policy.
- i18n ядра (9 экранов на ru/kk) — следующий продуктовый спринт после c3.
