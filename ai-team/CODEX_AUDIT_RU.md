# Полный аудит работы GLM по ASHYQ Apply

Дата проверки: 7 сентября 2026 года

Проверенная ветка: `ai/c1/integration`

Финальный локальный HEAD аудита: `ab2e70a46110bbd667cd881f25ab880de63df492`

Проверенный `origin/main`: `7b1fce0a5b58ca0540751b104baf2fce94817b22`

## Итог одним абзацем

GLM сделал полезную и в основном качественную локальную кампанию, но его финальная формулировка
«проект доведён до конца» неверна. Реально интегрированы пять задач из 24: T01, T04, T09, T10 и
ограниченный PILOT-срез T18. Код этих пяти задач собирается и проходит тесты, однако проект в целом
не завершён, live research не достиг рабочего качества, provider-backed search/LLM отсутствует,
публикации и deployment не было. В ходе независимого аудита найдены и исправлены три дополнительных
дефекта. Ветка теперь локально зелёная и готова к review, но **не готова к production release**.

## Что именно сделал GLM

GLM-кандидат `e533d62` сохранён отдельной ссылкой `audit/glm-c1-e533d62`. После наложения на
актуальный `origin/main` его полезный diff составляет 32 файла, 3 200 добавлений и 275 удалений:

1. **T01 — password reset:** перестал возвращать reset token в HTTP-ответе во всех окружениях.
2. **T04 — частичная стоимость:** отделил полный расчёт от lower-bound/частичного и неизвестного;
   `known zero` больше не равен отсутствующим данным.
3. **T10 — job fencing:** добавил attempts-token fencing для записей worker/run и PostgreSQL-проверки
   конкурентных попыток.
4. **T09 — frontend drafts:** черновики переживают reload, защищены от hydration race и разделены по
   case/tab.
5. **T18 — часть live discovery:** расширил детерминированные правила KZT/₸ и IELTS, добавил
   `PageOutcome`-диагностику и более честный canary-отчёт.

GLM также создал локальный `ai-team/` с планом, ledger, контрактами, логами и acceptance packets.
Размер комплекта около 972 KB, 132 файла.

## Что в заявлении GLM не соответствует фактам

### 1. Это не завершённый проект

`ai-team/TASKS.md` содержит 24 задачи. Интегрировано пять. В самом ledger вообще есть только семь
объектов задач: T01, T04, T09, T10, T18, T25 и T26. T25 и T26 остаются `BACKLOG`.

T18 по карточке зависит от T08, T13, T16 и T17, которые не завершены. Поэтому исторический статус
`DONE_LOCAL_INTEGRATION` означает лишь локальную интеграцию небольшого slice, а не готовность всей
live-research функции.

### 2. Live research не был проверен в поле

GLM прямо оставил live canary как `NOT_RUN/PILOT-ONLY`, хотя итоговый текст звучал почти как закрытие
проблемы. Независимый canary показал, что это существенная оговорка, а не формальность.

### 3. Search API и LLM отсутствуют

В коде нет provider adapter для web search и нет LLM extraction/verification adapter. В конфигурации
нет ключей. Без выбора провайдера, privacy boundary, лимитов, retry/cost controls и secrets эта часть
не может считаться реализованной.

### 4. Acceptance checker слабее, чем звучит отчёт

Все пять `acceptance-packet.json` проходят `check_team.py packet`, но checker проверяет структуру,
непустые поля и строки evidence. Он не аутентифицирует runtime agent IDs и не доказывает смысловую
подлинность логов. В одном T09 packet QA evidence фактически указывает на developer artifact, а один
reviewer ref сокращён. Поэтому код и gates можно проверить независимо, но полную независимость всех
ролей нельзя доказать только файлами.

### 5. Ledger содержал фактический дефект

`preflight.completed_at_local` был записан как невалидное `2026-09-06T23:2x+03:00`. Я не стал
угадывать минуту: поле заменено на `null`, исходная строка сохранена в
`completed_at_local_source_invalid`. В ledger добавлен блок `codex_audit_2026_09_07`, который
официально исправляет ложную формулировку полной готовности.

## Что я независимо нашёл и исправил

### `7f364cf` — rollback stale payment reconciliation

GLM security review заметил риск, но не устранил его. Двухсессионный PostgreSQL-тест доказал реальный
дефект: stale worker после потери fence мог сохранить `PaymentEvent` при non-terminal provider status.
Теперь неуспешный fenced transition вызывает `LeaseLost`, и весь payment transaction откатывается.

Сфокусированные проверки: 30 тестов passed, включая PostgreSQL concurrency. Опасение о дублировании
`ResearchRun` в terminal paid-path не воспроизвелось: этот путь уже откатывался при failed completion.

### `135138a` — корректная зона `edu.kz`

`admissions.nu.edu.kz` ошибочно считался отдельным registrable domain, потому что `edu.kz` не было в
списке multipart suffixes. Добавлены `edu.kz` и regression case.

### `02d648c` — фильтрация live-программ по профилю

Первый живой canary показал, что перед нужным BSc Computer Science выбирались MSc Electrical and
Computer Engineering и BSc Mathematics. Из-за лимита двух программ правильная страница вообще не
доходила до verification. Теперь после чтения страницы discovery проверяет совпадение degree level и
subject с профилем. Offline RED→GREEN тест закрепляет поведение.

## Живой canary Nazarbayev University

Canary выполнен ограниченно: только `nu.edu.kz`, robots.txt соблюдён, browser tier отключён, секреты и
production DB не использовались.

### До исправления profile filter

- доступ: `REACHED`;
- страницы: 35 успешно, 0 fetch failures;
- programme page: найдена;
- scholarship page: найдена;
- claims: 0;
- false positives: 0.

### После исправления

- доступ: `REACHED`;
- страницы: 26 успешно, 0 fetch failures;
- выбрана точная страница `BSc Computer Science`;
- claims: 1 (`program_exists`);
- false positives: 0;
- core verification completeness: **0%**.

Почему completeness осталась нулевой: plain HTTP fetch видит на основной NU admissions page только
42 читаемых символа — фактически JS shell. При этом официальная отрендеренная страница действительно
содержит IELTS, дедлайны и tuition: [Regular Admissions](https://nu.edu.kz/admissions/how-to-apply/foundation-undergraduate/regular-admissions/).
Страница программы также доступна и корректно описывает предмет:
[BSc Computer Science](https://scai.nu.edu.kz/bsc-cs).

Следовательно, GLM исправил словарь и наблюдаемость, но не доставил надёжный rendering/provider path.
`REACHED` здесь нельзя путать с «данные проверены».

## Полная независимая верификация текущей ветки

| Gate | Фактический результат |
|---|---|
| Backend pytest | 1 153 collected/passed, exit 0 |
| Coverage | 93.00%, порог 92% не понижен |
| Ruff check / format | pass, 154 файла |
| mypy app + tests | pass, 154 source files |
| Frontend typecheck | pass |
| Frontend lint | pass |
| Vitest | 182/182, 20 файлов |
| Production build | pass |
| Playwright normal | 75 passed, 1 skipped |
| Playwright auth | 6/6 passed |
| Alembic | один head `e7c1a4d90b52`, upgrade pass |
| Demo seed | pass; Groningen #1, UBC `OUT_OF_BUDGET` |
| pip-audit production deps | 39 dependencies, 0 known vulnerabilities |
| npm audit production deps | 0 vulnerabilities |

После E2E все автоматически перегенерированные screenshot diffs восстановлены; ветка чистая.
Текущий публичный `main@7b1fce0` также имеет успешный
[release-gates run](https://github.com/wpalish/ashyq-apply/actions/runs/34115345524).

## Что GLM потребовал от владельца и что сделано

| Требование GLM | Что сделал Codex | Состояние |
|---|---|---|
| Разрешить bounded live canary NU | Запустил безопасный single-site canary, сохранил и разобрал два результата | Выполнено локально |
| Выбрать search provider и LLM provider, положить ключи | Проверил отсутствие adapters/keys; не покупал сервис и не создавал секреты за владельца | Требует бизнес-решения |
| Review и публикация `ai/c1/integration` | Синхронизировал с актуальным main, исправил дефекты, полностью прогнал gates | Готово к review, не опубликовано |
| Добавить `ai-team/` в Git | Исправил ledger, проверил secrets/packets и после явного разрешения владельца подготовил весь bundle к публикации | Выполнено в отдельном evidence commit |

Первоначально публикация не выполнялась без отдельной команды. После этого отчёта владелец явно
разрешил «задеплой всё в GitHub»: ветка и evidence bundle публикуются через PR, без прямого merge в
защищённый `main` и без application deployment.

## Состояние `ai-team/`

- JSON валиден, `check_team.py plan` сообщает 24 задачи.
- Все пять packet-файлов структурно валидны.
- Secret-like файлов или значений audit regex не нашёл.
- 31 файл содержит абсолютные `/Users/wpalish/...` пути.
- Runtime invocation IDs из файлов невозможно независимо подтвердить после завершения ZCode-сессии.
- Добавлен честный Codex verdict: `PARTIAL_CAMPAIGN_VERIFIED_AND_REPAIRED; PROJECT_NOT_COMPLETE`.
- Комплект добавлен в публикационную ветку после отдельного явного разрешения владельца.

Владелец осознанно разрешил публикацию всего bundle. Машинные пути сохранены как forensic provenance;
это по-прежнему не превращает runtime refs в аутентифицированное доказательство полной готовности.

## Главные оставшиеся блокеры до публичного запуска

### P0 — release/security

1. **Browser/network boundary.** Безопасно завершить и проверить H02/SSRF/redirect/subresource policy.
   В отдельном worktree `task/release-hardening` уже есть незакоммиченный крупный H02-кандидат; его
   нельзя слепо копировать или терять.
2. **Staging reset delivery.** Staging разрешает `EMAIL_SENDER=console`, то есть reset links попадают в
   логи, а пользователь не получает письмо. Для публичного staging нужен fail-closed SMTP/provider.
3. **Provider privacy/security.** До подключения search/LLM определить разрешённые данные, redaction,
   budgets, timeouts, rate limits, audit trail и fallback semantics.
4. **Deployment baseline.** Production secrets, TLS/CORS/cookies, backups/restore drill, migrations,
   observability, error reporting, retention/deletion и incident plan не проверены этой кампанией.
5. **Отдельная release-hardening ветка.** В
   `work/ashyq-apply-master-fix` есть 24 коммита исправлений и незакоммиченные H02-изменения в пяти
   tracked файлах плюс `docs/NETWORK_BOUNDARY.md`. Это другая линия истории; нужен осознанный reconcile,
   а не merge «на удачу».

### P1 — продуктовая полнота

1. Завершить 19 неинтегрированных карточек из 24, начиная с реальных зависимостей T18.
2. T16/T25: search provider adapter и безопасный browser/provider route.
3. T08/T13/T17: необходимые extraction/verification части, от которых зависит T18.
4. T26: dated `NewsEvent`/`SourceChange`, applicability, conflict handling и diff источников.
5. Funding/documents adapters должны писать такие же `PageOutcome`, как requirements/cost.
6. Закрыть оставшиеся T10 race follow-ups: claim-token propagation, startup reconcile check-then-act,
   run-level single-writer.
7. Закрыть T09 envelope size/depth, slot GC и data-at-rest/logout semantics.
8. Устранить React `act(...)` warnings в payment tests и объяснить единственный skipped E2E.

### P2 — качество и документация

1. Обновить устаревшие цифры тестов в README/current-state docs.
2. Добавить sanitization/redaction canary diagnostics и bounded regex windows.
3. Проверить Money на non-finite JSON, percentage bounds и edge formats.
4. Свести два параллельных planning-набора: оригинальный repository brief и GLM `ai-team/TASKS.md`.

## Git-состояние и безопасный следующий шаг

- Проверенный code/handoff baseline перед evidence commit: `ai/c1/integration@ab2e70a`.
- Включает актуальный `origin/main@7b1fce0`.
- Оригинальный GLM candidate сохранён: `audit/glm-c1-e533d62`.
- На момент завершения технического аудита upstream отсутствовал; последующая явная команда владельца
  разрешила push ветки и создание PR. `main` напрямую не изменяется, application deployment не запускается.
- Основной checkout остаётся на локальном `main`, который отстаёт от origin на пять коммитов, и хранит
  только untracked `ai-team/`; я не переключал и не переписывал его.

Безопасная последовательность дальше:

1. Просмотреть diff `origin/main..ai/c1/integration` и этот отчёт.
2. Если код устраивает — явно разрешить push ветки и создание PR. Merge делать после GitHub CI/review.
3. Отдельно выбрать search/LLM strategy; без этого live research остаётся pilot.
4. Отдельно reconcile `task/release-hardening`, затем провести production readiness review.
5. Только после P0 — deployment в staging с реальными SMTP/observability/backup controls.

## Финальный вердикт

GLM не «доделал проект полностью». Он реализовал пять полезных локальных изменений и построил богатую,
но местами переоценённую evidence-цепочку. После моего аудита текущий кандидат существенно честнее и
надёжнее: три дополнительных дефекта закрыты, все локальные gates и dependency audits зелёные, live NU
поведение измерено. Однако релизный статус остаётся **READY FOR OWNER CODE REVIEW, NOT PRODUCTION READY**.
