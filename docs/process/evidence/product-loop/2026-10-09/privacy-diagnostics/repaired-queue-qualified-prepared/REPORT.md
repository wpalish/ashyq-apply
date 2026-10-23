# Prepared sibling queue — exact scope qualified

**QUALIFIED_SAVED_ONLY_EXACT_SUBSTITUTION / NOT_EXECUTED.** Fresh siblingSHA`02a3177263538f02595b4d1bd4a1094df3711126d0d8cee8b1f548ae22c62cb7` is byte-for-byte the prior qualified queueSHA`e5d7c351b882fed0c6096a88058972e867f937e945c0c125aeb6a5666cf741f2` after only the five requested string substitutions. exact-diff.patch preserves the complete diff. The source comparison is not a runtime test.

| Existing name | Fresh sibling name | Occurrences changed |
|---|---|---|
| native-queue | repaired-native-queue |1|
| applied-source-pins.json | repaired-source-pins.json |4|
| application-receipt.json | test-repair-application-receipt.json |1|
| EXACT_SOURCE_APPLIED_FULL_PENDING | EXACT_TEST_REPAIR_APPLIED_FULL_PENDING |1|
| applied-head.txt | repaired-head.txt |1|

The exact same code remains for:

- Required typed application receipt and exactly34loaded pins; initialpins SHA bound to receipt, immutable pins-document and receipt SHA rechecked on every verify.
- Recorded repaired HEAD, expected task branch, clean primary tree, all34current selected file hashes and immutable providerSTOP65b5.
- No existing output reuse: fresh OUT.mkdir(exist_ok=False), with its own logs/execution records. It does not overwrite or adopt the first failed native-queue.
- Availability probe without starting/adopting ports/DB; actual bundled runner owns the exclusive lock. Probe is not a lifetime reservation; contention produces a nonzero stop rather than retry.
- Own launched-child Results parsing, canonical new non-symlink summary, exactrepo/HEAD/branch, actualpassed status/all exitcodes0 and exact5/8/13doctor/core/full step names; exactlyoneown result before the next suite.
- One doctor→core→full sequence with absolute --repo. Nonzero suite stops before the next suite; ambiguous own result/source/receipt/HEAD assertion also stops. A failed core therefore keeps full NOT_RUN. Configured distinct steps inside a suite may finish before its combined nonzero; this is not a retry of that suite.

All inherited functions, conditions, argv generation, expected suite steps, STOP constant and ownership logic are otherwise unchanged; no app/config/source/test/default/gold/reset path or new live/pilot/provider/model/cloud/production command appears in the diff. No prepared tool or check was executed in this review.

Fresh repaired pins/receipt/head and output directory are intentionally absent at the saved read. Root must first apply the separately reviewed exact test repair, commit/push the clean WIP, produce the exact repaired source34 receipt and HEAD, then execute this sibling under its own existing guards. This packet does not independently evaluate root's OFF/ON29controls or establish a new actual native/full result.

Original firstfailed core/doctor originals107b0cd7, originalqueuee5d7c351 and priorprepared findings/qualification remain unchanged. A later passing fresh run cannot relabel their4391PASS+1FAIL/core7of8/fullNOT_RUN history. No primary/Git/source/runtime/reset scope was changed. Containers, legal/operator/consent, production and search quality are outside prepared acceptance.
