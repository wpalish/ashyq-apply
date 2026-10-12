# G3 EventRef addendum: independent read-only reconciliation

**2026-10-12 · DESIGN ONLY · NOT APPLIED / NOT RUN**

Reviewed `G3_EVENTREF_AND_RAW_AUTHORITY_ADDENDUM.md` SHA-256 `9292ca3db7edb0a7423a97a8760da579bebf1cc68534d4f7282b2a1a50e51e8e` and its sealed receipt `af55ba1e62ee4fca81e36998799dad3fc2913150f5a2b5797a090fbf7a2ad705`. Compared against the unchanged freeze proposal `f5acdae226110346798aca2ab8e51a40894e902adc5e2d4eb71b5c85740d839a` and the earlier independent review `8f498fc30d8eeea447e8bcf5fe849f01bf46095c125feab24b5b9ba2000b3df7`. No application, source, Git, helper, import, test or runtime was changed or run.

## Disposition

The addendum closes the two identified design ambiguities:

1. **No state/receipt hash cycle.** Exact `EventRefV1` has only `event_id`, `revision`, `kind`; extra fields are forbidden. A new head can be referenced by several records without embedding its receipt hash in the state. The specified acceptance order computes the complete state digest first, then the receipt digest. Current/head read checks the full exact head receipt and its self-hash separately. Older state refs get bounded own metadata checks; this is explicitly weaker than reading their entire receipt, with full validation deferred to history/event/export.
2. **Original URL authority is checked first.** Raw authority is isolated before parser normalization and rejects non-ASCII, credentials, percent escapes and malformed host/port forms. Unicode-host punycode conversion can no longer turn a rejected original authority into an allowed action href. Literal ASCII punycode remains only an unverified informational link. No DNS/fetch or global SourceLink behavior is added.

`EventAffectedRefsV1` also supplies the missing record-association control: exact applied-delta-derived ordered unique application IDs (≤20), document task IDs (≤400), and a selector-change boolean. A metadata-only older-ref check can require the referenced record to be in this finite header and the command kind to be allowed for the ref's role, rather than accepting any own event of the right general type. Full head/history/export reads compare the copied header with the typed receipt and derived applied delta. The 20/400 limits cover the maximum present bounded state; the separate 50-mapping import cap and source-target budgets remain distinct. The declared 1,662-reference/≤200-per-batch/≤9-batch ceiling is arithmetically consistent.

**Implementation precision:** `active_selector_changed` should mean an actual accepted selector mutation, including a future explicit transition to a null/legacy selection if the closed command union permits one. The text currently says “creates/replaces”; existing accepted G3 V2 permits an explicit versioned return to legacy. Treat this as a replacement and derive the boolean from the actual applied delta, as the addendum already requires. Do not set it just because a request mentions a selector. This does not reopen the hash-cycle finding.

No new blocking defect was found in the inspected finite addendum. This is closure of design wording only; no G3 schema, migration, API, frontend or native control has been qualified.
