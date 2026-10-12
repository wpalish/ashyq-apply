# G2 recovery: final saved local qualification

**2026-10-12 · SAVED EVIDENCE ONLY · LOCAL IMPLEMENTATION QUALIFIED**

This review read completed local evidence and current file bytes only. I did not launch app imports, tests, browsers, helpers, Git, providers or network requests. It qualifies the bounded G2 browser recovery increment in the current local source; it is not deployment, live source research, pedagogy/content approval, or whole-product acceptance.

## Terminal results and preservation

| Gate | Saved terminal result | Independent comparison |
| --- | --- | --- |
| Static13 | Ruff check/format, mypy, frontend typecheck/lint/unit/build all exit 0. Frontend JUnit **596 passed, 0 failures/errors/skips**. | Parsed `static-persistence7` and `static-persistence13` JUnits by class/name: **all 546 old IDs retained**, exactly 50 added, none removed or duplicated. Current `frontend/src/api/client.ts` remains SHA-256 `f667d2f3b89d64ea42392f9e5bba3a30d04a1a76b2203fa2b4a337a7a8cc6789`. |
| Native Demo2 | `20261012T045340Z-demo`: exit 0, **105 passed + 1 historical skip**, 0 failure/error, 106 total. Desktop and mobile G2 save and lost-ACK controls passed. | Parsed JUnit by project/class/name against G1 Demo predecessor: **all 102 old IDs retained**, exactly four G2 IDs added (two scenarios × desktop/mobile). Separate sealed Demo qualification `f5b2da38c8332e0fbe5fbed045bc588487153ac7989773fafd79be4167b977c7` extracted the actual forwarded native HTTP200 ACK/body from the saved report; the two own commands matched their receipts, accepted revision2, one budget250, newer local draft260, no second PUT/preview, and exact current/history/export after reload. |
| Native Auth4 | `20261012T051801Z-auth`: exit 0, **12 passed**, 0 failures/errors/skips. | Parsed JUnit against G1 Auth predecessor: **all 10 old IDs retained**, two added. Old exact practice/second signed-in browser and new G2 clean-browser scenario passed. New recovery scenario's assertions cover denied then accepted authenticated Privacy & terms navigation, retained own draft on return, separate browser with no private draft/journal but exact saved server revision1, dismissed logout with zero logout requests, one acknowledged logout, Welcome back, exact journal removal, and zero route PUT/preview. These are observed test assertions with a terminal PASS, not a separately reconstructed Auth network trace. |

The Demo lost-ACK test's `route.fetch()` forwarded one exact own-case browser PUT to the real local API and attached its actual accepted status/body **before** aborting the browser response. The saved independent Demo review confirms the attachment is not a fabricated mock receipt. The Auth private-draft scenario uses the real local authenticated API and a second clean browser. Existing native configs retain serial workers, zero retries, 120-second test timeout, and their distinct Demo/Auth modes.

## Exact source and carry boundary

I independently verified all **772** paths in `g2-execution/SOURCE_COPY.persistence12.json` against both current root and lab: zero hash mismatches. Auth4's **429** source-before and source-after entries are identical and match the current binding. Demo2's **429** before/after entries are identical; the only later current-binding difference is `frontend/e2e/auth-journey.spec.ts`, which Demo excludes through `frontend/playwright.config.ts` `testIgnore`. Thus Demo2 is carried to the current source only within that explicit executable-suite exclusion; it was not rerun after the Auth-only label correction.

The frozen full backend source-before map contains **624** consumed paths; I compared all 624 against current root and found zero mismatches. Earlier saved SQLite/PostgreSQL full gates each passed 5,417 tests as qualified in `G2_SAVED_LOCAL_QUALIFICATION.md` SHA-256 `7bafa73275f45333f7013471d69710fb88479d2346c5c21df89b1eddabbf837f`. Those backend executions were **not** rerun for the browser recovery edits; their unchanged consumed bytes support a bounded carry, not a fresh backend runtime claim.

Both saved native runs have `source_unchanged=true` and matching source-before/source-after maps. Auth4 root terminal receipt records runner/owned groups absent, ports clear and private runtime cleanup. I independently checked that its synthetic database, WAL, cache, exports, temporary and Vite-cache paths are absent. Saved PNGs exist for Demo desktop/mobile lost-ACK (`1440×5704`, `1082×20480` pixels) and Auth private draft (`1440×3813` pixels). Root is separately reviewing screenshot readability; this saved-only review asserts existence and dimensions, not visual quality.

## Failed attempts and limits

Earlier immutable failed runs remain diagnostic evidence: static8 infrastructure PATH error, static9 test type error, Native1 Demo disclosure selector error, Native2 Auth old global question-fieldset selector error, and Auth3 new test Legal-label timeout. Each received a finite test/harness correction; successful terminal results above come from later fresh runs. No failed result is relabeled PASS or silently substituted.

This qualification establishes local source-bound recovery behavior and preservation of the tested legacy flows. It does not establish cross-tab atomic browser-storage CAS, production deployment, official exam scores, admission eligibility, live provider/search quality, complete curriculum, or G3 implementation.

## Primary saved pins

- `G2_RECOVERY_STATIC13_DEMO_CARRY_VERIFICATION.json` SHA-256 `9592b38e5208c12e841492fbb2dd5f30cbd0a4a84e7a8430bff82ae30fa0141a`; frontend JUnit SHA-256 `a8fc7f3f2b2c911975bbd426fc19f9cb3b2c0f09fa7fca312087b08b0c28e5f4`.
- `G2_NATIVE_AUTH4_TERMINAL_VERIFICATION.json` SHA-256 `140ac54a995dd8087224916a57a95420a86f38938198aaa4d040fb9f4943f55e`; Auth4 JUnit SHA-256 `d0f2090a5fd01659aa516280ac5a4811c1ea6a22e5fac38c348104b1b3e3bbca`.
- `proposals/g2-recovery-qualification/SEALED_DEMO_NATIVE2_QUALIFICATION.json` SHA-256 `f5b2da38c8332e0fbe5fbed045bc588487153ac7989773fafd79be4167b977c7`.
- `g2-execution/SOURCE_COPY.persistence12.json` binds the current 772 root/lab paths. Auth4 raw `run.json`, `test.log`, `junit.xml`, `source-before.json` and `source-after.json` are under `g2-execution/evidence/e2e/20261012T051801Z-auth`; Demo2 equivalents are under `…/20261012T045340Z-demo`.
