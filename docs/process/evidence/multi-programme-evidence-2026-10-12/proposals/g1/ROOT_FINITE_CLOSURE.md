# G1: закрытие дефекта nonfinite после применения root

**12.10.2026 · Узкий review: исходники и сохранённые receipts.**

**Вывод:** минимальное исправление в двух application-файлах принято по исходникам. В сохранённом focused-final4 после исправления подтверждены **214 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, включая все 33 новые finite-проверки. Полный backend gate этой версии ещё не квалифицирован этим review: root сообщил активный `exec82841` (static7 → focus4 → full2). Это не вывод о готовности всего продукта, публикации или качестве живого поиска.

Автор review читал обычные исходники и конечные receipts и использовал только stdlib для AST/hash/XML. Импорты приложения/runner, запуск тестов/runtime, Git, active source и helpers не выполнялись и не менялись. Запечатанное предложение и первая receipt сохранены без изменений.

## 1. Привязка к фактическим байтам

Root сообщил замороженный HEAD `e5d12f58`. Git независимо не читался. Исторические поля `baton` / `HEAD` в final8 metadata остаются `d090a97a…`; это не подтверждение текущего commit. Привязка этого review основана на проверенных текущих **SHA-256**:

| Файл | Текущий SHA-256 |
|---|---|
| [routes_preparation_graph.py](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_preparation_graph.py:36) | `7ddff09f9ef9601571568d51c3701e901166193de1801280b2901d067a0ef7c9` |
| [preparation_graph_loader.py](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/preparation_graph_loader.py:20) | `dd5c5c635a9b80832aeb334081667d2d5c69a65304fb348441aa44469781dd6b` |
| [test_preparation_graph_api.py](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_preparation_graph_api.py:806) | `61d52735b742a9a527e78331965a19a2a7f55d7ab76db947c2e380e77afd7987` |

Все три файла побайтно совпадают с `g1-execution/source`, с соответствующими entries [APPLIED_SOURCE_PINS.final8.json](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/APPLIED_SOURCE_PINS.final8.json) и [INITIAL_SOURCE_COPY.final8.json](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/INITIAL_SOURCE_COPY.final8.json). Обе metadata receipt проверены как metadata, без чтения всех 759 declared file bodies.

Metadata SHA-256:

- `APPLIED_SOURCE_PINS.final8.json`: `a8f5499860690fdc5f59ede9787401ea48a97701fcb290c5af341d371a1c6e9a`.
- `INITIAL_SOURCE_COPY.final8.json`: `0333294ea67bc760b2bfad1b60511532308fff4bdaa0e3e50eb976d55f5bd347`.

## 2. Предложение применено с двумя ограниченными отличиями

[SEAL.json](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1-finite-v2/SEAL.json) имеет прежний hash `b8490ac155b938c40a9a77213a65c34ff8f703c4ecc5194a4286404dd84df8ae`. Все **12** перечисленных в seal файлов независимо проверены; несовпадений нет.

- Router полностью совпадает с запечатанным proposed-файлом, SHA и AST совпадают.
- Loader отличается от proposal единственной строкой: `isinstance(value, (list, tuple))` → `isinstance(value, list | tuple)`. Это root correction для UP038. Production Dockerfile выбирает Python 3.12 ([builder](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/Dockerfile:6), [runtime](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/Dockerfile:21)); объединение типов поддерживается. Других изменений нет.
- Test-файл отличается единственным переносом `@pytest.mark.parametrize`; AST полностью совпадает с sealed proposal. Все **52 исходных top-level AST nodes** сохранены как точный prefix; старые тесты и assertions не ослаблены.

После удаления только объявленных новых finite-guards/import/helper из AST текущих router и loader восстановленные AST **точно равны обоим original preimages**. Это проверка узости application-дельты, не исполнение AST.

## 3. Закрытые пути и сохранённые старые правила

| Путь | Добавленная граница | Сохранившееся поведение |
|---|---|---|
| [ClaimRow → ClaimOut](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_preparation_graph.py:149) | Raw `row.payload` finite JSON до Pydantic; typed `mode="python"` float guard до `mode="json"` | Authority колонок id/type/status/url/specificity/accessed_at, вычисление freshness, failure flag и duplicate-ID отказ |
| [ConflictRow → Conflict](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_preparation_graph.py:184) | Те же raw/typed границы | Authority claim_type, `unresolved=True`, failed-read handling |
| [Авторитетная колонка checklist](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_preparation_graph.py:121) | Raw JSON до DocumentChecklist; typed guard до сериализации | Проверки disagreement/identity, прежний column-versus-payload выбор без записи назад |
| [Payload-only checklist и остальные stored fields](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/preparation_graph_loader.py:42) | Существующий raw before-validator оставлен; добавлен typed guard в after-validator | `extra="forbid"`, запрет duplicate award IDs, старый finite JSON/serialization guard и исключения |

[Shared helper](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/preparation_graph_loader.py:20) рекурсивно проверяет float в dict keys/values и list/tuple; NaN и ±Infinity отклоняются. Native date/datetime/enum и None helper не преобразует. Другие неподдерживаемые значения по-прежнему регулируются существующими JSON/Pydantic guards. Литерал `"NaN"` в поле Any не объявлен числовым NaN; coercion в typed `DocumentItem.max_file_size_mb` проверяется после Pydantic.

Прежние conservative branches в [_source_slice](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_preparation_graph.py:217) и остальной router сохранены. Invalid evidence не превращается в текущую подтверждённую requirement. Не менялись схемы Claim/DocumentItem, БД, миграции, права, v1 preparation handlers, schedule/attempt seams или providers.

Ограничение вывода: дефект file-size доказывает пропуск invalid input и изменение snapshot/digest после coercion. Он не доказывает, что документ становился VERIFIED: G1 DocumentAction до этого уже оставлял непроецируемый document predicate неизвестным.

## 4. Реальное воспроизведение до исправления

Независимо прочитаны [focused-final3 result](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/evidence/focused-final3/20261011T234527391948Z/result.json) и [JUnit](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/evidence/focused-final3/20261011T234527391948Z/sqlite/junit.xml). Сохранённые source-before/source-after побайтно равны (SHA `1e9b0d0eaa7f783f0760c0349d2eba19fa751001f1f03bfeb76dd2c4f1f2540e`). Их source maps привязаны к **original** router `188fb95e…` и loader `656f79f4…`, а test-файл — к sealed proposed `a361a372…`. Это старое приложение плюс новые tests-first controls.

JUnit содержит **214 уникальных cases**: **193 PASS / 21 FAIL / 0 ERROR / 0 SKIP**. Матрица не подгонялась:

| Новые controls | Cases | На старом приложении |
|---|---:|---|
| Raw Claim nested NaN / ±Inf | 3 | 3 FAIL (`failed` оставался False) |
| Raw Conflict nested NaN / ±Inf | 3 | 3 FAIL (`failed` оставался False) |
| Raw authoritative checklist: admission / scholarship / school × NaN / ±Inf | 9 | 9 FAIL (`DID NOT RAISE ValueError`) |
| Coerced file-size strings NaN / Infinity / -Infinity × column / payload | 6 | 6 FAIL (`DID NOT RAISE ValueError`) |
| Finite/None/Any-string/date/enum/scope/authority controls | 12 | 12 PASS |
| Существующие cases | 181 | 181 PASS |

Переданные root числа теперь проверены по сохранённому XML, а не только по сообщению. Hash JUnit: `695a77bcf5b4e8cafe31b7c629e66c533483872222bb10223a7c37279da76d7e`; pytest.log: `96d29323e2245278351cb3e726ef6d8106c69918e430ef446f17336d237d3b3c`; root result: `957bfcbd9f8cc7b3dec03d5849b4b367e29ec251fbee2572740e703c64af7fc1`.

Raw result фиксирует `outside_attempts=[]`, `guard_startup_failures=[]`, source unchanged, shutdown confirmed и runtime removed. Это конечный focused SQLite diagnostic; PostgreSQL в этом запуске не стартовал, coverage не измерялся.

## 5. Сохранённый diagnostic после исправления

В [focused-final4 result](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/evidence/focused-final4/20261011T234914925340Z/result.json) / [JUnit](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/evidence/focused-final4/20261011T234914925340Z/sqlite/junit.xml) независимо подтверждены:

- **214 уникальных cases**, все PASS; все **33 finite-v2 cases** PASS, 0 failures/errors/skips.
- Source-before/source-after одинаковы: `ecf3e4d62c82e3c97299ba24ee09e4daef47b0401f9fb31f6cbcabbd3aef02d6`; три finite-related файла в map имеют точно hashes раздела 1.
- `outside_attempts=[]`, `guard_startup_failures=[]`, source unchanged, shutdown confirmed, runtime removed, active cluster markers пусты.
- Receipt status: `FOCUSED_DIAGNOSTIC_PASS_NOT_FULL`. Это **SQLite focused acceptance**, не полный backend/coverage или PostgreSQL acceptance.

Result SHA: `f483e903ed674ff260e9bcaea2e7cd7f11e9999a3ee0bbc33919987080d09ca9`; JUnit SHA: `f7676b110fdfc5612e762f7357f7f93eb7dd4d1b18927f1e4a3742f0476f8268`, совпадает с hash в result.

Tests-first → actual failure → narrow application repair → fixed focused diagnostic подтверждены сохранёнными исходниками/receipts. Review не запускал эти проверки.

## 6. Границы текущего acceptance

**Принято:** узкая application-дельта и сохранение старых guards; историческое воспроизведение 21 дефекта; исправленные 33 controls на текущих pinned bytes в focused SQLite.

**Ещё требуется отдельная конечная квалификация:** текущий полный SQLite + PostgreSQL gate с coverage, итог всех статических gates, source equality и cleanup полного запуска, demo seed/migration/native demo/auth приемка в разрешённой границе. Active gate не считается PASS. Старые full/static receipts относятся к своим source snapshots.

У автора нет новых фактических blocker findings в этой узкой finite-дельте. Недоступный до terminal full result не заменяется гипотезой об успешном прогоне. Общее завершение G1, готовность Unimatch, интеграция/main/deploy, живое качество поиска, paid flow и остановленные collector/controller/provider workflows этим review не квалифицированы и не возобновлялись.

## 7. Аннотация к предыдущему G1 source acceptance

[ACTUAL_HELPER_ACCEPTANCE.md](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/ACTUAL_HELPER_ACCEPTANCE.md) относится к исторической final4 привязке. Настоящий review добавляет final8 только для трёх inspected ordinary sources и independently-read focused receipts. Он не переписывает sealed receipt и не объявляет, что все 759 source bodies или helpers заново проверены. Current expected/source guard contracts должны получить итоговую root qualification по конечному полному запуску.

[Сохранённый пакет предложения](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1-finite-v2/README.md) и [tests-first receipt](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1-finite-v2/TESTS_FIRST_RECEIPT.json) остаются первоначальными proposal artifacts; их historical `NOT_EXECUTED` отражает действие автора на момент seal. Root integration и runtime proof подтверждаются отдельными receipts выше.
