# G2 allocator sealed proposal: independent final reconciliation

**2026-10-12 · READ-ONLY / SEALED PROPOSAL REVIEW · NOT_APPLIED / NOT_IMPORTED / NOT_RUN.** This reviews only the three proposed files and reconciles `G2_ALLOCATOR_DRAFT_REVIEW.md` (SHA-256 `e40a01d0509bf42327fb71c645e43f4ee1fc401008ae3f01eefb95b40fdcfcce`). No application source, Git, HANDOFF, helper, import, test or runtime was changed or executed.

| Sealed artifact | SHA-256 verified here |
| --- | --- |
| `SEAL.json` | `fa09515208a383a7bd0471c7fbc76495bd0a2c2187af867a95ad945f05740b8d` |
| `files/backend/app/schemas/shared_route.py` | `c9fde4116e9925cd71988c45a800b1d3e5e4ddff4eadfb30b69326d9444c8cdc` |
| `files/backend/app/domain/shared_route_allocator.py` | `fc151bb887556febcccafe706353e952b5d962c2f158b91eec21e667aadc8f76` |
| `files/backend/tests/test_shared_route_allocator.py` | `e2edee3f7d81dec126789e6100ce75d783be4f4ae9c1c37f6e70a86e90cbdbb7` |

`SEAL.json` reports only syntax AST parsing; its 51 test functions / 142 statically expanded cases were **not collected or run**. The three destination application paths were recorded absent at seal. These are proposal bytes, not integrated source or a green gate.

## Draft finding closure

| Initial finding | Final static disposition |
| --- | --- |
| **F1: whitespace around selected programme IDs passed the G2 DTO.** | **Closed in proposed schema.** `SharedRouteInputV1._route` now rejects any `selected_result_ids` value unequal to its stripped form, alongside duplicate rejection, without changing order (`shared_route.py:261–266`). The additive test supplies leading/trailing/tab-newline examples and confirms reversed clean order remains intact (`test_shared_route_allocator.py:437–442`). G1's whole-selection ownership/decision validation is still a later API obligation; this schema guard does not replace it. |
| **F2: output DTO accepted shape-valid but unbound action/occurrence IDs.** | **Closed for local exact identities in proposed schema.** `reference_action_id` and `reference_occurrence_id` derive the hashes from exam+exact ref and action+local date+ordinal zero (`shared_route.py:144–160`). `DatedSlot` rejects altered action/occurrence IDs and non-20-minute current lessons (`:315–336`); `UnallocatedAction` rejects altered action IDs and non-20-minute current lessons (`:364–377`). Domain code calls the same derivation at action/slot creation (`shared_route_allocator.py:44–46, 263–271`). Literal SHA anchors, version/UUID distinctness, forged IDs, altered lesson minutes and independent track/exam association are covered by proposed controls (`test_shared_route_allocator.py:576–606, 663–709`). The **complete persisted receipt/request digest**, selected own-review set and replay integrity remain a separate future API/persistence gate, as the seal itself states. |

## Narrow check of new guards and tests

- The strict local identity binding does not make programme IDs part of an action ID; stable exact lesson/review identity remains independent of programme order and planned date. The tests pin literal SHA outputs and compare unchanged action IDs across altered programme/date input (`test_shared_route_allocator.py:576–596`), rather than deriving every expected ID from the function under test.
- The 20-minute checks apply to **current lesson planning allocation** in both scheduled and unallocated output. Own attempt-review minutes remain applicant-entered. This matches `LearningUnit.planned_minutes=20` as capacity allocation, not a claim about lesson duration or improvement. The proposed test varies 1, 19, 21 and 180 minutes in both output locations (`:702–709`).
- Exact `SchedulableRef` output is limited to lesson and own attempt review (`shared_route.py:137–141`); the additive test rejects assessment/external-resource refs and official proof fields (`test_shared_route_allocator.py:739–748`). Additional controls cover source-order conservation, shared day/week caps, partial/nonfinite targets including constructed-instance revalidation, no caller aliasing, exact ordered selection, retake expiry and `date.max` (`:121–170, 637–660` plus the corresponding scenario tests). These are meaningful **proposed assertions**, not observed passes.

**Conclusion:** F1 and the local-ID portion of F2 are resolved in the sealed three-file proposal. No new defect in the requested identity/whitespace/20-minute guard scope was found by static reading. Root still needs its own source binding and permitted isolated test gate before claiming integration; ownership, shared CAS, complete receipt persistence/replay, export/delete, frontend and production are outside this three-file proposal.
