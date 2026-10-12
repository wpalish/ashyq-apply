# G3 initial pure: combined finite repair review

2026-10-12 · **SOURCE_ONLY / SIX_FINDINGS_CLOSED_SOURCE / READY_FOR_ROOT_APPLICATION_AND_GATES / NOT_APPLIED / NOT_IMPORTED / NOT_RUN**

## Scope and seals

Independent review of only source1→repair1's four accepted fixes and repair1→repair2's two remaining accepted fixes, their targeted controls and preservation of predecessor source. No additional broad audit or new prerequisite was introduced.

All declared member hashes were verified **before** reading each repair's source/diffs:

| Immutable packet | Seal SHA-256 | Declared members |
| --- | --- | --- |
| proposals/g3-initial-pure-source1 | 41a34f0226609b0710a83135b815f0b35ef873096296b2bfd50478731544b1e1 | 9; verified in original review |
| proposals/g3-initial-pure-source-repair1 | f19f2c775ed89ad4f8d9beee5d50c6717f9ead2c912d8f702dbfe41422fe187f | 11; all matched |
| proposals/g3-initial-pure-source-repair2 | f77aa5e618144160a3e36f743030258987300075b1a7186b1f91c78d75024d10 | 11; all matched |

Stage root: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12`.

Original independent review/seal remains unchanged: report `32c16500421ea9e551ab687bcc89d3509d8f9dfcebf98765cabe578cd90d4b10`, seal `526de37b1b1eb3612269ff67749de6b5b49aefc1aa160c2640129c10b108c00f`. Its independent42-group oracle SHA `dc6fdfcb211d0a8837b1214e1a8675fbc29bc7a8e67b81df171288f25e222f05`, all original8 accepted design pins, ninth root disposition and deferred D01–D06 boundaries are preserved.

Read/hash-matched finite authority: repair1 grant `3d61dedea4c2aa31204eade4fc928b74854dc1bfca06a6f8d2e3481dc9a22624`; F5/F6 addendum `91dc795db00722a0b0fedb88ce2832731feac82b154f5f26102bea9ddb450a9b`. Parent explicitly directed the separately sealed root-authored repair2. No model/API/migration/UI/helper/runtime source grant is inferred.

## Six exact dispositions

Coordinates refer to final repair2 files, except test ranges labeled repair1 (unchanged in repair2). Closed here is source-contract closure, **not PASS**.

| Finding | Final source/control disposition |
| --- | --- |
| F1 uppercase native UUID | **CLOSED_SOURCE.** Schema:85–92 accepts native A–F spelling and canonicalizes UUID. Repair1 tests:132–153 independently assemble canonical request hash, compare upper/lower intent/transitions and replay original receipts. The old erroneous uppercase negative is replaced by a malformed non-hyphenated negative. |
| F2 planning correction can be corrected | **CLOSED_SOURCE.** Domain:186–197 fully revalidates the supplied saved receipt; :283–289 associates its exact affected/applied application without requiring a nested submission body. Repair1 tests:260–284 cover correction of planning correction, an older accepted prior under new CAS and unchanged predecessor export/receipts. |
| F3 valid own wrong-app relationship422 | **CLOSED_SOURCE.** Domain:284–289 separates generic missing/foreign/exact-ref404 from valid own wrong-application422. Repair1 tests:287–319 distinguish those cases and malformed/selfhash/forged-nonfinite saved receipt503 with fixed safe detail. Physical owner lookup remains deferred. |
| F4 embedded decoded sensitive key=value | **CLOSED_SOURCE.** Schema:1145–1152 matches embedded key=value without delimiter exception. Repair1 token controls preserve exact literal proof identity, exclude it from semantics/ACK/href, reject tampered actionable DTO, and retain the single-decoding/unverified-destination boundary. No network or global SourceLink policy change. |
| F5 personal-create receipt binding closure | **CLOSED_SOURCE.** Schema:1089–1092 now requires null binding/ref and applicant_entered origin for CreatePersonalTask. Tests:751–768 use a real prior reviewed binding and valid new personal receipt, show the copied bound DocumentTask is otherwise structurally valid, independently recompute the forged outer receipt selfhash and require saved_unreadable from replay. Reviewed BindSourceTask and unmodified personal replay positives remain. This is semantic consistency, not signed authenticity or coherent trustedDB-rewrite protection. |
| F6 combined stable personal Today order | **CLOSED_SOURCE.** Domain:714–725 sorts all personal cards by target.id, then kind/card.id; overdue retains date first with those ties. Tests:772–780 cover inverse app-a/doc-z AND app-z/doc-a across undated/overdue/today/future partitions (2×4 literal cases). Tests:783–789 separately preserve equal-date native study order and study-before-personal, with one unchanged minute total. |

No remaining blocker was confirmed in the **accepted six-finding repair scope**. This does not claim exhaustive re-audit of arbitrary inputs or future integrations.

## Diff and control preservation

Each repair's `original/` copy is byte-identical to its predecessor's postimage (six cmp exits0 across two transitions).

Repair1 schema/domain supplied diffs exactly match native text diffs. Its tests diff differs only in valid blank-line hunk context; independent **in-memory text-only reconstruction**, checking context/deletion text and old/new hunk counts, yielded the exact 748-line test postimage with no errors. No patch/application was executed.

For repair2, all three supplied diffs match native original-to-postimage diff text exactly (three cmp exits0). Only four schema guard lines, the bounded personal-order helper/sort and overdue tie-break, and three appended test functions change. The original repair1 test file is an unchanged prefix; no predecessor control/body is removed or rewritten by repair2.

Literal definition-name reading (not import/collection) shows:

- source1:42 test definitions;
- repair1:47 test definitions, all original42 retained;
- repair2:50 test definitions, all predecessor47 retained;
- repair1's69 top-level functions are47 tests+22 helpers.

Repair2's seal field `unchanged_predecessor_test_functions:69` is a **metadata wording error**:69 refers to all top-level functions, not tests. Its README correctly states47 predecessor tests. Treat that field as69 total /47 tests /22 helpers; a separate metadata clarification can preserve the sealed original. This does not alter source or create a runtime count.

The original42 oracle groups remain source-bound. P05/P20/P30/P32 now have the requested finite repairs/controls; P03/P13/P14's personal-creation receipt concern and P42's personal ordering concern are closed by repair2. Prior partial qualifications and future D01–D06 gates remain. These source counts and prior G2 gates provide no G3 execution result.

## Exact final source

| Repair2 postimage | SHA-256 |
| --- | --- |
| files/backend/app/schemas/admissions_actions.py | 870738ed180f7164e8b15f4bd8baf47c855a622748cef2728f91774e26a9b6b7 |
| files/backend/app/domain/admissions_actions.py | e15f92ea37b28bd222ed239aaa21edf3294f289797e9479c7db25031e182b8ad |
| files/backend/tests/test_admissions_actions.py | ee268deb6228e8c3253add12442572b9faa1c91ca5d31f9b6eaef1466feac2d5 |

## Disposition

**Ready for root to decide application of these exact three pure files and bind/run its authorized local gates.** This peer review does not apply or execute them. Only the new external reports/seals were written; app/Git/HANDOFF/helper/runtime bytes remain untouched by this reviewer. Existing sealed packets/reviews remain immutable.

NOT_IMPORTED / NOT_COLLECTED / NOT_RUN. No Python/AST import or test execution, DB, network, browser, provider, stopped/live/held-out work occurred. Future native API ownership/CAS/delete/rollback, actual source authorization/query bounds/export/history, browser recovery/typed navigation, migration and production remain separate gates. No official-submission verification, admissions readiness, live search quality, deployment or product completion claim.

