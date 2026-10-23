# G3 first pure source: independent review

2026-10-12 · **SOURCE_ONLY / CHANGES_REQUIRED / NOT_APPLIED / NOT_IMPORTED / NOT_RUN**

## 1. Reviewed boundary and evidence

This review covers the immutable first external packet at:

`/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g3-initial-pure-source1`

The packet SEAL.json SHA-256 is `41a34f0226609b0710a83135b815f0b35ef873096296b2bfd50478731544b1e1`. All nine declared member hashes were verified **before** source reading and reconciled again at closure. The complete schema (1,151 lines), domain (714), tests (646), README, preimage/native-pin metadata and the three add-file diffs were reviewed. Each /dev/null diff payload, after removing the three unified header lines and its leading addition marker, is byte-identical to the corresponding postimage (three cmp exits 0). This was text/hash comparison, not patch application or Python execution.

The independent planned oracle was sealed before reading this packet: G3_INITIAL_PURE_ORACLE_MATRIX.md SHA `dc6fdfcb211d0a8837b1214e1a8675fbc29bc7a8e67b81df171288f25e222f05`; its seal SHA `08d608488dea4afa4b9355a23447b1d99dd3cf9e49cc669bf4134bf520c12370`. All eight accepted design references plus the separate ninth ROOT_G3_INITIAL_IMPLEMENTATION_DISPOSITIONS.md were used. Those hashes were rechecked unchanged.

Coordinates below refer only to this sealed packet:

| Alias | File | SHA-256 |
| --- | --- | --- |
| S | files/backend/app/schemas/admissions_actions.py | 336b600dde899dce003558d531c0a432ceb748f3ead9d88cc9f74d97205d504d |
| D | files/backend/app/domain/admissions_actions.py | be6b2836bea9c31d68380a4484ab11588ac28e2a4897e8a79fd2188313e4ba86 |
| T | files/backend/tests/test_admissions_actions.py | ccd8186c4ec971f013ddbf192ba82d1e09e66346a0a31303cc1dd76e4be61896 |

At the final read, all three application destinations remained absent, including symlinks. No application/test/helper/Git/HANDOFF bytes, old design or seal were changed by this review. No modules were imported; no collection, execution, DB, browser, provider, network or stopped workflow was used. The producer's parse-only metadata is not a runtime result.

## 2. Concrete findings

All six are finite acceptance findings against the existing frozen contract. No new command, state, table or owner policy is proposed. F1–F5 need repair before accepting this source packet; F6 is a smaller but explicit ordering discrepancy.

### F1 — Preserve native uppercase UUID input compatibility [P2]

**S:85–92; T:125–132; oracle P05.**

The new UUID validator accepts only lowercase a–f in hyphenated strings. The existing native `backend/app/schemas/shared_route.py:55–63` accepts a–f/A–F and converts either to a UUID. Native file SHA was reread as `50c2dca8ad250f3d12fc9645a6307ac4dd05bf05a61c79c17bbf925b4c8042e2`. The independent oracle explicitly preserves that canonical compatibility.

The test deliberately replaces its all-digit UUID with `AAAAAAAA-0000-0000-0000-000000000001` and expects rejection. It therefore pins the incompatibility rather than testing canonical identity.

**Minimal correction/control:** accept the native uppercase hyphenated spelling, normalize through UUID, and assert that equivalent upper/lower spellings preserve the canonical request digest/replay identity. Keep malformed UUID, bool revisions and injected server fields rejected. No UUID policy expansion beyond native spelling is needed.

### F2 — An accepted planning correction cannot itself be corrected [P2]

**D:271–292; S:533–545; T:225–239; oracle P20.**

`CorrectDeclarationV1` expressly permits a prior `correct_declaration` ref. However, D:273 requires `prior.applied_delta.declaration` to exist. A valid correction whose replacement is planning/preparing reaches D:290–292 and intentionally leaves that nested declaration null. Its accepted immutable receipt is consequently rejected as `record_not_found` when used as the prior receipt for another explicit correction.

A valid source-level scenario is: create application; declare submission; correct that declaration to planning; then explicitly correct the accepted planning-correction event using its exact fully validated same-case/same-application receipt. The second correction is blocked despite satisfying the finite allowed prior kind. An intervening personal event does not remove the right to reference an older own accepted declaration.

**Minimal correction/control:** establish the affected application from the fully validated allowed prior receipt/request and its exact applied application, without requiring every allowed correction to contain a submission/withdrawal body. Preserve exact event ID/revision/kind, case, application and full receipt validation. Add a positive correction-of-planning-correction and an older-own-prior control. The current application still has only created/latest/status refs; do not add a last-submission/withdrawal pair.

### F3 — A valid own prior declaration for another own application gets the missing-record error [P2]

**D:273–274; oracle P20 / FINITE fixed error contract.**

The same compound guard merges a valid loaded same-case receipt associated with a different own application into `record_not_found` (404). The frozen distinction is wrong own relationship → `invalid_transition` (422), missing/foreign record → generic `record_not_found` (404), and corrupt saved receipt → `saved_unreadable` (503).

**Minimal correction/control:** separate own exact-ref existence from the relationship check. Exercise two own application records, then keep the foreign/missing and corrupted-receipt controls distinct. This is the pure error contract; actual database authority and HTTP privacy remain later gates.

### F4 — Embedded decoded token key=value is allowed as a clickable action link [P2]

**S:1145–1148; T:493–508; oracle P30/P32; FINITE §3 rule 5.**

Private-key matching checks only segment start or a preceding semicolon/ampersand. Thus the synthetic literal `https://example.edu/prefix-token=PRIVATE` passes the inspected branches: valid absolute ASCII authority, no query/fragment, valid public-looking syntax, and the segment does not match `(?:^|[;&])token=`. It reaches true and can be projected as `actionable_unverified` with the literal href. The frozen lexical policy also rejects **embedded decoded key=value token forms**, without that delimiter exception.

Current tests cover a token at segment start and after semicolon, but omit the hyphen-embedded example. The producer already flagged this boundary in its immutable README.

**Minimal correction/control:** apply the frozen conservative embedded-key rule to the decoded path and add the literal/once-decoded embedded-token negatives, asserting no raw literal or clickable fallback. Preserve ordinary informational positives, raw ASCII authority checks, numeric IP rejection, default-port rules and locked no-new-proof envelope. No DNS, fetch, portal certification or global SourceLink change is authorized.

### F5 — A personal-creation receipt can contain an unapproved source binding [P2]

**S:620–652 and 1085–1092; D:342–349; oracle P03/P13/P14.**

For both creation kinds, receipt validation checks exact personal input, application association, creation ref and unreported origin. For `CreatePersonalTaskV1`, it does **not** require `binding=null`, `binding_ref=null` and `origin=applicant_entered`. The stricter reviewed binding-selection guard is entered only for BindSourceTask/RebindSourceTask.

Static counterexample: take an otherwise valid personal-task creation receipt at revision N; insert a valid same-case binding plus an earlier allowed bind/rebind ref, change the created task's origin to source_reference, leave its creation/latest ref, personal input, application ID and unreported state unchanged, and recompute its outer self-hash. DocumentTask's old binding-ref role/revision checks permit this shape; the CreatePersonalTask receipt guard does not reject it. Receipt-only replay revalidates that DTO and returns it without checking this missing command-to-delta restriction.

**Minimal correction/control:** forbid any binding/ref/source origin in a personal-creation delta; add an adversarial **rehashed** typed receipt control with a structurally valid copied old binding, plus the legitimate reviewed BindSourceTask positive.

This is a missing semantic invariant of an accepted receipt. It is **not** a claim that a client can edit the database, that current state/affected metadata could never detect a copied wrong association, or that hashes protect against a coherent malicious rewrite of the entire trusted state/history. Full receipt semantic validation is needed independently for replay/history/export.

### F6 — Today's and undated personal cards use entity grouping instead of the frozen stable-ID tie-break [P2]

**D:682–688, 704, 710; T:570–589; oracle P42 / V2:168–170.**

Personal document tasks are sorted and appended first, followed by separately sorted applications. The today/undated partitions preserve that grouping without sorting the combined cards. An open application with ID a and a document task with ID z on the same day (or both undated) is therefore emitted document z → application a. That is a document-first category rule, rather than the promised stable task/event ID ordering. The card IDs `application:a` / `document:z` also make this example unambiguous under a stable typed-card ID sort.

The existing selected-plan-failure control compares a set of undated IDs, so it cannot detect the ordering discrepancy. Exact saved study-array order is correctly preserved and should remain unchanged.

**Minimal correction/control:** use a documented stable-ID ordering for the combined personal today/undated groups; assert cross-entity ID order, including equal entered dates. Leave overdue date ordering, future study-before-personal date ordering, terminal summaries and native study order intact. This is an ordering repair, not another allocation.

## 3. Source coverage against the independent planned oracle

“Present” below means inspected source/control intent only, **not executed PASS**. A partial row does not add another confirmed defect; it records the proof boundary or an unexercised planned case.

| Oracle group | Static result and meaningful existing controls |
| --- | --- |
| P01 | Finite raw recheck and closed revalidation are present in S:37–74/155–164 and D:59–75. T:115–122 covers raw/constructed known-field nonfinite values and a native constructed item. This does not establish every possible construct/copy representation; no import/runtime proof was performed. |
| P02–P04 | Strict IDs/revision/text, extra-forbid commands and exact applicant input are represented by S:77–180/435–591 and T:125–146. The UUID member of T:125 is wrong under F1. Boundary text and non-ASCII exact preservation are not exhaustively exercised by the current test source. |
| P05 | Canonical object/array/UUID digest code is present; uppercase native compatibility is contradicted by F1. |
| P06 | Aggregate owner/unique ID/application-target/ref guards are present in S:594–697; personal association controls T:193–209 and state/head tampering T:282–302. Physical ownership is deferred. |
| P07–P10 | Exact three-field refs, roles, ordered actual affected refs, preallocated head and acyclic state/receipt hash construction are present. T:147–160/211–222/282–290 supply substantive controls. Application refs are only created/latest/status; task refs only created/latest/report/binding. There is no clear command. |
| P11–P12 | D:352–385 validates current/head and supplied role-associated metadata; T:282–311/329–367 covers mismatch and all-cap metadata batching. The 1,662 bound is a pure distinct-ref bound, not a SQL-query or old-body validation proof. |
| P13–P14 | Original receipt replay/full history validation and tamper controls are present in D:342–405/T:171–181/293–311. F5 shows command-to-delta semantic validation is incomplete despite hash checking. |
| P15–P16 | D:78–91 hashes full exact native user+org under a versioned actor label. T:161–181 checks prefix collision/org/original replay actor. Applicant-declared provenance and responsible actor/reporter separation are represented; actual principal/membership enforcement is deferred. |
| P17–P19 | Immutable creation target, strict selected/award context, personal reports and literal applicant-declared submissions are represented; T:182–222/458–476 supplies controls. No task mutation arises from mentioning it in submission. No official verification/readiness flag is inferred. |
| P20 | Direct terminal-to-planning rejection and one explicit loaded-own withdrawal correction are tested in T:225–239. F2/F3 block the full accepted correction/relationship contract. Older-prior and re-correction positives are needed. |
| P21–P22 | D:245–263 and T:242–265/466–476 retain the nullable old report digest/ref/actor/time across rebind and allow personal operations without current source observations. Dynamic source authority and case deletion are deferred. |
| P23–P24 | Raw six-list/index/recorded-source handling and separate full/semantic/proof/procedure digests are present in D:418–508. T:369–404/428–457 covers duplicate/index and URL omission/None/value distinctions. Blocked literal identity is hashed from authorized supplied source; it is not echoed in the binding receipt. |
| P25–P28 | Independent constraint/proof/procedure and ambiguous/unprojected G1 mapping controls are present in D:442–530/T:405–465. Missing exact source/award relation remains unresolved; no graph/AND/OR/waiver proof is manufactured. Native adapter authority and age-only native observation controls remain later source-bound integration proof. |
| P29–P32 | Raw ASCII-before-parser, numeric/private host forms, single decoding, no-query/fragment, no raw fallback and research-locked envelope have meaningful controls at T:477–518. F4 leaves the embedded key=value contract open. These controls never prove destination access or portal identity. |
| P33–P34 | Prospective current union20, application20/task400 and actual current ref caps are represented by D:222–239/316–339 and S:655–697. T:314–367 separates target/record caps and permits existing-target operations. Real competing 19→20 commands need database CAS proof. |
| P35 | Explicit import50/exact capture/binding/report provenance exists in S:549–570/D:293–302/T:266–281. No shared legacy key cleanup is performed in the pure slice. Browser false→true race and ACK delivery remain deferred. |
| P36 | Closed three-origin follow_current_accepted selection and observed-head comparison exist in S:388–434/D:303–315/T:529–542. No clear/none command is added. |
| P37 | Explicit raw presence flags and G2 current/history priority are represented in D:551–579/T:543–554. They preserve unavailable selected origin without truthiness fallback. Actual native raw v2 {} reads/no-GET-backfill remain adapter gates. |
| P38–P39 | Receipt retains original observed head; Today reads a supplied chosen current head without allocator/fallback. Native structural/persisted-v2 identities are typed, not rebuilt in the pure domain. Technical tick versus structural fingerprint and refreshed-v2 versus persisted tokens require the future native adapter. |
| P40–P41 | Exact native learning/review refs, independent practice permission, single known minute ledger and unknown personal workload are represented by S:816–967/D:580–714/T:570–626. T:592–599 distinguishes expired lesson from own review; T:615–626 distinguishes known empty allocation0 from unavailable/unknown. Actual App.tsx epoch navigation is deferred. |
| P42 | Saved study order, unavailable plan preserving personal actions, mixed-read redaction, terminal summaries and DST/date uncertainty have controls at T:570–646. F6 identifies the missing cross-entity stable personal ordering. |

The complete test file was read. The README's parse-only counts (42 test functions and 97 literal parameter cases) have not been independently collected or executed and are not quality or acceptance counts. Existing test assertions that mirror a rejected policy (F1) cannot supply a contract proof.

## 4. Minimal disposition and later gates

**Changes required for the first pure packet.** Preserve source1/SEAL, the independent oracle and this review. The producer can supply a separate finite repaired packet for F1–F6 with new hashes and targeted controls. Root determines application and any later runtime binding. This review does not itself grant edits or execution.

The pure slice already keeps several material boundaries visible: supplied trusted context; immutable original ACK; no clock/ID/I/O allocation; independent personal report/source applicability; exact versioned study refs; one workload; fixed safe errors; no inferred official receipt. These are source observations, not proof of database authority or real user completion.

The planned D01–D06 controls remain **deferred**: native owner-before-UUID/source entitlement; migrated real SQLite/PG CAS/absent-row/delete/rollback races; actual bounded metadata reads/torn-head detection/no G3-owned DML; per-role <=20+20 target adapters/current guard; immutable complete export/delete/actor erasure; HTTP privacy and owner/case-epoch journal/import/typed navigation. No migration/API/UI code is opened by this report. G2's old gate results do not become a G3 PASS.

No further source blocker was confirmed in this bounded pass. This does not claim exhaustive validation of arbitrary preconstructed objects, every checklist mutation combination, a coherent adversarial full-DB rewrite, official admissions readiness, live search quality, deployment or completion of the product.

## 5. Immutable review inputs

| Stage-relative input | SHA-256 |
| --- | --- |
| ROOT_G3_FINITE_CONTRACT_ACCEPTANCE.json | f9ca10267d61139eb0dc5d48a854ff0f639815d75e27f69eaf3b0a8c04073d21 |
| ROOT_G3_DESIGN_ACCEPTANCE.md | 81fc914fd0756436ebd3974ad7847131e90c5e19b64121fb2733b5fd36d8f70d |
| proposals/g3-design/G3_CONTRACT_DESIGN_V2.md | 7b3857d7a273e3bbb3b38644101a03fd41159bbc121b406b3a76ef929f3edbbb |
| proposals/g3-design/G3_IMPLEMENTATION_DEPENDENCY_MAP.md | 81171a86f90c11e19438efe760ad9e0cd4fcbc394c036a3ec7f9bb1143537bdb |
| proposals/g3-design/G3_NATIVE_BINDING_ADDENDUM_FINAL_V2.md | 0c15b69b2cdb9347a1f30501822aeff4cf913f3e12d08635bdd1d30a7b525474 |
| proposals/g3-design/G3_FINITE_CONTRACT_FREEZE_PROPOSAL.md | f5acdae226110346798aca2ab8e51a40894e902adc5e2d4eb71b5c85740d839a |
| proposals/g3-design/G3_EVENTREF_AND_RAW_AUTHORITY_ADDENDUM.md | 9292ca3db7edb0a7423a97a8760da579bebf1cc68534d4f7282b2a1a50e51e8e |
| G3_SOURCE_BOUNDARY_PROPOSAL.md | 613cb42daeb2aba30ee1d4e5c6a016c8665dde61e92ffd7148f78a030fd16c1c |
| ROOT_G3_INITIAL_IMPLEMENTATION_DISPOSITIONS.md | bbacf306f96b8f877bb08c6f5be9dd46f3851c7497b0ea653aa9012d52c7da38 |
| G3_INITIAL_SOURCE_GRANT.json | 2d69074ecf90d164b8535484004667feca1529c9eea92a8352acd503c190ceb2 |
| G3_INITIAL_PURE_ORACLE_MATRIX.md | dc6fdfcb211d0a8837b1214e1a8675fbc29bc7a8e67b81df171288f25e222f05 |
| SEALED_G3_INITIAL_PURE_ORACLE_MATRIX.json | 08d608488dea4afa4b9355a23447b1d99dd3cf9e49cc669bf4134bf520c12370 |

A separate review seal records all nine packet member hashes, source/diff equivalence, the unchanged inputs, findings and the NOT_RUN boundary. Only this review and its separate seal are written by this agent.

