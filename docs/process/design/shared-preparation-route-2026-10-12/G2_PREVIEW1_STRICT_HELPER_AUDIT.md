# G2 preview1 strict helper / panel audit

**2026-10-12 · READ_ONLY_SOURCE_REVIEW · NOT_APPLIED / NOT_IMPORTED / NOT_RUN**

Reviewed only the immutable preview1 helper/panel, its unchanged UI preimage and the native shared-route input/anchor schema as contract references. No app/source/Git/import/tests/runtime/provider/closed-label work. Preview1 bytes were preserved. Known F1 (meaningful manual/disabled input falsely clean after ACK) and F2 (accepted ACK hidden on local cleanup failure) are already assigned; they are not counted as new findings here.

## Finding R1 — inherited expired state becomes a persistent recovery dead end (P2)

**Exact preview1 source:** SharedRoutePanel.tsx:464–470,474–485,615–633,386–399.

A valid path is:

1. An allowed page gets a valid server preview. Access expires before PUT, which returns the native402. sendWrite records pending.state=expired and persists the original typed body/UUID.
2. The owner later regains preparation access (allowed=true), including after reloading the same own case. The strict helper accepts/restores expired because it is an allowed dispatched state (sharedRouteRecovery.ts:159–163).
3. The owner reviews a successful fresh preview of the retained input. The fresh preview remains unsaved: savePreview returns whenever pending exists (Panel475), and the save control is disabled by !!pending (621).
4. retryOriginal excludes expired even when allowed=true (485/626). The explicit fresh-intent control is rendered **only** for conflict (627), so this owner cannot retire the rejected old intent and issue the reviewed fresh one.
5. Only resetLocal removes the pending marker. It resets every draft/manual field and generation (393–398), losing the input which the recovery feature intentionally retained.

This is distinct from F1 and F2. It is not an incorrectly accepted server write; it blocks a legitimate reviewed new save. The expired exclusion/conflict-only control is inherited from the preimage (367,500–507), while preview1 persists/restores the dead state across reloads.

**Small correction for the author:** permit an explicit, owner/current-intent-fenced transition from expired to a reviewed new intent after a fresh successful preview and currently allowed access, retaining the complete current draft/manual fields and keeping the original body/UUID immutable until that deliberate transition is acknowledged locally. Use a new UUID only on the subsequent explicit save. Do not automatically PUT, reuse the old UUID for changed preview inputs or clear a sending/uncertain command as if rejected. Continue free current/exact-history reconciliation before presenting an unresolved accepted outcome as a new command.

**Focused control, NOT_RUN:** save returns402; reload restores expired input/UUID; access becomes allowed; fresh preview succeeds; explicit new-intent adoption preserves fields and produces a new UUID for the second save. Storage/CAS failure must retain the original pending and block the new intent, rather than discard the form.

## Other finite source observations

No additional confirmed owner/parser/CAS overwrite defect was established in the inspected bytes.

- Owner/key/profile binding is derived from the captured native owner, checked against currentApplicantOwner, and the storage key is recomputed rather than accepted from journal fields (helper166–179). Foreign/mismatched envelope stays invalid; exact-own explicit reset is required.
- Existing invalid raw bytes are not silently overwritten: write compares exact raw, then requires matching valid draft ID/journal revision (197–207). Read rejects oversize, malformed and unrecognized typed fields (180–189). This is per-tab browser recovery, not transactional cross-context storage CAS.
- Body shape/input limits, exam order/priorities, chosen review exam, review IDs, date buffers and legacy presence/null rules agree with current UI buildInput and native SharedRouteInputV1/LegacyAnchor in normal supported flows (helper99–147; Panel179–237; native schema261–293,568–590). A partial manual draft remains draft text; it is not sent or used as ownership evidence.
- Reconciliation performs at most one exact expected_revision+1 history read if the current accepted head advanced, without automatic PUT/preview/reallocation (Panel330–344). It still checks profile, original UUID/body and intent fences before acknowledgement.
- ACK retirement compares current raw/draft ID/revision and original command before clearing pending. A later generation remains dirty (helper217–224). Known F1/F2 qualify this behavior until their separate fixes are applied; this review does not declare them closed.

One compatibility boundary is **not proven by source reading**: helper106 adds browser Intl timezone acceptance to the native server ZoneInfo contract (schema72–79), whereas buildInput only enforces exact bounded text. Different browser/server timezone databases could reject a server-previewed input locally. No concrete mismatch for this installed browser/server was measured, so this is not counted as a confirmed finding. The future tests should preserve a server-approved exact timezone body without treating the browser registry as new authority.

## Pins

Paths relative to stage unless marked native checkout:

| Input | SHA-256 |
| --- | --- |
|proposals/g2-recovery-app-preview1/files/frontend/src/lib/sharedRouteRecovery.ts|ef26ecdc337d6d0d2ad8f0f0cc4e11de9bd2136d3fed9e52650cb5d63bdbfe52|
|proposals/g2-recovery-app-preview1/files/frontend/src/screens/SharedRoutePanel.tsx|2660e56d271a39c3cd2e3f4eb281b8b5388e83d872af93e35d3bcd5678d10a43|
|proposals/g2-recovery-app-preview1/preimages/frontend/src/screens/SharedRoutePanel.tsx|a5057f0c6307a863a4b6c7054144682217142400fd4a40a6c8422eaefa9ccd5e|
|native work/unimatch-calendar-materials/backend/app/schemas/shared_route.py|50c2dca8ad250f3d12fc9645a6307ac4dd05bf05a61c79c17bbf925b4c8042e2|

Conclusion: one additional actionable blocked recovery flow, inherited in the UI and now durable across reloads. No new runtime proof or acceptance claim. Preview1 remains immutable; fixes/tests belong to the author's next sealed packet and require root's own application/gates.

