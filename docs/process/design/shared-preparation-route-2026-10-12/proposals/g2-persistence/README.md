# G2: внешний пакет persistence/API

**Статус: SEALED_SOURCE_PROPOSAL, NOT_APPLIED, NOT_IMPORTED, NOT_RUN.** Этот пакет содержит пять полных предлагаемых файлов. Он не подтверждает интеграцию, миграцию, прохождение тестов, публикацию или готовность всего продукта.

Разрешение и preimages: [root write-ahead](design-references/G2_PERSISTENCE_SOURCE_WRITE_AHEAD.json). Решения: [root integration contract](design-references/ROOT_G2_PERSISTENCE_INTEGRATION_DECISIONS.md). Root сообщил актуальный HEAD `f3efd228`; Git здесь не читался и не менялся. Непосредственно проверены байты разрешённых source preimages: прежняя schema сохранена, четыре новых пути в root checkout ещё отсутствуют. Root остаётся единственным автором application integration, Git и execution.

## Состав и ограничение изменения

| Предлагаемый путь | Назначение | До пакета |
| --- | --- | --- |
| [backend/app/schemas/shared_route.py](files/backend/app/schemas/shared_route.py) | Дополнительные strict preview/write/receipt/current DTO и проверка immutable bindings | Existing; исходник сохранён в [originals](originals/backend/app/schemas/shared_route.py) |
| [backend/app/models/shared_route.py](files/backend/app/models/shared_route.py) | Текущая версия по profile PK и immutable own history | Absent |
| [backend/app/api/routes_shared_route.py](files/backend/app/api/routes_shared_route.py) | Preview, atomic PUT, immutable ACK/history, current statuses, reference-only export | Absent |
| [backend/app/api/preparation_transactions.py](files/backend/app/api/preparation_transactions.py) | Общий свежий write fence parent → existing legacy child | Absent |
| [backend/migrations/versions/c3e71d902023_shared_route.py](files/backend/migrations/versions/c3e71d902023_shared_route.py) | Только две новые таблицы; predecessor `b5c81d9e2022` | Absent |

`backend/app/domain/shared_route_allocator.py` не входит в application delta: его полный исходник и SHA сохранены как read-only [reference](source-references/backend/app/domain/shared_route_allocator.py). Все 30 прежних class/function AST schema совпадают с preimage. Сохранены exact lesson/reference identity, action conservation, два персональных exam streams, один weekly/daily budget и optional target keys. Никаких ослабленных типов, ignores или замены domain allocator.

## Стабильный API контракт

Префикс: `/api/profiles/{profile_id}/preparation/shared-route`.

| Метод | Суффикс | DTO / результат |
| --- | --- | --- |
| GET | пустой | `SharedRouteCurrentOutV1`: `{profile_id, revision, view|null}` |
| POST | `/preview` | `SharedRoutePreviewRequestV1` → unsaved `SharedRoutePreviewOutV1` |
| PUT | пустой | `SharedRouteWriteV1` → exact immutable `SharedRouteWriteReceiptV1` ACK |
| GET | `/revisions/{revision}` | `SharedRouteViewV1`: immutable receipt + отдельные current statuses |

Preview input: `{applicant_input, expected_revision}`. `applicant_input` — существующий strict `SharedRouteInputV1`, включая exact ordered 2–20 own approved/maybe results, 1–2 personal exam choices, timezone, starts_on, study_days, shared_weekly_minutes и exact own_review refs. Сохраняются только реально переданные personal target component keys; отсутствующие targets не превращаются в `null` fields.

PUT input: `{applicant_input, expected_revision, client_write_uuid, preview_fingerprint, source_fingerprint, legacy_anchor, planned_on}`. Клиент копирует binding values из показанного preview; API пересчитывает новую команду под fence. Preview fields: `profile_id`, `expected_shared_revision`, `legacy_anchor`, `planned_on`, `expires_on_local_date` (та же дата), `requested_result_ids`, `selected_result_ids`, `selection_source='server_verified_owned_explicit'`, `source_fingerprint`, `allocation`, `preview_fingerprint`, `review_reasons`, `saved=false`.

Receipt: `schema_version='shared-route-v1'`, `profile_id`, `revision`, `expected_revision`, `client_write_uuid`, `canonical_request_digest`, `accepted_at` UTC, exact `selected_result_ids`, `applicant_input`, `accepted_planned_on`, catalogue/planner versions, `catalogue_snapshot`, `owned_review_snapshot`, immutable `allocation`/`allocation_digest`, source fingerprint + ordered per-goal reference digests, preview fingerprint, legacy anchor и full snapshot digest. Сохраняются reference availability и персональные планы; raw G1 proofs, premium names, questions/answers, score feedback и current dynamic statuses в receipt не копируются.

Current view: `{receipt, current_status, visible_evidence}`. `current_status` отдельно содержит UTC `as_of`, ordered `goal_statuses`, legacy/imported status, exact-action `content_statuses`, `preparation_access`, `needs_review` и конечные typed `review_reasons`. Current G1 singleton slices доступны только для разрешённых owned goals; финально наблюдаемый research lock очищает все premium slices. `eligible` здесь означает текущую доступность выбранной цели и совпадение source binding, а не admission eligibility, доказательство waiver или готовность подать заявку.

## Запись, replay и erasure coordination

- Owner и текущие реальные User/Membership проверяются до own UUID lookup; чужой profile/history не раскрывается. Exact accepted UUID/digest возвращает прежний ACK до term/source/revision/catalogue gates и не пишет новую версию. Другой payload с тем же UUID получает 409.
- Свежая запись требует clean Session. Pending new/dirty/deleted/nested state не commit/discard. Только clean preflight reads rollback. SQLite: первым физическим guarded SQL идёт `BEGIN IMMEDIATE`; inherited busy timeout сохраняется. PostgreSQL: fresh asserted `READ COMMITTED`, transaction-local lock timeout 5 s, strong owned Profile `FOR UPDATE`, затем existing legacy child `FOR UPDATE`.
- Child lock выбирает **только ID**, без декодирования legacy settings/sidecar JSON. После ожидания повторный UUID lookup идёт до legacy semantic parsing, source, term и allocation. Нет placeholder child, legacy DML, parent timestamp DML, global mutex, поздних Org/User locks или audit FK.
- Root использует `begin_fresh_preparation_write`, `lock_owned_preparation_profile`, `begin_owned_preparation_write` в coordinated delete. Case/account erase lock order остаётся root-owned; helper не вводит обратные parent/user/org locks.
- Новая команда проверяет весь selection, current revision, legacy structural anchor, текущую explicit native evidence manifest и exact content/reference availability. Перед acceptance повторно читает native G1 с fresh ORM state, catalogue, actor и term. Финальное actual UTC `accepted_at` переводится в выбранную IANA timezone; если местная дата уже отличается от preview, 409 без автоматического перераспределения.
- Current CAS + unique history/profile/revision + unique profile/UUID flush/commit атомарны. На timeout/integrity/commit ambiguity сначала rollback, затем fresh owner/actor/original UUID reconciliation; совпавший accepted ACK читается, новую команду сервер не создаёт.
- Research source writers не разделяют этот parent fence. Контракт подтверждает наблюдённые source manifests и повторный read около acceptance; он не обещает глобальную serializable snapshot of research/auth/terms.

## Immutable reads и export

`SharedRouteCurrentRow`: profile PK/FK, revision/schema/snapshot/digest/updated_at. `SharedRouteHistoryRow`: own profile FK, revision/UUID/request_digest/receipt/accepted_at/origin и TimestampedBase. Relationships ожидаются root: `shared_route_current` scalar и `shared_route_history` list, обе `back_populates='profile'`.

Stored receipt проходит raw/typed finite checks, strict parsing, authoritative row-column bindings, exact action/reference conservation и request/preview/allocation/full-snapshot digests. GET/history/export/replay не вызывают allocator. Один SQL statement читает current pointer и maximum accepted history revision: absent current с history либо несовпадающий pointer — safe 503, без silent repair/reset revision zero. Exact own UUID replay и history revision остаются читаемыми независимо от сломанного current pointer.

Root export seam: `export_shared_route_records(session, profile_id)` (caller уже проверил owner) → `{'current': typed_receipt|null, 'history': all_typed_own_receipts}`. После чтения typed current и всех typed histories дополнительно сравниваются их actual loaded heads; absent iff no history, иначе current revision должна равняться последней history revision. Interleaved READ COMMITTED save даёт safe 503, а не current N/history N+1. Нет retries, locks, DML, нового transaction или переаллоцирования.

## Native adapters и controlled failures

Только публичные in-process native `preparation_graph(...)` / `review_attempt(...)` с explicit `profile_id`, selection/UUID, principal и **тем же Session**. Private G1 assembly, HTTP, workers, adapters, providers и quota не используются. New own-review import требует explicit exact native lesson/version registry → track → exam association; missing association отказывается целиком, без угадывания по ID. Старый accepted review reference остаётся читаемым даже после retirement lesson/version.

Safe codes: 409 `shared_route_revision_conflict`, `shared_route_uuid_conflict`, `shared_route_preview_stale`; 503 `shared_route_saved_unreadable`, `shared_route_write_unconfirmed`, `shared_route_legacy_unreadable`, `shared_route_evidence_unreadable`, `shared_route_binding_unreadable`; native 402 `preparation_subscription_required`; 422 `review_reference_mismatch`, `review_exam_unestablished`, `review_exam_mismatch`. Native owner/missing/decision 404/422 сохраняются. Helper begin/lock SQL failures rollback + controlled 503; dirty state отвергается без discard. Ошибки не маскируются пустыми успешными данными.

## Source-only проверка и обязательные acceptance gates

[SOURCE_ONLY_CHECKS.json](SOURCE_ONLY_CHECKS.json) — AST parsing пяти files, byte/preimage checks, сохранность прежних 30 class/function AST, domain unchanged pin, explicit native-call argument inspection и отсутствие network/provider imports. Это metadata evidence, **не Ruff/mypy/import/pytest/migration proof**. Source snapshots, design decisions, SHA/bytes и manifest закреплены в [SEAL.json](SEAL.json).

Source fixes по root/peer review включены: finite ReviewCode maps без f-strings; fresh acceptance local date; один SQL current/history pointer check; экспортная final loaded-head consistency; legacy ID-only lock до UUID replay; raw и post-typed finite native graph guards; финальный research-access recheck даже при пустых visible slices. Их runtime closure ещё NOT_RUN.

Root должен отдельно подтвердить: source-bound Ruff/mypy; unchanged allocator/pure assertions; API owner/UUID/CAS/status/export corruption controls; реальные SQLite и PostgreSQL concurrent histories, legacy absent/present writes, lost ACK, delete ordering и rollback; controlled migration upgrade/downgrade/seed/current single head; затем соответствующий полный backend/static suite и native FE journey. Не заменять физический PostgreSQL прогон SQLite, не считать skipped controls успешными. По мере изменения source root должен сохранять first failure и новые source pins.

Этот increment создаёт персональный shared preparation plan. Он не публикует полный IELTS/SAT course, новые unseen diagnostics, official bands/scores, гарантии поступления, результат search-quality/500 audit или весь продукт Ready. Существующие STOPs и закрытые provider/security/label workflows не возобновлялись.
