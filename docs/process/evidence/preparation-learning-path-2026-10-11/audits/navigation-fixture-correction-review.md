# Navigation fixture correction — finite static closure

**QUALIFIED_STATIC_ACCEPT_PENDING_FRESH_ROOT_GATES.** Reviewer read saved source/receipts only. No tests, runtime, browser, Git or source changes were performed.

## Exact change

`frontend/src/App.preparation.test.tsx:7` replaces only the synthetic import:

```tsx
import { access, learningCatalogue as catalogue, plan, progress } from '@/screens/preparationFixtures';
```

Before SHA `8021082aab1534739a0cc6fa156536fee54494714bd21ded7be769d84df227db`; after/current SHA `a747eb16c7b3653b3e31087e65d2ab7ac4fa4d855914861cef9b7a432eedaff6`. Replacing this one import in the preserved preimage reconstructs the current file byte-exactly. All five test bodies, assertions, helpers, setup and transport-denial check remain unchanged. No assertion was skipped, loosened or removed.

## Requested opt-in and mock shape

- Actual screen `:117–123` requests `learning-pack-2026-10-11-v1` for catalogue/history, rejects the wrong catalogue version, requires every summary version, and requires matching history catalogue/version-qualified completion metadata.
- `preparationFixtures.ts:37–40` supplies that opt-in catalogue version and the three legacy summaries with their correct individual `starter-2026-10-11-v1` content versions. Its track order/IDs still match those summaries. This is deliberately a bounded synthetic navigation fixture, not a nine-lesson backend catalogue or content-coverage proof.
- Existing `progress()` at `:58–64` already supplies the requested learning catalogue version, correct profile ID and `completed_lessons`; no progress fixture change is needed.
- Optional client query parameter remains implemented at `client.ts:426–439`; no-argument API behavior and legacy catalogue export are untouched. Production version and ownership fences remain active.

Current PreparationScreen SHA is still `bc84b35a426d654bdb541cfcd303d7165cc5bc0bb8d667668ddc73fde28c1e3a`, equal to the independently reviewed display postimage. The correction does not alter that screen, its access/render labels or its guards.

## Preserved first whole result

Saved original JUnit contains **510 controls: 508 PASS, 2 FAIL, 0 ERROR, 0 SKIP**. Both failures are the old navigation mock tests for direct evidence and selected-programme goals. The fixture's old starter-only catalogue is statically incompatible with the valid new opt-in fence. The original raw output/JUnit remain intact; this closure does not relabel that failed run as accepted. Saved receipt is `FAIL_OR_INCOMPLETE`, with unchanged source and no build step recorded after unit failure.

The new alias is a precise fixture-contract repair, not a production bypass. Fresh whole frontend and native/backend execution remain root's responsibility. No completed result for corrected bytes is asserted here.
