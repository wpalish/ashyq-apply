# G3 frontend captured-case DELETE repair 1

Status: **external source only; NOT_APPLIED / NOT_IMPORTED / NOT_RUN / NOT_ACCEPTED**.

## Authority and scope

Root delegated this finite F1 repair under HANDOFF section 5, entry `2026-10-12T17:50:53.097744+00:00`. The captured entry is in `inputs/AUTHORITY_HANDOFF_EXCERPT.md`.

Only these two complete postimages are proposed:

- `frontend/src/lib/admissionsActionsRecovery.ts`
- `frontend/src/lib/admissionsActionsRecovery.test.ts`

Both exact preimages come from immutable foundation packet `g3-frontend-foundation1`, SEAL SHA256 `e48a39997f0295d91710525fa3d4a0c873cf00e1397433ffc23b2b52de4c7b01`. That original packet remains unchanged. This repair must be overlaid on its two corresponding postimages; it does not replace the other four foundation files.

Root remains the sole primary/lab/Git/HANDOFF/helper/runtime writer. No UI, Store, auth, backend, DTO, schema, configuration, dependency or old test changes are included. No independent application/runtime verification has been performed by the author or peer.

## Concrete F1 and repair

Native Store captures case A, awaits its DELETE, verifies the same owner, then cleans A before checking whether the operation generation became obsolete. The original G3 helper called ordinary `active(binding)` and therefore rejected A's successful deletion once the user opened case B or the case epoch changed.

The replacement DELETE helper has a dedicated deletion-only guard. It captures owner/profile/family/generation/current callback once and requires:

1. `acknowledgedProfileId` equals the captured profile.
2. The callback's current **scope** and independent native `currentApplicantOwner()` identify the captured owner. A callback cannot substitute for the native owner check.
3. The captured family is exactly derived from that owner and profile, with a valid captured generation. The stored alive fence has that exact owner/profile/generation; its bytes remain pinned through cleanup.
4. Any existing tombstone is validated and never overwritten. After writing the separate tombstone, its exact bytes are checked with the fence before and after subsequent storage operations.

The deletion-only guard deliberately does not require the current live profile/epoch to still be A. It does not manufacture an A callback or change any ordinary guard. All preceding ordinary read/journal/retry/command ACK functions and the following legacy helper are byte-identical to the original.

The caller must call this helper **only after the matching captured case's native DELETE successfully resolves**, while the same authenticated owner is still verified, and before Store's stale-operation-generation return. A caller-provided profile string or local tombstone is not independently a server ACK. The actual Store integration test belongs to the later UI integration grant and is not claimed here.

## Bounded cleanup and retention

Deletion scans the captured exact family under its dedicated guard, including each storage length/key/read operation. Only canonical UUID entry keys plus that family's fence/index/tombstone are accepted. Parsed index/entry bytes must retain exact captured owner/profile/generation and the existing strict finite shapes. It records exact candidate bytes and removes them only if unchanged under the same deletion guard.

If the fence/tombstone authority is malformed, foreign, replaced or lost, the helper fails closed without adopting or overwriting it. If the captured family authority is valid but entry/index/extra family bytes are invalid, the successful deletion can install the separate tombstone while leaving those bytes untouched and reporting `residual_unknown`. It never infers ownership from an index alone. Entry digests are not recomputed during this synchronous deletion helper: strict own headers/family/generation/shape determine cleanup candidates; the matching native successful DELETE is the required upstream authority.

Storage failures, changed bytes, concurrent/interleaved writes, or invalid residual keys produce `residual_unknown`. The marker blocks later hydration even if a late alive initializer or late intent write arrives. If storage or owner verification fails after the marker write, `tombstoned: false` means the helper could not complete verification; it does not certify that a partially written marker is absent.

LocalStorage remains non-transactional. `completed_best_effort` means the exact verified family had no observed residual index/intent bytes at the final checks. It is not certified erasure or an atomic cross-tab guarantee. Sibling case B, its pending entries/index/fence, raw legacy marks, and unrelated origin keys are retained. No owner-wide wipe is added.

The original finite 64-entry journal retention limitation remains unchanged and still requires a separately reviewed explicit retention UX before broad screen integration. No automatic acknowledged-intent eviction is introduced by this DELETE-only repair.

## Proposed controls and evidence boundary

All original recovery test bytes are preserved. Exactly **15 additional cases by source arithmetic** are appended before the original late-write control:

- Six single controls: authenticated captured A DELETE after active B/epoch switch, independent native owner refusal, owner change during family scanning, generation change during entry reading, replacement-intent interleaving, and owner change during marker writing.
- Five authority-byte cases: foreign fence, changed fence generation, malformed fence, foreign tombstone and malformed tombstone.
- Four family-payload cases: foreign entry, foreign index, changed entry generation and malformed entry.

The A→B successful ACK control also verifies that ordinary stale A read/journal/retry/command ACK still refuse, B's exact bytes remain unchanged, raw marks/unrelated keys persist, live B/epoch stays unchanged, and later A activation is blocked by the tombstone. Wrong-case ACK is refused before any marker write.

Expected source arithmetic: recovery **46 + 15 = 61**; entire foundation **87 + 15 = 102**. These are **NOT_COLLECTED / NOT_RUN**, not passed tests. The author performed only text authoring, reads, exact byte comparisons, hashes and unified diffs. No application imports, AST, formatter, lint, test collection, tests, DB, browser, network or provider execution occurred.

F2/F3/F4 reported by the independent product reviewer concern separate ACK/enum/receipt-shape gaps in the original foundation. They are outside this two-path deletion-only authority, are not repaired here, and prevent interpreting this finite F1 packet as qualification of the whole foundation. Root controls any subsequent finite repair and all actual gates.

The immutable seal and manifest enumerate the exact preimages/postimages/diffs/inputs/review members. Apply only after root verifies those members, performs ordinary source review and grants the applicable next source-bound gate.
