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
