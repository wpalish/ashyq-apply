# Correction to saved Auth selector diagnosis

**2026-10-12 · READ ONLY · original diagnosis preserved**

Corrects the causal attribution in `G2_NATIVE2_AUTH_OLD_SELECTOR_DIAGNOSIS.md` SHA-256 `3303f033fa2519b6206421e1f80e546d37a29a6d868daa9a9a62e7b91e68cdb4`. The recommended exact question-fieldset locator remains valid; the original explanation named the wrong preceding fieldsets.

In `frontend/src/screens/PreparationScreen.tsx:313–326`, the legacy schedule's disabled fieldsets are under `mode === 'schedule'` and are **not mounted** during the saved Auth failure, where Practice is pressed. The actually preceding fieldsets come from `:327–328`: `SharedRoutePanel` remains mounted inside `<div hidden={mode !== 'shared'}>` during Practice, and its form has fieldsets at `SharedRoutePanel.tsx:555,559,586`. Those hidden shared-route fieldsets precede `PracticeSession` question fieldsets at `PreparationScreen.tsx:449–462` in DOM order. The old global `page.locator('fieldset').nth(index)` therefore enters the hidden shared-route form and waits for a radio that is not there. The saved error snapshot shows the correct visible SAT Math radios `4`, `20`, `30`.

The finite repair remains test-only: scope line 76 of `frontend/e2e/auth-journey.spec.ts` to `fieldset.preparation-question`, preserving the original three answers and every existing assertion. No practice or shared-route application bug is established by this terminal failure. Fresh native execution is still required.
