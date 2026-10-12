# G1: review переноса approved backend-full helper

**12.10.2026 · STRATEGY SOURCE REVIEW ONLY · NOT_EXECUTED.**

Область — перенос уже approved [run_full_backend.py](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/backend-full/run_full_backend.py) в новую внешнюю namespace `g1-execution`. Reviewer не импортировал helper/app, не запускал preflight/tests/probes, не менял helper, checkout, Git или manifests. Читал только helper source, saved hash receipts и application metadata; исторические fixture bodies/labels/private runtime не открывались.

На момент чтения в `g1-execution` были только SOURCE_APPLICATION и FRONTEND_NATIVE_APPLICATION metadata. Поэтому ниже оценивается стратегия; готовая новая copy и её реальный preflight этим документом не подтверждаются.

## Проверенная исходная привязка

Текущие approved helper bytes сверены с [saved backend-full-final2/helper-pins.json](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/evidence/backend-full-final2/20261011T215427507540Z/helper-pins.json): все перечисленные ниже совпали. Старые `artifact-manifest.json`/`SOURCE_BINDING.json` и README сохраняются как исторические записи, не как свежая G1 seal. Например, README описывает 21 diagnostic selectors, actual runner содержит четыре calendar selectors; SOURCE_BINDING описывает 566 pins, actual approved map содержит 573. Это не основание переписывать историю или ослаблять runner.

| Preserved file | SHA-256 |
|---|---|
| `run_full_backend.py` | `3b986a32597d41b1f6bf0db18a0c5ff9f40366cf34d091dee73ac597d391dea7` |
| `pytest_full.py` | `ae987bac75d8d22c63be7448d67cefd04480cb1ff67894d18f3288090300ffe1` |
| `guard_runtime.py` | `6835a7e41d7abe67ed02afef30c1feb142d36bf87648c1638fd98920aa3728a3` |
| `guard_optional.py` | `e309aa99aaf671f70a0e8292600b82d46eb77215af3316703553a98daba03627` |
| `sitecustomize.py` | `747bb4ba27a5f002f45d28e590776e8e052039a8acf949da0ddba61dc12d8bc7` |
| `os_network_probe.py` | `7ff451578d221dce4d781d0180bfb6bbc45b576d4a7cc61719b12586286105e5` |
| `mock_endpoint_plugin.py` | `fee728e2ff824b07b0e927b47c8087f08acc2111277d41053caffc3e37b48588` |
| `asset-requirements.json` | `852b12e28dd3f62bcaead8589609ec7127c5b78040b6f00f8f9b80a4ba20087c` |
| `transitive-requirements.json` | `64c90bb19bfbf9972079075dee038ddd708fb548ec0e72800ed6288a748ca4c4` |
| `existing-public-fixture-paths.json` | `913254fd326c5f89c159b33941753d9aac8e70b270ad8ea03ca02825e5e5f849` |
| Predecessor `expected-native-source-pins.json` | `86698d7828d71bd5fddd2abc84685370c901f6fba3a3b2b4700bf9e72c7a0536` |

## Допустимый минимальный перенос

1. Сделать bounded copy известных static helper/guard/manifest файлов в новую helper directory; не переносить runtime, receipts как новые результаты, `__pycache__`, caches, secrets или installed state. [PACKET](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/backend-full/run_full_backend.py:20) уже вычисляется из `__file__`, поэтому namespace меняется самим расположением copy, без изменения body functions.
2. Сохранить единственный общий `local-runner/.run.lock`, неблокирующий non-truncating flock и PRIMARY exclusion. Не вводить параллельный stage lock и не снимать/пересоздавать чужой lock. Source — frozen внешняя `/source`, evidence — вне source/primary; clean namespace сама по себе не разрешает execute.
3. В новой copy изменить только fixed literal `DIAGNOSTIC_TARGETS` и explicit expected source map; отдельный новый receipt описывает exact predecessor hashes, allowed delta, new helper/source hashes и факт NOT_EXECUTED до реального запуска. Старые records не перезаписывать.
4. Сохранить asset/transitive/path manifests байт-в-байт, включая классификации и frozen blob metadata. Они содержат 45 + 7 exact prerequisite entries; 32 + 7 имеют frozen blob metadata. Нельзя добавлять unlisted fixture/held-out bodies, превращать path-only metadata в новый corpus scan или переосмыслять прежнее разрешение как live collector/provider authorization.
5. Все preserved executable body functions и guards должны остаться теми же. При сравнении runner AST допустима только замена значения `DIAGNOSTIC_TARGETS`; namespace не требует новых runtime allowances.

## Fixed diagnostic selectors

Минимальный G1 focus — literal `tests/test_preparation_graph.py` и `tests/test_preparation_graph_api.py`. Root может явно включить native preparation/domain/API и document scope/dependency files для проверки существующего seam; тогда этот точный список записывается в новый receipt. Не принимать свободные selectors из environment/stdin/config, не добавлять `-k`/ignore/skip/exclusions в full mode. Diagnostic должен остаться `FOCUSED_DIAGNOSTIC_*_NOT_FULL`, без full/coverage PASS claim.

## Explicit current source pins

Predecessor map — 573 entries. Backend application metadata объявляет **6 новых paths + изменение existing main**; каждый preimage совпал с predecessor map. Дополнительно approved frontend application меняет уже pinned `frontend/src/types.ts`: его preimage `d85303be…` также совпал с predecessor map. Следовательно, projected map содержит **579 entries**, при точном изменении восьми path bindings, а не только семи backend bindings. Остальные predecessor bindings сохраняются. Ниже actual hashes прочитанного snapshot; root должен подтвердить их на окончательном freeze, не использовать старые sealed postimages после repairs/formatting.

| Path | Current SHA-256 |
|---|---|
| `backend/app/schemas/preparation_graph.py` | `4d7c55dd33295f1e6e9e6750a2da50c1a120e83635836d279857241d1a3fd249` |
| `backend/app/domain/preparation_graph.py` | `440395ce3c9d3bf52e64c371018cd32f0d4b79de9e5f534a84b5745b73876364` |
| `backend/tests/test_preparation_graph.py` | `7fb8dd82d3dbd75aa5a551c2565712f46b5ee8392869311d8e6eaeb830140d44` |
| `backend/app/api/routes_preparation_graph.py` | `188fb95ef36a33456145d452af17d1e9d645540731353e791a3bb2f6fbfec239` |
| `backend/app/schemas/preparation_graph_loader.py` | `985d4a1f6d4dc05ec7c3a5c948a03376d7de612faed6cdb847c05d96ea7657a2` |
| `backend/app/main.py` | `b83563f60e08ccb9ed2522463bca6e1bc94bb31dc2c82f13398cdf59f2f8ad9c` |
| `backend/tests/test_preparation_graph_api.py` | `8afdfeefb81abd305dfa511d1b41dd80d4321ba104acbeae91db0872763d60a4` |
| `frontend/src/types.ts` | `1db0143b20def355da62687d290f34628b7a0d4f1beeab8415689caf20f60ca1` |

Existing pinned `frontend/src/lib/format.ts` и `frontend/src/components/social.tsx` совпали с predecessor bytes. Новые frontend panel/client/i18n/e2e paths принимаются отдельным frontend gate; этот backend helper не является полной проверкой всего frontend. Reviewer не пересчитал fixture payload hashes или все source-tree files: source pins здесь проверены только для перечисленных ordinary code paths, manifests — по их сохранённым bytes.

## Body modes и guards, которые должны сохраниться

- [Default preflight / execute opt-in](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/backend-full/run_full_backend.py:311): без `--execute` не запускаются child/runtime phases. Shared lock не заменяется; source-private paths и drift останавливают preflight.
- [Full argv](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/backend-full/run_full_backend.py:263): все native `tests`, `--cov=app`, threshold **92**, original pytest/plugin/native fixture semantics. Full SQLite затем owned private Unix PostgreSQL; phase-one failure оставляет phase two NOT_RUN, без retry/substitution.
- [PASS predicate](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/backend-full/run_full_backend.py:298): 0 failures/errors/skips, timeout/exit successful, guard receipts present, 0 outside attempts/startup failures, no app preimport, positive private PG connection, identical before/after source pins, confirmed owned cleanup/runtime removal. Diagnostic не превращается в full PASS.
- [Inherited OS sandbox](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/backend-full/run_full_backend.py:135) и negative parent/actual descendant probes сохраняются; Python guard не заменяет OS proof. Real DNS/IP sockets/outside Unix sockets и unlisted research assets запрещены теми же guard bodies.
- [Private PG bootstrap](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/backend-full/pytest_full.py:23) остаётся caller-owned, с SELECT 1 probe и cleanup; native SQLite и PG fixtures не подменяются. URI normalization касается только empty placeholder у этого synthetic server, все исходные method args forwarded.
- [Mock endpoint fixture](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/execution/backend-full/mock_endpoint_plugin.py:10): ровно прежние 5 modules и 6 exact browser cases, host/443/IPv4/TCP constraints, fixed answer без real DNS/socket, function-scoped teardown. Для G1 никакие новые endpoint allowances не нужны.
- Controlled demo/search-none/auth-off/payments-off environment, inherited child guards, fail-closed startup metadata и owned process cleanup сохраняются; никакой live-quality, paid/auth production или STOP resume вывод из offline gate не следует.

**Вердикт:** стратегия допустима при перечисленном exact rebinding и сохранении bodies/guards. Новая helper copy, её manifest, actual source preflight и runtime receipts пока не проверены; это отдельные следующие шаги родителя. Изменение guards, asset scope, PASS predicate, full selectors или thresholds этой стратегией не разрешается.
