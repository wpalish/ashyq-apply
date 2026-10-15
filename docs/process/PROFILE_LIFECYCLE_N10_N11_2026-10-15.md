# Профиль Unimatch: N10/N11, 15 октября 2026

## Результат

Обе P1 из независимого разбора воспроизведены и исправлены. Дополнительный контроль выявил и закрыл потерю панели восстановления при отказе sessionStorage после первого create ACK. Исполняемый код: `9ca4d307a900a343d77025a95383a6f0aa4d70eb`, ветка `task/admissions-actions-today`, зависимый Draft PR88, base `task/shared-preparation-route`.

Это локальная приёмка перечисленных переходов. Весь продукт и все возможные переходы профиля не объявляются завершёнными.

## Причины и исправления

**N10:** ACK старого тела удалял envelope нового текста; accepted journal уже не участвовал в восстановлении. Теперь новый draft синхронно записывается под server profile id с принятой base/revision и прочитывается для проверки. Затем сохраняется accepted command binding, проверяется pointer и удаляется старый local slot. Новый текст остаётся несохранённым на сервере; старый ACK не даёт ему метку Saved.

Основной durable источник нового текста после ACK — проверенный envelope. При неподтверждённом переносе исходный per-tab journal с immutable UUID/body и mutable latest_draft остаётся recoverable. Серверная acceptance не превращается в unknown из-за ошибки браузерного хранилища. Если первый create ACK нельзя записать в journal, UI сохраняет local identity до повтора исходной команды. Replacement write/research блокируется. Перед завершением сравнения envelope также проверяется. Advanced replay сохраняет пользовательский draft для сравнения с поздней серверной версией.

**N11:** после optional cases GET проверялось только право опубликовать cases; устаревший обработчик всё равно отправлял research POST. Теперь непосредственно перед POST проверяются generation, owner, case epoch/identity и принятый target profile. Для позднего409 запрещён join GET после смены дела. Уже отправленная работа этим guard не отменяется.

## Таблица переходов

| Переход | Durable источник | Разрешённое действие |
|---|---|---|
| Capture → dispatch | Исходный journal UUID/body/base/draft | Только исходная команда |
| Typing во время pending/unknown | journal.latest_draft и envelope | Тело отправленной команды неизменно |
| ACK с новым текстом | Проверенный envelope с accepted base/revision | Принять captured body, сохранить новый draft |
| Create local → server | Envelope → accepted binding → pointer → retirement | Очистка после проверки переноса |
| Ошибка retirement | Original journal и известная acceptance | Восстановление без replacement write |
| Advanced ACK/conflict | Original, current draft, current server | Сравнение меняет draft; новый Save явный |
| Metadata await → research | Актуальные owner/case/epoch/gen/target | Ноль новых POST для старого намерения |
| Reload / A→B→A | Envelope своего case и собственный journal | Новое дело не получает старый текст |

## Проверки

| Проверка | Фактический результат |
|---|---|
| Исходные независимые сценарии на baseline | **10 PASS / 3 FAIL**: два N10, один N11 |
| Те же исходные сценарии на исправлении | **13 PASS**; файл совпадает с independent original побайтово |
| Дополнительный create-storage OFF | **1 PASS / 1 FAIL**; другие24 явно отфильтрованы |
| Текущий полный frontend | **944 PASS / 93 файла**; typecheck/lint/build PASS, девять прежних lint warnings |
| Текущий native Demo | **7 PASS**, реальный сервер/worker/SQLite/browser |
| Текущий native Auth | **7 PASS**, реальная регистрация/вход и сервер/browser |
| Точность native source | **503** primary/lab/before/after consumer paths совпали в каждом прогоне |
| Прежние полные серверные проверки | **Carry**, не новый запуск: все **651** source paths каждого сохранённого SQLite/PostgreSQL прогона совпали с текущими байтами |

В frontend проверены update/create, ordinary/replay ACK, typing до/после autosave, immediate reload, normalization, отказ local/session storage, departed draft, New case/switch/roundtrip/owner change при успешном и ошибочном delayed metadata, unchanged intent с ровно одним POST, advanced create ACK и поздний409 без join. Старые assertions, journal limit16 и G3 cap64 сохранены.

Native сохраняет исходный core journey, два conflict/merge сценария и real committed lost-create-ACK replay. Добавлены delayed update ACK → typing → ACK → reload, такой же create и abandoned research до POST. Ответы реального сервера только задерживались/терялись; acceptance не подменялась. Для N11 наблюдаются ноль POST и пустой серверный run list. Native3 квалифицирует текущий код; Native2 относится к предыдущему executable.

Первые отказы сохранены: independent OFF; on1/on2 ошибки новых фикстур; static3 prefer-const; native1 preflight из-за отсутствующего optional pyproject.toml, до запуска серверов; storage-create OFF. Они не переименованы в PASS. Текущие логи сохраняют прежние mocked read-hook traces и build chunk warning. Зелёный итог не означает чистые логи или измеренную production производительность.

## Артефакты

- [Индекс оригиналов с SHA256](evidence/profile-lifecycle-2026-10-15/INDEX.json)
- [Текущая квалификация](evidence/profile-lifecycle-2026-10-15/FINAL_QUALIFICATION.json)
- [Точный diff четырёх source/test файлов](evidence/profile-lifecycle-2026-10-15/CHANGES.diff)
- [Карта рассмотренных изменений](evidence/profile-lifecycle-2026-10-15/FILE_REVIEW.csv)
- [Очистка собственных процессов и synthetic DB](evidence/profile-lifecycle-2026-10-15/CLEANUP_VERIFICATION.json)

Полные runtime logs/HTML/синтетические скриншоты остаются во внешней лаборатории `product-platform/2026-10-15-profile-lifecycle`. Trace/cookies/DB в Git не публикуются. Это разбор изменённых переходов четырёх файлов, не полный семантический аудит прежних1177.

## Открытые этапы

**D:** N04 — общий контракт всех ProgramResult writers; N03 — порядок acknowledged states; N07 — сохранность notes/rejection при conflict/unknown/failure. Затем E: N05 freshness, N06 deadline semantics, N08 export outcomes; F/G, отдельно поиск и выпуск.

Начало D: существующая `checkpoint-c-final/D_WRITER_MATRIX_DRAFT.md`. Нужны полная writer/transaction/lock-order/field/retry matrix и реальные SQL-entry race controls на SQLite/PostgreSQL перед выбором стратегии. Очередь одной вкладки не заменяет защиту БД.

PR88 остаётся Draft, hosted rollup[] = NOT_RUN. Production/release/security acceptance отсутствует. Все STOP/UNSCORED, HELDOUT150 и ограничения live evaluation/model/provider/effort сохранены. Агенты не запускались. IELTS/SAT остаются дополнительными инструментами.
