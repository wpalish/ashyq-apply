# G1: независимый review pure/schema/test proposal

**12.10.2026 · SOURCE REVIEW ONLY · приложение и тесты не запускались.**

Область: sealed G1 proposal и узкие исправления, внесённые родителем в `work/unimatch-calendar-materials` во время review. Это оценка исходников; она не подтверждает успешный импорт, прохождение gates, готовность нового API, публикацию или готовность всего продукта.

## Привязка и сохранность

- [Sealed receipt](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/SEALED_RECEIPT.json) описывает исходный proposal на application anchor `9d3315e8cf2dcca93e01de8aa1fd6c7abbbbe557`. Parent сообщил текущий исходный HEAD `e66bf341`; Git-команды reviewer не выполнял.
- Независимо проверены SHA-256 всех **5 sealed файлов**: совпадают с receipt. Proposal, README и receipt не перезаписывались.
- До применения родителем независимо сверены **7 исходных seam hashes** из receipt: совпадали. Эта проверка относится к моменту до интеграции, а не является обещанием неизменности checkout после правок родителя.
- AST чтение sealed test source обнаружило **37 функций `test_*`**, текущее чтение после двух новых тестов — **39**. Это число функций в тексте, не число collected/passed cases.
- Reviewer читал обычные исходники и писал только этот внешний отчёт. App imports, тесты, БД, сервер, migrations, providers/models, labels/held-out, stopped collectors, Git/HANDOFF и секреты не использовались.

## F1 — P1: состояние документов не входило в агрегат

**Подтверждено по sealed source.** В [_document_actions](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/files/backend/app/domain/preparation_graph.py:331) отдельный документ получает `conflicted`, `stale` либо `unknown`. В [programme_states](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/files/backend/app/domain/preparation_graph.py:516) учитывались только exam atoms; [graph aggregate](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/files/backend/app/domain/preparation_graph.py:545) наследовал это состояние программы.

При current IELTS и отдельном конфликтующем/устаревшем документе программа и граф могли остаться `current`. `projection_state=partial` и `requires_review` сохранялись, поэтому это не доказательство готовности документа; однако `evidence_state=current` противоречил обещанному смешанному агрегату в [README, п. 3](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/README.md:22).

**Минимальный синтетический сценарий, без выполнения:**

1. Программа A: exact scoped current IELTS atom, `partial=False`, `stale_result=False`.
2. Checklist A с Transcript и точным claim ID; статус document claim по очереди `CONFLICTING`, `POSSIBLY_STALE`, `VERIFIED_CURRENT`.
3. Программа B: только независимый current IELTS.
4. A и aggregate должны стать соответственно `conflicted`, `stale`, `unknown`; IELTS A и программа B остаются `current`. В третьем случае документ всё ещё `unknown`, поскольку его формат/условия не нормализованы полностью.

**Минимальное исправление:** добавить `own_documents[*].evidence_state` в `programme_states`, сохраняя известные atom states и original checks.

**Root actual source:** исправление видно в [domain:685](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/domain/preparation_graph.py:685). Новый [test_document_uncertainty_remains_in_programme_and_graph_state](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_preparation_graph.py:545) проверяет три состояния, отдельный IELTS и вторую программу. По чтению исправляет F1; execution evidence в этом review отсутствует.

## F2 — P1: ID и имя scholarship использовали неполную проверку уникальности

**Подтверждено по sealed source.** В [award_name_counts / subject_keys](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/files/backend/app/domain/preparation_graph.py:478) проверялись коллизии name↔name. ID всегда добавлялся, а уникальное имя добавлялось отдельно. Поэтому alias одного award мог одновременно быть ID другого award.

**Минимальный синтетический сценарий, без выполнения:**

| Award | ID | Name |
|---|---|---|
| A | `award-a` | `One` |
| B | `award-b` | `award-a` |

Один exact scoped official current score claim с `subject_key="award-a"` и два checks, ссылающихся либо на его exact ID, либо на общий legacy URL. Sealed source включал claim в оба award pools; native `project_checks` мог подтвердить один score для обоих awards. Это подмена предмета доказательства, даже при правильном programme scope. Existing [duplicate names test](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/files/backend/tests/test_preparation_graph.py:375) данный cross-namespace случай не покрывал.

**Минимальное исправление:** глобальный `normalized alias → set of exact award IDs`, содержащий одновременно все ID и names. Claim допускается в award pool только при owner set ровно `{current_award.id}`. Ни exact claim reference, ни URL reference не должны разрешать неоднозначный subject.

**Root actual source:** [глобальная alias map](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/domain/preparation_graph.py:627) реализована; [новый parametrized test](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/tests/test_preparation_graph.py:520) проверяет exact ID и legacy URL, отсутствие proofs и сохранность original references. По чтению устраняет описанную ID↔name коллизию. Map также делает неоднозначными normalized-ID коллизии вроде `award-a` / `AWARD-A`; отдельный тест этой ветки пока не найден.

### Узкий остаточный случай F2: пустой alias

В прочитанном snapshot map допускает `""`. [Scholarship.id/name](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/result.py:75) и [Claim.subject_key](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/claim.py:35) — обычные строки без запрета пустого/whitespace значения.

Один award `id="award-a", name=" "` и current scoped score с `subject_key=" "` получают один нормализованный пустой alias. Единственность пустой строки не устанавливает subject identity. Это source-only остаток, переданный родителю; runtime reproduction не выполнялась.

Минимальная защита — исключить пустые normalized aliases при построении map и `subject_keys`, сохранив исходные DTO. Синтетический тест: whitespace name/subject, exact ID и URL refs → `unknown`, no proofs, no hints, original refs intact; unique непустой alias должен продолжать работать. Этот случай следует закрыть вместе с F2, не вводя новую широкую миграцию/schema policy.

## Что source review подтверждает в узких границах G1

| Контур | Оценка исходников | Граница приемки |
|---|---|---|
| Explicit selection | Request 1–20 exact IDs, whole-selection errors, owned envelope/profile check и explicit order предусмотрены в pure builder и tests. | Dataclass не доказывает DB authorization. Нужен native route ownership test и ordered response receipt. |
| Proof/scope/freshness | Reused native `project_checks`, exact compatible references, three-valued scope и stale/conflict state; original check copied. | Loader обязан переопределять авторитетные row columns, вычислять freshness на одном `now` и не заимствовать claims чужого result/case. Stored check status не становится новым eligibility verdict. |
| Locked minimization | Locked DTO/builder запрещают premium names, run ID, scope, claims, docs/questions/digests и custom reasons. | Research entitlement проверяет server loader; preparation subscription не открывает research. |
| Scholarship purpose | Admission/award atoms раздельные; score summary без check не создаёт цель; ambiguous subject остаётся unresolved после исправлений F2. | Пустой alias и normalized-ID regression требуют закрытия; availability award не является доказанной применимостью. |
| Alternatives/waivers | Сохранены отдельные unresolved waiver/alternative contexts, original predicate/quotes/proofs. | Нет accepted branch, inferred AND/OR, waiver fulfillment или общего score maximum. |
| Documents | Exact cross-location semantic owner projection сохраняет originals; same-list repetitions, owner/purpose/scope/prompt distinctions не стираются. Зависимости только внутри result; missing/ambiguous/scope gaps/cycles видимы. | `linked` не равно выполнено; все fulfillment `untracked`, actions `requires_review`. Чужой offer не фабрикуется как документ. F1 должен остаться исправленным. |
| Exam groups | `family_only`, unknown identity/edition/route; нет invented component scores. | Это observations, не shared workload, versioned learning task, accepted study plan или admission readiness. |
| Manifest | Selected source view, exact displayed proof IDs и policy context предусмотрены. | Fingerprint не гарантирует immutable transaction snapshot и не является persisted accepted plan/quality score. |

## Приёмка по порядку

1. Закрыть F1 и F2 фактическими native synthetic cases; для F2 включить пустые aliases и normalized-ID collisions. Sealed packet оставить историческим, исправления — только в actual source родителя.
2. На source freeze выполнить native format/type/pure/DTO gates и сохранить реальные receipts. Не заменять существующие tests новым proposal suite. Reviewer запусков не делал.
3. Проверить [обязательные loader/API cases](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g1/API_LOADER_WIRING_PLAN.md:23): own profile, foreign/missing generic 404, rejected/undecided 422, ordered whole selection; locked/expired entitlement; authoritative columns/scope/freshness/global partition; malformed and unresolved conflict fail conservatively; GET без writes/network/worker effects. Этот pure review не заменяет API review.
4. Frontend должен сверять оба selection receipts, case и request generation; показывать original checks отдельно от current source evidence и unresolved alternatives/dependencies. G1 не поддерживает UI «сохранён общий план»/«работа выполнена».
5. Провести обычный synthetic native walkthrough нескольких ordered programmes: разные admission/award scores, locked slice, conflicting/stale document, ambiguous dependency и selection change. Не запускать closed pilots/labels/providers для приемки этой read-only проекции.

**Вердикт:** узкий G1 design сохраняет нужные границы и пригоден для native проверки после закрытия указанных случаев. F1 и ID↔name часть F2 исправлены по actual source inspection; blank alias остаток передан родителю. Успешный runtime, API readiness и готовность всей платформы этим документом не заявляются.

## Snapshot actual source после первых двух исправлений

Хэши только прочитанного snapshot после форматирования; последующие исправления родителя могут их изменить:

| File | SHA-256 |
|---|---|
| `backend/app/schemas/preparation_graph.py` | `4d7c55dd33295f1e6e9e6750a2da50c1a120e83635836d279857241d1a3fd249` |
| `backend/app/domain/preparation_graph.py` | `90b425a4631412376326b3f30eac9759708255b6ce5acb0c1fb56022474e9a55` |
| `backend/tests/test_preparation_graph.py` | `b3c909fcb2dd07fc85387d7d0783ac603f2a829974eb245d9aa7db2c3356464f` |
