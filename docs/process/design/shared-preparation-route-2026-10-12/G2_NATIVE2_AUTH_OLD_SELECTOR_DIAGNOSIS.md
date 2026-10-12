# G2 native2 Auth: old practice selector diagnosis

**2026-10-12 · READ ONLY · SAVED TERMINAL ONLY · NO RUNTIME ACTION**

Saved run: `g2-execution/evidence/e2e/20261012T045632Z-auth`. The saved Playwright `error-context.md` reports old test `frontend/e2e/auth-journey.spec.ts:72–121` timing out at **line 76**, waiting for `page.locator('fieldset').first().getByRole('radio', { name: '4', exact: true })`. The same saved page snapshot shows the SAT Math lesson visible, its three question groups and radios `4`, `20`, `30`, and a disabled `Submit practice` button. Thus the observed failure is before answer submission; no failed practice write or G2 recovery behavior is evidenced.

Current `frontend/src/screens/PreparationScreen.tsx:315–324` renders hidden, disabled legacy schedule `fieldset` elements ahead of the practice form. The actual lesson question controls render as `fieldset.preparation-question` at `:449–462`. The global `fieldset` index in the old Auth test now selects a schedule fieldset instead of the first question, so Playwright waits until the test timeout. This is a test locator drift caused by the added page structure, not evidence that the correct radios disappeared.

**Narrow repair for root to review:** at the old test's line 76, scope the existing loop to `page.locator('fieldset.preparation-question').nth(index).getByRole('radio', { name: value, exact: true }).check()`. Keep the original `['4', '20', '30']`, receipt wait, submit, persisted-attempt assertions and second-browser checks byte-identical. No application/source guard or old assertion should be removed. Re-run fresh static and Auth native after the exact test-only change; the saved failure does not establish a later result.
