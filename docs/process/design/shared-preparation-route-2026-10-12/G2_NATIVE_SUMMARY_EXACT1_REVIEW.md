# G2 native summary selector: independent exact-one review

**2026-10-12 · READ ONLY · TEST PROPOSAL NOT APPLIED / NOT RUN**

Reviewed `proposals/g2-native-summary-repair1/SEAL.json` SHA-256 `bf86d6616d3143f888e1021db22316e310f0c36c6dbf05be9877cc0707fcf963`, preimage `ba9e527016103492f291d7a450a9b071ce2c8487765c188eedf0b4ba0c104469` (matching current root `frontend/e2e/preparation.spec.ts`), and postimage `a4bd15cfc036c5621b1a9d1d5735c088d233cbf336e5e3867e160f5ca3335319`.

The sole change replaces the disclosure click's descendant `summary` locator with `:scope > summary` inside the already selected own-reviews `details`. This selects the parent disclosure rather than its nested reference summaries. The surrounding real review selection, preview/save, exact attempt, assertions, native API guards and production code are byte-identical. No old assertion is removed or weakened.

**Disposition:** narrow test selector repair is consistent with the reported desktop/mobile locator ambiguity. Requires a fresh static and native terminal run; this static review does not infer that either will pass.
