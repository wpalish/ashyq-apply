# T35 A1 — Reviews (both on frozen candidate 8bf1f5d08fe3d389e4ab6bb9c2d485932fd12e4f)

## Reviewer (agent_96fe2888-9d75-4ae4-9ed5-9675f76883d8) — VERDICT: PASS

ACCEPTANCE_MAP все пункты PROVEN (mail.py:68-72 verifying context + правильный порядок opt-out (check_hostname ДО verify_mode — иначе CPython setter кидает ValueError); config.py:100 default True; production refusal :206-211 из lifespan main.py:50; rehash routes_auth.py:172-190 со strict < — downgrade-cost невозможен; ValueError-guard присваивание внутри try — нет частичного состояния).

COMMIT_PLACEMENT_RULING: корректен — SessionLocal autocommit=False; get_session без commit в конце → явный commit обязателен; commit фиксирует UPDATE хеша + INSERT AuditEvent атомарно (пара upgrade↔audit); create_session собственный prune+add+commit не ломается (паттерн зеркалит register); отказоустойчивость: commit rehash удался + create_session упал → 500, повторный логин видит needs_rehash False, дублей нет; до блока только SELECT'ы.

CONFIG_COORDINATION_NOTE: хунки T34 (верх validate_runtime) и T35 (поле :96 + guard :204-211) разнесены; встречная проверка: тесты каждой стороны остаются зелёными после другой (T35 clean-validate использует дефолтный fake из enum T34; T34 prod-guards не трогают smtp). Порядок T34→T35→T36 подтверждён.

Nonblocking followups: release note по self-hosted relay friction; конкурентный двойной логин — кандидат на интеграционный прогон; живой STARTTLS handshake — только double (offline). Untested → интегратору: full suite + cov 92 + PG.

## Security (agent_99feb3f2-a7ba-40af-879a-f03d66f260a8) — VERDICT: PASS

TLS_POST_FIX (вкл. STARTTLS-strip verdict по исходнику stdlib cpython-3.12.13): smtplib.starttls() :769-773 — ehlo_or_helo_if_needed() затем `if not self.has_extn("starttls"): raise SMTPNotSupportedError` — STARTTLS НИКОГДА не шлётся безусловно; MITM, подавляющий capability → SMTPNotSupportedError → send падает (без try/except) → plaintext-пути НЕТ ни при verify, ни в opt-out ветке. Подмена сертификата → SSLCertVerificationError в wrap_socket (CERT_REQUIRED + check_hostname + server_hostname). Дополнительно: send() до session.commit() в reset-flow — висячий валидный токен при сбое релея невозможен.

REHASH_POST_FIX: строго post-verification (нет орикла); CPU-burn ограничен (один доп. scrypt на legacy-аккаунт, только с правильным паролем); audit-строки соответствуют схеме, без PII; concurrent double-login ≤2 строк — принято контрактом.

SHORT_PASSWORD_RESIDUAL_RULING: тикет P2 (не блокирует) — legacy <12 пароли никогда не апгрейдятся и ветка молчит; обоснование: pre-patch было хуже; guard обязателен (иначе 500); оба пути ротации уже требуют min_length=12 → любой поворот пароля чинит; тикет: ops-скан по needs_rehash==True + уведомление/принуждение + наблюдаемость на except-ветке.

NEW_FINDINGS: T-f1 P2 legacy short-passwords (follow-up); T-f2 P3 (pre-existing) reset-request 500-vs-202 дифференциал при сбое релея — оставить fail-loud; T-f3 P3 release note (relay friction).

Required extra tests (QA, non-blocking): параллельный двойной логин на PG; real-socket SMTP double (self-signed sink → SSLCertVerificationError; no-STARTTLS sink → SMTPNotSupportedError).
