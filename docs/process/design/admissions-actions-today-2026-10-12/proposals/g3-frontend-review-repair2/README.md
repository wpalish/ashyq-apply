# G3 frontend finite review repair 2

Status: **external source only; NOT_APPLIED / NOT_IMPORTED / NOT_RUN / NOT_ACCEPTED**.

## Exact authority and bases

Root issued `G3_FRONTEND_FINITE_REVIEW_REPAIR2_GRANT.json`, SHA256 `d9c29375c853ac2b371dda23c16a7b8fb749b8969dcf584e43155409b2c73461`. Its exact snapshot is `inputs/SOURCE_GRANT.json`.

Only four full postimages are proposed:

- `frontend/src/lib/admissionsActionsRecovery.ts`
- `frontend/src/lib/admissionsActionsRecovery.test.ts`
- `frontend/src/types/admissionsActions.ts`
- `frontend/src/types/admissionsActions.test.ts`

Recovery preimages are the immutable DELETE repair 1, SEAL `2c7d73199aa4a691257d5d9a7af59797949e3f5de57f443b49db4c3a2e9e43bb`. Types preimages are the immutable original foundation, SEAL `e48a39997f0295d91710525fa3d4a0c873cf00e1397433ffc23b2b52de4c7b01`. Both seals and all their members remain unchanged. This packet overlays only these four paths; the original additive API client and transport tests remain the original foundation versions.

Root is the sole primary/lab/Git/HANDOFF/helper/runtime writer. No screen, Store, auth, backend, wire DTO, schema, configuration, dependency or native control changes are included. The finite repair does not recreate the complete native validator in the frontend or change any public contract.

## F2: acknowledged replay after asynchronous hashing

The acknowledged branch previously returned the earlier validated entry together with newly read raw bytes after digest awaits without proving they still represented that entry. It now requires `g3Canonical(parse(raw)) === g3Canonical(validatedEntry)` immediately after the final owner/case/generation-fenced raw read. Missing/changed bytes refuse as `changed`; malformed JSON refuses as `invalid`. This branch performs no write and does not claim that a known server ACK has undone a local corruption.

The controls alter acknowledged entry bytes during the final receipt hash: changed draft generation, malformed JSON, foreign owner, or an extra full-current field. Each refuses and preserves the exact altered bytes and index, with the only storage write being the test's deliberate interleaving. A same-content JSON key-order change remains a successful read-only replay. Existing unchanged replay controls are retained.

## F3: strict scalar enums

All five `includes(String(value))` checks are replaced by an explicit string type check followed by membership:

- Personal responsible actor in command/receipt personal input.
- Command document report state.
- Correction prior event kind.
- Receipt document report state.
- Receipt application status.

Single-element JSON arrays, plain objects and booleans cannot become enum values through string coercion. Existing scalar positive commands are preserved. Rehashed malformed receipt controls cover task responsible actor, applicant-report state and application status; each retains the pending intent and then accepts the unchanged scalar receipt for that same intent.

## F4: two direct receipt intent relations

Selection receipts now require their complete observed native head to equal the request's complete native head. Common origin/profile/schema/revision and every origin-specific field are compared. Only typed G2 UUID and UTC fields normalize semantically: UUID case and `Z`/`+00:00` representations may differ, and fractional seconds normalize to Python's exact six microsecond digits without rounding. Different instants or even a one-microsecond difference refuse. Legacy V1/V2 fingerprint fields compare exactly. No arbitrary notes, local dates, applicant text or original request body changes.

Personal task creation now directly requires `binding === null`, `binding_ref === null`, and `origin === 'applicant_entered'`. A plausible source record carrying a copied valid binding cannot retire a personal-create intent merely because it was rehashed. Genuine `bind_source_task` receipts remain allowed. The positive bound fixture derives the native `g3-checklist-binding-v1` reference digest independently with Node SHA256 over the exact canonical UTC payload; the negative copies that valid reference into the wrong command relation.

Rehashed G2 head mismatches cover profile, revision, UUID, snapshot digest, allocation digest, different instant and a one-microsecond difference. Legacy V1/V2 wrong-head controls also retain their matching positive ACK. The positive G2 control uses uppercase typed UUID, original `Z` microseconds and short-fraction transport for top-level accepted time while retaining the original personal intent bytes.

## Preservation and proposed controls

Both old test files are exact byte prefixes of their new versions. All 61 prior recovery cases, including original F1 repair cases, remain intact; the original 31 form cases remain intact. Recovery source changes only the acknowledged replay branch: removing the added two guard lines restores its exact DELETE repair 1 preimage. All DELETE-only helpers, legacy helpers, ordinary owner/case fences, pending ACK path, original request/body hashing and storage controls remain byte-identical.

Type source changes are limited to five scalar enum replacements, private native-head comparison helpers, and the two direct F4 relations. Their literal inverse restores the original foundation type module exactly. No API client/transport path is changed.

New cases by **source arithmetic only**:

| Group | Cases |
| --- | ---: |
| F2 changed replay variants + equivalent replay positive | 5 |
| F3 array/object/boolean command enum controls | 3 |
| F3 rehashed receipt enum controls, 3 fields × 3 shapes | 9 |
| F4 wrong G2 observed head | 7 |
| F4 legacy V1/V2 wrong head + matching positive | 2 |
| F4 exact UUID/UTC G2 transport positive | 1 |
| F4 copied valid binding negative + genuine bound positive | 1 |
| **Added total** | **28** |

Expected cumulative source arithmetic: forms **34**, transport **10**, recovery **86**, total **130**. These are **NOT_COLLECTED / NOT_RUN**, not passed tests. The author used only source reads, text authoring, hashes, literal byte preservation comparisons and unified diffs. No application imports, AST, formatter, lint, test collection, tests, DB, browser, network or provider/model execution occurred.

The known finite 64-intent journal capacity, later explicit retention UX, later actual Store/UI integration controls and all prior STOP boundaries remain unchanged. This source packet is not whole-foundation qualification or product completion. Root and independent peer review the immutable packet and control any later application and actual native gates.

`MANIFEST.json`, `SOURCE_PRESERVATION.json` and `SEAL.json` enumerate exact authority/bases, postimages, source arithmetic and every immutable member. Seal creation itself is not approval or runtime evidence.
