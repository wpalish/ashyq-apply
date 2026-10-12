# G2 recovery exact-one test query repair: independent static review

**2026-10-12 · READ ONLY · PROPOSAL NOT APPLIED / NOT RUN**

Reviewed external `proposals/g2-recovery-test-types-repair1/SEAL.json` SHA-256 `15aa4d3a53eb666793fb04cc36c6e02b04daa13bd30ec0834ddbfde8c259dc35`. Its single preimage `frontend/src/App.preparation.test.tsx` is SHA-256 `8c74cbd18da3e9668e975442c24b31fa7829f225fff23bf730fed07093bfe6c6`, matching the current root file at review. The complete postimage is SHA-256 `406ad762023db5f3d55e71024c84ee27563358b622e4ef08da202c6284f3a490`.

The diff changes exactly four newly added Testing Library `getByRole('button', ...)` queries: three Shared route actions and one New case action. Each unsupported `{name: '…', exact: true}` option becomes an anchored accessible-name regular expression. `^…$` preserves the intended exact accessible name. No old test body, assertion, setup, runtime source or production behavior is altered. This directly addresses the reported TypeScript `ByRoleOptions` shape failure without weakening a check.

**Disposition:** finite static repair acceptable for root application and fresh static/native verification. This review did not import the app or run TypeScript/tests, so it does not claim the subsequent gate passed.
