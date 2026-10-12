# Auth old question selector: sealed exact-one peer review

**2026-10-12 · READ ONLY · TEST-ONLY PROPOSAL NOT APPLIED / NOT RUN**

Reviewed `proposals/g2-auth-question-selector-repair1/SEAL.json` SHA-256 `8320c8352accb5bc8e6988287cdcfb91e8e50d9d6573021bc7b1e5a632077e62`. Independently verified all four package-member hashes, the current root preimage `f3d9be295640cc157ebdd591d7cb5f4a817cf82ab415bca8af6ac336f4ce62c4`, and postimage `4ed22753500706698f965d36b64f8c0ebdf80f224a8b5f719ac8c167c320234b`.

The complete postimage is an exact one-expression replacement at old Auth test line 76: `page.locator('fieldset')` becomes `page.locator('fieldset.preparation-question')`. The existing fieldset tag, loop order, correct answers `4/20/30`, radio accessible names, receipt wait and all later assertions remain byte-identical. Production source and runner guards are outside this packet.

The saved Auth failure's visible SAT Math radios coexist with always-mounted hidden shared-route fieldsets, so the narrowed selector targets actual `PracticeSession` question groups. The separately preserved correction `G2_NATIVE2_AUTH_SELECTOR_DIAGNOSIS_CORRECTION.md` fixes the earlier mistaken legacy-schedule attribution; it does not change this test repair.

**Disposition:** acceptable finite test-only repair for fresh static and native verification. This review did not run either gate and makes no claim about their outcome.
