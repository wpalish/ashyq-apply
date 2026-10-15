# G3 UI integration plan1 — native screens only

**PLAN_ONLY / SOURCE_CLOSED / NOT_APPLIED / NOT_IMPORTED / NOT_RUN / NOT_ACCEPTED.**  
Prepared by `/root/open_search_solutions`, 2026-10-13. This is finite integration metadata for root's next bounded UI grant. It does not authorize source, helper, runtime, Git or HANDOFF changes. Backend/foundation gates and the new root write-ahead remain prerequisites; existing STOPs remain unchanged.

## 1. Exact basis and useful first screen slice

Use the existing own-case API and foundation, not a second admissions ledger or planner. Keep native `#/home`, `#/approved`, `#/documents`, `#/preparation`; no new router, backend DTO, course, crawler, upload, portal submission or payment flow.

- **Home:** read-only server Today with its separate action/plan/source/access states, exact target clicks and one selected study budget.
- **Plan / Approved:** durable own application records and personal declaration/history controls alongside retained programme decisions and Collect.
- **Documents:** durable own personal/source-bound tasks and self-reports above the retained collected-checklist/browser-tick reader.
- **Preparation:** consume an exact owner/case/epoch-bound lesson/review handoff through the existing dispatcher. No new catalogue or allocation.

The frozen scout is `proposals/G3_NATIVE_FRONTEND_SEAM_SCOUT.md`, SHA256 `b5b251ee1fecd5a9be5bc559bbd7eb5557e4e28516ee5c1a1dc9acd493add989`. Its native screen pins still match current source. Original foundation seal `e48a39997f0295d91710525fa3d4a0c873cf00e1397433ffc23b2b52de4c7b01` has **19/19 declared member SHA/size matches** in this inspection. It remains an unqualified predecessor with four recorded findings; this plan does not read or qualify a mutable repair. Exact read pins are in the companion seal.

## 2. Concrete native callsites and bounded extensions

| Existing path / callsite | Finite integration |
| --- | --- |
| `screens/HomeScreen.tsx:7–16,58,71–80` | Mount a new `TodayPanel` for a hydrated saved case; keep the research next-step panel independently. A failed Today read is an error/retry state, not zero tasks. A new/unsaved case receives the existing save-profile action. |
| `screens/ApprovedScreen.tsx:13–36,49–87` | Mount a reusable `AdmissionsActionsPanel` in applications mode **outside** the `results.length===0` early return. Own saved applications survive empty/stopped/disappeared research rows. Keep current decide/Collect callbacks and their gates unchanged. |
| `screens/DocumentsScreen.tsx:37–62,106–121,157–171` | Mount the same panel in document mode independently of `current` checklist/results. Keep `toggle/loadDone` as browser convenience only, with an explicit old-browser-marks label. Do not turn the four sorted owner arrays into durable task identity. |
| `App.tsx:106–133,237–247,281–312,415–445,478–495` | Pass the native leave-risk callback to G3 panels; retain individual symbol registrations, hash/native/back/case/new-case/beforeunload guards and immediate owner-security unmount. Add a transient exact target handoff, not URL-encoded personal/source data. Keep current main focus and navigation. |
| `screens/PreparationScreen.tsx:47–58,104–120,177–231,244–249,372–389` | Add the optional exact handoff and reuse `openLearningTarget`. Keep native lesson/access/version and review owner/UUID/version checks. A directly requested review needs a small independent review rendering/explicit retry path because the current review UI is inside `data &&` at259. |
| `lib/store.tsx:182–237,364–366,890–929` | Capture the G3 A-family binding/fence before DELETE; invoke repaired matching-case cleanup after actual ACK + owner recheck at898–903, before obsolete-generation return904. Expose only current owner/case/epoch identity needed by panels, not a new global action store. |
| `api/client.ts` / foundation typed client505–528 | Reuse exactly `admissionsActions`, `writeAdmissionsAction`, `admissionsActionsHistory`, `admissionsActionEvent`, `previewAdmissionsSource`, `previewAdmissionsImport`, `admissionsToday`. No raw fetch or auth/error/client refactor. |
| `lib/i18n.ts:27–33,1197–1247`, `styles/unimatch.css` | Add a finite G3 dictionary with EN/RU/**kk** (KZ UI label) and scoped responsive classes. Keep the existing locale fallback and global styles. |

Candidate new implementation files: `screens/AdmissionsActionsPanel.tsx`, `screens/TodayPanel.tsx`, `lib/admissionsActionsMessages.ts`. Their tests should be new bounded files. The existing recovery helper/test need a **separate explicit finite grant** for acknowledged-entry retirement; the original foundation has no such export. This is local journal maintenance, not a new server feature or contract.

## 3. One own-case controller and existing command families

The panel boundary uses the verified `DraftIdentityContext`, saved server profile ID, native `caseEpoch`, mounted/operation/draft generations and a live identity callback. Undefined scope is used only under the existing explicit auth-disabled AuthGate branch (108–113), never as inferred anonymous access. Key the panel by owner + profile + epoch, and withhold stale responses before paint and around I/O.

One reusable controller owns the current G3 GET, editor, exact command journal and history. Use foundation types/guards and recovery operations; do not copy their validators, canonical hash rules or G1 projection into JSX. Do not cache full server current/Today/material/source/actor snapshots in browser storage or optimistically apply an ACK delta as a current read.

Finite UI command groups:

- Applications: `create_application`, personal details, planning/preparing, explicit submission/withdrawal declaration, and correction of an exact owned prior declaration event. Existing current state has only created/latest/status refs; history holds older declaration bodies. Do not invent last-submission refs or infer university acknowledgment.
- Documents: personal task, personal details/dependencies/responsible actor, explicit self-report, source bind/rebind using server preview, and reviewed legacy import.
- Existing selector/Today state is displayed as supplied. No clear/none command. A selector write can be offered only with an already **server-supplied exact native head**, matching origin; do not manufacture an alternative legacy sidecar/settings digest.

New target selection uses explicit current approved/maybe result IDs; exact scholarship award choice remains distinct from admission purpose. Intake/route can remain typed unknown or explicitly entered/confirmed. Backend authority validates selection, ownership, union20 and other caps; the screen does not rebuild those algorithms. An existing own record stays editable under source lock or missing result, using saved personal fields and safe status rather than loading hidden programme metadata.

For source binding, choices are original checklist `(location,index)` before sorting: all six native arrays, distinct same-name occurrences, explicit purpose/award. Send only the input expected by `previewAdmissionsSource`; retain its exact returned selection/token for bind/rebind. The old TS DocumentItem lacks complete raw scope identity: never synthesize scope, proof, URL omission/null or a G1 action ID. On stale/locked/changed preview, refuse the new bind and require explicit renewed preview; preserve the original pending command unchanged.

Display personal report and current source observation separately. Rebind keeps prior report and its `report_refers_to_previous_binding` notice. “Not needed” is applicant-reported, not a waiver; submission/withdrawal/correction are applicant declarations with `official_verification=not_performed`. No upload, signature, portal submission, admitted/ready badge or official score change.

Render a G3 action hyperlink only when the backend supplies `state=actionable_unverified` and a non-null href, with “information; destination not verified” copy. Blocked/demo/not_available is nonclickable, with no raw rejected URL echo. Do not run blocked raw URLs through the global SourceLink or change that global helper.

## 4. Native captured-case DELETE — A ACK while B is active

Required exact sequence at Store890:

1. Capture A ID, verified owner scope, current epoch and **A's existing generation/family binding** before awaiting `api.deleteProfile(A)`. The live callback reads current identity, not a captured A closure. If the G3 preflight cannot safely establish that binding, retain residual-unknown cleanup; do not prevent an otherwise authorized server DELETE or fabricate cleanup authority.
2. Await the native DELETE and then existing `assertStoreOwner()`. A failed/unresolved DELETE authorizes **no** G3 cleanup.
3. Beside `forgetSharedRouteRecovery(A,scope)`, invoke repaired `acknowledgeAdmissionsCaseDeletion(capturedA,A)`. Its deletion-only authority matches current verified owner, acknowledged A, exact family/generation; it does **not** require active case/epoch still A. Ordinary reads/journal/retry/command-ACK guards remain active-case fenced.
4. Preserve immutable deletion tombstone and helper's best-effort/residual result; a late alive initializer or write cannot reopen A. Malformed bytes, changed owner/generation or storage failures never authorize B/foreign cleanup.
5. Only then apply the existing obsolete-operation check and active-form reset. A late A ACK must not blank B or mutate B journal. Local cleanup failure/obsolete form result is not a server DELETE rejection.

G3 cleanup touches only its matching family. It does not add an owner-level wipe, reset G2, retire other UUID families or certify complete historical raw-checkmark erasure. Existing native legacy-mark behavior is not broadened in this increment.

## 5. Today → exact LearningTaskRef → native dispatcher

The server already supplies `TodayCardV1.target`, `actionable`, date certainty, dependency reasons and workload origin. Use those fields, rather than inferred title/ID/selected programme. A personal target routes to Documents/Applications and focuses that exact owned record after its own GET; missing record stays unavailable.

For a lesson/review click:

- Only an actionable server card with `kind=lesson` or `attempt_review` is dispatched. Copy the **complete native LearningTaskRef** plus captured owner/profile/epoch and a one-use navigation nonce into App transient state. Assessment/external_resource/null/unsupported refs do not become lessons.
- Verify the tuple before navigation, when PreparationCase consumes it and after native I/O. Honor the existing leave guard; if navigation is refused, do not issue lesson/review I/O. Clear stale handoffs on switch-start, owner change, new case, route replacement or unmount. StrictMode/locale/render retries cannot consume one nonce twice.
- Lessons call the existing dispatcher with `lesson_id + content_version`; no bare ID/latest catalogue fallback. Fresh preparation access is still required. Loading/access failure retains an exact explicit retry target; it never counts as opened/submitted.
- Reviews call `preparationAttemptReview(profileId,attempt_id)` with the pinned lesson/version expectation, without looking in recent20 or substituting current material. Saved review access remains independent of new-practice subscription. A catalogue/progress read failure must not swallow a valid direct own review: use the existing exact review loader/renderer outside the catalogue-dependent wrapper for this handoff, with its own error/retry state.
- Do not mark an attempt, tick a plan, allocate time, fetch latest material or submit answers as a navigation effect.

Today keeps `component_reads/mixed_revision`, action/read timestamps, needs_refresh, selected origin/revision, date/timezone uncertainty and notices visible. No zero-minute fallback, merged G2+legacy budget or personal-time estimate. Preserve the backend's section/slot ordering; do not reorder study actions by a current catalogue. No GET backfill or automatic selector write.

## 6. Recovery, explicit retry and the cap64 retention control

Save flow is: explicitly review fields → freeze original UUID/body/CAS/source token → `journalAdmissionsAction` succeeds → mark that existing intent sending → one native POST. No successful journal/index write means no dispatch. Hydration, restore, GET failure or source refresh never automatically POST.

After a matching own native 200 receipt, keep an observed remote-ACK/reference in **transient owner-bound state before local retirement**. Call the single foundation ACK-check/persistence path; local cleanup/storage failure is a separate notice, never “not saved” or an invitation to resend a known accepted UUID. If strict ACK validation is needed separately from storage, expose/reuse the existing foundation checker in the bounded helper grant; do not implement a second checker in the panel. A malformed/foreign receipt does not become known accepted. Owner replacement withholds the old receipt completely.

Unknown outcome retains original body and UUID. Manual `admissionsActionRetryBody` returns only that original command. Explicit reconciliation uses current head if it exactly matches the UUID/request, or own event endpoint when event ID is known; otherwise user-controlled paginated own history. Do not treat the latest unrelated event or a missing history page as proof of absence. Known ACK/current/history reads do not reallocate or reload premium proof. A409 marks the old intent conflict: reload/review then an explicit fresh UUID for changed input/CAS/preview, never mutate/retry the conflicted original automatically. Newer unsaved form edits survive an older ACK.

The foundation's cap is **64 local UUID entries**, including acknowledged entries, not a server/application cap. The necessary local retention extension must:

- show confirmed vs unresolved entries and an explicit “Remove this confirmed browser record” choice; explain server history stays;
- accept only explicitly selected, freshly verified acknowledged entries in the exact active own family/generation with captured raw/index expectations; never remove pending/not_sent/sending/uncertain/conflict or a newer draft;
- remove only those UUID entries and their corresponding advisory descriptors, using existing identity/readback/reconciliation primitives. No clear-all, arbitrary index keys, automatic eviction, orphan adoption or localStorage atomic-CAS claim;
- preserve siblings, new concurrent pending entries, other cases/owners, G2 and raw `docsDone` bytes. Changed/malformed/storage/index races remain a refusal or honest partial/residual-unknown result; explicit reconciliation is available, not a silent index reset;
- prove cap64 → explicit confirmed retirement → next new journal/dispatch succeeds, including storage refusal and concurrent pending insertion. All pending originals remain recoverable.

Browser legacy import remains explicit: literal-true candidates, unknown historical source/time, exact chosen own task mappings and preview. Bound mappings require current authorized exact source token; unbound personal import stays free. No name matching, automatic prepared state or raw mark deletion after import ACK. Refused >50-candidate snapshots remain untouched and are not silently truncated.

## 7. Finite meaningful controls before UI acceptance

These are proposed controls, **not executed or passing**:

| Control | Native source boundary to extend |
| --- | --- |
| Empty research/case result disappearance still shows durable own tasks/apps; current GET503 is unavailable, not an empty reset. | New `AdmissionsActionsPanel.test.tsx`; retained Approved/Documents empty paths. |
| Shared leave guard catches meaningful unsaved form, unknown/conflict intent and original retry; old token cleanup cannot clear a newer registration; security owner change unmounts immediately. | App existing guard / new panel tests, additive `App.preparation.test.tsx`. |
| Real captured DELETE A resolves while B active: only A tombstone; B/raw unrelated preserved; failed DELETE/owner replacement/wrong ACK/generation/storage refusal controls. | New `lib/store.admissionsActions.test.tsx` plus native Store/draftIdentity fixtures. This must call real Store action, not only the helper. |
| Real original POST reaches own backend, response is then dropped: reload has original UUID/body; explicit retry/exact own reconciliation yields one immutable server event and one state advance. | Add bounded Demo/Auth native journey controls, forwarding the real response before fault; no fabricated receipt. |
| A valid known remote ACK followed by local storage failure stays confirmed; newer form and sibling pending survive; no accepted-UUID automatic POST. | New panel controls plus existing recovery tests. |
| Cap64 full refuses dispatch; explicitly retire chosen acknowledged entries only; next request works; pending/new insertion/raw legacy/cross-case and partial storage controls. | Finite recovery-helper extension/test + new panel controls. |
| Same-name raw checklist entries preserve location/index before lead-time sort; stale rebind retains old report; locked source permits personal report/edit and reveals no new source/blocked raw URL. | New panel tests using actual typed API fixtures, retained Documents privacy controls. |
| Explicit submission/withdrawal/correction records applicant declaration and exact own prior event; source absence/expiry does not invent portal acknowledgment or change document reports. | New application-mode controls, own history pages. |
| Today old-version lesson and review outside20 dispatch exact refs once; no latest fallback; foreign/late A response withheld; declined navigation makes zero requests. | Add App + Preparation learning-path controls using existing version/UUID fixtures. |
| Direct review remains visible under catalogue failure/expired new-practice access; error retry keeps exact ref; no attempt POST on click. | Add native Preparation controls, independent handoff renderer. |
| Mixed/source/preparation/date uncertainty displays independently, no second budget or zero fallback; unsupported/null refs disabled. | New `TodayPanel.test.tsx` with backend-projected DTOs. |
| EN/RU/kk all new keys/states/actions, real locale switch; keyboard and320px no overflow, visible focus/44px targets, long IDs/notes/URLs, dropdown and disclosure flows. | Finite i18n tests, scoped styles, later saved native screenshots and browser controls. |

Preserve existing native assertions, fixtures, owner/HTTP policy and historical skips; no guard/floor/timeout/provider expansion belongs to UI work.

## 8. Scoped RU / EN / KZ and320px flow

Use `kk` internally, existing locale selector and dictionary fallback. Translate only finite new G3 headings, form labels, confirmation/error/recovery/dependency/uncertainty states and actions through the new dictionary merge; untranslated legacy screens are not claimed translated. Suggested user-facing concepts are “your report / reported submission”, “source needs review”, “date only; timezone unknown”, “original request”, “server confirmation; browser cleanup failed”, and “confirmed browser record; server history remains”. No admission-ready, official-submitted, probability or mastering language.

320px layout is a single column: Today → Applications/Documents actions → bounded expandable details/history → explicit recovery controls. Use fieldsets/legends and associated labels; dates/timezones retain precision, buttons wrap, source/digest details use overflow-wrap, and history is paginated. Expanding a form/ref changes no saved state. Respect reduced motion and focus an exact target/error after navigation. Desktop alignment reuses existing Panel/Notice/Chip, not another design system.

## 9. Actual gaps to keep explicit and implementation order

1. Original foundation F1–F4 are recorded at `G3_FRONTEND_FOUNDATION_INDEPENDENT_REVIEW1.md`, SHA256 `916c697cfb464b33b2d66e5d50298835080fdb0f1a6fd88e374723fbaad33657`. Await its separately qualified repair/application; this plan does not claim fixes.
2. Explicit acknowledged-entry retirement is absent from that original helper. Root must grant the narrow helper/test extension before screens claim confirmed-entry capacity management. A family containing64 unresolved entries still refuses new journal/dispatch; this plan does not authorize discarding those originals or claim unlimited capacity. No new backend schema is necessary.
3. Current Preparation renderer is catalogue-dependent; direct review handoff needs the finite independent-rendering connection described above.
4. Current Today exposes a native head only for its selected/derived origin. Existing legacy GETs do not directly expose every G3 digest needed for an alternative selector head. Initial screen scope displays the supplied active plan and exact targets; it must not invent a legacy head or add an endpoint. Alternative-origin selection can appear only if root supplies an existing exact server head seam; this is not a prerequisite for own tasks/apps/Today reads.

Bounded order after root grants source: qualified foundation → shared panel/recovery/retention + Store ACK wiring → Applications/Documents → Today + App exact handoff/Preparation rendering → finite messages/styles → source-bound native static/component/native journey and320px evidence. Root controls the exact path/preimage grant and runtime binding; these are dependency steps within one screen slice, not a full product roadmap.

No application source, runtime, imports, AST, formatting, tests, Git, HANDOFF, network/provider, labels or stopped experiment was touched for this plan. Only this external Markdown and its metadata seal are authored. No implementation, full-product/search readiness, release, hosted CI, deployment, university submission or learner outcome is asserted.

