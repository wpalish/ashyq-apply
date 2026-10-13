# Unimatch core implementation progress

Root solo; branch `task/admissions-actions-today`. Current release status: **core incomplete / production unchanged / live search quality not measured**. IELTS/SAT learning remains optional.

| Stage | Current state | Exact local evidence / remaining work |
|---|---|---|
|0 baseline/reuse|Reviewed and reconciled|892fc5e5; G3 selected over separate ecd10015 product-completion. No merge.|
|1 early programme observation|Locally verified|e9677b2e/64a8ea3e; full5765 each native default DB phase,94.33/94.32%; API ownership/export/delete and timeout/cancel/lease controls; frontend732 before commands. Quality still separate.|
|2a Store/journal safeguards|Locally verified|746 frontend tests/build; synchronous G3 case generation, captured lateDELETE, exact selected ACK cleanup/cap64/corrupt index; backend exact full3 carry.|
|2b forms transport/recovery|Locally verified, not mounted in Documents yet|769 frontend tests/build; typed hook, original envelope/UUID/body/CAS, own digest-checked fresh current, explicit retry/ACK-only cleanup/reconciliation, tested recovery panel EN/RU/KK.|
|3a documents|Personal metadata forms locally verified|778 frontend tests/build; manual create/date+notes/self-report/history/recovery mounted. Source binding and explicit legacy import now locally verified (786 tests); label/responsible/delete extension and integrated reload remain.|
|4 applications|Incomplete|Existing G3 selected-result events/history; manual application needs compatible versioned extension because frozen v1 requires result_id.|
|5 Today/dates|Incomplete|Server G3 projection exists; exact navigation/date-only/unknown timezone and optional learning split remain.|
|6 integrated journey|Not run on these changes|Demo/Auth/second login/export/delete/errors/320–1440 layout still required.|
|7 live search quality|Blocked by existing STOPs|Separate live/heldout authorization required; no inferred score from local tests.|
|8 release|Not done|Main/deployment/production/containers untouched; operator and quality acceptance gates remain.|

Current evidence indexes: `evidence/core-completion-2026-10-13/checkpoint1`, `checkpoint2`, `checkpoint3`, `checkpoint4`, `checkpoint5`, `checkpoint6`. Original failed attempts are preserved; later qualification names actual accepted source. New request generation is distinct from the existing UI feedback epoch, whose exact deletion behavior remains covered by unchanged original tests. Clearing local ACKs never deletes server actions/history. A client ACK is not an official university submission or document verification.

Old findings still requiring implementation/verification: LocalDate display, timezone deadline comparison, stable document binding forms, legacy Documents JSON-null handling, Billing case-bound access on failure, unavailable-list wording, profile-version stale-result notice and read-time source age. Backend tests and source review do not accept this entire product.

## Manual application contract checkpoint (WIP)

Explicit V2 application targets now store applicant-entered university/programme/intake/route with no fabricated evidence IDs. The original V1 classes and accepted receipts remain closed and unchanged. Existing personal/declaration/correction commands operate on the V2 aggregate. Native current/Today/history/export/replay/no-research/foreign/CAS/migration controls ran on both explicit DB fixtures. First full SQLite-default phase: 5783 passed, two failures in a new test expecting a declaration delta where the existing export returns its full receipt. Exact test-only correction is applied; the repeat and PostgreSQL-default full phase are pending. No feature acceptance, integrated browser proof, live search quality or deployment is claimed. FE4b is external proposal only.

## Manual applications — server qualification

Fresh full native5 gates: **5785 passed in each SQLite-default and PostgreSQL-default phase**, zero failures/errors/skips, coverage **94.28665% / 94.28195%**. Both retain the existing explicit native SQLite/PG fixtures. Exact 638 consumed files per phase match current primary/lab; network guards are clean and owned runtime removed. Fresh Ruff/format/mypy409 pass, one migration head f9c83e902026. Old FE786/72 source remains exact; this carries only its local FE unit/build gates and is not browser/server integration. Interface4b still external proposal. Individual metadata/context/deletion, Today and dated old findings remain open, as does native integrated acceptance. Main/production/current live search quality are unaccepted.

## Applications interface — local qualification

Plan now mounts saved native applications, including manual context without research. Existing G3 commands handle selected-result creation, dates/notes, planning, applicant submission/withdrawal declarations and exact historical corrections; source/read limitations stay visible. Original request recovery supports both closed V1 and manual V2 formats. Controller entry is bound to the rendered case and synchronous getter; old gestures cannot address a new case before rerender. Attempted forms and source/import previews keep original body/CAS and direct retries to recovery. Full FE4b3: **804 tests /75 files pass**, typecheck/lint(original9warnings)/build pass; backend native5 exact638 carry in both phases. These FE tests use a mocked API seam and separately Node-signed synthetic fixtures. They are not browser/API/DB integration or production proof. Individual metadata/context/deletion, Today and old findings plus real isolated journey remain unfinished.

## Personal edit/context/removal contract checkpoint (WIP)

A closed compatible V2 companion adds document metadata editing, explicit application context changes and own personal-record removal with history snapshots. Prior V1/manual V2 receipt/state formats remain readable with unchanged hashes. Context changes mark earlier bindings/reports for review. Declared submission/withdrawal targets cannot silently move; deletion of an application refuses linked documents. Removing the last record keeps an explicit own aggregate head. Focused native controls:22 pass across existing SQLite/PG fixtures; first18pass/4fail surfaced two actual domain defects (Today context reason and invalid self-dependency classification), repaired with assertions retained. Fresh static410 pass; current formatting is AST-identical to the diagnosed code. **Full backend and new UI integration pending**, no acceptance or release claimed.

## Personal edits/context/removal — server qualification

Full native8: **5807 tests pass in each default DB phase**, zero failures/errors/skips; coverage **94.20236% / 94.19771%**. Exact640 consumed-source maps and cleanup/guards verified against current primary/lab. Static Ruff/format/mypy410 and one migration head a0 pass. The two focused defects (Today context review omission and self-dependency misclassified as saved-data failure) are fixed; first failure remains checkpoint10. Server metadata/context/delete is locally verified. UI4d, real browser persistence and Today remain unaccepted.

## Complete personal forms — local qualification

Documents support own label/responsible/link/dependencies/date/notes edits and explicit self-reports, exact source binding/import, personal-record removal/history. Applications support manual/exact selected targets, context edits, declaration/correction/history and explicit removal with linked-document guard. Original-intent recovery is shared. **824 frontend tests /77 files, typecheck/lint(9 original warnings)/build pass**; exact640 backend map carries both5807 full native results. These controls use mocked transport and independent synthetic hashes; native browser/API/DB integration remains **NOT_RUN**. Checkpoint13 retains first failures and exact repairs. Today/date/Billing/profile/source-age and integrated journey still require work.

## Date and Billing findings — local qualification

Date-only values retain their calendar day; offset-bearing Instant display is separate. Known-zone date ordering no longer uses current UTC day, and current deadline badges no longer use persisted deadline_passed. Unknown zone/closing time remains explicit. Billing binds every read/quota/payment callback to current case generation, hides former entitlements and makes errors unknown. **835 frontend tests /79 files, typecheck/lint(9 original warnings)/build pass**, Old native8 full5807 is historical on changed format.ts;639 other consumed files are exact and fresh24 native changed-file consumer tests pass. No new full gate/coverage claim. Rejected and heap-exhausted first attempts are retained; repaired getter-stability and constructor fixture need no resource/test waivers. Native Today/exact navigation, profile/source-age and real browser/API persistence remain unfinished.

## Native Today and exact transitions — local qualification

Home reads the existing server Today projection; it does not calculate a second personal plan. Documents/applications/dependencies/dates are visible without a course or research success; selected-plan study tasks are separate. Read failures retain explicitly last-confirmed own data. Exact case/record/result/lesson/version/attempt references open existing own editors or show unavailable; names are not lookup keys and cases do not switch automatically. **848 frontend tests /82 files, typecheck/lint(9 original warnings)/build pass**; current consumer640 map unchanged since fresh24 contract controls, full5807 remains historically scoped on formatter. Native browser/API/DB journey and profile/source-age remain unaccepted.

## Actual research inputs and read-time freshness — WIP

Eight backend paths implement a closed existing-snapshot input observation namespace, actual fenced runner section hashes, permanent mixed provenance, unknown legacy/corrupt data and detached current age/status projection. Original stored result/claim/binding/receipt/evaluation/order remains unchanged. **55 focused controls pass with explicit native SQLite/PG fixtures; static415 passes**. Full current backend/coverage, new frontend read warning and real browser journey remain **NOT_RUN**; this is WIP. Checkpoint16 preserves all first failures and repairs.

## Actual research inputs and read freshness — native qualification

Fresh full native11: **5826PASS in each default DB phase**, zero failures/errors/skips; coverage **94.18551% / 94.1809%**. All645 consumed files match primary/lab/before/after. Static415 and cleanup/guards qualified. Metadata is read context, not a new admissions assessment. FE common notice and browser acceptance remain unimplemented/unverified; retained-target personal editing and projected claim status filter/count/paging are explicit pending findings.

## Common research read notice — frontend qualification

Exact8 frontend source files, **853 tests pass**, type/lint/build pass; source frozen. Changed named sections, permanent mixed input, legacy unknown and original assessment/source-age limits displayed through existing owned GET run. Saved profile/case generation fences reject late responses. Fresh backend whole gate is pending because frontend/types.ts is a native consumer; real Demo/Auth journey remains NOT_RUN.

## Retained application target and projected claim filters — focused qualification

Static415 passes; **69 focused checks pass** with actual SQLite/private PostgreSQL fixtures, no full coverage claim. Exact saved target remains personally editable after lost result/selection/award access; changed target still rejected. Current age status/count/paging use identical inclusive windows and authoritative row metadata without DML. Full current backend and basic native7 Demo/Auth journey are pending.
