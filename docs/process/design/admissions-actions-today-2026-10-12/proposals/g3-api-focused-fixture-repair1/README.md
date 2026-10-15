# G3 focused API Today fixture repair1

Status: **EXTERNAL_SOURCE_ONLY_NOT_APPLIED_NOT_IMPORTED_NOT_FORMATTED_NOT_RUN_NOT_ACCEPTED**. One proposed application path: `backend/tests/test_today.py`. Parent `/root` owns route changes, source application, write-ahead/HANDOFF, independent review and all native execution.

## Authority and exact basis

`G3_API_FOCUSED_REPAIR1_GRANT.json` SHA256 `b786a779c02610a7077bb7c172d2de1ac3621baf928d9aaa7ce373b6f84ea60b`, write-ahead timestamp `2026-10-13T05:48:52.993578+00:00`. Today-only delegated slice. The complete preimage is the native focused API2 source `2925c3fbbf4c10bc24744d4579e25f838690e441503195ae41d2fed8979fda16`; it matches recorded source-before and source-after. Complete postimage: `0acb3fcdbb9929fb921920fbcdb57f5d50bd63ef025e38d4871aa432b0c8a86d`.

## Finite scenario changes

1. **Exact native versions.** Retain the existing entire per-slot comparison of occurrence ID, date, timezone, exact ref (including version), order and minutes. Retain the own attempt-review presence assertion. Replace the erroneous one-version-for-all expectation with the exact set of versions in the accepted native G2 receipt, and separately require the own attempt-review's version set to equal exactly the original attempt version. Mixed starter/learning-pack identities are preserved. No catalogue, allocator, schema or saved reference is altered.
2. **Legitimate dependency plus missing-reference refusal.** The IANA/date/order HTTP scenario now depends on its first preceding genuine owned unreported task. Its exact native read annotation is `dependency_not_reported_ready`. After the four accepted tasks, build one missing-reference create command with expected revision4. Repeat this identical UUID/body twice; each must return exact `record_not_found`404, capture no INSERT/UPDATE/DELETE, preserve exact native_snapshot and stored G3 rows, and preserve the original request body. No fake accepted receipt, digest repair or dangling accepted history is created.

Both changes correct new synthetic scenario assumptions observed in the root's failed focused diagnostic. All remaining assertions, functions and imports are byte unchanged. The previous domain missing-ID command guard remains intact; the proposed negative control now explicitly exercises it through real HTTP. Defensive `dependency_missing` read projection is not claimed as accepted through an impossible command.

## Source preservation and scope

Exactly four finite literal replacements were made. Applying their exact textual inverse reconstructs the full preimage bytes and SHA256. Non-target-function prefix, inter-function span and suffix were separately checked byte unchanged without AST. Originals/postimages/diff are complete. No primary, lab, runtime source, domain/schema/model/configuration, other test, Git or HANDOFF was written. No application import, AST, formatter, linter, collection, test, provider, database or browser was executed.

The parent recorded an earlier actual focused result of192 tests/48 failures; it is not a pass or coverage receipt for this postimage. This packet adds no new test function or configuration. The two corrected parametrized scenarios and repeated same-intent negative requests remain **NOT_RUN** until root's authorized execution.
