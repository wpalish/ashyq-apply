# G3 API wire v1 — routine wrappers for the frozen families

2026-10-12 · **EXTERNAL IMPLEMENTATION OUTLINE / SOURCE NOT_AUTHORED / NOT_IMPORTED / NOT_RUN**.

This note chooses concrete transport spellings inside the already frozen finite families. It is not another design freeze or source/runtime gate. `G3_API_SOURCE_GRANT.json` now permits the external six-path source proposal; root alone applies/runs it. The root storage receipt records 19 SQLite + 19 PostgreSQL controls passed, 5 warnings; that qualification is storage only, not this API or Today.

All additional DTOs below live in the granted new `api/routes_admissions_actions.py`, reuse strict `schemas.admissions_actions.Base`, and do not change the existing pure/schema/model contracts. No extra command, whole-state replacement, explicit clear/none selector, raw URL fallback or public action side effect.

## 1. Exact HTTP and callable surface

Prefix **`/api/profiles/{profile_id}/admissions-actions`**. Each callable takes explicit `profile_id`, native `principal: Principal = Depends(get_principal)` and `session: Session = Depends(get_session)`; in-process callers supply all arguments explicitly.

| Route | Callable / body / response |
| --- | --- |
| GET prefix | `read_admissions_actions` → `ActionsCurrentOutV1`. |
| POST prefix + `/commands` | `write_admissions_action`, direct **existing `ActionRequestV1`** body → exact persisted **`ActionWriteReceiptV1`**, status200 first delivery and replay. No wrapping ACK in mutable view. |
| GET prefix + `/events` | `read_admissions_events(after_revision=0, limit=20)` → `ActionsHistoryOutV1`; revision cursor nonnegative, limit1..100, ascending immutable revision order. |
| GET prefix + `/events/{event_id}` | `read_admissions_event` → exact **`ActionWriteReceiptV1`**; same safe404 missing/foreign. |
| POST prefix + `/preview` | `preview_source_binding`, **`SourceBindingPreviewInV1`** → **`SourceBindingPreviewOutV1`**. Unsaved strict source observation only; no fence, allocated record ID, UUID save, or backfill. |
| POST prefix + `/import-preview` | `preview_legacy_import`, **`LegacyImportPreviewInV1`** → **`LegacyImportPreviewOutV1`**. Unsaved chosen-own-task validation; no raw browser-key deletion/read or import save. |
| GET `/api/profiles/{profile_id}/today` | `read_today(timezone: str | None = None)` → existing **`TodayProjectionV1`**; query zone validated as IANA. Selected plan zone otherwise; labeled UTC display fallback otherwise. |

Router-local validation translates malformed body/query and nonfinite/forged fields to the fixed G3 dictionary; no request input/validation detail echo and no global exception-handler change. Owner/case predicates precede UUID/record/source reads. Existing native401/404/dependency behavior remains intact.

## 2. Exact additional DTO fields

All `profile_id`, result/task/event IDs, UUID/digest/date fields reuse native G3 aliases. Ints are strict/bounded, booleans are not coercions, `extra=forbid`; no arbitrary payload/dict/snapshot field. Nullable fields are explicit.

- **`DocumentReportReviewV1`**: `task_id`, `reasons: list[Literal[report_refers_to_previous_binding, not_needed_is_not_a_waiver]]`. Personal annotation from the saved task, separate from source reasons.
- **`ResultActionLinksV1`**: `result_id`, `programme_information: ActionLinkReadV1`, `requirements_information: ActionLinkReadV1`. Informational/unverified only; current authorized raw lexical links only. Locked output has no newly loaded href, title, proof or link-count enrichment.
- **`ActionsCurrentOutV1`**: `profile_id`, `revision` (0 for genuine no current/no events), `state: CaseActionsStateV1 | None`, `head_receipt: ActionWriteReceiptV1 | None`, `observed_at: UtcTimestamp`, `current_source_statuses: list[SourceReadStatusV1]` (max20), `document_report_reviews: list[DocumentReportReviewV1]` (max400), `action_links: list[ResultActionLinksV1]` (max20). State/head absent iff revision0; otherwise exact validated own head.
- **`ActionsHistoryOutV1`**: `profile_id`, `events: list[ActionWriteReceiptV1]` (max100), `next_after_revision: Revision | None`, `source_evaluation: Literal[not_evaluated]`. Fetch limit+1 only for next cursor; return exactly ≤limit validated ascending bodies, not a complete-history claim or premium history scan.
- **`OccurrenceSelectionInV1`**: `location: ChecklistLocation`, `index: strict int >=0`.
- **`SourceBindingPreviewInV1`**: `result_id`, `purpose: Literal[admission,scholarship,both]`, `award_id: ReferenceId | None`, `occurrences: list[OccurrenceSelectionInV1]` (1..6, unique locations). The exact existing pure raw-occurrence contract chooses one original occurrence per location; same-list duplicates remain separate previews, never merged.
- **`SourceBindingPreviewOutV1`**: `profile_id`, `result_id`, `selection: BindingSelectionV1`, `source_preview_digest: Digest`, `source_status: SourceReadStatusV1`, `observed_at: UtcTimestamp`. No copied prompts/title/excerpt/whole checklist in output. The existing bind/rebind command copies these exact reference-only `selection`/digest fields; the new fenced write rereads/validates them.
- **`LegacyImportPreviewInV1`**: `expected_revision: ExpectedRevision`, `legacy_snapshot_digest: Digest`, `mappings: list[LegacyImportMappingV1]` (1..50, unique task IDs/key digests). Reuse exact existing literal-true/value/confirmation and null original-time fields. No raw browser key map, ownership inference or claimed source version.
- **`LegacyImportPreviewOutV1`**: `profile_id`, `revision`, `legacy_snapshot_digest`, `mappings: list[LegacyImportMappingV1]`, `observed_at`. Chosen saved task binding and optional fresh source-preview tokens must match. These are reviewed applicant declarations, not server proof that browser marks were historically true. No new import token outside the existing command contract.

The command remains the exact closed12 union. Source-only wrappers introduce no additional actor, clock, ID, official-verification, outcome or raw-source authority in client commands.

## 3. Native loader and write seams

- **Ownership/auth**: `api.tenancy.owned_profile`; request `security.get_principal`. Read no_autoflush; command uses existing **`begin_owned_preparation_write`** unchanged (fresh SQLite first BEGIN IMMEDIATE / PG READ COMMITTED + local5s timeout → strong own Profile → active User/member read → existing legacy child ID lock). No private G2 loader import, late Org/User FK, audit or placeholder.
- **Current loader**: own current + scalar max accepted revision in **one** statement, using native shared-route anti-torn-head shape. Genuine absent only if both absent; history-only/current-latest mismatch→saved_unreadable503. Read exact head body, validate copied headers and request/receipt hashes, then own metadata chunks from `domain.metadata_batches` (≤200,≤9;≤1662 IDs) and `validate_current_snapshot`. Metadata does not certify every old body's hash.
- **Event loader**: finite raw row receipt/affected_refs first; existing `validate_model(ActionWriteReceiptV1, ..., saved_unreadable)`; exact ID/profile/revision/schema/kind/UUID/request_digest/receipt_digest/accepted time/affected_refs equality. String UUID columns compare to `str(typed_uuid)`. Never silently omit corrupt rows.
- **Command**: `validate_request`; fence; own UUID lookup before mutable current/source/plan/access; `replay_receipt` exact own accepted ACK. New intent loads checked current, checks expected revision, builds explicit `ActionContextV1`, uses `apply_action`, atomically flushes current plus one event, commits once. Duplicate/lock/commit failure fully rolls back, then fresh own actor/UUID reconciliation. No current/source repair, quota, preparation gate, clock/ID defaults or mutable-view ACK.
- **New-source role**: own result/run + approved/maybe **column** metadata before `has_full_access`; only then actual raw checklist and actual exact award/G1 public `preparation_graph` observation. `build_binding_selection`, `checklist_identity`, `compare_binding` retain raw six lists/indices, scope and null/omission behavior. Recheck original preview/reference before bind/rebind; no arbitrary client checklist/claims accepted. Existing personal action has no premium load requirement.
- **Correction/import/selector**: exact own fully validated declaration receipt with matching affected application; own explicit task mappings and unchanged saved binding/current source token; native persisted selected-plan observation respectively. Missing/foreign declaration404, valid wrong own application422, corrupt saved503. Preserve old reports/history; no latest-status-only restriction or clear selector command.

## 4. UTC storage/header normalization

`models/base.ensure_utc` only attaches UTC to naive values; it returns already aware nonzero-offset PG values unchanged. G3 `UtcTimestamp` requires zero offset. Therefore database column adapters must use **`ensure_utc(value).astimezone(UTC)`** (after non-null/type validation) before constructing EventMetadata/current typed headers or canonical wire. New acceptance context uses native UTC `utcnow()`.

Do not mutate/re-hash saved receipt JSON, change native `ensure_utc`, reinterpret applicant-entered dates/timezones or derive an admission/certificate date. Normalize row `accepted_at` and `updated_at` instants only. Meaningful control: same saved UTC instant read under a PG nonzero session timezone yields equal canonical UTC headers, original ACK and unchanged self-hashes; malformed/missing time still fails closed.

## 5. Export and Today adapters

**`export_admissions_action_records(session, profile_id)`** returns `{'current': CaseActionsStateV1 | None, 'events': all ordered ActionWriteReceiptV1, 'submission_declarations': accepted declaration receipts}` as JSON-compatible personal/reference-only data. Own profile is checked by the existing caller; helper keeps exact profile predicates, no source/plan/auth-account join, locks/DML/new Session/reallocation. After all event bodies load, `validate_complete_export` reconciles full1..N sequence/head; mixed currentN/eventsN+1 or corrupt old row503. Existing export keys/policy stay byte-semantic intact; add `admissions_actions` section plus three counts and note only. Corrections/withdrawals remain full events, never rewrite original submission.

**Today**: choose_origin with genuine G2 current **or history** presence; raw non-null v2 marker `{}` remains selected/unavailable, then saved v1, then none. Stored G3 selector always wins. Explicit public in-process `read_shared_route`, `read_learning_path`, `read_schedule` and native preparation access receive the same explicit session/principal/profile. No self HTTP, second Session, private G1/G2 loader, source fetch, allocator or save.

- G2 head/ref/minutes from exact persisted receipt/accepted slots; preserve slot order and exact version/attempt refs. Current content availability and preparation access stay separate.
- V2 raw persisted sidecar digest/head is separate from refreshed GET DTO; typed saved dated refs remain frozen. Empty/malformed sidecar or native422 maps unavailable, never v1 fallback. V1 retains its native today-based saved-settings/tick projection; bare old lesson IDs receive no invented version.
- Independent G3≤20 targets/G2≤20 saved goals; composite≤40. Role bounds are not promised SQL query counts. Keep unavailable personal component separate from plan/access failure.
- After assembly, one bounded metadata/token recheck (head/selector/plan/owned decisions/access already read). Feed explicit initial/rechecked tokens and final research authorization to existing `TodayComponentsV1` → `project_today`. Change→mixed_revision/needs_refresh; clear newly unauthorized premium slices and withhold contradictory joins. No retry loop/coherent-snapshot claim.
- Personal tasks use no minute allocation; one selected native workload only. Preserve pure stable-ID ordering, entered date uncertainty, previous-cycle semantics, declaration summaries and readiness not_assessed.

## 6. Finite source work and acceptance

Exact root grant: new route + main router registration only + profile export addition only + new real API/Today tests + additive real-writer controls in existing concurrency file. Existing pure schema/domain, models, original120 and storage38 controls, auth/native preparation/G1/G2/delete/Fetcher/config remain unchanged. Test author pins this wire before authoring; this note is not itself source acceptance.

Controls must use actual native two-DB lab/HTTP writes: closed12/safe errors, owner-before-UUID/source, exact replay even changed actor/source/expiry/current corruption, current/head/metadata association corruption, query bounds/locked premium refusal, full>100 export/mixed reads, exact selector/Today one budget/refs/date/access/failure independence, physical absent/present CAS/UUID/lock/rollback/erase/cap races. All new API/Today/concurrency controls remain NOT_AUTHORED/NOT_RUN at this note's seal.
