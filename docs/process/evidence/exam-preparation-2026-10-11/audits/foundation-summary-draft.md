# Подготовка к экзаменам: foundation — черновик отчёта

**Дата:** 2026-10-11. **Статус:** локальный foundation реализован; финальное принятие native UI **PENDING**. Первая новая native Demo-проверка выявила конкретный дефект; повторный прогон после исправления и native Auth ещё не приняты. Этот документ не является финальной release-квитанцией.

Основа: сохранённые contracts, независимые static reviews и терминальные receipts. Root сообщил freeze owned source `e8fb18db`; Git/primary, приложение, браузер и провайдеры автор этого отчёта не запускал. Числа ниже прочитаны из сохранённых JSON/JUnit.

## 1. Что появилось

Один экран `#/preparation`, доступный из навигации, Home и Plan:

- **Goals & evidence:** требования к экзаменам из выбранной сохранённой программы; исходные пороги, компоненты, пояснения, цитаты и область применимости. Это просмотр сохранённого evidence, а не новый поиск или обещание персонального полного курса.
- **Practice:** три оригинальных starter-урока версии `starter-2026-10-11-v1`, по три задания: IELTS Reading — *stated evidence and inference*; SAT Math — *linear relations and proportional reasoning*; SAT Reading & Writing — *evidence and sentence clarity*. Всего **9 оригинальных вопросов** с объяснениями после отправки.
- **Progress:** сохранённые отправленные попытки, правильные/отвеченные задания и история; завершение означает «отправлено», а не «освоено». Собственная история включается в export (`study_attempts`).

Каталог IELTS Academic и Digital SAT указывает только реально доступные starters. TOEFL iBT, DET, HSK/HSKK и CSCA — **planned**: официальные внешние ссылки и ограничения редакции/приёма; соответствующих курсов здесь пока нет. Это metadata экзаменов, не универсальное требование ко всем программам. [Контракт](../proposals/backend/CONTRACT.md), [frontend contract](../proposals/frontend/CLIENT_CONTRACT.md), [review содержания](curriculum-review.md).

## 2. Доступ по подписке и сохранение

Новая практика разрешена по серверному education-entitlement: начавшийся действующий срок подписки в состоянии ACTIVE **или EXHAUSTED**. Исчерпанная квота исследования не отключает обучение. Research case unlock / CASE_FULL сами по себе не дают этот доступ. Pending, cancelled, expired, отсутствующая или некорректная дата начала не дают новый practice-доступ.

В режиме отключённых платежей UI честно пишет **Development starter access**; это не доказательство покупки или доступности коммерческого продукта. Billing объявляет включённые starters только при подтверждённом серверном `preparation_access`; отсутствующее поле не означает включение.

Отправленные попытки сохраняются для своего кейса. Повтор после ошибки сети использует тот же UUID и неизменённые ответы; другая отправка с этим UUID отклоняется. Собственная история и replay уже принятой попытки доступны после конца срока. Неотправленные ответы остаются только в текущей форме: refresh/выход из урока не обещают их сохранение. Практика не меняет введённые официальные IELTS/SAT/academic scores, не расходует research quota и не запускает провайдеров. **3/3 practice — не IELTS band, SAT scaled score, сертификат или прогноз поступления.**

Case/account/lesson intent guards исключают запоздалые ответы прежнего кейса/владельца; unsaved case сначала требует сохранения, signed-out state не запрашивает частную историю. Эти границы имеют component/API controls; полный native путь ещё не принят.

## 3. Как трактуются требования

- `unknown`, `locked`, `stale`, `conflicted` сохраняют своё значение: неизвестное или скрытое требование не считается отсутствующим или выполненным.
- Исходная scope по программе, degree, intake и группе заявителей не расширяется. Запись без подтверждённой области не становится правилом «для всех». Более позднее изменение профиля делает сохранённый snapshot stale.
- Overall и отдельные компоненты IELTS/SAT показываются отдельно. Урок Reading не удовлетворяет Writing/общий порог; практика SAT Math не заменяет общий официальный SAT score.
- Optional, waiver-check и неразрешённые альтернативы не превращаются в обязательность, предоставленный waiver или самостоятельно выбранное AND/OR. Scholarship и admission policies не объединяются.
- Current требует подходящего сохранённого официального evidence и применимой scope; discovery snippets и synthetic `fixture://` не становятся текущими официальными источниками. Здесь страницы повторно не загружаются.

Официальные сведения сверены в отдельном [audit экзаменов](official-exams.md) на 2026-10-11; это не новое подтверждение каталога программ, каждой цели или будущей редакции экзамена.

## 4. Сохранённые проверки и точные ограничения

| Проверка | Фактический результат | Квалификация |
| --- | --- | --- |
| Backend Ruff / format / mypy | все exit0 | Сохранённый static receipt; backend consumed bytes сохраняются при отдельном mobile delta. |
| Последний frontend typecheck / lint / build | все exit0 | `frontend-mobile-final`; before/after625 source pins совпали. |
| Frontend Vitest | **465 PASS**, 0fail/error/skip | До исправления найденного native same-value дефекта. Component fixtures не заменяют настоящий E2E. |
| Full backend, SQLite phase | **4653 PASS**, 0fail/error/skip; coverage **95.4354%** | Native cov floor92 сохранён; outside/startup attempts0; source unchanged; owned shutdown/runtime removal подтверждены. |
| Full backend, PostgreSQL phase | **4653 PASS**, 0fail/error/skip; coverage **95.4290%** | Те же 4653 test identities, повторно под другой DB-конфигурацией; это не9306 уникальных тестов. Native явные DB fixtures могут отличаться от phase default. |
| Synthetic demo seed | PASS: migrate/seed/query0,20 rows, order/buckets PASS | Свежая synthetic DB; provider none; external network OS_DENIED; runtime removed. Не live catalog/search evidence. |
| Native Demo, первый run `20261011T130607Z-demo` | **79 PASS /2 FAIL /1 прежний intentional skip /8 serial NOT_RUN**, всего90 | Оба desktop/mobile падают на новом Goals-flow; exit1, source unchanged. Новые submit/reload/mobile controls после него не исполнялись. |
| Native Demo после исправления | **PENDING** | Нужен новый завершённый receipt на исправленных bytes; исходный failed run сохраняется. |
| Native Auth | **PENDING** | Не переносить предыдущие E2E других версий. |

Full backend сохраняет все4531 прежние test identities и добавляет122 preparation cases (92 API +30 domain). Это проверка локальной инженерной реализации и offline native contracts. Reviewer отдельно оговаривает: реальная одновременная HTTP-гонка двух UUID-запросов и новый end-to-end HTTP account-delete для этой функции не доказаны последовательными controls. [Backend terminal review](backend-terminal-review.md), [frontend receipt](../evidence/frontend-mobile-final/result.json), [full backend](../evidence/backend-full/20261011T124000847599Z/result.json), [seed](../evidence/demo-seed-qualified/result.json).

**Выявленный native дефект:** выбор уже выбранной программы очищает plan и выставляет Loading, но неизменившиеся effect dependencies не запускают повторный запрос. Сохранённый trace имеет исходный plan GET200; API-ошибка этим наблюдением не установлена. Root готовит early-return для одинакового value и два controls: resolved и in-flight сохранение исходного запроса. Ни изменение timeout, ни ослабление native assertions не требуется. [Failed run](../evidence/e2e/20261011T130607Z-demo/run.json).

Mobile-layout статически рассчитан для390/320px, default font: шесть коротких labels при полных accessible names, цели>=44px, общий reserve/safe-area. Но native geometry и reachability controls в первом run были serial NOT_RUN; физический notch, text zoom и все прочие экраны этим packet не приняты. [Mobile review](mobile-layout-review.md).

## 5. Что пока не заявляется

Это foundation из трёх коротких starter-уроков. Полноценные IELTS/SAT courses, calibrated proficiency/mastery, официальный mock/score, эффективность обучения, покупка реального subscription, primary integration, production deployment и живое factual acceptance не подтверждены этими квитанциями. **Search quality: NOT_MEASURED. GLOBAL_PROVIDER_STOP / UNSCORED остаются закрытыми.** Финальная summary-квалификация ждёт исправления, свежего frontend gate и реальных завершённых Demo/Auth receipts от root.

## 6. Предлагаемые критерии следующего полного IELTS/SAT increment

Перед разработкой согласовать конкретный syllabus, объём уроков/заданий и роли преподавателя; слово «полный» использовать только для принятого покрытия.

1. **Покрытие:** проверяемая матрица IELTS Academic Listening/Reading/Writing/Speaking и всех утверждённых SAT Math / Reading & Writing domains; каждый обещанный урок реально содержит обучение, самостоятельную практику и разбор, а каждый обещанный день — завершённый learner path. Пробелы в матрице видны пользователю.
2. **Контент:** оригинальные или разрешённые тексты/аудио/изображения, версия и права для каждого asset; независимая предметная проверка всех ответов/объяснений. IELTS Writing/Speaking имеют понятные rubric, примеры и действующий путь качественной обратной связи — без имитации официального examiner score.
3. **План и прогресс:** ученик задаёт цель/срок/нагрузку; рабочий план сохраняется в своём кейсе. После reload/сети видны только подтверждённые данные; resume, retry, повторения и изменение цели проверены. Submission, completion и mastery различаются; официальный профиль не перезаписывается.
4. **Доступ:** term entitlement независимо от quota, понятный отказ/expiry, читаемая история после expiry; исключение другого кейса/владельца во всех async путях, export/deletion и реальные конкурентные retry controls. Billing обещает только поставленное и проверенное покрытие.
5. **UI:** keyboard/focus/error recovery, reduced motion, читаемость и последние действия над fixed bar на320/390; text zoom и safe insets добавить как отдельные измеряемые controls. Длинные planned notices не мешают доступным урокам.
6. **Принятие:** свежие type/lint/build/unit, обе native DB full gates с исходными assertions/floor, actual demo/auth lesson→submit→reload→progress/export и failure/retry/expiry controls на точных bytes; сохранённые receipts/cleanup. Любое обещание прироста band/score требует отдельно согласованной валидации на учащихся — passing software tests этого не доказывает.
