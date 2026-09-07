# Мастер-промпт: исправление ASHYQ Apply на уровне Tech Lead

> Передай coding-агенту этот документ целиком. При возможности приложи `LEAD_REVIEW_RU.md` и `review-evidence.zip`. Сам промпт содержит достаточную постановку, чтобы начать работу и без приложений.

---

## Роль и результат

Ты — Tech Lead и senior full-stack engineer проекта **ASHYQ Apply**. Работаешь с репозиторием:

https://github.com/wpalish/ashyq-apply

Твоя задача — **исправить перечисленные дефекты в коде, добавить защищающие их тесты и довести проект до проверяемого состояния для выпуска**. Не ограничивайся новым аудитом, рекомендациями, переименованием статусов или красивым планом.

Сохраняй существующую архитектуру и полезные функции. Нужны целевые исправления доменной логики, сохранности данных, безопасности, worker lifecycle, live extraction, UX и release-процесса. Переписывать приложение на другом стеке не требуется.

Работай небольшими проверяемыми изменениями. Завершением считается не «код написан» и не «build зелёный», а выполнение acceptance criteria с воспроизводимыми доказательствами.

Соблюдай инструкции окружения и репозитория. Не выполняй операции с внешними последствиями, для которых нет разрешения.

## Контекст аудита

Аудит завершён 6 сентября 2026 года на коммите:

`f018307f5d4186a61fd3d463066abf799936dfc8`

Во время аудита main обновился с `627d42d5fd42c1489dbeb7bd2dea43763914c7f5`; итоговый срез включает ranking v2 и новый shortlist UI.

На итоговом срезе локально проходили:

- 892 backend-теста на SQLite, coverage 92,56%;
- 141 frontend unit test;
- Ruff, format, mypy, TypeScript, ESLint и production build.

Несмотря на это, независимые проверки воспроизвели ошибки ниже. GitHub CI данного SHA упал на frontend E2E. Полные новые локальные PostgreSQL/E2E-прогоны не завершились в пределах внешнего тайм-аута; это не доказательство конкретной ошибки этих подсистем.

**Важно:** текущий HEAD может отличаться. Указанные файлы и строки — точки входа, а не инструкция механически применить старый diff. Сначала проверь актуальность каждого finding. Уже исправленный пункт не ломай заново: докажи исправление regression-тестом и отметь `already_fixed_verified`.

## Непереговорные правила

1. Не трогай чужие незакоммиченные изменения. Не используй `git reset --hard`, массовый `git clean` или удаление пользовательских данных для получения чистой сборки.
2. Не push, не deploy, не force-push и не запускай миграции на реальной базе без отдельного разрешения. Локальные ветки/коммиты создавай только в пределах разрешённого workflow.
3. Все проверки захвата аккаунта, SSRF, token races и ошибочных данных выполняй на изолированных синтетических fixtures. Не атакуй публичный сервис и не используй реальные профили абитуриентов.
4. Не печатай секреты, reset/session tokens и персональные данные в логи и отчёты. Тестовые email должны быть явно синтетическими; внешняя отправка писем в тестах запрещена.
5. Не ослабляй auth, CSRF, CORS, CSP, SSRF, стоимость production scrypt или tenant isolation ради зелёных тестов.
6. Не понижай действующий coverage gate. На аудитном срезе минимум составлял 92%. Не удаляй assertions и не добавляй skip/xfail только потому, что тест неудобен.
7. Не лечи race увеличением sleep/timeout. Для синхронизации используй явные состояния, транзакции, управляемые часы и детерминированные тесты.
8. Не отключай проблемные функции молча. Если функция должна fail closed по соображениям безопасности, это должно быть явным, протестированным и отражённым в продуктовой политике.
9. Не добавляй Redis, брокер, новый framework, LLM-провайдера или микросервисы без доказанной необходимости. Используй существующий стек, если он решает задачу.
10. Не выдавай неизвестную сумму за ноль, опубликованную возможность — за лично полученную стипендию, отсутствие claims — за высокое качество извлечения.
11. Не объявляй исправление подтверждённым по одному code review. Нужен тест безопасного поведения. Диагностический скрипт, который просто печатает неправильный результат и завершается с exit 0, ещё не regression-test.
12. Если проверка недоступна, честно укажи `blocked` и точную причину. Не подменяй непроверенное словом `passed`.

---

## Этап 0. Зафиксируй состояние и план выполнения

Сначала:

1. Проверь `git status`, HEAD, текущие инструкции репозитория, README, SECURITY, CI, requirements, package scripts, миграции и deployment configuration.
2. Сопоставь текущий код с findings ниже. Прочитай нужные соседние функции и существующие тесты; не сканируй бесконечно весь проект вместо исправления подтверждённых блокеров.
3. Проверь совместимость окружения с CI: Python 3.12 и Node 22, если актуальная конфигурация не требует иного.
4. Запусти разумный baseline. Не запускай PostgreSQL matrix и Chromium E2E параллельно на машине с ограниченной памятью. Default E2E и auth E2E запускай последовательно: они используют общие порты.
5. Создай или обнови единый execution ledger, например `docs/FIX_EXECUTION_PLAN.md`.

Для каждого пункта сохраняй:

| Поле | Что записать |
|---|---|
| ID | Стабильный идентификатор из этого промпта |
| Актуальность | reproduced / already_fixed_verified / not_reproduced / needs_investigation |
| Root cause | Конкретная нарушенная логика или граница |
| Изменения | Файлы, модель данных, API, миграция, если нужны |
| Regression test | Имя теста и проверяемый инвариант |
| Результат | Точная команда, exit status, итог, SHA |
| Остаточный риск | Что не проверено и почему |
| Статус | planned / in_progress / fixed_verified / blocked |

`Not reproduced` не означает автоматически `fixed`. Для спорного finding сохрани исходный сценарий, текущий результат и объяснение отличия.

После краткого плана **переходи к реализации**, не останавливайся только на документе. Обычные локальные инженерные решения принимай самостоятельно; спрашивай только при существенной неоднозначности продуктовой политики или перед необратимыми/внешними действиями.

---

# Блок A. Безопасность и границы deployment

## S01 — reset token выдаётся неаутентифицированному клиенту в non-production

**Приоритет:** P0, если staging доступен извне с настоящими данными.

**Точки входа:**

- `backend/app/api/routes_account.py`, reset-request, примерно строки 137–205;
- `docker-compose.yml`, environment/ports, примерно строки 44–76;
- mail sender и соответствующие auth tests.

**Воспроизведено:** synthetic stranger запросил reset для synthetic victim, получил token из API response, сменил пароль и вошёл владельцем. В production этот token в response не возвращался: не называй это доказанным production takeover.

**Исправление:**

- Убери reset link/token из внешних API responses во всех окружениях.
- Для тестов используй injected fake mail sender или изолированный mail sink, не debug-поле API.
- Сохрани нейтральное поведение для существующего/несуществующего email; проверь ветки ответов, не создают ли они тривиальную утечку существования аккаунта.
- Сохрани TTL, single-use и отзыв сессий после reset.
- Раздели безопасную локальную конфигурацию и публичный deployment. Локальные debug-порты bind к loopback; публичный доступ — только через предусмотренную защищённую границу.
- Не меняй production-guards на более слабые ради convenience staging.

**Acceptance:**

- Ни production, ни staging, ни development HTTP response не содержит reset/session token.
- Посторонний клиент без доступа к mailbox не может завершить reset.
- Владелец с тестовым письмом может завершить reset ровно один раз.
- Истёкший/повторно использованный token отклоняется.
- После reset прежние сессии отозваны.
- Контракт существующего и отсутствующего email проверен тестами.

## S02 — spoofed X-Forwarded-For обходит rate limit

**Приоритет:** P1.

**Точки входа:** `backend/app/main.py:139–152`, `frontend/nginx.conf:29–35`, Compose proxy trust и API ports.

**Воспроизведено:** лимит 2, одинаковый реальный client/proxy suffix, четыре разных пользовательских prefixes → четыре запроса без 429.

**Исправление:**

- Определи доверенную границу и конкретные trusted proxies/CIDR/hops.
- Не доверяй левому элементу XFF только из-за boolean flag.
- На первой доверенной границе перезаписывай/санитизируй недоверенные forwarded headers; при нескольких proxies разбирай цепочку согласно явно заданной модели доверия.
- Запрос от недоверенного socket peer не должен получать доверие к forwarded headers.
- Не публикуй API напрямую, если архитектура предполагает доступ только через nginx.
- Сохрани корректную работу нескольких настоящих клиентов за доверенным proxy: нельзя превратить лимит одного пользователя в лимит всего сервиса.

**Acceptance:**

- Перебор поддельных prefixes не обходит лимит.
- Недоверенный прямой клиент не может выбрать себе identity через XFF.
- Два настоящих клиента за доверенным proxy учитываются раздельно.
- IPv4/IPv6 и malformed headers обработаны предсказуемо.
- Проверены лимиты login/reset и дорогих research starts.
- Добавлен deployment-level тест или smoke, а не только unit-тест helper.

## H01 — атомарность reset и масштабирование rate limiter

Это дополнительные проверки hardening, а не уже доказанные production exploits.

- Проверь конкурентное потребление одного reset token двумя независимыми DB-сессиями. Выполнение reset, пометка token использованным и необходимые изменения сессий должны быть атомарными. Используй conditional UPDATE/lock с проверкой числа изменённых строк либо эквивалентный корректный механизм.
- Если заявлена multi-replica поддержка API, общий лимит должен жить на общей доверенной границе или в shared store. Не добавляй Redis автоматически: существующий PostgreSQL/edge может быть достаточен.
- Если продукт пока официально single-replica, сделай это явным проверяемым deployment constraint; не обещай распределённые квоты, которых нет.

**Acceptance:** из двух одновременных попыток reset успешна ровно одна; rate-limit guarantees соответствуют реальной topology.

---

# Блок B. Финансовая модель и ranking

До изменения UI сформулируй небольшую общую доменную модель для:

- complete / partial / unknown cost;
- applicable / unavailable / unknown scholarship;
- confirmed compatible / incompatible / unknown stacking;
- affordable / unaffordable / unknown affordability.

Можно использовать существующие типы, расширив их совместимо. Не создавай отдельную противоречивую логику для каждого экрана. Сначала установи инварианты, затем используй их в расчётах, ranking, API, exports и human explanations.

## F01 — неполная сумма расходов выдаётся за полную

**Приоритет:** P1. **Точка входа:** `backend/app/domain/costs.py:25–76, 247–267`.

**Сценарий:** tuition 10 000 USD, tuition award 10 000 USD, living costs отсутствуют → `computable=true`, `gap=0`, `warnings=[]`.

**Исправление:**

- Раздели опубликованный полный cost of attendance и сумму лишь известных категорий.
- Определи правила обязательных категорий и источники подтверждения полноты. Не считай расходы отсутствующими только потому, что crawler их не извлёк.
- Явно известный нулевой расход допустим; отсутствующий расход не равен нулю.
- Частичную сумму можно показывать как known subtotal/lower bound с missing categories, но не как полный annual gap.
- Отобрази uncertainty в API, ranking, UI и экспортах. Не исправляй только подпись, оставив ошибочную сумму в сортировке.

**Acceptance:** неизвестные жильё/питание не создают вывод «всё покрыто»; подтверждённый полный total по-прежнему корректно рассчитывается; unknown и zero различимы во всех потребителях.

## F02 — недоступная стипендия уменьшает расходы

**Приоритет:** P1. **Точки входа:** `funding.py:239–309`, `costs.py:134–158`.

**Сценарий:** deadline passed, current intake unavailable, application window closed; award всё равно получает `CONFIRMED_OPPORTUNITY` и уменьшает gap.

**Исправление:**

- Централизуй applicability по applicant, degree/program/cohort, intake, academic year, deadline и application window.
- Используй одно решение applicability в funding fit, gap, ranking и объяснениях.
- Не засчитывай closed/expired/unavailable award как доступное финансирование. Не удаляй историческую информацию: сохраняй её с причиной исключения из расчёта.
- Не смешивай опубликованную возможность податься и индивидуально присуждённую помощь. Если существующая модель поддерживает полученный award, обрабатывай его отдельно и на основании явного состояния, а не догадки.
- Зафиксируй UTC/timezone и date-boundary semantics; используй управляемые часы в тестах.

**Acceptance:** проверены прошлый/сегодняшний/будущий deadline, разные intake/year, закрытое окно, unknown availability. Никакая недоступная award не улучшает текущую доступность обучения.

## F03 — неподтверждённое stacking и совместимость сумм

**Приоритет:** P1. **Точка входа:** `costs.py:173–187`.

**Сценарий:** primary `unknown`, secondary `yes` → дополнительные 5 000 USD засчитаны, gap стал нулём.

**Исправление:**

- Требуй явного подтверждения совместимости обеих сторон.
- Проверяй academic year и применимость не только primary, но и каждой secondary award.
- Учитывай ограничения категорий покрытия; не финансируй одну и ту же стоимость дважды без подтверждённого правила.
- Не считай excess aid автоматически выплачиваемым доходом.

**Acceptance:** матрица yes/no/unknown с обеих сторон; несовместимые годы; overlapping coverage; превышение подтверждённых расходов. Unknown stacking никогда не уменьшает подтверждённый gap.

## F04 — сравнение денежных сумм без валюты

**Приоритет:** P2. **Точка входа:** `funding.py:207–224`.

**Сценарий:** 1 000 000 JPY против 40 000 USD классифицированы как примерно 100%, хотя встроенная конвертация давала около 16,45%.

**Исправление:**

- Не теряй currency/period на границе `_coverage_share` и вызывающих функций.
- До арифметики приводите сравниваемые суммы к одной валюте и совместимому периоду.
- Зафиксируй точность, округление, метод/дату FX и поведение unsupported currency.
- Не вводи незаметную несовместимость JSON number/string при смене денежного типа.

**Acceptance:** одинаковые, разные и неподдерживаемые валюты; absolute/percentage awards; разные периоды; нулевые знаменатели. Classification и отображаемые деньги согласованы.

## F05 — bucket противоречит affordability

**Приоритет:** P1. **Точки входа:** `ranking_v2.py:309–346, 468–469`.

**Воспроизведённые случаи при остальных положительных факторах:**

- неизвестный gap → `WELL_PLACED` с утверждением «в пределах бюджета»;
- budget=0, gap=15 000 USD → тот же bucket и объяснение.

**Исправление:**

- Не используй truthiness чисел для различения known/unknown.
- budget=0 и positive gap → недоступно по бюджету.
- budget=0 и подтверждённый complete gap=0 → доступность возможна.
- unknown gap/ceiling → неизвестная доступность; она не поддерживает положительное обещание о бюджете.
- Bucket и bucket_reason формируй из того же доменного решения, что affordability axis.
- Не сериализуй Infinity/NaN как обходной способ обработки нулевого budget.
- Сохрани смысл unknown vs not_applicable; не повышай completeness, исключая неизвестные обязательные поля из знаменателя.

**Acceptance:** таблица budget=None/0/positive × gap=None/0/positive; boundaries равенства бюджету и порогам; hard exclusions; нулевые веса; ranking v1 compatibility, если этот режим остаётся поддержанным.

### Общие финансовые инварианты

Добавь parameterized/property-style tests там, где это полезно:

- Потеря подтверждённых финансовых данных не улучшает утверждение о доступности.
- Истечение срока/потеря applicability award не увеличивает засчитанную помощь.
- Добавление неподтверждённой award не уменьшает подтверждённые расходы.
- Эквивалентные суммы после FX не меняют смысл classification.
- UI, API, ranking и export не говорят противоположное об одном result.
- Валидный неизвестный результат лучше выдуманного точного результата.

Не превращай эти требования в запрет показывать сценарные оценки. Если продукт показывает потенциальную стоимость после конкурентной стипендии, сценарность и её условия должны быть явными и не смешанными с гарантированными средствами.

---

# Блок C. Черновики и frontend state

**Основная точка входа:** `frontend/src/lib/store.tsx`, примерно строки 207–218 и 274–312.

## FE01 — новый кейс теряет draft после reload

Восстановление draft сейчас зависит от серверного profileId. Новый локальный кейс должен иметь самостоятельную идентичность и восстанавливаться без существующей записи на сервере.

## FE02 — autosave удаляет draft до окончания hydration

Debounce 600 мс может очистить существующий draft раньше, чем загрузится профиль. Управление initial loading не должно зависеть от того, успел ли API ответить быстрее таймера.

## FE03 — draft одного кейса накладывается на другой

Глобальный draft и отдельный active pointer допускают несовместимую пару из двух вкладок. Это frontend state bug, не доказанный backend tenant bypass.

**Общее исправление:**

- Раздели initial hydration, editing, saving, saved и failed состояния.
- Autosave не имеет права удалять/перезаписывать данные до завершения нужной hydration.
- Namespace draft по user/org/case; для нового кейса используй локальный draft ID.
- Храни schema/version, case identity, baseline revision и timestamp там, где это нужно для безопасного восстановления.
- Проверяй восстановленный payload, а не только делай `JSON.parse` и type cast.
- Защити case switch и refresh от устаревших ответов: request generation/AbortController или эквивалент.
- Не трактуй transient network error как доказанное удаление профиля. 404, 401 и временный сбой — разные состояния.
- Определи политику draft при logout/смене организации, чтобы данные одного пользователя не показывались другому. Не уничтожай несохранённую работу неожиданно.
- Сделай эффекты корректными при remount и React StrictMode.

**Обязательные tests:**

1. Новый кейс → edit → debounce → reload → edits восстановлены.
2. Saved case с dirty draft → API response задержан дольше debounce → edits сохранены.
3. Active B + draft A → данные A не накладываются на B.
4. Switch A→B, поздний ответ A → остаётся B.
5. Две реальные browser pages одного context меняют разные кейсы → состояния не смешиваются.
6. Corrupt/старый draft → контролируемое восстановление, без 500/падения UI и без скрытой записи demo поверх профиля.
7. Save failure → draft остаётся и UI показывает ошибку, а не `Saved`.
8. Logout/другой user/org → изоляция соблюдается.

Не переносить весь store на новый state framework ради этих исправлений. Раздели обязанности ровно настолько, насколько необходимо для предсказуемого lifecycle и тестируемости.

---

# Блок D. Run/job lifecycle и документы

## J03 — retry скрывает checklist и блокирует повторную сборку

**Приоритет:** P1. **Точки входа:** `runner.py:959–975`, `routes_research.py:432–486`, result models и JobStore.

**Сценарий:** research → approve → collect → retry research → collect again. Checklist исчезает из payload, отдельная DB-копия остаётся; новая documents job не создаётся из-за старого ключа.

**Исправление:**

- Определи canonical representation checklist и правила обновления derived payload/columns.
- Введи или используй revision/generation для research result и document collection.
- Повтор той же команды должен возвращать ту же задачу; новая допустимая генерация должна создавать новую работу.
- Для succeeded/dead/cancelled job должно быть определённое поведение retry, а не вечный запрет по старому ключу.
- При изменении evidence либо сохраняй совместимый checklist, либо явно помечай его устаревшим и пересобирай. Пользователь должен понимать состояние.
- Не теряй approvals, rejection reasons, notes и пользовательский прогресс документов.

**Acceptance:** весь сценарий проходит через API и worker; checklist видим и соответствует версии result; нет двойного запуска одного поколения; новая генерация не блокируется прошлой.

## J02 — stale worker записывает terminal state

**Приоритет:** P1. **Точки входа:** `runner.py:134–168, 273–280`, `jobs/store.py`, `jobs/worker.py`.

**Сценарий:** job принадлежит new-worker; old-worker получает LeaseLost, но пишет run.stage=failed.

**Исправление:**

- Потеря lease — отдельный control-flow outcome, не обычная ошибка run.
- Stale worker делает rollback и прекращает бизнес-записи, включая error/cancel handlers.
- Обеспечь fencing на записи progress, stage, counters, claims, results и terminal state по актуальному owner/attempt/generation.
- Проверка «я владелец» и последующая запись не должны иметь незащищённое окно race.
- Избегай проверки через устаревший ORM identity map; учитывай autoflush и транзакционные границы.
- Проверь claim/complete/fail/reap/cancel как согласованную state machine.

**Acceptance:** PostgreSQL-тесты с двумя независимыми сессиями подтверждают, что stale worker не может испортить результат нового. Покрой истечение lease, heartbeat race, cancellation, завершение и takeover. SQLite-only проверки недостаточны для конкурентных гарантий.

## J01 — recheck выполняется впустую и не перепланируется

**Приоритет:** P1. **Точки входа:** `domain/freshness.py:27–50`, `jobs/worker.py:174–190`.

**Сценарий:** TTL=30 дней, age=30 дней + 2 минуты; stale=false, перечитано 0 claims, новых jobs 0, next_recheck в прошлом.

**Исправление:**

- Одна UTC timestamp-семантика наступления expiry для планирования и проверки.
- Следующая дата должна продвигаться, а не повторно ссылаться на уже выполненный idempotency key.
- Раздели идемпотентность команды и поколение периодической задачи.
- Для failed fetch и no-op recheck явно задай retry/backoff/next due policy.

**Acceptance:** tests на TTL−epsilon, TTL, TTL+epsilon, naive/aware DB timestamps, повтор scheduler, error/retry и manual recheck. Нет бессрочно просроченной next_recheck без объяснённого terminal state или будущей работы.

## A01 — воспроизводимость run и согласованность состояния

- Сохраняй immutable snapshot/version профиля на research run либо эквивалентную достоверную привязку входных данных.
- Раздели получение нового evidence и rerank существующего evidence.
- Централизуй запись payload и поисковых/сортировочных колонок. При необходимости добавь invariant checks и безопасную миграцию существующих строк.
- Проверь graceful shutdown/старты wrapper и worker. SIGTERM/SIGINT или завершение тестового сервера не должны оставлять собственные orphan workers. Не используй kill-all, затрагивающий чужие процессы.

Не делай большой косметический refactor одновременно с починкой state machine. Сначала тесты и минимальная корректная транзакционная модель, затем небольшое выделение ответственности.

---

# Блок E. API contracts, rerank и экспорт

## R01 — rerank сохраняет невалидный профиль

**Приоритет:** P2. **Точки входа:** `api/routes_results.py:417–479`, `schemas/profile.py:258–271`.

**Сценарий:** priorities с duplicate и persist=true принимаются с 200; последующие GET profile и rerank дают 500.

**Исправление:**

- Используй общую constrained schema priorities, включая допустимые значения, max length и уникальность.
- Валидируй весь merged ApplicantProfileIn до записи; assignment в существующую Pydantic model не считать полноценной валидацией.
- Invalid input → 422 без частичной записи результатов или профиля.
- persist=false не меняет сохранённый профиль; persist=true сохраняет только валидную согласованную версию.
- Определи и проверь допустимость rerank для текущих run states и конкурирующего worker.

**Смежные контрактные проверки, не объявляемые заранее доказанными багами:**

- UI передаёт все параметры, которые обещает пересчитать.
- Переключение advanced weights → priorities и обратно действительно работает.
- Изменения budget/country/climate, если входят в контракт rerank, отражаются во всех зависимых оценках и объяснениях без нового crawl.
- UI не показывает `Reordered`/`Saved`, если API завершился ошибкой.

**Acceptance:** duplicate/too-long/unknown priorities отклоняются; профиль после любого успешного save читается; failed rerank не оставляет частичные изменения; repeated valid rerank детерминирован.

## S03 — formula injection в XLSX/CSV

**Приоритет:** P2. **Точка входа:** `export/tabular.py:152, 176–183, 234–236`.

**Сценарий:** user note `=1+1` записывается в XLSX как formula cell (`data_type='f'`). CSV также сохраняет опасный prefix.

**Исправление:**

- Введи общую безопасную обработку недоверенных текстовых полей: notes, excerpts, names, questions и другие строки из внешних источников.
- XLSX должен явно хранить такие значения текстом; CSV требует отдельного корректного escaping.
- Учти `=`, `+`, `-`, `@` и ведущие управляющие символы согласно выбранной spreadsheet threat model.
- Не превращай легитимные числовые financial columns в строки и не ломай Unicode/переносы строк.

**Acceptance:** load_workbook подтверждает отсутствие формул в недоверенных text cells; CSV tests проверяют escaping и round-trip; обычные числа, даты, кириллица и источники не повреждены. Не заявляй RCE лишь на основании формульной ячейки.

---

# Блок F. Network/PDF hardening и live extraction

## H02 — browser/network boundary

Это зона дополнительной проверки, а не доказанный production SSRF.

- Проверь browser fallback: Chromium выполняет собственное соединение после URL/DNS validation. Наличие pinning у HTTP client не переносится автоматически на него.
- Определи реальную egress boundary для fetch/browser, включая private, loopback, link-local, metadata, IPv6 и redirects.
- Политику инфраструктуры проверяй в изолированном окружении. Не изменяй firewall общего host или production без разрешения.
- Внутренние разрешённые соединения к PostgreSQL/API не должны ломаться из-за неправильно применённой egress policy.
- При невозможности безопасного browser fallback поведение должно быть явно fail closed с диагностикой, а не молчаливым обходом защиты.
- Проверь HTTP 403/404/429, redirects, content type, response limits и cleanup streams. Ошибочная страница не должна становиться VERIFIED claim.

**Acceptance:** controlled negative tests не достигают запрещённых адресов; разрешённые официальные страницы читаются; ограничения и необходимость инфраструктурной защиты документированы без ложных обещаний.

## H03 — PDF resource limits

- Ограничение размера upload не ограничивает decompression/parsing CPU и RAM.
- Выполняй тяжёлый разбор вне async request loop с реально применимыми timeout/resource limits. Один timeout ожидания thread не доказывает остановку самого parser.
- Гарантируй cleanup temporary files/processes и понятный ответ при отказе.
- Проверь соответствие privacy wording фактическому spooling/storage. Не обещай «никогда не касается диска», если используемые механизмы этого не гарантируют.
- Используй безопасно ограниченные синтетические damaged/oversized fixtures, не реальные чувствительные transcripts.

**Acceptance:** невалидный/тяжёлый PDF не блокирует API неограниченно, не оставляет parser-процессы и не вызывает неограниченный расход ресурсов.

## L01 — live URL discovery не даёт проверяемых claims

**Наблюдение аудита:** один canary для Nazarbayev University: 35 успешных страниц, programme/scholarship pages найдены, 0 claims, completeness 0%. Это не доказательство провала всех университетов.

**Работа:**

1. Воспроизведи pipeline на ограниченной выборке, соблюдая robots, rate limits и правила источников.
2. Раздели discovery failure, wrong page classification, rendering problem, extraction failure и unsupported data. Добавь структурированные diagnostics.
3. Проверь правильность degree/program/intake/campus/cohort. News с упоминанием programme — не programme page; требования другого уровня обучения не относятся автоматически к текущему.
4. Создай curated ground-truth набор минимум для 10 университетов или явно согласуй меньший pilot scope с объективной причиной. Используй несколько типовых синтетических профилей.
5. Для каждого включи вручную проверенные критичные поля: programme, requirements, deadline, tuition, living costs, awards и applicability. Сохраняй источники/дату и минимальные достаточные evidence fixtures.
6. Исправь общие механизмы discovery/extraction; не добавляй hardcoded ответы только для прохождения NU canary.
7. В tests добавь negation/context cases: отсутствие portfolio requirement не превращается в требование portfolio; старый intake и другой cohort не становятся актуальными условиями.
8. Unknown остаётся unknown. Не добавляй LLM только ради ненулевого числа claims и не заполняй пустоты правдоподобными догадками.

**Метрики, отдельно:**

- discovery recall относительно размеченного набора;
- claim precision и корректность source/context;
- coverage критичных полей;
- доля результатов, позволяющих безопасный следующий шаг;
- freshness/recheck correctness;
- latency/error classes и ограничения доступа.

Укажи числитель/знаменатель и unsupported/blocked cases. Нельзя объявить успешное качество по «0 false positives» при 0 extracted claims.

**Acceptance:** offline golden tests воспроизводимы, ограниченный live smoke даёт измеренный отчёт, поддерживаемый scope честно отражён в UI/docs. Целевые пороги качества зафиксированы до оценки результата и не понижаются задним числом ради зелёного gate. Если live-доступ недоступен, offline proof и live-blocker должны быть разделены; release live-функции не объявлять проверенным.

---

# Блок G. UX, сопровождение и release gates

## U01 — тяжёлый initial profile flow

- Сохрани полноту анкеты, но примени progressive disclosure: обязательное для первого полезного результата отдельно от необязательного/расширенного.
- Не делай обязательными данные, которые не нужны выбранному сценарию.
- Изменение структуры формы не должно терять drafts, ломать accessibility или скрывать важные финансовые предупреждения.
- Если выбор между интерфейсом консультанта и абитуриента требует продуктового решения, сформулируй его явно. Не выдумывай подтверждённые conversion metrics.

## U02 — narrow-screen money rendering

- Проверь реальные значения, длинные валюты/учебные годы и предупреждения на 320/360/768 px и desktop.
- Сумма, валюта и период должны читаться без обрезания существенной информации.
- Не маскируй overflow глобальным `overflow-x:hidden`, если данные становятся недоступны.
- Сохрани keyboard navigation, accessible names, focus и контраст обеих тем.

## Q01 — тесты защищают не те инварианты

- Все подтверждённые F/FE/J/S/R scenarios преврати в permanent tests безопасного поведения.
- Добавь cross-module tests согласованности денег, bucket, текста, API и export.
- Важные конкурентные сценарии тестируй на PostgreSQL, а не только SQLite.
- Runtime errors приложения отличай от падений браузера/инфраструктуры. Сохраняй доказательства root cause.

## Q02 — хрупкий E2E и каскадные пропуски

- Устрани неоднозначные locators вроде `getByText('Saved')`, используя role/name/scope и явные test IDs там, где нужно.
- Уменьши ненужные зависимости serial tests: один failure не должен лишать проверки всего workflow.
- Сохрани интегральный journey, но независимые сценарии делай независимыми.
- Screenshots/traces/video отправляй в test artifacts, а не перезаписывай tracked `docs/screenshots` при каждом обычном запуске.
- Не лечи приложение увеличением retries и не вычёркивай mobile coverage.
- Default E2E и auth E2E запускай последовательно; управляй собственными серверами и cleanup.

## D01 — документация противоречит реализации

- Обнови SECURITY, README/current-state, configuration examples и release checklist по фактическому коду.
- Убери устаревшее утверждение об отсутствии password reset.
- Раздели implemented, verified, known limitation и roadmap.
- Опиши угрозы staging, proxy topology, draft lifecycle, data retention, supported live scope, scheduling/retry guarantees и rollback.
- Не заявляй отсутствие хранения на диске, полную SSRF-защиту или production readiness без подтверждения соответствующего уровня.

## O01 — эксплуатация должна быть проверена, а не только описана

- Добавь/исполни runtime smoke PostgreSQL + migrations + API + worker + frontend/proxy в изолированном Compose project/volumes.
- Проверь register/login/reset через test mailbox, сохранение профиля, research, approval, documents, export и удаление synthetic data.
- Проверь restart worker/API во время research и возобновление без потери/дублирования результатов.
- Выполни backup/restore drill только на scratch DB, не на исходной рабочей базе.
- Миграции должны работать на пустой БД и при upgrade существующего среза. Старые result payloads не должны падать при чтении или получать выдуманную completeness.
- Добавь/проверь наблюдаемость: dead jobs, overdue rechecks, lease loss, extraction yield, error classes, API errors. Логи не должны содержать профиль/секреты.
- Зафиксируй rollback plan и operational constraints. Не добавляй инфраструктурную сложность без необходимости.

Если Docker недоступен локально, добавь соответствующий CI runtime gate и оставь локальную проверку `blocked`. Успешный `docker compose build` не равен проверенному runtime.

## P01 — не расширяй scope раньше исправления core

Не добавляй новые community/feed/чат/LLM-функции. Существующие не удаляй без согласования. Сначала должен стабильно работать путь:

**profile → evidence → корректный shortlist → decision → documents → export → recheck/recovery.**

---

# Порядок небольших PR / change sets

Уточни зависимости после triage, но базовый порядок такой:

1. **Security boundary:** S01, S02, атомарность reset и безопасные test/deployment settings.
2. **Financial correctness:** F01–F05, общий доменный контракт, согласованные API/UI/export consumers.
3. **Draft integrity:** FE01–FE03 и lifecycle/regression tests.
4. **Worker/recovery:** J01–J03, run snapshot/generation, fencing, canonical state и migrations.
5. **API/export hardening:** R01, S03 и смежные rerank contracts.
6. **Live/network/PDF:** H02–H03, L01, diagnostics и goldens.
7. **Release polish:** U01–U02, Q01–Q02, D01, O01 и итоговый gate.

Если один блок требует общей миграции или контракта раньше — выдели подготовительный совместимый change set. Не дублируй конкурирующие модели состояния в разных PR.

Для каждого change set:

- сначала воспроизводящий тест, если это баг;
- минимальное исправление root cause;
- targeted tests;
- cross-module regression, если затронут контракт;
- краткое объяснение diff и migration/rollback impact;
- обновление execution ledger.

Не смешивай в один большой diff багфиксы, массовое форматирование, переименование файлов и redesign всего UI.

---

# Проверки и команды

Сверь команды с актуальными scripts/config. Устанавливай зависимости из lock/requirements, не обновляй их массово без отдельной причины.

Типовой backend gate, из `backend/`:

```bash
.venv/bin/ruff check app tests scripts
.venv/bin/ruff format --check app tests scripts
.venv/bin/mypy app tests scripts/backup_drill.py

# Только отдельная тестовая SQLite DB по абсолютному пути:
UNIMATCH_DATABASE_URL=sqlite:////ABSOLUTE/TEST/PATH/audit.db \
  .venv/bin/pytest --cov=app --cov-fail-under=92

# Полный PostgreSQL-primary matrix — последовательно с тяжёлыми E2E:
.venv/bin/python scripts/pg.py .venv/bin/pytest

.venv/bin/pip-audit -r requirements.txt
```

`/ABSOLUTE/TEST/PATH/audit.db` — placeholder: создай выделенный scratch path. Не используй существующую пользовательскую БД. Если актуальный coverage gate выше 92%, сохраняй более высокий порог.

Типовой frontend gate, из `frontend/`:

```bash
npm ci
npm run typecheck
npm run lint
npm test -- --run
npm run build
npm audit --audit-level=high

# Не одновременно: общие порты и ограниченные ресурсы.
npm run e2e -- --workers=1
npm run e2e:auth -- --workers=1
```

Дополнительно:

- fresh-schema и upgrade migration tests;
- PostgreSQL concurrency tests;
- controlled security negative tests;
- isolated deployment/runtime smoke;
- offline golden extraction tests;
- bounded live smoke, если доступ разрешён;
- backup/restore drill в scratch environment.

Для длительных сервисов используй штатный менеджер процессов окружения и гарантированный cleanup. Не оставляй orphan processes после прерванного теста. Фиксируй версию runtime и SHA рядом с результатами.

---

# Definition of Done

Работа не считается полностью завершённой, пока не выполнено следующее:

- [ ] У каждого finding есть проверенная актуальность и итоговый статус.
- [ ] S01/S02 устранены; безопасность не ослаблена в других местах.
- [ ] F01–F05 защищены tests; unknown/zero, currency/year/applicability/stacking согласованы.
- [ ] FE01–FE03 проходят, включая slow hydration и реальные разные browser tabs.
- [ ] J01–J03 проходят; stale worker не пишет, новая генерация не блокируется старой задачей, recheck продвигается.
- [ ] Успешный rerank не может сохранить нечитаемый профиль.
- [ ] Недоверенный текст не становится spreadsheet formulas.
- [ ] Дополнительные H-проверки проведены либо перечислены как конкретные блокеры, без выдуманных exploits.
- [ ] Существующие профили/results и legacy payloads читаются после upgrade.
- [ ] Auth, tenant scoping, decisions, notes и document progress не регрессировали.
- [ ] Полные SQLite/PostgreSQL/frontend/E2E/auth suites выполнены на итоговом SHA; результаты не смешаны со старым срезом.
- [ ] Coverage/линтеры/типизация/аудит зависимостей соответствуют текущим gates.
- [ ] Live quality измерено на объявленном scope; неизвестные поля не сфабрикованы.
- [ ] Runtime/recovery/restore проверены либо release явно заблокирован отсутствующей проверкой.
- [ ] Документация соответствует фактической реализации и результатам.
- [ ] В git diff нет secrets, test DB, traces или случайно изменённых screenshots.

Если что-то `blocked`, можно завершить текущую итерацию отчётом о блокере, но **нельзя объявлять весь проект production-ready**.

---

# Формат итогового ответа

Дай не рекламное описание, а инженерный отчёт:

1. **Итоговый SHA и границы работы.**
2. **Таблица всех ID:** reproduced/already fixed, что изменено, regression-test, результат, остаточный риск.
3. **Изменения контрактов и данных:** новые поля, migrations, совместимость старых записей, rollback.
4. **Проверки:** точные команды, pass/fail/skipped/not-run, coverage; отдельно локальные результаты и CI. Не объединяй разные SHA в один «зелёный» результат.
5. **Live benchmark:** scope, ground truth, числитель/знаменатель метрик, неподдержанные/недоступные источники.
6. **Оставшиеся blockers:** причина, воздействие и следующий конкретный шаг. Не прячь их в общей фразе «нужен дополнительный hardening».
7. **Release verdict:** `NO-GO`, `PILOT-ONLY` или `READY FOR DEFINED SCOPE` с обоснованием. Готовность к ограниченному scope не называть универсальной гарантией.

**Начни с текущего git state, краткого плана и воспроизведения S01/F01. Затем реализуй исправления по этапам, пока не выполнены доступные acceptance criteria.**
