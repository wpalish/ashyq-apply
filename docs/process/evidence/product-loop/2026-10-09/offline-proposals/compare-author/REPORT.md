# Compare: матрица свидетельств подготовки — предложение

**Статус: подготовлено отдельно, не применено.** Достаточный минимальный increment — одна правка `ComparePanel.tsx` и новый `ComparePanel.preparation.test.tsx`. Предложение использует существующие данные и существующий `ResultDetail`, не меняет API, types, ShortlistScreen или backend. Начальный ориентир от root — `d6a727aa`; позднее root сообщил `45bcc99a` после B4 и подтвердил, что ComparePanel не менялся. Git здесь не читался и не изменялся. Снятые хэши восьми используемых исходных файлов до/после совпали: [source-integrity.json](./source-integrity.json).

## Минимальная матрица

| Что пользователь сравнивает | Сохранённое поле | Предложенный вывод | Граница смысла |
|---|---|---|---|
| Intake выбранной программы | `ProgramResult.intake` | `Requested intake`; пустое → `Not recorded` | Intake запроса/результата не доказывает scope каждого документного источника |
| Список ещё не собран | `checklist === null` | `Not collected` | Наличие обязательных документов неизвестно |
| Список прочитан частично | `completeness=partial` | `Partially read from sources` | В том числе сохранённые документы из недоступных при обновлении страниц; не новое подтверждение |
| Источники прочитаны | `completeness=official` | `Read from official pages` | Не «полный список», не «пользователь прочитал», не готовность к подаче |
| Сбор не дал доступного списка | `completeness=unavailable` | `Collection attempted — unavailable` | Не доказательство отсутствия требований |
| Обязательные элементы в сохранённых списках | `admission_documents`, `scholarship_documents`, строгий `required===true` | Раздельные количества admission / scholarship; раскрываемые названия | Не суммарный уникальный пакет: один элемент может иметь разные цели; пустое → `No required items recorded` |
| Кто должен действовать | `DocumentItem.owner` | You / Your school / Your referee / A third party | Отображаем сохранённую роль; отсутствующая/неизвестная → `Owner not recorded`; не назначаем новую |
| Откуда требование | `DocumentItem.source_url` | Существующий `SourceLink` рядом с документом | Отсутствующая → `Source not recorded`; programme URL не подставляется за документный источник |
| Неизвестное в чеклисте | `checklist.unresolved` | Видимое число вопросов и раскрываемые question / why_it_matters | Не складываем с result.unresolved, чтобы не создавать ложный итог с дубликатами |
| Неверная привязка списка | `checklist.result_id !== result.id` | `Checklist link needs clarification`; чужие документы скрыты | Даже вкладка Documents в открытых деталях не получает чужой список |
| Следующее действие | Существующий `ResultDetail(result)` и сохранённые ссылки | `View details` открывает именно выбранный result; вкладки Requirements / Documents / Sources & evidence | Не запускает collection, research, send, payment или сохранение статуса |

Owner action arrays не считаются дополнительными документами: backend явно формирует их как проекции двух исходных списков. Counts поэтому относятся к двум именованным спискам, без повторного суммирования applicant/school/recommender/certification arrays.

## Почему контракт поддерживает эту правку

Точные фрагменты и SHA-256 сохранены в [contract-evidence.json](./contract-evidence.json). Ключевые опоры:

- `frontend/src/types.ts:311–349`: required/name/owner/source_url, две документные группы, result_id, unresolved и три completeness значения.
- `backend/app/adapters/documents/web_documents.py:280–294`: `official` выбирается при наличии документов и отсутствии failed pages; это состояние чтения, не оценка готовности заявителя.
- Тот же adapter, строки 764–797: owner arrays повторяют исходные списки; предыдущие документы из failed URL сохраняются с `partial`, без обновления claim/verification date.
- `frontend/src/screens/DocumentsScreen.tsx:24–54`: галочки находятся в localStorage `ashyq.docsDone`; это удобство конкретного браузера, а не API-состояние документов. Compare их не читает и не сохраняет.
- `backend/app/schemas/result.py:281–296`: optional `DocumentItem.scope` существует на backend и опускается, если не записан. Текущий frontend `DocumentItem` это поле не описывает. Proposal не заявляет, что scope отсутствует вообще, и не подменяет его result.intake.
- `frontend/src/components/ResultDetail.tsx:20–81,471–548`: существующие детали и вкладка Sources уже привязаны к переданному result и показывают сохранённые claims/источники.
- `frontend/src/components/primitives.tsx:108–143`: SourceLink допускает только HTTP(S); fixture и небезопасные ссылки остаются текстом.

## Проверка

| Проверка | Итог | Артефакт |
|---|---|---|
| Финальная одинаковая suite на оригинальном ComparePanel | **RED: 9/9 failed**, ожидаемо отсутствуют intake/list/source/next action | [red-final.log](./logs/red-final.log) |
| Та же suite на proposal | **GREEN: 9/9 passed** | [green-final.log](./logs/green-final.log) |
| Изолированный strict TypeScript для минимального import closure и теста | **PASS**, exit 0 | [typecheck.log](./logs/typecheck.log) |
| ESLint только двух предложенных файлов, max-warnings 0 | **PASS**, exit 0 | [lint.log](./logs/lint.log) |
| Node deny-network guard, реальные проверки | **0 перехваченных network/listen попыток** | [network-summary.json](./network-summary.json) |
| Guard self-test | **PASS**, HTTP / fetch / listen заблокированы до доступа; 3 преднамеренные попытки | `logs/guard-network` |
| Использованные исходники до/после | **8/8 SHA-256 совпали** | [source-integrity.json](./source-integrity.json) |
| Full suite / browser layout / live / production / accounts | **NOT RUN** | Этот этап ограничен offline proposal |

Тесты проверяют различие null/partial/official/unavailable, отдельные intake, строгий required filter, отсутствие двойного счёта owner arrays, роли/неизвестную роль, правильный document URL/отсутствующий URL/небезопасный URL, сохранённые вопросы, подавление чужого списка, открытие/переключение/закрытие правильных деталей и отсутствие localStorage write. Две ранние typecheck ошибки в тестовой CostBreakdown фикстуре исправлены (`items` — объект, поле `total`). Первичные логи сохранены как `typecheck.initial.log` и `typecheck.fixture-total.log`; финальный PASS не скрывает эти промежуточные ошибки.

Runtime содержит только необходимый import closure. `node_modules` — read-only использование уже существующих dependencies через symlink; установки не выполнялись. Cache направлен в собственный runtime; `--configLoader runner` исключает bundle temp в исходном node_modules. Guard блокирует Node net/tls/http/https/fetch/dgram и server.listen; это не утверждение об отдельном OS-level firewall. Команды и cwd сохранены в [checks.json](./logs/checks.json).

## Границы следующего review

1. Это proposal, не разрешение применять. Корневой агент должен независимо проверить конечные два файла и pinned пакет.
2. Нужна UI-проверка ширины трёх колонок, длинных имён/URL, мобильного scroll и расположения раскрытых деталей. Новых CSS правил нет; используются существующие Compare стили.
3. `View details` открывает существующую панель внутри Compare. Если одновременно открыты детали той же программы в основной карточке, возможен повтор блока; новый глобальный navigation contract намеренно не введён. Drawer/scroll/focus не проверены браузером.
4. Полной документной готовности, прочтения пользователем, uploads, submission receipts, сроков start-by, автоматического назначения ответственного и актуальности каждого документа этот контракт не доказывает. Proposal не вводит такие показатели и не вычисляет новые дедлайны.
5. Вкладка Documents у существующего ResultDetail пока показывает ordered_steps, а не полный editor документов. В Compare источник и роль доступны в раскрываемом списке; сбор/редактирование остаются существующим отдельным journey.

## Конечные файлы

- [ComparePanel.tsx](./proposed/frontend/src/components/ComparePanel.tsx)
- [ComparePanel.preparation.test.tsx](./proposed/frontend/src/components/ComparePanel.preparation.test.tsx)
- [proposal.patch](./proposal.patch) — unified diff только этих двух файлов.
- `packet-pins.json` — конечные SHA-256 и reviewable packet manifest.

После seal эти предложенные файлы, patch и report не редактируются без нового явно обозначенного packet revision. Primary/source/Git/HANDOFF/STOP и B4 proposal здесь не изменены.
