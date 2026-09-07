# Независимый аудит кода — 2026-09-06 (сессияGLM, HEAD 85352b5)

Статус: 3 из 5 областей аудированы параллельными ревью (pipeline/jobs; API/security/payments;
adapters/extraction). Области domain-логика и frontend/infra — НЕ завершены (агенты прерваны
лимитом параллельности). Находки ниже — гипотезы с высокой достоверностью: часть подтверждена
запуском тестового окружения, часть чтением кода. **Планировщик обязан проверить актуальность
каждой на текущем HEAD до исправления.** Нумерация — по порядку серьёзности внутри области.

## Соответствие карточкам очереди

| Находка | Task |
|---|---|
| Rate limiter берёт первый hop X-Forwarded-For; nginx добавляет клиентский заголовок → пер-IP лимиты обходятся | T02 |
| SMTP STARTTLS без проверки сертификата (reset-письмо перехватываем) | T01 |
| Recheck-цепочка умирает после первого срабатывания: off-by-one freshness + коллизия idempotency-ключа по дате | T13 |
| Повторный вход в funding_discovery дублирует evidence/claims (upsert только в verify) | T11/T12 |
| Robots.txt не перепроверяется на redirect-хопах; browser-тир уязвим к DNS-rebinding | T16 |
| Некорректный URL → ValueError убивает весь run (find_pii пропускает %40-энкодинг; кэш перехардкоживает utf-8) | T16 |
| Webhook ApiPay: пустой secret даёт hmac с пустым ключом (fail-open); typo в provider тихо включает FakeProvider | новый риск |
| Paywall-обход: `GET /api/profiles/{id}/export` и `set_decision`/`set_notes` возвращают полный payload без free_view (подтверждено запуском) | новый риск |
| `collect-documents` без guard'а на running job → две параллельные сборки по одному run | T12 |
| Cancel во время documents/queued оставляет run навсегда in-progress; startup-recovery перелицовывает отменённый run в RETRYABLE_FAILED | T10 |
| Reconcile платежей исчерпывает 30 попыток за ~4.6ч при TTL счёта 24ч → webhook становится SPOF | новый риск |
| `session.refresh(run)` в checkpoint стирает некоммиченные счётчики funding-стадии (~75% pages_checked теряется) | T10/T11 |
| is_official_domain подделывается query/path; post-redirect host не перепроверяется → VERIFIED_CURRENT с чужого домена | T16 |
| Манипуляция числами в extraction: `_MONEY` принимает любые 2+ цифры после $; FEE_WAIVER_AVAILABLE=True из отрицания | T18 |
| `needs_rehash` — мёртвый код; scrypt-апгрейд при логине не происходит | T01/T03 |

## Новые риски без карточки

По TEAM_RULES §«Общий ledger»: для нового риска заводится задача с теми же минимум четырьмя
ролями. Кандидаты: paywall-обход (2 эндпоинта), fail-open webhook secret, SMTP без верификации,
reconcile TTL. Диспетчер решает порядок после T01.
