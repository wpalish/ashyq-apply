# Frontend privacy proposal — independent peer

Verdict: REJECT_UNTIL_REPAIR, bound to B READY6063029c and all12 exact proposed source/test pins.

All110 selected originals/hashes/bytes verified; native primary base and STOP65b5 unchanged. Own normal-import frontend copy ran B62 controls plus one independent control: **62 PASS /1 FAIL**. No fixture/setup error. Socket/DNS/HTTP/listen guard process receipts all0 attempts. No backend/SQL/browser/full/provider/model/production execution.

Confirmed blocker: `frontend/src/AuthGate.tsx:29–32,114–123,145–152` binds an asynchronous post-login/reset status without checking the owner marker/generation after that wait. The initial effect has this check, but the submit path bypasses it. Actual AuthGate and actual API request/authTransition executed with synthetic `fetch` Responses, not substituted search/API methods. Sequence: signed-out status → successful A login → delay A status → newer B owner acknowledged via native storage event + status → resolve older A status. Result: owner becomes A and B's newly scoped draft is deleted. JUnit preserves the exact expected B state and received `{owner:A,draft:null}`. Calls are precisely status/login/status/status; no university/profile calls.

Preconditions: overlapping post-auth refresh and another tab's client-auth transition on the same origin. Confirmed local private-data loss and stale binding; server-side tenant write was not executed. This does not assert atomic cookie fencing or production exploitation. Root must not apply606 before a bounded marker/generation check covers post-auth refresh, preserving existing success tests and stale-status controls.

Other reviewed bounds: authenticated user+org scoped pointers/marks, failure acknowledgments, captured Store save/start owner fencing and success-only deletion are narrow and useful. Current-result marks only; historical nonreturned IDs/account/billing/audit/backups are not erased. Already-dispatched cookie races remain a truthful limitation. Root owns final native/full/browser checks.
