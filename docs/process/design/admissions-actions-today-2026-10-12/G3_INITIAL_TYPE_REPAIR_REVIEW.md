# G3 initial type18: independent finite source review

2026-10-12 14:51 UTC · SOURCE-ONLY · APPLICATION_NOT_IMPORTED / TESTS_NOT_COLLECTED / TESTS_NOT_RUN

## Disposition

**No blocker found in the complete final context2 diff. Qualified for the root's authorized native static3 and focused initial G3 gate.** No primary/lab application, Git, HANDOFF, runner/helper or configuration was changed by this reviewer. Source parsing used Python3.12.13 stdlib AST only, `-I -B -S`, with OS network and file-write denial; no application module was imported or executed.

## Exact sealed packets

| Packet | SHA-256 of SEALED_PROPOSAL.json | Members independently verified |
| --- | --- | --- |
| `proposals/g3-initial-type-repair1` | `851a1dbce1b335d97f6e90e915a040bfcfc74d7673f265215ac4e8b0f5250656` | 19 hashes and sizes, including retained external Ruff cache members |
| `proposals/g3-initial-type-context2` | `5472f83b6ad4a59f3a142e6a93eed51fab8276e36af9048d91855abade9551cc` | 15 hashes and sizes, including retained external Ruff cache members |

Every member was verified before source review. The three context2 `combined-diffs/` were reconstructed as text against type1's original primary bytes and reproduced each full final file exactly (schema17/domain10/tests36 hunks). The preserved first formatter snapshot is not rewritten or substituted for the native100 final.

## Contract review

| Final source location | Change and source qualification |
| --- | --- |
| Schema:54 | Added `isinstance(value,date)` is implied by the retained exact `type(value) in {date,datetime}` guard. Date subclasses/unknown objects remain rejected; finite checks stay before JSON normalization. |
| Schema:118 | Wrong runtime types are rejected before offset access; cached offset is still required to be non-null and zero. The same accepted UTC conversion and rejection remain. |
| Schema:219 | Independent RawDocumentChecklist avoids invariant list subclass override. All **13 native data fields** have exact native annotation/default ASTs, with only six DocumentItem lists changed to RawDocumentItem lists. There are14 class assignments only if model_config is counted. result_id/university/program, six lists, ordered_steps/unresolved/generated_at/completeness remain. |
| Schema:219 | Prior raw checklist configuration is AST-identical: extra-forbid, strict, allow_inf_nan=False, str_strip_whitespace=False, revalidate_instances=always. RawDocumentItem's complete class AST is unchanged, retaining native fields/defaults and inherited unrecorded-scope serializer. Native DocumentChecklist has no validator/serializer method to lose in this change. |
| CaseActionsStateV1 | Local `own_application` separates the optional lookup from the earlier loop variable. Own-current-app lookup, missing rejection and result/award/purpose checks remain. |
| Schema:1020 | Added LearningTaskRef annotation only. TypeAdapter strict validation, exact lesson/review ID checks and raw-versus-validated finite equality are unchanged. |
| Schema:1310 | Explicit ApplicationRecordV1\|DocumentTaskV1 list retains the same applications-then-tasks iteration and exact profile/latest-event guard. No weaker Base type or ignored attribute check is substituted. |
| Domain:1211 | Dependency stack annotation accepts variable-length tuple trails. Push/pop order, cycle/missing readiness checks, reasons and deduplication are unchanged. |
| Domain personal_card | Optional result_id annotation only; the same bound-result or own-app fallback with None remains. No invented target or source read is introduced. |
| Domain:1317 | Literal branches map g2/legacy_v2/legacy_v1 to the same exact value and reject every other origin with existing saved_unreadable. Study slot order, expiry/own-review access and one selected-plan workload remain unchanged. |
| Tests:1650, 1772 | Only helpers change behavior: head constructs the same UUID value explicitly; study passes the same date/reference/minutes/availability/completion payload through strict native JSON-wire validation. No fixture identity, date, ref or assertion was removed. |

No type ignore, Any widening, disabled check, changed error code/limit, raw checklist field omission, relaxed validator or altered test selector was found. Remaining combined-diff edits are formatting/import annotation support.

## Independent AST preservation

All ordered50 top-level test definitions, decorators, parameters, bodies and assertions are exact AST matches to the original primary. This is **source preservation**, not50 test passes. The only changed test helper definitions are `head` and `study`.

The complete changed-definition set is exactly:

- Schema: `finite_wire`, `_utc`, `RawDocumentChecklist`, `CaseActionsStateV1`, `_learning_ref`, `validate_receipt_delta`.
- Domain: `project_today`.
- Tests: `head`, `study`.

The schema's other validators, aliases, receipts, commands and earlier finite fixes remain intact at the AST level. The independent seal records all50 unchanged test AST hashes.

## Source pins

| Relative path | Original primary preimage | Final context2 |
| --- | --- | --- |
| `backend/app/schemas/admissions_actions.py` | `9f516e35f9b5486960c7dcdef720b2794d58f5bc18c8cb9d3f15ab6a158d477d` | `61ca24cc599bd215ef43a05a6d3a9f8e9ecaad33bde419bffa9fbc837b8ab43f` |
| `backend/app/domain/admissions_actions.py` | `e3d0c99b72a67b82c694596c7904bab0ae42122aafc6138abb668159f9c0c64a` | `7c8f29ca50ac71ab33cae402b879e7bcacc4396508e0bb811bcacd1937a77ec0` |
| `backend/tests/test_admissions_actions.py` | `0c6ff0e8c4c6179e801c98c6923a21bf1ab31357dd26f37a7137b2be1e2c9cae` | `43603f435a86b89808d7fc5d9811f215f5e17d1d1cc9e0e533bfca72459de724` |

Native result.py pin: `f4eab02362d8bcdcec72bc1f16e2636f7abe7c0844b72b18bb4eac94f3927974`.

Read terminal prior native static2 mypy.log pin: `4b780efab1364143f68c7a58b0000b933236929cb60bbe63b690cab31ec01eee`; it reports18 errors in exactly the three new files. No log, cache or gate was changed or rerun here. The next root gates must establish native lint/format/mypy and actual Pydantic/fixture behavior on these final bytes; this source review adds no broader prerequisite and makes no runtime/release/product acceptance claim.

