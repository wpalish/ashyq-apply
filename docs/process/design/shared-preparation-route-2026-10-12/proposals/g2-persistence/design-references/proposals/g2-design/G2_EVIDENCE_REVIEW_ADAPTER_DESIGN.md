# G2 evidence and own-review adapters — native seams, reference identity

2026-10-12. **EXTERNAL DESIGN ONLY · NOT_APPLIED / NOT_IMPORTED / NOT_RUN.** This is a bounded Markdown proposal for the next G2 API writeahead, not implementation, test results, production acceptance or permission to resume stopped work. Root remains the sole source/Git/HANDOFF writer. No application modules were imported or executed; no tests, providers or stopped collectors ran. Credentials and frozen evaluation labels were not opened. Ordinary source files and their hashes were read.

## 1. Integration decisions and unchanged contracts

The accepted persistence/typed v2 and `ROOT_G2_INTEGRATION_DECISIONS.md` remain byte exact. Root subsequently resolved two native-seam ambiguities:

1. The same comparable per-goal native manifest with `evidence_state=current` may yield G2 `eligible` even when the native G1 `projection_state=partial` includes `exam_identity_unestablished`. Keep all native uncertainty, source scope and policy notices. This is unchanged observed evidence for an allowed personal selection, **not official applicability, admission readiness or programme coverage**.
2. An own historical review stays readable under the native review contract even with `lesson=None`. A **new import** also needs a server-known explicit association from the exact lesson/version to its track and then to the selected exam. If absent, reject explicitly as `review_exam_unestablished`; never infer it from lesson spelling, the client's exam choice or another content version.
3. G1 manifest fields/fingerprint stay unchanged. Locked `approved → maybe` remains an allowed selection and is not distinguished by the native locked fingerprint. Current strict selection still rejects `rejected/undecided`. Document the limitation; do not manufacture a premium digest or widen the native source scope.

Read adapters do not allocate dates, submit attempts, change scores, regenerate accepted slots, consume provider quota, alter official applicant fields or update `profile.updated_at`. Preparation expiry and research entitlement are independent. New G2 mutations require the native active preparation term; own history/review reads and an exact persisted same-UUID replay retain their separate expiry-safe contracts. CAS, UUID replay and current/history commit remain governed by the separate G2 transaction design.

## 2. Exact G1 seam and ownership boundary

The actual public route function is `backend/app/api/routes_preparation_graph.py:287`, not an HTTP client or copied private loader. The future adapter supplies **all four** arguments explicitly: `preparation_graph(profile_id=<owned case>, result_id=<exact ordered list>, principal=<current principal>, session=<current Session>)`. Never rely on its `Query`/`Depends` defaults. This file stays unchanged; do not import its private `_selection`, `_claims`, `_source_slice` or `_manifest` helpers into a competing loader.

For a **new preview/save**, call native G1 once with the complete input selection (2–20 exact unique result IDs in applicant order). Its ownership completeness check precedes decision validation, it rechecks the authorized selection, and it keeps exact per-programme scope/claim/conflict isolation. Any missing/foreign result is generic 404; rejected/undecided is 422. Do not trim IDs or substitute latest-run candidates. Validate returned profile, requested/selected order, `selection_source=server_verified_owned_explicit`, programmes and manifest IDs before binding a preview.

For a **saved GET/history**, first validate the receipt and own profile. Its accepted IDs and allocation stay intact even if a programme disappeared. A separate bounded metadata query selects only `ProgramResultRow.id`, `run_id`, `user_decision`, joined to `ResearchRun.profile_id == owned_profile_id`, for the saved IDs. No result names, payload/checklist, run diagnostics, claim/conflict rows or general export are loaded at this step. Reassemble the result of that query in the accepted order; database ordering is not authority.

Then classify each saved ID without a whole-selection error:

- Absent from the owned query: `result_unavailable`. Missing and foreign remain indistinguishable; no lookup outside the owned case.
- Owned but decision is not exactly `approved/maybe`, including an invalid stored value: `decision_changed` with only the fixed safe code.
- Otherwise check native `has_full_access(session, principal.organization_id, profile_id)` before premium loads. If false: `research_locked`, no new premium digest and no evidence slice.
- Only for an owned, allowed, currently authorized ID, call the native route in process with `result_id=[that exact ID]`, the same Session/principal/profile. Its own checks remain authoritative. Validate exactly one matching programme and manifest; never borrow another programme's proof or request scope.

Run the adapter under `session.no_autoflush`, with no commits/flushes or receipt mutations. Do not catch unrelated database/transaction failures and return fictitious empty current evidence. Unexpected infrastructure failures remain read failures. If a native singleton call reports 404/422 after a metadata read, perform at most one safe owned metadata recheck to classify a selection race. If the row still appears eligible but cannot yield a valid slice, use `evidence_unknown`; do not retry a provider, loop indefinitely or erase the historical receipt. Lost case ownership remains a generic case 404 rather than a goal status.

If access is observed revoked during assembly, suppress already assembled premium slices and classify remaining allowed selections as locked. A final entitlement read may enforce the last observed case access; it is not an atomic guarantee against revocation after that read. Stop further premium reads once locked. The native source revalidation and the G2 transaction fence do not make independently written research evidence a repeatable-read snapshot.

## 3. Native manifest and safe per-goal reference digest

The native `ProgrammeSourceManifest` has **exactly** these fields (`schemas/preparation_graph.py:282`):

| Field | Native meaning and constraint |
| --- | --- |
| `result_id` | Exact selected result ID, in graph/request order. |
| `run_id` | Authoritative selected run; null on a locked card. |
| `result_snapshot_digest` | Native digest of result scope/decision/checks/scholarships/checklist/unresolved/partial/failure/staleness. Null when locked. |
| `authoritative_evidence_digest` | Native digest of authoritative claims and unresolved conflicts. Null when locked. |
| `resolved_claim_ids` | Sorted exact IDs bound by requirement/document/policy proofs; empty when locked. |

There is no manifest `user_decision`, exam edition, readiness, generation clock or raw scope field. Do not extend it in this increment. For a structurally valid, authorized and **readable** programme slice, propose this exact G2 reference hash input:

```text
{
  "schema_version": "shared-route-goal-reference-v1",
  "g1_schema_version": "preparation-graph-v1",
  "profile_id": <owned profile ID>,
  "manifest": <the exact native ProgrammeSourceManifest JSON object>
}
```

Canonical bytes: JSON with sorted object keys, separators `,` and `:`, `ensure_ascii=False`, `allow_nan=False`, UTF-8; SHA-256 lowercase hex. Preserve every manifest field and null value and native `resolved_claim_ids` order. Hash the validated native JSON representation, not `repr`, client-provided digests, raw ORM payload or a URL-only approximation. Bind profile/schema namespace to prevent accidental cross-case/version comparison. The receipt stores only ordered `{result_id, reference_digest}`, never the raw manifest, run IDs, claim IDs, source names or raw scopes.

Return **null** for a locked slice or native `projection_state=unavailable`, even if the latter contains non-null hashes of a minimal failure envelope. Such placeholders are not a comparable authoritative baseline. A readable native partial/unknown/stale/conflicted slice can have an observed reference digest, but its uncertainty is separately preserved and cannot be promoted to current by equality. Invalid/malformed DTOs also cannot supply a comparable digest.

At preview/save, the receipt's `source_fingerprint` is the **unchanged native whole-selection fingerprint**. Per-goal references come from each entry of that same complete validated graph. At saved read, derive a reference digest from a validated singleton entry and compare with that goal's accepted digest. **Do not compare the singleton graph's whole fingerprint to the multi-programme receipt fingerprint**, or recompute/overwrite the accepted receipt fingerprint from today's slices.

The native whole fingerprint hashes profile ID, ordered selection and ordered manifests (`domain/preparation_graph.py:770`). Authorized manifest result hashes include the decision; locked manifests contain only ID plus null/empty fields. Therefore changing `approved` to `maybe` changes an authorized manifest but not a locked one. This is an observed limitation, accepted for the two still-allowed decisions; it proves neither source applicability nor readiness. No per-goal premium hash may be reconstructed from a locked receipt or cached card.

Native normalization matters (`domain/preparation_graph.py:501–546`):

- Checklist `generated_at` and claim `age_days` are excluded from native hashes. Their ordinary clock changes alone must not mark a saved goal changed.
- Claim `is_stale`, stored status, source URL, accessed-at, scope and other serialized evidence remain included. Crossing a freshness threshold can change the observed identity; this is **not a claim that the university edited a page**.
- Result partial state, stored parsing failure, profile-vs-result staleness and unresolved questions remain included. Do not remove them to obtain a matching digest.
- Claims/conflicts retain native authority and same-run/per-result isolation; no G2 payload reassembly can override them.

## 4. Current source status assembly

Each saved goal yields exactly one fixed `GoalStatusV1` in its accepted order. Its `safe_reason_code` is null only for `eligible`, otherwise exactly the state code. Do not expose private parsing exception text in that field.

| Current owned read | Accepted reference | G2 goal state |
| --- | --- | --- |
| Missing/foreign | Any | `result_unavailable` |
| Rejected/undecided/invalid decision | Any | `decision_changed` |
| Research access locked, including a native locked return | Any | `research_locked`; no new evidence digest/slice |
| Native unavailable or malformed slice | Any | `evidence_unknown`; ignore minimal-envelope placeholder hashes |
| Readable slice, no comparable accepted baseline | Null | `evidence_unknown`; do not call it a source change |
| Readable slice, comparable native reference differs | Non-null | `source_changed`; keep original evidence uncertainty visible |
| Same reference, native `evidence_state` stale/conflicted/unknown | Non-null | `evidence_unknown`; no freshness upgrade |
| Same reference, native `evidence_state=current`, `projection_state=projected` **or partial** | Non-null | `eligible`; preserve partial/edition/waiver/route reasons |

Here `eligible` means an owned allowed selection with unchanged observed current evidence. It does not mean an application is eligible, required exam editions are resolved, waivers accepted, all score components satisfied or the personal lesson covers programme requirements. Every native G1 requirement check, proof scope verdict, waiver/alternatives policy, document dependency and unresolved notice remains unchanged. Never synthesize common maxima, an AND/OR route or a programme-cover edge.

For the otherwise undefined `RedactedCurrentG1Slice` in typed v2, propose reuse of the exact native `PreparationGraph` DTO constrained to one matching saved ID. Current **selection eligibility and entitlement** permit the slice; G2 `source_changed/evidence_unknown` do not authorize an old premium copy. A fresh authorized native slice can explain its own partial/stale/conflicted/unknown state. Keep its native fields and graph invariants; do not flatten it into another proof parser. Locked/unavailable selection races emit no premium slice. Native authorized `unavailable` may be represented by its minimal safe native failure envelope, without treating it as comparable source evidence.

`CurrentRouteStatus.as_of` records the read assembly time. Native G1 obtains one freshness timestamp **per call** (`routes_preparation_graph.py:321`), and its DTO does not expose that timestamp. A strict new preview/save uses one native whole-selection call. Saved per-goal calls have separate clock instants and can be mixed observations. Do not claim that `as_of` is one atomic freshness/source read or patch a global clock to simulate it. If a later requirement truly needs one native shared timestamp for safe partial selections, that is a separately reviewed G1 API extension.

Aggregate `needs_review` derives deterministic safe reasons for every non-eligible goal and the existing legacy/content/imported-ref states, preserving case order. Native partial applicability notices remain visible even when the goal's manifest comparison is eligible. A G2 personal route may be usable while official applicability remains unresolved. GET/history never repair digests, rewrite accepted dates, drop missing IDs or rerun the allocator.

## 5. Own reviews: receipt authority and exact registry association

The actual receipt seam is `routes_preparation.py:563–594`, `review_attempt(profile_id, attempt_uuid, principal, session)`. Supply real arguments explicitly in process. It first checks own profile, looks up the exact `(profile_id, canonical client_attempt_id)` pair, returns a generic missing/foreign 404, and reads the saved attempt without a preparation-term gate. It resolves **the recorded lesson ID and content version**. If exact content is retired/unknown, it returns the unchanged own receipt with `lesson=None`; this must keep working.

`models/study.py:16–36` stores lesson/version/UUID, request digest, answers/feedback, correct/total and timestamps, but **no track or exam association**. Neither the receipt's ID nor its numeric practice outcome proves the exam. The progress list defaults to the latest 20 attempts (`routes_preparation.py:600–639`); absence from that list does not establish missing ownership or unavailable historical content.

New preview/save import resolves each unique exact requested UUID at most once (input cap 400), validates its returned profile, attempt UUID, `lesson_id`, `version` and exact `AttemptReviewRef`. Wrong own lesson/version is a fixed 422; missing/foreign uses the native generic missing response. The imported exam must be one of the input's 1–2 exam choices. No attempt submission, regrading, new UUID, score conversion or preparation quota action occurs.

Separately establish registry association for the exact `(lesson_id, content_version)`:

1. If the native review supplies an exact matching lesson, use its literal server track metadata. Current `lesson_dispatch` recognizes only exact starter/pack versions (`learning_pack.py:533–558`); it never substitutes a newer version. Bind that track through the server's literal `EXAMS.track_ids` (`catalogue.py:181–212`): `ielts_reading → ielts_academic`, `sat_math/sat_reading_writing → digital_sat`. This is personal content association, not university acceptance.
2. If `lesson=None`, only a **preserved literal historical registry mapping for that exact pair** may supply the track/exam. Such a mapping is not present for arbitrary retired versions in the inspected dispatcher. A same-ID lesson in today's catalogue, ID prefix, exam-looking title, client-selected exam or answer shape cannot fill the gap.
3. If no explicit association exists, reject the **new import/command** with fixed code `review_exam_unestablished`. Do not omit the review, guess the exam, or disguise this unresolved identity as `version_unavailable` allocation. An explicit mismatching known association is rejected; it is never silently reassigned to the other exam.

An exact own historical receipt with a preserved known association can be a dated **receipt-review action**, even when its original lesson is no longer available; retain its exact old ref and place it after current lessons of its own exam in input order, as typed v2 requires. `available` for this action means the native unchanged saved review can be shown, not that original questions/lesson can be reopened or that an unseen diagnostic/official score exists. Display the native `lesson=None` notice. If the exact own review itself cannot be read, it is unavailable, not replaced by today's lesson.

Existing accepted G2 receipt/history stays readable after a registry/content retirement or expiry. Current content status probes exact own review availability; stricter **new-import** association validation must not retroactively delete an accepted ref, recalculate slots or block own history. A missing/foreign current attempt yields `review_unavailable`; malformed unreadable own data yields `unknown`. Neither status manufactures a replacement attempt. Readable old receipt with `lesson=None` is kept with its original notice. New preview/import cannot evade the association rule by replaying a different UUID; same-UUID persisted write replay follows the separate immutable-ACK protocol before new-command gates.

This is a root clarification of typed v2's older-review availability rule, not an edit of that sealed document. The proposed first implementation may import only known exact starter/pack associations. Arbitrary historical imports must remain explicitly rejected until a separately reviewed literal historical registry exists. Do not backfill exam/track into immutable StudyAttempt scores or treat a future mapping as evidence of admissions acceptance.

## 6. Persistence, export and deletion seams

The G2 current/history rows store only the accepted full reference-only allocation, applicant inputs, exact action refs, ordered IDs, safe reference digests, native whole fingerprint and immutable write receipt. No G1 graph/proofs/names/excerpts/current status or current premium manifest is persisted into the receipt. Historical GET uses the same current safe source adapter under current entitlement; it never displays evidence cached at acceptance.

`routes_profile.py:268–401` already exports all owned saved attempts and study schedules plus owned research records; ownership is its native boundary, and it has no preparation/research entitlement gate. Reuse the existing `attempt_view` serialization/ordering policy for existing rows. Add only reference-only G2 current/history sections and their honest counts/notes in a later root allowlist. **Do not** call general export to obtain current G1 evidence, or silently change existing owned research export policy in this increment.

New G2 rows need case foreign keys and native ORM case-child registration like `models/applicant.py` to support complete own-case export/delete, while preserving another case. Deletion ordering/concurrent-write safety is separate from this read adapter; root's accepted delete/legacy-CAS design governs it. Neither adapter mutates a legacy settings row, ticks, nullable v2 sidecar, payments ledger or attempt receipt. A cached graph is request-local only, keyed by profile/selection/principal/context; never reuse across cases, owners or later entitlement reads.

## 7. Optional future G1 contract changes — outside this increment

- A **versioned** native decision manifest field could bind public `approved/maybe` decision changes even when locked. It needs explicit schema/domain/fingerprint tests and migration/replay compatibility decisions; do not silently add a G2 synthetic premium digest now. The accepted current limitation is sufficient for the two still-eligible decisions because strict current selection catches rejection.
- An exposed native `as_of` or public safe-partial-selection projector could provide clearer batch timing while retaining per-goal missing/locked envelopes. This requires separate G1 scope; a wrapper cannot claim it already exists.
- A literal historical exact-content association registry can support retired review imports. Its provenance must be actual preserved content metadata; do not infer a mapping from current spelling. No new registry/source dependency is created by this document.

## 8. Required later controls — scenarios only, NOT_RUN

| Control | Required result |
| --- | --- |
| Explicit in-process native G1 invocation | Exact Session/principal/profile/list passed; no HTTP, default Depends/Query, duplicated evidence loader or provider call. |
| A/B own selection, reverse order, singleton saved probes | Preview whole fingerprint binds order; per-goal comparison of the same entries matches, despite a different singleton whole fingerprint. |
| Saved missing/foreign/rejected result among valid IDs | Generic ordered status per old ID; surviving allowed slice still readable; exact receipt/slots remain byte/semantic equal. New complete selection fails rather than trims. |
| Locked sentinel names/checklist/claims/conflicts | SQL observation forbids premium loads; native locked fields stay null/empty; `visible_evidence=[]`; old receipt safe digests unchanged and no new premium digest. |
| Locked approved→maybe, rejected/undecided control | Native locked fingerprint equality documented for the two still-allowed decisions; rejection detected through native current selection, not a fabricated digest. |
| Authorized same digest/current + partial exam identity | Goal eligible only as observed selection; partial/unknown edition/waiver/ANDOR notices and exact proofs stay unchanged; no official readiness claim. |
| Same digest with stale/conflicted/unknown or null baseline | `evidence_unknown`, never eligible by hash equality. Unavailable placeholder digest never becomes a confirmed reference. |
| Claim age increment/checklist clock vs freshness threshold/authority change | `age_days/generated_at` alone stable; is_stale/status/source/scope/authoritative column/conflict changes preserved. source_changed never asserts a live website edit. |
| Same-run multiple results and other-run claim/conflict sentinels | Native own-result plus same-run shared rows only; no cross-goal scope/claim borrowing. |
| Metadata race, mid-read entitlement change, malformed native slice | Bounded safe recheck; final known lock clears premium slices; conservative unknown status; unexpected DB failure not disguised as empty current evidence. |
| Exact known own review under active/expired prep term | Native old receipt read unchanged after expiry; a new mutation still requires active prep term; explicit correct track/exam import only; exact UUID/version bound, no submit/regrade/official score writes. |
| Retired exact version: readable receipt but no registry association | Existing native review/history still succeeds with lesson=None; **new import rejects review_exam_unestablished**, preserving every requested item or rejecting the command as a whole. |
| Historical literal mapping exists / same-ID current version only | Only preserved exact-pair mapping may admit old review; current-version metadata/ID spelling/client exam do not establish the historical association. |
| Foreign/missing UUID, own version mismatch, older than latest20 | Generic foreign/missing rejection; fixed own mismatch rejection; exact older receipt lookup succeeds independently of the progress display list. |
| GET/history/export after prep expiry/catalogue retirement | Exact immutable allocation/digests remain; per-goal/current review status separate; no allocator/new dates/implicit import or premium history copy. |
| Same-UUID replay versus new command, own-case deletion | Persisted ACK remains exact under replay protocol; unknown new review association rejected; G2 cascade complete for own case and isolated from another case. |

The 20-goal and 400-review caps bound native read work but do not prove latency. Baseline adapter may perform up to 20 native singleton G1 calls on a saved read and one native review call per unique requested UUID. Cache repeated exact refs within one request only. Record query/serialization counts in future offline API controls; any batching optimization must reuse native authority and keep this lock/ownership contract. No performance PASS claim is made here.

## 9. Source/design pins inspected (SHA-256)

All source paths below are relative to `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials`. These are observed file hashes, not a claim of a new commit, integration gate or deployment. Typed v2's older route preimage remains historical; this adapter uses the current route hash below.

| Path | SHA-256 |
| --- | --- |
| `backend/app/api/routes_preparation_graph.py` | `7ddff09f9ef9601571568d51c3701e901166193de1801280b2901d067a0ef7c9` |
| `backend/app/domain/preparation_graph.py` | `2ba1488a582a4a8e4a37d747a5a4e4d1d44ceb70c980ad50195438dae3b35c09` |
| `backend/app/schemas/preparation_graph.py` | `4d7c55dd33295f1e6e9e6750a2da50c1a120e83635836d279857241d1a3fd249` |
| `backend/app/api/routes_preparation.py` | `11c77dd288e5f00bb7159447833981de1aca446f0e47726a116aec405d1645f2` |
| `backend/app/models/study.py` | `cd48802f039ef76f507328af22eb27735fab56ea5a25071bdca522053af59acc` |
| `backend/app/preparation/catalogue.py` | `8ca74f40b88df74a27bc5b0d5aa52d5e60ce5b5417f4e37c049690b47d716169` |
| `backend/app/preparation/learning_pack.py` | `778b94d392b89406e4ddd13726a25d91a808114e2026064289f12500e02b7aae` |
| `backend/app/api/routes_profile.py` | `d9bd87d528f7c8545c3b6e1875d7924f09bb4bb2e63f5cf18db022e0fe0c235a` |
| `backend/app/models/applicant.py` | `54086f053fbf2db1b4a1471b9dac5595191f425ae2d6c6fe61d7744f1397caeb` |
| `ROOT_G2_INTEGRATION_DECISIONS.md` (external stage) | `e9d51228d38316f650d057207fd933437600564e53007e4733b052b391d5cbf5` |
| `G2_IMPLEMENTATION_DEPENDENCY_MAP.md` (external g2-design) | `47b21ed69e2ab087bae7d6d8820e316cba852e35d089f2d64db6876aa57a7210` |
| `SHARED_ROUTE_PERSISTENCE_SPEC_V2.md` (external g2-design) | `27bc906301708c604c723e1a1d2fdb6ae79f454750871b4d6f82a98cd4728de3` |
| `TYPED_CONTRACT_DESIGN_V2.md` (external g2-design) | `3916138d910830dfb0b484f2a562a488889798985f11ac2abdb2ffcd7282f37c` |
| `G2_LEGACY_CAS_TRANSACTION_DESIGN.md` (external g2-design) | `0fac39aa833050cba9819c4531707acb84eaf89577e61434d2d9995beab48f4f` |

**State:** design sealed after source-only inspection. The future API source proposal still needs root writeahead, exact native-wrapper/DTO tests, real two-session legacy-CAS controls and ordinary gates. No source proposal, application imports, tests, network calls, source edits, Git or STOP-workflow action was performed by this report.
