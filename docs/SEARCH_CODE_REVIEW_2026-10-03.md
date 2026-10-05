# Почему поисковик не работает: построчный разбор кода

Дата: 2026-10-03. Ветка `arena/01a0f379-ashyq-apply`, код = `b145da2` (PR #40).
Метод: чтение `backend/app/adapters/search/**` и `live_discovery.py` + семь прогонов
зондов на копии дерева (`/tmp/p311`, Python 3.11 с снятым PEP 695). Каждое
утверждение ниже подтверждено выводом зонда, а не рассуждением.

---

## 0. Что работает правильно (чтобы не чинить это заново)

Зонд 2 прогнал `queries_for → prefilter → rank_candidates` на реалистичной
выдаче индекса (лента новостей, MSc-страница, реальная BSc-страница):

```
rejections={'not_a_programme_page': 6, 'wrong_degree_level': 6, 'duplicate': 10}
ranked (2):
   12.060 https://www.rug.nl/bachelors/computer-science
          signals=('strong_alias_in_title','degree_in_title','registry_seed_host')
    3.000 https://www.rug.nl/bachelors/artificial-intelligence
          signals=('related_field_only','degree_in_title','registry_seed_host')
```

Новостная лента отсеклась по пути, MSc — по уровню степени, дубликаты схлопнулись,
правильная страница встала первой с объяснимыми сигналами. **Сама поисковая
машина работает.** Проблема не в ней.

---

## 1. ГЛАВНАЯ ПРИЧИНА: поиск выполняется до проверки, есть ли куда положить результат

`live_discovery.py:1436-1448` — порядок операций в `_add_search_results`:

```python
report = await discover_candidates(provider, intent, fetch=read, top_k=10)   # 6 запросов + handshake + 3 хопа
...
pages = selected[PageCategory.PROGRAM_PAGE]
if RECOVER_SEARCH_CANDIDATES:
    await self._recover_search_pages(report.candidates, pages, trace, profile)  # тут же break по слотам
```

Проверка слотов (`MAX_PAGES_PER_CATEGORY = 3`) находится **внутри**
`_recover_search_pages`, то есть **после** того, как поиск уже выполнен и оплачен.

Зонд 7, `_add_search_results` напрямую:

| состояние | вызовов `provider.search()` | чтений результатов | страниц добавлено |
|---|---|---|---|
| 0 из 3 слотов занято | **6** | 9 | 0* |
| 3 из 3 слота занято | **6** | 1 | **0** |

\* ноль — из-за фикстуры зонда; важно, что в обоих случаях поиск **выполнен**.

То есть когда sitemap и обходчик каталога уже заполнили три слота, весь поиск —
handshake, шесть запросов, три хопа — выполняется и **выбрасывается**. Провайдер
об этом не знает и не может знать.

---

## 2. Провайдер создаётся заново на каждый институт → handshake 19 раз за прогон

`live_discovery.py:1051` — `discover()` итерирует 19 институтов и для каждого
вызывает `_discover_one` → `_add_search_results` → `get_search_provider()`.

`search/__init__.py:38` — `get_search_provider()` это обычная функция **без
кэширования**: `return ExaMcpSearchProvider()`. Ни `lru_cache`, ни синглтон.

`exa_mcp.py:119-121` — состояние handshake живёт на экземпляре:
`self._initialized`, `self._session_id`.

Зонд 3:

```
=== a NEW provider per institution (what get_search_provider() does) ===
HTTP requests for 19 institutions x 1 query: 57
handshakes: 19
notifications: 19
```

Один институт = 8 HTTP-запросов (2 handshake + 6 запросов). Прогон по 19
институтам = **152 запроса**, из которых **38 — чистый оверхед handshake**.
При кэшированном провайдере их было бы 2.

---

## 3. 15 секунд делятся на handshake и на сам запрос — и первым погибает лучший запрос

`exa_mcp.py:243-253`:

```python
async with asyncio.timeout(self._timeout):      # DEFAULT_TIMEOUT_SECONDS = 15.0
    await self._initialize(client)               # ДВА последовательных POST
    result = await self._post(... "tools/call")  # и только потом сам поиск
```

`_initialize` (`exa_mcp.py:186-210`) делает `initialize`, затем
`notifications/initialized` — два последовательных round trip'а. Итого под одним
`asyncio.timeout(15.0)` умещаются **три** сетеых round trip'а.

Зонд 4 (шкала 100×, `timeout_seconds=0.15` = реальные 15 с):

```
A) handshake 6s + 2s, query 9s   → outcomes=['SearchUnavailable', 'ok', 'ok']
B) handshake 2s + 1s, query 9s   → outcomes=['ok', 'ok', 'ok']
C) handshake 1s + 0.5s, query 3s → outcomes=['ok', 'ok', 'ok']
```

Каждый запрос по отдельности укладывается в 15 с с запасом — и первый всё равно
падает по таймауту. А первым в `queries_for` идёт `field_and_degree`
(`intent.py:216`), **самый специфичный и самый полезный** запрос.

Из-за п.2 это повторяется на каждом институте: **19 раз теряется именно лучший
запрос**. И handshake не кэшируется между попытками, так что падение ничего не
исправляет.

В `config.py` **нет настройки таймаута поиска** — `DEFAULT_TIMEOUT_SECONDS = 15.0`
захардкожен в `exa_mcp.py:27`.

---

## 4. Навигационный хоп structurally unreachable — а стоит 3 чтения на институт

`retrieval.py:452-465`: кандидаты хопа добавляются **после** усечённого списка:

```python
ranked = ranked[:top_k]          # top_k=10
...
ranked = tuple(... for c in ranked) + tuple(appended)   # хоп — в хвосте
```

`live_discovery.py:1681-1683` — цикл восстановления смотрит только первые
`MAX_PROGRAM_CANDIDATES_CHECKED = 8`.

Зонд 6 (HTML с прозрачной ссылкой `/content?menu=188` — ровно тот случай, ради
которого хоп и написан):

```
search candidates: 10
hop entry points opened: ('https://cs.kaist.ac.kr/',)
hop candidates produced: 1
  10 navigation https://cs.kaist.ac.kr/content?menu=188  (never checked: budget is 8)
candidates the recovery loop will actually look at: 8
of them, navigation-hop candidates: 0
```

Хоп делает 3 чтения на институт (**57 чтений за прогон**) и его результат
недостижим: он на позиции 11+, а смотрят только первые 8. KAIST, ради которого
весь механизм существует, не получает ничего.

---

## 5. Три константы отбрасывают 70 % работы поиска

| константа | значение | где |
|---|---|---|
| `top_k` (аргумент вызова) | 10 | `live_discovery.py:1442`, `:1571` |
| `MAX_PROGRAM_CANDIDATES_CHECKED` | 8 | `live_discovery.py:80` |
| `MAX_PAGES_PER_CATEGORY` | 3 | `live_discovery.py:72` |

Зонд 5:

```
A) 0 slots used, 10 candidates  → fetches=8, checked 8, confirmed 0
B) 2 slots used, 10 candidates  → fetches=8, checked 8, confirmed 0
C) 3 slots used, 10 candidates  → fetches=0, checked 0, confirmed 0   ← поиск не читает ничего
```

Из 10 отранжированных кандидатов используется не больше 3. Из 8 проверок —
только когда слот свободен.

---

## 6. HTTP 429 обрабатывается как шесть независимых запросов

Зонд 3, провайдер отвечает 429:

```
queries attempted: 6, all raised: True
first error: SearchUnavailable: Exa MCP answered 429 http=429
HTTP requests spent on 429s: 6
handshakes re-done: 6
```

`retrieval.py:398-412` ловит `SearchUnavailable`, пишет диагностику и **идёт к
следующему запросу**. `_initialized` остаётся `False`, поэтому каждый из шести
запросов заново пытается сделать `initialize` и заново получает 429.

На 19 институтов это **114 запросов в заведомо мёртвую точку**. Это ровно то, что
бриф запрещает: «не повторять запросы в цикле, не обходить лимиты». Ответ
`429` с `Retry-After` — это сигнал остановиться, а не попробовать ещё пять
разным формулировками.

---

## 7. Сводка: сколько работы выполняется впустую за прогон по 19 институтам

| Что | Запросов | Реально используется |
|---|---|---|
| MCP handshake | 38 | 2 (если бы провайдер кэшировался) |
| Поисковые запросы | 114 | 0, когда 3 слота заняты |
| Чтения точек входа хопа | 57 | 0 (выход недостижим, п. 4) |
| **Итого** | **209** | **≤ 3 страницы на институт, и только если слот свободен** |

---

## 8. Что чинить, в порядке отдачи

1. **Кэшировать провайдер.** `get_search_provider()` → один экземпляр на процесс
   (`functools.lru_cache`). Убирает 36 лишних handshake за прогон. Правка в одном
   файле, риска нет, эффект измерим.
2. **Разделить таймауты.** Handshake — свой бюджет (например 10 с), `tools/call` —
   свой (15 с). Либо сделать `initialize` ленивым и однократным вне `search()`.
   Возвращает лучший запрос семьи `field_and_degree`.
3. **Останавливаться на 429.** Если `SearchUnavailable` несёт `http_status == 429`,
   прекращать запросы до конца института (и до конца прогона), а не перебирать
   шесть семейств. Соответствует бри́фу.
4. **Проверять слоты до поиска.** Если `len(selected[PROGRAM_PAGE]) >=
   MAX_PAGES_PER_CATEGORY`, не вызывать `discover_candidates` вовсе. Убирает 114
   бесполезных запросов.
5. **Дать хопу шанс.** Либо считать его в пределах тех же 8 проверок (вклинивать
   по приоритету хоста, а не дописывать в хвост), либо явно отключить
   `hop_entry_points` и не тратить 57 чтений. Сейчас он платит и не работает.

Пункты 1, 2, 4 — по три строки каждый и не меняют поведения в удачном случае.
Пункты 3 и 5 — изменения политики, их надо мерить парным прогоном.

---

## 9. Чего в разборе НЕТ

- `queries_for`, `prefilter`, `rank_candidates`, `fusion`, BM25 — проверены,
  работают (зонд 2).
- Приватность: `DiscoveryIntent` и `_reject_applicant_data` не пропускают профиль
  в провайдер; `search_coverage["represented"]` корректно пересчитывается в
  `_apply` (`live_discovery.py:1826-1834`) — сначала казалось, что он захардкожен
  нулём, но он обновляется ниже.
- `GOLDEN_DEMO_SHA256` не затронут.

Известные и намеренные отключения (не баги, но и не помощь): `CONFIRM_SEARCH_
PROGRAMMES=False`, `SEARCH_BEFORE_NAVIGATION=False`, `SKIP_REFUSED_SEARCH_HOSTS=
False`, `NAVIGATION_SLOT=False`, `rank_by_page_kind=False`,
`REJECT_ARCHIVE_HOSTS=False`, `reject_irrelevant_kinds=False`,
`ADMISSION_LEXICON=False`. Каждый выключен «до замера» — и вместе они означают,
что все измеренные улучшения не применяются.

---

## 10. Как воспроизвести

Зонды лежат в `/tmp/probe1..7.py` (в песочнице не сохраняются). Порядок:
скопировать `backend/app` в `/tmp/p311`, снять PEP 695-aliases (`type X = ...` →
`X = ...`, один файл — `live_discovery.py:764`), поставить `lxml httpx
beautifulsoup4 tldextract pydantic pydantic-settings` в venv на 3.11, запускать
зонды с `sys.path.insert(0, "/tmp/p311")`.
