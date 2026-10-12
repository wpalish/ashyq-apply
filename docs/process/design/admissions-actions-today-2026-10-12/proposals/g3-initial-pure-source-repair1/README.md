# G3 initial pure source — finite repair1

2026-10-12 · EXTERNAL PROPOSAL ONLY · NOT_APPLIED / NOT_IMPORTED / NOT_RUN / NOT_ACCEPTED

## Authority and immutable predecessor

Root is the sole application writer. This packet proposes exactly the three new source paths granted by G3_INITIAL_PURE_REPAIR1_GRANT.json, SHA-256 `3d61dedea4c2aa31204eade4fc928b74854dc1bfca06a6f8d2e3481dc9a22624`. Root review1 is `db3c75f8ff8be0fb2c73a3f1618a19f08ce5decd19da917830b02e105249ca68`.

The original authored packet and all nine members remain immutable. Its SEAL.json is `41a34f0226609b0710a83135b815f0b35ef873096296b2bfd50478731544b1e1`. This repair preserves complete copies of the original three source postimages under `original/`; every diff is relative to those postimages, not an invented application preimage. All three application paths are still ABSENT at seal time.

All eight accepted frozen design pins and the ninth root implementation disposition remain unchanged and are recorded in this SEAL. The original 17 ordinary native source pins were rechecked without imports or runtime. Provider/model/quota/security/reset/live/expert/held-out/controller STOPs are unchanged.

## Exact finite changes

### 1. Native UUID equivalence

The exact hyphenated parser now accepts upper- or lowercase A–F, returning the native canonical UUID value. It still rejects shorthand, non-hyphenated spelling, whitespace and malformed characters; revision and confirmation coercions remain forbidden.

The demonstrated incorrect uppercase-negative case is replaced by a genuinely non-hyphenated UUID negative. The new synthetic control checks equal typed intent, canonical lowercase JSON spelling, an independently reconstructed literal request digest, equal pure accepted transitions and original receipt replay for both spellings. No storage/replay endpoint result is claimed.

Control: `test_native_uppercase_uuid_is_the_same_canonical_intent_digest_and_original_replay`.

### 2. Embedded decoded sensitive key=value

Sensitive key=value matching no longer requires a segment-start or ;/& delimiter. Plain `prefix-token=PRIVATE`, encoded key, encoded equals and combined one-pass forms are blocked. The raw-authority check, exact original proof identity, one decoding pass, current-source authorization envelope and fixed safe output are unchanged. There is no SourceLink/global URL policy edit, DNS lookup or destination verification.

Added negative link literals preserve the entire old list. New controls check that the exact raw literal still changes proof reference identity without changing item semantics; the literal appears in neither the action href nor immutable ACK. A tampered actionable DTO is also rejected. The existing at-most-one decoding rule remains explicit; no recursive URL repair is introduced.

Controls: expanded `test_blocked_links_emit_no_raw_literal_or_clickable_fallback`; `test_embedded_token_literals_affect_original_proof_but_never_action_href_or_ack`.

### 3. Correction after a prior planning correction

A supplied prior receipt is fully revalidated, including raw finite values, exact request/delta/actor/event/self-hash checks. The correction relationship uses its exact affected application and applied application record, rather than assuming every accepted correction has a submission/withdrawal body. A prior correction to planning legitimately has a null declaration body and remains correctable.

The new control creates a real pure submission, an accepted correction to planning and a later correction referencing that exact own receipt. It checks applicant-declared/not_performed provenance, a subsequent explicit correction of that same earlier own reference under the current CAS, unchanged original receipts and the complete predecessor-bound export chain. Current application records retain only their original three reference roles; no embedded last-submission or last-withdrawal record is added.

Control: `test_a_prior_own_planning_correction_can_itself_be_corrected_without_rewriting_history`.

### 4. Missing/foreign versus wrong-own relationship versus corruption

A missing receipt or valid foreign receipt produces the fixed404 record_not_found. A fully valid same-profile receipt that concerns a different existing own application produces fixed422 invalid_transition. A malformed saved receipt, mismatched self-hash or raw forged nonfinite receipt produces fixed503 saved_unreadable, without raw input or private note echo. A caller still has to establish current ownership and load the exact own receipt; supplied context itself is not authority.

Controls: `test_correction_distinguishes_a_wrong_own_application_from_missing_or_foreign_receipts`; `test_corrupted_saved_prior_correction_receipts_are_safe_503_not_client_errors`.

## Preservation and check boundary

All original42 test function names remain. Source-AST comparison found only the two authorized original control changes: the incorrect UUID negative replacement, and additional cases in the old blocked-link parameter list. Apart from that UUID test body, every original test body remains identical at AST level. Five new test functions were appended among the related controls. There are47 proposed source test functions /110 literal parameterized cases, counted from syntax only, NOT_COLLECTED and NOT_RUN.

All three source files were parsed with stdlib AST for grammar only. They have not been imported, formatted, linted, typechecked or executed. The first packet is unchanged; no application, Git, HANDOFF, lab, helper, runtime, database, network or browser mutation occurred.

## Remaining independent findings — outside this repair grant

The separately sealed first-packet independent review (`32c16500421ea9e551ab687bcc89d3509d8f9dfcebf98765cabe578cd90d4b10`) additionally reports F5 personal-task receipt binding closure and F6 global stable-ID personal Today ordering. Those are pending root disposition. They are intentionally not changed by this four-fix grant and are not asserted resolved, accepted or executed. This package is not an application-readiness or product-completion claim.

## Source pins

| Proposed relative path | Original authored postimage SHA-256 | Repair postimage SHA-256 | Lines |
| --- | --- | --- | --- |
| `backend/app/schemas/admissions_actions.py` | `336b600dde899dce003558d531c0a432ceb748f3ead9d88cc9f74d97205d504d` | `67b2096466b68377053411a00991f64ea6754b3ef543708ac38d0b6e8b302629` | 1151 |
| `backend/app/domain/admissions_actions.py` | `be6b2836bea9c31d68380a4484ab11588ac28e2a4897e8a79fd2188313e4ba86` | `6f71564468662fc1a34edba39bb5083abddd8953f5f6eb5e780dba6d0bf32585` | 729 |
| `backend/tests/test_admissions_actions.py` | `ccd8186c4ec971f013ddbf192ba82d1e09e66346a0a31303cc1dd76e4be61896` | `cc5c5fac0aced12e8c67345bed012d9079fa79febd9f4c2088422e49e0ae2baa` | 748 |

## Members and next owner step

`files/` contains the exact three proposed full postimages. `original/` contains their exact predecessor copies. `diffs/` contains three narrow original-to-repair diffs. PREIMAGES.json and SEAL.json record the actual ABSENT application paths separately from external predecessor hashes. This README and all listed members are immutable after seal.

Root and the independent reviewer can now read the complete authored snapshot. Source acceptance, application copying, wiring, static/focused gates and any further repair require their own finite root step. Model/API/migration/frontend, ownership/transaction/export/delete integration and production remain outside this initial pure proposal.
