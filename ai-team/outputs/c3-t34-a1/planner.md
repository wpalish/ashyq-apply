# T34 A1 — Planner contract (frozen)

- Invocation ref: agent_fa833a7b-7147-4ee3-ad1f-e8c006d7340f
- Baseline: edf546de9f998c0909337d0abe6f8e1c9c4a0be5
- STATUS: PLANNED
- Dispatcher ruling (config.py): T34 и T35 developers могут идти параллельно (хунки разнесены/заякорены: T34 — только тело validate_runtime, вставка вверху; T35 — поле после :96 + проверка после :201; сообщения не пересекаются); ПОРЯДОК ИНТЕГРАЦИИ: T34 → T35 → T36. T35-QA параллельно не мешает (RED на baseline).

## Facts (baseline, file:line)

- S3(a) CONFIRMED: apipay.py:58 `self._secret = webhook_secret.encode()`; :158-162 verify_webhook guard только `if not signature` → hmac.new(b"", ...) детерминирован и атакуем. Единственный consumer routes_webhooks.py:41-44 (False → 401); это единственный неаутентифицированный write-эндпоинт — подпись И ЕСТЬ auth.
- S3(b) CONFIRMED: config.py validate_runtime :169-211 — ноль payments-проверок; поля уже существуют :133-138 (SecretStr("")). ВАЖНО: validate_runtime вызывается только в main.py:50 (lifespan API); worker.py:471-478 НЕ вызывает — поэтому defense-in-depth (C2/C4) обязателен.
- S3(c) CONFIRMED: provider.py:60-77 — :65 apipay → ApiPayProvider; ЛЮБОЕ другое значение → get_shared_fake :75-77 c fallback `or "test-secret"`. Опечатка = молчаливый FakeProvider в биллинге.
- FakeProvider не трогаем: get_provider никогда не даёт ему пустой секрет; production+fake+enabled отсечётся на старте; payments_enabled=False → всё free.
- Существующие тесты: test_payments_config.py (4, SecretStr masking), test_apipay_adapter.py (секреты не-пустые; конструкция C2 ничего не ломает), test_payment_webhook.py (13, paid_client → provider=fake, secret "whsec-test"; фикстуры гоняют реальный lifespan — provider=fake в enum, dev → RuntimeError не будет). Паттерны: Settings(**values).validate_runtime() (test_security.py:375-404); production base dict (test_metrics.py:250-259).

## Frozen contract

- C1 config.py validate_runtime (вставка сразу после docstring, до :171; WITHOUT новых полей): провайдер ∉ {fake, apipay} → RuntimeError "UNIMATCH_PAYMENTS_PROVIDER must be 'fake' or 'apipay'."; apipay: len(api_key secret) < 20 → "UNIMATCH_APIPAY_API_KEY is required (>=20 chars) when provider is apipay."; len(webhook_secret) < 32 → "UNIMATCH_APIPAY_WEBHOOK_SECRET is required (>=32 chars) when provider is apipay."; is_production and payments_enabled and provider=="fake" → "Production cannot take payments through the fake provider." Замороженные match-подстроки тестов: "UNIMATCH_PAYMENTS_PROVIDER", "UNIMATCH_APIPAY_API_KEY", "UNIMATCH_APIPAY_WEBHOOK_SECRET", "fake provider". Текст заморожен (перенос строк допустим). Без strip-семантики.
- C2 apipay.__init__ (первые statements): not api_key → ValueError "ApiPayProvider requires a non-empty api_key."; not webhook_secret → ValueError "ApiPayProvider requires a non-empty webhook_secret." (worker не вызывает validate_runtime — конструирование должно падать громко).
- C3 verify_webhook: после `if not signature` вставить `if not self._secret: return False` (401, не 500; пустой секрет никогда не доходит до hmac.new).
- C4 get_provider: перед fake-return `if settings.payments_provider != "fake": raise RuntimeError("UNIMATCH_PAYMENTS_PROVIDER must be 'fake' or 'apipay'.")` + комментарий (assert запрещён — исчезает под -O).
- RED: R1 exploit test (provider._secret=b"", подпись ключом b"" → verify False; baseline True) в test_apipay_adapter.py; R2/R3 пустые ключ/секрет при конструировании → ValueError; R4 provider="apipy" → validate_runtime match UNIMATCH_PAYMENTS_PROVIDER; R5 короткие ключ/секрет при apipay (параметризовано); R6 production+fake+enabled → match "fake provider". Green guards: валидный apipay prod-конфиг проходит; dev+fake+enabled проходит. Route-level 401-с-b""-ключом тест НЕ обязателен (после C1/C2 конфигурация не стартует; durable-форма — R1+R4/R5).
- allowed_paths: config.py ТОЛЬКО тело validate_runtime (без полей); apipay.py __init__+verify_webhook; provider.py get_provider. Тесты QA: test_payments_config.py (R4-R6+guards), test_apipay_adapter.py (R1-R3). Read-only регресс: test_payment_webhook.py, payment_service/reconcile/provider, paywall, billing. Не в scope: conftest.py, fake.py (решение: не нужен), routes_webhooks.py, service/entitlements/worker/schemas/frontend.
- Operational consequence (для release notes): API отказывается стартовать при typo-провайдере или apipay без секретов — это и есть фикс (fail-fast); worker защищён при первом использовании провайдера (C2/C4), отказ на старте worker'а — follow-up вне резервов.
