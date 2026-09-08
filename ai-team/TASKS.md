# Очередь ASHYQ

Это исходный backlog. Фактические статусы хранит единственный главный агент в ledger.

| ID | Приоритет | Работа | Зависимости |
|---|---|---|---|
| [T01](tasks/T01.md) | P0 | Reset без выдачи токена клиенту | — |
| [T02](tasks/T02.md) | P1 | Trusted proxy и защита rate limit | T01 |
| [T03](tasks/T03.md) | P1 | Атомарный reset и topology лимитера | T01, T02 |
| [T04](tasks/T04.md) | P1 | Полная, частичная и неизвестная стоимость | — |
| [T05](tasks/T05.md) | P2 | Currency/period-safe scholarship classification | T04 |
| [T06](tasks/T06.md) | P1 | Применимость award по датам и intake | T04, T05 |
| [T07](tasks/T07.md) | P1 | Подтверждённое stacking и совместимость aid | T06 |
| [T08](tasks/T08.md) | P1 | Согласованные buckets и affordability | T07 |
| [T09](tasks/T09.md) | P1 | Draft lifecycle и изоляция кейсов | — |
| [T10](tasks/T10.md) | P1 | Fencing всех writes после lease loss | — |
| [T11](tasks/T11.md) | P1 | Run snapshots и canonical state | T10 |
| [T12](tasks/T12.md) | P1 | Версии checklist и повторная сборка | T11 |
| [T13](tasks/T13.md) | P1 | Правильные TTL и recheck scheduling | T10 |
| [T14](tasks/T14.md) | P2 | Валидный и атомарный rerank contract | T08, T09, T11 |
| [T15](tasks/T15.md) | P2 | Безопасные XLSX/CSV text cells | T04, T05 |
| [T16](tasks/T16.md) | P1 | Browser/HTTP egress и корректные outcomes | — |
| [T17](tasks/T17.md) | P1 | Ограниченный и изолированный PDF parsing | — |
| [T18](tasks/T18.md) | P1 | Измеримый live research на curated scope | T08, T13, T16, T17 |
| [T19](tasks/T19.md) | P2 | Постепенное раскрытие анкеты | T09 |
| [T20](tasks/T20.md) | P2 | Mobile стоимость, период и accessibility | T08, T09 |
| [T21](tasks/T21.md) | P1 | Cross-module regression gates | T03, T08, T12, T13, T14, T15, T16, T17 |
| [T22](tasks/T22.md) | P1 | Стабильный E2E и отдельные artifacts | T19, T20, T21 |
| [T23](tasks/T23.md) | P2 | Правдивые docs и scope release | T18, T22 |
| [T24](tasks/T24.md) | P1 | Runtime, recovery, restore и release verdict | T23 |

На каждую задачу — четыре независимые роли; на критичные — дополнительный Security. Зависимости плюс реальные пересечения файлов определяют параллелизм.

---

# Кампания c3 — безопасность (мастер-промпт: ai-team/reference/MASTER_C3_PROMPT_RU.md)

Baseline `edf546d` (main @ PR #9). Находки S1–S8 подтверждены на этом SHA. Служебный вход — `ai-team/reference/INDEPENDENT_AUDIT_2026-09-06.md` + мастер-промпт. Worktrees `ai/c3/<task>/{qa,dev}`. Полный текст карточек (с дизайн-позициями и точными acceptance) — §5 мастер-промпта; ниже — рабочие копии без изменений смысла.

## T33 — Целостность paywall: три обходных эндпоинта (S1+S2)

P0. Findings: S1, S2. Резерв: `paywall-contract`. Роли: planner, dev, qa, reviewer, **security**.
Scope: `backend/app/api/routes_results.py` (set_decision, set_notes), `backend/app/api/routes_profile.py` (export_profile), тесты paywall/billing/frontend_contract.
Дизайн-позиция: decision/notes остаются доступны free на видимых строках (верх воронки), но ответ через существующую проекцию `free_view` (payments/entitlements.py:76); `export_profile` — данные пользователя всегда (профиль, метаданные прогонов, решения/заметки, audit), claims/conflicts/полные result-payload только при `has_full_access`, урезанные строки с `"paid_content_withheld": true` и честным текстом note; surface-scan тест всех маршрутов, отдающих ProgramResult/claims/conflicts.
Acceptance: RED на edf546d (free-орг получает claims/scholarships/funding_gap через три эндпоинта); после фикса payload = free_view побайтово на видимой строке; export без entitlement не содержит ни одного claim/conflict/checklist, с entitlement — полный; surface-scan чист; покупка кейса открывает полные ответы; полный suite зелёный, cov ≥ 92.

## T34 — Payments fail-closed: секреты, провайдер, webhook (S3)

P0. Резерв: `payments-contract` (config.py payments-блок). **СЕРИАЛИЗОВАН с T36 по config.py — T34 первым.** Роли: 4+security.
Scope: `backend/app/config.py` (validate_runtime + payments-настройки), `payments/provider.py`, `payments/apipay.py`, `payments/fake.py` (при необходимости), тесты payments/webhook/apipay.
Дизайн-позиция: validate_runtime — провайдер ∈ {fake, apipay} (иначе RuntimeError); при apipay api_key ≥20 и webhook_secret ≥32 обязательны; production + fake + payments_enabled → RuntimeError; ApiPayProvider.__init__ — ValueError на пустые секреты; verify_webhook — пустой секрет → False без вычисления HMAC.
Acceptance: RED на edf546d (подпись ключом b"" принимается вебхуком); после фикса — fail-closed везде, секреты required при apipay; typo провайдера и production+fake → отказ старта; существующие payment-тесты живы; полный suite, cov ≥ 92.

## T35 — SMTP TLS-верификация + scrypt-рехеширование при логине (S4+S5)

P0 (TLS) / P1 (rehash). Резерв: `auth-flows`. Роли: 4+security.
Scope: `backend/app/mail.py`, `backend/app/config.py` (smtp_tls_verify: bool = True), `backend/app/api/routes_auth.py` (login rehash), `security.py` (хелпер при необходимости), тесты account_flows/logging.
Дизайн-позиция: starttls с `ssl.create_default_context()`; `smtp_tls_verify=False` — только для self-hosted релея; production + verify=False → отказ в validate_runtime; rehash после успешного verify_password + AuditEvent `password_rehashed`, ровно один раз.
Acceptance: RED на edf546d (starttls без SSL-контекста; хеш не меняется при логине); после фикса — строгий контекст по умолчанию, апгрейд + audit ровно один раз; полный suite, cov ≥ 92.

## T36 — Доверенный прокси: последний hop + непубликованный API-порт (S6)

P0. Зависимость: **после T34** (общий config.py). Резерв: `runtime-config`. Роли: 4+security.
Scope: `backend/app/main.py` (client_address), `backend/app/config.py` (proxy-блок), `docker-compose.yml` (api: ports → expose; опционально закомментированный 127.0.0.1-вариант с пояснением), `scripts/verify_compose.sh`, тесты security/client_address.
Дизайн-позиция: при trust_proxy_headers брать ПОСЛЕДНИЙ hop XFF (один доверенный прокси в стеке; обобщение `trusted_proxy_hops: int = 1` допустимо, default обязан давать последний hop); compose не публикует 8099 на 0.0.0.0; verify_compose.sh проверяет отсутствие публикации.
Acceptance: RED на edf546d (спуфнутый первый hop получает собственный лимит-бакет); после фикса — последний hop, адрес клиента корректен при одном nginx; compose не публикует 8099; abuse-тесты зелёные; полный suite, cov ≥ 92.

## T37 — Дубли claims при повторном входе в funding-стадию (S7)

P1. Резерв: `pipeline-runner`. Роли: 4 (security опционален).
Scope: `backend/app/pipeline/runner.py` (_update_result, только ветка extra_claims), `backend/tests/test_pipeline.py`.
Дизайн-позиция: при extra_claims сначала `_replace_evidence` (существует, :1122), затем `_store_claims`/`_store_conflicts`; planner обязан проверить, что funding-путь не сносит verify-набор того же прогона — иначе точечный delete по funding-типам claim_type (решение в contract).
Acceptance: RED на edf546d (повторный вход в funding удваивает claims по result_id); после фикса — ровно один набор funding-claims, user_decision/notes сохранены; reextract_page (T32) и TestRetry зелёные; полный suite, cov ≥ 92.

## T38 — Правдивые документы после c2 (S8)

P2. Зависимость: после T33–T37 (числа из acceptance-пакетов). Резерв: `docs-truth`. Роли: 4 (QA сверяет числа с пакетами — усиление против «опциональна» мастер-промпта, по минимуму 4 роли TEAM_RULES).
Scope: `README.md`, `RELEASE_CHECKLIST.md`, `docs/CURRENT_STATE.md`.
Дизайн-позиция: README:23 → факт T30 «7 of 10 canary institutions (2026-09-08)» со ссылкой на LIVE_DISCOVERY_REPORT.md; verification-таблица из ОДНОГО источника (последний зелёный CI на merge-коммите), убрать противоречие про Docker; RELEASE_CHECKLIST заголовок CI → актуальное состояние + правило обновления статуса при каждом слиянии; CURRENT_STATE секция after c2/c3 (что открыто: реестр 19, i18n, юрист, деплой, T31 blocked).
Acceptance: ни одно число не противоречит пакетам c2/c3; каждое изменённое утверждение с ссылкой на источник; handoff_check.py зелёный.
