# G1 — фактическая привязка helper и исходников

Дата: 12.10.2026. Метод: чтение обычных исходников, JSON-метаданных, AST и SHA-256 через стандартную библиотеку Python; без импорта приложения/helper и без выполнения тестов.

## Заключение

**Привязка фактической копии G1 к approved helper подтверждена по исходникам и текущим метаданным `final4`. Приёмка исполнения остаётся отдельной.** Конкретных препятствий в проверенной привязке нет. Этот документ не утверждает, что backend, native journey или весь продукт уже прошли свежую приёмку.

Родитель сообщил о последовательных исправлениях после первых завершившихся отказом проверок и новом запуске. Рецензент не читал их runtime-логи и не запускал второй контур. Метки `PREPARED_NOT_EXECUTED`/`NOT_RUN` внутри подготовительных JSON сохраняют происхождение пакета; они не описывают актуальный процесс родителя.

На момент завершения отчёта родитель сообщил `static-final5 PASS`, `focused-final2 PASS` и активный полный SQLite прогон. Эти runtime статусы здесь записаны как сообщение родителя, без самостоятельного чтения или квалификации receipts.

Окончательный предмет этой сверки — actual bytes в `g1-execution/source`, [17 current applied pins](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/APPLIED_SOURCE_PINS.final4.json) и [759-file copy receipt](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/INITIAL_SOURCE_COPY.final4.json). Ранее сверенный `final3` теперь исторический. `HEAD`/`baton` внутри подготовительных JSON не использованы как доказательство текущего Git HEAD. Git рецензент не вызывал. После сверки родитель подтвердил текущую frozen версию `04830101` (pushed); этот commit ID сообщён родителем, независимо через Git не проверялся.

## 1. Контрольные суммы актуальных метаданных

| Файл | SHA-256 |
|---|---|
| [HELPER_REBINDING.json](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/HELPER_REBINDING.json) | `8ff4d94abb0fdddfb7500b007d6c64485958d52a4b74877e222d717f94155dc2` |
| [APPLIED_SOURCE_PINS.final4.json](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/APPLIED_SOURCE_PINS.final4.json) | `9d0f19874d26d08c02bd6737c3874359b8bd5c74e3ac7ab4b2fcf09064d13c60` |
| [INITIAL_SOURCE_COPY.final4.json](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/INITIAL_SOURCE_COPY.final4.json) | `5146b080c08c2249bfe44fe94ba9036dec0e9ae39d208a640141279f521e5e75` |
| [ASSERTION_REPAIR_BINDING.json](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/ASSERTION_REPAIR_BINDING.json) | `a19708812da29c478619f041f0373f7918f3d7f6c59c01cd3027eea4e958aac9` |
| [FINITE_INPUT_REPAIR_BINDING.json](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/FINITE_INPUT_REPAIR_BINDING.json) | `611e5e67d97107ea183a5d1dfd47d6b3fea0b92abbc89949f1f98239c9cb1dc6` |
| [current expected-native-source-pins.json](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/backend-full/expected-native-source-pins.json) | `d2403e05e03c07e0a42407e85c318be32c019d667956634b24b5b6d333620e51` |

Сверка установила:

- Старый approved expected map содержит **573** пути, текущий — **579**. Разница ровно **8 разрешённых привязок**: 6 новых файлов и 2 изменённых существующих. Удалений нет.
- Copy receipt содержит **759 путей, все уникальны**. Все указанные файлы существуют; среди этих объявленных файлов нет символьных ссылок.
- Все **579 записей** текущего expected map совпадают с SHA-256 в `final4` copy receipt.
- У **17 обычных путей** из applied receipt независимо вычислены реальные SHA-256: все совпадают одновременно в external copy, рабочем checkout и copy receipt. Это включает текущий loader и API tests после finite-input repair.
- Для остальных объявленных файлов проверены существование и согласованность метаданных. **Рецензент не прочитал и не перехешировал все 759 тела**; исторические fixture/corpus/raw bodies не открывались. Проверка фактических разрешённых assets при запуске остаётся обязанностью неизменённого preflight.

### 8 изменённых привязок expected map

| Путь | Actual SHA-256 `final4` |
|---|---|
| `backend/app/main.py` | `b83563f60e08ccb9ed2522463bca6e1bc94bb31dc2c82f13398cdf59f2f8ad9c` |
| `frontend/src/types.ts` | `1db0143b20def355da62687d290f34628b7a0d4f1beeab8415689caf20f60ca1` |
| `backend/app/api/routes_preparation_graph.py` | `188fb95ef36a33456145d452af17d1e9d645540731353e791a3bb2f6fbfec239` |
| `backend/app/domain/preparation_graph.py` | `2ba1488a582a4a8e4a37d747a5a4e4d1d44ceb70c980ad50195438dae3b35c09` |
| `backend/app/schemas/preparation_graph.py` | `4d7c55dd33295f1e6e9e6750a2da50c1a120e83635836d279857241d1a3fd249` |
| `backend/app/schemas/preparation_graph_loader.py` | `656f79f47ddc8520317f8de32f2881661ed9592dfba0e4450f2b9e5681d9c1e7` |
| `backend/tests/test_preparation_graph.py` | `76d67d9fc2dc7b8d688bb613da7faf4c50570b17456f9ad3050b3c0becd50627` |
| `backend/tests/test_preparation_graph_api.py` | `214e4397eb66d261bce9e9f3a9bf24d19f0d75b02ddf78d64af9f03d42d2a23c` |

Оставшиеся 9 applied paths — обычные API/FE компоненты, сообщения, tests и два e2e файла; их точные суммы доступны в linked applied receipt и также сверены с actual bytes.

## 2. Фактические 16 helper bindings

Для каждой строки independently сопоставлены actual old/new SHA-256 с `HELPER_REBINDING.json`. **16 из 16 привязок согласованы.** Правильные predecessors для переименованных файлов указаны явно.

| Helper | Проверенное различие |
|---|---|
| `backend-full/run_full_backend.py` | Только literal `DIAGNOSTIC_TARGETS`: 4 старых learning/study selectors заменены на 2 G1 selectors. AST вне этого assignment полностью совпадает. |
| `backend-full/sitecustomize.py` | Байты идентичны approved predecessor. |
| `backend-full/guard_runtime.py` | Байты идентичны. |
| `backend-full/guard_optional.py` | Байты идентичны. |
| `backend-full/pytest_full.py` | Байты идентичны. |
| `backend-full/os_network_probe.py` | Байты идентичны. |
| `backend-full/mock_endpoint_plugin.py` | Байты идентичны. |
| `backend-full/asset-requirements.json` | Байты manifest идентичны; тела fixture assets здесь не читались. |
| `backend-full/transitive-requirements.json` | Байты manifest идентичны. |
| `backend-full/existing-public-fixture-paths.json` | Байты manifest идентичны. |
| `e2e/loopback-only.sb` | Байты sandbox policy идентичны. |
| `e2e/run-native.py` | Только literal внешнего source namespace. |
| `e2e/runtime-child.py` | Только два literal cwd для backend/frontend во внешнем namespace. |
| `run_static_frontend_initial.py` | Predecessor — `execution/run_static_frontend_final8.py`; только source/output namespace. |
| `run_demo_seed.py` | Predecessor — `execution/run_demo_seed_final.py`; только source namespace. |
| `run_native_pair.py` | Байты идентичны. |

[Approved full runner](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/backend-full/run_full_backend.py):
`3b986a32597d41b1f6bf0db18a0c5ff9f40366cf34d091dee73ac597d391dea7`.

[Actual G1 full runner](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/backend-full/run_full_backend.py):
`3ed463bd966cec9aba7c04274f217768b1fb5b6ce5ebf2995a12b606aa9fb311`.

Дополнительно прочитаны производные `run_static_frontend_final4.py` и [run_static_frontend_final5.py](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/run_static_frontend_final5.py): каждая отличается от G1 initial только именем output directory. SHA-256 `final4.py` — `263011a1ab9a4e313b468e2519369480ecb8049df5f035307532ae3756d8d9ef`. Они не исполнялись рецензентом.

### Сохранённые ограничения

Source review полного runner подтверждает неизменность shared non-truncating lock, явного external source, исключения primary, проверки source/assets before/after, private owned PostgreSQL, сетевого sandbox, startup guards и очистки только принадлежащего запуску runtime. Full mode остаётся всеми backend `tests`, исходными fixtures/plugins, coverage gate **92%**, нулём failed/error/skipped, проверкой реальных private PG connections и остановкой при первом отказе. Focused mode остаётся diagnostic, без переименования в full acceptance. [Preflight](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/backend-full/run_full_backend.py:74), [Phase and pytest selection](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/backend-full/run_full_backend.py:223), [PASS predicate](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/backend-full/run_full_backend.py:298), [Owned cleanup](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/backend-full/run_full_backend.py:173).

Отдельно сохранены strict network/data guards, точечный mock unit endpoint и отрицательный OS probe. Их неизменные байты не доказывают успешный OS probe в текущем запуске: для этого нужны actual receipts. Native font binding унаследован через namespace-only копию, sandbox policy не ослаблена.

## 3. Копия и зависимости

Metadata inventory не содержит `.git`, содержимого `.venv`/`node_modules`, настоящих `.env`, runtime `.db`/`.sqlite`/`.sqlite3` и пользовательских `backend/data` файлов; допускается только `.gitkeep`. Actual `.env` и `backend/.env` в copy отсутствуют. Это ограниченная проверка объявленного inventory и явно названных путей, без чтения приватных данных.

Зависимости использованы прежними symlinks. Independently проверено равенство **canonical targets** old/new:

- `backend/.venv` → `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/ashyq-apply/backend/.venv`.
- `frontend/node_modules` → `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/integration-2026-10-11/source/frontend/node_modules`.

Текст относительной backend-ссылки может различаться; конечный target одинаков. Содержимое зависимостей не читалось, не копировалось и не устанавливалось рецензентом.

## 4. G1 controls и исправления assertions

Новые source-level API controls действительно проверяют независимые отрицательные случаи; наличие этих assertions ещё не означает их успешное выполнение:

1. **Локальный malformed conflict не заимствуется второй программой того же run.** Первый slice остаётся conflicted, второй current, его atom сохраняется. [API test](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/tests/test_preparation_graph_api.py:469).
2. **Authoritative columns сильнее copied payload.** Unresolved IELTS conflict в DB не становится resolved SAT из payload; atom получает conflicted evidence и unknown policy. [API test](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/tests/test_preparation_graph_api.py:492).
3. **Conflict partition требует exact run/result pair либо global conflict того же run.** Cross-paired row и unselected result не загрязняют selected slices; run-global действует только на свой run. [Three parametrized controls](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/tests/test_preparation_graph_api.py:520). Actual query и per-slice partition согласованы с этим контрактом: [Query and partition](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/api/routes_preparation_graph.py:347).
4. **Resolved DB column исключает payload, утверждающий unresolved.** Evidence программы и IELTS atom остаётся current. [Resolved-column control](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/tests/test_preparation_graph_api.py:554).

Найденное ранее assertion `projection_state == projected` исправлено на **partial** и проверку `exam_identity_unestablished` для каждого atom второй программы. Это соответствует сознательной неполноте идентичности экзамена: current evidence не создаёт установленный accepted route/variant/edition. Изменение исправляет ожидаемый результат теста без ослабления product policy. [Corrected assertion](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/tests/test_preparation_graph_api.py:546), [Identity reason](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/domain/preparation_graph.py:263), [Programme partial derivation](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/domain/preparation_graph.py:689).

FE assertion также теперь явно требует unknown atom policy и один unresolved alternatives group; отдельно раскрывает conflicting document evidence. Это соответствует подготовленной synthetic structure и не утверждает установленную альтернативу. [Corrected FE controls](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/frontend/src/screens/PreparationGraphPanel.test.tsx:187).

### Последнее finite-input исправление

`final4` loader проверяет **raw stored input** через `json.dumps(..., allow_nan=False)` до Pydantic serialization. После parsing отдельно проверяются unique award identities и finite JSON snapshot. Это закрывает случай, когда nonfinite observation превращается в `null` при serialization и получает новый digest. Рецензент прочитал обычный loader; runtime результата не проверял. [Raw finite-input validator](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/schemas/preparation_graph_loader.py:27), [Exact snapshot validator](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/source/backend/app/schemas/preparation_graph_loader.py:38), [Repair binding](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g1-execution/FINITE_INPUT_REPAIR_BINDING.json).

## 5. Граница приёмки

Сейчас по этой независимой проверке можно утверждать: **actual source binding согласована; guards/assets manifests и full execution contract сохранены; G1 controls и latest repair отражены в frozen byte pins.**

Для отдельного завершения G1 ещё требуются fresh terminal receipts родителя на этих exact source pins:

- Static frontend и focused diagnostic; первый отказ сохраняется отдельно, повторный PASS не заменяет его историю.
- Полные SQLite и PostgreSQL suites с нулём failures/errors/skips, сопоставимыми unique test IDs, coverage и всеми guard/owned-runtime условиями.
- Demo seed/migration и native journeys, включая authenticated path, если он входит в текущую разрешённую приёмку.
- Source before/after и helper pins в каждом actual receipt должны соответствовать выбранной версии; переход от final3 к final4 нельзя выдавать за исполнение прежнего snapshot.

Исторический backend full2 календарного этапа не является fresh PASS для G1. Подготовленные metadata не являются результатами исполнения. Общая live search quality, продакшн, paid acceptance и публичный launch этим документом не проверены; остановленные workflows остаются остановленными. G1 сохраняет family-only grouping и unresolved alternatives/waivers/identity; общий score target или исполненную подготовку он не устанавливает.

Этот внешний отчёт дополняет, не заменяет сохранённые [G1_PURE_SOURCE_REVIEW.md](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/G1_PURE_SOURCE_REVIEW.md), [ROOT_FIX_CLOSURE.md](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/ROOT_FIX_CLOSURE.md) и [BACKEND_HELPER_REBINDING_REVIEW.md](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/BACKEND_HELPER_REBINDING_REVIEW.md). Sealed proposal/receipt и прежние findings не переписаны. Репозиторий, helpers, Git и HANDOFF рецензентом не изменялись.

## Дополнительная semantic review после сверки binding

Read-only проверка обнаружила условную finite-input coverage gap в authoritative claims/conflicts/column checklist, см. [FINITE_AUTHORITATIVE_INPUT_REVIEW.md](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/FINITE_AUTHORITATIVE_INPUT_REVIEW.md). Это не нарушает проверенную helper/source binding, но semantic acceptance требует отдельного решения и fresh controls. Превращение чисел установленным serializer не воспроизводилось рецензентом.
