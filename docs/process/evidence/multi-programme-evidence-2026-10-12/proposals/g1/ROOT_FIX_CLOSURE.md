# G1 root fixes: закрытие findings по исходникам

**12.10.2026 · RESOLVED_BY_SOURCE_INSPECTION / PENDING_NATIVE_RUNTIME.**

Это отдельное дополнение к [исходному review](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/G1_PURE_SOURCE_REVIEW.md). Его прежний текст, sealed code и receipt сохранены. Проверен текущий actual source в `work/unimatch-calendar-materials`; импортов приложения, тестов, migrations, Git, runtime или provider действий reviewer не выполнял.

## Закрытие

| Finding | Actual source | Содержательный test source | Статус |
|---|---|---|---|
| F1: документы выпадали из общего evidence state | [DocumentAction states добавлены в programme_states](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/domain/preparation_graph.py:684) | [current IELTS + CONFLICTING / POSSIBLY_STALE / VERIFIED_CURRENT document](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_preparation_graph.py:575): programme/graph соответственно conflicted/stale/unknown, отдельный IELTS и вторая программа current. | Закрыт по чтению. |
| F2: alias name одного award совпадал с ID другого | [Единый normalized alias → exact owner IDs](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/domain/preparation_graph.py:627), допустим только owner set `{award.id}`. | [Exact claim ID и legacy URL collision controls](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_preparation_graph.py:520): оба awards unknown, no proofs, original references intact. | Закрыт по чтению. |
| Остаток F2: пустой normalized alias принимался за subject identity | [Map исключает пустую строку, subject_keys также требуют непустой alias](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/domain/preparation_graph.py:629). Short-circuit `if alias` предотвращает lookup отсутствующего пустого key. | [Пустой и whitespace subject/name](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_preparation_graph.py:537) остаются unknown без resolved claim IDs. | Закрыт по чтению. |
| Normalized-ID regression control | Та же глобальная owner map сохраняет разные exact award IDs даже при одинаковом normalized alias. | [Award-A / award-a / subject AWARD-a](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_preparation_graph.py:551): два независимых unknown atoms без proofs. | Тестовый источник добавлен; runtime pending. |

Пустые aliases удалены только из поиска доказательства, без изменения legacy Scholarship/Claim schemas. Для непустого уникального subject сохраняется прежний механизм; admission и scholarship purpose не объединены. Documents всё ещё `untracked`/`requires_review`, а VERIFIED_CURRENT document claim не подтверждает автоматически все форматные и условные поля.

## Точные pins прочитанного snapshot

| Actual file | SHA-256 |
|---|---|
| `backend/app/schemas/preparation_graph.py` | `4d7c55dd33295f1e6e9e6750a2da50c1a120e83635836d279857241d1a3fd249` |
| `backend/app/domain/preparation_graph.py` | `440395ce3c9d3bf52e64c371018cd32f0d4b79de9e5f534a84b5745b73876364` |
| `backend/tests/test_preparation_graph.py` | `7fb8dd82d3dbd75aa5a551c2565712f46b5ee8392869311d8e6eaeb830140d44` |

Все **5 sealed proposal hashes** повторно совпали с [SEALED_RECEIPT.json](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/SEALED_RECEIPT.json). AST текущего schema равен sealed schema за исключением module docstring и форматирования. В current test source **41 функция `test_*`**; это не collected/passed count. Проверка выполнена isolated system Python standard library по сохранённым байтам, без app imports и выполнения кода проекта.

## Что остаётся подтвердить

- Native format/type/pure/DTO/API gates на frozen source и соответствующие реальные receipts. Этот документ не заменяет их и не сообщает PASS.
- Новый server loader: owned complete ordered selection, entitlement/minimization, authoritative row columns, one freshness timestamp, scope/global claim partition, malformed evidence handling и GET без side effects. Pure fix closure не является проверкой endpoint.
- Existing legacy regressions, полный SQLite/PostgreSQL backend gate и frontend request-receipt/uncertainty presentation приемка.
- G1 остаётся read-only evidence projection. Accepted shared plan/workload, completed documents, admission outcome, live search-quality измерение, deployment и full-product readiness не заявляются; действующие STOPs сохранены.
