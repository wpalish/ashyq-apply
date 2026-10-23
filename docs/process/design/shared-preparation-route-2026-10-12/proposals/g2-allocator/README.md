# G2 shared route — sealed typed/pure proposal

**2026-10-12 · NOT_APPLIED / NOT_IMPORTED / NOT_RUN.** This package contains exactly three proposed new backend files. Root owns application, Git, runner binding and execution. AST parsing and byte comparison here are not Ruff, mypy, pytest, runtime, persistence or product acceptance.

## Scope and authorization

Root reported released G1 `ed6ae6fe` / Draft86 and new `task/shared-preparation-route` write-ahead `6f6c736f`. The current HANDOFF §5 authorizes only these initial three new paths. Their application preimages were absent when this seal was written. The accepted typed and persistence V2 documents stay immutable; their current pins, the ordinary read dependencies and the exact HANDOFF entry are in [SEAL.json](SEAL.json).

The historical [PRE_SOURCE_INSPECTION.md](PRE_SOURCE_INSPECTION.md) and [READ_ONLY_INSPECTION.json](READ_ONLY_INSPECTION.json) describe the earlier period when source proposals were not yet authorized. They remain unchanged. New source bytes were created only after root's separate G2 authorization. The peer's [draft review](G2_ALLOCATOR_DRAFT_REVIEW.md) is preserved; its draft hashes differ from this sealed package.

| Proposed new path | Bytes | SHA-256 |
| --- | ---: | --- |
| `backend/app/schemas/shared_route.py` | 21370 | `c9fde4116e9925cd71988c45a800b1d3e5e4ddff4eadfb30b69326d9444c8cdc` |
| `backend/app/domain/shared_route_allocator.py` | 13083 | `fc151bb887556febcccafe706353e952b5d962c2f158b91eec21e667aadc8f76` |
| `backend/tests/test_shared_route_allocator.py` | 39052 | `e2edee3f7d81dec126789e6100ce75d783be4f4ae9c1c37f6e70a86e90cbdbb7` |

## Exact callable contract

```python
allocate_shared_v1(
    value: SharedRouteInputV1,
    *,
    catalogue: FrozenExactCatalogue,
    own_reviews: Sequence[ValidatedOwnedReviewV1],
    planned_on: date,
) -> SharedAllocationV1

canonical_input(value: SharedRouteInputV1) -> dict
```

- Input: exact ordered 2–20 result IDs; one local ISO start date, IANA timezone and weekday set; one weekly 30–1260 minute budget; one or two explicitly ordered IELTS Academic/Digital SAT exam choices; explicit dates and buffers; optional, partially supplied personal targets; at most 400 exact own reviews with explicit 1–1260 minute allocations. Confirmations must be literal `True`. Numeric target strings, booleans, null components and nonfinite values are rejected; omitted target components are never filled. `personal_targets=None` and an empty target object remain valid.
- `FrozenExactCatalogue` accepts exactly the current nine lesson references in native track order with the original starter/pack versions and separately supplied strict availability. It is a caller-frozen public identity snapshot, not an app dispatcher call. The three legacy reference classes/union and content bytes remain unchanged; the new schedulable subset uses the original `LessonRef` and `AttemptReviewRef` classes.
- `ValidatedOwnedReviewV1` is upstream-supplied exact receipt/exam/availability data. The pure function checks exact requested UUID/ref/exam agreement and the known current track. It does **not** establish DB ownership or invent a historical exam association. A trusted historical receipt may be available with `lesson=None`; the future adapter must use the actual owned receipt resolver, not current catalogue membership or the latest-20 display list. Unknown historical association must be rejected upstream.
- `planned_on` is an explicitly supplied `date`, with no clock call. The function revalidates/copies Python snapshots before any JSON conversion, preserves caller input lists/refs/targets, and neither reads nor writes persistence.
- Output retains all selected exact lessons once, every whole scheduled or unallocated action, one shared capacity ledger, entered date/buffer calculations, stable IDs and a digest. Readiness stays `not_assessed`; programme applicability stays `unknown`. These are personal practice actions, not programme cover edges, official minimums, readiness predictions or scores.

## Deterministic allocation

IELTS preserves its four Reading lessons. SAT interleaves the three Math and two Reading/Writing lessons while preserving each track's order. A current exact review follows that lesson; historical exact reviews follow current lessons in explicit input order. Current lessons retain exactly 20 planning minutes; reviews retain the applicant's entered minutes.

One local daily cap of 180 and one entered weekly budget apply across both exams. Whole unavailable or oversized actions are removed with reason precedence `version_unavailable` → `too_long_for_day` → `too_long_for_week`; no shrink, split or substitution. The cyclic exam cursor survives dates. Expired heads drain before fitting, including when only a still-open retake review remains. Entered first/retake dates of either exam are excluded globally. The ledger contains ascending local Monday keys, including zero-use eligible weeks. The final classification boundary is the last actual visited date, or planning start if none; it never fabricates a horizon-plus-one date. The 400-slot cap preserves unscheduled actions. Calendar overflow is a controlled validation error.

Canonical input preserves programme/exam/review array order and only supplied target fields; only weekdays are sorted as a set. Exact action identity excludes programme IDs and scheduled date. Occurrence identity binds the action, local date and ordinal zero. The allocation digest binds canonical inputs, exact catalogue/availability, ordered accepted output and the supplied planning date.

## Draft findings reconciled in the final bytes

- **F1:** leading/trailing whitespace in any selected result ID now rejects the entire selection without trimming. Exact order remains preserved. The new literal controls include space, tab and newline cases.
- **F2:** `DatedSlot` and `UnallocatedAction` now validate the prescribed SHA-256 action derivation from exam and the exact original reference. Scheduled occurrences validate action/date/ordinal-zero identity. Current lesson allocations cannot be changed from 20 minutes. Known lesson/track association is still checked at allocation level.
- New corruption controls use well-shaped wrong hashes and altered lesson minutes. The known-track and calendar/daily-cap controls carry independently computed correct literal hashes, so a hash failure does not mask the specific guard under test. SHA anchor expectations are literal and independent of application helper output.

**Trust boundary remaining for later integration:** output DTO checks cannot bind own review minutes/references to a separate accepted request or authenticate a client payload. The future receipt writer/reader must bind and verify the complete server-accepted request/allocation/catalogue snapshot and digest. A fingerprint is not ownership, a signature, official correctness or learner attainment. Saved GET/replay must read the persisted full allocation without reallocating it; that wiring is outside this package.

## Test proposal and qualification boundary

The test file contains **51 test functions / 142 cases expanded statically from literal parametrizations**. Actual pytest collection and results are **NOT_RUN**. The proposal covers literal nine-reference queues, explicit priorities, action conservation, ISO-year/DST/Monday accounting, one daily/weekly ledger, zero-use weeks, whole oversized/unavailable reviews, old-version own reviews, expiry drain, global exam-date exclusions, no-eligible-date versus elapsed-window behavior, the 400-slot cap, optional targets/strict native types, finite typed-snapshot rejection, calendar extremes/overflow, stable identities, immutable caller inputs and restored-output corruption.

There is no test claim for real DB ownership, two-session SQLite/PG CAS, preview/save, receipt persistence/replay/current-state redaction, legacy coordination, case/account export/delete, frontend, native browser, official requirements, live search quality, full course completeness or production deployment. These remain separate bounded stages.

## Root next step

1. Review this exact seal against accepted V2 and the preserved peer finding text; confirm all three native preimages are still absent and dependency pins unchanged.
2. Apply only these three new files as the sole root writer. Any formatting/static repair must retain this original package and record the new delta and source pins.
3. Bind the approved isolated runner to the actual frozen application bytes before imports. Run native Ruff/format/mypy and the focused pure tests; preserve the complete first failure and cleanup receipts. Do not report the statically counted cases as passed tests.
4. Separate later write-ahead for route/persistence/legacy shared CAS/export/delete/UI/native acceptance. No G1 gate receipt qualifies G2.
