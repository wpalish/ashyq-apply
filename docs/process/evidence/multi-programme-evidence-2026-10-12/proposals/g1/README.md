# G1 multi-programme preparation graph — external code proposal

**2026-10-12 · NOT_APPLIED · NOT_IMPORTED · NOT_RUN**

Prepared only by source reading against clean frozen source HEAD `9d3315e8cf2dcca93e01de8aa1fd6c7abbbbe557` in `work/unimatch-calendar-materials`. This directory is outside that checkout. No source/Git/HANDOFF edits, app imports, tests, migrations, runners, collectors, providers or model calls were performed. Closed pilots, frozen labels/held-out and all existing provider/model STOPs stay closed.

## Proposed files

| File under `files/` | Intended role after root accepts and applies it |
|---|---|
| `backend/app/schemas/preparation_graph.py` | Separate strict versioned request/response DTOs. Existing Claim, RequirementCheck, PreparationPlan and calendar wire shapes remain the source contracts. |
| `backend/app/domain/preparation_graph.py` | Pure projection of server-loaded owned evidence. Reuses native `project_checks`, `_referenced_claims`, `_compatible_with_label`, `_claim_state`, `combine_states` and `NOTICE`. |
| `backend/tests/test_preparation_graph.py` | Synthetic pure test source. It has not been collected, imported or executed. |
| `API_LOADER_WIRING_PLAN.md` | Separate future native route/auth/freshness loader and native test plan. No loader or endpoint code is applied here. |

There is **no `build_plan` helper** in the read source. The existing public preparation seam is [`project_checks`](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/domain/preparation.py:227), returning the checks used by [`PreparationPlan`](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials/backend/app/schemas/preparation.py:215). G1 uses that seam rather than claiming an absent helper. Private native pure helpers are reused explicitly to keep binding/state rules identical; promotion to public helpers would be a separate root-owned source decision, not a requirement of this proposal.

## Narrow G1 behavior

1. An explicit ordered selection of 1–20 exact IDs is validated as a whole. Duplicate/trimmed IDs are rejected. Missing and foreign IDs share `result_not_found`; owned rejected/undecided selections return `result_not_selected`. Unrequested loaded rows do not become selected results. A dataclass envelope itself does not establish database authorization.
2. `requested_result_ids` records client intent; `selected_result_ids` records the complete server-validated owned approved/maybe selection. They have the same order only after validation. No silent trimming or automatic latest-run replacement is allowed.
3. Each programme keeps its own decision, evidence state, projection state, notice, original checks and uncertainty. Mixed current/stale/unknown/locked/conflicted facts cannot become an all-current aggregate. In a partial source slice, individual known facts can remain current while the programme is unknown/partial.
4. Original `RequirementCheck` values, status, scope display string and references are copied intact. URL references are distinguished from `resolved_claim_ids`, which are exact stored IDs. ClaimOut proof retains raw value/quote/source/status/scope; exact scope verdict/gaps/contradictions are shown separately. No new eligibility evaluation is run.
5. Known exam families get observation groups only. `grouping=family_only`, `identity_state=unknown`, `edition=null` and explicit missing edition/variant/retake/route dimensions are fixed G1 facts. Unclassified atoms remain visible and are **not** grouped into a pretend shared exam. A dict key is recognized as an award exam family only for the existing one-key `{ielts|sat|toefl: raw_value}` adapter shape; arbitrary dictionaries and labels do not establish an exam identity.
6. No synthesized maxima, numeric schedule targets, baseline values, component splitting, dates, shared workload, selected branch, all_of/any_of operator or accepted waiver exists in this DTO. The plan's later `6.5/7.0 → maximum 7.0` example belongs after typed route/test identity proof. Root explicitly agreed this narrower G1 boundary.
7. Co-published alternatives and waiver conditions remain `alternatives_unresolved` / `waiver_check`, with context proofs. When both are present, they have separate unresolved groups; native waiver-first atom policy stays unchanged and cannot hide the co-publication route gap. A quoted “or” alone is not converted to a validated relation operator. Scholarship atoms retain their own award ID and subject, with unique subject binding; duplicate award names cannot establish a unique award. Raw `Scholarship.min_test_scores` without stored checks do not manufacture new RequirementChecks.
8. `lesson_id_hints` are existing preparation hints, not versioned tasks, score coverage or saved allocations. Unknown/stale/conflicted atoms never acquire hints. Missing Writing/Speaking/Listening requirements or content are not filled by an overall/reading hint.
9. Documents copy existing checklist items and uncertainties without collection. A unique exact cross-location owner projection can be merged while retaining all original items and locations. Same-list repetitions, different owner/purpose/scope/prompt/specification or ambiguous duplicate occurrences are kept separate. Dependencies resolve only within the same result with established compatible scope and exactly one name candidate; missing/ambiguous/scope gaps/cycles remain visible.
10. Every document fulfillment remains `untracked`, every action `requires_review`. Even exact document refs do not claim that every copied format, deadline or conditional predicate has been normalized/confirmed: that projection is explicitly unfinished. Legacy URL-only document provenance is not upgraded. A linked prerequisite is not proof of completion or receipt; an external admission offer prerequisite is not fabricated as a checklist item. Existing lead times remain unclassified stored planning values, not guaranteed published processing times.
11. Locked programmes disclose the permitted selection ID/decision receipt and locked state only; no run ID, names, requested scope, checks, questions, document payload, exact proof IDs or source digests. The standalone programme DTO enforces consistent locked states and a fixed public reason/notice, so alternate producers cannot hide payload in custom text. The future loader must use the same owned-profile/research entitlement rules as v1. Preparation access must not unlock research evidence.
12. `source_manifest` covers every selected result and every displayed exact proof, including policy context. Source fingerprints describe the loaded evidence view, not an accepted plan, admission readiness, quality score or immutable DB snapshot guarantee.

## Identity boundary before persistence

G1 requirement IDs identify **occurrences in an ordered stored check snapshot**: result + purpose/award + requested scope + original check index + typed claim kinds + published predicate. They preserve duplicate checks and do not change from citation order or access-time edits alone. Changing source status/freshness changes the manifest fingerprint; changing the published predicate or reordering stored checks can change occurrence IDs. Document IDs likewise identify read-only stored occurrences and conservative owner projections.

These IDs are not a new durable ledger. G2 must explicitly version stable semantic identity/remapping before saving accepted plans; it must not silently reinterpret this occurrence identity as an ApplicationRecord or completed task ID. No persisted graph rows, revisions, migrations, export/delete side effects, progress backfill or common-capacity allocator are introduced by G1.

## Proposed meaningful tests (source only)

- Two current IELTS observations retain independent minima/check status/proof/scope while producing no shared numeric target.
- Existing single-result preparation semantics are preserved for ordinary admission checks; non-exam snapshots are retained separately.
- A current programme cannot upgrade stale, wrong-scope, unrecorded-scope, conflicted, partial, malformed or locked programme evidence.
- Missing/foreign/rejected/undecided/duplicate selections fail without a silently partial selected graph; loaded-row order does not change explicit order.
- Ambiguous shared legacy URL remains unknown; exact compatible ID plus URL binds only its own record.
- Waiver and co-published alternatives remain separately unresolved when simultaneous, including a stored quote containing “or”; AND/OR fields/operators are rejected by the schema.
- A standalone locked programme DTO rejects run IDs, questions, custom text/reasons and inconsistent states without relying on the producer's branch.
- SAT total/IELTS overall cannot create missing numeric section targets or schedule settings; generic English dicts do not establish SAT identity.
- Admission optional SAT and scholarship required SAT remain separate; missing/duplicate/mismatched award subjects and absent stored checks cannot borrow proof.
- Exact owner projection dedupe preserves same-list duplicates and distinct document purposes/owners/prompts; external, ambiguous, wrong/unknown-scope, cyclic and cross-programme dependencies stay unresolved/untracked.
- “Official” checklist completeness and a shared URL cannot confirm every document predicate; partial checklist questions remain visible.
- Input models stay unchanged; response round-trips strict wire DTOs; cross-programme dependency/scope injection is rejected; freshness/status changes are fingerprinted.

No test-pass count is claimed. Root should apply/review the chosen proposal only after closing the current frozen calendar receipt, then run actual native offline format/type/pure/API gates. Existing legacy tests remain required; the proposed tests do not replace them.

## Source binding

Read-only source SHA-256 values at `9d3315e8`:

| Source | SHA-256 |
|---|---|
| `backend/app/domain/preparation.py` | `07cf2c70355847b76affbe72564b80841bad9009af671056e6b38c2d098295b4` |
| `backend/app/domain/claim_scope.py` | `e29c2f751734396d2208a8c968588f8f561813017785cd1a58067a56d1f5753c` |
| `backend/app/schemas/preparation.py` | `b88e53c64fab532e1662ee970a11cea4057bf5a1dcd473f73cfb3b2860d30cdc` |
| `backend/app/schemas/result.py` | `f4eab02362d8bcdcec72bc1f16e2636f7abe7c0844b72b18bb4eac94f3927974` |
| `backend/app/schemas/claim.py` | `109d65d69da8d0d773618b8ff35487d4bea1bb37b8f60acb8895d1baaa9bf794` |
| `backend/app/api/routes_preparation.py` | `11c77dd288e5f00bb7159447833981de1aca446f0e47726a116aec405d1645f2` |
| `backend/tests/test_preparation_domain.py` | `45c54b4a2dacb4b71e4b400da09c39979fe9df81949110f3aed1366df59e20c2` |

All new code bytes are proposals outside the frozen checkout. Read-only source confirmation is not successful import, integration, native local verification, deployment, live recall, applicant outcome or readiness of the whole product.
