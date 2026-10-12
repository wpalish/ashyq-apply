# G2 recovery — native2 Demo qualification

Status: **QUALIFIED_SAVED_NATIVE2_DEMO_ONLY**. Auth is **NOT_QUALIFIED_BY_THIS_REVIEW**. This is an independent read-only inspection of an already completed local run, not a new execution or deployment.

Reviewed at 2026-10-12 05:12 UTC by `/root/open_search_solutions`. No application/source/Git/HANDOFF/helper edits, imports, test or application execution, provider calls, auth-data reads, or stopped-pilot work. Only text/hash/archive/image inspection and new external qualification artifacts were performed. The original HTML was not executed.

## 1. Exact run and binding

Run: [20261012T045340Z-demo](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/evidence/e2e/20261012T045340Z-demo/run.json).

| Evidence | Observed value |
|---|---|
| Native suite | Demo, desktop-chromium + mobile |
| JUnit | 106 cases, 0 failures, 0 errors, 1 skip = **105 passed** |
| Embedded HTML report | 106 total, 105 expected, 0 unexpected, 0 flaky, 1 skipped, `ok=true`, errors empty |
| Recorded process outcome | exit 0 |
| Saved source maps | 429 before and 429 after; exact equality |
| Source binding | Every one of the 429 saved pins occurs in binding10's 772 pins with the same SHA; zero missing or mismatching paths |
| Source-bound run HEAD | `5f4f9b442ae96e0ba9a3d6330240975e561025c8` in SOURCE_COPY.persistence10.json |
| Environment | Native local synthetic SQLite Demo, AUTH_ENABLED=false, SEARCH_PROVIDER=none, DECISION_PROVIDER=none; loopback API/front end |
| Fault | One UI delivery abort **after** forwarding the original PUT to the real local API and observing its real successful ACK; no fabricated response or receipt |

The single skip is the existing desktop case `community.spec.ts:81`, “every community screen is reachable on a phone”, with annotation “the wrapped navigation only applies below 900px”. Its mobile counterpart passes. There are no G2-recovery skips. The 24 preparation cases pass across the two projects.

The saved harness copies match all four hashes in `harness-before.json`: loopback guard, native recovery helper, predecessor native helper, runtime child. No `harness-after.json` is present, so this report does not invent an after-manifest. Saved source maps and the separately pinned root terminal verification support the completed-run boundary.

## 2. Actual forwarded ACKs, recovered from saved bytes

The Playwright report stores its ZIP in the `playwrightReportBase64` template. Offline extraction retained the original HTML and ZIP hashes and read member `47ff6f7eed4fa2ee7144.json`; the two `application/json` attachment bodies were written byte-for-byte as decoded text to this separate external directory. They are **actual saved bodies**, not a reconstruction from source or descriptive run metadata.

| Project | Saved result | Actual status | Original UUID = ACK UUID | Revision |
|---|---|---|---|---|
| desktop-chromium | passed, retry 0, errors empty | 200 | `938be128-26e9-4930-a57f-20ee230798cc` | expected 1 → accepted 2 |
| mobile | passed, retry 0, errors empty | 200 | `9832a266-0e47-4c5d-afe9-12155e404495` | expected 1 → accepted 2 |

[Desktop actual ACK](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g2-recovery-qualification/native2-demo-artifact-read/forwarded-native-ack.desktop.json), [mobile actual ACK](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/proposals/g2-recovery-qualification/native2-demo-artifact-read/forwarded-native-ack.mobile.json).

For both saved attachment bodies, independent JSON inspection confirms:

- URL profile identity matches the receipt profile; original command UUID matches receipt UUID.
- `applicant_input` is structurally equal, including the ordered selected programme IDs.
- `legacy_anchor`, preview fingerprint, and source fingerprint match the original command.
- Accepted planning day is 2026-10-12, with one shared weekly budget of 250 minutes; each capacity row stays at or below 250.
- The exact owned review reference is retained: `ielts-reading-1`, `starter-2026-10-11-v1`, with its own attempt UUID.
- Receipt allocation digest equals the saved allocation's digest.
- The receipt explicitly preserves `readiness=not_assessed` and `programme_applicability=unknown`. It provides no official readiness or admission proof.

Hashes:

| Saved/extracted artifact | SHA-256 |
|---|---|
| Original HTML report | `e2141aaa16bbbbb29e0e2b92bce49dcd1fb3e239c1771aea882ed3a1ce887b31` |
| Extracted original embedded ZIP | `23806e3e752ad58583d1895ac601e5cdd2691a88e3bf6ffe6c09edf981cabd2b` |
| Exact desktop attachment body | `e602c34b0850691a26189b998547828f05bbb494d2aad262aea284e3c39b37b7` |
| Exact mobile attachment body | `75a3616b1f39dc893bf84a3451bf720901e2e756f5ee8dde62ea703b20416acd` |

## 3. Navigation, same-tab reload, and ledger controls

The actual pinned [native test](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/source/frontend/e2e/preparation.spec.ts:679), together with the two saved passed results, establishes this finite sequence:

1. Start from saved revision 1; explicitly preview 250 minutes.
2. Forward one real PUT, attach the observed status/body, then abort its UI delivery; show the uncertain-outcome message.
3. Change the separate browser draft to 260; preserve the exact original pending command and dirty state under the synthetic owner/case journal.
4. Dismiss the navigation guard and remain on preparation with draft 260.
5. Accept the guard, navigate Home, and reload **in the same tab** while the private shared-route component is absent. The original pending command remains.
6. Return to shared route; native current revision 2 reconciles the original command, clears pending, and retains dirty draft 260.
7. Assert exactly one post-preview UI PUT and zero automatic preview POSTs.
8. Read native current receipt, historical revision 2, and case export: current/history match the observed ACK exactly, with precisely the earlier history plus the new receipt. Legacy schedules, attempts, and profile academics remain equal to baseline.

This is not a claim of cross-tab atomic browser-storage CAS or of all recovery races. It verifies the controlled same-tab Demo lost-ACK flow.

Both saved screenshots were visually inspected: [desktop](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/evidence/e2e/20261012T045340Z-demo/docs/screenshots/g2-recovery-lost-ack.png), [mobile](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/evidence/e2e/20261012T045340Z-demo/docs/screenshots/mobile/g2-recovery-lost-ack.png). They show Accepted revision 2/current saved route revision 2, saved weekly budget 250, a separate browser draft, and explicit needs-review/unknown applicability copy. Screenshots supplement the assertions; they do not replace the actual ACK or native ledger controls.

## 4. Narrow carry to the Auth-selector repair

No Demo rerun is claimed. Independent metadata comparison of binding10 and [binding11](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/SOURCE_COPY.persistence11.json) finds:

- Both have exactly 772 members; no paths added or removed.
- Exactly one changed member: `frontend/e2e/auth-journey.spec.ts`.
- Old SHA `f3d9be295640cc157ebdd591d7cb5f4a817cf82ab415bca8af6ac336f4ce62c4`.
- New SHA `4ed22753500706698f965d36b64f8c0ebdf80f224a8b5f719ac8c167c320234b`.
- The native Demo [config line 11](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/g2-execution/source/frontend/playwright.config.ts:11) explicitly excludes this file.
- The original 429-member run map therefore differs from binding11 only at this excluded Auth file; the other 428 match. All 771 other full-binding members also match.
- Focused hashes of current root and lab for preparation.spec.ts, SharedRoutePanel.tsx, sharedRouteRecovery.ts, the Demo config, and the new Auth file agree.

This permits carrying the **saved Demo outcome** to binding11 (`c1ef1aa82085ef22ff62cb2a4ace9e23d8b7fdda`) within that exact one-file excluded delta. The [root carry verification](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/G2_RECOVERY_STATIC12_DEMO_CARRY_VERIFICATION.json) separately records current binding equality, static12 terminal results, and the same exclusion. This audit does not independently qualify the static/full backend runs or the fresh Auth run.

Current relevant byte pins:

| File | SHA-256 |
|---|---|
| preparation.spec.ts | `a4bd15cfc036c5621b1a9d1d5735c088d233cbf336e5e3867e160f5ca3335319` |
| SharedRoutePanel.tsx | `9568c85899a8f7915a965f9a0de9c0ec8a9a5a54086be3fb6c98c8addefb62d7` |
| sharedRouteRecovery.ts | `e5c1affec9bd8fba64238865d09aec8b8f36afb4bd8b059267a385f9e3280561` |
| Native Demo config | `f37cc93a48b1f6bc07bfa85ba0c4dbdab0b0d598187118f619d41d712460662e` |

## 5. Cleanup and unqualified boundaries

The pinned [root terminal verification](/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/product-platform/2026-10-12/G2_NATIVE2_TERMINAL_VERIFICATION.json), at 05:03:35 UTC, records Demo runner/process groups absent, ports clear, and owned synthetic DB/cache/export/tmp paths removed. This replaces the earlier “root cleanup pending” state **for native2**. This agent read that terminal receipt; it did not probe processes or delete anything.

Auth native2 is unqualified: the root terminal receipt records 3 passed, one old practice selector timeout, and 8 not run. The new Auth controls were not reached. Root is running a separately corrected Auth attempt; this report does not read or qualify its mutable output.

No actionable blocker was found for this bounded saved Demo qualification or its explicit carry. This report provides **no** live search recall, provider access, production readiness, whole-product completion, deployment, official test-score, university eligibility, or UniLight superiority claim. G3 remains SOURCE_CLOSED until root's separate release/baton/write-ahead.

## 6. Sealed evidence references

| Input | SHA-256 |
|---|---|
| Demo run.json | `8cb52534b5db8c5ddd5c044856825b697582780445c8983f6a7241e731f48850` |
| Demo JUnit | `9b6563a910cd6bde081ad836d37c19e2faa4019c7733f8668ea4e9a2bf712407` |
| Demo test.log | `658975d1dca96189c8c0d4abb0a46a5eb4d69870fdb8584e4d01e7ead487b448` |
| Demo source-before and source-after (each) | `fef64d55bf41f7b5221e65d03a5109fb3de48e12e642f8842441cb15d2ecb0f5` |
| Demo generated config | `f56e655cea8d55597d60b7f6548f41bedc750c7a21c48f218ed1151334df86c5` |
| binding10 | `4a1ff273413b38568e90cd5ade936af50f5498cc33ec43c7a9bfa1eb38320353` |
| binding11 | `7d36c635c8062baafc66dfd3f00ee3e3812a29f230083f030ff052463edc4bba` |
| Root native2 terminal verification | `7d24879211e051e03b1377612af6b37a54ef93b0d5da3d5066b18405f59b3b43` |
| Root static12/Demo carry verification | `887a6d3bf59e7a5f5e7840da21baf0f09832440b7112699557cde3364d1b689e` |

The companion receipt pins this report and extracted artifacts. All original evidence and source bytes were left unchanged.

