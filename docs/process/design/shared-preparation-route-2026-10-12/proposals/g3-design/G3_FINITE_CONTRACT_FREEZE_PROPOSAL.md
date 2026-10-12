# G3 finite contract freeze proposal

**2026-10-12 · DESIGN_ONLY · PROPOSED_FOR_ROOT_REVIEW · NOT_APPLIED / NOT_IMPORTED / NOT_RUN**

Separate proposal closing the four still-open implementation seams in accepted G3 V2 and its final-v2 native binding addendum. Existing accepted design/map/addendum/receipts remain unchanged. This is neither G3 implementation approval nor code, runtime, deployment, search-quality or full-product acceptance. Root is the sole application/source/Git/HANDOFF/runtime writer. No app import, tests, network, providers, auth data, closed labels or stopped workflow was used.

Pinned source root: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials`. External stage: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12`. Source/design hashes were read at **2026-10-12 03:39:14 UTC**; these are read-only observations, not a release receipt. G2 runtime outcomes were reported by root, not independently run here.

## 1. Findings and proposed closure

| Gap | Actual contract/source finding | Proposed finite closure |
| --- | --- | --- |
| Actor identity | V2 §2/§3 requires trusted reporting-principal attribution, but does not prescribe full UserID persistence. Native Principal has full user/org IDs; native AuditEvent.actor uses a nonunique eight-character UserID prefix. Tenant authority is org membership, not proof the physical student made the report. | Server-derived versioned actor_ref_digest over full native user_id + organization_id; pseudonymous display only; no User FK, name/email copy or new AuditEvent. Preserve original actor on immutable replay. |
| Action links | V2 §8 requires public absolute links without private credentials/tokens. Native isSafeHref only checks http/https; it currently accepts credential, private/local and query-bearing forms. | A separate G3 lexical action-link policy; global SourceLink unchanged. Rejected literal is never an href or automatically parsed out of notes, but remains exact proof identity when authorized. No destination verification. |
| Errors | V2/final-v2 defers exact error mapping. Native ApiError already parses detail.code + detail.message; native profile401/404 and billing contracts exist. | Fixed G3 error dictionary, route-local validation privacy, no prices/premium payload or new payment flow. Native owner and existing preparation/billing routes unchanged. |
| Current/event binding | V2 pins atomic current + event and UUID/CAS, but not the typed state, head linkage or corrupt-read behavior. Native G2 validates typed receipt/row metadata and current/latest head before reading source. | Versioned finite-JSON state/request/receipt hashes; current state bound to one exact owned head event, with row/receipt metadata and inner invariants validated. GET never repairs/reallocates; current/head disagreement503. |

No additional owner/product decision is required to propose these conservative defaults. Root must accept or replace this proposal before its future bounded G3 source write-ahead. The four findings are design gaps, not newly implemented defects.

## 2. Reporting actor: exact server binding, not a human-name claim

### ActorRefV1

Freeze the response/event field as:

- schema_version: literal **g3-actor-reference-v1**;
- actor_kind: **authenticated_principal | local_development**;
- actor_ref_digest: 64 lowercase hexadecimal SHA-256 characters.

The digest input is exactly the canonical finite JSON object `{schema_version:"g3-actor-reference-v1", user_id:Principal.user_id, organization_id:Principal.organization_id}`: deterministic sorted keys, compact separators, UTF-8, ensure_ascii=false, allow_nan=false. Use the full exact stable native identifiers; no slicing, email lookup, ID spelling inference or ad hoc normalization. actor_kind is separately server selected from Principal.local_development and bound by the enclosing receipt hash.

Full user/org IDs are used in server memory for this derivation. New G3 state/events/ACKs do not copy those raw actor IDs, email, display_name, role or account credentials. Existing native records/FKs are not changed. This deterministic digest is a **pseudonymous, correlatable reference**, not anonymization, a signature, a unique person name or official applicant identity.

Native source: security.py:27–34,191–239; api/tenancy.py:12–24; models/research.py:209–229; routes_profile.py:461–468. Existing AuditEvent.actor `user:<first8>` may remain a native display tag but cannot identify a G3 reporting principal. Do not create an AuditEvent just to supply G3 attribution: the immutable case event already records the actor and adding an org FK would add unnecessary locking/erasure work.

### Acceptance, replay and display

1. Derive the actor only from the current native Principal after the fresh own-case/user/membership fence. Client actor fields are not accepted. The responsible_actor of a task (applicant/school/referee) is independent of the authenticated reporting actor.
2. G3 retains native authority: currently authorized organization members can act on an own case. UI says **“Reported by a workspace member · <digest prefix>”**, or **“Local development report”**. A shortened digest is a display reference only; equality/audit uses the full digest. Do not label this the student's name or claim the school/referee authenticated.
3. Canonical request identity contains the complete typed client intent and case/schema/UUID/revision, not newly derived actor fields. ActorRefV1 is included in the accepted receipt and its self-hash.
4. Same case UUID + same typed intent returns the original persisted receipt/actor after owner authorization, including when another currently authorized member replays it. Do not rewrite an actor, accepted time or receipt hash from the viewing/retrying Principal. Different intent remains409.
5. Personal observation, submission declaration and correction have the same provenance rule. Submission always remains applicant_declared_submission / receipt_origin=applicant / official_verification=not_performed, even if the member reports a portal receipt.

### Erasure and retention

New G3 rows remain case-owned FK/cascade records, with **no User FK** and no live actor-account lookup during read/history/export. Case deletion and confirmed sole-member account/workspace deletion remove that case's G3 rows. Native shared-member account deletion preserves the shared workspace/cases; the immutable pseudonymous actor reference remains with that case's history, without reconstructing a deleted user's identity. This follows routes_account.py:387–455, rather than deleting another member's case history.

Do not promise anonymous retained history, erasure of every shared-case actor reference or continued retention of the organization-scoped native audit. A later owner request for named attribution or selective removal of a retained shared-case pseudonym would require a separate privacy/immutable-history design; it is not needed for this bounded stage.

## 3. G3 action links: conservative lexical policy only

Keep native primitives.tsx:123–154 and global SourceLink behavior byte-compatible. Add the following policy only to G3/Today action-link projection and new explicitly typed G3 entered-link inputs, if such inputs are included in the later command schema. Do not introduce a new URL command, parse note text into links, normalize source proof or follow any URL.

### ActionLinkReadV1 projection

Use role **programme_information | requirements_information | applicant_entered_external**, provenance **current_source | applicant_entered | demo | unknown**, destination_verification literal **not_performed**, state **actionable_unverified | blocked | demo_text | not_available**, href nullable and a fixed safe reason. Official-info provenance requires the existing current authorized exact source scope/proof; merely matching a university hostname or a legacy saved ref does not set it.

An actionable link is informational. None of these roles is official_submission_portal, authenticated recipient, a completed submission or a verified live destination. Click performs only normal browser navigation; no autofill, request, portal authentication, upload, payment or declaration is triggered.

### Exact lexical allow rule

All conditions must pass; otherwise no href is emitted:

1. Nonempty original string ≤2,000 characters; no leading/trailing or embedded whitespace, ASCII control, DEL, backslash; literal absolute `http://` or `https://` prefix, case-insensitive. No base URL, silent trimming or repaired-relative form.
2. Parse as an absolute web URL. Reject username/password and any percent escape in the raw authority. Scheme must be http/https. Reject any query marker or fragment marker, including empty ?/#. Do not strip them into an apparently equivalent allowed URL.
3. Authority must be an ASCII DNS-style hostname with at least two nonempty labels; labels contain only ASCII letters/digits/hyphen and do not begin/end with hyphen; final label contains at least one letter. Reject a terminal dot, IP literals (including parser-normalized IPv4 numeric forms and IPv6), single-label names and non-default ports. Explicit default http80/https443 is allowed.
4. Reject localhost and the product deny suffixes .localhost, .local, .internal, .lan, .home, .test, .invalid, .example, .onion. This is a conservative local UI denylist, not a DNS/public-network certification or an assertion that every other domain is public.
5. Reject path segments, case-insensitively after at most one percent-decoding pass, equal to login, signin, sign-in, auth, oauth, callback, logout, session, password, reset, reset-password, verify, verification, invite, invitation, magic, magic-link, token, access_token, auth_token, api_key, apikey or secret. Reject malformed escapes, decoded control/backslash, encoded slash and embedded decoded key=value token forms for these names. Do not recursively decode or repair a blocked URL.
6. fixture:// is demo_text with no href. Every other unsupported scheme/form is blocked. Punycode ASCII hosts can pass the syntax rule but gain no trustworthy-host/official claim.

These rules intentionally block some legitimate public query/fragment/login-style pages. The UI should say **“This link form is not available as an action link; destination not verified.”** It does not say the page/site is absent or inaccessible. An arbitrary private/token path could still be indistinguishable from a public path lexically; this rule does not certify absence of secrets, DNS reachability, redirects or site access.

### Rejected literal and research locks

The exact raw recorded DocumentItem.source_url, including missing/None versus present value, still participates in the full proof/reference identity fixed by final-v2. Never hash a normalized/stripped clickable surrogate. A URL-only change remains proof_changed_item_same when item semantics match.

Rejected authoritative literal is not echoed into an href, copied to an immutable G3 ACK, logged in errors, or fed to SourceLink's literal fallback. Show a fixed blocked label and the already allowed own reference identity. Do not expose a possible private credential/token string as a fallback; an authorized user may already hold it in the native source record, but G3 does not copy it into action presentation.

Current source link/proof computation occurs only after the current owned target + research entitlement guard. A locked branch emits its fixed research_locked envelope and existing own accepted refs; it does not reveal a NEW URL, URL-presence flag, block reason, proof hash or source count. Applicant-entered links remain entered; a blocked new typed entered-link input gets the fixed422 invalid_link, without storing or echoing the rejected literal.

## 4. Typed error dictionary and response discipline

Freeze G3 errors as HTTPException.detail `{code:<constant>, message:<constant>}`. client.ts:104–134 already reads this shape. No SQL error text, pydantic input value, URL, source/award/task title, claim text, entitlement price/count or foreign identifier is included. Field paths, if used, come from a fixed G3 schema allowlist and contain no raw values.

Native get_principal401 **Authentication required.** and owned_profile404 **Applicant case not found** remain unchanged. Unknown/foreign G3 record IDs share404; owner validation always precedes UUID/record/source access. No global exception handler, ApiError or native billing contract is changed.

| HTTP / code | Fixed message / meaning |
| --- | --- |
|404 admissions_actions_record_not_found|Action record not found. Same result for missing/foreign application, task or event.|
|422 admissions_actions_input_invalid|Check the action request fields. Closed-body, finite JSON, ID/UUID/date/enum validation; no echoed input.|
|422 admissions_actions_target_not_selected|The target is not a currently selected result. Only after exact owned metadata; new rejected/undecided selection.|
|422 admissions_actions_invalid_transition|This action requires a reviewed declaration or correction. No arbitrary submitted/official status setter.|
|422 admissions_actions_limit_exceeded|The case action limit would be exceeded. New distinct-target/record cap, no hidden counts.|
|422 admissions_actions_invalid_link|This link form is not allowed for an action link. No URL echo.|
|422 admissions_actions_plan_unavailable|Select an existing saved preparation plan. A genuinely absent chosen native plan; no invented blank plan.|
|403 admissions_actions_source_locked|Current source details are unavailable for a new binding. Bind/rebind/exact new scholarship-source branch only; metadata-only admission target and existing personal actions are unaffected. No new payment route.|
|409 admissions_actions_revision_conflict|The case actions changed. Reload and review before saving.|
|409 admissions_actions_uuid_conflict|This request identifier already represents a different action.|
|409 admissions_actions_source_preview_stale|The source binding changed. Review a fresh source preview.|
|409 admissions_actions_plan_head_changed|The saved preparation plan changed. Review its current accepted head.|
|409 admissions_actions_legacy_import_changed|The captured legacy import inputs changed. Review the import again.|
|503 admissions_actions_saved_unreadable|Saved case actions could not be read safely. Current/head/event/inner-reference mismatch; no reset, repair or omission.|
|503 admissions_actions_source_unreadable|The current source binding could not be read safely. New-binding malformed authoritative source; existing personal read uses evidence_unknown instead.|
|503 admissions_actions_plan_unreadable|The selected saved plan could not be read safely. G2 current/history corruption or unavailable native read; preserve selected origin.|
|503 admissions_actions_write_unconfirmed|The action could not be confirmed. Keep the original request and retry. SQL/lock/unknown commit result after fresh owned UUID reconciliation.|
|503 admissions_actions_write_session_unavailable|The action requires a clean request session. Do not commit/discard unrelated pending auth/application mutations.|

Preserve the final-v2 native distinction: native malformed legacy plan422 maps to a fixed G3 plan-unavailable validation response for a new selector; a native unreadable G2/DB failure503 maps to plan_unreadable. Saved read/Today reports a typed unavailable component and retains personal actions instead of treating it as absent, clearing selection or deriving fallback. No G3 wrapper changes the native routes' status/body.

New G3 command body validation uses a **route-local** APIRoute wrapper in the future G3 route module, attached only to its own router. It catches RequestValidationError and emits the fixed422 input_invalid, because default framework validation can carry raw input in its JSON. Native route/global validation behavior stays intact. JSON/nonfinite handling, malformed structure and forbidden actor/official fields return that fixed message; no exception repr/SQL/URL forwarding. Do not catch native HTTPException or disguise a DB/auth failure as input validation.

Personal reads/writes/replay/history/selector/export remain free after preparation expiry/research lock. G3 adds no402, entitlement mutation, charge or quota use. Existing preparation lesson/attempt APIs keep their native402; G3 Today displays the separately observed permission. Existing CASE_FULL research access is a pure read.

A lost/network/503 response keeps the exact original UUID/body for identical retry. A reviewed revision/source/plan conflict preserves the draft; a changed intent uses a new UUID. A confirmed422 does not automatically retry;401/404 invalidates adoption and rechecks the owner/case. Error status is not permission to repair the saved head.

## 5. Current state, immutable receipt and event integrity

### Canonical envelopes (avoid a hash cycle)

Use versioned finite JSON for each new digest; sorted object keys/compact UTF-8 serialization, unchanged array order and scope omission, explicit nullable values, no NaN/infinity, no repr/coercion. Native G1/G2 and legacy fingerprints are consumed exactly, not redefined.

- **CaseActionsStateV1:** schema_version=admissions-actions-v1, profile_id, positive revision, head_event_id; the bounded typed applications/document_tasks and nullable exact active selector. It contains own personal data + original source/plan reference identities only, never dynamic current premium evidence. Each record has its stable server ID, creation event ref, latest mutation event ref, and applicable latest declaration/report/binding event refs.
- **state_digest:** SHA-256 of canonical `{schema_version:"g3-state-digest-v1", state:<complete typed CaseActionsStateV1>}`.
- **canonical_request_digest:** SHA-256 of canonical `{schema_version:"g3-action-request-digest-v1", profile_id:<own case>, request:<complete typed accepted command>}`. Request includes its literal schema, command kind, exact canonical client UUID, expected revision and all original payload/ref/confirmation fields. No actor/current source enrichment is added.
- **ActionWriteReceiptV1:** event_id/profile_id/schema/kind, revision/expected_revision, client_write_uuid, complete typed request + its digest, accepted UTC time, ActorRefV1, predecessor_event_id|null, before_state_digest|null, after_state_digest and the bounded typed personal/reference-only applied_delta/affected record refs. Submission delta keeps literal applicant_declared provenance. receipt_digest is SHA-256 of canonical `{schema_version:"g3-action-receipt-digest-v1", receipt:<all receipt fields except receipt_digest>}`.
- **Current row:** own profile PK/FK, revision/schema, typed state JSON, digest=state_digest, accepted updated_at. No receipt_digest is placed inside the hashed state, avoiding state↔receipt circular hashing.
- **Event row:** stable event ID + own profile FK, unique(profile_id,revision), unique(profile_id,client_write_uuid), full immutable safe receipt and duplicated revision/schema/kind/UUID/request_digest/receipt_digest/accepted_at metadata. No User FK; no premium current source or dynamic status.

Preallocate the event ID before constructing the state. First revision1 has expected0, predecessor=null and before_digest=null. Later revision N has expected N−1 and the exact prior accepted head event/state digest. No native row/fingerprint change, full-state replacement command, history-sized snapshot duplication in every ACK or new actor ledger is introduced.

### Read validation

1. Verify native owner. Observe own current + latest accepted event revision in one scalar/current metadata statement, following native G2 _current_row's anti-torn-head pattern. No current/no accepted event means genuine empty revision0. Any current-missing/history-present or current.revision != latest accepted revision is503, never empty/reset.
2. Validate finite typed state and its internal constraints before exposing it: IDs unique/bounded, exact profile everywhere; application target/purpose/award/intake immutable; task application refs resolve inside this case; source task/binding target belongs to its exact application or explicit case-personal origin; total current source target union≤20; report/status/selector literals and event-ref kinds/revisions valid. Explicit unknown scope/date/version stays unknown. not_needed_reported is not a waiver.
3. Load **one exact owned head event** (same profile/revision/head_event_id). Validate its full typed receipt and canonical request/self-hashes, metadata copies/UTC time, revision=expected+1, affected delta shape and declaration provenance. Require state_digest == row.digest == head.after_state_digest; current updated_at == head.accepted_at. The head request/row actor cannot be substituted from the viewer.
4. Validate references to earlier immutable events through bounded own metadata batches, not all history: application created/latest/status refs (≤3×20), task created/latest/report/binding refs (≤4×400), selector/head refs (≤2), total at most **1,662 distinct event refs**. Use chunks≤200 IDs (at most9 fixed batches) with the exact profile predicate so this does not assume a high SQLite bind-variable limit. Match profile/event ID/revision/kind/receipt digest, positive revision≤head; reject missing/foreign refs. These are internal personal event references, independent of the separate ≤20 G3 /≤20 G2 source-target budgets. No G1/source/history allocation is run. Full original declaration/correction payload is read only by its own history/event route or a command that needs that exact original declaration.
5. A history/event read validates that requested own row's complete receipt/hashes/metadata and its typed original refs, without rebuilding source, plan or the old current state. Paginated history20/default100/max is ordered; no truncation disguised as complete history.
6. Export returns all ordered own accepted receipts under the established owned export policy. Validate complete revision sequence1..N and reconcile the actually loaded current/head with loaded latest event before returning. An interleaving head change or malformed row yields safe503 rather than mixed complete export or omitted rows. No GET repair, DML or retry loop.

Current metadata presence alone does not authorize premium loading. Current personal state/receipt checks precede the per-target current-source guard and never copy locked evidence. GET/Today itself owns no DML; native authentication's existing session cleanup/last_seen commits (security.py:209–223) remain outside this new G3 read contract and are not incorrectly advertised as globally write-free.

This is consistency validation within the trusted database/transaction boundary, **not a signature against coherent malicious rewriting of both state and history**. Rehashing only the outer current JSON must not defeat the exact head/state and inner semantic checks. A current/head read is not a certification of every historical row: an unreferenced old-event gap is detected on that history read or the complete export. No retrospective history replay or cryptographic official-proof claim is introduced.

### New-command transaction

Use released begin_fresh_preparation_write + strong owned profile/member fence (preparation_transactions.py:22–107), with the same SQLite BEGIN IMMEDIATE / PostgreSQL READ COMMITTED + native bounded lock timeout. Own UUID receipt lookup precedes mutable current/source/plan/expiry checks; repeat it under the fresh fence before a new command. A valid old UUID receipt replays independently of current source/head availability; an unowned/deleted case never does.

For a new intent, validate expected current revision/head, appropriate personal versus new-source authority, exact source/plan preview and local date semantics; derive actor; apply the pure closed transition to a new state; atomically write current and one event. Event insert/flush/commit failure rolls back current and every related write. No profile.updated_at, score, quota, research, native G2 or legacy tick mutation.

CAS/create/unique loss rolls back the **whole** transaction, then fresh owned UUID reconciliation: equal intent returns original ACK, different intent uuid_conflict, absent event revision_conflict. SQL/lock/unknown failure that cannot be safely reconciled is write_unconfirmed. Do not infer absence from an unreadable event or commit a dirty incoming session.

Existing profile/account erasure lock order is preserved. New case-owned cascade records participate in the same transaction; no new late org/User FK, placeholder schedule row or separate AuditEvent is added by G3. Real migrated two-connection controls are a future source gate, not evidence provided by this design.

## 6. Bounded future controls (not authored or run)

| Control | Required result |
| --- | --- |
|Actor full-ID collision and role/name changes|Same eight-character prefix with different full user IDs gives different full actor_ref_digest; different org gives different digest; email/display-name/role changes do not rewrite old receipt. Truncated display equality does not grant authority.|
|Actor replay and deletion|Authorized member B replays A's same UUID/body and receives exact A receipt/actor; foreign/member-removed caller cannot. Case/sole-member account erases G3; shared-member deletion retains sibling case/ref-only history, no User FK lookup.|
|Link lexical matrix|Allowed public syntax has unverified informational label; credential/control/query/fragment/IP/numeric-IP/local suffix/nondefault port/private-path forms are nonclickable; no DNS/fetch. A blocked URL change still changes proof identity, without a href/raw private fallback. Locked source yields no new URL/presence/reason/hash.|
|Error shape/privacy|All proposed G3 errors use fixed code/message; malformed/forged actor/official fields do not echo raw values. Native401/404 and payment contracts unchanged. Existing personal command/read/replay is allowed after source disappearance/lock/term expiry.|
|Head and inner corruption|Missing current with history, wrong ID/revision/time/digest, absent/wrong own referenced event, malformed finite JSON, rehashed outer state with head mismatch and mismatched profile/task/binding fail safely503; no GET reset/DML/reallocation.|
|Atomicity/idempotence|Physical migrated file SQLite/private PostgreSQL two connections, present/absent head, same UUID and different UUID races, event failure rollback, lock timeout/release, fresh reconciliation and delete both orders; no mocked concurrency/PASS by inheritance.|
|Export mixed read|A real accepted write between current and ordered-event loading causes explicit head mismatch/unreadable, not mixed export; complete own receipts/counts and sibling erase retained.|
|Today/case navigation|One chosen native plan, original selector ACK versus new observed native head; typed exact LearningTaskRef with case/owner/epoch fences; no fallback/version inference/second budget or automatic declaration; personal records survive safe selected-plan/source failure.|

Future implementation stays inside the previously mapped G3 schema/domain/model/API/Today + bounded frontend link/DTO/client seams. No attachment, private draft, portal autofill, provider, payment, search, new course, new calendar/ledger or G2 allocator/receipt modification is authorized by this proposal.

## 7. Source and preserved design pins

Read-only references above use the following exact source bytes; re-pin against the released parent preimages before adoption. If root changes a file afterward, this proposal remains an observation of these bytes.

| Preserved external design | SHA-256 |
| --- | --- |
| `ROOT_G3_DESIGN_ACCEPTANCE.md` | `81fc914fd0756436ebd3974ad7847131e90c5e19b64121fb2733b5fd36d8f70d` |
| `proposals/g3-design/G3_CONTRACT_DESIGN_V2.md` | `7b3857d7a273e3bbb3b38644101a03fd41159bbc121b406b3a76ef929f3edbbb` |
| `proposals/g3-design/G3_IMPLEMENTATION_DEPENDENCY_MAP.md` | `81171a86f90c11e19438efe760ad9e0cd4fcbc394c036a3ec7f9bb1143537bdb` |
| `proposals/g3-design/G3_NATIVE_BINDING_ADDENDUM_FINAL_V2.md` | `0c15b69b2cdb9347a1f30501822aeff4cf913f3e12d08635bdd1d30a7b525474` |
| `proposals/g3-design/SEALED_G3_NATIVE_BINDING_ADDENDUM_FINAL_V2_RECEIPT.json` | `3fca6f1c32799611ca4bef624b0fa7a18eebc117c5542f2846790f28fab840f4` |

| Native source relative to pinned root | SHA-256 |
| --- | --- |
| `backend/app/security.py` | `e8359112da7f35d7952049ed3e01066e0b6f41cd051052f5654ac740458bc816` |
| `backend/app/api/tenancy.py` | `34557c1bae4f9cc36413cfd952a001342df9a35a1c5ecf5ad19bd83cf121363f` |
| `backend/app/models/research.py` | `03bc5f07438456d08e412ac2c0ed615464253a1a1bb9ecf3e548ff72d7aeef12` |
| `backend/app/models/base.py` | `dfab71868df728ce3dc74d01f9d547512eb8076795207e113425a1eb1b786b62` |
| `backend/app/api/preparation_transactions.py` | `ecbf9c12c95d6a178bf6d1c8c2aca8dcc3b5522e8b0aa4da64e465c99c68d2d7` |
| `backend/app/api/routes_profile.py` | `b12a3a301829cc4f4eed5d8df53c2315efa11e5fb0e05e3ba2d9ead25d5202a3` |
| `backend/app/api/routes_account.py` | `50c4bf6cc7da8d72596dd87c9acff858894a12fce441ea2273a3b6c460697521` |
| `backend/app/api/routes_shared_route.py` | `fec7d50d7e29cbebea1d1d46bb2245ccb129f216974ba281fd2550013bbe37f9` |
| `backend/app/models/shared_route.py` | `a1cf969acfde2dea68c42c98edd8ad99fa8ebc5b18633f6bf1bdbf0bc9ab8e20` |
| `backend/app/schemas/shared_route.py` | `50c2dca8ad250f3d12fc9645a6307ac4dd05bf05a61c79c17bbf925b4c8042e2` |
| `backend/app/payments/http.py` | `81994d3e620d8484bd52a341d682fe9bb9c247d43d408a40f62a5179e7bec3cd` |
| `backend/app/payments/entitlements.py` | `c866a0c548331d8fd7ae5487006dd29c03b89fbd0256183e703cb79bad21190f` |
| `frontend/src/components/primitives.tsx` | `ef745e6002023398e5d69f6e6227c719d879bc10997c94f179b15d67747a676b` |
| `frontend/src/lib/applicantStorage.ts` | `0a3230d223e5dbfc1ead6dbece478ce54c9ec6bc557493115716e5709818fd0e` |
| `frontend/src/api/client.ts` | `f667d2f3b89d64ea42392f9e5bba3a30d04a1a76b2203fa2b4a337a7a8cc6789` |
| `frontend/src/lib/store.tsx` | `5f7d2fd0c93c3125442aaa1f2e271748dc25528f39266603735270ec2b8343a3` |
| `frontend/src/App.tsx` | `5cd7408024f9732cfd661a78e3a8f2f45c01267117a6d50dee9b24a1f9328e26` |

**Root disposition requested:** accept these four finite design defaults or replace specific fields/error rules in a separate root decision. G3 remains DESIGN_ONLY/NOT_AUTHORIZED for source application until the G2 release and a new bounded write-ahead.
