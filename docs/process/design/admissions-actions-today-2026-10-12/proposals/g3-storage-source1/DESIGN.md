# G3: первый подшаг хранения

2026-10-12 · **DESIGN_ONLY · NOT_APPLIED · NOT_IMPORTED · NOT_RUN**

Короткое уточнение [существующего плана](G3_PERSISTENCE_INTEGRATION_PLAN.md), без нового design freeze. Root — единственный автор/исполнитель. По сообщению root: static4 PASS (mypy401), focusedinitial1 PASS120 / 0 FES / 7 warnings; полный backend на двух БД RUNNING. Здесь приложение не импортировалось, БД/тесты не запускались.

## 1. Точный следующий allowlist

Первый шаг — **две таблицы и их ORM-связи**, с meaningful migrated twoDB контролями. Публичного G3 writer/export/Today/UI на этом шаге ещё нет.

| Путь относительно checkout | Единственное изменение |
|---|---|
| `backend/app/models/admissions_actions.py` — новый | `AdmissionsActionsCurrentRow`, `AdmissionsActionsEventRow`. |
| `backend/app/models/applicant.py` | TYPE_CHECKING-импорты и две Profile relationships. |
| `backend/app/models/__init__.py` | Явная регистрация/экспорт этих двух классов. |
| `backend/migrations/versions/<UNASSIGNED>_admissions_actions.py` — новый | Только две таблицы, их constraints/FKs/index. |
| `backend/tests/test_admissions_actions_concurrency.py` — новый | Начальные migration/storage/rollback/cascade controls; реальные writer races добавятся при API-grant. Имя уже предусмотрено исходным планом. |

**Revision, filename и down_revision: UNASSIGNED**, до свежего root isolated single-head observation. Исторический G2 migration filename не определяет нынешнего parent. Новый точный migration path затем включается в root write-ahead с absence check.

Производственные функции этого подшага — только migration `upgrade()` / `downgrade()` и декларации двух ORM-классов. Новый storage service/helper не нужен. Текущие G3 schema/domain, router/main, export/delete endpoints, native fence и G2 — без изменений.

## 2. Имена, поля и ограничения

Оба класса от native **Base**, без независимого event UUID/time defaults. [TimestampedBase](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/models/base.py:35) содержит updated_at onupdate; у G3 accepted event/time уже задаёт серверный pure context.

| Таблица | Точные поля |
|---|---|
| `admissions_actions_current` | `profile_id` String(32) PK/FK; `revision` Integer; `schema_version` String(32); `state` JSON/PG JSONB; `state_digest` String(64); `updated_at` DateTime(timezone=True), явно head.accepted_at. Все NOT NULL. |
| `admissions_actions_events` | `id` String(32) PK, явно receipt.event_id; `profile_id` String(32) FK; `revision` Integer; `schema_version` String(32); `kind` String(32); `client_write_uuid` String(36); `request_digest`, `receipt_digest` String(64); `accepted_at` DateTime(timezone=True); `affected_refs`, `receipt` JSON/PG JSONB. Все NOT NULL, accepted values явные. |

Ограничения:

- Единственный FK каждой таблицы — applicant_profiles.id, ON DELETE CASCADE. Нет source/result/User/нового Organization FK, current→event FK или третьей таблицы.
- Обе revision CHECK 1..2147483647; обе schema CHECK exact `admissions-actions-v1`. Не создавать revision0-row: genuine absence — нет current **и** events.
- Event kind — CHECK closed12 из существующего CommandKind; без select-clear/none. UNIQUE(profile_id, revision), UNIQUE(profile_id, client_write_uuid). Составной revision unique индекс обслуживает ordered history; дублирующий индекс не нужен.
- Current.state — полный [CaseActionsStateV1](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/admissions_actions.py:799), максимум20 applications / 400 tasks и nullable accepted selector. Head ID остаётся внутри state. State digest по существующему G3 contract.
- Event.receipt — полный [ActionWriteReceiptV1](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/admissions_actions.py:873). request_digest=canonical_request_digest; receipt_digest/accepted_at/schema/kind/UUID/revision/profile/id и typed affected_refs дублируют ровно эту receipt. UUID сохраняется в native canonical форме. Header берётся из реально applied delta; mention-only submission task refs не становятся изменёнными task IDs.
- Полная receipt сохраняет request, actor digest, declarations/corrections, predecessor/before/after digests и safe reference-only delta. EventRefs внутри state остаются строго event_id/revision/kind: head receipt digest в state не вкладывается.
- События append-only в будущем writer; ORM/SQL constraints сами по себе не доказывают криптографическую неизменяемость. Никакого event UPDATE/backfill/upsert/replay timestamp tick.

Profile relationships: `admissions_actions_current: Mapped[AdmissionsActionsCurrentRow | None]` и `admissions_actions_events: Mapped[list[AdmissionsActionsEventRow]]`, обе back_populates='profile', cascade='all, delete-orphan', passive_deletes=False. В новом классе обратная `profile`. Это продолжение [native cascade](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/models/applicant.py:39), без Profile payload/timestamp update. Source disappearance и shared-member account removal не стирают личную историю оставшегося дела.

## 3. Meaningful migrated twoDB acceptance

Все ниже — будущие root тесты, **NOT_AUTHORED / NOT_RUN здесь**, только выделенные synthetic file SQLite и private PG.

1. **Аддитивная миграция:** реально populated parent→new head; только две G3 таблицы/ожидаемые constraints/FKs/unique/index. Native Profile, G2 current/history, legacy sidecar/ticks и выбранные sentinel payload/revisions/timestamps не изменились; нет backfill. Downgrade/re-upgrade удаляет/возвращает только G3, native sentinels сохранены.
2. **Полный typed roundtrip:** synthetic chain реальных pure transitions (source bind, applicant declaration/correction, rebind с earlier-binding report); commit→новый Session. Canonical JSON/IDs/UUID/time/digests/affected headers равны исходным. SQLite time восстанавливается existing ensure_utc; existing validate_current_snapshot/validate_complete_export принимают точные загруженные значения. Не hand-built упрощённая receipt.
3. **Физические constraints:** duplicate own revision, own UUID, event PK; revision0/overflow, bad schema/kind — IntegrityError и rollback. Один UUID у разных Profile допустим. Отсутствующий parent отвергнут при FK-on.
4. **Атомарный rollback:** к prior accepted pair обновить current и вставить физически конфликтующий event в одной транзакции. После rollback новый Session видит прежние current/head/events/native sentinels. Это storage atomicity, не доказательство API CAS/replay.
5. **Case cascade/изоляция:** native Profile DELETE с synthetic preseeded G3 rows удаляет их и сохраняет sibling case. SQLite FK-on + отдельно native ORM FK-off policy, PG FK-on; один общий commit и native status/body сохранены.
6. **Account lifecycle:** native sole-member confirmed erase удаляет дела/G3; shared-member removal сохраняет shared case/events/original pseudonymous actor, без actor User FK. Это последовательные lifecycle controls; настоящие writer/delete races потребуют следующего G3 API.

## 4. Зафиксированные швы следующего API-шагa

- Writer использует неизменный [native fence](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/preparation_transactions.py:22): fresh clean Session; SQLite BEGIN IMMEDIATE первым SQL / PG READ COMMITTED+local5s; strong own Profile→actor/member reads→existing legacy child ID-only lock. Own UUID replay раньше mutable current/source/access. Без нового preparation402 gate для personal commands, late User/Organization FK/audit или G2/legacy save.
- State+один event/header атомарны. Current/latest/fullhead/header проверяются existing [validate_current_snapshot](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/domain/admissions_actions.py:652); history-only/mismatch safe503, без пустого/reset fallback.
- В следующем route grant `export_admissions_actions_records` добавляется в [existing owned export](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_profile.py:277): весь ordered history, exact counts/note, existing [validate_complete_export](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/domain/admissions_actions.py:726); current N/history N+1 real interleaving отказывает safe503. Первый storage шаг export не завершает.
- Native DELETE ordering сохраняется: case Organization→Profile/existing-child; account User→sorted Organizations/memberships→sorted sole Profiles. Дочерние Profile-only FKs/ORM cascades не вводят новый lock order. Physical two-connection write/erase/UUID/CAS controls — следующий шаг, не inherited PASS.

**Контрактного блокера не обнаружено.** Base вместо TimestampedBase event — конкретное решение имеющегося onupdate, не дополнительный audit prerequisite. Принятие storage означает проверенное хранение, а не готовность G3 API/Today/UI/export/релиза. Все прежние STOPs и freeze текущего full gate сохраняются.

## 5. Source pins

Фактически прочитанные dependency bytes; Git/head/runtime не наблюдались этим подшагом.

| Dependency | SHA256 |
|---|---|
| `backend/app/models/applicant.py` | `613cdd1db26bf5dd9bc4af39af310b8720a6edec5e2e68a6090a95d59c8d6c28` |
| `backend/app/api/preparation_transactions.py` | `ecbf9c12c95d6a178bf6d1c8c2aca8dcc3b5522e8b0aa4da64e465c99c68d2d7` |
| `backend/app/schemas/admissions_actions.py` | `61ca24cc599bd215ef43a05a6d3a9f8e9ecaad33bde419bffa9fbc837b8ab43f` |
| `backend/app/domain/admissions_actions.py` | `86483457542cfd79c13b630c7d06eed5afe446a39fd2bf070d1f04f808e29bc8` |

New candidate `backend/app/models/admissions_actions.py`: ABSENT at read.

New candidate `backend/tests/test_admissions_actions_concurrency.py`: ABSENT at read.
