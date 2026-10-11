# Stage 1 native calendar terminal qualification

**2026-10-12 · Local terminal evidence only.** This is a read-only review of saved Demo and Auth receipts. It does not establish deployment, live provider quality, production readiness or G1 implementation. No tests, app runtime, traces, databases, account state or provider calls were opened by this reviewer.

## Saved terminal results

| Suite | Receipt | JUnit and terminal | Source / cleanup |
| --- | --- | --- | --- |
| Native Demo | `execution/evidence/e2e/20261011T223151Z-demo/run.json` | 100 tests: **99 passed, one retained old skip**, zero failures/errors; exit 0. New dated opt-in lesson/save/review test passed on desktop and mobile. Existing 409 conflict, console-error and 320-pixel mobile navigation tests also passed. | 412 source paths; before/after map delta zero; three harness pins match current helper bytes; `ports_clear_after=true`, empty `ports-after.log`. |
| Native Auth | `execution/evidence/e2e/20261011T223732Z-auth/run.json` | **9 passed**, zero failed/skipped/errors; exit 0. The prior eight test names remain the exact leading eight JUnit entries; new opt-in/own receipt/clean second-browser test passed. | 412 source paths; before/after map delta zero; three harness pins match current helper bytes; `ports_clear_after=true`, empty `ports-after.log`. |

Both receipts state `mock_routes_or_apis=false`, `providers=none`, and use the saved loopback-only runner. Their generated Vite configs preserve native server options and allow only the execution frontend and the resolved Inter/JetBrains Mono package directories for the font seam. Both `frontend-server.log` files have no `403` or `outside of Vite serving allow list` line. All 420 pinned Inter files and 326 pinned JetBrains Mono files still match `execution/native-font-binding-repair.json`; no dependency bytes changed.

The failed first Auth terminal (`20261011T223420Z-auth`) remains a separate 8-pass/1-error receipt. Its test source SHA-256 was `f0c43881686a065c3b04e7ce8d4d45d31e155213ef01566f8d32ee689b1be90d`. The final Auth source SHA-256 is `2d251b0cd2fe8cc1738aa00aa50a295bf4c9d5a29ca5f369be4fb13b1e1800eb`, identical in execution source and root work copy. In-memory reversal of exactly `firstTick.check()` → `.click()` plus the post-ACK `toBeChecked()` line recreates the failed file's full SHA. The real PUT listener, successful-response assertion, subsequent server GET and completed-task assertion remain. This is a test interaction fix for the server-controlled checkbox, not a production guard or mock change.

## Binding to the current checkout

The successful Demo source map pins `frontend/e2e/preparation.spec.ts` at `4333ea72af5a366262a72f7e2eb3ab8eab4b7dfb39839303a12555d29d1e8f2c`, matching the reviewed test-setup repair. The successful Auth map pins that same Demo spec hash and the final Auth spec hash above. Root's saved `execution/FINAL_CARRY_QUALIFICATION.json` records current HEAD `6a66da456f14d964ec16091f321fb7f23a74077f`, zero differences across its 609-path backend source map, and exactly one Demo-map delta: `frontend/e2e/auth-journey.spec.ts`. Native Demo's config ignores `**/auth-journey.spec.ts`, so that later Auth-only test edit is outside Demo's consumed test set; the receipt qualifies carrying Demo at this HEAD. This is a source-binding qualification, not a rerun of Demo after the Auth edit.

The successful Auth run saved four distinct second-session viewport PNGs, all nonempty: 320 (53,877 bytes; SHA-256 `6f0054ce60e5d4f4f26bd2a15b1fa2641e224df8db0e93686a60c1203189d0da`), 768 (76,248; `c26ac0c322f37073ab5486cfdf104550f7c0aa727c201899d7f49460cd75f25b`), 1024 (94,252; `df213d718c63bbc0f900cece9142f4b2ef7dd132a3ad8da68c412ff5879f98d2`) and 1440 (97,575; `035f322ce67137c8482b12332c28034ed0737167b537ffd0fa29c7d551552716`). The test's viewport overflow assertions passed. Visual readability of those four images is a separate root review; file existence and test status alone do not prove it.

The Demo and Auth outcomes apply to this frozen local source and these saved synthetic, loopback-only runs. The earlier red terminals are retained as historical failures; neither was relabelled as a pass.
