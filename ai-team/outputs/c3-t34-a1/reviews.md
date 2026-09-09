# T34 A1 — Reviews (both on frozen candidate b55a3b083558812079e7a2ff366cc9019e2d7393)

## Reviewer (agent_cc2f693c-925e-45fe-87c3-1241059d98c1) — VERDICT: PASS

SHA via ref + reflog + mtime-scope. ACCEPTANCE_MAP: exploit закрыт (C3 apipay.py:170-171 после signature-guard, до hmac.new :172; route 401 routes_webhooks.py:41-44); R1 exploit-shaped (форс _secret=b"" ПОСЛЕ валидной конструкции — устойчив к C2); секреты required (config.py:178-187, raw values, без strip — как заморожено); typo/prod-fake отказ старта (:176-177, :188-189, из main.py:50 lifespan); существующие тесты нетронуты (побайтово vs dc04fc3). Все 4 сообщения C1 байт-совпадают (двухлитеральный перенос >=32 разрешён).

ERROR_PRECEDENCE_RULING: принято — C1-top заморожен; только-auth конфиги по-прежнему видят UNIMATCH_AUTH_ENABLED (payments-блок no-op при дефолтах); ни один существующий тест не кодирует старый приоритет.

OPERATIONAL_NOTES: fail-fast на misconfigured payments — это фикс (release note); worker защищён при первом использовании (C4/C2), не при старте — follow-up тикет; остаток: worker-only + короткий-но-непустой секрет конструируется (длина — только C1) — замороженное следствие.

Nonblocking followups: worker boot-time validate_runtime тикет; C4-тест (единственное непокрытое suite-ом утверждение — QA проверил live); release notes по трём новым отказам старта.

## Security (agent_ab896b3f-1b46-4787-8dbf-6cb21ac263b1) — VERDICT: PASS

FORGERY_POST_FIX: обходов нет — verify_webhook ровно 3 выхода (пустая подпись / пустой секрет / реальный HMAC+compare_digest); _secret не может быть b"" после C2; длина-утечек нет (fixed 71-char hex).

PROVIDER_CONFUSION_POST_FIX: полный grep по репо (scripts/, backup_drill, migrations/env, canary, grant_subscription, handoff_check) — НИ одна сторонняя точка входа не обходит обе проверки; worker: RuntimeError/ValueError пробрасываются мимо except PaymentError → job fail → rollback → retry/dead-letter (fail-closed). Остаток: prod+fake+disabled — публичный "test-secret" фоллбэк, но payments_enabled=False ⇒ has_full_access True ⇒ грант ничего не даёт; включение payments поймается C1.

SECRET_HANDLING: чисто — get_secret_value() ровно 5 раз (2 len-проверки C1 + существующие); ни одно новое исключение не содержит секретного материала; синтетика в тестах.

WEBHOOK_PROTOCOL_NOTES (pre-existing): replay-окно без timestamp/nonce — LOW (apply_status ранний возврат + идемпотентный grant_case_access ⇒ replay даёт только дубль journal-строк); route exception → 500 (fail-closed, не оракул); payments-first приоритет маскирует вторую ошибку при triage — QoL тикет.

NEW_FINDINGS tickets: #1 LOW pre-existing webhook-replay hardening (timestamp в подписи); #2 INFO публичный test-secret фоллбэк в выключенных конфигах (опционально отказаться в production); #3 LOW residual короткие-непустые секреты в worker-only; #4 LOW ops: алертинг на повторяющиеся payment_reconcile фейлы с UNIMATCH_PAYMENTS_PROVIDER (30 попыток до dead-letter).

Required extra tests (QA, non-blocking): route-level 401 с b""-подписью; worker-процесс с typo-провайдером; replay одного валидного webhook дважды → один Entitlement.
