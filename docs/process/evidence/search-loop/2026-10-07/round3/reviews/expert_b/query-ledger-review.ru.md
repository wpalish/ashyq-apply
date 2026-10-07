# Round 3: production query ledger — подтверждённый разрыв учёта

**Подтверждён дефект общего шестизапросного бюджета университета.** На замороженных исходниках production-путь может вызвать провайдера семь раз: один раз для идентичности сайта и шесть для программ. Возвращённые `DiscoveryTrace.search_queries_sent` и `Candidate.search_queries_used` показывают шесть. У неизвестной или неуспешной identity-попытки один вызов полностью теряется из обоих счётчиков.

Это независимое офлайн-воспроизведение production-методов с fake vendor, а не утверждение о семи реальных платных запросах в текущем capture. Настоящих сетевых/vendor вызовов не было. Замороженный commit `d669fd2` указан владельцем; Git-команды экспертом не выполнялись. Проверены точные хеши файлов ниже.

## Контракт и первая потеря

`app.adapters.search.intent` задаёт `DEFAULT_QUERY_BUDGET=6` и включает `SHARED_QUERY_BUDGET=True`. Комментарий определяет один общий бюджет всех этапов на университет, хранящийся на candidate. Требования вычитают `candidate.search_queries_used` из шести и резервируют один запрос для стипендий; стипендии отказываются от поиска при счётчике ≥6.

Разрыв начинается в `CatalogueDiscoveryAdapter._identify_site`: перед `provider.search(...)` и после него нет изменения identity trace/candidate счётчика. Даже успешный provider search, который нашёл root и позволил продолжить исследование, остаётся невидимым для общего бюджета.

Затем `_enrich` вызывает `_discover_one(entry, profile)` без передачи расхода. `_discover_one` создаёт новый `DiscoveryTrace` со счётчиком ноль. Из старого trace переносится только `search_failures`. Простое добавление identity-count к старому trace не решает проблему: отдельный контроль с заранее выставленным `search_queries_sent=1` воспроизводит его потерю при замене trace.

Наконец, оба planner-пути используют полный бюджет. Single-field `_add_search_results` вызывает `discover_candidates` без `query_budget`, поэтому генератор планирует шесть. Multi-field выбирает `intents[:DEFAULT_QUERY_BUDGET]` и распределяет все шесть между ними; текущий расход trace не вычитается. `_apply` записывает в candidate только расход нового trace. Три независимых прямых planner-контроля подтвердили, что при исходном count=1 оба пути отправляют ещё шесть, а при count=6 single-field всё равно отправляет шесть и возвращает count=12.

## Найден ли другой production guard

`ResearchRunner._make_discovery_adapter` в live-режиме создаёт этот же `CatalogueDiscoveryAdapter`. `_stage_discover` вызывает `adapter.discover` и переносит diagnostics; дополнительного числового лимитера в этом пути нет.

Обычная фабрика `get_search_provider` оборачивает vendor в `_ThrottleLatch`. Этот latch блокирует повторные запросы после HTTP 429 по process-wide cooldown, но не считает успешные запросы и не содержит лимита шесть. `SearchProvider` и `SearchResponse` не несут per-institution budget. Реальный `_ThrottleLatch` сохранён в воспроизведении; семь вызовов fake vendor прошли через него. Изученный Exa client ограничивает результаты, timeout и размер ответа, а не количество запросов университета.

Строгий evaluation-лимитер существует отдельно: `_ExpertBudget.before_search` проверяет общий счётчик до vendor dispatch. Он не является production guard, который создаёт `ResearchRunner`.

## Точные результаты воспроизведения

[reproduce_query_ledger.py](reproduce_query_ledger.py) вызывает реальные `_enrich`, `_identify_site`, `_discover_one`, `_add_search_results`, `discover_candidates` и `_apply`. Vendor и session — локальные fake; identity probes и не относящиеся к вопросу sitemap/navigation/confirmation/walker I/O заменены mocks. Provider factory сохраняет действительный `_ThrottleLatch`. LLM не вызывался; официальные страницы, gold и heldout не читались. Все результаты сохранены в [query-ledger-reproduction.json](query-ledger-reproduction.json).

| Сценарий | Identity vendor calls | Programme vendor calls | Все fake vendor calls | Returned trace count | Candidate ledger |
| --- | --- | --- | --- | --- | --- |
| `registry_control` | 0 | 6 | 6 | 6 | 6 |
| `seed_identity_control` | 0 | 6 | 6 | 6 | 6 |
| `identity_then_single_field` | 1 | 6 | 7 | 6 | 6 |
| `identity_then_multifield` | 1 | 6 | 7 | 6 | 6 |
| `identity_unknown` | 1 | 0 | 1 | 0 | 0 |
| `identity_provider_error` | 1 | 0 | 1 | 0 | 0 |
| `identity_plus_strict_evaluation_guard` | 1 | 5 | 6 | 6 | 6 |
| `precounted_upstream_trace_is_discarded` | 1 | 6 | 7 | 6 | 6 |

Контроль с registry и контроль с уже подходящей seed-страницей обходятся без identity-provider query и корректно тратят шесть. Эти проверки показывают, что семь возникают именно при дополнительном identity search, а не из-за случайного повторного вызова search stage.

Для strict-сценария использован действительный локальный `_ExpertBudget.before_search`. Получено: attempts=7, dispatched fake vendor calls=6, `blocked_search_queries=1`, `stop_reason=search_budget_exhausted`, `provider_failure=None`. Последняя family добавлена в retrieval `queries_run` перед вызовом seam и отвергнута wrapper до vendor; `SearchUnavailable` превращается в `Search service unavailable (exa).`. Следовательно, этот diagnostic в данном воспроизведении означает локальный лимит, а не недоступность или отказ внешнего сервиса. Общий STOP не изменялся.

`DiscoveryTrace.as_dict` дополнительно не сериализует `search_queries_sent`, поэтому raw discovery trace не позволяет восстановить этот count; поле отдельно сохранено в независимом JSON. Это ограничение observability не нужно для доказательства превышения: fake vendor фиксирует каждый dispatch независимо от candidate ledger.

## Минимальное общее исправление, без изменения caps

1. После успешного получения provider, непосредственно перед identity search, списать один запрос из identity trace. Попытка, закончившаяся provider error, тоже расходует лимит; ошибка фабрики до dispatch не должна считаться отправленным запросом. До dispatch проверять остаток. Локально заблокированный запрос нужно отличать в диагностике от реально отправленного; консервативный budget charge допустим, но нельзя представлять его как доказанный HTTP dispatch.
2. Передать исходный расход в `_discover_one` до планирования — например, через новый необязательный параметр с default=0, которым инициализируется новый trace, либо через общий trace. При раннем возврате без identity также сохранить count в candidate. При переносе failures не дублировать их. Сложение count только после `_discover_one` исправляет telemetry, но оставляет фактические семь вызовов.
3. При `SHARED_QUERY_BUDGET=True` оба planner-пути должны вычислять `remaining=max(0, 6-trace.search_queries_sent)`. Single-field передаёт `query_budget=remaining`. При нуле — не вызывать retrieval, поскольку `queries_for(budget=0)` сейчас бросает `ValueError`. Multi-field выбирает не более `remaining` intents и распределяет ровно этот остаток; coverage сообщает реальное количество назначенных subjects.
4. `_apply` сохраняет совокупный расход identity+programme; существующие requirements/scholarship guards тогда получают правильный остаток. Не повышать 6, 60 или 120 секунд; navigation/read budget не является vendor query и не заменяет этот ledger. При историческом выключенном BL-1 сохранить явно предусмотренное поведение; default остаётся включённым.

Изменение должно быть общим для всех учреждений; названия вузов, домены или семь отдельных university exceptions не нужны. План выше — предложение для владельца. Эксперт исходники не изменял, green-результат исправления ещё не заявляется.

## Независимые regressions для исправления

- Identity found через search → single-field: ровно 1+5=6 dispatch, trace/candidate count=6, отсутствие seventh attempt и budget-as-service diagnostic.
- Та же проверка для multi-field, включая больше requested fields, чем остаток: сумма распределённых budgets=5, coverage отражает реально queried fields.
- Неизвестный identity и provider error: count=1, candidate сохранён без invented programme facts; seed/registry identity без provider search сохраняет прежние шесть programme queries.
- Precharged trace переносится в `_discover_one`; прямой single/multi planner с count=1 отправляет не более пяти, а с count=6 не отправляет ничего и не вызывает `queries_for(0)`.
- При уже заполненных programme slots identity query всё равно переносится в candidate, а requirements/scholarship расходуют только оставшиеся пять. Проверить несколько программ одного университета без двойного reset.
- С тем же локальным strict wrapper исправленный production путь не достигает седьмой попытки. HTTP 429 и existing STOP продолжают останавливать запросы; не ослаблять latch или evaluation caps.

## Baseline и сохранность

Существующие тесты frozen-кода прошли: **44 passed, 0.88s** (`test_shared_query_budget`, `test_search_layer_budget_fixes`, `test_search_throttle_latch`, `test_multifield_search`); ещё **3 passed, 47 deselected, 0.86s** (catalogue outage/identity/live-timeout). Они не включают потерянный identity query в сквозной бюджет, поэтому зелёный baseline не опровергает воспроизведение. Дополнительно пройдены восемь production-path reproductions и три прямых precharged planner controls.

Все 11 изученных source SHA-256 совпадают до/после. Общий `development-STOP.json` отсутствовал до/после короткого воспроизведения. Сетевых вызовов, Git-команд, source/HANDOFF/gold/heldout изменений эксперта — **0**. Записаны только evidence и temp-artifacts в выделенной папке Round 3 Expert B. Предел доказательства — текущий непрерывный production путь; resume/retry всего pipeline, конкурентные запросы и фактический внешний spend в live captures здесь не измерялись.

## Хеши файлов

- `backend/app/catalogue/discovery.py`: `b2f057bc90831ea465c35561e710ad4cded038e88c45a629f34c2bccf226daab`
- `backend/app/adapters/discovery/live_discovery.py`: `b1d7e8f34a3cb59a3a93a1606aee191256e32f5d08e4ba71bc08d75a03521c4f`
- `backend/app/adapters/search/__init__.py`: `744352635429689ec1ce88dbc1bae19214c712d234afed568e4b9c3123dfc239`
- `backend/app/adapters/search/base.py`: `7846c074d334d87fc0e89eefdae4bb7edb9e9454fdb4ed3542bb2aede83297b8`
- `backend/app/adapters/search/intent.py`: `7eb24e254b70f2695c3ba07161773c7d047b121afd3811197908e917faf10b51`
- `backend/app/adapters/search/retrieval.py`: `ccbe3611602762f8f9ff3729bc75e76bbce7b9a04388e74ae561e996a46e1d7b`
- `backend/app/adapters/search/exa.py`: `70149ed992c6a34938585045461d77e55102815766dd85b51c0df72a5b6a4a45`
- `backend/app/adapters/requirements/web_requirements.py`: `dc1b9f81f7b6b532e0c7ac17e994dbe42af0fb91f57c7acd32900118050534b2`
- `backend/app/adapters/scholarship/web_scholarships.py`: `d1ce759b48ae5100676b9b8e80709b910f76ba9addd2f42f3eed711e45eb870e`
- `backend/app/pipeline/runner.py`: `686a6961964eb020056cba8b80f51c3cee622d2e6d62e63194b7d520e55fd71f`
- `backend/evaluation/research/live.py`: `d537aaef6527572dd6dda929e3ac235861e28a5e3ef5cd829ef11f3c71b73399`

## Хеши функций

| Функция | Строки | SHA-256 текста функции |
| --- | --- | --- |
| `backend/app/catalogue/discovery.py::CatalogueDiscoveryAdapter._enrich` | 122–140 | `299caee7cf66b084e61600a57e8f7f3157fe55229b602621e60fef0ffb7ee69d` |
| `backend/app/catalogue/discovery.py::CatalogueDiscoveryAdapter._identify_site` | 142–174 | `11086a248cffff5fdbd6f10e18f8da4ca9a2c9fdae23d37778e94612405ce9a1` |
| `backend/app/adapters/discovery/live_discovery.py::DiscoveryTrace.as_dict` | 826–846 | `a93f982633fe25bf5c6bb721614a14517df4d01d0a588e583987e73b768f51eb` |
| `backend/app/adapters/discovery/live_discovery.py::LiveDiscoveryAdapter._discover_one` | 1105–1220 | `b9b992554f6f6aff8447ff76d4e456d6ddeeaedd354355ac8d18bc0266bb02ee` |
| `backend/app/adapters/discovery/live_discovery.py::LiveDiscoveryAdapter._add_search_results` | 1417–1562 | `19b14ae2b4d5283cc700a59f54a0da5e23113ecce9a94556202b7fc7429d86fe` |
| `backend/app/adapters/discovery/live_discovery.py::LiveDiscoveryAdapter._add_multi_field_search_results` | 1564–1735 | `73292594c38582ce057a975c8054a83a1d2c967f51af9e5dfe3c5484dc7ea443` |
| `backend/app/adapters/discovery/live_discovery.py::LiveDiscoveryAdapter._apply` | 1877–1945 | `634acd19694dae09b9f5f061d19fc391af1f4121b3e288d1293c8320a3ef14d5` |
| `backend/app/adapters/search/__init__.py::_ThrottleLatch.search` | 75–88 | `f7e29d01e3337af0c0c3ea74717113c251f5fba7768c4b739e6175c06b47df29` |
| `backend/app/adapters/search/__init__.py::get_search_provider` | 91–136 | `6b15cd33146bc985bc7c203bc7231f829596bb179221abec3ebb9127ba987edd` |
| `backend/app/adapters/search/retrieval.py::discover_candidates` | 357–513 | `e37bb9d4402c96ef06157e1ea1046265d4f2eb946a867b96f87d870827a2e509` |
| `backend/evaluation/research/live.py::_ExpertBudget.before_search` | 134–145 | `5eb3826d5278637f7266f5ed8d9d4ef7289cd4c4dc03433b6bb7c04aba0ed404` |
