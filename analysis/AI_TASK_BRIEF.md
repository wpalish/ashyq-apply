# AI TASK BRIEF — ASHYQ Apply: подбор университетов v2

> **Для кого этот файл.** Для ИИ-агента (Claude Code, Cursor, Codex и т.п.) или разработчика, который
> будет реализовывать изменения в репозитории `github.com/wpalish/ashyq-apply`. Файл самодостаточен:
> здесь весь контекст, все принятые решения, точные формулы, порядок задач и критерии приёмки.
> Подробности и обоснования — в соседних документах (см. §0.2), но для начала работы достаточно этого файла.
>
> **Дата фиксации:** 2026-09-05. **Статус решений:** утверждены владельцем продукта.

---

## 0. Как пользоваться этим файлом

### 0.1. Порядок работы для ИИ-агента
1. Прочитать §1–§3 (контекст, проблема, решения) — 5 минут.
2. Прочитать §4 (инварианты) — они превращаются в тесты и **не обсуждаются**.
3. Выполнять задачи §6 строго по порядку: этап 0 → 1 → 2 → 3 → 4 → 5. Внутри этапа — по номерам задач.
4. После каждой задачи: `ruff check`, `ruff format --check`, `mypy`, `pytest` — зелёные. Покрытие ≥ 92 % (CI-гейт).
5. Каждая задача заканчивается коммитом с сообщением в стиле репозитория (см. §7.3).
6. Если что-то в этом файле противоречит коду — **остановиться и спросить**, не угадывать.

### 0.2. Сопутствующие документы (в папке `analysis/`)
| Файл | Зачем читать |
|---|---|
| `SPEC_matching_v2.md` | Полная спецификация: все формулы, схемы, промпты, API, тесты. **Источник истины при расхождениях.** |
| `ANALYSIS.md` | Аудит текущего алгоритма и экспериментальные доказательства проблем |
| `DESIGN_agentic_search.md` | Обоснование архитектуры агента, приватности, community-слоя |
| `reference/ranking_v2.py` | Исполняемая референс-реализация формул §5. Портировать в `backend/app/domain/`, не переписывать с нуля |
| `scripts/01..03_*.py` | Скрипты, которыми доказаны проблемы v1 (можно использовать для регрессии) |

### 0.3. Как запустить проект локально
```bash
cd backend
python3 -m venv .venv && ./.venv/bin/pip install -r requirements-dev.txt   # или ./setup.sh (нужен uv)
UNIMATCH_DEMO_MODE=true ./.venv/bin/alembic upgrade head
UNIMATCH_DEMO_MODE=true UNIMATCH_ENABLE_BROWSER_TIER=false ./.venv/bin/python seed_demo.py   # полный демо-прогон, ~5 с
./.venv/bin/python -m pytest                        # 785 тестов
./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m ruff format --check app tests
./.venv/bin/python -m mypy app tests
# референс v2 на сохранённом прогоне:
UNIMATCH_DEMO_MODE=true ./.venv/bin/python ../analysis/reference/ranking_v2.py
```

---

## 1. Контекст проекта

**ASHYQ Apply** (внутренние имена пакетов, БД и env-префикс — `unimatch`/`UNIMATCH_`, **не переименовывать**) —
сервис шортлиста университетов и стипендий для иностранных абитуриентов, прежде всего из Казахстана.
Отвечает на вопрос: *«куда я могу поступить и кто из них реально за это заплатит?»*

| Слой | Стек | Где |
|---|---|---|
| Backend | Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, PostgreSQL/SQLite, httpx, BeautifulSoup, Playwright | `backend/app/` |
| Frontend | React + TypeScript + Vite; 12 экранов | `frontend/src/` |
| Данные | demo-корпус: 40 синтетических кандидатов (16 с полными страницами); live-реестр: 10 вузов | `backend/app/corpus/`, `backend/app/adapters/discovery/institution_registry.json` |
| Тесты | 785 backend (pytest, покрытие 92 %), 120 frontend unit (Vitest), 63 e2e (Playwright) | `backend/tests/`, `frontend/src/**/*.test.tsx`, `frontend/e2e/` |

**Пайплайн** (`backend/app/pipeline/runner.py`, state machine на 6 стадий):
```
profile → 1.validate → 2.discover → 3.verify → 4.funding → 5.assess → user decision → 6.documents
```

**Философия продукта — evidence-first. Это главная ценность, её нельзя сломать:**
- каждое число на экране ссылается на официальную страницу, цитату (`Claim.original_text_excerpt`) и дату;
- система **никогда не предсказывает** вероятность поступления (нет «73 %», нет слова «шанс»);
- оценки не конвертируются молча; «неизвестно» никогда не превращается в догадку;
- отсутствие данных **не отсеивает** вуз: hard-filter срабатывает только на *подтверждённое* требование, которое абитуриент *подтверждённо* не выполняет;
- ничего из профиля не уходит в исходящие URL (`assert_no_pii` в `Fetcher`); live-поиск не использует поисковики именно поэтому.

**Архитектура кода:** `app/domain/` — чистые правила без I/O; `app/adapters/` — всё, что трогает сеть/файлы; вся сеть — только через `app/adapters/fetching.py::Fetcher` (robots.txt, rate-limit, кэш, PII-guard).

**Что уже сделано хорошо и НЕ ТРОГАЕТСЯ:** `domain/eligibility.py`, `domain/funding.py`, `domain/costs.py`, `domain/conflicts.py`, `domain/freshness.py`, `domain/currency.py`, `domain/grades.py`, `adapters/fetching.py`, очередь `jobs/`, auth/tenancy, миграции.

---

## 2. Проблема: почему подбор сейчас не работает

Доказано экспериментально на демо-прогоне (`analysis/ANALYSIS.md`, §3):

| # | Симптом | Причина в коде |
|---|---|---|
| P1 | **#1 в шортлисте — UBC с недостачей 21 471 USD/год** при потолке семьи 6 000 USD и `funding_criticality=decisive` | `domain/scoring.py::score_result` — аддитивная сумма 13 компонент: Affordability = 0 компенсируется Funding 1.5 + Academic 1.0 + Country 1.0 |
| P2 | **Климат не влияет ни на что**: temperate/warm/cold дают одинаковый топ-5, макс. сдвиг 1.7 % шкалы | вес `climate_fit` 0.3 из максимума 8.45; то же для city/size/campus/workload |
| P3 | Поле «cs», «informatics», «Computer Science» (регистр) → **0 верифицируемых вузов** | `adapters/discovery/fixture_discovery.py::_matches_field` — substring без синонимов и таксономии |
| P4 | Смена предпочтений требует **повторного краулинга** | fit-лейблы вычисляются в `runner.py::_stage_verify` (строки ~401–425) и замораживаются в `ProgramResult.climate_fit` и т.д. |
| P5 | Extracurricular занимает 7 % шкалы, но **одинаков для всех вузов** | `_activity_strength(profile)` зависит только от профиля |
| P6 | Штраф за пропуски внутри score наказывает вузы с плохо парсящимися сайтами, а не худшие вузы | `total × (1 − 0.03·n)` |
| P7 | Нет понятия «сбалансированный список»: топ-20 может быть 20 амбициозных вариантов | — |
| P8 | Кандидатов негде искать: live = 10 захардкоженных вузов; programme-page recall = 1/10 | `live_discovery.py` перебирает `institution_registry.json` |
| P9 | 12 слайдеров весов 0–3 — пользователь их не трогает | `ScoringWeights` + `PreferencesScreen.tsx` |

---

## 3. Принятые решения (утверждены, не пересматривать без владельца)

| # | Решение | Выбор |
|---|---|---|
| D1 | Модель агрегации score | **Взвешенное геометрическое среднее** с ε = 0.02 (некомпенсаторная) |
| D2 | Неизвестные данные | **Отдельная метрика `coverage`**, не штраф внутри score; сортировка по `fit · coverage^γ`, **γ = 0.5** |
| D3 | Портфель | **Делаем сразу** (этап 0): корзины + сбалансированный шортлист с квотами **10 / ≥2 well-placed / ≥4 plausible / ≤3 ambitious / ≤3 на страну**, квоты — настраиваемые параметры |
| D4 | Вселенная вузов | **Не строим большую БД.** Кандидатов и страницы находит **ИИ-агент**, результаты кэшируются в shared research cache, который со временем сам становится каталогом |
| D5 | Роль ИИ | **Исследователь + отдельный текстовый комментарий.** Агент находит страницы, извлекает claim'ы с цитатами и пишет advisor-комментарий **рядом** со score. **Ни одно число от ИИ не попадает в fit / coverage / bucket / порядок** |
| D6 | Приватность промптов | По умолчанию **`preferences_only`** (уровень, направление, страны, язык, тип учебной программы). **`profile_aware`** — только по явному opt-in пользователя с текстом согласия |
| D7 | Community insights (Reddit и др.) | **Отдельная вкладка**, никогда не влияет на подбор. Источники: свой social-модуль → официальные студенческие блоги → Student Room / GradCafe → Reddit **только через поисковый инструмент LLM-провайдера с URL**; собственный клиент Reddit Data API **не пишем** |
| D8 | Веса | **Ранжирование 6 групп приоритетов** drag-and-drop → веса Rank-Order Centroid. Слайдеры остаются в «расширенном режиме» |
| D9 | LLM-провайдер | Выбрать **после пилота этапа 2**; обязательное условие — zero-retention / no-training. Прод не стартует без `UNIMATCH_LLM_DATA_POLICY_ACK=true` |
| D10 | Языки текста advisor | **Русский + английский**; казахский — после отдельной проверки качества |
| D11 | Post-study work в месяцах | Новый `ClaimType.POST_STUDY_WORK_MONTHS` — на этапе 2; до этого ось честно `UNKNOWN` |
| D12 | Названия корзин в UI | **Не** «safety/match/reach» (safety читается как обещание): `WELL_PLACED` / `PLAUSIBLE` / `AMBITIOUS` / `OUT_OF_BUDGET` / `NEEDS_CLARIFICATION` / `EXCLUDED` |

---

## 4. Инварианты — превращаются в тесты, не обсуждаются

| # | Инвариант | Тест |
|---|---|---|
| I1 | Ни одно число из ответа LLM не участвует в `fit`, `coverage`, `bucket`, `sort_key` | архитектурно: `domain/ranking_v2.py` не импортирует ничего из `adapters/research/` (тест на импорты) |
| I2 | Claim без цитаты, найденной в нормализованном тексте страницы, не сохраняется | A2 |
| I3 | В режиме `preferences_only` исходящий промпт не содержит имени, гражданства, GPA, баллов тестов, бюджета, evidence-ссылок | A1 |
| I4 | Ось в состоянии `unknown` никогда не понижает `fit` — только `coverage` | T3 |
| I5 | Ось в состоянии `not_applicable` (пользователь выбрал «any») не влияет ни на `fit`, ни на `coverage` | T4 |
| I6 | Один и тот же вход → байт-в-байт одинаковый порядок (tie-break по `id`) | T6 |
| I7 | Community-инсайт и advisor-комментарий не меняют `fit`, `coverage`, `bucket` | A4, архитектурно |
| I8 | Все существующие тесты объяснимости проходят на v2 (каждая ось имеет непустой `reason` и `weight`) | T9 |
| I9 | Ключ `research_cache` строится только из preferences-derived данных; два разных профиля с одинаковыми предпочтениями дают один ключ | A3 |
| I10 | `NullResearchAgent` (агент выключен) → поведение пайплайна байт-в-байт равно текущему | A6 |

---

## 5. Алгоритм v2 — точные формулы

Референс: `analysis/reference/ranking_v2.py` (портировать, все формулы там уже есть и проверены).

### 5.1. Веса из приоритетов (Rank-Order Centroid)
Пользователь ранжирует 6 групп. Вес группы на позиции k из n: `w_k = (1/n) · Σ_{j=k..n} 1/j`.
Для n=6: `[0.408, 0.242, 0.158, 0.103, 0.061, 0.028]` (сумма = 1).

| Группа | Оси и доли внутри группы |
|---|---|
| `funding` | funding_fit 0.5, affordability 0.5 — **обе × criticality**: nice_to_have 0.5 / important 0.75 / decisive 1.0 |
| `academic` | academic_fit 0.6, programme_standing 0.4 |
| `country` | country 1.0 |
| `city_climate` | city 0.5, climate 0.5 |
| `career` | career 0.5, post_study_work 0.5 |
| `campus_life` | university_size ⅓, campus ⅓, workload ⅓ |

Дефолтный порядок: `["funding", "academic", "country", "city_climate", "career", "campus_life"]`.
Если пользователь явно менял `ScoringWeights` (расширенный режим) — `weights_source="weights_override"`, используются его веса, нормализованные к сумме 1.
**Extracurricular из скоринга вузов удалён** (одинаков для всех строк). Он остаётся в `admissions_fit_for` и через него влияет на корзину.

### 5.2. Утилиты по осям
Каждая ось → `value ∈ [0,1]` **или** `UNKNOWN` **или** `NOT_APPLICABLE`, плюс человекочитаемая причина. `ε = 0.02`.

| Ось | Формула |
|---|---|
| **academic_fit** | eligibility MET: `clip(0.6 + 2·margin, 0.6, 1.0)`, margin = средний относительный запас над числовыми минимумами (уже считается в `scoring.py::admissions_fit_for`); MET без числовых минимумов: 0.75; PENDING: 0.5; GAP: 0.15; NEEDS_OFFICIAL_CLARIFICATION: UNKNOWN |
| **funding_fit** | CONFIRMED_OPPORTUNITY 1.0 · COMPETITIVE 0.7 · LIMITED 0.3 · NOT_ELIGIBLE ε · UNKNOWN → UNKNOWN |
| **affordability** | `r = gap / ceiling`; ceiling = `max_acceptable_gap` иначе `max_annual_budget`, конвертированный в валюту gap (как сейчас в `_comparable_ceiling`). r ≤ 1 → 1.0; 1 < r ≤ 1.5 → `1 − 1.4·(r − 1)`; r > 1.5 → ε. ceiling = 0: gap = 0 → 1.0, иначе ε. gap или ceiling неизвестны → UNKNOWN |
| **country** | в preferred → 1.0; вне списка → 0.35; список пуст → NOT_APPLICABLE; в excluded → **knock-out** |
| **programme_standing** | rank ≤ target_band → 1.0; иначе кусочно-линейно по `ln(rank)` через якоря (1→1.0, 100→0.8, 500→0.5, 1500→0.2), дальше 0.1; ранга нет → UNKNOWN |
| **city / climate / university_size / workload** | предпочтение `any` → NOT_APPLICABLE; атрибут `unknown` → UNKNOWN; совпало → 1.0; по лестнице: 1 ступень 0.75, 2 → 0.5, дальше 0.25. Лестницы: city `[small, medium, large, metropolis]`; climate `[cold, temperate, mediterranean, warm, tropical]`; workload `[moderate, demanding, very_demanding]`; size `[small, medium, large]` |
| **campus** | без порядка: совпало 1.0, иначе 0.25; `any` → N/A; unknown → UNKNOWN |
| **career** | не ценит ни internships, ни coop → N/A; coop ценит и подтверждён → 1.0; internships подтверждены → 0.8; страница есть без конкретики → 0.5; иначе UNKNOWN |
| **post_study_work** | не нужен → N/A; months известны → `clip(months/24, ε, 1)`; месяцы не распарсились → UNKNOWN |

### 5.3. Агрегация
```
K = оси со state == known
fit      = exp( Σ_{i∈K} w_i · ln(max(u_i, ε)) / Σ_{i∈K} w_i )
coverage = Σ_{i∈K} w_i / Σ_{i∈K ∪ UNKNOWN} w_i        # NOT_APPLICABLE не входит никуда
sort_key = fit · coverage^γ,   γ = 0.5  (config UNIMATCH_RANKING_GAMMA)
fit = None, coverage = 0, sort_key = 0 — если K пусто
```
**Без округления внутри арифметики** — округляет только презентация (иначе ломается T3).

### 5.4. Knock-out'ы (строка листится в корзине EXCLUDED, `sort_key = 0`, не ранжируется)
1. `country ∈ excluded_countries`
2. подтверждённый hard-filter из `eligibility.py` (`RequirementCheck.is_hard_filter == True`)
3. `degree != level` — на уровне retrieval
4. `field_match == 0` (§5.6) — на уровне retrieval

**Не** knock-out: непрочитанное требование, test-optional, несовпавшая шкала GPA, превышение бюджета (это корзина OUT_OF_BUDGET).

### 5.5. Корзины и портфель
```
NEEDS_CLARIFICATION  admissions_fit == INSUFFICIENT_DATA
OUT_OF_BUDGET        r > τ(criticality): decisive 1.5 · important 2.5 · nice_to_have ∞
WELL_PLACED          STRONGER_FIT ∧ funding CONFIRMED_OPPORTUNITY ∧ r ≤ 1
PLAUSIBLE            admissions_fit ∈ {STRONGER, PLAUSIBLE} ∧ funding ∈ {CONFIRMED, COMPETITIVE} ∧ (r неизвестен ∨ r ≤ 1.5)
AMBITIOUS            всё остальное
EXCLUDED             knock-out
```
Шортлист (детерминированный):
1. Сортировать по `(−sort_key, id)`.
2. Добрать `min_well_placed=2` из WELL_PLACED, затем `min_plausible=4` из PLAUSIBLE, соблюдая `max_per_country=3`. Недобор → note «найдено N, хотели ≥ M».
3. Заполнить до `size=10` по `sort_key` из {WELL_PLACED, PLAUSIBLE, AMBITIOUS}, соблюдая `max_ambitious=3`, `max_per_country`.
4. OUT_OF_BUDGET / NEEDS_CLARIFICATION / EXCLUDED — отдельные секции ниже, с причиной.
Пользовательские approve/reject поверх: reject убирает из портфеля и запускает добор.

### 5.6. Таксономия направлений — ISCED-F 2013
Профиль и программы маппятся в 4-значные коды через словарь синонимов (`domain/fields.py`, стартовый список в `SPEC_matching_v2.md` §3.1: cs/informatics/informatik/информатика/… → 0613 и т.д.). Сравнение по иерархии: 4 знака → 1.0, 3 → 0.7, 2 → 0.4, иначе 0. Нормализация: lower + удаление degree-токенов (`adapters/matching.py::content_tokens` уже есть) + точное вхождение синонима; fallback Jaro-Winkler ≥ 0.92 по токенам. Эмбеддингов на этом этапе нет.

### 5.7. Ожидаемый результат на демо-корпусе (для проверки порта)
Профиль `DEMO_PROFILE`, дефолтные приоритеты:

| # | Университет | v1 score | fit | coverage | Корзина |
|---|---|---|---|---|---|
| 1 | Groningen | 6.39 | 0.83 | 0.97 | PLAUSIBLE |
| 2 | KU Leuven | 5.92 | 0.80 | 0.94 | PLAUSIBLE |
| 3 | Toronto | 5.54 | 0.82 | 0.77 | PLAUSIBLE |
| 4 | Tokyo | 5.18 | 0.72 | 0.94 | PLAUSIBLE |
| 5 | TU Delft | 5.93 | 0.68 | 0.97 | AMBITIOUS |
| 12 | **UBC (был #1)** | 6.54 | 0.43 | 0.97 | **OUT_OF_BUDGET** |

При `city_climate` на 1-м месте и climate=warm: NUS #11→#5, Toronto #3→#8. При climate=cold: Oslo #14→#6.
Точные значения могут отличаться в 3-м знаке после порта (career/post_study_work оси в референсе упрощены) — важна структура порядка и корзины.

---

## 6. Задачи по этапам

Формат: `[Этап.Номер] Название — файлы — критерий приёмки`. Выполнять по порядку.

### ЭТАП 0 — Ranking v2 + Portfolio (не зависит от агента; ~3–4 дня)

**[0.1] Схема профиля: приоритеты и privacy-режим**
- `backend/app/schemas/profile.py`: в `Preferences` добавить `priorities: list[PriorityGroup] = []` (max 6, без дублей, валидатор) и `research_privacy: Literal["preferences_only","profile_aware"] = "preferences_only"`. `PriorityGroup = Literal["funding","academic","country","city_climate","career","campus_life"]`. Константа `DEFAULT_PRIORITIES`.
- `ScoringWeights` остаётся; добавить в `ApplicantProfileIn` поле `weights_override: bool = False`.
- Приёмка: существующие сохранённые профили загружаются (все поля с default, `extra="forbid"` не нарушен); тест на дубли в `priorities`.

**[0.2] Модуль весов**
- Новый `backend/app/domain/priorities.py`: `roc_weights(order) -> dict[group, float]`, `axis_weights(order, criticality) -> dict[axis, float]`, `weights_from_override(ScoringWeights) -> dict[axis, float]` (маппинг старых имён на оси, нормализация к 1).
- Приёмка: T10 — сумма весов 1 ± 1e-9, монотонность по позиции.

**[0.3] Модуль ranking v2**
- Новый `backend/app/domain/ranking_v2.py` — порт `analysis/reference/ranking_v2.py`: `Missing`, `Axis`, все `u_*`, `aggregate`, `KnockOut`, `Bucket`, `bucket_of`, `Quotas`, `build_shortlist`, и верхнеуровневая `rank_result(result: ProgramResult, profile: ApplicantProfileIn, *, gamma) -> RankingV2`.
- Ось `academic_fit` использует margin — вынести расчёт margin из `scoring.py::admissions_fit_for` в отдельную функцию `requirement_margin(result) -> float | None` и переиспользовать.
- Ось `affordability` использует существующий `scoring.py::_comparable_ceiling` (сделать публичным).
- **Запрещено импортировать что-либо из `app.adapters.*`** (I1). Тест на импорты.
- Приёмка: T1–T7, T9, T10 (описания в §8).

**[0.4] Схема результата**
- `backend/app/schemas/result.py`: добавить `AxisScore`, `RankingV2`, `Bucket` (enum в `domain/enums.py`), поля `ProgramResult.catalog_attributes: dict[str,str]`, `catalog_attributes_source: str`, `ranking: RankingV2 | None`. Точные поля — `SPEC_matching_v2.md` §2.2.
- `preference_score` (v1) **остаётся** на переходный период.
- `climate_fit`/`city_fit`/`workload_fit`/`size_fit`/`campus_fit` остаются в схеме, но с этапа 0.5 заполняются из `rank_result` (для обратной совместимости фронта), а не на verify.

**[0.5] Пайплайн: атрибуты на verify, ранжирование на assess**
- `runner.py::_stage_verify`: вместо вычисления `_fit_label(...)` сохранять `result.catalog_attributes = cand.attributes` и `catalog_attributes_source = "registry"` (demo: `"fixture-catalog"`).
- `runner.py::_stage_assess`: после `admissions_fit_for` и `score_result` (v1) вызывать `rank_result(...)`; писать `result.ranking`, обновлять лейблы `*_fit` из осей, `row.score_total = ranking.sort_key` при `UNIMATCH_RANKING_VERSION=2` (иначе как сейчас). Добавить `row.bucket` (новая индексированная колонка `String(40)`, миграция Alembic).
- Флаг `UNIMATCH_RANKING_VERSION: int = 2` в `config.py` (дефолт 2; 1 — старое поведение для отката).
- Приёмка: `seed_demo.py` даёт порядок из §5.7; при `UNIMATCH_RANKING_VERSION=1` вывод байт-в-байт как сейчас.

**[0.6] Re-rank без краулинга**
- `backend/app/api/routes_results.py`: `POST /api/runs/{run_id}/rerank`, body `{priorities?, preferences?, funding?, weights?, gamma?}` → применить поверх сохранённого профиля (не сохраняя его, если не передан `persist=true`), пересчитать `ranking`/`bucket`/`score_total` для всех строк, вернуть `{rows: N, gamma}`. Tenancy-проверки как у соседних эндпоинтов.
- `GET /api/runs/{run_id}/shortlist` → `{chosen: [...], notes: [...], quotas}` из `build_shortlist`. Квоты — из query-параметров с дефолтами (позже — настройка организации).
- `GET /api/runs/{run_id}/results`: параметры `sort=key|fit|coverage|gap|deadline`, `bucket=`.
- Приёмка: T8 — `rerank` меняет порядок и делает **0** вызовов `Fetcher` (мок с assert); контракт-тест `test_frontend_contract.py` обновлён.

**[0.7] Портирование тестов объяснимости и документация**
- Существующие тесты `test_scoring_and_profile.py`, проверяющие объяснимость и влияние полей профиля (`test_every_component_names_its_weight_and_its_reason`, `test_university_size_moves_the_score`, `test_funding_criticality_changes_the_weight_of_funding`, `test_a_tenge_ceiling_is_converted_before_it_is_compared`, `test_a_campus_mismatch_is_not_dressed_up_as_acceptable` и др.) — продублировать для v2 в `tests/test_ranking_v2.py`. v1-тесты не удалять до удаления v1.
- `docs/PROFILE_FIELDS.md`: обновить строки `priorities`, `research_privacy`, `weights_override`, и пометить extracurricular как «Context in ranking; scored via admissions fit».
- Новый `docs/adr/0003-noncompensatory-ranking.md`: почему геометрика, почему coverage отдельно, почему γ = 0.5.

**[0.8] Frontend этапа 0 (минимум, чтобы результат был виден)**
- `frontend/src/types.ts`: типы `RankingV2`, `AxisScore`, `Bucket`.
- `ShortlistScreen.tsx`: колонки «Соответствие» (fit, 0–1 с двумя знаками) · «Подтверждено» (coverage в %) · «Корзина»; дефолтная сортировка `key`; секции OUT_OF_BUDGET / NEEDS_CLARIFICATION / EXCLUDED свёрнуты ниже; блок «Сбалансированный шортлист» с notes.
- `PreferencesScreen.tsx`: блок «Что важнее?» — 6 карточек с кнопками вверх/вниз (DnD — этап 5); спойлер «Расширенные веса» с текущими слайдерами и чекбоксом `weights_override`. Кнопка «Пересчитать» → `POST /rerank`.
- `ResultDetail.tsx`: список осей с value/weight/reason/state.
- Дисклеймер под fit: *«Соответствие вашим приоритетам по подтверждённым данным. Не вероятность поступления.»*
- Приёмка: typecheck, lint, unit-тесты, e2e `journey.spec.ts` проходит с новыми колонками.

### ЭТАП 1 — Каркас research-агента без LLM (~2–3 дня)

**[1.1] Интерфейс и схемы**
- Новый пакет `backend/app/adapters/research/`: `base.py` — `Protocol ResearchAgent` с 6 методами (`discover`, `locate_pages`, `extract_claims`, `programme_brief`, `applicant_commentary`, `community_insights`) и схемы `DiscoveryQuery`, `CandidateLead`, `PageSet`, `ProposedClaim`, `ExtractionContext`, `AdvisorCommentary`, `Insight` (поля — `SPEC_matching_v2.md` §6.2, §7, §8.2).
- `null.py` — `NullResearchAgent`: все методы возвращают пусто/NOT_FOUND.
- `fixture.py` — `FixtureResearchAgent`: отвечает из demo-корпуса (`catalog.json` + страницы), чтобы демо и тесты работали без сети и без LLM.
- Приёмка: A6 — с `NullResearchAgent` полный демо-прогон байт-в-байт равен текущему.

**[1.2] Excerpt-валидатор**
- `backend/app/adapters/research/validation.py`: `normalize(text)` (lower, NFKC, схлопнуть пробелы, убрать пунктуацию), `accept(claim: ProposedClaim, page_text: str) -> tuple[bool, str]` — правила: цитата ⊂ нормализованного текста; 20 ≤ len ≤ 600; нормализованное значение claim'а (число/дата) встречается внутри цитаты.
- Принятый claim → `Claim(extraction_method="llm_assisted", confidence=min(agent, 0.9))`, дальше — стандартные `enforce_source_hierarchy`, `apply_freshness`, `find_conflicts`.
- Приёмка: A2.

**[1.3] Shared research cache**
- Миграция Alembic: таблица `research_cache(key PK, kind, args JSONB, payload JSONB, source_urls, model, prompt_version, created_at, expires_at)` + индекс `(kind, expires_at)`. JSON→JSONB только на PostgreSQL (по образцу миграции `c9e05a71f4d8`).
- `backend/app/adapters/research/cache.py`: `cache_key(kind, args)` = sha256 канонического JSON; TTL по `kind`: lead 180 д., pages 120 д., claims — `freshness.max_age_days(claim_type)`, insights 365 д., brief 180 д. `applicant_commentary` **никогда не кэшируется**.
- Приёмка: A3 — ключ не зависит от профиля.

**[1.4] Прокладка в пайплайн как эскалация**
- `runner.py`: в `_stage_verify` и `_stage_funding` после rule-based адаптеров, если категория страницы `NOT_FOUND` или claim-набор пуст → `agent.locate_pages` → `Fetcher.get` → `agent.extract_claims` → валидатор → в общий список claim'ов. Агент **никогда не ходит в сеть сам** — только получает уже скачанный текст.
- `config.py`: `UNIMATCH_RESEARCH_AGENT: Literal["null","fixture","llm"] = "fixture"` в demo, `"null"` в live до этапа 2; `UNIMATCH_AGENT_BUDGET_PAGES_PER_RUN: int = 120` — превышение → диагностика «бюджет исследования исчерпан», не тихий обрыв.
- Приёмка: демо-прогон с `fixture` даёт те же результаты, что и без агента (корпус уже полный); счётчик `pages_via_agent` в `ResearchRun` и в `/metrics`.

### ЭТАП 2 — LLM-агент: поиск страниц и извлечение (~4–5 дней + eval)

**[2.1] `LlmResearchAgent` для `locate_pages` и `extract_claims`**
- `backend/app/adapters/research/llm.py`; провайдер за конфигом `UNIMATCH_LLM_PROVIDER`, `UNIMATCH_LLM_MODEL`, `UNIMATCH_LLM_API_KEY`; структурированный вывод (JSON schema из Pydantic-моделей); `prompt_version` — константа в модуле, входит в ключ кэша.
- Промпты — дословно из `SPEC_matching_v2.md` §6.5 (system + locate_pages + extract_claims), вынесены в `backend/app/adapters/research/prompts/*.md` и загружаются при старте.
- Prompt builder с двумя режимами privacy; в `preferences_only` доступны только `DiscoveryQuery`/`ProgrammeQuery`-поля.
- Прод-гейт: `UNIMATCH_LLM_DATA_POLICY_ACK=true` обязателен, иначе приложение не стартует с `agent="llm"` (по образцу существующей проверки `/metrics` без токена).
- Приёмка: A1 (PII-тест на промпт демо-профиля: нет `"4.8"`, `"7.0"`, `"1400"`, `"Kazakhstan"`, `"6000"`, `display_name`); мок-провайдер в тестах.

**[2.2] `ClaimType.POST_STUDY_WORK_MONTHS`**
- `domain/enums.py` + `adapters/government/web_government.py` (rule-based парсер «up to N months/years») + агентное извлечение. Ось `post_study_work` начинает получать число.

**[2.3] Canary-eval**
- Скрипт `backend/scripts/canary_agent.py` по образцу `canary_discovery.py`: 10 вузов из `docs/CANARY_AUDIT.md`. Отчёт в `docs/AGENT_CANARY_REPORT.md`.
- **Гейты для включения `agent="llm"` в проде:** programme-page recall ≥ 7/10 (сейчас 1/10); category-page recall ≥ 27/30 (сейчас 26/30); материальных false positives = 0; доля claim'ов, отброшенных excerpt-валидатором, — измерена и опубликована; стоимость холодного прогона — измерена.
- По результатам — записка по выбору провайдера (D9).

### ЭТАП 3 — Discovery и retrieval (~3 дня)

**[3.1] `discover` через рейтинги с весами**
- Промпт `discover` из спеки §6.5. Веса источников (`domain/rankings.py`): QS/THE World 1.0; QS/THE by Subject при совпадении с ISCED-полем 1.3; ARWU / US News 0.8; нишевые предметные при совпадении 1.0; национальные 0.6; агрегаторы/блоги 0. Год: ×0.85 за каждый год старше текущего, старше 3 лет → 0.
- `consensus_rank = exp(weighted_median(ln(rank_i), w_i))`; каждый `RankingEntry` с URL и годом.
- `institution_registry.json` остаётся как seed/whitelist и источник атрибутов для 10 известных вузов.

**[3.2] Таксономия ISCED и retrieval-слой**
- `domain/fields.py` (§5.6) + замена `_matches_field` в `fixture_discovery.py` и `matches_field`/`matches_field_text` в `live_discovery.py` на `field_match(...)`.
- Pre-score и отбор на верификацию: `pre_fit = aggregate(известные оси из {country, programme_standing, climate, city, university_size, campus, workload, est_cost_band})`; отбор `verify_limit` жадно по `pre_fit · coverage^γ` с `max_per_country = ceil(verify_limit / 4)`. `est_cost_band` — только здесь, никогда не показывается как число.
- Приёмка: `analysis/scripts/01_discovery_sensitivity.py` — «cs», «informatics», «Computer Science» дают те же 16 верифицируемых, что и «computer science».

### ЭТАП 4 — Advisor и Community (~3 дня)

**[4.1] Advisor commentary**
- `programme_brief` (всегда) и `applicant_commentary` (только `profile_aware`); схема `AdvisorCommentary`; промпт §7 спеки.
- Валидатор (`domain/advisor.py`): каждое число в тексте встречается в `evidence_claim_ids` или в профиле; запрещённые паттерны `\d+\s?%`, `chance`, `likely|unlikely to (be )?admit`, `guarantee`, `safety school`, `you will get`; каждая `concern` ссылается на ≥1 claim_id; язык = язык UI (ru/en). Провал → отбросить, лог, ≤1 повтор.
- `questions_to_ask` → `UnresolvedQuestion` с новым полем `origin: Literal["pipeline","advisor","community"] = "pipeline"`.
- Приёмка: A4.

**[4.2] Community insights**
- Схема `Insight` (§8.2 спеки); промпт §8; источники по D7. Показ: `source_type ∈ {ashyq_community, official_student_blog, student_union}` **или** `corroborated_by ≥ 2`. URL перепроверяется `Fetcher`'ом при сохранении — недоступен → отбросить. TTL 365 д.
- Red flags по активностям → `UnresolvedQuestion(origin="community")`, формулировка как вопрос, тот же валидатор запрещённых паттернов.
- Интеграция с существующим social-модулем (`api/routes_social.py`, `domain/social.py`): посты с тегом вуза — источник `ashyq_community`.
- Приёмка: A5; I7.

### ЭТАП 5 — Frontend полностью (~3–4 дня)

- Приоритеты — настоящий drag-and-drop (без внешних зависимостей, если бандл вырастет > +10 kB gzip — обсудить).
- Тумблер «Разрешить использовать мой профиль для поиска» с текстом согласия (что уходит, кому, зачем; из таблицы §6.4 спеки); `PATCH /api/profile/{id}/research-privacy` с записью в audit (без содержимого).
- Detail: вкладки Eligibility · Admissions fit · Funding · **Advisor** · **Students say** (баннер: «Мнения студентов. Не официальная позиция университета и не влияет на подбор»).
- i18n строк ru/en; `GET /api/meta/capabilities` + `ranking_version`, `agent: {enabled, model, privacy_mode}`.
- e2e: новый `ranking.spec.ts` (смена приоритета → порядок меняется без нового run) и обновление `journey.spec.ts`.

---

## 7. Правила работы в репозитории

### 7.1. Гейты (CI, `.github/workflows/ci.yml`)
`ruff check` · `ruff format --check` · `mypy app tests` (без per-module escape hatch) · `pytest --cov=app --cov-fail-under=92` на SQLite **и** PostgreSQL · frontend `typecheck`, `lint`, `test`, `build`, `e2e` · `pip-audit`, `npm audit`.

### 7.2. Стиль кода проекта (соблюдать)
- Docstring и комментарии объясняют **почему**, часто со ссылкой на дефект, который правило предотвращает. Не писать очевидное «что».
- Никаких «magic numbers» без имени и комментария; пороги — именованные константы или конфиг.
- Каждое суждение — с человекочитаемой причиной (`reason`/`explanation`), как в существующем `ScoreComponent`.
- Новые enum'ы — в `domain/enums.py`, `StrEnum`, с явным `UNKNOWN`, где применимо.
- Домен (`app/domain/`) не импортирует адаптеры и не делает I/O.
- Тесты — по одному поведению на тест, имя описывает поведение (`test_an_excluded_country_scores_zero_on_country_preference`).

### 7.3. Коммиты
Стиль репозитория — короткая строка в нижнем регистре с префиксом `feat:`/`fix:`/`test:`/`docs:`/`style:`, описывающая **поведение**, а не файл: `feat: rank with a geometric mean so an unaffordable place cannot buy its way to the top`. Один коммит — одна задача из §6.

### 7.4. Что нельзя
- Переименовывать `unimatch`/`UNIMATCH_` (осознанное решение, см. README).
- Ослаблять `Fetcher` (robots, rate-limit, PII-guard) или ходить в сеть мимо него.
- Отправлять в LLM что-либо сверх таблицы privacy-режимов (`SPEC_matching_v2.md` §6.4).
- Показывать пользователю слово «вероятность», «шанс», «%» рядом с подбором.
- Удалять v1-скоринг и его тесты до отдельного решения (планово — через два релиза после этапа 0).
- Понижать `--cov-fail-under=92`.

---

## 8. Каталог тестов (краткие описания; полные — `SPEC_matching_v2.md` §10)

| # | Файл | Проверяет |
|---|---|---|
| T1 | `tests/test_ranking_v2.py` | Строка с `r = 3.6` и всеми остальными осями = 1.0 ранжируется ниже строки с `r ≤ 1` и fit ≥ 0.6 |
| T2 | там же | Две строки, отличающиеся только климатом: при `city_climate` на 1-м месте порядок меняется при смене предпочтения |
| T3 | там же | Перевод оси known → UNKNOWN не понижает fit; понижает coverage ровно на её долю веса |
| T4 | там же | NOT_APPLICABLE-ось не влияет ни на fit, ни на coverage |
| T5 | там же | Excluded country → `knocked_out_by`, `bucket=EXCLUDED`, `sort_key=0` |
| T6 | там же | 1 000 перестановок входа → идентичный вывод |
| T7 | там же | Портфель: квоты соблюдены; недобор → note; `max_per_country` не нарушен |
| T8 | `tests/test_api.py` | `rerank` меняет порядок и делает 0 вызовов Fetcher |
| T9 | `tests/test_ranking_v2.py` | Каждая ось имеет непустой `reason` и `weight`; портированные тесты объяснимости v1 |
| T10 | там же | ROC-веса суммируются в 1 ± 1e-9; монотонны |
| T11 | там же | `domain/ranking_v2.py` не импортирует `app.adapters.*` (I1) |
| A1 | `tests/test_research_agent.py` | Промпт в `preferences_only` не содержит PII демо-профиля |
| A2 | там же | Excerpt-валидатор: отбрасывает цитату, которой нет; принимает точную; отбрасывает число вне цитаты |
| A3 | там же | Ключ кэша не зависит от профиля |
| A4 | там же | Комментарий с `%`/«chance» отбрасывается |
| A5 | там же | Insight без URL или с недоступным URL не сохраняется |
| A6 | `tests/test_pipeline.py` | `NullResearchAgent` → результат прогона байт-в-байт равен текущему |

---

## 9. Определение «готово» для этапа 0

- [ ] `seed_demo.py` показывает порядок из §5.7: Groningen #1, UBC в OUT_OF_BUDGET.
- [ ] `analysis/scripts/03_climate_sensitivity.py` (адаптированный под v2): при `city_climate` первым приоритетом топ-5 меняется между warm и cold.
- [ ] `POST /rerank` со сменой приоритетов возвращает новый порядок < 1 с, без сетевых вызовов.
- [ ] T1–T11 зелёные; все 785 существующих тестов зелёные; покрытие ≥ 92 %; ruff/mypy чистые.
- [ ] `UNIMATCH_RANKING_VERSION=1` возвращает старое поведение байт-в-байт.
- [ ] Frontend: typecheck/lint/unit/e2e зелёные; на шортлисте видны fit, coverage, корзина; смена приоритета + «Пересчитать» меняет порядок без нового прогона.
- [ ] `docs/adr/0003-noncompensatory-ranking.md` и обновлённый `docs/PROFILE_FIELDS.md` в коммите.

---

## 10. Открытые вопросы — решены по рекомендациям, вернуться при указанных триггерах

| Вопрос | Принято | Триггер для пересмотра |
|---|---|---|
| LLM-провайдер | после пилота этапа 2 | результаты canary-eval [2.3] |
| γ | 0.5 | отзывы на демо после этапа 0 |
| Квоты портфеля | 2 / 4 / 3 / ≤3 на страну, настраиваемые | подтверждение от консультантов по поступлению |
| Языки advisor | ru + en | отдельная проверка качества kk |
| Post-study work в месяцах | этап 2, задача [2.2] | — |
