# G2 terminal acceptance clock peer review

Status: **INDEPENDENT STATIC REVIEW / NOT_APPLIED / NOT_IMPORTED / NOT_RUN**. This report is outside the sealed proposal. No application source, tests, Git, HANDOFF, helpers, browser or runtime were changed or executed.

## Inspected bytes

- Final external packet `proposals/g2-acceptance-clock-final2/SEAL.json` SHA-256 `945260570213c7d22cc55b688a184f5cf9f0146bcaba20d58efe85d4bdc727be`; proposed API `fec7d50d7e29cbebea1d1d46bb2245ccb129f216974ba281fd2550013bbe37f9`; proposed test `84c166681851a448e24aaeb14bcdab4587777c47e3e137027760130c9fcfeee8`. I compared the final seal's member hashes with the actual two files, saved originals, README and DELTA.patch. The predecessor `proposals/g2-acceptance-clock/SEAL.json` SHA-256 `4f5ed8264824a6703507ff7a767260b3efbb4771fcc05a3a7c7a17dfc7d3564f` is preserved and byte-identical to final2's predecessor copy.
- Exact final2 preimages: API `f6dc485b26b9af6d04ba6e4a83d1da28ff1146b47ac3cab51c16d825d7bfb3d5`; test `13e04e275e8b3ffd263f513f7e382a53bd736eec4fc687ab8c5f179c209b3636`. Both hashes still matched the frozen application source at this read-only review; Git was not read.
- Native contracts: `backend/app/payments/preparation.py:15-43` returns the actual `PreparationAccess` with term `starts_at`/`ends_at` for an allowed paid term, and `development_only=True` with no bounds when payments are disabled. `backend/app/schemas/preparation.py:23-29` permits those nullable bounds. Native lesson GET still requires `version: Query(...)` in `backend/app/api/routes_preparation.py:486-498`.

## Source verdict

**No concrete blocking defect found in the inspected two-file delta.** Proposed `save_shared_route` still checks owner and an existing canonical write UUID before the new command gate. The new command runs the existing native preparation term lookup at one clock value, then takes a fresh UTC `accepted_at` *after* that actual SELECT. It rejects a changed local planning day as 409 before accepting the receipt, then rejects a paid term whose observed interval no longer contains `accepted_at` as 402. It does not perform a second Subscription query, rerun the allocator, change the receipt shape or weaken the original same-UUID replay. The native development branch remains allowed despite absent term bounds; it is still subject to the local-day preview check.

The new test attaches `after_cursor_execute` to the real engine, advances only the route clock after the command's second actual `SELECT ... FROM subscriptions`, asserts exactly two subscription reads, and checks 409 at local midnight versus 402 at term expiry with no DML and no changed synthetic DB snapshot. It does not mock the payment helper, access DTO, models, clock inside the payment helper, allocator or storage. The existing midnight test's iterator gains the one added terminal observation. This is meaningful source structure, not evidence of a passing run.

Final2 also corrects the existing combined expiry control's exact lesson request: it now supplies `params={"version": review_payload["version"]}`. Native lesson GET requires that query argument before entering its preparation access check, so the predecessor's no-version request would have tested 422 validation rather than the intended 402 expiry rule. The own saved attempt review GET still expects 200 after expiry. This test repair is narrow, preserves the UUID replay assertions, and introduces no new application route.

## Nonblocking verification boundaries

- The new parametrized control uses the paid-term branch. A direct **G2 save in native development mode** is not newly asserted here; `test_preparation_api.py:338-339` establishes the native access DTO's development behavior, while the proposed API's `development_only` branch is statically explicit. Root can add one focused acceptance assertion if the ordinary gates reveal a regression; this is not a reason to expand the two-file repair before an actual failure.
- The proposal observes a term interval returned by one real SELECT, then uses a second clock value. A concurrent independent billing mutation after that SELECT is not serialized by this patch; the accepted G2 bounded design never claimed a global payment writer lock. Native concurrency and terminal timing require the root's actual SQLite/PostgreSQL receipts.
- The lesson endpoint's mandatory exact version query remains in existing source and is outside this packet. No claim is made about a new lesson or score.

Final-seal reconciliation: final2's two source pins and preimages match the inspected files and frozen application bytes. The final2 seal remains **NOT_APPLIED/NOT_IMPORTED/NOT_RUN**; this static review does not substitute for the first-failure reproduction or post-repair run.
