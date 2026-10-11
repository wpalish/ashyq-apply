# Native Demo/Auth — independent terminal receipt review

**2026-10-11 · QUALIFIED LOCAL NATIVE E2E PASS · saved-only review.**

Независимо прочитаны завершённые run metadata, JUnit, terminal logs, relevant API access logs, consumed native tests/config/helpers, before/after source pins и owned cleanup. Reviewer не запускал приложение, браузер, тесты, API, Git или провайдеры и не менял source. Reviewer ранее авторствовал backend foundation; это независимая проверка receipts и сохранения assertions, а не слепая приёмка backend кода или whole product.

## Фактические terminal результаты

| Phase | JUnit unique cases | PASS | FAIL / ERROR | SKIP | Exit | XML time |
| --- | --- | --- | --- | --- | --- | --- |
| [20261011T140255Z-demo](../evidence/e2e/20261011T140255Z-demo/run.json) | **92** | **91** | **0 / 0** | **1 inherited** | **0** | 126.744346s |
| [20261011T140504Z-auth](../evidence/e2e/20261011T140504Z-auth/run.json) | **7** | **7** | **0 / 0** | **0** | **0** | 11.427113s |

JUnit testcase counts independently summed; identity is **testsuite hostname/project + classname + name**. Desktop/mobile copies must not be collapsed into one case. Totals: **99 phase-qualified cases,98 PASS,1 inherited skip**. [Sequential wrapper](../evidence/e2e-terminal.json) records demo→auth exit0 and PASS; this agrees with actual JUnit and terminal logs, not expected counts.

Demo contains the same **80 old native cases:79 PASS+1 skip**, plus **12 new preparation cases:6 scenarios×desktop/mobile, all PASS**. The sole skip remains desktop `community.spec.ts / every community screen is reachable on a phone`; it was present before this work. Auth contains all six old cases plus the new second-session preparation case, all seven PASS. No new preparation skip or retry was substituted for a failure; native configs retain one worker, retries0,120s test timeout and20s expect timeout.

## What the executed new controls establish

The exact consumed [preparation.spec.ts](../../../integration-2026-10-11/source/frontend/e2e/preparation.spec.ts) uses normal native clicks/checks and real local API requests:

1. A Delft programme is actually saved from Find, selected in Preparation and exposes `IELTS writing` plus explicit development starter access. The retained same-selection regression path completes.
2. A real Reading lesson GET opens by ordinary click. Submit stays disabled until every radio is answered, then a real POST returns3/3 formative feedback and the matching attempt UUID. Exact full `academics` JSON is compared before and after submission and after replay; no official-score mutation was accepted.
3. Reposting the identical request **sequentially** returns the same database row ID. Reload then real progress reports exactly one attempt with the same UUID; own profile export contains exactly one `study_attempts` row. This proves sequential idempotent replay and persisted history for this path.
4. At320/390, the real six-destination navigation remains one row, keeps full accessible names,≥44px targets and labels≥12px, and its measured main bottom reserve covers the fixed bar plus the tested gap.
5. At320/390, the final Restart action has a real centre hit-test,≥44px height and lies above the bar; Submit's bottom is also measured above it. This test does **not** independently hit-test/click Submit at every custom width. The original normal Submit click does pass under the mobile project.
6. Native closed details retain actual quote/source/scope and open/close by normal click. At320/390, actual catalogue URL text/hrefs equal API metadata; document overflow and expanded layout viewport checks pass. All three starters open by normal hit-testable click and return real lesson GET200, with choice targets≥44px. The original mobile Start Reading path that failed earlier remains intact and now passes.

Auth's new [case](../../../integration-2026-10-11/source/frontend/e2e/auth-journey.spec.ts:72) submits a real SAT Math attempt, then calls `newSession(browser)` to create a fresh context without copied cookies/localStorage. It logs into the same synthetic account, reads saved progress through the actual API and checks the exact attempt UUID. Both contexts are closed. This is server persistence across two sessions of one account, not a foreign-tenant authorization test.

Saved API logs independently corroborate successful lesson/attempt/progress/export requests in both Demo contexts and successful login/progress in Auth. The detailed JSON assertions above are confirmed by the passed, source-bound native cases; this reviewer did not independently query the saved database. Screenshot/visual review is root's separate scope.

## Exact source and assertion preservation

Both runs contain **395 source entries**. Independently checked `before==after`, identical maps across phases, and all395 current source hashes match those maps at review. Only ordinary app/native test/config/migration source is hashed; stopped evaluation inputs were not read. Both three-entry saved harness maps match their snapshots and current helper bytes.

- Eight non-preparation E2E paths remain hash-identical to the first attempt, including original helpers/configs. The old80 Demo testcase identities/statuses are exactly unchanged.
- Auth preimage `f569d646bba65985e039764033db59b9abdf875e9e029b4e6c7f84ff513d45c1`→current `c8867af545bcf6f8c8ef5394a3eac49b3e1b78ca47ea4d1955afc723a40d1999`: independent text diff contains insertions only, preserving all six original bodies/assertions.
- Original three preparation tests remain a complete5,311-byte prefix, SHA `b3e092f8409bca0da2b731642e82886c91dcc497ac51233494a79233f2bf2e09`. Current six-test file is byte-identical to the sealed reviewed UI proposal, SHA `35fcc0c7812eb3688832158998103310232803e30ec91a36426e7c525adf0851`. The previously reviewed five-test13,218-byte prefix is also retained. No force-click, old assertion weakening or raised timeout was introduced.

| Receipt | Demo SHA256 | Auth SHA256 |
| --- | --- | --- |
| run.json | `1669eae9c774601b47844cbd54409af30d3f21da032963fe550e52e7a60b075d` | `c07b08adb3d9ac9f529c4ba341f17ad71bbcceaf0b0429992b37d3c9512ae4dd` |
| junit.xml | `89e8d1a1eae8a5449c4edcc0ecace5636e74c2c8d0f9a6723107c196bcfd3751` | `8b15b0f7d246986ceac615f5387dcbf56d05b67c0240f8d77951d86e9d32fbbb` |
| source-before.json / source-after.json | `998d752e77df283c061695424ab9a1b523430b4a05030230e9cea7f698600e58` | same |
| harness-before.json | `55524637ee2fdf4e844ec08934e24bbe8869e50c31f6a5ab8e68059100d848cd` | same |
| owned-cleanup.json | `f1f372d057d961d422267b1d97d536fd71886ca1da3883577bf063142877f002` | `d6fa0ed0142b89fab78c3fe283bbbbb8db86868fc313a926829abba7be41a187` |
| backend-server.log | `97f4aa340e98aa8599461c07b90778add78c2f80fd705afa1dc62a865d140561` | `fc45466c184c1503702f39a7b99b17661c0bc2fa9c39467c14e92348d11b4507` |

Wrapper terminal SHA `800cfa45dfb19bcfb2becbf4e33427481834b1cf32a2bd20b7a4b412132dfc45`. Consumed screen/CSS hashes match the sealed UI review; consumed backend binding SHA `07cf2c70355847b76affbe72564b80841bad9009af671056e6b38c2d098295b4`. Git/branch/deployment state is not attested by these source maps.

## Isolation and cleanup qualifications

The wrapper statically holds the shared `.run.lock` via non-truncating `r+`/flock through both phases. Each phase used a different owned synthetic SQLite DB/cache/export/temp directory, no source `.env`, no reused server, real demo lifespan/worker and `SEARCH_PROVIDER=none`, `DECISION_PROVIDER=none`, payments disabled/fake and email console. Auth is genuinely enabled only in its phase. Its sign-in interlock passed.

Actual recorded command runs under `sandbox-exec` with network denied except owned loopback5229/8139 and local Unix IPC. These receipts establish that configuration and completed synthetic local run, not an instrumented count of every denied outbound attempt; do not copy backend-full's guard-attempt claims into this receipt. Providers/closed experiments/live quality were not exercised.

Both before/after listener logs are empty; `ports_clear_after=true`. Cleanup receipts target exactly their recorded owned child groups: Demo47068/47051, Auth47344/47330. API logs contain shutdown-request and application-shutdown-complete messages. Child process receipts lack final exit/cleanup fields, so independently proving termination of every individual worker PID is outside this saved evidence. No foreign process cleanup or claim that the retained synthetic data directories were deleted is made.

## Preserved failure history and remaining claims

- `20261011T130607Z-demo`: actual79 PASS,2 FAIL,9 SKIP,0 ERROR; first preparation scenario failed in both projects due same-value selection leaving loading state. Auth was not started.
- `20261011T131348Z-demo`: actual85 PASS,1 ERROR,4 SKIP,0 FAIL; mobile normal Start Reading click timed out with interception/expanded viewport; Auth was not started. Both phases retained source-unchanged/ports-clear receipts. They remain failure evidence, not retroactively PASS.
- These final receipts close those concrete native paths after source-bound repairs. They do not establish concurrent HTTP insertion-race recovery, a new account/profile deletion HTTP E2E, foreign-account isolation, paid-term/exhaustion behavior or public response absence of answer keys. Those contracts require their separately scoped backend/unit evidence.
- The first native evidence assertion proves Writing text is retained; it does not itself assert absence of a wrongly assigned Reading shortcut. Source-family/component/legacy-URL binding is covered by its separate reviewed pure/API regressions and full backend receipts, not invented as a browser assertion.
- Mobile scope is the native Pixel7 project plus320/390 default-font measurements, not physical notch/text zoom/<320px/full accessibility acceptance. These are synthetic local engineering results, not production, official scores, calibrated learning outcomes, complete courses, live search quality or a resumed STOP/UNSCORED experiment.

**Verdict:** the actual final native Demo/Auth receipts are internally consistent, bind unchanged/current consumed source and preserve prior assertions. Accept this bounded local native gate with the qualifications above. Full backend/static/frontend receipts and release/deployment approval remain distinct evidence scopes.
