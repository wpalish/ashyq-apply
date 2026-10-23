# Qualified composite closure

**Accept the saved 13-stage composite: seven unchanged-input stages from the original full, four fresh frontend stages and two fresh E2E stages.** This is not a single `13/13` full run. The original `20261008T220925Z-check-75e57309` remains **FAILED12/13** with its two real demo failures preserved.

Only `journey.spec.ts:199` changed from `2 approved` to `2 chosen by you`; all other assertions, including subsequent documents/export actions, are identical. Lint/typecheck/build consume this file, so their old PASS was not carried: fresh `--suite frontend` passed all four stages at source head `74928d730a5d0a7bb94f82ed2d1cb3478bbb1034` (snapshot `504461ad033a386e7b93df6d701fc29a12c73aa2ca1a9098aeabeeff77ea026e`). Fresh `--suite e2e` passed both stages at the same head (snapshot `8737e461b2b0e25c8faed0e4f4a4d6611891271bbd7d55f26090f74ca7812b1b`). Demo reports **79 passed, one skipped**, no failures/not-run cases; auth reports **six passed**. Fresh units report **282 passes across 30 files**. Expected ErrorBoundary stderr is retained, not reclassified as failure.

Carried stages are Ruff, Ruff format, mypy, SQLite, PostgreSQL, pip audit and npm audit. All 940 backend files and the frontend types/format/social/workflow/package/config inputs they consume match original and fresh physical snapshots plus current source. The only non-documentary source-map change is the one E2E assertion; document/evidence metadata drift is separately recorded. Static Python path review found no backend caller of `journey.spec.ts`. No fake test skip or weakened assertion was introduced.

Original saved JUnit confirms **4369 unique backend IDs in each DB**, exact same identities as prior core, zero failure/error/skip. SQLite coverage is **95.27%** only; no PostgreSQL coverage claim. These are two executions of the same IDs, not 8738 unique tests.

All current 14 application/test pins match both corrected physical snapshots and their maps, including E2E hash `1ce58de26b37247892b1b7c10abe45640bc64a32c25d7e27b9bd8b4e467a1077`. Saved fresh head is the source checkpoint; this reviewer did not query Git status/HEAD. Fresh E2E status lists only six staged synthetic failed-run proof files; the stage source maps show no other executable/test change. Original full head `9a79bff7` and its first packet remain immutable.

Counts retain their original scopes: C2 files/C9 controls, A11=C9+2; B52, A54=B52+2; root91 is overlapping focused evidence, not a further 91 unique experiments. Private source-selection predicates have zero violations in all three maps; no private runtime data was opened. STOP remains `65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d`.

Root-owned synthetic preview endpoint was `http://127.0.0.1:5173/#/shortlist`, provider none/auth false, closed before the original full. Mobile geometry and qualified screenshots are root evidence; no browser action ran here. No Docker, hosted CI, live research, current admissions applicability, product completion or search completion is asserted.

This independent peer performed saved-artifact/JUnit/log parsing, static input review and opaque hash checks only. No tests, app imports, runtime/ports, SQL, Git, network/provider/model, labels/scorer semantic reads or primary edits. Known future UX/search gaps from prior review remain outside this bounded acceptance.
