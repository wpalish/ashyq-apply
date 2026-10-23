# G2 Auth Legal label repair 1

**SEALED EXTERNAL TEST-ONLY PROPOSAL — NOT APPLIED / NOT IMPORTED / NOT RUN**

## Exact scope

One existing file, `frontend/e2e/auth-journey.spec.ts`. Only the two new-test button name selectors at lines 698 and 702 change from `name: 'Legal', exact: true` to `name: 'Privacy & terms', exact: true`. All callbacks, values, assertions, timeouts, guards and other source bytes remain unchanged. This retains the previous question selector repair.

## Grounded reason

Root reports the fresh Auth3 run `20261012T050846Z-auth` passed 11 tests and timed out in the new recovery test before Legal navigation at line 698; this was before logout. The source-only inspection confirms the actual English `nav.legal` value is `Privacy & terms` at `frontend/src/lib/i18n.ts:205`. This packet changes the test labels to match that current native interface. It does not change any application label, routing, access or recovery behavior. The saved run was not independently executed for this proposal.

## Pins

- Exact root preimage SHA-256: `4ed22753500706698f965d36b64f8c0ebdf80f224a8b5f719ac8c167c320234b`.
- Full proposed postimage SHA-256: `708b4a18f4cbcc8de2291114b67ebe76691b0036a9285d1e6688bca57595be24`.
- Source line count unchanged: 731.
- Only differing lines: 698 and 702.
- Reversing the two literal label substitutions restores the exact preimage.

## Members

- [Preimage](preimages/frontend/e2e/auth-journey.spec.ts)
- [Full proposed postimage](files/frontend/e2e/auth-journey.spec.ts)
- [Exact two-line diff](diffs/frontend/e2e/auth-journey.spec.ts.diff)
- [Member SHA manifest](SEAL.json)

## Boundaries

No app, helper, Git, runtime, wire or guard change. No import, test collection, gate or browser run. Root alone may apply after verifying the current preimage and perform separately authorized fresh gates. This proposal itself has no pass result.
