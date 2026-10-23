# Отклонённые PII значения в диагностике — DESIGN_ONLY

Предлагается отдельная задача после выпуска текущего security round: закрыть сохранение **уже отклонённых** значений в Fetcher, privacy exceptions и диагностических sinks. Этот пакет — план, не исправление. Source/tests прочитаны 9 октября 2026; тесты, DB, provider, сеть, CUA, Git и primary edits для него **NOT RUN**. Привязка к 21 прочитанному файлу находится в `source-pins.json`; точные фрагменты — в `source-excerpts.json`. Это не whole-tree/HEAD receipt и не дополнительное условие принятия предыдущего legal packet.

## Первый подтверждённый путь

1. [Fetcher._get](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/adapters/fetching.py:973) обнаруживает PII до cache/DNS/request. Но warning использует `url[:120]`, а refusal возвращает исходный `FetchResult.url`. Усечение строки не удаляет её чувствительное содержимое. В [redirect branch](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/adapters/fetching.py:628) отклонённый hop также попадает в warning и `final_url`. Это статически подтверждённое сохранение в сообщении/возвращаемом объекте; реальный сетевой вызов или запись production log не проводились.
2. [WebCostAdapter](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/adapters/cost/web_costs.py:54) при отказе копирует **original candidate.costs_url**, а не безопасную identity результата: в `errors`, `PageOutcome.url` и `retry_urls`. Поэтому только очистить `FetchResult.url` недостаточно. Requirements также использует исходный `target.url` для error/PageOutcome, но privacy refusal в его условный retry list не включён.
3. [Runner](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/pipeline/runner.py:883) принимает cost outputs; `_record_page_outcomes` и `_record_diagnostics` сохраняют строки, retry aggregation сохраняет URL. [RunView](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/api/routes_research.py:175) возвращает errors/unknowns/retry_urls. Это конкретная цепочка при передаче такого synthetic URL кандидату, не доказательство существования PII в текущей базе.

## Отдельная ветвь QueryPrivacyError

[Intent guard](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/adapters/search/intent.py:73) помещает `value!r` в exception message; population allowlist также помещает rejected marker. Значение остаётся в `str(exc)`, `repr(exc)` и `args`, хотя provider его не получает. **Прямая действующая query→persisted-run утечка здесь не установлена:** `_public_requested_fields` и single-field discovery catches уже не логируют исключение, а существующий multifield test проверяет сохранность безопасного Mathematics и отсутствие rejected email в trace/provider calls.

Если такой error выйдет из stage, общий [runner exception handler](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/pipeline/runner.py:469) пишет traceback, `run.errors` и audit.error. Далее [worker](/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/app/jobs/worker.py:159) пишет traceback и передаёт текст в JobStore.fail/last_error. Это подтверждённые generic sinks; достижимость через injected synthetic stage должна быть проверена отдельно. JSON formatter сохраняет exception text; изменение только message без проверки exc_info недостаточно.

## Минимальный контракт следующего исправления

| Граница | Сохранить | Исключить |
|---|---|---|
| QueryPrivacyError | ValueError subtype, безопасное имя поля из allowlist, machine-readable reason: email/currency/grade/long-number/population-not-allowed; понятный текст без значения | rejected value в message/args/атрибутах/цепочке diagnostic; его hash также не нужен |
| Fetcher privacy refusal | `REFUSED_PRIVACY`, reason label/code, реальные счётчики; status `None`, если HTTP ответа не было | rejected input/hop в warning, url/final_url, LogRecord args/extra |
| Public URL identity | Полный exact URL для обычного публичного URL, включая полезный CMS id/публичный query. Для отказа — проверенная публичная origin identity; для poisoned hop — безопасный initial source URL | userinfo, rejected query/fragment/path. Если public origin нельзя безопасно установить — bounded placeholder, а не echo raw |
| Adapters→runner | fetch-failed/unknown distinctions, page classification, typed reason, настоящий HTTP status для обычных ошибок, безопасная source identity | original unsafe input, ошибочно возвращённый как retryable URL. Privacy refusal не становится обычной ссылкой для retry |
| Runner/worker typed privacy exception | failure stage/type, correlation/run/job identity, safe reason/field; lease fencing и поведение повторного выброса | raw exception string/chained exception в logs/audit/run/job |

Не создавать фиктивный status 0/200 для локального отказа. Если понадобится показывать уже наблюдённый 302 до отказа hop, назвать его redirect status отдельно от ответа конечной страницы. Не превращать отказ в доказательство отсутствия программы или требований.

Сначала исправить constructor/logging boundary, затем **в том же bounded increment** связанные adapter diagnostics/retry и runner/worker typed-privacy sinks. Общий безопасный renderer предпочтительнее ручных regex в каждом sink, но helper не должен получить raw rejected value для сохранения. Domain не импортирует adapters и не делает I/O. Перенос/расширение PII detector и новая API/DB схема не требуются для этого плана; выбор расположения helper остаётся implementation review.

## Проверка, которая имеет смысл

Финитный набор из шести сценариев и отрицательный контроль описаны в `test-plan.json`. Synthetic sentinel расположен в начале URL/field, поэтому текущий truncation его не скрывает. Проверяются реальные refusal ветви и downstream outputs, а не вызов будущего sanitizer напрямую. На исходном коде ожидается semantic RED для warning/result/hop/exception/cost persistence; **этот прогноз основан на прочитанном коде и не является выполненным RED**. После исправления каждый тот же сценарий должен стать GREEN с полезными причинами и public identity.

Будущий harness: MockTransport + stub resolver/fail-fast socket guard, tmp cache, in-memory sinks/session/JobStore spies; никаких private runtime symlinks/copies. Runner error test использует actual QueryPrivacyError из DiscoveryIntent в injected stage; worker получает этот же тип через свой actual exception branch. Не нужно запускать production worker или читать DB. Если real persistence потребует synthetic temporary DB, это отдельный явно scoped test в следующей задаче, здесь он не разрешён и не запущен.

Existing acceptance нужно сохранить: initial URL/hop refusal **до DNS/второго HTTP**; безопасные CMS numeric path IDs; original error phrase/category controls; safe multifield subject продолжает находиться; unrelated 404/robots/timeout не теряют status/reason/public source. Уже существующие tests не заменяют sentinel no-retention assertions.

Scope limitation: этот increment касается значений, которые guards уже отклонили, и связанных диагностических путей. Он не доказывает детекцию всех форм PII, очистку исторических копий/logs, provider privacy, backup deletion или безопасность всей системы. Дополнительные scholarship/document/government/crawler serialization sinks требуют проверки при реализации shared boundary; нельзя заявить общий coverage по одной cost цепочке.
