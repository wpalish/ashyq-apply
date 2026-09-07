# T01 / A1 — ashyq-security output (сохранено диспетчером дословно, оценка не менялась)

- ROLE: ashyq-security
- INVOCATION_REF: agent_29ea0b5a-9125-455d-9a02-1f398996c690 (real runtime agentId)
- VERDICT: PASS (только для SHA f7f14b28c43afe20df01ad38a26964c397f393fc)
- CHECKED_SHA: f7f14b28c43afe20df01ad38a26964c397f393fc (подтверждён через git metadata: logs/HEAD worktree verify, ref-файлы ai/c1/t01/verify и ai/c1/t01/qa)

## ATTACK_SURFACE_ANALYSIS (остаточных HTTP-путей получения token не найдено)
- reset-request все ветки возвращают ровно {"detail": ...} (routes_account.py:156,160,167,206); reset_link удалён; docstring правдив.
- token_urlsafe(32) попадает только в Message письма (169-194); confirm reset: 200 PrincipalView без токенов, Set-Cookie только на успехе, 400 generic.
- routes_auth.py:69-203 — токенов в телах нет; unknown-email smoothing dummy-hash сохранён.
- security.py:129-155 — session token только httpOnly cookie, sha256-хэш.
- Заголовки/main.py: security headers, X-Request-ID санитизирован, Retry-After без секретов; /metrics 404/bearer constant-time; OpenAPI только схема; audit-лог tenant-scoped с detail={}.
- Grep backend/app: raw token только routes_account.py:169 (→mail) и security.py:131 (→cookie).

## RecordingSender: get_sender возвращает только Smtp/Console; недостижим по HTTP; не пишет на диск/не логирует. ConsoleSender (pre-existing) пишет token в логи — в prod запрещён (config.py:195-199), в staging-console — зафиксирован как residual (P3).

## GUARDS_ASSESSMENT: не ослаблены. config.py:146-148 и guards 171-211 соответствуют baseline; middleware CSRF/limiter/trust_proxy без изменений (S02-дыра client_address — pre-existing); single-use/TTL/revoke-all/hash-only сохранены. Тесты: ни одного удалённого/смягчённого assert; добавлены более сильные.

## FINDINGS
1. [FIXED, было P0] baseline routes_account.py:203-204 — утечка устранена.
2. [INFO P3 pre-existing] ConsoleSender token в логах dev/staging-console.
3. [INFO P3 pre-existing] Timing-различие existing vs unknown; контракт сохранил семантику.
4. [INFO] Frontend dead branch client.ts:171, AuthGate.tsx:104-106.
5. [PROCESS] Ветка ai/c1/t01/dev = b5154ff ≠ замороженный candidate — PASS не переносится на новые коммиты.

## REQUIRED_EXTRA_TESTS (безопасные, для QA/очереди)
1. Матрица окружений × raw response.text + заголовки без 32+ символьного urlsafe-токена.
2. POST /password/reset с невалидным token → 400 без Set-Cookie.
3. Staging-проба с UNIMATCH_EMAIL_SENDER=console: token не в HTTP-ответе.
4. H01-проба (вне T01): два конкурентных POST /password/reset с одним token → ровно один 200; гонка видна в коде (217-256, нет атомарного UPDATE ... WHERE used_at IS NULL).
5. RED-доказательство S02: прямой порт + trust_proxy_headers=true, ротация XFF обходит per-address лимит.

## RESIDUAL_RISKS (вне T01)
- S02 подтверждён: docker-compose.yml:48 (staging), :65 (TRUST_PROXY_HEADERS true), :75-76 (0.0.0.0:8099) — spoofed XFF обходит per-address лимиты; per-email лимит держит. P1, не блокирует T01.
- H01: гонка выкупа token — pre-existing.
- Staging без SMTP → письма только в логи контейнера.
- Frontend gates и dead-code cleanup — вне T01.

## NEXT_ACTION
Принять candidate f7f14b28 для S01; контрольный git diff 85352b5..f7f14b28 одной командой (закрытие без-shell ограничения reviewer/security — диспетчер: выполнено при верификации заморозки, scope чист); судьба b5154ff (tree-идентичен, только message — нарушение процесса зафиксировано); очередь: S02, H01, frontend dead-code, HANDOFF/ledger.
