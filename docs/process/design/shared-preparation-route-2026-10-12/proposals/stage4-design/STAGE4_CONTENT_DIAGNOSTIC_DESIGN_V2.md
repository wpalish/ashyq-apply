# Stage 4 content and diagnostic design v2 — bounded clarifications

**2026-10-12 · SEALED DESIGN_ONLY · SOURCE_NOT_CHANGED / NOT_IMPORTED / TESTS_NOT_RUN / NO_PUBLISHING**

This separate revision resolves F1–F3 in `STAGE4_INDEPENDENT_DESIGN_REVIEW.md`. The original `STAGE4_CONTENT_DIAGNOSTIC_DESIGN_ONLY.md` remains immutable and supplies the rest of the Stage4A/Stage4B scope. Where wording differs, the three clauses below supersede original §3.1 Planning, §3.3 estimate validation, §5.2 exposure timestamps/unseen boundary, §5.3 served-form snapshot, and §6 diagnostic export. This is a design artifact, not an application patch, content package, review fact, diagnostic method, or release approval.

## 1. Stage4A duration contract: legacy unknown is a valid value

`ContentRecord` metadata uses a closed conditional pair:

| Field | Contract |
| --- | --- |
| `estimated_minutes` | Positive finite integer **or null**. Legacy lesson refs with no evidenced duration use null. No default or zero sentinel. |
| `estimate_status` | `unknown` iff `estimated_minutes=null`; otherwise `planning_estimate`. |
| `estimate_basis` | Null when unknown. A non-null estimate needs an explicit recorded owner-approved planning basis/version, not an inference from item count, test time, lesson title or model output. |

Stage4A maps the nine existing exact lesson/version refs with `estimated_minutes=null`, `estimate_status=unknown`, and no asserted author/rights/reviewer fact. A subsequent estimate is a new versioned metadata fact with provenance and review of that fact; it does not mutate the existing lesson body or accepted attempts. Validation rejects bool/float/NaN/Infinity, nonpositive values and mismatched status/basis. Unknown is not validation failure.

`LearningUnit.planned_minutes=20` in the existing learning schedule is an **allocation of planning capacity**, not observed lesson duration. The coverage panel may show “20 minutes allocated in this plan” only when it displays a saved schedule slot with that exact basis; it cannot show “this lesson takes 20 minutes” from that field. Coverage/completeness denominators and teacher/learner QA never derive from an estimated duration. A legacy lesson with no estimate remains actionable through the existing owned exact-version lesson route, subject to current preparation access.

Stage4A controls before source adoption: all nine legacy refs accept null/unknown; positive estimates require basis; malformed or infinite estimates fail; neither coverage DTO nor UI substitutes schedule minutes for duration; old catalogue, lesson, attempt, receipts and v1/v2 schedule shapes stay byte-compatible. These are proposed controls, **NOT_RUN**.

## 2. Future Stage4B immutable form data and own export

Keep two distinct immutable representations at reservation:

| Representation | Stored content | Read/export rule |
| --- | --- | --- |
| `ReservedFormPublicSnapshot` | Exact case/session/form release, ordered item/version/family refs, learner-facing instructions, prompts, options, public method version/limitations and public-body hash actually selected for that reservation. No answer key, accepted-answer set, hidden rubric rule, private method payload or private package hash. | Exact owned session/history/replay and owner export may return **only this safe selected snapshot**. It is labeled *reserved for possible delivery*, not proof the learner saw it. Retired/missing current bank does not replace it with latest. |
| `ScoringSnapshotPrivate` | Immutable exact private key/rubric/method package or protected reference sufficient to score the reserved form at its original release. | Server grading only after owner/session/access checks. Never returned by catalogue, reservation, pre-submission history, validation error, Today, or bulk profile export. No unserved bank list or low-entropy key digest is exposed. |

Submission stores exact raw answers, immutable accepted receipt and permitted feedback tied to the reserved release/method. An owner export of a **submitted** session includes its safe reserved form snapshot, raw own answers, accepted feedback and exact method/version refs, but not the private scoring package beyond answers already explicitly disclosed by accepted feedback. An owner export of an **abandoned or reserved** session includes the safe selected snapshot and exposure/reservation status, but no feedback or correct answers. If no snapshot was durably selected, return a typed unavailable reason rather than current/latest content. Export is complete for the held own learner-facing snapshot and personal records, while protecting unserved bank and keys. Case deletion removes both representations and all related journal/receipts; no hidden tombstone survives to preserve an “unseen” claim.

The source stage must bound snapshot size, protect the private package at rest, and verify release/option equality between the reservation receipt, served response, submission, history and export. A later key/rubric change requires a new release and does not regrade an accepted receipt. The existing `StudyAttempt` table and its export wire shape remain unchanged. All controls are **NOT_RUN**.

## 3. Future Stage4B reservation provenance and limited unseen claim

Create a durable case-owned `coverage_started_at` UTC timestamp and journal schema/version before the first Stage4B diagnostic or future practice delivery that can share a diagnostic item family. Do not infer the start from browser history or from the oldest surviving exposure row. The cutoff is an **instrumentation boundary**, not evidence about previous external study. On case deletion it is deleted; a recreated case has unknown prior exposure. The current 39 familiar practice items stay excluded regardless of cutoff.

One transaction chooses an eligible exact form, persists its safe public snapshot/private scoring binding, records all item/family exposures with `reserved_at` UTC, and commits before a prompt response is sent. `reserved_at` proves a server reservation and burns those families even if the tab is abandoned or the response is lost. Optional `delivery_attempted_at` may record server send attempt; neither timestamp proves receipt, reading or learning. Do not name a pre-response timestamp `first_delivered` or expose `seen_by_learner=true` without an independently defined observation contract.

Within this boundary, “unseen” means **no earlier reservation or instrumented delivery of that item family in this case journal since `coverage_started_at`, plus exclusion of the known 39 familiar items and registered aliases**. It does not mean new to the person, device, another case, external practice, pre-journal period or deleted history. If a future practice route can present a bank family without journaling before prompt, that family is not eligible for the unseen diagnostic claim until its coverage is restored and reviewed. Text/hash similarity is only an exclusion aid, not proof of semantic independence.

Same UUID+case+intent replays the same reserved session/snapshot; different intent conflicts. Concurrent overlapping form reservations must have one winner or an honest no-unseen/conflict response. Own history/replay after preparation expiry returns the saved safe snapshot, while starting a new session or submitting a new response follows the native preparation-access gate. Do not consume research quota, replace a form with “latest,” or turn a reservation into a completed diagnostic. Proposed lost-response, abandonment, concurrent-family, cutoff, expiry, export/delete and second-browser controls remain **NOT_RUN**.

## 4. Preservation and acceptance boundary

Stage4A remains a small opt-in metadata/coverage increment with no new diagnostic, content bytes, publisher API, learner rows or changed legacy practice receipts. Unknown rights/reviewer/edition/syllabus status cannot become `published` or `complete_for_approved_syllabus` by a registry projection. Stage4B remains separate and requires real lawful original bank, approved rights/reviewer/key/method evidence, private packaging, exposure persistence, privacy/export/delete controls and learner/teacher QA before release. A fixed small Reading observation form would still be uncalibrated and partial; it cannot report IELTS band, SAT score, mastery, official certificate or admission probability.

The proposed source path allowlists, test matrix and other limits in the original design remain proposals, not passes. No G1 gate result transfers to Stage4. Root is the sole source/Git writer and must reconcile fresh source/preimages and write-ahead after current frozen work before any application stage.

## 5. Exact external pins

| Artifact | SHA-256 |
| --- | --- |
| Original `STAGE4_CONTENT_DIAGNOSTIC_DESIGN_ONLY.md` | `1057440c8a2962f02484a69912d8e5edda2993169d23cf8fb7e4287f3f51d43f` |
| Independent `STAGE4_INDEPENDENT_DESIGN_REVIEW.md` | `bcf0f1a4ba0b2062da5f24abfa72a898f3cb01902cfcc8b83cf76218320b1d9a` |
| Native `backend/app/schemas/learning_schedule.py` | `a5c26ea689d67aa68cf46936adc5057c854613a99691259282ba5ca64ea684b6` |
| Native `backend/app/api/routes_profile.py` | `d9bd87d528f7c8545c3b6e1875d7924f09bb4bb2e63f5cf18db022e0fe0c235a` |
| Native `backend/app/models/study.py` | `cd48802f039ef76f507328af22eb27735fab56ea5a25071bdca522053af59acc` |

Native hashes are carried from the prior static review; this v2 made no new application read/import/run and does not claim source has been implemented. Original design and review are untouched. See the separate seal receipt for this v2's own hash.
