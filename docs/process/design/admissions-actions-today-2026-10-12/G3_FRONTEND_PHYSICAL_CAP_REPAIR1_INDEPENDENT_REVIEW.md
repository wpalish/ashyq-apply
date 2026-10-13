# G3 physical journal cap repair1: independent finite source review

Reviewer: /root/open_search_solutions.
Completed source inspection: 2026-10-13 06:46:17 UTC.
Disposition: **NO SOURCE-ONLY BLOCKER FOUND** within the two-path grant.
NOT_APPLIED_BY_REVIEWER / NOT_IMPORTED / NOT_AST / NOT_RUN / NOT_ACCEPTED.

## Authority and exact pins

- Grant G3_FRONTEND_PHYSICAL_CAP_REPAIR1_GRANT.json: cbcedbc352900728e7b5310fe4df38110eeef45731128553f6e9b4aea97761ef.
- Packet proposals/g3-frontend-physical-cap-repair1/SEAL.json: c8b6876371cba70956bac3c7e6792c9772ea68d15f8ab99dc094d3e223498a7d.
- Independently verified all 10 declared member hashes and byte counts. The copied grant matches the actual grant.
- Both actual current primary files matched their exact grant preimages at inspection.

| Sole proposed path | Current preimage SHA256 / bytes | External postimage SHA256 / bytes |
|---|---|---|
| frontend/src/lib/admissionsActionsRecovery.ts | d9984a8787d63b83a36f8f7d517a243a1e3759f31ae0fa67d3eadec6a6fd97cf / 47133 | 29768832e7f0d972f55606c6310aeb915f90663e9527f825feda95bbe2eb881e / 47243 |
| frontend/src/lib/admissionsActionsRecovery.test.ts | 259112fc1fa7f63118440333a8464fa27d1201b0cf5ef7ad6b9d71542724efc3 / 60735 | 5724262f6ccaf1f567ac0bda067d308a55c35280a3ccd303c17fe90c3831c477 / 63230 |

The complete manifest, README, preservation metadata, both full diffs, complete 653-line proposed helper, full appended test and relevant current test hooks/context were read. No source execution or AST was used.

## Production change and finite counterexamples

In proposed helper lines 174-187, ownFamilyKeys retains the active-owner/fence checks on both sides of physical storage enumeration. The existing whole-family bound of 64+3 at 180 and both original key-validity checks at 181-183 are unchanged. Only the former filtered/sorted return becomes a filtered intent-key list, a count greater than the unchanged limit 64 refusal, and the same sorted return at 184-186.

- A valid own family with 64 intent keys and fence/index metadata remains under both the coarse and actual-intent limits; the returned IDs/order are identical.
- 65 valid own intent-key names with only an alive fence and no index total 66 own keys, so the old coarse threshold could pass. The new actual count returns limit before scan reads/parses those entry bodies. This covers the retained malformed65 regression at test lines 431-435.
- Invalid key names at an otherwise under-coarse-bound family still produce the original invalid result before the new intent count. The coarse greater-than67 precedence is preserved as well.
- Other owners/cases and unrelated keys remain excluded by the exact own-family filter. No family threshold, validator, parser, ACK, index, retention, deletion or transport change is introduced.
- scan performs ownFamilyKeys before entry read/parse at 283-291 and repeats the physical-key scan at 304-305. The new guard adds no I/O or mutation.
- Existing fence and index validation precedence is retained; inspectCase may validate its index before entering scan. The before-parse statement here refers to entry-body parsing, not a new global override of existing authority/index errors.
- The separate deletionFamilyKeys implementation at 523-541 is byte unchanged. The new count does not add a cleanup or retention policy.

Independently replacing the unique function-scoped three-line postimage span with the prior return reconstructs the entire original helper exactly. The scope includes the immediately following Creation comment so it distinguishes the unchanged similar deletion return. All other helper bytes, including constants and both original guards, are preserved.

No newly introduced semantic counterexample was found in this finite read. This is not a broader re-audit or a race/cleanup proof.

## Appended native helper control

The complete old 60735-byte test file is independently verified as the exact prefix of the new file; appended bytes are 2495. All pre-existing assertions and test bodies remain unchanged.

New lines 676-706 add one positive capacity/preservation test:

- Existing global beforeEach/afterEach at 63-64 also applies to the new describe: synthetic owner/case setup, fresh local/session stores and native Web Crypto are retained.
- 64 distinct valid command UUIDs are passed through real journalAdmissionsAction, not fabricated journal/index JSON or mocked success responses. Each persisted body and not_sent state is asserted.
- Real readAdmissionsActionsRecovery must return all64 descriptors/entries, exact sorted UUIDs and pending/not_sent states.
- Full key/value snapshots include all localStorage and sessionStorage bytes, the exact index raw string and an unrelated key; successful read must leave them unchanged.
- A distinct65th command is refused with the native limit result; its original caller body is preserved and its entry key remains absent. Full physical storage and raw index snapshots are unchanged.
- A subsequent real read must still equal the earlier64-entry result and preserve both stores.

The new valid64-to65 test is a meaningful positive boundary/control, not the sole regression reproducer; the prior malformed65-key test remains exact and exercises the earlier bad error path. The package's 86+1=87 case count is source arithmetic only, not this reviewer's collection or runtime result.

## Qualification boundary

Only ordinary source/diff reads, hashing and exact text preservation checks were performed. Only this new external report and its metadata seal were written. No application/primary/lab edits, imports, AST, lint/format/test execution, DB/browser/network/provider operations, Git/HANDOFF/helper/config edits or stopped workflows occurred.

No additional source prerequisite is proposed. Root owns exact application and authorized native gates. This disposition claims no executable PASS, browser durability result, full gate, deployment or product acceptance.

