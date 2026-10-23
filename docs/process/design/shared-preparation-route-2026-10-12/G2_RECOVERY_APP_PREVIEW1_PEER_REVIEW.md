# G2 recovery application preview1 peer review

2026-10-12 · **READ ONLY / SEALED REVIEW SNAPSHOT / NOT APPLIED / NOT RUN**

Reviewed immutable `proposals/g2-recovery-app-preview1/SEAL.json` SHA-256 `7b5e081b4c74e0d18c096a8f4acc096c91541cc22faffcc9feddb0a610f3b6aa`, its seven full application postimages/diffs, sealed final recovery design and native preimages. All six existing preimage hashes in the snapshot matched the frozen checkout at review time. The new helper had no source preimage. No application import, tests, browser, Git, runtime or source edit was made.

## Findings for the final 15-path packet

**F1 — an ACK can falsely clear unsaved form risk.** `SharedRoutePanel.tsx` records `submitted_generation = generation.current` before PUT; `acknowledgeSharedRouteRecovery` clears `dirty` whenever that generation has not changed. But `manual_id` and unfinished `manual_review` are journaled inputs that never enter `SharedRouteWriteV1.applicant_input` until explicitly added. Disabled exam fields can likewise be omitted by `buildInput`. Example: type a manual ID, already have two other selected IDs, preview/save the route, receive ACK without further edits. The manual ID remains visible/browser-only while `dirty=false` and App removes the leave warning. Compare the accepted input projection with retained form fields, or otherwise keep the unsent fields dirty; test manual ID/review and disabled exam inputs before ACK, then voluntary navigation and logout. This is a source proposal defect, not a server write defect.

**F2 — a real accepted receipt is hidden by browser cleanup failure.** `acknowledge` validates the server receipt but, when compare-clear of session journal fails, leaves pending as `uncertain` and never calls `setAck(receipt)`. The direct PUT handler then calls `readCurrent`; if that GET also fails, the UI offers no accepted revision even though an exact server ACK was observed. Keep accepted server receipt/read status separate from local journal-retirement status: display the exact accepted revision with a cleanup warning, retain the original journal for safe reconciliation, and avoid a false claim that server outcome is unknown. Cover failed session cleanup after real PUT200 and failed subsequent GET.

## Positive checks and remaining gates

The helper uses an owner+case session key under existing logout cleanup prefix; validates a bounded, whitelisted original body; writes before new PUT; does not auto PUT/preview on reload; allows only one exact target history GET when a later current head exists; and compares current raw journal before retirement. `App.tsx` places the hash leave decision before screen mutation, retains per-registration tokens, and leaves auth-owner unmount in AuthGate. Authenticated Legal routes through App while public Legal remains available before authentication. Successful case-delete ACK targets the captured case journal. These are static source observations, not test PASS.

The final packet must preserve the root 15-path allowlist and address F1/F2 without weakening existing response identity/CAS checks, old test assertions or native network guards. The earlier full backend receipt only carries for byte-identical consumed files; this new frontend behavior needs its own static and native gates.
