# G3 frontend physical intent cap repair1

Status: **SOURCE_ONLY_NOT_APPLIED_NOT_IMPORTED_NOT_RUN_NOT_ACCEPTED**.

## Authority and exact scope

Source grant: G3_FRONTEND_PHYSICAL_CAP_REPAIR1_GRANT.json, SHA256 cbcedbc352900728e7b5310fe4df38110eeef45731128553f6e9b4aea97761ef. Exactly two proposed files: the recovery helper and its existing test file. Root owns application, qualification, primary/lab sources, Git and HANDOFF. Independent review is pending.

## Cause and minimal repair

The existing ownFamilyKeys coarse bound permits up to64+3 total family keys, reserving room for fence/index/tombstone. If reserved metadata is absent,65 actual UUID intent keys can remain below that coarse bound. The scan then parses malformed entry bytes and reports invalid before detecting the physical intent count.

The proposed helper preserves the coarse whole-family bound and both existing key-validity checks byte-for-byte. After those checks, it collects the actual intent keys and rejects a count greater than the unchanged G3_RECOVERY_ENTRIES_MAX64 before returning the sorted keys. Therefore malformed bodies in an otherwise valid over-cap key family are not parsed. Existing invalid-key precedence and all fence/owner/storage guards remain unchanged. Only the ownFamilyKeys return expression receives this finite count guard. The separate deletion-only family scan, ACK, retention, index validation, transport, types, limits and configuration remain unchanged.

## Meaningful appended control

The entire current recovery test preimage is preserved as an exact byte prefix, including its existing malformed65-key limit assertion and all86 existing expanded cases (the86 count comes from the source grant, not a new collection). One appended control uses the real open/journal/read helper path to create64 distinct valid pending personal commands, verifies their original bodies and not_sent state, and reads the complete64-entry/index result. It then submits a distinct65th command and expects limit while preserving the original caller body, every full localStorage key/value byte, all sessionStorage bytes and the exact index raw string. The rejected UUID has no stored entry. A subsequent read must still return the same64 entries without any storage changes. An unrelated synthetic key is included in the full storage preservation comparison. No transport or server is called.

The existing malformed65-key test directly exercises the repaired regression. The new valid64-to65 test is a positive capacity boundary/preservation control; it is expected to have passed before this repair as well. It is not presented as the sole regression reproducer.

## Source preservation and expected verification

- Exact current preimages are copied to preimages/; complete proposals are under postimages/.
- Diffs are unified source text comparisons.
- A single literal helper replacement scoped to ownFamilyKeys is inverted and compared to the whole original helper; all surrounding bytes, including the similar separate deletion function, are exact.
- The complete original test is an exact prefix of its postimage; only one new test is appended.
- Grant and native preimage SHA256 pins are checked before authoring and immediately before sealing.
- Source arithmetic: existing86 recovery cases +1 appended =87 expected. This is **NOT_RUN**, not collected or passed evidence.

Root/peer should verify the immutable packet and finite scope before application. Only root may run the native frontend gates and actual Vitest suite against applied sources. Earlier actual gate results reported by root are not execution performed by this packet author and do not qualify this postimage.

No application imports, AST parsing, formatter, lint, test collection/execution, browser, provider, network, DB, secret/user-data access or mutation was performed. No primary/lab, existing source packet, helper/runtime, Git or HANDOFF file was changed. Standard-library text/byte/hash/diff operations were used only to author and seal this external packet.
