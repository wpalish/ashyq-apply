# Отклонённые значения в диагностике: native proof и внешний proposal

Статус: **EXTERNAL_PROPOSED_NOT_APPLIED**, 9 октября 2026. Финальная одинаковая пара из шести test bodies: **OFF 5 semantic FAIL / 1 обычный контроль PASS; ON 6 PASS**. Ruff check/format на 13 предложенных файлах PASS; mypy на изолированной копии 154 app source files PASS. Primary, Git, текущий baton и release не изменялись. Это пакет для независимого review и отдельного successor task; он не разрешает применение.

Основа — executable `5b48d5e43d0ba7247c850ba4556584ab7415a986`, current exact20 manifest `22ca29438dadb49deb393941ed6d67624301418118f0dd501b63949a41a2a1df`, предыдущий DESIGN_ONLY ready `d3878cfcfa11415a51413627f735bc26a8d878daafe3eb314a02e748e021787c`. Все 154 исходных app `.py` и current20 совпали до/после. HANDOFF изменил root во время работы: это ожидаемый context drift его Draft/release, отдельно записанный в `source-pins-after.json`; whole-tree/HEAD неизменность не заявляется. Текущие sections HANDOFF прочитаны; гигантская историческая часть целиком не reviewed.

## Выполненные вызовы

| Группа | Реально вызванная ветвь | Исходный дефект / результат ON |
|---|---|---|
| P1 | Fetcher.get initial email URL | URL/warning сохраняли sentinel; ON diagnostic origin, typed refusal/status None; cache/DNS/request spies 0 |
| P2 | Redirect loop, fake resolver, MockTransport | Warning/final_url сохраняли poison hop; ON exact безопасный initial URL. Два resolver calls относятся к initial source, один mocked HTTP; destination calls 0, status None |
| P3 | DiscoveryIntent и exception constructor | str/repr/args содержали rejected value; ON field/reason и bounded explanation. ON выполняет пять reason branches; OFF останавливается на первом email retention assertion |
| P4 | Пять adapters, catalogue lead и catalogue document, sitemap и confirmed-program failure; runner recorders | Original input снова попадал в errors/PageOutcome/retry/run attrs. ON безопасная identity, no privacy retry, typed partial. Девять refusal branches в группе |
| P5 | Actual runner error handler/_audit/Session.add и Worker.execute/JobStore.fail | Raw exception chain попадала в text/JSON logs, errors/audit/fail argument; ON typed reason без exc_info chain, FAILED/rethrow/lease token сохранены |
| P6 | Ordinary CMS/public query/404; queries/public fields; ordinary error, lease/cancel | Exact ordinary URL/status/reason/retry, обычный traceback/audit/rethrow, budget6/sharedTrue/reserve1; Mathematics остаётся; lease no-write, cancellation typed exit — PASS в обеих копиях |

`scope-matrix.json` содержит branch counts и exclusions. P4 adapters каждый сохранил pages_checked=1/pages_failed=1, claims=[]; documents/awards/confirmed programmes пусты. Refusal не является доказательством отсутствия программы/требований. Catalogue-level privacy refusal теперь возвращается до `js_no_program_list`: непрочитанный каталог нельзя описывать как прочитанный список без программ. Candidate trace сохраняет число рассмотренных leads и безопасную diagnostic identity; это не новый programme/Claim.

**P5 — injected actual QueryPrivacyError escape**, полученный настоящим DiscoveryIntent в подставленном stage. Текущие `_public_requested_fields`/direct discovery catches уже suppress rejected value; их непосредственная query→persisted-run утечка не утверждается. Проверена реальная обработка исключения при таком escape. Session.add/JobStore.fail заменены memory spies, `_save` выключен: доказаны native assignments и параметры sinks, **не SQL durability/API roundtrip**. Root full с двумя DB в другой задаче этого доказательства не добавляет.

## Почему нужны эти 11 source paths

| Path после `backend/app/` | Необходимая граница и native proof |
|---|---|
| adapters/fetching.py | P1/P2: убрать rejected URL/hop из log/result; общие diagnostic/retry helpers |
| adapters/search/intent.py | P3/P5: безопасный constructor с allowlisted field/reason; raw value не принимается |
| adapters/cost/web_costs.py | P4: original costs_url reintroduction в errors/PageOutcome/retry |
| adapters/requirements/web_requirements.py | P4 actual verify failure: source URL diagnostic; прежний conditional retry unchanged |
| adapters/documents/web_documents.py | P4 actual _from_page failure: original URL/error/retry/PageOutcome; reason теперь сохранён также в detail |
| adapters/government/web_government.py | P4 actual post_study_work failure: original URL/error/PageOutcome |
| adapters/scholarship/web_scholarships.py | P4 actual find с allow_search=False: original failure URL/retry/PageOutcome |
| adapters/discovery/live_discovery.py | P4 actual sitemap/confirm failure trace. Recover-pending/nav replacements проверены source-only, **не native coverage** |
| adapters/discovery/catalog_walker.py | P4 actual lead/catalogue refusal: outcomes/candidate trace; no no-list fallthrough после отказа |
| pipeline/runner.py | P5 actual error/audit sink: для QueryPrivacyError без chained traceback; generic operational errors unchanged/P6 |
| jobs/worker.py | P5 actual fail argument/log sink: тот же typed branch, прежний fail/lease token/control flow |

Три общих Fetcher helpers централизуют diagnostic identity и privacy retry. Обычный URL остаётся exact. Для **уже найденного detector** rejected URL сохраняется только структурно безопасный origin без userinfo/path/query/fragment; если origin не получается, bounded placeholder. Это diagnostic identifier, не проверенный официальный источник, не URL для повторного чтения и не DNS verification. Для poisoned hop остаётся exact safe initial URL. Новая ordinary-URL эвристика, изменение find_pii/assert_no_pii, hash rejected value, admission/Claim/schema/default/budget/TypeSafe threshold изменения отсутствуют. AST checks для find_pii/assert_no_pii/_refusal/query rendering/audit rendering/heartbeat совпали; остальные 143 app files unchanged.

Два test paths: новая six-group `backend/tests/test_rejected_diagnostics.py` (байты совпадают с финальным native harness) и существующий `test_fetch_pii_hops.py`: одна obsolete assertion `final_url == hop` заменена на exact safe ENTRY_URL и усилена no-token assertion. Старый guard no-hop-request/counter/content/reason не ослаблен. Existing test body здесь **NOT RUN**; независимый peer/root должен проверить его в последующей задаче. New tests без proof env не пишут observations; основная test логика та же.

## Логи, ограничения и история

`logs/off-issued.log`, `on-issued.log`, execution JSON, JUnit и P1–P6 observations — финальная same-body пара, test SHA в receipt. Fake values только `.invalid`, никаких реальных данных. Raw OFF сохранён намеренно как defect proof. Native guard: DNS/connect/listen/DB/child_process **0 в каждой из 9 issued native executions**; provider/model/worker process/ports/CUA — NOT RUN. Asyncio local socketpair не блокировался; guard запрещает внешние connect/listen/DNS. HTTP только MockTransport, DNS policy только stub.

Всего реально issued: **9 executions × 6 groups = 54 group executions, 28 PASS / 26 FAIL / 0 pytest errors**. Это authoring history, а не 54 независимых security cases. Ранний P2 FAIL был ошибкой harness count assumption (safe initial resolves twice), не privacy-failure; сохранён в `logs/off-attempt1`. Исправленные пары в paired-attempt2–4 сохранены. Expanded ON P4 обнаружил дополнительный raw `js_no_program_list` residual; raw есть в paired-attempt3. Тогда также был исправлен missing FetchOutcome import после lint. Последняя пара повторена после финального formatting всех предложенных байтов. P3 OFF завершается на первом retention assertion, поэтому четыре дальнейших reason controls выполнены ON-only; P6 independent ordinary controls выполнены в обеих копиях. Ранние версии harness до каждого authoring edit отдельно не sealed; эти ранние логи — историческое свидетельство, не exact reproducibility claim. Канонические final bodies/source pinned.

Ruff initial failures/import ordering/literal style сохранены в lint-before.log; `imports-literals` менял только I/C408, затем ClassVar/format. Build-script промежуточная ошибка неверного import anchor была authoring failure, исправлена до финальной пары. Сам builder — provenance recipe; окончательные authoritative bytes — `proposed/` после recorded formatter. Никаких скрытых retries внешних систем.

Изолированные OFF/ON snapshots содержат только app `.py`; .env, private data, DB, dependencies, corpus/registry assets не копировались. Guard blocks SQL even though normal model/db imports construct an engine. Поэтому successful content extraction/registry/provider/research journeys не входят в scope. Generated mypy/pytest caches не входят в sealed selection. Existing dependencies использовались read-only; ничего не установлено.

Следующий шаг только у root после текущего Draft/release и нового HANDOFF task: независимый actual native peer/negative controls → qualified минимальный apply → fresh source pins/doctor/core/full. Реальная persistence/API negative проверка требует отдельного разрешённого synthetic DB scope. Пакет не доказывает все PII detectors, историческую очистку, backup deletion, production, provider privacy, compliance или overall security.
