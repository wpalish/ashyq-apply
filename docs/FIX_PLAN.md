# MASTER PROMPT — ASHYQ Apply: полное устранение дефектов

> Скопируй всё, что ниже линии, и отправь Claude Code одним сообщением в корне репозитория `ashyq-apply`.
> Промпт рассчитан на несколько сессий: фазы независимы, каждая заканчивается зелёными тестами и коммитом.

---

Ты — senior-инженер, отвечающий за репозиторий ASHYQ Apply (FastAPI + SQLAlchemy/Alembic + PostgreSQL/SQLite backend, React+Vite frontend, durable job queue на PostgreSQL, Playwright fetch-тир). Продукт: шортлистинг университетов и стипендий для международных абитуриентов, где каждое значение на экране имеет источник (claim: URL + excerpt + дата). Философия продукта: «unknown — первоклассный ответ; никогда не превращать неизвестное в догадку». Культура репозитория: предельно честная документация (docs/CURRENT_STATE.md, RELEASE_CHECKLIST.md со статусами PASS/FAIL). Не ухудшай эту культуру — улучшай.

Внешний аудит нашёл дефекты, перечисленные ниже. Часть воспроизведена вживую (помечено ⚡). Твоя задача — исправить ВСЁ по фазам, на каждый баг написав сначала падающий регрессионный тест.

## ГЛОБАЛЬНЫЕ ПРАВИЛА

1. **Test-first.** Для каждого бага: сначала тест, воспроизводящий дефект (красный), потом фикс (зелёный). Имена тестов описывают продуктовый сценарий, как в существующих (`test_a_...`).
2. **Коммиты.** Один логический фикс (или одна фаза, если фиксы мелкие и связанные) = один коммит. Сообщения на английском в стиле репо (`fix: ...`, `feat: ...`). Никаких гигантских коммитов «fixed everything».
3. **НЕ переименовывай внутренние пакеты/модули БД `unimatch`** — это осознанное решение (см. README). Пользовательские строки (UI, title, User-Agent, экспорт-дисклеймеры) — ДА, унифицируй на «ASHYQ Apply».
4. **Не ослабляй проверки**: не удаляй тесты, не снижай coverage-порог, не убирай security-гейты CI, не глуши линтеры новыми ignore без письменного обоснования в конфиге.
5. **Документация.** После каждой фазы обновляй RELEASE_CHECKLIST.md / docs/CURRENT_STATE.md честно: новый статус только если есть команда/тест, доказывающие его. Добавь в чеклист новые гейты для исправленных P0.
6. **Ворота качества после каждой фазы** (всё должно быть зелёным перед коммитом):
   - `cd backend && ./.venv/bin/python -m pytest` (SQLite; если доступен `scripts/pg.py` — прогони и PG-ветку)
   - `cd backend && ./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m mypy app`
   - `cd frontend && npm run typecheck && npm run lint && npm test && npm run build`
   - E2E, если установлены браузеры: `cd frontend && npm run e2e`
7. **Стиль кода** — как в репо: комментарии объясняют «почему», докстринги у публичных функций, без мёртвого кода.
8. Если окружение чего-то не позволяет (нет Docker, нет pgserver-wheel) — сделай всё возможное headless, а непроверенное помечай в чеклисте честно (`WRITTEN, NOT RUN`), никогда не ставь PASS наугад.
9. Фазы независимы. Если контекст сессии заканчивается — останавливайся на границе фазы, зафиксировав состояние в коммите и короткой заметке в RELEASE_CHECKLIST («next: Phase N»). Следующая сессия continues с этой фазы.
10. Окружение: Python 3.12 (`backend/setup.sh` через uv), Node 22. `pgserver` в requirements-dev — опциональный инструмент для локального PG; если его wheel не ставится на платформе, тесты PG-ветки скипаются — это приемлемо, но тогда не ломай SQLite-ветку.

## PHASE 0 — Baseline

Прогони все ворота качества из правила 6 и убедись, что старт зелёный (backend ~549 passed, frontend 47 passed, tsc clean). Зафиксируй: `git status` чистый, есть точка отсчёта. Дальше — только вперёд.

## PHASE 1 — P0: блокеры

### 1.1 ⚡ `POST /api/runs/{id}/retry` уничтожает результаты (критично)
Файлы: `backend/app/api/routes_research.py` (retry_run), `backend/app/pipeline/runner.py` (`_maybe`, `_persist_result`, `_update_result`).
Дефект: retry безусловно удаляет все `ProgramResultRow`, но сбрасывает в `pending` только стадии `failed/running`. У успешного run'а все стадии `done` → runner их пропускает → shortlist становится пустым (воспроизведено: 20 результатов → 0). Для run'а, упавшего на assessment, — то же самое: verification «done», строки удалены, assessment оценивает пустоту.
Фикс:
- Убрать bulk-delete результатов: `_persist_result` уже делает upsert по `(run_id, dedupe_key)` — дублей не будет.
- Семантика стадий: retry без `stage` → сбросить ВСЕ стадии в pending (полный честный перезапуск); retry со `stage=X` → сбросить X и все стадии после X по `STAGE_ORDER`.
- **Сохранять пользовательские решения при пересоздании строки**: в `_persist_result`/`_update_result` переносить `user_decision`, `user_decision_reason`, `user_notes`, `decided_at` из существующей строки в новый payload (сейчас пересозданный результат их затирает).
- UI (`frontend/src/screens/ProgressScreen.tsx` + `store.tsx` + `api/client.ts`): две явные кнопки — «Retry from the failed stage» (передаёт `stage` упавшей стадии) и «Re-run everything» (без stage, с подтверждением, что результаты пересчитаются, а решения сохранятся). Текущая единственная кнопка подписана «from the failed stage», но вызывает полный retry — это обман.
Приёмка: новые API-тесты: (a) retry успешного run'а сохраняет строки И решения; (b) retry run'а, упавшего на assessment, со `stage=assessment` не трогает verification и восстанавливает оценки; (c) retry со stage сбрасывает его и последующие. E2E/vitest на две кнопки.

### 1.2 ⚡ Повторный `collect-documents` — тихий no-op
Файл: `backend/app/api/routes_research.py` (collect_documents).
Дефект: `idempotency_key=f"documents:{run_id}:{approved}"` — ключ по КОЛИЧЕСТву одобренных. Изменил состав shortlist'а, сохранив счёт (одну отменил, другую одобрил) → enqueue возвращает старый succeeded job, новые строки не получают чеклисты (воспроизведено).
Фикс: ключ = детерминированный хэш отсортированного множества id одобренных строк, например `documents:{run_id}:{sha256(",".join(sorted(ids)))[:16]}`; плюс правило в `JobStore.enqueue`: существующий job в ТЕРМИНАЛЬНОМ статусе не блокирует новый — для такого ключа создавай job с суффиксом попытки (или просто не используй терминальные job'ы как дедуп). Выбери один механизм и задокументируй в докстринге.
Приёмка: API-тест точного сценария ⚡ (3 approved → collect → swap одной строки → collect → новый job выполнен, у новой строки есть checklist; у старой отменённой — поведение определено и протестировано).

### 1.3 IDOR: `set_decision` без tenant-проверки
Файл: `backend/app/api/routes_results.py`.
Дефект: `set_decision` (единственный роут результатов) не вызывает `owned_run(session, run_id, principal)`; в `get_result` тот же вызов продублирован дважды (copy-paste). Аутентифицированный пользователь другой организации может менять решения чужих строк.
Фикс: добавить `owned_run` в `set_decision`; убрать дубль в `get_result`. Провести ревизию ВСЕХ роутов: каждый, работающий с run/profile/result/claims/export, обязан проходить через `owned_run`/`owned_profile`.
Приёмка: тесты в `tests/test_security.py`: второй пользователь/организация получает 404 на `set_decision`, `get_result`, `export`, `claims`, `questions` чужого run'а. RELEASE_CHECKLIST gate 14 — обновить evidence.

### 1.4 Docker-стек не стартует (gate 22)
Файлы: `docker-compose.yml`, `Dockerfile.fly`.
Дефекты (все три независимы):
(a) сервис `api`: `read_only: true`, tmpfs только `/tmp`, но `config.get_settings()` при импорте вызывает `ensure_dirs()` → `mkdir /app/backend/data/{httpcache,exports}` → EROFS → crash-loop;
(b) сервис `worker`: volume `worker-cache:/app/data` — неверный путь, реальный cache_dir `/app/backend/data/httpcache`;
(c) сервис `web`: `depends_on: api: condition: service_healthy`, но у `api` нет healthcheck (ни в compose, ни HEALTHCHECK в Dockerfile.fly).
Фикс: volume/tmpfs на `/app/backend/data` для api и worker (общий том допустим — кэш идемпотентен); healthcheck для api (python-урловский `GET /api/health`, образ slim — используй `python -c "import urllib.request..."`); проверить, что migrate-job и read_only-ограничения согласованы.
Приёмка: если Docker доступен — `docker compose up --build` реально поднят, демо-run проходит через web→api→worker, скрин/лог в evidence чеклиста; gate 22 → PASS. Если недоступен — точный скрипт проверки `scripts/verify_compose.sh` + статус «WRITTEN, NOT RUN» (честно).

### 1.5 Rate limiting не работает за reverse-proxy
Файлы: `backend/app/main.py`, `fly.toml`, `docker-compose.yml`, `Dockerfile.fly`, `frontend/nginx.conf`.
Дефект: uvicorn запускается без `--proxy-headers`/`--forwarded-allow-ips`; лимитер ключуется по `request.client.host` = IP прокси → лимиты 10 login/мин и 20 runs/мин становятся ГЛОБАЛЬНЫМИ (DoS всех пользователей одним скриптом), в логах нет реальных IP. Per-email лимита на login нет; неизвестный email не выполняет scrypt → тайминг-энумерация.
Фикс:
- `--proxy-headers --forwarded-allow-ips` (в fly.toml — доверенная сеть Fly; в compose — сеть nginx) во всех командах запуска uvicorn.
- Login: лимит «per normalized email» в дополнение к per-IP (in-memory достаточно, задокументируй ограничение); при отсутствии пользователя — выполнить dummy `verify_password` против фиктивного хэша, чтобы выровнять тайминг; ответ всегда одинаковый.
- Регистрация: 409 остаётся (UX), но добавь per-IP+email rate limit на register.
Приёмка: тесты: два разных X-Forwarded-For → разные bucket'ы (с включёнными proxy-headers); 11-й login на один email за минуту → 429 даже с нового IP; тайминг-тест не обязателен, но dummy-verify покрыт unit-тестом.

### 1.6 ⚡ Двойной клик «Start research» → два параллельных run'а
Файлы: `backend/app/api/routes_research.py` (start_run), `frontend/src/screens/PreferencesScreen.tsx`, `frontend/src/lib/store.tsx`.
Дефект: `idempotency_key=f"research:{run.id}"` уникален для каждого запроса — защита бессмысленна (комментарий в коде утверждает обратное — исправь и комментарий). Два POST подряд → два run'а (воспроизведено), оба жгут worker-слоты и внешний трафик.
Фикс:
- Backend: отклонять старт нового run'а, если у профиля уже есть активный (stage в IN_PROGRESS_STAGES, не cancelled, job не в терминальном статусе) → 409 с `detail`, содержащим id активного run'а; ИЛИ (лучше) принимать клиентский заголовок `Idempotency-Key` для POST /api/runs и дедупить по нему. Реализуй оба.
- Frontend: кнопка старта блокируется на время запроса (`loading`), при 409 store присоединяется к существующему run'у вместо ошибки.
Приёмка: тест: два последовательных start_run для одного профиля → второй 409 (или тот же run); vitest/store-тест на обработку 409; комментарий в коде соответствует поведению.

## PHASE 2 — P1: надёжность backend и безопасность

### 2.1 Fencing для job-lease (зомби-worker)
Файлы: `backend/app/jobs/store.py`, `backend/app/jobs/worker.py`.
Дефект: `_beat` при потере lease только логирует и завершается — job продолжает исполняться; `complete()/fail()/mark_cancelled()` не проверяют владельца → зомби-worker может отметить succeeded job, уже перехваченный другим worker'ом; счётчики run'а (pages_checked, claims_recorded — read-modify-write) при этом удваиваются.
Фикс: все терминальные апдейты и heartbeat — с guard `WHERE status='running' AND worker_id=:me` (worker_id прокидывать в JobStore или хранить на экземпляре). При `heartbeat() == False` — worker обязан прервать исполнение job'а: подними событие отмены, которое `_check_cancelled`/runner увидит, и пометь job `failed` с ошибкой «lease lost» (без перезаписи, если владельцем уже другой — guard из предыдущего пункта это обеспечит).
Приёмка: тест: job claim'ят, lease «крадут» (вручную обновляют worker_id), исходный worker вызывает complete() → статус НЕ меняется, возвращается признак потери; worker при потере heartbeat прерывает run (unit-тест с фейковым heartbeat).

### 2.2 `JobStore.enqueue` откатывает чужую транзакцию
Файл: `backend/app/jobs/store.py`.
Дефект: при IntegrityError на unique-ключе делается `session.rollback()` всей сессии вызывающего — противоречит докстрингу «caller owns the session»; в `collect_documents` молча откатывает `run.cancelled=False` и AuditEvent.
Фикс: вставка job'а внутри `session.begin_nested()` (SAVEPOINT); откатывать только его.
Приёмка: тест: в сессию добавлен объект, enqueue проигрывает гонку по unique-ключу → объект вызывающего survives, возвращается существующий job.

### 2.3 `budget_currency` игнорируется в скоринге
Файл: `backend/app/domain/scoring.py` (Affordability-компонент).
Дефект: ceiling (`max_acceptable_gap` или `max_annual_budget`) — в валюте профиля (`funding.budget_currency`), а `gap.gap.amount` — в target_currency (USD). Для KZT-бюджета ratio≈0 → «affordable» у любого вуза. Плюс `or`-логика считает легитимный `max_acceptable_gap=0` отсутствующим.
Фикс: конвертировать ceiling в target_currency через `app.domain.currency.convert` (rate+date уже путешествуют с ConvertedMoney — добавь их в explanation компонента); выбирать ceiling через `is not None` (приоритет: max_acceptable_gap, затем max_annual_budget). Если валюта неподдерживаема — компонент честно `data_present=False` с объяснением, а не мусорное число.
Приёмка: тесты: KZT-ceiling против USD-gap даёт ratio≈1 при равной покупательной способности (480 KZT/USD из bundled snapshot); `max_acceptable_gap=0` уважается; неподдерживаемая валюта → missing-компонент.

### 2.4 Lease: единый источник правды + частый heartbeat + `stale` в UI
Файлы: `backend/app/pipeline/state.py`, `backend/app/api/routes_research.py`, `backend/app/pipeline/runner.py`, `frontend/src/screens/ProgressScreen.tsx`.
Дефекты: (a) `is_lease_expired` использует хардкод `LEASE_SECONDS=120`, хотя `settings.job_lease_seconds` конфигурируется env'ом — два источника правды; (b) `run.heartbeat_at` обновляется только в `_save()`, который в verify-стадии вызывается раз в 4 кандидата → в live-режиме здоровый run помечается stale; (c) UI НЕ рендерит `run.stale`, `job_error`, `recovery_count` (типы объявлены в types.ts) → при смерти worker'а ProgressScreen: без спиннера, без Cancel, без Retry — мёртвый тупик.
Фикс: (a) `_view` передаёт `lease_seconds=settings.job_lease_seconds`; хардкод удалить; (b) heartbeat run'а — на каждой итерации цикла кандидатов/строк (лёгким update без полного `_save`, если накладно); (c) ProgressScreen: при `stale && !job_running && stage in-progress` — risk-баннер «Worker stopped responding» + `job_error` + `recovery_count` + рабочая кнопка Retry (см. 1.1).
Приёмка: backend-тест на lease из settings; vitest/e2e: stale-run рендерит баннер и кнопку; heartbeat обновляется чаще (тест на счётчик записей или mock времени).

### 2.5 Причина отказа в UI
Файлы: `frontend/src/screens/ShortlistScreen.tsx`, `ApprovedScreen.tsx`, `store.tsx`.
Дефект: продукт и README обещают «rejections keep their reason»; `DecisionIn.reason` есть; UI всегда шлёт `reason=''` — поля ввода нет.
Фикс: при нажатии «No» — inline-поле причины (или маленький поповер) с необязательным текстом и быстрыми чипами («cost», «deadline passed», «no funding», «not a fit»); reason сохраняется через существующий decision-эндпоинт; ApprovedScreen показывает reason у rejected.
Приёмка: e2e: reject с причиной → причина видна в Approved и переживает reload; vitest на flow.

### 2.6 `applyConversion` портит профиль при ошибке
Файл: `frontend/src/screens/ProfileScreen.tsx`, `frontend/src/api/client.ts`.
Дефект: сырой `fetch(...).then(r => r.json())` без проверки `r.ok`, в обход типизированного клиента: при 4xx в draft записывается `{detail: ...}` вместо объекта GPA → профиль повреждён. Плюс лишний пре-вызов `validateProfile`.
Фикс: добавить `previewConversion(grade, methodKey)` в api-клиент (с нормальной обработкой ошибок); в ProfileScreen — try/catch, при ошибке показать notice, draft не трогать; убрать бессмысленный chained validateProfile.
Приёмка: vitest: ошибка API → draft неизменен, ошибка показана; успешный путь применяет converted_value.

### 2.7 `post_study_work` без доказательства у 2..N-го кандидата страны
Файл: `backend/app/pipeline/runner.py` (`_stage_verify`, gov_cache).
Дефект: government-claims добавляются только первому кандидату страны; остальные получают значение из кэша без claim'ов в своей строке — значение на экране без источника, нарушение философии продукта.
Фикс: кэшировать ТУПИЛ (claims, строка) и добавлять claims каждой строке этой страны (claims идемпотентны по dedupe на уровне строки); source_urls строки включают government-страницу.
Приёмка: тест: два кандидата одной страны → у обоих в claims есть POST_STUDY_WORK claim с source_url.

### 2.8 Citizenship-матчинг подстрокой
Файл: `backend/app/pipeline/runner.py` (`_scholarship_eligibility`).
Дефект: `citizenship.lower() in " ".join(restrictions)` → «Korea» ⊂ «North Korea only» = ложное MET; «Kazakhstan» ∉ «Central Asian nationals» = ложное NOT_APPLICABLE → стипендия жёстко отвергается. Это гадание — нарушение доктрины.
Фикс: матчинг по словоформам с границами слов: нормализовать citizenship и restriction-текст (lower, unicode-fold), искать совпадение корня страны/демонима как отдельного слова; при отсутствии совпадения, если restriction-текст не удаётся уверенно интерпретировать (содержит групповые слова типа «Central Asia», «EU/EEA», «developing countries» без явного совпадения) — статус проверки PENDING («requires official clarification»), а не NOT_APPLICABLE; `applicant_eligible` → "unknown", never a hard "no" на неоднозначности. Учитывать `second_citizenship` из профиля, если заполнен (см. также 4.7).
Приёмка: тесты на оба направления: «Korea» vs «North Korea» → НЕ met; «Kazakhstan» vs «Central Asian countries» → unknown/pending; точное совпадение → met; second citizenship совпал → met.

### 2.9 Неоднозначные даты
Файлы: `backend/app/domain/eligibility.py` и `backend/app/pipeline/runner.py` (`_as_date`).
Дефект: перебор `%d/%m/%Y` затем `%m/%d/%Y` молча угадывает «03/04/2027» (3 апреля vs 4 марта).
Фикс: если строка числовая и обе интерпретации валидны и дают РАЗНЫЕ даты → возвращать None (claim становится NEEDS_OFFICIAL_CLARIFICATION «date format ambiguous: d/m or m/d»). Однозначные случаи (>12 в первой компоненте, ISO, текстовые месяцы) — работают как раньше.
Приёмка: тесты: «03/04/2027» → None; «25/05/2027» → 25 мая; «May 25, 2027» → 25 мая; ISO — ок.

### 2.10 Глобальный `ValueError → 400` handler
Файл: `backend/app/main.py`.
Дефект: любой ValueError из любой глубины (включая UnsupportedCurrency и обычные баги) возвращается клиенту как 400 с сырым внутренним текстом: маскирует 500-е и раскрывает внутренности.
Фикс: убрать глобальный handler; в роутах, где ValueError — ожидаемая пользовательская ошибка (preview_conversion и т.п.), он уже явно конвертируется в HTTPException — проверить grep'ом все места; непредвиденный ValueError должен становиться 500 с generic detail и полным traceback в логе.
Приёмка: тест: роут, бросающий внутренний ValueError → 500, в detail нет исходного текста; известные user-error пути по-прежнему 400 с человекочитаемым сообщением.

### 2.11 ⚡ Инъекция в Content-Disposition + валидация `decision`
Файл: `backend/app/api/routes_results.py` (export).
Дефект: `?decision=approved" ; x-injected="1` попадает в заголовок filename (воспроизведено).
Фикс: валидировать `decision` по `UserDecision` (иначе 400 «unknown filter»); stem собирать только из `[a-z0-9-]`.
Приёмка: тест: кавычки/CRLF/мусор в decision → 400 или безопасный filename; валидные значения работают.

### 2.12 `/api/health` не проверяет БД
Файл: `backend/app/api/routes_meta.py`.
Дефект: health возвращает конфиг; Fly-чек зелёный с мёртвым PostgreSQL.
Фикс: `SELECT 1` с коротким таймаутом; при недоступности БД — 503 и `"status": "degraded"` (конфиг-поля сохранить). Обновить healthcheck-и (compose 1.4, fly.toml) — они должны падать на 503.
Приёмка: тест с живой БД → 200 ok; тест с испорченным URL/engine → 503 (через monkeypatch).

### 2.13 Auth: недостающие flows (пакет)
Файлы: `backend/app/api/routes_auth.py`, `backend/app/security.py`, `backend/app/models/auth.py`, новая миграция, `frontend/src/AuthGate.tsx` + новые экраны/модалки.
Сделать:
(a) **Смена пароля**: `POST /api/auth/password` (текущий + новый, ≥12); при успехе — отозвать ВСЕ сессии пользователя кроме текущей.
(b) **Сброс пароля**: токены одноразовые, хэш в БД, TTL 1 час, rate-limit; отправка письма — через плuggable sender: интерфейс + консольный sender для dev/demo (лог + в dev-режиме ответ может содержать ссылку ТОЛЬКО если `environment != production`), для production — SMTP-настройка в Settings (env). В prod-режиме ответ всегда «if the email exists, a link was sent» (анти-энумерация).
(c) **Удаление аккаунта**: `DELETE /api/auth/me` с подтверждением паролем; удаляет user, memberships, sessions; организации, где пользователь — единственный владелец, удаляются вместе с их профилями/run'ами (каскады уже настроены), при наличии данных требуется явный confirm-параметр. Audit-событие до удаления.
(d) **Переключение организаций**: `GET /api/auth/organizations` (список membership'ов) + `POST /api/auth/session/organization` (перевыпуск сессии под выбранную org, роль проверяется). UI: селектор workspace в topbar при >1 организации.
(e) **Гигиена сессий**: лимит активных сессий на пользователя (например 20, старейшая отзывается); периодическая чистка истёкших (в worker'е — лёгкая задача раз в N минут или при reap); `scrypt n=2^17` (обновить формат-строку и verify — старый формат 2^14 продолжать принимать при verify, но новые хэши только 2^17; миграция не нужна — rehash при следующем логине).
(f) **SameSite**: Strict → Lax (Origin-check и CSRF-защита middleware уже есть и остаются).
(g) **Подтверждение email** — МИНИМАЛЬНО: поле `email_verified` + настройка `auth_require_verified_email=false` по умолчанию; полный flow с письмами — только если (b)-sender уже позволяет; иначе — задокументируй как следующий шаг в CURRENT_STATE, не имитируй.
Приёмка: API-тесты на каждый flow (включая негативные: чужой токен сброса, повторное использование, смена пароля отзывает сессии, лимит сессий, переключение org меняет tenant-scope данных). E2E: login → смена пароля → logout. Обновить SECURITY.md.

### 2.14 Шрифты и CSP
Файлы: `frontend/index.html`, стили, `frontend/public/`.
Дефект: Google Fonts блокируется собственным CSP в проде (`style-src 'self'`) → типографика деградирует; в dev — утечка к третьему лицу. `<title>` — «UniMatch».
Фикс: self-host (woff2 через `@fontsource/*`-пакеты ИЛИ vendored-файлы в public/fonts + @font-face в global.css); убрать внешние link/preconnect; `<title>` → «ASHYQ Apply — evidence-backed university & scholarship shortlisting».
Приёмка: в production-билде нет внешних запросов (grep по dist + CSP не менялся); визуальный smoke (e2e скриншот).

### 2.15 ErrorBoundary
Файл: `frontend/src/main.tsx` + новый компонент.
Фикс: корневой ErrorBoundary с внятным fallback («Something broke while rendering. Your data is safe on the server.» + кнопка Reload), логирующий ошибку; опционально — второй уровень вокруг `<main>`, чтобы падение экрана не роняло сайдбар.
Приёмка: vitest: компонент-бомба → fallback виден, приложение не белое.

### 2.16 Freshness без действия
Файлы: `backend/app/jobs/*`, `backend/app/pipeline/runner.py`, новая queue-kind `recheck`.
Дефект: `next_recheck_at()` используется только в тестах; POSSIBLY_STALE claims не перечитываются никогда.
Фикс (минимальный честный вариант): при завершении run'а (awaiting_user_decision) worker ставит отложенный job `recheck` с `available_at = min(next_recheck_at)` по claims run'а; handler перезапускает verification/funding ТОЛЬКО для строк с устаревшими claims, апсертя результаты (механика 1.1 уже это умеет), решения пользователя сохраняются. UI: в ProgressScreen/SourcesScreen — строка «Next automatic re-check: <дата>» + ручная кнопка «Re-verify now» (ставит recheck job немедленно).
Приёмка: тест: завершённый run имеет queued recheck job с корректным available_at; handler обновляет stale claim; решения survive.

### 2.17 Валютный снапшот: сигнал протухания
Файлы: `backend/app/domain/currency.py`, `routes_meta.py`, `frontend/src/screens/ExportScreen.tsx` (и Preferences, где показываются деньги).
Фикс: если `RATE_DATE` старше 90 дней от сегодня — capabilities возвращает `currency.stale_warning`; UI показывает warn-строку рядом с конвертациями; `RATE_SOURCE` переименовать с «UniMatch» на «ASHYQ Apply». Добавить `scripts/update_rates.py`-заготовку (читает текущие курсы из открытого источника, печатает diff и готовый блок `_PER_USD` с новой `RATE_DATE` — применяется вручную, с указанием источника и даты в PR).
Приёмка: тест на warning при старой дате (freezegun/monkeypatch today).

## PHASE 3 — P2: UX

### 3.1 Грязная форма и потеря правок
Файлы: `frontend/src/lib/store.tsx`, `App.tsx`.
Фикс: store отслеживает `dirty` (draft ≠ last saved/restored snapshot); переключение кейса, «New case», «Blank/Demo profile» при dirty → подтверждение («You have unsaved changes…Discard / Save first»); черновик автосейвится в localStorage (ключ отдельно от saved profile, с пометкой «unsaved draft restored») — осторожно: предыдущий баг «demo data overwrote real profile» не должен вернуться (восстановление черновика не подменяет savedProfile).
Приёмка: vitest: dirty → switchCase требует подтверждения; после reload несохранённые правки восстановлены; saved profile не затёрт.

### 3.2 URL-роутинг
Файл: `frontend/src/App.tsx`.
Фикс: минимальный роутинг без новой тяжёлой зависимости (hash-router: `#/shortlist`, `#/runs/<id>` не нужен — состояние run'а уже в localStorage): экран ↔ `location.hash`, `popstate`/`hashchange` → setScreen; gate'ы сохраняются (нельзя перейти на shortlist без результатов — редирект на progress с объяснением). Back/forward работают, refresh восстанавливает экран, ссылку на экран можно скопировать.
Приёмка: e2e: навигация back/forward между экранами; прямой заход по `#/export` при отсутствии run → редирект+объяснение.

### 3.3 Поллинг
Файл: `frontend/src/lib/store.tsx`.
Фикс: один интервал, созданный один раз (deps — только признак «run активен», а не объект run); in-flight guard (не стартовать новый getRun, пока предыдущий в полёте); пауза при `document.hidden` (visibilitychange) с немедленным опросом на возврат; при ошибке — backoff (1.2s → 2.4s → 5s → cap 15s), ошибка поллинга НЕ показывает глобальный баннер на каждый тик (достаточно одного banner при >3 последовательных ошибках); результаты перечитывать при изменении `results_count` И после перехода stage в терминальный.
Приёмка: vitest с fake timers: один запрос в тик, пауза в hidden, backoff на ошибках.

### 3.4 Мёртвые поля профиля (~20 штук)
Файлы: `backend/app/domain/scoring.py`, `backend/app/domain/funding.py`, `backend/app/pipeline/runner.py`, `backend/app/domain/validation.py`, `frontend/src/screens/PreferencesScreen.tsx`, `ProfileScreen.tsx`.
Дефект: собираются, но не влияют ни на что: `safety_priority`, `diversity_priority`, `housing_guarantee_priority`, `university_size`, `campus_type`, `research_interests`, `values_coop`, `needs_work_during_study`, `must_cover_housing/meals/health_insurance/books/travel`, `requires_full_ride`, `accepts_full_tuition`, `accepts_partial`, `max_family_contribution`, `willing_to_submit_need_documents`, `funding_criticality`, `second_citizenship`, `class_rank`, `class_size`.
Фикс — для каждого поля РОВНО одно из двух (никогда не оставлять молча неиспользуемым):
- **Подключить**, если данные для честного использования есть: `must_cover_*` → проверка coverage-таблицы стипендии (не покрывает обязательную категорию → warning в funding_fit + unresolved question, НЕ молча); `requires_full_ride`/`accepts_full_tuition`/`accepts_partial` → фильтр/пометка в funding fit; `second_citizenship` → scholarship citizenship checks (2.8); `university_size`/`campus_type` → preference score против registry attributes (`size`, `campus` уже есть в реестре); `values_coop`/`needs_work_during_study`/`research_interests` → хотя бы unresolved-вопрос/пометка в деталях, если страница не дала данных; `class_rank/class_size` → контекст в explanation admissions fit (не баллы — честности ради); `max_family_contribution` → affordability-объяснение; `funding_criticality` → вес funding-компонент скоринга (документировать формулу).
- **Убрать из UI**, если честного использования нет (diversity/safety/housing priority без данных источников — кандидаты на удаление ИЛИ на явную пометку в UI «collected, not yet used in results» — удаление предпочтительнее).
Приёмка: таблица в docs (поле → где используется → тест) ; каждый подключённый путь покрыт тестом; в UI не осталось полей без эффекта и без пометки.

### 3.5 Сырые enum'ы в фильтрах
Файл: `frontend/src/screens/ShortlistScreen.tsx`.
Фикс: в `<option>` использовать `STATUS_LABEL[k] ?? humanize(k)` (как в StatusChip), значение — исходный enum.
Приёмка: vitest: в фильтре нет «NEEDS_OFFICIAL_CLARIFICATION», есть «Unverified».

### 3.6 Локали и форматирование
Фикс (минимум): единая локаль форматирования — `Intl` от `navigator.language` с fallback en-GB (деньги и даты ОДНОЙ локалью); в `format.ts` убрать хардкод en-US. Полная i18n-система (ru/kk) — отдельная фаза 6, здесь только согласованность.
Приёмка: format-тесты обновлены.

### 3.7 Брендинг
Файлы: везде по списку.
Фикс: пользовательские строки → «ASHYQ Apply»: `<title>` (см. 2.14), сайдбар `brand__mark`, footer-дисклеймер, сообщение в `api/client.ts` («Cannot reach the ASHYQ Apply API…»), дисклеймер и filename в `backend/app/export/tabular.py` (`ashyq-<runid>.csv`), User-Agent бота → `ASHYQApplyBot/0.2 (+https://github.com/wpalish/ashyq-apply; contact: ...)`, `RATE_SOURCE`. Ключи localStorage `unimatch.*` → `ashyq.*` С миграцией (при загрузке читать старые, писать новые). Внутренние имена пакетов/БД/env-prefix `UNIMATCH_` — НЕ трогать (осознанное решение), но добавить заметку в README.
Приёмка: grep «UniMatch» по frontend/src и user-facing строкам backend → только исторические упоминания в доках; тест на миграцию localStorage-ключей.

### 3.8 Экспорт «своих данных»
Файлы: `backend/app/api/routes_profile.py` (export_profile), `frontend/src/screens/ExportScreen.tsx`.
Дефект: подпись «complete record held», но нет результатов/claims/audit; в UI — `<pre>` без скачивания.
Фикс: backend включает results (payload'ы), claims, conflicts, audit events организации по этому профилю; frontend — кнопка Download JSON (blob) + просмотр. Подпись соответствует содержимому.
Приёмка: API-тест на полноту; e2e на скачивание.

### 3.9 Тон панели ошибок в Progress
Файлы: `backend/app/pipeline/runner.py` (сбор errors), `frontend/src/screens/ProgressScreen.tsx`.
Дефект: в `run.errors` смешаны реальные сбои фетча и честные «unknown»-диагнозы («cannot confirm that programme exists») — панель «Research limitations» пугает (47 записей на чистом демо-прогоне).
Фикс: разделить на уровне раннера/адаптеров два списка: `errors` (сбои) и `unknowns`/диагнозы неопределённости (новое поле run'а или структурированные записи с kind); UI: две панели — «What could not be confirmed (this is normal — unknowns are never guessed)» и «Fetch failures». Обратная совместимость: старое поле errors продолжает существовать.
Приёмка: тесты на классификацию; e2e-скриншот демо-прогона с двумя панелями.

### 3.10 Заметки без решения
Файлы: `backend/app/api/routes_results.py`, `frontend/src/screens/ShortlistScreen.tsx`.
Дефект: редактирование note переотправляет decision (ставит decided_at даже у undecided).
Фикс: отдельный `PATCH /api/runs/{run_id}/results/{result_id}/notes` (только notes, tenant-check!), decision-эндпоинт остаётся для решений; UI «Save note» дёргает его.
Приёмка: тесты: note без изменения decision/decided_at; IDOR-проверка на новый роут.

### 3.11 Пагинация
Файлы: routes_profile (list), routes_cases, routes_research (list_runs), routes_results (claims).
Фикс: единые query-параметры `limit`/`offset` (дефолты: 50/100, max 200; у claims max 500) + заголовок/тело с total; `list_runs` — batch-подсчёты вместо N+1 (один grouped query на results_count/decided_count). UI: «Show more» в коротких списках; `switchCase` ищет последний run профиля через `list_runs?profile_id=` (сервер уже умеет фильтр) вместо глобальных 50.
Приёмка: тесты на limit/offset и на отсутствие N+1 (assert количества запросов или explain).

### 3.12 Календарь дедлайнов
Файлы: новый `GET /api/runs/{run_id}/deadlines.ics`, `frontend/src/screens/DocumentsScreen.tsx`.
Фикс: ICS-экспорт (валидный VCALENDAR: admission deadlines + scholarship deadlines как VEVENT с DTSTART;UID;DTSTAMP, all-day) и панель «Upcoming deadlines» (ближайшие 10, сортировка, «passed» помечены) + кнопка «Add to calendar (.ics)».
Приёмка: тест на валидность ICS (парсинг) и состав событий; e2e на панель.

### 3.13 collect_documents: молчаливые пропуски
Файл: `backend/app/pipeline/runner.py` (collect_documents, `_stage_funding` — тот же паттерн `by_name`).
Дефект: сопоставление кандидатов по точному имени; несовпадение → silent `continue`; «Checklists built for 0» → COMPLETED.
Фикс: сопоставлять по `dedupe.university_key(name, country)`; при пропуске строки — писать запись в `run.errors` (kind=unknown, см. 3.9) И unresolved question в строку результата; если построено 0 чеклистов при >0 одобренных — stage finish с явным warning в detail.
Приёмка: тест: переименованный кандидат → ошибка видна в run.errors и unresolved строки, а не тихий пропуск.

### 3.14 Прогресс-цифры
Файл: `backend/app/pipeline/runner.py` (`_stage_verify`).
Фикс: `items_done/items_total` считать программами (seen_keys), а не кандидатами; `programs_verified`/`pages_checked` коммитить вместе с heartbeat (см. 2.4b).
Приёмка: тест на консистентность counters после прерванного прогона.

## PHASE 4 — P3: гигиена

4.1 **Мёртвый код**: `can_transition` — либо реально применять в `_transition` (с логированием запрещённых переходов и тестами), либо удалить; блок `if any(... NOT_ELIGIBLE ...): pass` в `_stage_funding` — реализовать задуманное (похоже на пропуск классификации при hard-провале citizenship — реши по контексту и покрой тестом) или удалить; `app/pipeline/queue.py` (tombstone) — удалить вместе с исключением в mypy.ini; дубль `owned_run` в `get_result` (сделано в 1.3); зависимости `tenacity`, `python-multipart` — удалить из requirements (grep подтверждает неиспользование; python-multipart вернуть, если появится multipart-upload).
4.2 **Линтеры**: добавить `ruff format --check` в CI и прогнать форматирование один раз отдельным коммитом (`style:`); в mypy.ini постепенно вернуть `arg-type` для `app/api` (если дорого — сузить исключения до конкретных модулей с обоснованием).
4.3 **Репозиторий**: добавить LICENSE (MIT, если владелец не возражает — иначе оставить явный TODO в чеклисте), CONTRIBUTING.md (setup, gates, commit-стиль, как гонять PG-ветку), `.github/ISSUE_TEMPLATE` (bug/feature); `LOOP_REPORT.md` → `docs/process/LOOP_REPORT.md`; `.claude/` НЕ трогать.
4.4 **БД**: новая Alembic-миграция: JSON→JSONB для PG (диалект-зависимо, SQLite остаётся JSON) по колонкам payload/detail/stage_state и т.д.; `ApplicantProfileRow.organization_id` — убрать default «dev-org» (явная передача везде; `seed_demo.py` пусть создаёт dev-организацию явно и НЕ мутирует глобальный settings singleton — копия настроек или параметр раннера); `FixedWindowLimiter` — периодическая очистка пустых deques.
4.5 **Мелочи API**: `audit?limit` → `Query(ge=1, le=1000)`; `DecisionIn.reason/notes` → `max_length` (2000/20000); `_stage_assess` — `today` брать как `datetime.now(UTC).date()` (не локальный `date.today()`); `_activity_strength`: заполнен `hours_per_week`, но нет `weeks_per_year` → считать annual_hours по документированному допущению (40 недель/год) И добавлять missing-field пометку, либо честно None + missing_fields — выбери и задокументируй; `available_methods` для конверсий — не предлагать `uk_class_to_us4` для не-UK процентных шкал (эвристика по scale_label: содержит «uk»/«british»).
4.6 **Покрытие registry честно в UI**: `capabilities` возвращает `live_coverage: {institutions: N, countries: [...], recall_note: "…"}` из institution_registry + docs/LIVE_DISCOVERY_REPORT; PreferencesScreen показывает это при включении live-режима (сейчас пользователь не понимает, что live = 10 университетов).
4.7 **E2E с auth**: новый e2e-spec (отдельный playwright-проект/конфиг с `UNIMATCH_AUTH_ENABLED=true` backend): register → login → create profile → run → logout → login снова → данные на месте; 401-редирект на AuthGate.
4.8 **Тест-гигиена**: добавить недостающие негативные API-тесты, названные по сценариям из этого промпта (1.1, 1.2, 1.6, 2.1, 2.2, 2.8, 2.9, 2.11, 3.13); в CI sqlite-ветке поднять `--cov-fail-under` до текущего фактического уровня (не ниже 80).

## PHASE 5 — Ops и observability (минимально жизнеспособно)

5.1 **Request-id middleware** (входящий заголовок или генерация, прокидывать в логи через logging Filter; отдавать `X-Request-ID` в ответе).
5.2 **Structured logs**: опция `UNIMATCH_LOG_FORMAT=json` (python-json-logger или ручной Formatter) — для прода; human-формат остаётся дефолтом dev.
5.3 **`/metrics`** (prometheus-формат без тяжёлых зависимостей: counters jobs done/failed/dead, runs by stage, http latency histogram, limiter hits) — эндпоинт только для внутренней сети/без tenant-данных; в fly.toml — internal port или отдельный process-чек.
5.4 **Бэкапы**: `fly.toml`/docs — конкретный scheduled-бэкап (fly postgres или cron `pg_dump` + retention), проверить `scripts/backup_drill.py` запускаемостью; описать в docs/BACKUP_RESTORE.md команду расписания.
5.5 **Админ-видимость dead jobs**: `GET /api/admin/jobs?status=dead` (только role=owner своей организации ИЛИ глобальный admin-флаг через env `UNIMATCH_ADMIN_TOKEN` — выбери tenant-safe вариант: org-scoped достаточно) + строка в ExportScreen/ProgressScreen «N jobs need attention» при наличии.
5.6 **Юридическое**: заглушки Privacy Policy и Terms (markdown-страницы + роуты/экран), явный TODO на юридическую ревизию — продукт хранит персональные данные, возможно несовершеннолетних.

## PHASE 6 — Опционально (если всё выше зелёное и есть бюджет времени)

6.1 **i18n-фундамент**: extraction строк в словари, ru + kk как первые локали (без машинного перевода спорных терминов — оставить glossary-файл и пометки для human review).
6.2 **Импорт транскрипта**: PDF → черновик профиля (через существующий pdf-парсер), с обязательным ручным подтверждением каждого поля (философия «ничего не применяется молча»).
6.3 **Расширение live-registry**: +10 университетов с verified seeds (процесс описан в docs/CANARY_AUDIT.md), приоритет — Центральная Азия и популярные у KZ-абитуриентов направления; каждый новый seed — canary-проверка.

---

## РЕЦЕПТЫ ВОСПРОИЗВЕДЕНИЯ (для регрессионных тестов фазы 1)

**⚡ 1.1 retry:** создать профиль (демо), `POST /api/runs` → дождаться `awaiting_user_decision` (демо ~15 c) → `POST /api/runs/{id}/results/{rid}/decision {decision:"approved"}` → `POST /api/runs/{id}/retry` → дождаться завершения → ожидать `results_count == 20` и решение сохранено (сейчас: 0).

**⚡ 1.2 documents:** одобрить 3 строки → `POST collect-documents` → дождаться succeeded → одну строку в `undecided`, другую в `approved` (счёт снова 3) → `POST collect-documents` → ожидать НОВЫЙ job и checklist у новой строки (сейчас: 202 + старый succeeded job, checklist отсутствует).

**⚡ 1.3 IDOR:** пользователь A создаёт run+result; пользователь B (другая org) → `POST /api/runs/{A_run}/results/{A_result}/decision` → ожидать 404 (сейчас 200).

**⚡ 1.6 double-click:** два `POST /api/runs` подряд одним профилем → ожидать один run/409 (сейчас два 202).

**⚡ 2.11 header injection:** `GET /api/runs/{id}/export.csv?decision=approved%22%20%3B%20x-injected%3D%221` → ожидать 400 или чистый filename (сейчас кавычка в Content-Disposition).

## ОПРЕДЕЛЕНИЕ ГОТОВНОСТИ

Релиз-критерий всего промпта:
1. Все ворота качества (правило 6) зелёные, включая новые тесты.
2. Каждый ⚡-сценарий покрыт регрессионным тестом и проходит.
3. RELEASE_CHECKLIST.md обновлён: старые gate'ы перепроверены, новые (retry-сохранность, documents-идемпотентность, tenant-полнота, compose-run, proxy-headers, stale-UX, dead-fields) добавлены со статусами и evidence.
4. `git log` — последовательность атомарных коммитов с понятными сообщениями; ни одного коммита «fix everything».
5. docs/CURRENT_STATE.md отражает новую реальность без преувеличений.

Начинай с Phase 0 и иди по порядку. Перед каждой фазой перечитай соответствующий раздел полностью. Если в ходе работы найдёшь дефект, не описанный здесь, — зафиксируй его в отдельном файле `docs/FINDINGS_BACKLOG.md` (не чини молча, не расширяй scope фазы).
