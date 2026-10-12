# G3: native frontend integration seams

Read-only source scout, 12 October 2026. This is an implementation map, not a new contract/freeze, a source proposal, or runtime qualification. No mutable frontend-foundation proposal was read. No app imports, AST, tests, browser, DB, network, Git or native source changes.

## Smallest screen integration

| Native seam | Concrete current boundary | G3 connection |
|---|---|---|
| `App.tsx:41–76,205–247,281–312,478–495` | Existing hash screens; Documents and Plan already ungated; keyed main unmounts old screen. `setScreen` and hash rollback share a leave guard. | Keep `#/home`, `#/approved`, `#/documents`, `#/preparation`. Home can host Today; Approved can host durable Applications; Documents can host durable personal/source tasks above the retained collected-checklist reader. Personal saved-case workspace must not be conditional on research rows. No new router required. |
| `HomeScreen.tsx:7–56,71–80` | Browser-derived next step knows profile/run/results only; checklist presence is not readiness. | Fetch owned Today only after saved case/hydration; retain its independent action/workload/source permission states, local day/timezone, unavailable/mixed notices and one study budget. Do not turn a failed read into zero tasks, merge G2+legacy minutes, or derive official deadlines from personal dates. |
| `ApprovedScreen.tsx:13–24,39–96` | Decisions/collection, not saved application records. The native hero chooses flattened result deadlines. | Show immutable G3 target/intake/award application records and current personal details/status separately from result decisions. Source informational links come from validated current G3 response, not a constructed URL. Existing Find/collect/preparation callbacks remain. |
| `DocumentsScreen.tsx:25–62,177–249` | Local marks use `result.id::name`; four owner arrays are sorted by lead time. | Preserve legacy marks as local convenience only. Durable task IDs/report receipts are separate; explicit import-preview/mapping only, no automatic adoption/name matching/clear. New report is applicant-declared, never official fulfillment or readiness. |
| `PreparationScreen.tsx:47–58,104–120,177–231,244–249` | Exact `LearningTaskRef` dispatcher already validates lesson id/version or owned attempt UUID/lesson/version. There is no external target prop yet (`App.tsx:495`). | Pass a single explicit owner/case/epoch-bound handoff through App to PreparationCase, consume once when needed access/data is ready, then call the existing dispatcher. Review uses the owned UUID endpoint even outside the recent twenty; expiry does not require new-lesson access for saved review. Never replace a pinned version with catalogue latest. |
| `store.tsx:182–237,364–366,890–929` | Context scope, owner-at-mount, operation generation and caseEpoch; delete cleanup occurs only after real DELETE ACK. | Use the same owner/profile/epoch tuple to remount/fence G3 reads, commands and handoffs. Add the captured-case G3 journal retirement/tombstone hook beside `forgetSharedRouteRecovery(caseKey, storageScope)` at901, after ACK+owner check and before rejecting obsolete screen generation. A late successful delete of A may retire A only; failed delete or B must not clear B. |

## Exact Today → App → Preparation handoff

Current `HomeScreen.onNavigate` and App's `setScreen` accept screen names only. A minimal future App-owned target carries the **server-projected exact ref**, captured verified owner, profile ID and caseEpoch plus a one-use navigation identity; it is not a lesson body, guessed exam association or global registry. Verify that tuple before navigation, before consumption and after I/O; clear/ignore on case switch-start, owner replacement and stale unmount. Keep hash address/history and main focus behavior. When preparation initial loading fails, retain target for explicit read retry; do not silently consume it as success or send a preparation attempt. The existing `openLearningTarget` maps lessons to `startLesson(id, content_version)` and reviews to `openReview({attempt_id, lesson_id, version})`.

## Personal command/recovery/nav seams

- `draftIdentity.tsx:10–16` is the owning React-tree identity, not a module identity. `AuthGate.tsx:85,113` keeps authenticated Legal inside that tree and remounts private content by verified owner. `applicantStorage.ts:23–41,59–72` rejects stale shared-cookie tabs; explicit demo and authenticated namespaces remain distinct.
- Existing `sharedRouteRecovery.ts:167–215,225–247` shows per-tab reference-only storage, exact raw compare, own pending body retirement and postDELETEACK case cleanup. A new G3 journal must use its own version/key/typed command validation; do not call G2 validators or reset G2 journals. Existing `ashyq.owner.` cleanup covers an appropriately scoped key on acknowledged logout/account deletion (`applicantStorage.ts:9–20,92–95`; `api/client.ts:224–226,258–262`).
- `SharedRoutePanel.tsx:283–315,317–345,430–487` is the useful behavior reference: exact original UUID/body before dispatch; no automatic POST on restore; current/own-history GET reconciliation; known ACK remains known if local cleanup fails; later draft survives. G3 uses its own event endpoint/canonical command receipt, not G2's revision-history URL. A fresh intent requires explicit review/save; source preview failure never changes a pending command.
- App's token-map registration at120–133 guards **every meaningful dirty draft or pending command**, including when storage succeeds, with native/hash/case/new-case/beforeunload protection. Add G3 panel registrations with distinct symbols and the same callback; old cleanup must retire only its symbol. Owner/security unmount is immediate, not blocked by confirmation. App logout at438–445 clears the risk set only after actual logout ACK and owner/operation fence. Keep those semantics.

## Raw source preview and self-declaration

The native TS checklist (`types.ts:342–355`) has six ordered arrays: `admission_documents`, `scholarship_documents`, `applicant_actions`, `school_actions`, `recommender_actions`, `certification_actions`. Build explicit `(location,index)` choices from these original arrays **before** any lead-time grouping, sorting, deduplication or display-name projection; preserve equal-name separate occurrences. Require explicit purpose and scholarship award identity; submit `/preview`, then retain the exact returned canonical selection/token for bind/rebind. If current data differs, preview is unavailable/changed/locked and a new explicit preview is required. Do not manufacture scope/proof/raw URL omission/null from the older TS DocumentItem shape, whose scope is absent (`types.ts:318–340`); the server's authorized raw adapter is authoritative.

`schemas/admissions_actions.py:428–449,589–638` preserves entered declaration date/time precision, channel/reference/task IDs and explicit confirmation. UI must label submission/withdrawal as **reported by the applicant**, `official_verification=not_performed`; accepted time/actor/event are server receipt metadata, not university acknowledgment. Correction selects an exact owned prior declaration event and explicit replacement (submission/withdrawal/planning); retain prior event/history, including planning-correction chains. Rebinding keeps the old report and shows `report_refers_to_previous_binding`, never auto-fulfills the new binding.

## Existing controls to extend later, without weakening

- `PreparationScreen.learningPath.test.tsx:201–249,251–349,381–417`: old-version review, late owner/case responses, pinned lesson and attempt outside20. Add Today handoff to those paths; no current-version or recent-list fallback.
- `storeIsolation.test.tsx:42,61`; Documents privacy/ownerMerge/recovery tests; `draftIdentity.test.tsx:50–171`: failed/late DELETE, owner replacement, ACK cleanup and no foreign draft read. Add G3 case tombstone exact-match controls.
- `frontend/e2e/journey.spec.ts:189,250` retains approve/collect/export and hash history; Auth journey561/657 retains clean-browser G2 and Legal/logout boundaries. Later new G3 native scenario should forward a real own command before lost-ACK fault, reload/manual original retry or exact own GET reconciliation, and assert no duplicate write; no fabricated receipt.
- Existing `.doc` styling (`styles/components.css:301–314`) and responsive plan/preparation patterns (`styles/unimatch.css:276–290,315–344,361–381`) can be extended with scoped G3 classes. Keep native labels/fieldset scoping, 44px controls, readable long IDs and keyboard focus; EN/RU/KK copy goes through finite `i18n` keys rather than presenting provenance/unknown only in English.

No screen implementation, source application, new acceptance test, or completed-product claim is made here.

### Inspected native source pins

- `frontend/src/App.tsx`: `293f8aeccb4286660bd1822a3a914a74218b85c4704be1b4fcdf0fda5b031725`
- `frontend/src/screens/HomeScreen.tsx`: `bda406914a413a5371d5299f48aa5dfe6b0fbf3bcfae9b1613bbf25b4be18517`
- `frontend/src/screens/ApprovedScreen.tsx`: `0395dc3be1315f4c09defc2e0be85434fad0848b407220fa2903f26cdbe6b89a`
- `frontend/src/screens/DocumentsScreen.tsx`: `e7ef0217c19f051c434acb69fb7f2b0ea1883a2228984054747cb8b77abcde9f`
- `frontend/src/screens/PreparationScreen.tsx`: `52c8c4df92498e8cbe1f52b135f755ea7329aab34cff9e71b0bc8431a8b64bb1`
- `frontend/src/lib/store.tsx`: `81afb3fbe97ccd015d9755bfd1fe4079e57eae8bfd2a48363c308545842f272a`
- `frontend/src/lib/draftIdentity.tsx`: `4039d06362d2861d79d5daec2891c1c1f613d93e4c0360bf5da915db55f3d015`
- `frontend/src/lib/applicantStorage.ts`: `0a3230d223e5dbfc1ead6dbece478ce54c9ec6bc557493115716e5709818fd0e`
- `frontend/src/lib/sharedRouteRecovery.ts`: `e5c1affec9bd8fba64238865d09aec8b8f36afb4bd8b059267a385f9e3280561`
- `frontend/src/screens/SharedRoutePanel.tsx`: `9568c85899a8f7915a965f9a0de9c0ec8a9a5a54086be3fb6c98c8addefb62d7`
- `frontend/src/AuthGate.tsx`: `b62948ab9c6f0b07bfc0238a21f80d2f7d32aa3ee008dd901c62da954b71c479`
