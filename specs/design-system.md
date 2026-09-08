# ASHYQ Apply Design System

> Версия 1.0 · 2026-09-08 · living source: `frontend/design-system.html`

## 1. Назначение

Система помогает школьнику и родителю принимать сложные решения о поступлении спокойно и осознанно. Она соединяет бренд-идею **Open Chapter / Ашық бет** с продуктовым контрактом **доказательство рядом с числом**.

Главная формула:

> Тёплая редакторская подача + строгая доказательная структура + понятный следующий шаг.

Источники решения, по убыванию специфичности:

1. `../../ashyq_brand/ashyq_brandbook_v1-1.md` — идентичность бренда; v1.1 отменяет лаймовый v1.0.
2. `../epics.md` §3, E00, E16 и §7 — поведение продукта, доверие, доступность и инвентарь.
3. `../photo-references/design_system.png` и `hero_section_example.png` — настроение, воздух, композиция и фотостиль.
4. `frontend/src/styles/tokens.css` — исполняемый контракт токенов.

## 2. Принципы

1. **Открытая глава.** Свободное пространство и открытая рамка показывают движение вперёд без буквальной книги или двери.
2. **Источник рядом.** Стоимость, дедлайн, требование, стипендия и любое другое материальное значение имеют `EvidenceLink` и дату проверки в одном действии.
3. **Никаких вероятностей.** Говорим «соответствие вашим приоритетам»; не используем шанс, вероятность, проценты и светофор поступления.
4. **Неизвестное — полноценное состояние.** Объясняем, чего нет, где искали и что можно сделать. Не показываем прочерк, пустоту или ноль.
5. **Сначала 360 px.** Таблица становится карточками; детали раскрываются по запросу; основное действие остаётся доступным большим пальцем.
6. **Три регистра доверия.** Факт, оценка и мнение ИИ отличаются формой, подписью и композицией, а не только цветом.
7. **Одна мысль на поверхность.** Спокойная плотность, не более трёх чипов в строке, один главный CTA.
8. **Три языка равноправны.** RU, KK и EN используют один компонентный контракт; проверяем +30% длины.
9. **Семантика не равна цвету.** Каждый статус имеет текст, знак и цвет; ключевое состояние доступно скринридеру.
10. **Обратимость и честность.** Решения можно изменить, демо и live всегда различимы, опасные действия подтверждаются.

## 3. Визуальное направление

### 3.1 Характер

`intelligent · warm · honest · globally oriented · clear · ambitious · human`

Не допускаются: лайм, неон, декоративные градиенты, glassmorphism, 3D, крипто/игровая эстетика, гербы, щиты, лавры, глобусы, буквальные книги и двери, фальшивые acceptance letters, стоковые улыбки и AI-люди под видом учеников.

### 3.2 Open Page

- Icon-size: две простые «страницы» с центральным отрицательным пространством.
- Editorial container: один открытый или срезанный угол; радиус 24 px только у больших страниц и фото.
- Route Line: `01 PROFILE → 02 SHORTLIST → 03 PREPARE → 04 APPLY`.
- Open Page не используется как декоративный паттерн поверх каждого блока; одного сильного появления на экран достаточно.

### 3.3 Фотография

- реальные люди в процессе, реальные города, кампусы и учебные моменты;
- естественный дневной свет, мягкие тени, тёплый Paper, чистое небо и воздух;
- кадр editorial/travel, без рекламной постановочности;
- подпись честно указывает источник фото и не выдаёт AI-персонажа за ученика.

## 4. Foundations

### 4.1 Цвет

Фирменные primitive-токены сохраняют точные HEX брендбука:

| Роль | HEX | Основное применение |
|---|---|---|
| Ashyq Ink | `#111827` | основной текст, тёмная поверхность, wordmark |
| Paper | `#F7F3EA` | светлый фон |
| Academic Blue | `#526DA6` | основной CTA, навигация, SAT |
| Library Burgundy | `#8E3F4C` | документы, application, риск |
| Scholar Teal | `#437A78` | IELTS, подтверждённые действия |
| Parchment Gold | `#C5A66B` | премиальный акцент, pending border |
| Deadline Coral | `#E47A6A` | дедлайны и срочность |

Exact swatch и цвет текста — разные задачи. Scholar Teal, Gold и Coral не всегда проходят 4.5:1 как мелкий текст на Paper, поэтому компоненты используют AA-безопасные `--color-success`, `--color-warning` и `--color-deadline`, сохраняя точный фирменный цвет в рамке, знаке или крупной поверхности.

Рекомендуемая доля на брендовой поверхности: Ink 45%, Paper 30%, Academic Blue 12%, Teal 6%, Burgundy 4%, Gold или Coral 3%. В продуктовом UI это ориентир, не квота на каждый экран.

### 4.2 Типографика

| Регистр | Семейство | Применение |
|---|---|---|
| Brand / action | Manrope 600–800 | wordmark, кнопки, navigation, короткие продуктовые заголовки |
| Editorial display | Fraunces 400–700 | H1, начало раздела, большая «новая глава»; не формы и не таблицы |
| UI / body | Inter 400–700 | основной интерфейс, инструкции, формы, legal |
| Evidence / data | IBM Plex Mono 400–500 | суммы, даты, требования, идентификаторы, freshness, источники |

Шкала: `12 / 14 / 16 / 18 / 22 / 28 / 36 / 48`. Базовый текст — 16 px, таблица — не ниже 14 px. Для казахского обязательна проверка `Ә Ғ Қ Ң Ө Ұ Ү Һ І` во всех используемых начертаниях.

### 4.3 Геометрия

- Spacing: 4 pt; основные шаги `4 / 8 / 12 / 16 / 24 / 32 / 48`.
- Radius product: `4 / 8 / 12`.
- Radius editorial page / image: `24`, только на крупном контейнере.
- Touch target: минимум `44 × 44`.
- Elevation: три уровня, но основное разделение создают Paper, поверхности и border; тени редкие.
- Motion: feedback 120–180 ms, не более 200 ms; loading cycle — отдельное исключение; `prefers-reduced-motion` обязателен.

## 5. Семантические роли

Цвет — последний слой. Реальный API/UI state сначала получает понятную формулировку и знак.

| Namespace | Состояние | Текстовый паттерн | Знак | Tone |
|---|---|---|---|---|
| eligibility | met | Требование выполнено | ✓ | success |
| eligibility | pending | Ожидает проверки | ○ | warning |
| eligibility | gap | Есть несоответствие | ! | danger |
| eligibility | unverified | Не опубликовано | ? | neutral |
| eligibility | n-a | Не применяется | — + текст | neutral |
| admissions-fit | stronger | Сильнее по вашим приоритетам | ◆ | success |
| admissions-fit | plausible | Реалистичный вариант | ◇ | info |
| admissions-fit | ambitious | Амбициозный вариант | △ | warning |
| admissions-fit | no-data | Недостаточно подтверждённых данных | ? | neutral |
| funding | full-ride | Полное покрытие | ✓ | success |
| funding | full-tuition | Обучение покрыто | ✓ | success |
| funding | partial | Частичное финансирование | ○ | warning |
| funding | need-based | Зависит от финансового профиля | i | info |
| funding | not-eligible | Не соответствует условиям | ! | danger |
| funding | unknown | Условия не опубликованы | ? | neutral |
| bucket | well-placed | Хорошо подходит | ◆ | success |
| bucket | plausible | Реалистичный вариант | ◇ | info |
| bucket | ambitious | Амбициозный вариант | △ | warning |
| bucket | out-of-budget | Выше бюджета | ! | danger |
| bucket | needs-clarification | Нужно уточнить | ? | deadline |
| bucket | excluded | Исключено с причиной | × | neutral |
| freshness | fresh | Обновлено N дней назад | ● | success |
| freshness | aging | Данные устаревают | ◐ | warning |
| freshness | stale | Нужна повторная проверка | ! | deadline |
| mode | demo | Демо-данные | D | demo |
| mode | live | Живые данные | ● | success |
| origin | fact | Факт с официальной страницы | ▣ | info |
| origin | preference | Ваше предпочтение | ◇ | warning |
| origin | opinion-ai | Мнение ИИ | ✦ | danger surface |

## 6. Три регистра доверия

### Факт

`OriginMark(fact) + mono value + EvidenceLink + FreshnessBadge`.

Источник открывается в одном действии. Fixture никогда не выглядит как внешняя ссылка. Конфликт источников показывается рядом, а не скрывается выбором «удобного» числа.

### Оценка

`OriginMark(assessment) + verbal fit + named axes + Disclaimer`.

Постоянный дисклеймер:

> Соответствие вашим приоритетам по подтверждённым данным. Не вероятность поступления.

Три суждения — eligibility, admissions fit и funding — не объединяются в одну цифру.

### Мнение / ИИ

`AIGeneratedLabel + quote form + distinct surface + optional evidence links`.

Мнение помогает сформулировать вопрос или заметить риск, но не становится университетским фактом. Копирайт не использует тон уверенного пророчества.

### Unknown

Формула: **что неизвестно → где искали → действие**.

Пример: «Стоимость не опубликована на официальных страницах. Проверены admissions и fees. Спросить вуз».

## 7. Компонентная архитектура

### Core P0

`AppShell` · `BottomNav` · `SideNav` · `TopBar` · `CaseSwitcher` · `ModeBadge` · `Button` · `IconButton` · `Input` · `MoneyInput` · `DateInput` · `Select` · `Combobox` · `ChipInput` · `Checkbox` · `RadioCards` · `Toggle` · `Slider` · `Tabs` · `Accordion` · `Card` · `DataTable/CardList` · `StatusChip` · `EvidenceLink` · `FreshnessBadge` · `UnknownValue` · `FitMeter` · `CoverageRing` · `BucketHeader` · `Banner` · `Toast` · `Modal` · `BottomSheet` · `Drawer` · `Stepper` · `ProgressRing` · `EmptyState` · `ErrorState` · `Skeleton` · `Tooltip` · `Popover` · `Avatar` · `Tag` · `LanguageSwitcher` · `ThemeSwitcher` · `AIGeneratedLabel` · `Disclaimer` · `OriginMark`.

### R1 product patterns

- Onboarding: `MarketingHero`, `StepsStrip`, `DemoPreview`, `AgeGate`, `ConsentBlock`, `FirstRunChecklist`.
- Profile: `SectionCard`, `SufficiencyBanner`, `TestPicker`, `ScoreInput`, `ScaleConverter`, `TranscriptImportSheet`, `AutosaveIndicator`.
- Priorities: `PriorityCardList`, `CountryChipPicker`, `CriticalityCards`, `FundingShapeChecklist`, `PrivacyToggle`, `RunSummaryCard`.
- Research: `StageTimeline`, `LiveCounter`, `FindingsFeed`, `FailureList`, `RunBanner`.
- Shortlist: `BalancedShortlistPanel`, `BucketSection`, `ProgrammeCard`, `GapLine`, `DeadlineCountdown`, `DecisionButtons`, `ReasonSheet`, `WhyHerePanel`, `CompareTray`, `FilterBar`.
- Programme: `ProgrammeHeader`, `RequirementRow`, `AwardCard`, `CostBreakdown`, `EvidenceDrawer`, `ConflictCallout`, `AxisList`, `ShareSheet`.

Компонент документируется одинаково: anatomy, variants, states, responsive behavior, content contract, accessibility, keyboard, localization and evidence contract.

## 8. Композиционные паттерны

### Desktop table ↔ mobile card list

- Desktop: один понятный caption, заголовки 14 px, источники внутри соответствующей ячейки.
- Mobile: один объект = одна карточка; label/value/action идут вертикально; первичный CTA не теряется.
- Запрещено: сжимать таблицу до 11–12 px или превращать карточку в горизонтальный scroll без сигнала.

### Progressive disclosure

- Сначала ответ и следующий шаг.
- Затем причины по осям.
- Затем evidence drawer и история изменений.
- До первого shortlist собираются только обязательные данные; остальное подписано «улучшит точность».

### State completeness

Каждый интерактивный компонент проектируется минимум в состояниях: default, hover, focus-visible, active, disabled, loading, error, success. Контентная поверхность дополнительно имеет empty и unknown.

## 9. Voice & tone

- Коротко, конкретно, спокойно; без восклицаний и автоматического «Поздравляем».
- Один CTA начинается с глагола: «Проверить требования», «Спросить вуз», «Сравнить».
- Не обещаем результат: «Подходит по текущим критериям», а не «Тебе точно сюда».
- Причина рядом с решением: «Выше бюджета на ₸ …», а не только красный chip.
- Деньги, даты и числа форматируются по локали: `₸ 1 850 000`, `15 янв 2027`.

## 10. Definition of done

- 360 / 768 / 1024 / 1440 проверены визуально.
- Light и dark сохраняют смысл и иерархию.
- Contrast ≥ 4.5:1 для обычного текста; статус имеет знак и текст.
- Touch target ≥ 44 px; keyboard и focus-visible работают.
- RU / KK / EN помещаются без обрезания; проверен KK +30%.
- Empty, loading, error, success, disabled и unknown показаны.
- Все материальные значения имеют источник и freshness в одном действии.
- Нет вероятности, гарантии, фальшивых данных и скрытой неопределённости.
- `npm run audit:tokens`, typecheck, lint, unit и build зелёные.

## 11. Артефакты

- Living catalogue: `frontend/design-system.html`
- Component implementation: `frontend/src/design-system/DesignSystem.tsx`
- Tokens: `frontend/src/styles/tokens.css`
- 21st project context: `frontend/.21st/design.json`
- Foundation and component specifications: `specs/`
