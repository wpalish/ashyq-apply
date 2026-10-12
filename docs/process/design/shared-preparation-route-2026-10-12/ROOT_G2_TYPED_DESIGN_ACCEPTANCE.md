# G2 — root acceptance of bounded design

2026-10-12. **DESIGN_ACCEPTED / NOT_APPLIED / NOT_IMPORTED / NOT_RUN.**

Root read the shared persistence v2 and both typed contract versions, and independently reviewed the complete v1→v2 delta. Independent persistence review v2 closed D1–D4. The accepted scope is an explicitly selected personal IELTS Academic/Digital SAT route over existing exact content, with one shared daily/weekly capacity and immutable applicant-owned history. This acceptance is not implementation, migration, full-course or admissions-quality proof.

Accepted design sources:

- `proposals/g2-design/SHARED_ROUTE_PERSISTENCE_SPEC_V2.md`, SHA256 `27bc906301708c604c723e1a1d2fdb6ae79f454750871b4d6f82a98cd4728de3`.
- `proposals/g2-design/TYPED_CONTRACT_DESIGN_V2.md`, SHA256 `3916138d910830dfb0b484f2a562a488889798985f11ac2abdb2ffcd7282f37c`.
- `G2_DESIGN_REVIEW_V2.md`, SHA256 `a2330ee13f962d090d3932922572aa5c44cff752f07593f53db24d9bd24caa5c`.

## Resolved before any source proposal

1. Reference-only immutable PUT/replay/history receipt is separate from current authorized evidence and review flags; no historical premium evidence cache.
2. Lost same-UUID CAS/uniqueness race rolls back and rereads the accepted own UUID receipt, preserving exact replay and atomic current/history updates.
3. Legacy technical revision protects preview→save; structural fingerprint protects read-time change detection. Old self-ticks do not stale accepted G2 or infer mastery.
4. Saved GET probes own result metadata per goal. Missing/foreign are indistinguishable; rejected, locked and unavailable goals preserve the original plan with explicit reasons. New writes retain strict whole-selection validation.
5. Full accepted allocation is persisted, including exact refs, action/slot IDs, dates, minutes, capacity, unallocated reasons and exam timing. GET/replay never reruns the allocator.
6. Historical exact-version reviews use the actual owned resolver, including versions absent from the current catalogue. Unavailable refs are retained, never substituted.
7. Expired lesson queue heads are drained before fit checks so an own review with an entered retake window can still be allocated.

## Implementation limits

Unknown official exam applicability does not prevent explicit personal practice; it never becomes an accepted programme route, merged numeric minimum, waiver, probability or official score. There are only the existing two exam choices, three tracks and nine lessons/39 questions. Twenty-minute lesson allocations are planner capacity, not a learning-time prediction. Review minutes are explicit applicant input. No new course material or automatic admission-date inference.

No shared cross-writer source lock is promised. Accepted manifests record the observed source; current GET can require review after changes. Legacy calendars retain their API/history and do not add a second active Today workload once G2 is explicitly selected.

Source proposals and active-branch implementation require a new root HANDOFF write-ahead after G1 has a terminal, qualified release. This document changes no source, helper, runtime, Git, production or stopped workflow.
