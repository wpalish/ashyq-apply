# SPEC — Подбор университетов v2: retrieval, ranking, portfolio, research agent

*Версия 0.1, 2026-09-05. Статус: на утверждение.*
*Зафиксированные решения: геометрическая агрегация · coverage отдельно от fit · портфель сразу ·
ИИ — исследователь + отдельный текстовый комментарий (не внутри score) · в промпты по умолчанию
только предпочтения, profile-aware — по явному opt-in · community-слой отдельно, не влияет на score.*

Исполняемая референс-реализация формул §4–§5: `analysis/reference/ranking_v2.py`
(запускается на сохранённом демо-прогоне, вывод — в §4.8).

---

## 0. Содержание

1. Цели, не-цели, инварианты
2. Модель данных (что добавляется)
3. Retrieval: таксономия направлений, knock-out'ы, pre-score
4. Ranking v2: веса, утилиты, агрегация, coverage
5. Portfolio: корзины и сбалансированный шортлист
6. Research agent: интерфейс, операции, промпты, приватность, кэш
7. Advisor commentary: качественное суждение ИИ вне score
8. Community insights
9. API и UI
10. Тесты и гейты качества
11. План внедрения по этапам
12. Открытые вопросы

---

## 1. Цели, не-цели, инварианты

### Цели
- Шортлист **реагирует на каждое предпочтение**, которое пользователь заполнил (сегодня климат
  сдвигает score на 1.7 % и не меняет порядок).
- **Критичный провал не компенсируется** мелкими плюсами (сегодня #1 — вуз с недостачей 3.6×
  потолка семьи).
- Смена предпочтений → **мгновенный re-rank без краулинга**.
- Поиск кандидатов **не ограничен ручным реестром из 10 вузов**; страницы программ находятся
  агентом (сегодня recall 1/10).
- Пользователь видит **сбалансированный набор**, а не топ-N по одному числу.

### Не-цели
- Не предсказываем вероятность поступления. Нигде нет «%» и слова «шанс».
- Не заменяем `eligibility.py`, `funding.py`, `costs.py`, `conflicts.py`, `freshness.py`.
- Не строим и не поддерживаем вручную каталог на тысячи вузов.

### Инварианты (проверяются тестами, §10)
| # | Инвариант |
|---|---|
| I1 | Ни одно число из ответа LLM не участвует в `fit`, `coverage`, `bucket`, порядке сортировки |
| I2 | Claim без цитаты, найденной в тексте страницы, не существует |
| I3 | В режиме `preferences_only` исходящий промпт не содержит: имени, гражданства, GPA, баллов тестов, бюджета, ссылок на evidence |
| I4 | Неизвестная ось никогда не понижает `fit` — только `coverage` |
| I5 | Ось с «нет предпочтения» (`any`) не влияет ни на `fit`, ни на `coverage` |
| I6 | Один и тот же вход → байт-в-байт одинаковый порядок (tie-break по id) |
| I7 | Community-инсайт никогда не меняет `fit`, `coverage`, `bucket` |
| I8 | Все существующие тесты объяснимости (`test_every_component_names_its_weight_and_its_reason` и др.) проходят на v2 |

---

## 2. Модель данных

### 2.1. Профиль (`schemas/profile.py`) — добавляется

```python
PriorityGroup = Literal["funding", "academic", "country", "city_climate", "career", "campus_life"]

class Preferences(Base):
    ...  # без изменений
    #: Порядок важности. Пусто → дефолт ниже. Заменяет 12 слайдеров в основном UI.
    priorities: list[PriorityGroup] = Field(default_factory=list, max_length=6)
    #: Что можно отправлять LLM-провайдеру. См. §6.4.
    research_privacy: Literal["preferences_only", "profile_aware"] = "preferences_only"

DEFAULT_PRIORITIES = ["funding", "academic", "country", "city_climate", "career", "campus_life"]
```

`ScoringWeights` **остаётся** как «расширенный режим»: если пользователь явно менял веса,
`weights_override=True` и ROC-веса не применяются. Обратная совместимость сохранённых профилей —
`extra="forbid"` не нарушается, поля с default.

### 2.2. Результат (`schemas/result.py`) — добавляется

```python
class AxisScore(Base):
    axis: str                                   # "affordability", "climate", ...
    value: float | None                         # None = unknown или not_applicable
    state: Literal["known", "unknown", "not_applicable"]
    weight: float
    reason: Str2000                             # человекочитаемо, как сейчас в ScoreComponent
    evidence_claim_ids: list[str] = []          # какие claim'ы это подтвердили

class RankingV2(Base):
    fit: float | None                           # [0,1]; None когда ни одна ось не известна
    coverage: float                             # [0,1] доля веса известных осей
    sort_key: float                             # fit * coverage**gamma
    gamma: float
    axes: list[AxisScore]
    unknown_axes: list[str]
    knocked_out_by: list[str] = []              # непусто → строка листится, но не ранжируется
    bucket: Bucket
    bucket_reason: Str2000
    weights_source: Literal["priorities_roc", "weights_override"]
    version: Literal["2"] = "2"

class Bucket(StrEnum):
    WELL_PLACED = "WELL_PLACED"                 # в UI: «Хорошо позиционирован»
    PLAUSIBLE = "PLAUSIBLE"                     # «Реалистично»
    AMBITIOUS = "AMBITIOUS"                     # «Амбициозно»
    OUT_OF_BUDGET = "OUT_OF_BUDGET"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    EXCLUDED = "EXCLUDED"

class ProgramResult(Base):
    ...  # всё существующее остаётся, включая preference_score (v1) на переходный период
    catalog_attributes: dict[str, str] = {}     # климат/город/размер/кампус/нагрузка — «сырьё» для re-rank
    catalog_attributes_source: Str200 = ""      # "registry" | "agent:<model>" | "koppen-geiger"
    ranking: RankingV2 | None = None
    commentary: AdvisorCommentary | None = None # §7
    insights: list[Insight] = []                # §8
```

**Ключевое изменение:** `climate_fit`, `city_fit`, … больше не вычисляются на стадии verify и не
замораживаются. На verify сохраняются только *атрибуты* (`catalog_attributes`); лейблы и утилиты —
чистая функция `rank(results, profile)` на стадии assess и в эндпоинте re-rank.

### 2.3. Shared research cache (новая таблица, Alembic-миграция)

```sql
CREATE TABLE research_cache (
  key            TEXT PRIMARY KEY,           -- sha256(kind || canonical_json(args))
  kind           TEXT NOT NULL,              -- lead | pages | claims | insights | brief
  args           JSONB NOT NULL,             -- только данные, производные от предпочтений (никогда от профиля)
  payload        JSONB NOT NULL,
  source_urls    TEXT[] NOT NULL,
  model          TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL,
  expires_at     TIMESTAMPTZ NOT NULL
);
CREATE INDEX ON research_cache (kind, expires_at);
```

TTL по `kind`: `lead` 180 д., `pages` 120 д., `claims` — по `freshness.MAX_AGE_DAYS` для типа
(дедлайны 30 д., цены 120 д., прочее 180 д.), `insights` 365 д., `brief` 180 д.
Кэш **общий для всех тенантов** — поэтому в `args` не может быть ничего из профиля (тест I3
проверяет и это). Результаты `applicant_commentary` (§7) в этот кэш не пишутся никогда.

---

## 3. Retrieval

### 3.1. Таксономия направлений — ISCED-F 2013

Профиль и программы маппятся в 4-значные коды. Сравнение по иерархии:

| Совпадение | `field_match` |
|---|---|
| 4 знака (0613 = 0613) | 1.0 |
| 3 знака (061x) | 0.7 |
| 2 знака (06xx) | 0.4 |
| иначе | 0 → программа не проходит retrieval |

Стартовый словарь синонимов (`domain/fields.py`; расширяется, агент может *предложить* код —
код принимается только если он есть в перечне ISCED):

```python
FIELD_SYNONYMS = {
  "0613": ["computer science", "computing", "cs", "informatics", "informatik", "software engineering",
           "информатика", "компьютерные науки", "программная инженерия", "ақпараттық технологиялар"],
  "0612": ["data science", "database", "network", "cybersecurity", "information systems"],
  "0619": ["ict", "information technology", "it"],
  "0688": ["artificial intelligence", "ai", "machine learning", "computational science"],
  "0714": ["electrical engineering", "electronics", "electronic engineering"],
  "0715": ["mechanical engineering", "mechatronics"],
  "0732": ["civil engineering", "construction engineering"],
  "0413": ["business administration", "management", "менеджмент"],
  "0311": ["economics", "экономика"],
  "0912": ["medicine", "медицина", "mbbs"],
  "0541": ["mathematics", "математика", "applied mathematics"],
  "0533": ["physics", "физика"],
  ...
}
```

Нормализация: lower, удаление degree-токенов (уже есть `matching.content_tokens`), затем точное
вхождение синонима; fallback — Jaro-Winkler ≥ 0.92 по токенам. Никаких эмбеддингов на первом этапе.

### 3.2. Knock-out'ы (строка листится в `EXCLUDED`, не ранжируется)

Только то, что уже разрешено правилами проекта, плюс страна:

1. `country ∈ excluded_countries`
2. Подтверждённый hard-filter из `eligibility.py` (дедлайн прошёл, набор закрыт, подтверждённый
   минимум не выполнен)
3. `degree != level` — на уровне retrieval
4. `field_match == 0`

**Не** knock-out: непрочитанное требование, test-optional, шкала GPA не совпала, бюджет (это корзина
`OUT_OF_BUDGET`, а не исключение — семья может передумать).

### 3.3. Pre-score и отбор на верификацию

Сейчас 40 → 20 срезаются по «страна + рейтинг» **до** того, как предпочтения хоть на что-то повлияли.
Новое правило:

```
pre_fit = aggregate(известные оси из {country, programme_standing, climate, city, university_size,
                    campus, workload, est_cost_band})           # та же геометрика §4.5
pre_key = pre_fit × coverage^γ
отбор: жадно по pre_key с ограничением max_per_country = ceil(verify_limit / 4)
```

`est_cost_band` ∈ {low, medium, high, very_high} — от агента, помечен `unverified`, **используется
только здесь** и никогда не показывается как число. Диверсификация по странам на этапе отбора —
чтобы верификационный бюджет не ушёл целиком в одну страну.

---

## 4. Ranking v2

### 4.1. Веса из приоритетов — Rank-Order Centroid

Пользователь ранжирует 6 групп. Вес группы k из n:

```
w_k = (1/n) · Σ_{j=k..n} 1/j
```

Для n = 6: `[0.408, 0.242, 0.158, 0.103, 0.061, 0.028]`. Внутри группы вес делится:

| Группа | Оси и доли |
|---|---|
| funding | funding_fit 0.5, affordability 0.5 — **× criticality** (nice_to_have 0.5 / important 0.75 / decisive 1.0) |
| academic | academic_fit 0.6, programme_standing 0.4 |
| country | country 1.0 |
| city_climate | city 0.5, climate 0.5 |
| career | career 0.5, post_study_work 0.5 |
| campus_life | university_size ⅓, campus ⅓, workload ⅓ |

`extracurricular` из скоринга вузов **удалён**: он одинаков для всех строк и не различает вузы.
Он уже участвует в `admissions_fit_for` (порог STRONGER_FIT) → через него влияет на корзину (§5).

### 4.2. Утилиты по осям

Каждая ось возвращает `value ∈ [0,1]` **или** `UNKNOWN` **или** `NOT_APPLICABLE` + причину.
`ε = 0.02` — пол для логарифма; фактически вето, но не NaN.

| Ось | Формула |
|---|---|
| **academic_fit** | MET: `clip(0.6 + 2·margin, 0.6, 1.0)`, где margin = средний относительный запас над числовыми минимумами (уже считается в `admissions_fit_for`); MET без числовых минимумов: 0.75; PENDING: 0.5; GAP: 0.15; NEEDS_CLARIFICATION: UNKNOWN |
| **funding_fit** | CONFIRMED 1.0 · COMPETITIVE 0.7 · LIMITED 0.3 · NOT_ELIGIBLE ε · UNKNOWN → UNKNOWN |
| **affordability** | r = gap / ceiling (потолок = `max_acceptable_gap` иначе `max_annual_budget`, конвертированный как сейчас). r ≤ 1 → 1.0; 1 < r ≤ 1.5 → `1 − 1.4·(r−1)` (r=1.5 → 0.3); r > 1.5 → ε. ceiling = 0: gap = 0 → 1.0 иначе ε. gap или ceiling неизвестны → UNKNOWN |
| **country** | preferred → 1.0; вне списка → 0.35; список пуст → N/A; excluded → knock-out |
| **programme_standing** | rank ≤ target_band → 1.0; иначе кусочно-линейно по `ln(rank)` через якоря (1→1.0, 100→0.8, 500→0.5, 1500→0.2), дальше 0.1; нет ранга → UNKNOWN. rank = консенсус-ранг §6.6 |
| **city / climate / university_size / workload** | пред = any → N/A; атрибут unknown → UNKNOWN; совпало → 1.0; по лестнице: 1 ступень 0.75, 2 — 0.5, дальше 0.25. Лестницы: city [small, medium, large, metropolis]; climate [cold, temperate, mediterranean, warm, tropical]; workload [moderate, demanding, very_demanding]; size [small, medium, large] |
| **campus** | без порядка: совпало 1.0, иначе 0.25; any → N/A; unknown → UNKNOWN |
| **career** | не ценит ни internships, ни coop → N/A; coop ценит и подтверждён → 1.0; internships подтверждены → 0.8; страница есть без конкретики → 0.5; иначе UNKNOWN |
| **post_study_work** | не нужен → N/A; months известны → `clip(months/24, ε, 1)`; текст есть, месяцы не распарсились → UNKNOWN (честно) |

### 4.3. Агрегация

```
K  = оси со state == known
fit = exp( Σ_{i∈K} w_i · ln(max(u_i, ε)) / Σ_{i∈K} w_i )
coverage = Σ_{i∈K} w_i / Σ_{i∈K∪UNKNOWN} w_i            # N/A не входит ни в числитель, ни в знаменатель
sort_key = fit · coverage^γ,   γ = 0.5 (config UNIMATCH_RANKING_GAMMA)
```

Почему так:
- **Некомпенсаторность.** affordability = ε при весе 0.2 даёт множитель `ε^0.2 ≈ 0.46` — вуз падает
  вдвое, что бы ни было по остальным осям. В аддитивной модели тот же провал стоил 9 % шкалы.
- **Объяснимость.** В log-пространстве это взвешенная сумма: каждая ось видна со своим весом и
  вкладом `w_i·ln(u_i)`; UI показывает `u_i`, `w_i` и причину — как сейчас.
- **coverage отдельно.** Отвечает на «насколько мы уверены», а не «насколько подходит». В UI две
  колонки и две сортировки; `sort_key` — дефолтная.

Замечание по γ: строки «только из каталога» (известны страна + климат) получают fit ≈ 1.0 при
coverage ≈ 0.3 → sort_key ≈ 0.53 — середина таблицы, корзина `NEEDS_CLARIFICATION`. Это желаемое
поведение: они не наверху и не потеряны. Если продуктово надо жёстче — γ = 1.

### 4.4. Что показываем вместо «6.5 / 10»

`fit 0.83 · подтверждено 97 %` + корзина + раскрывающийся список осей. Число `0.83` подписано:
*«соответствие вашим приоритетам по подтверждённым данным, не вероятность поступления»* (дисклеймер
уже есть в схеме `ExplainableScore.disclaimer`).

### 4.5. Re-rank без краулинга

`rank(results, profile)` — чистая функция от сохранённых `ProgramResult` (claims, checks, funding,
`catalog_attributes`) и профиля. Эндпоинт `POST /api/runs/{id}/rerank` (§9) вызывает её и
перезаписывает `ranking`, `bucket`, `score_total`. Ноль fetch'ей — тест T8.

### 4.6. Результат на демо-корпусе (референс-реализация)

Профиль: CS bachelor, KZ, IELTS 7.0/W6.0, потолок 6 000 USD, climate temperate, приоритеты по умолчанию.

| # | Университет | v1 score | **fit** | **cov** | key | Корзина |
|---|---|---|---|---|---|---|
| 1 | Groningen | 6.39 | 0.83 | 0.97 | 0.81 | PLAUSIBLE |
| 2 | KU Leuven | 5.92 | 0.80 | 0.94 | 0.78 | PLAUSIBLE |
| 3 | Toronto | 5.54 | 0.82 | 0.77 | 0.71 | PLAUSIBLE |
| 4 | Tokyo | 5.18 | 0.72 | 0.94 | 0.70 | PLAUSIBLE |
| 5 | TU Delft | 5.93 | 0.68 | 0.97 | 0.67 | AMBITIOUS (IELTS W gap) |
| … | | | | | | |
| 12 | **UBC (был #1)** | **6.54** | **0.43** | 0.97 | 0.42 | **OUT_OF_BUDGET** (21 471 USD при потолке 6 000) |
| 13 | Aalto (был #3) | 6.18 | 0.42 | 0.94 | 0.41 | OUT_OF_BUDGET |

Чувствительность к климату (приоритет `city_climate` на 1-м месте):
- **warm** → NUS поднимается с #11 на #5, Arizona State с #15 на #10, Toronto падает с #3 на #8.
- **cold** → Oslo с #14 на #6, Aalto с #13 на #8.
В v1 порядок топ-5 не менялся ни при каком климате.

Сбалансированный шортлист: 4 PLAUSIBLE + 3 AMBITIOUS и честная пометка *«0 well-placed вариантов
(хотели ≥ 2)»* — на этом корпусе для этого профиля их действительно нет.

---

## 5. Portfolio

### 5.1. Корзины

```
NEEDS_CLARIFICATION  admissions_fit == INSUFFICIENT_DATA
OUT_OF_BUDGET        r > τ(criticality):  decisive 1.5 · important 2.5 · nice_to_have ∞
WELL_PLACED          STRONGER_FIT ∧ funding CONFIRMED ∧ r ≤ 1
PLAUSIBLE            fit ∈ {STRONGER, PLAUSIBLE} ∧ funding ∈ {CONFIRMED, COMPETITIVE} ∧ (r неизвестен ∨ r ≤ 1.5)
AMBITIOUS            всё остальное (в т.ч. GAP по одному требованию с планируемой пересдачей)
EXCLUDED             knock-out (§3.2)
```

Корзина — категориальный вывод из уже существующих трёх независимых суждений (eligibility,
admissions fit, funding fit) + бюджет. Ничего нового не «предсказывается». Названия в UI намеренно
не «safety/match/reach»: *safety* читается как обещание.

### 5.2. Сбалансированный шортлист

```python
@dataclass
class Quotas:            # параметры профиля/организации, не константы
    size: int = 10
    min_well_placed: int = 2
    min_plausible: int = 4
    max_ambitious: int = 3
    max_per_country: int = 3
```

Алгоритм (детерминированный, `O(n log n)`):
1. Отсортировать по `(−sort_key, id)`.
2. Добрать `min_well_placed` из WELL_PLACED, затем `min_plausible` из PLAUSIBLE, соблюдая
   `max_per_country`. Недобор → note *«найдено N, хотели ≥ M»*.
3. Заполнить остаток по `sort_key` из {WELL_PLACED, PLAUSIBLE, AMBITIOUS}, соблюдая
   `max_ambitious`, `max_per_country`.
4. OUT_OF_BUDGET / NEEDS_CLARIFICATION / EXCLUDED — отдельные секции ниже шортлиста, с причиной.

Пользовательские решения (approve/reject/maybe) остаются поверх: reject убирает из портфеля и
запускает добор.

---

## 6. Research agent

### 6.1. Интерфейс

```python
class ResearchAgent(Protocol):
    async def discover(self, q: DiscoveryQuery) -> DiscoveryResult: ...
    async def locate_pages(self, lead: CandidateLead, programme: ProgrammeQuery) -> PageSet: ...
    async def extract_claims(self, page: FetchedPage, wanted: list[ClaimType], ctx: ExtractionContext) -> list[ProposedClaim]: ...
    async def programme_brief(self, lead: CandidateLead, programme: ProgrammeQuery, evidence: list[Claim]) -> AdvisorCommentary: ...
    async def applicant_commentary(self, result: ProgramResult, profile: ApplicantProfileIn) -> AdvisorCommentary: ...  # только profile_aware
    async def community_insights(self, lead: CandidateLead, programme: ProgrammeQuery) -> list[Insight]: ...
```

Реализации: `LlmResearchAgent` (прод; провайдер + web-search tool за конфигом),
`FixtureResearchAgent` (demo и тесты; отвечает из корпуса), `NullResearchAgent` (агент выключен —
текущее поведение). Вся сеть — **только через существующий `Fetcher`** (robots, rate-limit, PII-guard,
кэш). Агент получает от нас уже скачанный HTML/текст, а не ходит сам.

### 6.2. Схемы запросов/ответов

```python
class DiscoveryQuery(Base):                       # ← preferences_only всегда достаточно
    level: DegreeLevel
    fields: list[FieldCode]                       # ISCED коды + человекочитаемые лейблы
    intake_term: str; intake_year: int
    preferred_countries: list[str]; excluded_countries: list[str]
    language_of_instruction: list[str] = ["en"]
    curriculum_type: CurriculumType               # national / IB / A-level — не идентифицирует
    max_candidates: int = 60

class CandidateLead(Base):
    name: str; country: str; city: str | None; homepage: HttpUrl
    ror_id: str | None
    rankings: list[RankingEntry]                  # source, year, position, url — каждая с URL
    consensus_rank: int | None
    attributes: dict[str, str]                    # climate/city_size/size/campus — source помечен
    est_cost_band: Literal["low","medium","high","very_high","unknown"]   # только для pre-score
    evidence_urls: list[HttpUrl]
    confidence: float

class PageSet(Base):
    program_url: HttpUrl | None; admissions_url: HttpUrl | None
    costs_url: HttpUrl | None; scholarships_urls: list[HttpUrl]
    careers_url: HttpUrl | None
    rationale: dict[str, str]                     # почему именно эти URL
    rejected: list[tuple[HttpUrl, str]]           # что отвергнуто и почему (для трассы)

class ProposedClaim(Base):
    claim_type: ClaimType
    normalized_value: Any
    excerpt: str                                  # ДОЛЖЕН быть найден в тексте страницы
    source_url: HttpUrl
    subject_key: str | None
    academic_year: str | None
    source_specificity: SourceSpecificity
    confidence: float
```

### 6.3. Excerpt-валидатор (инвариант I2)

```
normalize(t) = lower, NFKC, схлопнуть пробелы, убрать пунктуацию
accept(claim, page) ⇔ normalize(claim.excerpt) ⊂ normalize(page.text)
                       ∧ 20 ≤ len(excerpt) ≤ 600
                       ∧ значение claim'а (число/дата) встречается внутри excerpt
```

Принятый claim сохраняется с `extraction_method="llm_assisted"` и `confidence = min(agent, 0.9)`;
затем проходит **те же** `enforce_source_hierarchy`, `apply_freshness`, `find_conflicts`, что и
rule-based. Rule-based extractors остаются и работают первыми; агент — эскалация, когда они вернули
NOT_FOUND (по аналогии с Playwright-tier).

### 6.4. Приватность — два режима

| Поле | preferences_only (default) | profile_aware (opt-in) |
|---|---|---|
| level, fields (ISCED), intake, preferred/excluded countries, language, curriculum_type | ✓ | ✓ |
| citizenship, second_citizenship, education_country, education_system | ✗ | ✓ (нужны для стипендий и country-specific requirements) |
| GPA + шкала, IELTS/TOEFL/SAT баллы, curriculum_results | ✗ | ✓ |
| budget ceiling, criticality | ✗ | ✓ |
| activities / achievements (summary без evidence_links) | ✗ | ✓ |
| display_name, evidence_links, class_rank, даты тестов | ✗ | **✗ никогда** |

Что даёт opt-in пользователю (текст согласия в UI): поиск country-specific страниц («requirements
for applicants with a Kazakhstani attestat»), стипендий по гражданству, и `applicant_commentary` (§7).
Технические условия: провайдер с no-training / zero-retention условиями (конфиг
`UNIMATCH_LLM_PROVIDER`, `UNIMATCH_LLM_DATA_POLICY_ACK=true` — прод не стартует без явного ack);
запись в audit log `research_privacy_changed` (без содержимого).

Тест I3 — как существующий тест на PII в audit log: строим промпт для демо-профиля в режиме
`preferences_only` и утверждаем, что в нём нет `"4.8"`, `"7.0"`, `"Kazakhstan"`, `"6000"`, имени.

### 6.5. Промпты (v1; версия хранится в кэше как `prompt_version`)

**Общая system-часть (все операции):**
```
You are a research assistant inside ASHYQ Apply. You find and quote official information about
university programmes. You never estimate, infer or predict. If a page does not state a value,
the answer is NOT_FOUND. Every value you return must be accompanied by a verbatim excerpt from
the page that contains it. Prefer the most specific official source: programme page for this
intake > programme page > university admissions page > application portal > scholarship
administrator > government. Rankings and aggregators may identify a university; they may never
support a requirement, a price or a deadline. Output strictly the JSON schema given; no prose.
```

**discover** (user-часть; вход = DiscoveryQuery):
```
Task: list up to {max_candidates} universities that offer a {level} programme in {fields} taught
in {language}, in {preferred_countries or "any country"} excluding {excluded_countries}, with
intake {intake_term} {intake_year}. Use ranking tables (QS, THE, ARWU, US News, QS/THE by subject,
recognised national rankings) as the discovery source. For each: name, country, city, official
homepage, every ranking position you found with its source, year and URL; climate and city-size
if a reliable source states them (say which); an estimated tuition band for international
students (low <5k USD, medium 5–15k, high 15–30k, very_high >30k) flagged as unverified; and
a confidence 0–1. Do not list a university you cannot give an official homepage for.
```

**locate_pages** (вход = lead + programme; агенту передаётся sitemap-выборка и до N ссылок с
главной, добытые нашим Fetcher):
```
Task: for {university} ({homepage}), identify the official pages for the {level} programme in
{field} for intake {intake}: (1) the programme page itself, (2) the international admissions /
entry-requirements page, (3) tuition fees / cost of attendance, (4) every scholarship page
relevant to international {level} applicants, (5) careers / internships if present. Candidate
URLs from the site's sitemap and navigation are listed below; you may propose others on the same
registrable domain only. Reject index pages, news, staff pages and other degree levels, and say
why for each rejection. Return NOT_FOUND for a category rather than a weak guess.
```

**extract_claims** (вход = текст страницы + список ClaimType с описаниями):
```
Task: from the page text below, extract only the following facts if they are explicitly stated:
{wanted claim types with one-line definitions}. For each fact return the normalised value, the
verbatim excerpt (20–600 characters, copied exactly), the academic year it applies to if stated,
and how specific the source is. Per-section English minimums are separate facts from the overall
minimum. A grade minimum must come with the scale it is published on. If the page states that a
test is optional, return the policy, not a minimum. Return nothing for anything not on the page.
```

Промпты `applicant_commentary`, `programme_brief`, `community_insights` — в §7 и §8.

### 6.6. Рейтинги: веса авторитетности и консенсус-ранг

| Источник | w |
|---|---|
| QS World, THE World | 1.0 |
| QS / THE by Subject — предмет совпал с ISCED-полем | 1.3 |
| ARWU, US News Best Global | 0.8 |
| Нишевые предметные (CSRankings и т.п.) при совпадении поля | 1.0 |
| Национальные (CHE, Guardian, Maclean's, Nikkei…) | 0.6 |
| Агрегаторы, блоги, «Top-10 for…» | 0 (отбрасываются) |

Год: вес × 0.85 за каждый год старше текущего (макс. 3 года назад, дальше — 0).
`consensus_rank = exp(weighted_median(ln(rank_i), w_i))` — медиана устойчива к одному выбросу.
Каждый `RankingEntry` хранится с URL и годом (схема есть); сам консенсус — производное, с
объяснением «медиана из N источников».

### 6.7. Кэш и стоимость

Ключи кэша строятся только из `DiscoveryQuery`/`ProgrammeQuery` (preferences-derived) → общий для
всех пользователей и тенантов. Порядок обращения: кэш → rule-based → агент → excerpt-валидатор →
кэш. Оценка (грубая, уточнить на пилоте): холодный прогон 20 вузов ≈ 60–100 страниц через
`extract_claims` ≈ 0.5–1 M входных токенов — единицы USD; при hit-rate 70 % — < 1 USD. Лимит
`UNIMATCH_AGENT_BUDGET_PAGES_PER_RUN` (default 120) — превышение → остальное `NOT_FOUND` с
диагностикой «бюджет исследования исчерпан», не тихий обрыв.

---

## 7. Advisor commentary — суждение ИИ вне score

Решение: ИИ даёт качественный комментарий **рядом** со score, никогда внутри. Два режима:

| Режим | Когда | Вход | О чём |
|---|---|---|---|
| `programme_brief` | всегда (в т.ч. preferences_only) | claims программы, community insights | «Что эта программа официально требует и на что, по данным студентов, смотрит» — про программу, не про абитуриента |
| `applicant_commentary` | только `profile_aware` | + профиль, requirement_checks, funding, ranking.axes | «Где вы сильны, где риск, что спросить у приёмной комиссии» |

```python
class AdvisorCommentary(Base):
    mode: Literal["programme_brief", "applicant_commentary"]
    summary: Str600
    strengths: list[Str300]      # ≤ 4
    concerns: list[Str300]       # ≤ 4, каждая ссылается на ≥1 claim_id
    questions_to_ask: list[Str300]   # ≤ 4 → создаются как UnresolvedQuestion(origin="advisor")
    evidence_claim_ids: list[str]
    model: str; prompt_version: str; generated_at: datetime
    disclaimer: str = "Advisory text generated from the cited sources. Not a prediction of any decision."
```

**Валидатор комментария** (иначе комментарий отбрасывается, лог, ≤ 1 повтор):
1. Каждое число в тексте встречается в `evidence_claim_ids` или в профиле (для applicant-режима).
2. Запрещённые паттерны: `\d+\s?%`, `chance`, `likely|unlikely to (be )?admit`, `guarantee`,
   `safety school`, `you will get`.
3. Каждая `concern` содержит хотя бы один `claim_id` из списка.
4. Язык вывода = язык интерфейса пользователя (ru/kk/en), но claim-цитаты — на языке источника.

**Промпт `applicant_commentary`:**
```
You advise an applicant on one programme. You have: the programme's verified claims (each with an
id, value and excerpt), the applicant's profile, and the requirement checks the system already
computed. Write for the applicant, in {ui_language}. Say where the profile clearly exceeds a
published requirement, where it sits at or below one, and what is unknown. Reference claim ids in
square brackets after each factual statement. Do not estimate odds, do not use percentages, do
not rank this programme against others, do not invent requirements that are not in the claims.
If a requirement check is PENDING or NEEDS_OFFICIAL_CLARIFICATION, phrase it as a question the
applicant should ask the admissions office, and put it in questions_to_ask. At most 4 items per
list. Output the JSON schema only.
```

---

## 8. Community insights

### 8.1. Источники (в порядке предпочтения)
1. Собственный social-модуль ASHYQ Apply (threads/posts с тегом вуза) — наш, с датами и авторами.
2. Официальные student-blogs и student-union страницы на домене вуза (это официальные источники
   ярусом ниже приёмной комиссии).
3. Публичные форумы: The Student Room, College Confidential, GradCafe.
4. Reddit — только через web-search инструмент LLM-провайдера, с обязательным URL; собственного
   клиента Reddit Data API не пишем (ToS/коммерческий тир/миграция на Devvit — см. DESIGN §6).

### 8.2. Схема и правила

```python
class Insight(Base):
    topic: Literal["extracurriculars", "essays", "scholarships", "interviews", "culture", "cost_of_living", "other"]
    statement: Str300           # всегда «students report that …»
    quote: Str600
    url: HttpUrl; source_type: Literal["ashyq_community", "official_student_blog", "student_union", "forum"]
    posted_at: date | None; retrieved_at: datetime
    corroborated_by: int        # число независимых источников с тем же statement
```

Показ: `source_type ∈ {ashyq_community, official_student_blog, student_union}` **или**
`corroborated_by ≥ 2`. URL перепроверяется Fetcher'ом при сохранении — недоступен → инсайт
отбрасывается. TTL 365 дней. UI: четвёртая вкладка «Что говорят студенты» с баннером
*«Мнения студентов. Не официальная позиция университета и не влияет на подбор»*.

Red flags по активностям → `UnresolvedQuestion(origin="community")`:
*«Несколько студентов сообщают, что на этом факультете проекты с кодом ценятся выше сертификатов
курсов [url, url]. В вашем профиле 3 сертификата и 0 проектов — хотите это учесть?»* Формулировка
как вопрос — проверяется тем же валидатором запрещённых паттернов (§7).

**Промпт `community_insights`:**
```
Task: find what current or former students publicly say about applying to the {level} programme
in {field} at {university}: what the selection appears to value (activities, essays, interviews),
how scholarships work in practice, cost of living, culture. Use only pages you can cite by URL.
For each statement give a verbatim quote, the URL, the post date if visible, and the source type.
Phrase every statement as "students report that …". Do not state anything as the university's
official position. Do not include anything about a named individual. Return at most 8 items.
```

---

## 9. API и UI

### 9.1. API
| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/api/runs/{run_id}/rerank` | body `{priorities?, preferences?, funding?, gamma?}` → пересчёт `ranking`/`bucket`/`score_total` без fetch; 200 с числом строк |
| `GET` | `/api/runs/{run_id}/results` | + поля `ranking`, `commentary`, `insights`; параметры `sort=key|fit|coverage|gap|deadline`, `bucket=` |
| `GET` | `/api/runs/{run_id}/shortlist` | `{chosen: [...], notes: [...], quotas}` |
| `PATCH` | `/api/profile/{id}/research-privacy` | `{research_privacy}` с записью в audit |
| `GET` | `/api/meta/capabilities` | + `ranking_version`, `agent: {enabled, model, privacy_mode}` |

### 9.2. UI
- **Preferences:** блок «Что важнее?» — 6 карточек drag-and-drop; спойлер «Расширенные веса»
  (текущие слайдеры). Тумблер «Разрешить использовать мой профиль для поиска» с текстом согласия.
- **Shortlist:** колонки `Соответствие` (fit) · `Подтверждено` (coverage) · `Корзина`; сверху блок
  «Сбалансированный шортлист» с notes; ниже секции OUT_OF_BUDGET / NEEDS_CLARIFICATION / EXCLUDED.
  Кнопка «Пересчитать» после смены приоритетов — мгновенно.
- **Detail:** вкладки Eligibility · Admissions fit · Funding · **Advisor** (§7) · **Students say** (§8).

---

## 10. Тесты и гейты

### 10.1. Golden-тесты ranking v2 (`tests/test_ranking_v2.py`)
| # | Тест |
|---|---|
| T1 | Строка с r = 3.6 и всеми остальными осями = 1.0 ранжируется ниже любой строки с r ≤ 1 и fit ≥ 0.6 |
| T2 | Две строки, отличающиеся только климатом: при `city_climate` на 1-м месте порядок меняется на противоположный при смене предпочтения |
| T3 | Перевод оси из known в UNKNOWN не понижает fit; понижает coverage ровно на её долю веса (I4) |
| T4 | N/A-ось не влияет ни на fit, ни на coverage (I5) |
| T5 | Excluded country → `knocked_out_by`, `bucket=EXCLUDED`, `sort_key=0` |
| T6 | Детерминизм: 1 000 перестановок входа → идентичный вывод (I6) |
| T7 | Портфель: квоты соблюдены; недобор → note; `max_per_country` не нарушен |
| T8 | `rerank` меняет порядок и делает **0** вызовов Fetcher (мок с assert) |
| T9 | Каждая ось имеет непустой `reason` и `weight` (I8, порт существующего теста) |
| T10 | Веса ROC суммируются в 1 ± 1e-9; порядок групп монотонен |

### 10.2. Агент
| # | Тест |
|---|---|
| A1 | Промпт-билдер в `preferences_only` не содержит PII демо-профиля (I3) |
| A2 | Excerpt-валидатор отбрасывает claim с цитатой, которой нет на странице; принимает — с точной; отбрасывает — с числом вне цитаты |
| A3 | Ключ `research_cache` не зависит от профиля (два разных профиля с одинаковыми предпочтениями → один ключ) |
| A4 | Комментарий с `%`/«chance» отбрасывается валидатором |
| A5 | Insight без URL или с недоступным URL не сохраняется |
| A6 | `NullResearchAgent` → поведение байт-в-байт равно текущему (регрессия) |

### 10.3. Гейты качества перед включением агента в проде (canary из `docs/CANARY_AUDIT.md`)
| Метрика | Сейчас | Гейт |
|---|---|---|
| Programme-page recall (10 вузов) | 1 / 10 | ≥ 7 / 10 |
| Category-page recall (admissions/costs/scholarships) | 26 / 30 | ≥ 27 / 30 |
| Материальные false positives | 0 | 0 |
| Claims, отброшенные excerpt-валидатором | — | измеряем и публикуем в `docs/` |
| Стоимость холодного прогона | — | ≤ бюджет, согласованный после пилота |

---

## 11. План внедрения

| Этап | Содержание | Файлы | Оценка* |
|---|---|---|---|
| **0. Ranking v2 + portfolio** | `domain/ranking_v2.py`, `domain/priorities.py`, `domain/fields.py` (ISCED), схемы §2.1–2.2, стадия assess → `rank()`, `catalog_attributes` на verify, `rerank` + `shortlist` эндпоинты, флаг `UNIMATCH_RANKING_VERSION=2`, тесты T1–T10 | backend: schemas/profile.py, schemas/result.py, pipeline/runner.py, api/routes_results.py, новые domain-модули, tests | 3–4 дн. |
| **1. Каркас агента** | `adapters/research/{base,null,fixture}.py`, `ExcerptValidator`, миграция `research_cache`, прокладка в verify/funding как эскалация, тесты A2, A3, A6 | adapters/research/*, migrations/, pipeline/runner.py | 2–3 дн. |
| **2. `LlmResearchAgent.locate_pages` + `extract_claims`** | провайдер за конфигом, промпты §6.5, prompt_version, бюджет страниц, тест A1, прогон canary, отчёт в `docs/` | adapters/research/llm.py, config.py, docs/ | 4–5 дн. + eval |
| **3. `discover` + retrieval** | рейтинги с весами §6.6, консенсус-ранг, pre-score и диверсифицированный отбор §3.3, замена `LiveDiscoveryAdapter` (реестр остаётся как seed/whitelist) | adapters/research/llm.py, adapters/discovery/*, domain/rankings.py | 3 дн. |
| **4. Advisor + Community** | §7, §8, валидаторы, тесты A4, A5, UnresolvedQuestion origins | adapters/research/llm.py, domain/advisor.py, schemas | 3 дн. |
| **5. UI** | приоритеты DnD, privacy-тумблер, колонки fit/coverage/bucket, портфель, вкладки Advisor / Students say, i18n строк | frontend/src/screens/*, types.ts, e2e | 3–4 дн. |

\* один разработчик, без учёта ревью; этап 0 можно начинать сегодня — он не зависит от агента и
уже даёт видимый результат (UBC уходит с #1, климат начинает работать).

Переходный период: v1 `preference_score` продолжает считаться и храниться, пока флаг = 1; фронт
читает `ranking` если есть. После двух релизов v1 удаляется вместе с тестами на его формулу
(тесты на объяснимость портируются на v2 в этапе 0).

---

## 12. Открытые вопросы (не блокируют этап 0)

1. **LLM-провайдер и web-search инструмент** для прода: нужен no-training/zero-retention договор.
   Кандидаты и цены — отдельная записка после пилота этапа 2.
2. **γ по умолчанию** — 0.5 или 1.0? Решить по отзывам на демо после этапа 0.
3. **Квоты портфеля по умолчанию** (2/4/3, ≤3 на страну) — подтвердить с консультантами по
   поступлению; сделать настраиваемыми на уровне организации.
4. **Языки UI для комментариев** — ru/kk/en с первого релиза или только ru/en?
5. **Post-study work в месяцах** — нужен новый `ClaimType.POST_STUDY_WORK_MONTHS` и парсер для
   government-адаптера; до этого ось будет UNKNOWN для всех (честно, но снижает coverage равномерно).
