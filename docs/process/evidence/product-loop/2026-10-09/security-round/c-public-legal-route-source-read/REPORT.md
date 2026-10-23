# Public legal route: bounded source review

**SOURCE_BACKED_ROUTING_GOOD — exact scope3; runtime NOT RUN.** Read-only inspection covers only `frontend/src/main.tsx`, `frontend/src/AuthGate.tsx` and `frontend/src/App.tsx`. No source/Git edits, native tests, CUA, server, DB or account actions occurred.

`main.tsx:23–33` renders `AuthGate` above `StoreProvider`, whose child is `App`. `AuthGate.tsx:84–90` returns the public `LegalScreen` directly for `#/legal`, before the pending-status branch and before returning authenticated children. React child elements passed into AuthGate do not mount the StoreProvider when that branch is returned. Thus signed-out/pending public legal does not mount the private StoreProvider/App path and cannot trigger that path's hydration on this route. The inspected `App.tsx:101–105` uses the private store, but is bypassed here; its `legal: null` gate and LegalScreen mapping are not the public placement mechanism.

AuthGate still runs its `api.authStatus()` effect (`42–71`) and handles owner transitions; this report does not assert zero public network requests. No `api.cases()` call or `window.location.reload()` loop exists in the public-legal branch of these inspected files. Source ordering closes the specific private-provider placement risk; it is not observed runtime proof of absence of all 401s, races or failures. LegalScreen internals and backend/client implementation were not expanded into this three-file check.

Exact bytes, lines and pre/post equality are recorded in source-pins.json and excerpts.txt. The existing native full failure remains a separate failed result; this route review does not repair or waive it. Browser captures remain 0/7 NOT RUN, and no runtime GO was received.
