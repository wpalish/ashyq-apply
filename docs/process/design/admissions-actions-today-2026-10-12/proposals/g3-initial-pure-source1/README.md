# G3 initial closed pure source proposal — first immutable snapshot

2026-10-12 · **SEALED SOURCE PROPOSAL / NOT_APPLIED / NOT_IMPORTED / NOT_RUN / NOT_ACCEPTED**

Root is the sole application/Git/HANDOFF/helper/runtime writer. This author wrote only external source postimages and their packet metadata. No application import, test collection, test execution, typecheck, lint/format gate, database/runtime, browser, provider/model/network or closed research work was performed. AST parsing inspected source grammar only; it establishes no runtime correctness. Root and an independent reviewer must qualify this first snapshot before adoption. Any correction must be a separate preserved packet.

## Authority and exact boundary

- Root `G3_INITIAL_SOURCE_GRANT.json`: `2d69074ecf90d164b8535484004667feca1529c9eea92a8352acd503c190ceb2`.
- All eight accepted authority pins in that grant matched during sealing. Their exact map is in SEAL.json.
- Additional root `ROOT_G3_INITIAL_IMPLEMENTATION_DISPOSITIONS.md`: `bbacf306f96b8f877bb08c6f5be9dd46f3851c7497b0ea653aa9012d52c7da38`.
- Only the three ABSENT application paths named below have proposed postimages. All were absent, including symlinks, when preimages were inspected. `PREIMAGES.json` records absence; the diffs originate from `/dev/null`. No fabricated original source bytes exist.
- No model/API/migration, registration, export/delete wiring, frontend, allocator, catalogue, G1/G2/legacy change or runtime helper is proposed here. No G3 usable release or product readiness follows from this packet.

## Proposed source/API map

| Proposed new path | Pure surface |
| --- | --- |
| backend/app/schemas/admissions_actions.py | Closed 12-command intent; exact three-field EventRef; full actor reference; bounded personal aggregate/delta/receipt; raw native checklist subclasses; exact native head/learning refs; independent Source/Today DTOs; finite canonical hashes; one lexical link rule used by output validation. |
| backend/app/domain/admissions_actions.py | Explicit `ActionContextV1`; `apply_action`; identical original `replay_receipt`; `validate_current_snapshot`, `metadata_batches`, `validate_complete_export`; six-list `build_binding_selection` and independent `compare_binding`; safe `project_action_link`; metadata-only `choose_origin`; supplied-only `project_today`. |
| backend/tests/test_admissions_actions.py | 42 source test functions, **97 literal parameterized cases counted by AST, NOT_COLLECTED / NOT_RUN**. Every institution, case, principal, claim, document and saved plan is synthetic. |

### Closed commands

`create_application`, `create_personal_task`, `bind_source_task`, `rebind_source_task`, `set_document_self_report`, `set_personal_details`, `set_planning_status`, `declare_submission`, `declare_withdrawal`, `correct_declaration`, `import_legacy_marks`, `select_active_preparation`.

There is no clear/none selector command, official verification flag, arbitrary dictionary/full-state command, URL-posting command, source declaration or automatic submission. `none` is derived only when native presence is genuinely absent. Caller-loaded ownership, native availability, source access, preview identity, allocated IDs and accepted UTC time are explicit inputs; these pure functions cannot establish them. No clock/random/Session/adapter/DB/provider/allocator call is present.

## Root mappings preserved

1. **Prior declarations and reference bound.** Current application has created/latest/status refs only, at most3 each. Full submission/withdrawal content stays in immutable receipt history. Withdrawal does not delete/rewrite any previous receipt. A correction requires a fully validated own prior declaration receipt, exact event/revision/kind and same application/affected association, current CAS and explicit replacement confirmation; it need not be the latest status event. No additional embedded declaration refs exceed the frozen1,662 bound. Tests cover current three-ref fields, historical submission survival and exact loaded correction context.
2. **Rebind does not transfer completion.** Keep durable task ID and original report including nullable `binding_digest_at_report`. Compute `report_refers_to_previous_binding` from accepted own references, separately from premium SourceReadStatus. A new explicit report may refer to the new accepted binding. `not_needed_reported` stays personal and adds a non-waiver notice.
3. **Hash cycle and metadata.** Event ID is supplied before state construction; only three-field EventRefs are stored in state. State digest precedes reference-only receipt and receipt self-hash. Current/head digest/time/ID/revision/affected delta and each referenced own association are validated separately. Older metadata is not an older-body hash claim. At-cap test constructs20 apps/400 tasks/selector with1,661 distinct actual refs, requiring9 batches of≤200 (within frozen1,662). Full export checks exact ordered revisions, predecessor chain and actual loaded current/head; missing current or newer exported head fails safely.
4. **Raw finite values.** Original Python/model values are checked before JSON normalization. Constructed/copied models are revalidated. Native generated_at alone is excluded from checklist content identity. All six ordered lists, duplicate occurrence indices, scope omission and ordered procedure remain. Omitted/None URL is no recorded URL; present exact bytes change proof identity while semantics excludes URL/claim IDs. Raw source bodies are hashed only in authorized supplied inputs; a G3 binding receipt/request/delta contains references/digests, no copied prompt/title/quote/URL.
5. **Actual G1 relationship.** Optional native action ID is attached only when actual original_items/source_locations unambiguously cover the complete exact numeric occurrence set. Same-list duplicate ambiguity does not guess an ID. Manifest/proofs/scope/missing claim identities are separate proof data; named award relation remains unknown. G1 IDs/digests are never regenerated or silently merged by title.
6. **Selector/Today.** Exact G2/v2/v1 head observations are immutable in ACK; current supplied head may later advance with the same selected origin. G2 current OR history presence wins over legacy even if unavailable; non-null v2 marker presence precedes v1; corruption never permits fallback. Unreadable G3 Today has `action_state=unavailable`, revision null and unknown/unavailable plan, not empty revision0. One chosen supplied accepted ledger/order is preserved. Documents have no estimated minute ledger. Exact review refs may remain available after expiry; new lesson actions depend on separately supplied native permission. Source lock after one supplied token recheck redacts all new hashes/reasons, and mixed tokens withhold joined actions. Existing personal records remain independently visible on plan/source failure.
7. **Dates.** Personal local dates and IANA zones are explicit. Date-only/no-zone values are labeled uncertain with display-only fallback; no certified deadline, closure, official readiness or urgency is inferred. Today DTO supports distinct source-date/previous-cycle uncertainty, but this pure personal projection does not invent source dates or silently turn a native checklist deadline into a personal due date. A future authorized source adapter must supply any source-date presentation explicitly.
8. **URLs and safe errors.** Raw ASCII authority is inspected before urlsplit; literal default ports and DNS labels only, with numeric IPv4/hex/octal forms, private suffixes, login/token paths, query/fragment, malformed escapes, encoded slash/control/backslash denied. Punycode is only unverified syntax. No DNS/fetch claim. Rejected literal is not emitted in href/receipt/error fallback. All ActionError details are fixed code/message and raw validation traceback chaining is suppressed. A locked source link gives only not_available, no new presence/blocking reason. Source errors do not imply programme absence.

## Source-only review caveats before acceptance

- This snapshot is unformatted and has not been linted, typed, imported or run. Root may discover real typing, validation or assertion failures; preserve first failure evidence and apply finite fixes under a new source write-ahead.
- Lexical token-key matching currently covers a key at decoded segment start or after `;`/`&`. Frozen wording also mentions embedded token-key forms: root/peer should explicitly review a path such as `prefix-token=PRIVATE` before accepting this policy, rather than assuming the drafted controls exhaust every embedding boundary. There is no network/public-host certification.
- Raw checklist cloning preserves native field defaults and exact source strings; nested native proof/schema roundtrip and strict JSON behavior require actual focused controls. None of the count above is a PASS receipt.
- This pure layer does not prove fresh ownership/access, transaction isolation, atomic persistence, SQL failure reconciliation, cascade erasure, pagination, API validation privacy, frontend recovery, native learning navigation or physical export races. Those later seams need separately granted implementation and meaningful gates. New G3 tables/migration/API/UI remain absent here.
- `StudyActionReadV1.availability` and own review association are prevalidated caller-supplied observations; no lesson-ID spelling establishes exam, catalogue or ownership. Today is a component read, never an atomic source snapshot.
- All earlier provider/model/quota/security/reset/live/expert/heldout/controller STOPs remain in force. No quality score, admissions odds, official score/band, payments or whole-product completion is claimed.

## Source manifests

SEAL.json pins every packet member size/SHA and exact three postimages. `NATIVE_READ_PINS.json` pins only named ordinary source/config/test files; no corpus/labels/private DB bytes were read. Original baseline772 remains the root grant metadata, not a claim that this author independently audited every file. Original authority files and other agents' packets are not members and were not overwritten.
