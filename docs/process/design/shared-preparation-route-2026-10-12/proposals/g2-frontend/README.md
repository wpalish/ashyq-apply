# G2 frontend proposal — one saved shared preparation route

Status: **EXTERNAL SOURCE PROPOSAL / NOT_APPLIED / NOT_IMPORTED / NOT_RUN**. The six paths under `files/` are proposed full frontend files. They are not in the application checkout. Root is the sole application, Git and runtime writer. Do not interpret this packet or its synthetic test source as a local gate, release, lesson quality result or deployment.

## Contract and placement

The proposal matches `ROOT_G2_PERSISTENCE_INTEGRATION_DECISIONS.md`, accepted `proposals/g2-design/TYPED_CONTRACT_DESIGN_V2.md` and the G2 backend DTO/API proposal (`proposals/g2-persistence`, not applied at the time this packet was prepared). It uses these exact owner-scoped endpoints:

| Method | Path after `/api/profiles/{profile_id}/preparation/shared-route` | Return |
| --- | --- | --- |
| GET | empty suffix | `SharedRouteCurrentOutV1` (`revision=0, view=null` for new cases) |
| POST | `/preview` | unsaved `SharedRoutePreviewOutV1` |
| PUT | empty suffix | immutable `SharedRouteWriteReceiptV1` only |
| GET | `/revisions/{revision}` | `SharedRouteViewV1` with fresh safe current status |

`PreparationScreen` adds a separate **Shared route** view and preserves the existing goals, study plan, practice, progress, exact lesson and own review flows. The shared panel stays mounted but hidden while another preparation view is selected, retaining an uncertain original write within the current case session. Saved G2 makes the old study plan a collapsed read-only historical panel; it cannot present a second active weekly budget. Unknown G2 current state also keeps legacy read-only pending a successful refresh. Existing v1/v2 schedule handlers, self ticks and original content are untouched by this packet.

The applicant explicitly orders 2–20 own approved/maybe result references, selects IELTS Academic and/or Digital SAT in an explicit priority order, enters personal exam dates, buffers, optional personal targets, study days/time zone and **one** weekly budget. Latest loaded results are suggestions only. An exact older saved result ID may be entered; the server validates the entire selection. Own reviews may come from recent history or an explicit older exact UUID/lesson/version reference. Neither option infers an exam association or review minutes. The preview is unsaved; saving sends the server's preview fingerprint and legacy/source anchors plus a new UUID for that user action. A retry sends the **same** body and UUID. A 409 retains the original UUID for exact replay; a different save intent requires a new preview and explicit action. A 503/network or unverified ACK never becomes a saved success in the UI. A fresh current GET reconciles an uncertain write only if its receipt matches that original body/UUID. A validated ACK keeps the shared route active even if the following status refresh fails or returns an older revision.

The frontend checks owner/case epoch through the existing `PreparationCase` key and `isCurrent`, then validates response profile, revision, ordered result echo, exact exam choices and buffer dates, one budget, dates/ref kinds, write UUID/input and receipt digests before rendering. Current/history status shows only safe reason labels. Premium G1 material remains in the separate Goals & evidence view; the shared route never enriches locked saved references with local result names. Exact action IDs, result IDs and attempt UUIDs are available in expandable reference details. Saved slots retain their exact refs and planned minutes; practice submission/ticks do not imply mastery, an official score, exam readiness or admission eligibility.

## Files and frozen source preimages

`files/frontend/src/screens/SharedRoutePanel.tsx` and `.test.tsx` are new. The other four are full copies with additive G2 changes. Source preimages from the app checkout at the G2 write-ahead were:

| Existing path under `frontend/src/` | SHA-256 preimage |
| --- | --- |
| `types.ts` | `1db0143b20def355da62687d290f34628b7a0d4f1beeab8415689caf20f60ca1` |
| `api/client.ts` | `8b27a74a87b1ee46307a6b2c8e24cfb9ddddd96d949377dd20c863c94d5c74e3` |
| `lib/i18n.ts` | `9167029fc364fadec35a3ecfd91c690e59bae24749fe29c1c184c72a471dc6f4` |
| `screens/PreparationScreen.tsx` | `41cb8a346dac441f536b713ad15d90f150f1398695fc3a37f521eda128c03cf6` |

Root should compare these exact preimages immediately before applying any full copy. `SEAL_RECEIPT.json` records the proposed postimages. This packet makes no migration, backend, content, payment, quota, social, research provider or legacy API change.

## Proposed verification after root applies

The new Vitest file is **NOT_RUN**. Its synthetic controls cover ordered programme/exam choice, strict IDs, explicit old own review, A→B→A preview rejection, same-UUID/body retry, 409 without optimistic save, exact receipt reconciliation after 503, mismatched ACK/foreign body, locked/expired history, case replacement, localized labels and absence of legacy calls. Its fixtures are deliberately minimal frontend response shapes; they are not backend allocator or database validity fixtures. Root still needs normal frontend typecheck/lint/test/build and native Demo/Auth runs against the applied backend. Native proof should use real own API and four viewport captures (320/768/1024/1440), reload plus a second clean browser, exact dated lesson and own receipt, read-only history after expiry, and one visible active budget. No such run is claimed here.
