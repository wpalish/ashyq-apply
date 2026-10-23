# Поиск: сохранение прерванной диагностики — 11 октября 2026

## Подтверждённый дефект
Один разрешённый холодный Groningen на7c8e23a7 достиг119033мс после35Fetches/6query seam attempts.32из34завершённых чтений успешны. Официальная Computing Science открылась и проходит текущий page-type/degree/subject фильтр, но discovery не вернул кандидата до отмены. Job остаётся незавершённым. Нельзя считать отсутствие результата отсутствием программы.

## Исправление этого PR
Прерванные трассы сохраняются отдельно от завершённых. Catalogue переносит наблюдённый внутренний trace на исходного владельца. Canary сообщает discovery_trace_complete=false только для неполного префикса; формат завершённых старых отчётов не меняется. CancelledError/RunCancelled/LeaseLost продолжают распространяться; кандидат и успешное завершение Job не создаются.

## Проверка на executable abcedf46
-43целевых теста PASS.
-Ruff/format/mypy363 PASS;frontend typecheck/lint/unit433/build PASS,2старых lint warnings.
-Полные SQLite/PostgreSQL:по4531уникальному одинаковому тесту,0fail/error/skip;95.4334/95.4268%coverage, threshold92unchanged.
-Все source pins до/после совпадают;outside network attempts/guard startup failures0; собственные временные кластеры удалены.
-Native migrated demo seed: Groningenfirst, UBC OUT_OF_BUDGET; providersnone, сетьOS_DENIED.
-Исходный полный прогон4529PASS+1FAIL и PGNOT_RUN сохранён; совместимость repaired отдельным новым прогоном. Два preflight отказа на пустые owned generated dirs сохранены как NOT_RUN; удалены только пустые exports/httpcache.

## Границы готовности
Это исправление диагностики. Подтверждённая страница ещё не сохраняется как частичный пользовательский результат до поздних стадий.2027intake/гражданство/финансирование/цена/дедлайн не подтверждены. Качество по эталону, полнота фактов и production authenticated E2E не измерены. Main и deployment не менялись. Старые STOP/heldout/секреты/пользовательские данные не тронуты. Независимая privacy приёмка и reset safety work остаются PENDING/STOPPED.

## Доказательства и следующий шаг
[EVIDENCE_INDEX](evidence/search-interrupted-diagnostics/2026-10-11/EVIDENCE_INDEX.json) содержит SHA/размер каждого выбранного оригинала. [Пять пунктов](evidence/search-interrupted-diagnostics/2026-10-11/FIVE_POINTS_STATUS.md), [причина потери](evidence/search-interrupted-diagnostics/2026-10-11/SEARCH_FINDING.md), [следующее изменение алгоритма](evidence/search-interrupted-diagnostics/2026-10-11/NEXT_ALGORITHM_INCREMENT.md). Новый живой прогон не запускался после исчерпания одноразового разрешения.
