# G3 pure repair1: finite independent review

2026-10-12 · **SOURCE_ONLY / FOUR_SOURCE_FINDINGS_CLOSED / TWO_PENDING / NOT_APPLIED / NOT_IMPORTED / NOT_RUN**

## Boundary and verification

Reviewed only source1-relative repair1 deltas and preservation of the original controls, after all **11** declared member hashes matched its SEAL.json. Repair1 seal SHA-256: `f19f2c775ed89ad4f8d9beee5d50c6717f9ead2c912d8f702dbfe41422fe187f`.

Packet: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-initial-pure-source-repair1`.

Original independent report remains unchanged at SHA `32c16500421ea9e551ab687bcc89d3509d8f9dfcebf98765cabe578cd90d4b10`, seal `526de37b1b1eb3612269ff67749de6b5b49aefc1aa160c2640129c10b108c00f`. Its 42-group independent oracle/accepted design basis and deferred D01–D06 boundaries remain authoritative; no oracle was rewritten to fit this repair. Original packet seal: `41a34f0226609b0710a83135b815f0b35ef873096296b2bfd50478731544b1e1`.

The root four-fix grant was read and hash-matched: G3_INITIAL_PURE_REPAIR1_GRANT.json `3d61dedea4c2aa31204eade4fc928b74854dc1bfca06a6f8d2e3481dc9a22624`. Later root acceptance of F5/F6 is a separate repair2 step; this report does not claim those changes are in repair1.

| Repair1 postimage | SHA-256 |
| --- | --- |
| files/backend/app/schemas/admissions_actions.py | 67b2096466b68377053411a00991f64ea6754b3ef543708ac38d0b6e8b302629 |
| files/backend/app/domain/admissions_actions.py | 6f71564468662fc1a34edba39bb5083abddd8953f5f6eb5e780dba6d0bf32585 |
| files/backend/tests/test_admissions_actions.py | cc5c5fac0aced12e8c67345bed012d9079fa79febd9f4c2088422e49e0ae2baa |

## Four finite dispositions

Coordinates refer to the sealed repair1 postimages. **Closed means source-contract closure only; no test PASS is asserted.**

| Finding | Disposition and exact repair | Meaningful control present in test source |
| --- | --- | --- |
| F1 native canonical UUID | **CLOSED_SOURCE.** Schema:85–92 now accepts native uppercase/lowercase A–F and returns UUID. Hyphens/strict input and malformed alternative remain. | Tests:132–153 compare genuinely alphabetic upper/lower typed intents, canonical lowercase JSON, independently assembled literal request hash, accepted pure transitions and original receipt replay. Original wrong uppercase rejection is replaced by a non-hyphenated negative. |
| F2 re-correct planning correction | **CLOSED_SOURCE.** Domain:186–197 validates a supplied original saved receipt; :283–289 uses its exact affected/applied application rather than requiring a nested submission/withdrawal body. A prior planning correction's null declaration no longer rejects it. | Tests:260–284 construct submission→planning correction→submission correction, then another current-CAS correction referencing the same earlier accepted planning correction. Original receipts/export sequence remain unchanged; applicant declaration provenance remains not_performed. |
| F3 wrong own relationship | **CLOSED_SOURCE.** Domain:284–289 keeps missing/foreign/exact-ref mismatch404 separate from valid same-profile wrong-application422. Saved corruption revalidation has fixed503 before normal context normalization. | Tests:287–300 compare own A/B422 against generic missing/foreign404. :304–319 supply bad selfhash, affected association and forged nonfinite saved receipt; expected503 has no PRIVATE note echo. These are pure controls, not database owner/HTTP execution proof. |
| F4 embedded token key=value | **CLOSED_SOURCE.** Schema:1145–1148 removes the delimiter exception; decoded embedded sensitive key=value anywhere in a segment is blocked. Existing single decode/raw ASCII authority/ports/privacy checks remain unchanged. | Expanded old blocked-link cases include plain key, encoded key/equals and combined once-decoded forms. Tests:596–613 keep original literal in proof identity but outside item semantics and immutable ACK, reject href/tampered action DTO, and distinguish an exactly one-decoded string from recursive repair. No fetch or destination certification. |

No additional blocker was confirmed within these four deltas. Complete receipt semantic closure is still subject to F5 and later review; F2/F3's full typed receipt validation does not make an incomplete validator complete.

## Pending accepted findings

| Finding | Repair1 status |
| --- | --- |
| F5 personal-create receipt must forbid source binding/ref/origin | **NOT_CHANGED / PENDING_REPAIR2.** Schema's command-to-delta guard is unchanged; the original rehashed receipt counterexample remains. |
| F6 global stable personal Today/undated ordering | **NOT_CHANGED / PENDING_REPAIR2.** Document-first group construction and unsorted combined partitions are unchanged. Root separately selected target.id, then kind/card.id as the finite stable tie-break; native study-array order is to remain unchanged. |

Repair1 alone is **not** ready for acceptance/application of the complete initial pure slice. Root will provide a separately sealed repair2 for these exact remaining findings.

## Preservation and original42 controls

All three repair1 `original/` files are byte-identical to source1 `files/` (three cmp exits0). Complete schema/domain deltas contain only the two parser-line replacements and finite prior-receipt/association guards described above. Their supplied diff text matches the native original-to-postimage diff exactly.

The test diff has a different valid blank-line context choice from native diff's first hunk. This is **not** a payload discrepancy: independent text-only in-memory reconstruction checked every context/deletion line and all four hunk old/new counts and starts, with zero errors, and reconstructed the exact 748-line test postimage. No patch was applied to disk and no Python source was imported.

A literal name comparison found every original42 test function name preserved and47 names in repair1. The complete test diff adds five function bodies, changes only the demonstrated incorrect UUID negative/body, and expands the existing blocked-link decorator. All other original function bodies remain textually unchanged in the supplied exact diff. These are source counts/preservation statements, not test collection or runtime counts.

The prior 42-group oracle disposition carries only at this source boundary: P05's compatibility control and P20's correction/relationship controls are now represented correctly; P30/P32's embedded-token case is added. The earlier partial/deferred qualifications, F5's P03/P13/P14 concern and F6's P42 concern remain. No inherited G2 PASS or original syntactic count becomes G3 quality proof.

## Execution and limits

**NOT_APPLIED / NOT_IMPORTED / NOT_RUN.** Only this separate external review/seal were written. No app/test/helper/Git/HANDOFF source was modified. No AST/app import, test collection/execution, format/type/lint command, DB, network, browser, provider or stopped workflow was used.

Ownership, transaction/CAS/delete/rollback, actual source authorization, fixed HTTP privacy, bounded native adapters, persisted selector/Today reads, export/history and browser delivery remain the planned later gates. This review provides no admissions readiness, live search quality, deployment or product completion claim.

