# G1 native API loader wiring — proposal only

**NOT_APPLIED / NOT_RUN. No API loader code is included in the proposal.**

## Existing seam and transport

Current single-result endpoint is `GET /api/profiles/{profile_id}/preparation/plan?result_id=…`, `routes_preparation.py:660–788` at frozen `9d3315e8`. It uses `owned_profile`, owned ProgramResultRow→ResearchRun join, independent `has_full_access`, authoritative claim columns, one freshness timestamp, unresolved conflicts and exact applicant requested scope. It returns native PreparationPlan. No `build_plan` function exists in this source.

Proposed separate read route: `GET /api/profiles/{profile_id}/preparation/graph?result_id=a&result_id=b`, preserving query order. Convert the query list to `PreparationGraphRequest(selected_result_ids=...)`; do not accept posted result/claim/scope/graph data as authority. Final transport naming is for root to bind once with frontend. Existing scalar endpoint/response must remain unchanged.

## Loader steps, after stage 1 closes

1. Resolve `owned_profile(session, profile_id, principal)` before any result payload is loaded. Validate 1–20 exact nonduplicate IDs without silent trimming, sorting, truncation or latest-run substitution.
2. Load metadata for **all requested** results using the existing join to `ResearchRun.profile_id == profile_id`. Compare the exact set to the request: any absent/foreign ID → one generic 404 with no partial body; a rejected/undecided owned ID →422. Reconstruct explicit request order, not DB `IN` order. Check authoritative `user_decision` column, not payload copy.
3. Resolve the same research entitlement as v1. Locked projection can be built from permitted owned ID/decision metadata only. Do not load premium payload for convenience; preserve identical limits on displayed evidence. Paid preparation access or historic attempts cannot unlock research facts.
4. Factor a private server-side evidence loader used by v1 and new G1, without changing the legacy shape. For each result, preserve run/result linkage and authoritative column overrides (`ClaimRow.id/status/source_url/accessed_at`), official/specificity/scope payload validation, supersession/freshness, unresolved conflicts, profile-change staleness and validation failure handling. Derive requested scope from the same result identity/applicant fields; do not trust client or source display strings.
5. Capture one `utcnow` for all loaded slices and calculate every claim's freshness from it. Batch per-run claims/conflicts if useful, then partition with the exact existing `result_id == selected_result OR result_id IS NULL` rule. A global claim still needs its own exact scope for each selected programme. Do not attach claims of an unselected result or another case. Do not let DB row limits silently manufacture absence/completeness.
6. Parse stored RequirementChecks and scholarships without adding checks from raw summary score dictionaries. Validate each checklist `result_id`. Preserve existing partial/unavailable collection and unresolved questions. For malformed source/check/profile/checklist records, expose an unavailable/partial per-programme slice with known failure state; an unreadable unresolved conflict must stay conflicted. Catch duplicate authoritative claim/award identity and unserializable historical values before pure projection instead of returning an optimistic slice or an unhandled 500. Do not fabricate default scope/type/component/operator values.
7. Construct typed `ProgrammeEvidence` values solely from the validated server rows, and call `build_preparation_graph`. Missing/foreign selection is all-or-nothing; malformed owned evidence can remain a visible unavailable slice. No premium metadata or evidence digest may leak through the locked path. For a malformed unavailable slice, retain only validated data in its manifest rather than re-hashing an unparseable payload.
8. Treat this as a current read view. Use the route's normal read transaction, one timestamp and deterministic partitioning; do not describe the hash as an immutable/accepted multi-row DB snapshot. If explicit repeatable-read semantics are added later, test them separately. No writes, locks held over I/O, worker jobs, collections, requests to official sites, models, retry providers or rechecks are introduced by this GET.
9. No route references StudyScheduleRow, learning sidecar, attempt creation/update, ApplicationRecord, new graph storage or exports/deletes. Existing saved calendars and receipts must remain byte/behavior compatible. G2 is an independent later acceptance/CAS/storage stage.

## Required native tests before claiming endpoint readiness

Pure proposal tests are source only and cannot prove these API behaviors:

- Principal/case ownership; generic foreign/missing 404; complete ordered approved/maybe selection; rejected/undecided 422 and nonduplicate query validation.
- Locked/expired research semantics, including no premium body/URL/scope/digest leak and no entitlement gained from preparation subscription.
- Claim authoritative column status overrides stale payload, exact global/per-result partitions, one freshness timestamp, profile update staleness and unreadable unresolved conflict as conflicted.
- Malformed checks/profile/checklist/claim records represented conservatively per owned programme; duplicates or mismatched checklist identity do not crash or silently create an empty “no requirements” interpretation.
- Admission/scholarship purpose/award binding, ambiguous legacy URLs, original check statuses and existing source scope contracts preserved.
- GET leaves existing profile/results/claims/checklists/legacy schedule/learning sidecar/attempts/export/delete state unchanged. No request invokes network/providers/model/worker/collection seams.
- Run existing `test_preparation_domain.py`, `test_preparation_api.py`, `test_document_scope.py`, `test_document_dependencies.py`, calendar/learning/export/delete regressions unchanged, then actual required root local gates. No frozen labels, held-out rescoring, closed pilots or collector resumes are authorized by this plan.

## Frontend handoff

Use both selection ID arrays as an exact response receipt, plus active case and request-intent generation, to reject delayed results for another case/selection. Preserve every programme card/decision/evidence/projection status separately. Show original check status as a stored snapshot, current evidence as its source state, and unresolved routes/types/dependencies separately. `lesson_id_hints` are bare practice hints; they are not LearningTaskRefs. Family groups should be labeled as observations, not as a shared accepted study plan. No saved-plan/workload/action-completed UI is backed by G1.
