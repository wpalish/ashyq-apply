# Auth3 new recovery test: Legal button wait diagnosis

**2026-10-12 · READ ONLY · SAVED TRACE/SOURCE ONLY · NO RUNTIME ACTION**

Saved terminal: `g2-execution/evidence/e2e/20261012T050846Z-auth`. The test log records **11 passed** and timeout of the twelfth, newly added recovery scenario. The reported `browserContext.close` at `frontend/e2e/auth-journey.spec.ts:730` occurs in `finally` after the timeout and masks the waiting action; it is not the initiating failure.

The saved `trace.zip` `test.trace` has `pw:api@45` begin at line **698**, title `Click locator('.journey-menu').getByRole('button', { name: 'Legal', exact: true })`, with no matching completion event before timeout. Its immediately preceding menu-summary click completes. No later test action is recorded: the scenario did **not** reach accepted Legal navigation, a clean-browser check, or logout. The final error-context snapshot's Welcome back screen therefore cannot establish a logout ACK from this scenario.

Current source explains the wait: `frontend/src/App.tsx:70` assigns the Legal screen label `nav.legal`; the menu button at `:400–405` renders `t(item.label)`. In English, `frontend/src/lib/i18n.ts:205` defines that label as **“Privacy & terms”**, not “Legal”. The new test asks for the nonexistent exact name at both `auth-journey.spec.ts:698` and `:702`.

**Narrow proposal for root:** change only those two new test queries to `getByRole('button', { name: 'Privacy & terms', exact: true })`. Keep the dismiss/accept dialogs, route/form/storage assertions, second clean browser, logout ACK checks and all old tests intact. This is a test selector mismatch; no application navigation/logout defect is established by this saved trace. A fresh static and Auth native terminal remains necessary.
