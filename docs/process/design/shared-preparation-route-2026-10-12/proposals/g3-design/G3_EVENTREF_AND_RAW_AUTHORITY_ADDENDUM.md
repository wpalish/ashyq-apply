# G3 EventRef and raw-authority clarification

**2026-10-12 · DESIGN_ONLY · ROOT_DISPOSITION_CLARIFICATION · NOT_APPLIED / NOT_IMPORTED / NOT_RUN**

Separate finite clarification of F1 and the URL-normalization precision point in G3_FINITE_CONTRACT_INDEPENDENT_REVIEW.md. Root explicitly selected the three-field EventRef and raw-authority-first rule. This document preserves G3_FINITE_CONTRACT_FREEZE_PROPOSAL.md at f5acdae226110346798aca2ab8e51a40894e902adc5e2d4eb71b5c85740d839a and its receipt at 501ff63c1f54cfd94149738c562e84e1aba17239088e46b02112a45ca264cf9c. G3 remains design only until G2 release and a new bounded root source write-ahead.

Read-only predecessor/native pin comparison at **2026-10-12 04:07:00 UTC** found all 22 predecessor read pins plus f5/501 unchanged. Peer review SHA-256: 8f498fc30d8eeea447e8bcf5fe849f01bf46095c125feab24b5b9ba2000b3df7. These are file observations, not runtime, migration or product acceptance. No application/helper/Git/HANDOFF import, edit or execution; no network/provider/auth/closed-label work.

## 1. Exact EventRefV1 inside hashed state

Every event reference anywhere within CaseActionsStateV1 has exactly these three fields, with extra fields forbidden:

| Field | Exact meaning |
| --- | --- |
| event_id | The exact stable server-allocated G3 event identifier. No client-generated relationship or spelling inference. |
| revision | A positive integer no greater than the enclosing current revision; the referenced event's exact accepted revision. |
| kind | The exact accepted finite G3 command/event kind. It must also be allowed for that reference's role. |

The own profile is inherited from the enclosing state/record and enforced in every metadata query. No receipt_digest, request_digest, actor, source payload or old receipt body is embedded in EventRefV1. No older-versus-new-head variant is introduced. This applies equally to application creation/latest/status refs, task creation/latest/report/binding refs and selector refs. The root state still carries its prescribed head_event_id and revision; a redundant head EventRef, if exposed within the state, must obey the same three-field rule.

In particular, the newly accepted head can supply several references in the same transition, such as a task's creation/latest/report refs. All use the same preallocated event_id/revision/kind and contain no head receipt hash. Whether one command actually supports those mutations is determined by its closed transition, not by inventing a new multi-action command.

Kind is a typed discriminator from the accepted finite command union, including the separately accepted selector command. It is not an arbitrary string. A creation ref must be to a command that actually created that record; a report/status/binding/selector ref must be to the corresponding authorized transition; a latest ref must be to a command that actually mutated that record. Merely mentioning a task/application as context or a submission attachment reference does not authorize a mutation association.

## 2. Hash order and current/head validation

Acceptance has this order inside the existing atomic current/event transaction:

1. Allocate the new event_id and accepted revision after the owned UUID/CAS checks.
2. Apply the closed transition and put only three-field EventRefs into the new bounded state.
3. Compute state_digest over the complete canonical typed state under g3-state-digest-v1.
4. Build the reference-only receipt with after_state_digest equal to that digest, the existing exact predecessor/before digest, trusted original actor, request and applied delta.
5. Compute receipt_digest over all receipt fields except receipt_digest under g3-action-receipt-digest-v1; insert the event and current row atomically.

Thus state_digest never depends on receipt_digest. The receipt may depend on state_digest. No iterative hash, placeholder receipt hash or post-commit state rewrite is necessary.

A current read loads one full exact owned head receipt. It validates the complete typed request/receipt/self-hashes, copied row metadata and accepted UTC time, then requires:

- current.head_event_id == head.event_id;
- current.revision == head.revision == state.revision, with exact own profile throughout;
- recomputed state_digest == current.digest == head.after_state_digest;
- current.updated_at == head.accepted_at.

Any current/head/inner-reference disagreement follows the existing fixed503 admissions_actions_saved_unreadable rule, with no repair, reset, omitted records or GET DML. The head receipt's own hash is validated separately; no state EventRef needs its digest. Own UUID replay validates that original full accepted receipt independently of mutable current source or plan availability.

## 3. Bounded older-reference metadata and record association

Replace the ambiguous f5 §5 read step4 phrase “match … receipt digest” with: **match exact own event ID/revision/kind and the applicable affected-record association**. There is no digest in a state EventRef to compare with the event metadata. Metadata-only reads do not validate an older receipt body or recompute its self-hash.

One narrow metadata header is required so an otherwise valid own event cannot be reused as another record's creation/report/binding ref. Freeze EventAffectedRefsV1 as an exact closed object:

| Field | Bound and meaning |
| --- | --- |
| application_ids | Ordered unique exact application IDs actually created or mutated by the accepted delta; at most20. |
| document_task_ids | Ordered unique exact task IDs actually created or mutated by the accepted delta; at most400. |
| active_selector_changed | Boolean true only when that event actually creates/replaces the accepted active selector. |

The arrays follow the server-applied delta's record order, deduplicated by first occurrence. This header is derived only from the closed server transition; clients cannot post or override it. It is the same affected_refs object inside the full receipt and duplicated as a finite metadata column on the existing proposed G3 event row. No third table, extra audit row, per-record history ledger, premium body or new source read is introduced. The existing stricter command cap, including at most50 explicit legacy import mappings, remains intact.

A full head/history/event/export validation checks this copied header equals the typed receipt's affected_refs and the affected record set derived from its applied_delta, including permitted kind/role associations. An older metadata-only current check validates its own schema/header shape and exact profile/ID/revision/kind, then requires the relevant application/task ID in the appropriate header array, or active_selector_changed=true for a selector ref. Head linkage is checked by §2 rather than by a fabricated record membership. Unknown, foreign, missing, wrong-role or wrong-associated metadata fails safely503. No full old body is loaded to make this association check.

Current reads still examine at most 1,662 distinct state refs: applications≤3×20, tasks≤4×400, selector/head≤2. Metadata chunks contain at most200 exact own event IDs, at most9 bounded batches; the already fully loaded head need not be read again. Profile filtering and native parameter limits are retained. These personal event bounds remain separate from the ≤20 G3 and ≤20 selected G2 source targets, composite Today≤40 reference IDs. No all-history scan, current-source comparison or allocator runs in this check.

This validates old reference metadata within the trusted database/transaction boundary. It does **not** certify that every older full receipt was checked, that its stored receipt_digest was recomputed, that an unreferenced old history gap was detected, or that coherent malicious database rewrites are prevented. Own history/event reads, an exact prior-declaration correction command and complete export perform the separately required full receipt validation. None upgrades applicant-declared submission to an official receipt.

## 4. Raw ASCII authority before parser normalization

This changes only the ordering precision of the already proposed G3 lexical policy in f5 §3. It does not change global SourceLink/isSafeHref (native primitives.tsx:123–154), source proof identity, link roles or any destination-verification promise.

After the existing original-string length/control/whitespace/backslash and literal http(s):// checks, isolate the **original raw authority** between the literal scheme delimiter and the first /, ? or #. Before invoking a URL parser or inspecting a parser-normalized hostname:

1. Reject empty authority, raw username/credential marker @, every percent escape in authority, non-ASCII code points, controls/whitespace and backslash.
2. Validate the original raw hostname using the existing ASCII DNS-label rule. Reject Unicode letters or dot lookalikes, terminal dots, single labels, IP/IPv6/numeric-IP forms and disallowed port syntax; only the already permitted literal default port form remains allowed.
3. Only after those raw checks use the parser as an additional absolute-http(s) validation, retaining all existing query/fragment, local suffix and one-pass path/token exclusions. Parser normalization never repairs a failed raw check.

For example, raw https://例子.cn/ is blocked; literal ASCII https://xn--fsqu00a.cn/ can pass the hostname syntax rule if all other checks pass, with destination_verification=not_performed. This is not a claim that either domain exists, is public, is safe, is a university or is an official portal. No DNS/fetch/redirect check is made.

The exact original recorded source_url absent/present value remains proof identity. Do not replace it with the parser hostname, normalized path, stripped query, punycode conversion or clickable surrogate. A blocked authoritative literal is not an href or raw private fallback. A research-locked branch still emits no newly computed URL-presence/block-reason/proof-digest metadata. No previously accepted safe ref is rewritten.

## 5. Required future controls; none authored or run here

| Control | Required result |
| --- | --- |
| Same-head references | A legitimate closed transition's created/latest/report refs can point to the new head using only ID/revision/kind; hashes can be computed once in the specified order. Extra receipt_digest in any state ref is rejected. |
| Own event is for another record | Correct own ID/revision/kind but missing applicable application/task/selector association fails503. Mere mention in a submission request is not an affected mutation. |
| Older metadata versus full receipt | Current read uses only bounded metadata and does not deserialize older bodies or claim old self-hash validation. On full history/export read, copied affected_refs or receipt-body/hash disagreement fails503. |
| Head/foreign/kind corruption | Wrong head ID/revision/digest/time, foreign/missing older ref or role-incompatible kind fails without DML, silent reset, current enrichment or allocator invocation. |
| Metadata bounds | At-cap20 applications/400 tasks stay within1,662 refs, chunks≤200/max9; no unbounded history load. Source-target and command/import caps remain separate. |
| Raw host precision | Unicode host/dot lookalike or percent authority is nonclickable before parser normalization; literal ASCII punycode only receives the unverified informational state. Credentials/query/fragment and the existing deny rules remain blocked. |
| Proof/lock privacy | A raw URL-only change still changes exact proof identity; blocked literal is not echoed into href/error/ACK/private fallback. A locked source exposes no new URL/presence/reason/hash. |

**Disposition:** the root-selected three-field EventRef and raw-authority order close the two identified ambiguities. The finite affected_refs metadata column is the explicit required implementation seam for root to freeze before future source sealing; it is not an applied migration or existing G3 model. Previous accepted V2/map/final-v2/f5/receipts and all native source bytes remain unchanged.

