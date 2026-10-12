# G2 Auth question selector repair 1

**SEALED EXTERNAL TEST-ONLY PROPOSAL — NOT APPLIED / NOT IMPORTED / NOT RUN**

## Scope

Exactly one existing test file: `frontend/e2e/auth-journey.spec.ts`. At line 76 only, replace `page.locator('fieldset')` with `page.locator('fieldset.preparation-question')`. The question index, original values `['4', '20', '30']`, radio matcher and every assertion remain byte-identical. No application, API, storage, guard, helper, Git or runtime change is part of this proposal.

## Evidence and reason

Root requested this bounded test-only repair after native2 Auth failed before practice submission. The independently saved [diagnosis](../../G2_NATIVE2_AUTH_OLD_SELECTOR_DIAGNOSIS.md) identifies hidden legacy schedule fieldsets preceding the lesson question fieldsets. Scoping to the native existing question class preserves the intended original controls. This saved failure is not a product readiness result.

## Pins

- Root source preimage SHA-256: `f3d9be295640cc157ebdd591d7cb5f4a817cf82ab415bca8af6ac336f4ce62c4`.
- Proposed full postimage SHA-256: `4ed22753500706698f965d36b64f8c0ebdf80f224a8b5f719ac8c167c320234b`.
- Source line count unchanged: 731.
- Only differing line: 76.
- Non-selector bytes on that line and all other lines are unchanged.

## Files

- [Exact preimage](preimages/frontend/e2e/auth-journey.spec.ts)
- [Full proposed postimage](files/frontend/e2e/auth-journey.spec.ts)
- [One-line unified diff](diffs/frontend/e2e/auth-journey.spec.ts.diff)
- [Immutable member manifest](SEAL.json)

## Application and verification boundary

Root is the sole application writer and must re-check the current preimage before applying. Fresh static and Auth native runs belong to root's separately authorized gate. No application or test import, collection, execution or browser action was performed for this packet.
