# Unimatch core implementation progress

Root solo; branch `task/admissions-actions-today`. Current release status: **core incomplete / production unchanged / live search quality not measured**. IELTS/SAT learning remains optional.

| Stage | Current state | Exact local evidence / remaining work |
|---|---|---|
|0 baseline/reuse|Reviewed and reconciled|892fc5e5; G3 selected over separate ecd10015 product-completion. No merge.|
|1 early programme observation|Locally verified|e9677b2e/64a8ea3e; full5765 each native default DB phase,94.33/94.32%; API ownership/export/delete and timeout/cancel/lease controls; frontend732 before commands. Quality still separate.|
|2a Store/journal safeguards|Locally verified|746 frontend tests/build; synchronous G3 case generation, captured lateDELETE, exact selected ACK cleanup/cap64/corrupt index; backend exact full3 carry.|
|2b forms transport/recovery|Not implemented|Existing native journal/receipts must drive forms and visible recovery; no auto retry/body/CAS refresh.|
|3 documents|Incomplete|G3 API exists; full metadata forms/bindings/history/reload and explicit legacy-mark migration remain.|
|4 applications|Incomplete|Existing G3 selected-result events/history; manual application needs compatible versioned extension because frozen v1 requires result_id.|
|5 Today/dates|Incomplete|Server G3 projection exists; exact navigation/date-only/unknown timezone and optional learning split remain.|
|6 integrated journey|Not run on these changes|Demo/Auth/second login/export/delete/errors/320–1440 layout still required.|
|7 live search quality|Blocked by existing STOPs|Separate live/heldout authorization required; no inferred score from local tests.|
|8 release|Not done|Main/deployment/production/containers untouched; operator and quality acceptance gates remain.|

Current evidence indexes: `evidence/core-completion-2026-10-13/checkpoint1`, `checkpoint2`, `checkpoint3`. Original failed attempts are preserved; later qualification names actual accepted source. New request generation is distinct from the existing UI feedback epoch, whose exact deletion behavior remains covered by unchanged original tests. Clearing local ACKs never deletes server actions/history. A client ACK is not an official university submission or document verification.

Old findings still requiring implementation/verification: LocalDate display, timezone deadline comparison, stable document binding forms, legacy Documents JSON-null handling, Billing case-bound access on failure, unavailable-list wording, profile-version stale-result notice and read-time source age. Backend tests and source review do not accept this entire product.
