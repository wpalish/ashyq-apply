# Auth recovery Legal label: sealed exact-two peer review

**2026-10-12 · READ ONLY · TEST-ONLY PROPOSAL NOT APPLIED / NOT RUN**

Reviewed `proposals/g2-auth-legal-label-repair1/SEAL.json` SHA-256 `89dd54dc2958b56e554f8d068ad61b247fef58f47e417395bce3c8173cd4b7f0`. Independently verified all four package members, current root preimage `4ed22753500706698f965d36b64f8c0ebdf80f224a8b5f719ac8c167c320234b`, and complete postimage `708b4a18f4cbcc8de2291114b67ebe76691b0036a9285d1e6688bca57595be24`.

The postimage is exactly two replacements in newly added `frontend/e2e/auth-journey.spec.ts` lines **698** and **702**: the button's expected accessible name changes from `Legal` to `Privacy & terms`. `exact: true`, both dismiss/accept dialog branches, navigation, original draft, clean-browser, logout and storage assertions are byte-identical. Native `App.tsx` renders `t('nav.legal')`; the English value in `i18n.ts:205` is `Privacy & terms`. The saved trace had blocked at the first nonexistent name, before exercising the later controls.

**Disposition:** finite test-label repair matches actual UI source and saved trace. It changes no application code, backend, wire or runner guard. Fresh static/Auth native terminal is still required; this review did not run it.
