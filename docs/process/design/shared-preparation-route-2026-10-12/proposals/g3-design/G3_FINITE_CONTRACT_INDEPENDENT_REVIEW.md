# G3 finite contract: independent design review

**2026-10-12 · READ ONLY · DESIGN ONLY · NOT APPLIED / NOT RUN**

Reviewed the immutable `G3_FINITE_CONTRACT_FREEZE_PROPOSAL.md` at SHA-256 `f5acdae226110346798aca2ab8e51a40894e902adc5e2d4eb71b5c85740d839a` and its receipt at `501ff63c1f54cfd94149738c562e84e1aba17239088e46b02112a45ca264cf9c`. Native source was read only under `work/unimatch-calendar-materials`; no application or test was imported or executed. This is a contract review, not implementation qualification.

## Finding F1 — freeze the exact EventRefV1 before source work

Section 5 correctly excludes `receipt_digest` from the hashed current state to avoid `state_digest → head receipt_digest → after_state_digest → state_digest`. The same section then says each referenced event must match its `receipt digest`, including the head among at most 1,662 references, but it does not define the typed event-reference fields or distinguish a newly created head from earlier events. A future implementation could inadvertently embed the head receipt digest in `CaseActionsStateV1`, recreate the cycle, or skip an intended reference check.

Define `EventRefV1` exactly. One safe choice is to store `{event_id, revision, kind}` in every state reference; verify the head against its separately loaded, fully hashed receipt and verify earlier refs against bounded own event metadata plus each stored self-digest. If an earlier reference carries `receipt_digest`, use separate prior/head reference variants and explicitly prohibit the head digest in the state. State hash input and metadata comparison fields should be enumerated in that contract. Keep the full old receipt check on its own history/export read, as proposed; a metadata-only current check must not be described as full old receipt validation.

**Disposition:** open design clarification, before bounded G3 schema/source write-ahead. The proposed current/head integrity rule is sound once this reference shape is fixed.

## Other checked boundaries

- **Actor and erasure:** Native `Principal` supplies full user and organization IDs; `AuditEvent.actor` uses only an eight-character prefix. The proposed server-derived full-ID digest therefore avoids treating an audit display tag as unique identity. The replay rule preserves the original accepted actor for the same owned UUID/body. Native `routes_account.py` retains shared workspaces on one member's deletion and removes sole-member workspaces/cases in one guarded erase; a case-owned G3 row without User FK fits those effects. It must remain described as a correlatable pseudonym in retained shared history, not anonymous or attributed to the physical applicant.
- **Authority and replay:** `begin_fresh_preparation_write` and `lock_owned_preparation_profile` establish a fresh write transaction, parent/case lock, active user and membership checks. The proposal's own-case authority before UUID lookup, then exact UUID replay before mutable policy, is consistent with that seam. A deleted/unowned member cannot obtain a retained receipt by UUID alone.
- **Links:** The separate G3 lexical rule, with no network fetch or global `SourceLink` change, is conservative. A raw-authority ASCII check should happen **before** URL-parser host normalization; otherwise a Unicode hostname may be silently punycoded and pass an “ASCII authority” test unintentionally. Punycode is explicitly permitted, so this is an implementation precision point rather than a new policy requirement. Locked-source presentation must retain the fixed envelope without URL-presence, block-reason or proof-hash leakage.
- **Errors and reads:** Fixed G3 detail codes/messages and a route-local validation wrapper leave native 401/404, billing and G2 handlers intact. The stated current/head self-hash checks, bounded own metadata batches (1,662 refs, chunks of 200, at most 9), paginated history and complete export are finite. Current reads validate referenced metadata but do not claim to validate every old receipt; history/export supply the stronger validation. The proposal correctly treats source/plan unavailability as a typed observation rather than deleting personal actions or repairing a saved head.

No additional concrete design defect was found in these inspected boundaries. No PASS is assigned to G3 source, migration, UI or runtime; G3 is still design only.
