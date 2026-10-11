# Native gate binding review — 2026-10-11

**Verdict: STATIC_BINDING_VERIFIED; no concrete binding blocker found. Backend runtime acceptance remains PENDING in this review.**

Read-only review of the external preparation integration and saved static/frontend receipts. Parent reported active gate HEAD `777e9e23`; this review binds to file hashes below, without invoking Git or establishing commit identity independently. Application receipt records its earlier parent HEAD `11091904`. No test, app, migration, browser, provider, LLM, database or runtime execution was performed by this reviewer. Only this external audit document was written.

## Read coverage and source binding

- Read application/preparation/baseline receipts, expected pin maps, import repair receipt and patch, both static/frontend launcher sources, saved first and v2 static/frontend result/log/JUnit/source snapshots, the ordinary native bootstrap, and native launcher pin/preflight/argv/acceptance sections. No running backend result or phase log was reviewed.
- Compared metadata hashes for historical fixture paths only. Their underlying payload bodies were not opened or independently hashed. Closed current pilot, labels and heldout inputs remain outside scope.
- `APPLICATION.json` contains 30 reviewed applied paths: 15 backend proposal paths, 13 frontend proposal paths and two root E2E paths. All 30 recorded after hashes match the first static source snapshot. All 15 sealed backend proposal files retain their original proposal hashes.
- Native expected pins expand **547 → 557**: zero dropped paths, ten additions and six changed existing values. `PIN_REBINDING.json` exactly describes those sixteen changes, with matching before/after values; the other 541 values are unchanged.
- Native expected557 and v2 static snapshot625 share 511 paths; all 511 hashes agree. This is a scoped intersection check, not whole-repository equality.

### Ten added native paths

- `backend/app/api/routes_preparation.py`
- `backend/app/domain/preparation.py`
- `backend/app/models/study.py`
- `backend/app/payments/preparation.py`
- `backend/app/preparation/__init__.py`
- `backend/app/preparation/catalogue.py`
- `backend/app/schemas/preparation.py`
- `backend/migrations/versions/f1a2b3c4d511_study_attempts.py`
- `backend/tests/test_preparation_api.py`
- `backend/tests/test_preparation_domain.py`

### Six changed existing native paths

- `backend/app/api/routes_billing.py`
- `backend/app/api/routes_profile.py`
- `backend/app/main.py`
- `backend/app/models/__init__.py`
- `backend/app/models/applicant.py`
- `frontend/src/types.ts`

The first five are reviewed backend integrations. `frontend/src/types.ts` is the existing shared native dependency. No search path, provider setting, Fetcher policy, scoring criterion or closed quality evidence path was rebound by this extension.

## Import repair qualification

First native Ruff attempt remains an actual saved failure: **11 I001 diagnostics in 10 files**, exit1, `FAIL_OR_INCOMPLETE`; later steps were not run. The API test module had two diagnostics, including its local migration-test import group. Root repaired exactly those ten files.

For every repaired file this reviewer verified exact archived proposal and current source SHA256, the same top-level import inventory including aliases, and an identical AST after removing only top-level import nodes. All constants, decorators, class/function bodies, nested imports and assertions therefore remain exact at the AST level. The local API-test change only inserts an import-group blank line. No test assertion, selector or expected outcome was added, removed or weakened.

Imports execute during initialization, so this establishes an import-order/body-preservation qualification; it does not prove that arbitrary reordered modules can never change initialization timing. No concrete such blocker was identified here. Native runtime evidence is still required.

| Repaired path | Proposal SHA256 | Current SHA256 |
|---|---|---|
| `backend/app/api/routes_billing.py` | `2b758fa375fe980a4c655040f1b78685394ba8f1a1e40870db975285b205aa7a` | `2254a2ff5ca975d6d1516356c499738fb276b32fbc2431da47288635b69f485e` |
| `backend/app/api/routes_preparation.py` | `f98fdd452cc4d98432c24530ac5d34558ffeecb697bf872c0dcfbc8d111944cc` | `9468402ee1ba94377b5d1f1ddde0f5f5c7eb98212eeb2100f2f055af4f6aca5b` |
| `backend/app/api/routes_profile.py` | `80c7894848d35202ab8e428e06f6991e18b10cff04627021b5a4ffdfcd1bcad0` | `c410ce3b1682e772c200718a82ba8cdee7f68a315eed1ebe6faf39b2359eb1ae` |
| `backend/app/main.py` | `e5e8a5a6ddcc158792658c901d59c5ceef3af546b3f9bc5845be89008e118eff` | `f2e9b6b2fdff3c216f77b3d88d7fff1e3dc22e4c19c8f207909459af859c14ef` |
| `backend/app/models/applicant.py` | `5f5d98c1f4c7555ba444ed1028184fdc5e8c62f4d868d000bc014be95d429464` | `3e86e9b343b2d7f1ab247521641004f9dde3122d981dd8634a1716cc9eaaeeff` |
| `backend/app/models/study.py` | `7852a20d8235978e5cfaeb9828110a3df7ea79f153c47427745aac10cb3591ea` | `cd48802f039ef76f507328af22eb27735fab56ea5a25071bdca522053af59acc` |
| `backend/app/payments/preparation.py` | `03464423ce2b0a7c917a38a89e497fdf287ee589c86118ea470af9a2a2e0ac80` | `ab44ed538177c2ac765cd86ec326bb53c196c01927dc04565a9911fe50150a26` |
| `backend/app/schemas/preparation.py` | `8cae2435eda20de914313aaff734a28790dd3a0e7d2784559e00bdc4ac0500aa` | `c02c040d842a97a41240a4ee9735df86a2cd4f9d6bb4bc6160174fd16e6e62d8` |
| `backend/tests/test_preparation_api.py` | `9454636eff5a601b512601ecd65a75898a4849f81fb08a0b40010a4dfc4cdd46` | `cd8ab75b35869824c998473f085ea64b64ac166e663040a15d463706b35686ff` |
| `backend/tests/test_preparation_domain.py` | `6234322046285b8e283e7cc0bcc23fb8ca71283c8d39da6900c5069b96d2fa4a` | `44a2026015add0eb2d331f12a1ddc905ae186deae33391c478bbf1c71e28a802` |

## Saved static/frontend outcomes

| Receipt | Recorded outcome | Source binding |
|---|---|---|
| First static/frontend attempt | Ruff exit1; 11 I001 errors; later steps not run | 625 paths, before = after |
| v2 static/frontend | Seven steps exit0; `PASS` | Same 625 path set, before = after |

First→v2 changes are exactly the ten import-repair paths. The remaining 615 snapshot values are unchanged. These snapshots cover `frontend/src`, `frontend/e2e`, `backend/app`, `backend/tests` and `backend/migrations` (excluding cache files). They do not establish equality for all repository configurations, scripts, evaluation code, generated distribution assets or dependencies.

Actual v2 saved observations:

- Ruff check passed; format check reports **404 files already formatted**.
- Mypy reports success for **372 source files**, with existing informational annotation-checking notes.
- Frontend typecheck and lint exited0; lint reports **0 errors and 4 warnings**, not warning-free.
- Independently parsed JUnit: **54 suites, 465 testcases, 0 failures, 0 errors, 0 skips**. Saved unit log agrees with 54 files/465 tests.
- Frontend build exited0.

Both launcher versions preserve the same seven commands, existing nonblocking local-runner lock, network-denying OS sandbox invocation and source-before/source-after requirement. Their evidence output destinations differ. The failed first receipt is preserved separately.

## Native backend acceptance floor preserved

Ordinary helper copies match both the preparation copy receipts and their previously qualified origin bytes. `PIN_REBINDING` records `helper_executable_changed:false`. The origin manifest retains the earlier expected547 map; the separate rebinding receipt qualifies the current expected557 map. An unchanged old manifest alone is not treated as sealing the newly rebound map.

Native bootstrap/launcher retains:

- Literal full native selector `tests`, coverage over `app`, and `--cov-fail-under=92`.
- SQLite followed by PostgreSQL in full mode; fixed diagnostic mode is separately labeled and cannot represent full coverage acceptance.
- Zero failures/errors/skips, coverage ≥92, no outside attempts or guard startup failures, activated guards, app not preimported, restored IPv6, PostgreSQL events, source equality, confirmed shutdown and removed owned runtime in its acceptance conditions.
- The inherited numeric JUnit condition is `tests > 0`, not a hardcoded full-suite case count. Actual full collection cardinality must be inspected in the later terminal review; this report does not invent a numeric case floor.

OS-denial probes, private Unix PostgreSQL positive probes, SQLite/PostgreSQL execution and their final coverage/cardinality are **not runtime-proven by this static review**. No result from the running backend gate is included.

## Upcoming mobile change scope

The frontend author has sealed a separate, not-yet-applied proposal with exactly `frontend/src/App.tsx`, `frontend/src/styles/unimatch.css` and `frontend/e2e/preparation.spec.ts`. This review checked path membership only, not mobile behavior or its asserted prefix retention. All three are outside expected557 and the native helper’s frontend pin list (`types.ts`, `lib/format.ts`, `components/social.tsx`); all three are inside the static/frontend625 snapshot scope. The backend test source contains no references to these three filenames.

If integration remains restricted to those announced paths, it does **not consume or invalidate backend557 source binding**. It changes the later frontend source, so the current same-byte static/frontend receipt cannot qualify that later version: fresh static/frontend checks and the relevant mobile E2E gate are required. No mobile gate is claimed here.

## Exact receipt/helper hashes

| Path relative to exam-preparation-2026-10-11 | SHA256 |
|---|---|
| `harness/APPLICATION.json` | `d45f56302a1fedd041a65b30642aa5a13896f26cdeb5c9703439d1856c4d2c7e` |
| `harness/PIN_REBINDING.json` | `9b28770ee91aa9d8734f9f7c51dcb54fae0a5e6827bc83c91bdde9a87767ced1` |
| `harness/IMPORT_ORDER_REPAIR.json` | `82f6e381fd7864ee89c7f254ded10b9b3cfd6e795632ee2c4759e8d988c3965e` |
| `harness/import-order-repair.patch` | `52cb2e97c5f4787f0faeb1f795f0b11fa629c1c50e9ab758fb286954609cadf7` |
| `harness/expected-native-source-pins.before.json` | `6d55317d750035abb0ffdc621087dc80b58f423b270b77e23dde619c0540f12e` |
| `backend-full/expected-native-source-pins.json` | `98c41a1c8c83a892ff50d5762df0cc88330c1e2d2c35ff9c53fa77c4f722abec` |
| `evidence/static-frontend-final/result.json` | `fa42d9ec381cd8b52b10f365b5df37b5254aab382abd637c895cbcedd7fe037a` |
| `evidence/static-frontend-final/source-before.json` | `66f768ce46dda27a37b63179ed4db72eb319b43eab8db04eb15a84172bc1cf47` |
| `evidence/static-frontend-final/source-after.json` | `66f768ce46dda27a37b63179ed4db72eb319b43eab8db04eb15a84172bc1cf47` |
| `evidence/static-frontend-final-v2/result.json` | `cb73a4070eeddd965f7845269de5327ba5d08919dfc335fe84202c1ecd3aa2bb` |
| `evidence/static-frontend-final-v2/source-before.json` | `bea6e8a4cc94c5ebc7267b3ec83ec96b54cdda257eccaa0b99fbd597e44c70f5` |
| `evidence/static-frontend-final-v2/source-after.json` | `bea6e8a4cc94c5ebc7267b3ec83ec96b54cdda257eccaa0b99fbd597e44c70f5` |
| `evidence/static-frontend-final-v2/frontend-junit.xml` | `06d946bd11f1d9c41a19a62064bd0368df2e53673851487c0202177dcd194b5c` |
| `backend-full/run_full_backend.py` | `77954e61a8a7b8937c9433d65f91838829d0539c6a213771f3191c1d305d24ba` |
| `backend-full/pytest_full.py` | `ae987bac75d8d22c63be7448d67cefd04480cb1ff67894d18f3288090300ffe1` |
| `run_static_frontend_final.py` | `a06da56bb49581fd72d584d13ce0fffa0e887ee4ca2f301bd2e9ffd801add67f` |
| `run_static_frontend_final_v2.py` | `9f5a60924fb7719fd4c41ac4945cd7932446426a45b9d7ebca8fc3ec292c325a` |

## Remaining qualification

No dropped pins, import/body/assertion weakening or native acceptance-floor change was found. This review is sufficient to bind the saved static/frontend receipt and the current native gate inputs. Full backend terminal receipts remain pending; primary integration, production deployment, broad exam readiness and live search quality are not established. **Search quality remains NOT_MEASURED; GLOBAL_PROVIDER_STOP/UNSCORED remains unchanged.**
