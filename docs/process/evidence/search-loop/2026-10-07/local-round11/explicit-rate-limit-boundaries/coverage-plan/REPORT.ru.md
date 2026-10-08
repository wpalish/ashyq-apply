# Конечная подготовка интеграционных тестов RATE_LIMITED

Подготовка, не принятие дизайна: 13 собственных копий текущего source/test совпадают с оригиналами. Тесты, импорт приложения, прототип и reset здесь не запускались. Готового proposal manifest A пока нет. Дефект OFF доказан отдельно в bd0f4467 пакете.

| Реальный native файл | Переиспользуемое покрытие | Недостающий seam |
|---|---|---|
| test_search_throttle_latch.py | Shared HTTP429, обычный500, isolation, expiry, reset | None/RATE_LIMITED metadata и оба map |
| test_exa_mcp.py | McpServer/MockTransport, metaTrue, внутренний retryTrue/False, восстановившийся второй ответ, HTTP429 | Реальный factory latch вокруг неизменного клиента |
| test_search_layer_budget_fixes.py | 429 cutoff, 500 continue, single/multi Live caller | Typed None/RATE cutoff и точные diagnostics |
| test_identity_query_ledger.py | on_query_attempt, local refusal не HTTP dispatch, shared budget, error/cancel | Typed cutoff без заряда оставшихся семей |
| test_hybrid_retrieval.py | Успех, обычный отказ, query budget | Неизменность результатов и не-rate ошибок |
| conftest.py | Autouse test-state reset API | Очистка двух map только в изолированном pytest |

Точные существующие имена и строки — reusable-tests.json. test_search_retrieval.py в repo отсутствует.

Шесть ограниченных дополнений:

1. Реальный ExaMcpSearchProvider через get_search_provider и MockTransport, без замены search/_search_once/_post. Вышедший отказ сохраняет status=None и reason IS RATE_LIMITED. Повторный, заранее созданный и заново созданный adapter не делают handshake/tools. Разделять transport calls и попытки query. Native RATE_LIMIT_RETRY=True даёт два tools/call до вышедшего отказа; изолированный False — один. Разрешённый first-rate/second-success не должен создавать latch. Существующий retry/default не менять; outer latch не доказывает остановку первого внутреннего ответа.
2. Сырая строка reason='rate limited' и похожий arbitrary message не latch/cutoff. SearchFailureReason — StrEnum: == со строкой может дать ложное разрешение; нужен тип/идентичность. TIMEOUT/TRANSPORT/500/success остаются прежними.
3. Совпавший активный provenance stamp сохраняет None/RATE. Expiry и новый отказ заменяют старые metadata; проверить HTTP429→None/RATE и обратно. Увеличенный/несовпавший until и stale origin не считаются текущими metadata. Legacy float-only fallback квалифицировать отдельно: он не может превращать совпавший текущий None/RATE в выдуманный429. Точная fallback policy до sealed proposal не одобрена.
4. Provider isolation и reset_search_throttle обоих map развивают существующие тесты с fake clock/isolated state. Это не primary reset или persisted STOP операция.
5. Реальный discover_candidates и on_query_attempt: typed отказ = throttledTrue, queries_run/callback1; оставшиеся запланированные семьи не оплачиваются. Новая локально блокированная попытка семьи может быть1 при0 vendor dispatch. Telemetry не утверждает HTTP dispatch. Переиспользовать identity+programme shared-budget controls, включая явный legacy-off.
6. Оба Live caller пути: single и multi _add_search_results прекращают запросы после1. search_failures сохраняет известный HTTP429 или typed-rate без статуса. search_limitations объясняет общий rate stop, не отсутствие программы или исчерпанный кредит. Для None/RATE никакого выдуманногоHTTP429; для настоящего429 сохранить известный status в failures плюс общий stop в limitations, не просто удалить старое утверждение.

Область review — только exact sealed source. Client/retry/SP/Fetcher/caps остаются авторитетными. Эти ephemeral process maps не доказывают межпроцессную/долговечную глобальную блокировку, качество поиска или контроллерный sticky STOP. Контроллерная граница STOP отдельно.

Никакой большой дублирующей матрицы: расширить перечисленные реальные fixtures. Существующие realMCP parser/retry и 429/ordinary controls должны пройти без ослабления ожидаемых данных.

Две ошибки подготовки не были тестами приложения: первая AST индексация предположила неверное имя test_it_respects_the_query_budget (preliminary JSON сохранён), затем поиск line по startswith не учёл indentation и дал StopIteration до финальных файлов. Итоговый AST index использует фактический test_the_query_budget_is_respected. Никаких source/prototype/app действий они не выполнили.
