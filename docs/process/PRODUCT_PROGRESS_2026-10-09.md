# Продуктовый прогресс ASHYQ Apply — 9 октября 2026

Срез UTC: 2026-10-08T23:48:46.374714+00:00. Ветка `task/product-research-recovery`.
Проверенная версия: `c7ece3c0a057a4fe6a8b8b5e43c3b17c8338cbd4`; следующие commits
добавляют только доказательства и передачу.

Реализовано **13 улучшений маршрута** в **16 уникальных frontend/test путях** за
два продуктовых раунда. Это11 изменений Home/Plan/Documents/Sources/Compare,
фильтров, выбора и API-ack перехода из Draft75, плюс2 нынешних изменения:
Find объясняет существующий остановленный/пустой run и ведёт к Progress, сохраняя
возвращённые строки; missing-list подсказка Documents учитывает Chosen by you
и Considering в Plan. Нынешний increment меняет ровно4 существующих файла.
19 meaningful новых frontend cases;27 старых test templates сохранили точные тела.
Автоповтора исследования, сбора документов или изменения решения не добавлено.

| Проверка | Актуальный наблюдённый результат |
|---|---|
| Doctor |5/5 PASS; environment-only, без source snapshot|
| Core |8/8 PASS; SQLite4369,95.28%; frontend301|
| Full |13/13 PASS одним свежим прогоном,17м33.49с|
| SQLite full |4369 уникальных PASS,32 предупреждения,95.28%,522.46с|
| PostgreSQL full |те же4369 уникальных ID PASS,32 предупреждения,380.12с;coverage не измерялось|
| Frontend |301 PASS в30 файлах — на69 больше исходных232; typecheck/lint/build PASS|
| Demo E2E |79 PASS,1 прежний viewport-skip,0fail/0not-run|
| Auth E2E |6 PASS|
| Static/dependency audit |Ruff/format/mypy386 и pip/npm audit PASS;0 известных vulnerabilities|
| Owned UI |5 native JPEG captures с AX/geometry/actions; desktop1131 и phone390, Progress route, exact KU hint, reload synthetic case/results|
| Docker/containers, hosted required checks, production |NOT RUN|
| Свежая принятая точность/полнота поиска |NOT RUN; старая серия UNSCORED/STOPPED|

Native full: `20261008T231450Z-check-c4cb266b`, testedHEADc7, initial snapshot
SHA-256 `7d2aac5dd661b438445f72d1b4dbb4ad50a80ab06f46ce8835b6cc971cc552eb`.
Core initialSHA0a0497a3 отличается metadata. Aefab8f76 независимо принял native13
и source16/protected1045/backend940; raw17full originals5,872,338B+3queue,
11core originals5,013,720B сохранены. Перекрывающиеся core/full/peer suites и
повторы DB не складываются в новые уникальные тесты.

C872aba86 проверил5 ограниченных критериев; A dbc9244b независимо принял эти пять synthetic UI критериев и сохранённые cleanup receipts. Body/document widths
совпали1131/1131 и390/390. На phone фильтры/первая строка ниже fold и доступны
обычной вертикальной прокруткой; все элементы не обещаны в первом viewport.
После native reload тот же выбранный синтетический case и20 результатов
доступны; query сбросился как ожидаемый ephemeral state. Root закрыл только
own preview, C закрыл собственную вкладку и восстановил viewport; ports5173/8099
свободны, исходная synthetic seed не изменена.

Полный initial manifest сохранён. Native E2E регенерировал38 PNG внутри snapshot:
24journey/12responsive+theme/2auth; остальные10,255 declared bytes точны. Первый
preview guard остановился до lock/DB/ports, отказ и complete mismatch inventory
сохранены. Отдельный helper учитывает только exact before/after delta3f645d11,
не переписывает manifest и не утверждает равенство нынешнего физического дерева
initial wholeSHA. В synthetic clone менялись stage/cancelled, но прежний completed
stage_state сохранился: Progress100% не доказывает реальную midrun/Worker остановку.
Optionalzero/no-run browser NOT RUN; unit controls остаются отдельными.

Первый раунд Draft75 остаётся qualified13-position composite7+4+2, source749.
Его initialfull9a79/05eade16 FAILED12/13 и23originals неизменны: E2E ожидал
старый `2 approved`. После узкой правки199 затронутые frontend4/E2E2 прошли.
Нынешний full13 относится к новой c7 версии; первый отказ не переименован в PASS.

Сравнивались5 продуктов: Unilight и официальные материалы BigFuture, UCAS,
Common App, MyStudyLife. Unilight62 matrix rows =11 свежих наблюдений,
11 публичных заявлений,6demо,22 исторических,9 непроверенных,3 закрытых согласием.
Проверены6/6 публичных demo-tab и7/7FAQ. Это не62 выполненные функции. Новый
закрытый кабинет полностью не пройден: обязательные соглашения не приняты;
private raw исключён из origin. Другие4 сервиса исследованы по официальным
описаниям, без проверки аккаунтов и эффективности.

Наше направление: применимое официальное основание выбора и полной стоимости →
конкретное следующее действие при неизвестности → долговечная личная подготовка.
Это гипотеза преимущества. Сохранены6 заданий и сравнительный протокол для16
взрослых участников,8desktop/8mobile; фактических участников/результатов0.

Следующий отдельный этап: **личные серверные отметки подготовки по пользователю,
case/result/версии checklist/itemref**, без автоматического импорта старых
localStorage ticks. B7b528036/A78236ea7 приняли только DESIGN_ONLY, не готовый код.
Нужны native ownership/entitlement, full checklist revision, refs до UI сортировки,
атомарный stale revision/CAS, late-response guard, requester-only export и erase;
отдельные migration/SQLite/PG/auth/device/logout/case/concurrency проверки.
Сейчас reload отметок проверен только в том же браузере; cross-device не реализован.

Для запуска остаются принятая свежая оценка поиска, публикация и полный
проверенный вошедший пользовательский путь. STOP65b5 не сбрасывается этой
продуктовой задачей; livegrant и точный expert selector-model остаются pending.
Draft75 и зависимый Draft текущего раунда (создание следующим шагом) — code review, не publication. Подробные материалы:
[PRODUCT_COMPLETION_PLAN](PRODUCT_COMPLETION_PLAN_2026-10-09.md),
[HANDOFF](HANDOFF.md), [native proof](evidence/product-loop/2026-10-09/recovery-round/final-native-peer/REPORT.md),
[UI proof](evidence/product-loop/2026-10-09/recovery-round/owned-ui/REPORT.md).
