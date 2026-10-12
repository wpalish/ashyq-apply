# G2 recovery final15 — independent strict source review

Status: **READ_ONLY_SOURCE_REVIEW_COMPLETED_NO_BLOCKER**. Application edits, imports, tests and runtime: **NOT_PERFORMED_BY_THIS_REVIEWER**. This is source review, not a collected test result or product/deployment acceptance.

Reviewed immutable packet: `proposals/g2-recovery-source/SEAL.json` SHA-256 `9c7c46be8d2fed537943f6167c84a3b7e65f3e43e9d93074bee85ba9226260f2`; packet sealed at `2026-10-12T04:18:59.918602+00:00`. Final packet rehash at 2026-10-12 04:30–04:31 UTC: all **46** sealed members and seal match.

## Disposition

No additional actionable blocker was found in the reviewed final15 strict parser, owner/profile fences, original-command recovery, F1–F3 correction paths or their proposed focused/native controls. Root may consider application under its existing write authority; native execution remains the root's separate gate.

## Contract closure

| Boundary | Source-bound observation |
| --- | --- |
| Strict journal parser | Helper lines 35–163 reject extra keys, foreign owner/profile, malformed dates, non-finite or out-of-bound numeric fields, duplicate targets/reviews, invalid current request shape and oversized raw text. Partial personal drafts remain representable separately from a complete PUT command. |
| Ownership and exact journal comparison | Helper lines 166–215 bind the current native owner and profile before read/write/reset; mutations require the expected raw string plus draft UUID and journal revision, then bounded revision increment and readback equality. This browser storage read/write sequence is **not an atomic cross-context CAS**. No such guarantee is credited. |
| Original command and dispatch | Panel lines 430–485 retain the original UUID/body; sending is journaled before PUT. A failed first journal write stays not-sent; an already-dispatched uncertain command remains dispatched. Restore does not automatically POST/PUT. |
| F1 — omitted meaningful fields | Helper lines 218–232 and Panel lines 298–315 keep a draft dirty after ACK when a manual review field, meaningful disabled-exam field or newer generation was omitted from the submitted command. Untouched disabled defaults do not falsely mark the draft dirty. |
| F2 — known ACK versus cleanup failure | Panel lines 298–315 record the matching server ACK before retirement. If retirement fails, the accepted ACK remains visible; the known-cleanup notice replaces the uncertain-write label, and the original accepted UUID retry control is hidden (lines 503, 627–629). A later GET failure does not erase the observed ACK. |
| F3 — renewed entitlement and explicit new intent | A confirmed 402 preserves the original command. Only an allowed fresh preview plus an explicit action can clear its pending state using the exact journal comparison (Panel lines 630–637); draft/manual fields remain. A new UUID is allocated only by the next explicit Save. Failed persistence does not dispatch or replace the stored original body. |
| Response/epoch fences | Current read, one expected revision history reconciliation, matching ACK, mount/unmount and request-intent guards remain owner/profile bound. A mismatched UUID/body/revision does not retire another intent; a newer current head is retained. |

## Meaningful proposed controls

The following are **test source reviewed, NOT_RUN**, not PASS claims:

- Helper cases cover own/demo/unbound and changed owner, foreign/malformed/oversized closed schema, exact original bodies, storage/readback failure, revision overflow, same UUID/raw comparison, case separation and F1 positive/negative dirty controls.
- Panel tests at lines 435–451 exercise a matching ACK followed by cleanup storage failure and GET 503: ACK remains visible, no accepted-command retry, one PUT, original durable journal retained.
- Panel tests at lines 465–481 exercise meaningful manual and disabled fields entered before submission; the ACK cannot falsely make that draft clean.
- Panel tests at lines 497–529 exercise confirmed 402, forbidden versus renewed access, form changes, preserved original command until fresh preview and explicit new intent, then a distinct UUID on the next Save.
- The additive native Demo control forwards a **real** loopback PUT via `route.fetch`, checks the successful receipt and attaches its bytes, then aborts delivery (preparation spec lines 710–717). The later new-draft/reload/current/history/export checks assert that reconciliation does not perform another write.
- The additive native auth control uses separate actual browser contexts, protected navigation, accepted logout acknowledgement and local journal cleanup; it proposes no synthetic server receipts or new provider calls.

## Preservation and pins

At the earlier pre-application read, all **13** existing target preimages matched the sealed preimages and both new helper/test paths were absent. This observation is retained as the initial read evidence; root may have applied after the no-blocker message, so it is not a claim about the checkout at report publication.

Independently compared whole declaration bodies: `matchesSharedPreview`, `matchesSharedReceipt`, `matchesSharedView` and `buildInput` are exactly unchanged. Both old native test source files are exact prefixes of their sealed postimages. The comparison used text equality; recorded character counts are not byte counts.

| Reviewed postimage | SHA-256 |
| --- | --- |
| `frontend/src/lib/sharedRouteRecovery.ts` | `e5c1affec9bd8fba64238865d09aec8b8f36afb4bd8b059267a385f9e3280561` |
| `frontend/src/lib/sharedRouteRecovery.test.ts` | `2004abe004ef130e80060ff0b5aed4f235826d0efb430f0a4ee89be3eaacfc9a` |
| `frontend/src/screens/SharedRoutePanel.tsx` | `9568c85899a8f7915a965f9a0de9c0ec8a9a5a54086be3fb6c98c8addefb62d7` |
| `frontend/src/screens/SharedRoutePanel.test.tsx` | `ceda3045b9c1df8ee3d88833a19e5d6813c12a1e79cc106020d6069ec556ac24` |
| `frontend/e2e/preparation.spec.ts` | `ba9e527016103492f291d7a450a9b071ce2c8487765c188eedf0b4ba0c104469` |
| `frontend/e2e/auth-journey.spec.ts` | `f3d9be295640cc157ebdd591d7cb5f4a817cf82ab415bca8af6ac336f4ce62c4` |

Native backend schema used for the request compatibility read: `backend/app/schemas/shared_route.py` SHA-256 `50c2dca8ad250f3d12fc9645a6307ac4dd05bf05a61c79c17bbf925b4c8042e2`. No backend source, entitlement, quota, official scoring, corpus or stopped workflow was changed or executed. Sibling App/auth boundaries have separate root/peer review; sealed-member hash verification does not substitute for reviewing or running every sibling path.

## Remaining gate

Run the separately authorized root static/focused/native gates against applied final bytes. This report does not establish browser/ZoneInfo timezone parity, cross-tab atomicity, server availability, live search quality, official admissibility or deployment readiness.

