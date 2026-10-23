# Round 2: независимая офлайн-диагностика Wits/Caltech и итоговое review SI-1

**Подтверждена ранняя потеря на проверке личности официального сайта.** В обоих сохранённых запусках `_enrich` завершался до поиска программ: `_probe_site` не находил полное имя в title/H1 и не принимал доступные сведения о владельце сайта. Общий дефект остановки в поиске программ, ранжировании или catalogue walker этими случаями не доказан: данные этапы не были достигнуты.

**Окончательный SI-1 проверен без оставшихся существенных замечаний в границах этого изменения.** Два исходных замечания Expert B исправлены и сохранены отдельно в [original-findings.ru.md](original-findings.ru.md). Эксперимент по умолчанию выключен. Проверка идентичности сайта открывает следующий этап исследования; она сама по себе не подтверждает Bachelor Computer Science, требования, стоимость или пригодность для набора 2027 года.

## Проверенные байты

- `backend/app/catalogue/discovery.py`: `b2f057bc90831ea465c35561e710ad4cded038e88c45a629f34c2bccf226daab`
- `backend/evaluation/research/live.py`: `d537aaef6527572dd6dda929e3ac235861e28a5e3ef5cd829ef11f3c71b73399`

Обе суммы проверены до/после независимых воспроизведений и перед сохранением отчёта. Хеши остальных изученных модулей, файлов captures, retained DB и сырых cached meta/body включены в [diagnosis-and-replay.json](diagnosis-and-replay.json). Хеши исходных функций из `discovery.py`:

| Функция | Строки | SHA-256 текста функции |
| --- | --- | --- |
| `_site_branding` | 34–64 | `ae620248f47641c7332e101cd9de3c1785101efc5be87fd1043056337e34555b` |
| `_enrich` | 122–140 | `299caee7cf66b084e61600a57e8f7f3157fe55229b602621e60fef0ffb7ee69d` |
| `_identify_site` | 142–174 | `11086a248cffff5fdbd6f10e18f8da4ca9a2c9fdae23d37778e94612405ce9a1` |
| `_probe_site` | 176–253 | `27ccbb28cb50abe8924365f08aeeb79ece9b5f3c77ad86af73b4b5d2585370a7` |

## Самый ранний подтверждённый сбой

В четырёх captures `registry_entry` отсутствовал. `_enrich` вызывал `_identify_site`; после отсутствующего результата добавлял `Official website identity not established ...` и возвращал исходного institution candidate без вызова `_discover_one`.

У Wits запись содержит `University of Witwatersrand` без отдельного алиаса `Wits`. Успешно прочитанная главная страница имеет title `Home - Wits University` и H1 `Straight From the ‘Gram`; полное имя в них отсутствует. При этом локальный footer-параграф содержит непрерывную строку `Copyright © 2026 - University of the Witwatersrand, Johannesburg.`. Необязательный отдельный артикль `the` объясняет отличие от имени в записи. Страница 200 находится на том же официальном сайте.

У Caltech запись содержит `California Institute of Technology` и алиас `Caltech`. Успешная главная www-страница имеет title `Home - www.caltech.edu` и H1 `Caltech Homepage`. В title/H1 нет полного имени и отсутствует слово `university`, `college` или `institute`, необходимое старому acronym-пути. `og:site_name` имеет точное полное имя `California Institute of Technology`. Это локальные bytes сохранённой официальной страницы, а не search snippet.

`LiveDiscoveryAdapter._discover_one`, sitemap/navigation, walker и programme search не запускались: `selected={}`, `manual_seeds={}`, sitemaps=0, navigation=false, walker catalogs=0/candidates=[]/confirmed=0. Сформированных программ и verified claims в изученных результатах нет. Никакая общая или не относящаяся к программе страница не повышена до доказательства программы.

## Почему было 3/4 чтения и один запрос

`_identify_site` ограничен двумя seed-подсказками, одним поиском идентичности (`max_results=3`) и максимум тремя уникальными возвращёнными корнями. `_probe_site` приводит корни к HTTPS. Seed содержит `http://www...`, а поисковый корень — `https://www...`; строковое сравнение исходных подсказок не исключает это повторное чтение. Вызов Fetcher учитывается строгим бюджетом даже при cache hit.

| Capture | Университет | Fetcher calls | Search queries | elapsed ms | Institution pages checked | Institution failures |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | Wits | 3 | 1 | 11970 | 3 | 0 |
| baseline | Caltech | 4 | 1 | 14702 | 4 | 2 |
| repeat | Wits | 3 | 1 | 9529 | 3 | 0 |
| repeat | Caltech | 4 | 1 | 14220 | 3 | 1 |

Во всех четырёх budget receipts отсутствуют `stop_reason` и `provider_failure`; ограничения 60/6/120000 не исчерпаны. Остановка соответствует локальному ограниченному алгоритму поиска идентичности. Остаток общего бюджета сам по себе не доказывает дефект общего критерия завершения поиска.

У Caltech bare-domain чтение недоступно из-за `robots.txt unreachable (ConnectError)` и политики RFC 9309. В baseline дополнительный catalogue-root ответил 403. Эти ограничения сохранены; они не объясняют отклонение успешно прочитанной www-главной страницы. В repeat глобальные четыре Fetcher calls включают Wikipedia-root, который не относится к institution-specific `pages_checked=3`. Это различие счётчиков не ошибка доказательства.

## Минимальное независимое воспроизведение

[diagnose_identity.py](diagnose_identity.py) вызывает действительные `_enrich`, `_identify_site` и `_probe_site` текущего кандидата. Retained DB открываются read-only/immutable; исходные страницы отдаются строго из сохранённых cache bytes, ошибки доступа воспроизводятся из receipts. Новый proof хранится только в памяти. `_discover_one` заменён маркером входа, возвращающим пустой набор программ.

| Retained case | Off: Fetcher/query, вход в следующий этап | On: Fetcher/query, вход в следующий этап | Новое основание |
| --- | --- | --- | --- |
| Wits baseline | 3/1, нет | 1/0, да | `homepage_copyright_owner` |
| Wits repeat | 3/1, нет | 1/0, да | `homepage_copyright_owner` |
| Caltech baseline | 4/1, нет | 2/0, да | `homepage_og_site_name` |
| Caltech repeat | 4/1, нет | 2/0, да | `homepage_og_site_name` |

Список корней для stub search восстановлен синтетически из наблюдаемых receipts. Текст и порядок исходного ответа Exa не сохранены, поэтому воспроизведение не заявляет точного восстановления ответа провайдера. В каждом прогоне candidate programmes остаются пустыми: подтверждён только переход через исходный identity gate. Код воспроизводится из backend с существующим Python окружением; сетевой Fetcher или provider не используются.

## Строгая форма SI-1 и проверки ложной идентичности

Новый путь работает только после провала старого title/H1-пути, при включённом флаге, существующем `uni.domain`, совпадающем registrable domain исходной подсказки и успешном ответе с допустимым same-site redirect. Он не разрешает произвольный host, найденный поиском.

`og:site_name` должен целиком совпадать с известным сырым именем или алиасом после нормализации; сохраняются порядок и границы токенов, игнорируется только отдельный `the`. Родительские квалификаторы имени не удаляются через legacy `canonical_name`.

Для copyright читаются только отдельные `footer p`/`footer small` до 300 символов. Строка должна начинаться с явного `Copyright`/`©` (допустимы `(c)`, год/диапазон и разделитель); имя владельца должно целиком совпадать с известным полным именем. Каждый фрагмент после запятой, `|` или `;` должен целиком совпадать с уже известным городом/страной этого университета. Произвольные юридические суффиксы, дальнейшие сущности, упоминания чужих университетов, текст body и copyright вне footer не принимаются. Подтверждение сохраняет непрерывный исходный параграф или точное значение метаданных.

[branding-owner-acceptance.json](branding-owner-acceptance.json) содержит **20 независимых проверок**: 15 helper-сценариев и пять проверок действительного `_probe_site`. Положительные — точный владелец, необязательный артикль и известная география, точный OG. Отрицательные — Foundation/Inc после разделителя, Foundation после известного города, чужой владелец с упоминанием цели, body-only/не-footer, OG с лишними словами или другим порядком, сырое квалифицированное имя `(Foundation)`, чужой host и cross-site redirect. Дополнительно исходный known-title proof полностью совпадает off/on и не приобретает `identity_basis`.

В CLI проверены default=false, передача дочернему процессу и запись булевого `site_branding_identity` как в обычном capture, так и при существующем STOP до запуска. [cli-prestart-stop-acceptance.json](cli-prestart-stop-acceptance.json) фиксирует два независимых off/on-прогона: children=0, observations=0, STOP сохранён, конфигурация точная. Settings, subprocess и pipeline SHA в этом воспроизведении синтетические; Git и provider не вызываются.

## Результаты проверок и границы

- Текущие branding-тесты: **18 passed, 32 deselected, 1.22s**.
- CLI forwarding/config regression: **2 passed, 16 deselected, 0.78s**.
- Независимые ownership/probe controls: **20/20**.
- Независимый pre-start STOP replay: **2/2**.
- Четыре пары retained-page off/on stage-entry replay: **4/4**.

Это review узкого SI-1, а не подтверждение всей launch readiness. Полный gate владельца не воспроизводился этим экспертом. Дальнейшая полнота programme retrieval и сведения для набора 2027 остаются неизвестными до отдельного авторизованного измерения downstream. Сохраняются реальные ограничения доступа Caltech.

Сетевых/provider вызовов эксперта в Round 2: **0**. Исходники, четыре retained DB и общий `development-STOP.json` сохранены: общий STOP отсутствовал до/после проверки. Gold/heldout не читались и не менялись. Записаны только файлы в выделенной папке Expert B и её тестовые temp-artifacts.
