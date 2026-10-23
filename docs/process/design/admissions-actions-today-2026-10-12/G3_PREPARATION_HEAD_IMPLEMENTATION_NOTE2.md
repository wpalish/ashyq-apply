# G3: минимальное чтение сохранённого плана — implementation note 2

**SOURCE_ONLY / PLAN_ONLY / NOT_APPLIED / NOT_IMPORTED / NOT_RUN.** Следующий ограниченный шаг после [note 1](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/G3_NATIVE_HEAD_SEAM_NOTE1.md) и [UI plan 1](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/G3_UI_INTEGRATION_PLAN1.md). Проверен текущий router SHA-256 `92e68f62a9af2ac5e8f474ac87de088bfca483e0b882e53d231b8a5b568d1c6e`. Новые source/test bytes не создавались; root назначает разрешение и выполнение.

## 1. Один endpoint, существующий ответ

`GET /api/profiles/{profile_id}/admissions-actions/preparation-head?origin=g2|legacy_v2|legacy_v1`

Обязательный `origin: Literal["g2", "legacy_v2", "legacy_v1"]`. Ответ непосредственно существующий `s.NativeHeadV1`: [schema:469](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/admissions_actions.py:469). Без wrapper, `none`, `unknown`, clear-команды, списка всех планов, нового allocator или бюджета. Запрос читает явно выбранный origin, не выполняет fallback.

Это собственный сохранённый reference, доступный после expiry. Он не подтверждает доступ к материалам, актуальность источников, готовность или применимость плана. Existing `select_active_preparation` остаётся отдельным явным POST с G3 CAS/UUID, `policy=follow_current_accepted` и точным полученным head. Его повторная проверка native head/access и original-UUID replay не меняются.

## 2. Точный reader без full view

В текущем router добавить локальный `_read_preparation_head(session, profile_id, origin) -> s.NativeHeadV1` и handler `preparation_head(...)` через существующий SafeActionRoute. Не вызывать `_read_plan`, `_safe_plan`, public `read_shared_route/read_learning_path/read_schedule`, G1, premium/access, catalogue, attempts, allocator, worker или clock. Не импортировать private G2 loaders. Today продолжает пользоваться полными native readers для workload; этот endpoint возвращает только head.

| Origin | Сохранённые данные и обязательная проверка | Ответ |
|---|---|---|
| `g2` | Один явно anchored own-profile SQL читает CurrentRow + own max(history.revision), как [native compound pointer:200](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_shared_route.py:200). Затем только одна own HistoryRow того же revision. Raw finite → полная повторная SharedRouteWriteReceiptV1 validation обоих JSON. Сверить current/profile/revision/schema/digest/updated_at и history/profile/revision/UUID/request_digest/accepted_at/origin; точные typed receipt bodies совпадают. Не сканировать все старые тела. | G2HeadV1 из проверенного receipt: profile/revision/UUID/snapshot_digest/allocation_digest/accepted_at. Максимум revision **2147483647**, не предел expected_revision. |
| `legacy_v2` | `_legacy_row` own profile с populate_existing. Raw settings → ScheduleSettings → typed finite; `learning_path is not None` проверяется до truthiness. Raw sidecar → LearningPathSnapshot → typed finite. `{}` означает повреждённый v2 marker, не отсутствие/fallback. Не строить refreshed view. | LegacyV2HeadV1: revision, `reference_digest("g3-native-v2-sidecar-v1", saved)`, saved draft/legacy fingerprints, native settings_fingerprint(settings) как observed structural fingerprint. |
| `legacy_v1` | Та же own legacy row/settings, raw → native typed → finite. Sidecar не нужен. Explicit v1 допустим при наличии v2: это выбранный origin, не автоматический fallback из невалидного v2. | LegacyV1HeadV1: revision, `reference_digest("g3-native-v1-settings-v1", settings)`, settings_fingerprint(settings). |

G2 current+latest должны наблюдаться в **одном statement**, сохраняя native consistency. Оба отсутствуют → plan_unavailable. History-only, current-only или несовпадающий latest revision → plan_unreadable, без reset/fallback. Full receipt validation сохраняет native self-hashes и [current/history binding:149](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_shared_route.py:149).

Сохранить точные [head constructors:1367](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/api/routes_admissions_actions.py:1367). settings_fingerprint исключает completion IDs, а saved-settings digest их сохраняет; revision также сохраняется. Несовпадение saved legacy fingerprint с current settings остаётся наблюдаемым reference, не исправлением/заявлением готовности. Legacy snapshot не имеет G2 immutable receipt self-hash; новый endpoint не придумывает эту гарантию. Raw и typed проверки идут до JSON normalization, в том числе при model_construct/model_copy.

Root может вынести только чистые локальные `_g2_head_from_receipt` / `_legacy_head_from_saved`, повторно используемые нынешним _read_plan и новым reader. Это устраняет дублирование wrapper strings; workload/content/status ветки и native loader files остаются прежними. Такой факторинг не отдельное предварительное условие реализации.

## 3. Ownership и ограниченные наблюдения

Весь handler внутри `session.no_autoflush`:

1. `_owned_read` до native queries: own organization/profile плюс действующие User/membership.
2. Начальный `_native_markers(...).token`, head-only read, конечный marker.
3. Перед возвратом повторить `_owned_read`: свежий ownership SQL с organization predicate и actor/membership. Старого Principal/identity-map объекта недостаточно.
4. Изменение tokens → фиксированный plan_head_changed409, без retry/repair/reallocation. Marker включает все native origins и profile updated_at; отказ при изменении другого origin консервативен. Два bounded observations не являются обещанием snapshot/linearizable GET.

Не брать write locks, не запускать strong write, commit/rollback/flush. Unrelated pending new/dirty/deleted state caller session не терять при GET/error. Unexpected SQL/parse faults возвращают безопасный словарь, не repr/SQL/raw input. Terminal owner/actor refusal имеет приоритет перед выдачей частного head.

Typed DB headers нормализовать через существующий `_db_utc` = ensure_utc(...).astimezone(UTC), сохраняя microseconds. Исходные JSON, receipt hashes и объявленные local dates не менять.

| Условие | Существующий безопасный ответ |
|---|---|
| Missing/invalid origin, malformed query | admissions_actions_input_invalid422, route-local, без input echo |
| Requested plan отсутствует; legacy invalid в нынешней raw/typed parse boundary | admissions_actions_plan_unavailable422 |
| G2 pointer/body/header/history inconsistency; unexpected SQL/read failure | admissions_actions_plan_unreadable503 |
| Изменившийся head | admissions_actions_plan_head_changed409 |
| Foreign/missing/deleted/moved case; revoked actor/membership | native404 Applicant case not found / native401 Authentication required |

Для DB-header/new head-validation ошибок сохранить safe503 без вывода значения. Не менять глобальные validation handlers, SafeActionRoute или существующий finite dictionary.

## 4. Точное type/client добавление

Уже есть NativeHeadV1 и isNativeHeadV1: [types:331](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/types/admissionsActions.ts:331). Новый wire type не нужен. В [client:504](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/frontend/src/api/client.ts:504) добавить один метод:

`admissionsPreparationHead(profileId: string, origin: NativeHeadV1["origin"]): Promise<NativeHeadV1>`

Использовать native request<unknown>, encodeURIComponent(profileId) и query({origin}); импортировать существующие NativeHeadV1/isNativeHeadV1. Перед возвратом проверить validator + head.profile_id === profileId + head.origin === origin; отказ — fixed ApiError503/code admissions_actions_plan_unreadable, без body echo. Native request owner checks до/после JSON сохраняются. UI отдельно удерживает DraftIdentity + captured case ID/caseEpoch + operation generation: stale response не рисуется и не журналируется.

GET не создаёт UUID/selector и не отправляет POST. После просмотра head нужен отдельный подтверждённый selector intent с exact head/original UUID journal. После409 — новое явное чтение, без auto-write. Screens/navigation/material handoff/retention64 UX этим шагом не считаются реализованными.

## 5. Конечные будущие acceptance controls

Минимальный предполагаемый allowlist root: существующий router; новый backend/tests/test_preparation_head_api.py; existing client и client.admissionsActions.test.ts. NativeHead schema/domain/types/models/migrations/native routes не требуют изменения. Backend использует настоящий migrated two-DB shared_route_lab и native writers, без fake accepted receipts или mock full-plan ответа.

- Реально сохранённые три origin → точные native heads, включая альтернативный origin. Own expired GET reference работает; selector POST → Today сохраняет один chosen workload/бюджет и прежние material/access ограничения.
- Полные public readers/G1/content/attempts/entitlements/allocator не вызываются. SQL capture и fresh snapshots: ноль DML/backfill, revisions/marks/history неизменны. Direct dirty caller session сохраняет pending state, без auto-flush/rollback.
- G2 absent/absent, current-only/history-only, revision/header/digest/UUID/time/body mismatch, raw NaN/±Infinity/coerced nonfinite → safe отказ без fallback. Positive PG aware nonzero-offset header даёт тот же UTC instant/microseconds; saved JSON/hash прежние.
- Legacy null / `{}` / invalid sidecar, raw/typed nonfinite. Explicit v1 при v2 читается как v1. Display as-of/content availability не входят в persisted sidecar digest. Completion tick меняет revision/full settings digest, не structural fingerprint.
- Реальный committed native save между наблюдениями →409; actor/membership revocation и case move/delete перед terminal fence →401/404 без head. Использовать второе соединение/SQL event interception, не подменять marker/head готовым ответом.
- Foreign/unauthenticated/forged query →fixed safe responses; новые GET не ослабляют существующие POST head recheck и accepted-UUID replay.
- Client exact GET path/query, strict origin/profile/head, 409/503 и owner change во время fetch/JSON. UI caseEpoch late response не входит в selector draft. Нет autoPOST/source retrieval/UUID generation.

Все controls — **предложения, NOT_AUTHORED/NOT_RUN**, не результаты. Нового общего audit/freeze prerequisite нет; root выдаёт точный source grant и запускает gate. Все прежние STOP границы сохранены.
