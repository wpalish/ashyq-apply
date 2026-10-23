# Offline code review: section_scope и requirements integration

Дата: 2026-10-07. Область: `backend/app/adapters/requirements/section_scope.py`, изменённые входы в `web_requirements.py`, независимые синтетические fixtures и `backend/tests/test_requirement_section_scope.py`. Source/git/gold/HANDOFF не изменялись. Сеть не использовалась. Реальный university replay и общий backend gate не проверялись этим экспертом; их результаты не являются независимым доказательством этого review.

## Вывод

В просмотренной финальной версии оставшихся существенных замечаний не найдено. Независимые проверки: 28 helper tests passed и 20 production-adapter offline fixtures passed. Обнаруженное ранее смешение degree-level qualifiers и самостоятельных audiences исправлено и проверено red/green. Ошибки mixed headings, отрицаний и выхода heading scope из таблицы также исправлены.

Review привязан к следующим файлам:

| Файл | SHA-256 |
|---|---|
| `backend/app/adapters/requirements/section_scope.py` | `8b2c8da32b7595f95aab817d97b90f7900aca93bab21060499a39ecfc83a2f79` |
| `backend/app/adapters/requirements/web_requirements.py` | `dc1b9f81f7b6b532e0c7ac17e994dbe42af0fb91f57c7acd32900118050534b2` |
| `backend/tests/test_requirement_section_scope.py` | `cea0cf4a4859b2f5a3de0f61b882ec4b18b30fa08ef01158637b505e5753547b` |

Все три hashes финального adapter smoke до и после совпадают. Финальный raw output: `section-scope-final-adapter-smoke.json`. Исторические red proofs выполнены на предшествующих стабильных helper `4928c6ed723f1b326a30f971a53f3c9d833a8b9b11e6b5d7120c7c87462035b0` и `0dffa225a9d334968412ef1085ce3b467c4f794febeb15c9c7750da963c5177b`; они явно отделены от финального green.

## Исправленный [P1]: Degree-level qualifier не является второй аудиторией

На промежуточном SHA `0dffa…`, `section_scope.py:83`–`97`, `_FULL_DEGREE` искал degree-level слова; `joint` становился истинным, когда между первой non-degree фразой и любым degree token найден conjunction. Дальний token `master` позволял принять союз, который соединяет bachelor/master уровни внутри одной exchange-аудитории.

Независимые red-примеры для промежуточного SHA `0dffa…`:

| Heading | Ожидание для first-degree | Получено helper |
|---|---|---|
| `Exchange students (bachelor and master level)` | Исключить exchange 5.5, сохранить последующий Bachelor 6.5 | `excluded_sections=0`; оба значения сохранены |
| `Exchange programmes for bachelor and master students` | Исключить exchange 5.5, сохранить последующий Bachelor 6.5 | `excluded_sections=0`; оба значения сохранены |
| `Undergraduate exchange and visiting students` | Исключить exchange/visiting 5.5, сохранить последующий Bachelor 6.5 | `excluded_sections=0`; оба значения сохранены |

В третьем примере первый распознанный non-degree match — `visiting students`: `exchange` перед `and` не входит в текущий match. Поэтому degree-level adjective `Undergraduate` и союз до visiting выглядят как две аудитории.

Историческое red-доказательство helper: `section-scope-final-helper-check.json` (название сохранено, внутри указан промежуточный SHA). Более ранний полный adapter smoke на стабильном SHA `4928…` подтвердил, что первый пример действительно создавал `ielts_min_overall=5.5` с неизвестными всеми scope-полями, а не только сохранялся в промежуточной DOM-view. Источник — fixture admissions page, classification guards не отключались. Доказательство: `section-scope-audience-qualifier-smoke.json`.

Финальная версия не считает дальний degree token отдельной audience, если между ним и non-degree фразой уже есть degree-level token, а exchange в `exchange and visiting` становится первым non-degree match. Все три exchange-only heading дают unknown для IELTS; с действующим Bachelor sibling дают 6.5. Настоящие `Bachelor and exchange programs`, `Degree-seeking or exchange students` и degree/non-degree lists сохраняют 6.5. Это проверено отдельными production-adapter assertions на финальном SHA `8b2…`.

## Что независимо подтверждено

- Оба table-входа (`web_requirements.py:407`–`409`, `469`–`473`) получают одну filtered HTML view. Exchange table не попадает в `tabled/answered` и не подавляет действующий Bachelor prose.
- `builder.page_text` и classification сохраняют исходную страницу (`340`–`365`); prose readers используют отдельные regions (`475`–`485`). Fixture с `IELTS overall` до вырезанного раздела и `6.5` после него не создаёт claim.
- Локальные scopes для aside/nav/header/footer/table/td/th предотвращают выход exchange heading из контейнера. Синтетический table-cell exchange heading перед основным IELTS 6.5 сохраняет основной claim.
- Нет hardcode университета/акронима, новых provider queries или изменения fetch/follow caps в просмотренной интеграции.

## Независимые checks и их границы

**Финальный green SHA `8b2…`:** 28 selected helper tests passed, 10 adapter pytest tests deselected; вместо последних выполнены 20 самостоятельных adapter fixtures. Использован обычный `WebRequirementsAdapter`, `Fetcher(offline=True)` и candidate с исчерпанным `DEFAULT_QUERY_BUDGET`. Provider дополнительно запрещён in-process assertion; попыток 0. Проверены normal и unknown-classified fallback table routes, exchange table → Bachelor prose, table-local scope, mixed/negated controls, все четыре local chrome containers, три qualifier-only и три qualifier + Bachelor sibling, fragment continuity и exchange-only unknown. Все английские claim excerpts отдельно проверены `is_verbatim_excerpt` против исходного `readable_text(html)`. Hashes helper/integration/test-file до/после одинаковы. Raw output: `section-scope-final-adapter-smoke.json`.

Ниже сохранена история red/green; её промежуточные failures не относятся к финальному SHA:

1. **8 adapter fixtures, стабильный helper SHA `4928…`.** Применялся обычный `WebRequirementsAdapter`, `Fetcher(offline=True)`, fixture programme → English link, candidate с уже исчерпанным `DEFAULT_QUERY_BUDGET`. Вызов provider additionally запрещён in-process assertion; попыток 0. Проверены exchange table → degree prose, normal table route, unknown-classified fallback table route, local table scope, mixed `or`, negation, разорванная фраза и exchange-only page. Все восемь дали ожидаемые IELTS values/unknown. Выход: `section-scope-adapter-smoke.json`.

2. **2 adapter qualifier fixtures, стабильный helper SHA `4928…`.** Та же offline схема и production guards. Оба exchange-only headings пропускают 5.5. Выход: `section-scope-audience-qualifier-smoke.json`.

3. **3 helper qualifier fixtures, стабильный helper SHA `0dffa…`.** Hash до/после одинаковый. Все три сохраняют 5.5; действующий последующий 6.5 тоже сохранён. Выход: `section-scope-final-helper-check.json`.

4. **Existing readers:** `tests/test_document_ir.py` и `tests/test_structured_extraction.py` — 20 passed. **Selected helper tests:** explicit audience / peer-heading / joint+negative controls / table-local scope — 25 passed, 1 failed (`Undergraduate exchange and visiting students`). Adapter pytest целиком здесь не запускался: reused `_run` fixture с неистраченным query budget может достичь configured topic provider; вместо этого использован самостоятельный безопасный adapter smoke. Tests выполнялись с отключёнными pyc/pytest cache и временными файлами только в expert_b.

5. Исходные расходы, intake-state, fees и admission-route readers продолжают использовать original text. PDF остаётся без HTML heading-filter. Это границы текущего исправления, а не доказательство audience isolation для всех типов данных. Не следует описывать узкий language/requirements fix как универсальную scope-проверку всех claims.

Предшествующие замечания и дизайн review сохранены отдельно в `scoped-audience-filter-review.ru.md`. Финальный вывод относится только к указанным SHA и проверенной области; общий backend gate остаётся отдельной проверкой родительского агента. Дальнейшие source changes требуют новой проверки.
