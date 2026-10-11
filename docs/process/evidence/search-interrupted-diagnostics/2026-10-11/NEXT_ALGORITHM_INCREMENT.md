# Следующее исправление алгоритма: подтверждённая страница до позднего поиска

## Начальная точка
Тестируемый диагностический код abcedf46. В единственном разрешённом живом Groningen на 7c8e23a7 Computing Science прочитана успешно, но кандидат не возвращён до общего deadline. В исходном `_discover_one` `_confirm_programs` затем `_walk_catalogs` затем `_add_search_results`, а `trace.selected`/`_apply`/return выполняются только после них. `_stage_discover` сохраняет кандидатов только после возврата всего `discover`. Один поздний await может оставить весь университет без опубликованного результата.

## Конкретная проверяемая цель
Сохранить уже проверенную официальную страницу как частичное наблюдение до вспомогательных этапов, без утверждений про intake, eligibility, fees, funding или deadline. Наличие страницы не является готовым ProgramResult. Не превращать cancellation или потерю lease в успешное завершение Job.

## Предлагаемая следующая работа (ещё не реализована)
1. Добавить отдельную типизированную коллекцию подтверждённых programme observations, заполняемую сразу после successful Fetcher + same-site + classifier + profile guard. Сохранять identity владельца, canonical/final URL и точные границы подтверждения. Поле не должно содержать applicant PII, HTML или секреты.
2. Перед длительными auxiliary/search этапами сохранять наблюдение через существующий source recorder / fenced Job checkpoint. Перед каждой записью проверить отмену и актуальный attempt token. Нельзя писать за новый worker после LeaseLost или после пользовательской отмены.
3. Разделить UI «подтверждена страница программы / условия ещё проверяются» и окончательный верифицированный результат; никакой оценки совместимости без фактов.
4. Измерить raw provider URLs, очищенные уникальные URL, очередь programme confirmation и исходы page-type/degree/subject фильтров. Дедупликация должна учитывать category и canonical URL, сохраняя provenance; cached requests также могут расходовать action budget, это не бесплатные чтения.
5. Проверить offline native fake-provider/Fetcher сценарии: медленный auxiliary после подтверждения, неверный уровень, redirect offsite, недоступная страница, lease сменился перед записью, user cancel, перезапуск worker. Завершённый старый результат byte-compatible.
6. Порядок sitemap/navigation/search и experimental flags пока не менять. Их off/on/off оценка требует отдельного живого разрешения на одинаковую пару, текущий one-case grant исчерпан.

## Обязательные ограничения
120 секунд / 60 чтений / 6 запросов для алгоритма; robots, egress, privacy, response-size и исходные STOP сохраняются. Не использовать эталонные/heldout данные для настройки. Production и main не изменены. Сначала закрыть текущую диагностику свежими native gates и отдельным зависимым Draft PR; затем согласовать точные source paths следующего increment в HANDOFF.
