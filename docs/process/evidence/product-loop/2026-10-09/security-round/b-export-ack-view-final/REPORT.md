# Qualified export-view source proposal — not applied

Confirmed defect: current ExportScreen retains the previously opened Stored profile
JSON after deleteEverything returns true. The same mounted component also accepts
late Show/Download answers and retains view/Deleted state across case selection.
Only ExportScreen.tsx changes; ExportScreen.privacy.test.tsx is new. Store, API,
backend/schema, original tests and E2E stay byte-identical. No new research or retry.

A case-owned generation and mounted fence checks data before showing it or creating
a download. Successful acknowledgment retires the generation, clears exported JSON
and confirmation and shows Deleted. Pending, false and rejected callbacks do not
claim success or clear the current record. A changed case drops the prior view,
confirmation and Deleted state. A new unsaved blank intent uses the existing draft
object to distinguish it from the Store-cleared case. No local applicant data or
operator setting is persisted by this component.

The existing boolean Store contract remains the authority. Native Store catches
server errors and returns false, checks owner/op generation and may clear profile
before its Promise resolves. The explicit test clears savedProfile and draft before
resolving true; honest Deleted survives. A later new blank case retires the notice.
A callback returning true after changing to a different saved case is ignored. This
is component-view protection, not a new server session/tenant transaction or rollback.

Finite native result: 37 actual cases = 15 new Export cases + 22 unchanged Journey
cases. ON 37 PASS, no errors/skips; OFF 26 PASS / 11 expected assertion RED. The OFF
JUnit has one extra reported unhandled error from an adversarial rejecting mock
callback: the state assertions pass but the old handler leaks its rejection. This
is not counted as an additional native test or proof that native Store rejects its
own callback Promise (it normally catches and returns false). Eleven red assertions
are overlapping boundaries, not eleven distinct security bugs. Same exact final new
test body runs OFF/ON. Positive no-run Show/Download, false/pending acknowledgment,
normal file name/URL revoke, and original Journey behavior remain intact.

Controls cover: opened JSON then acknowledgment; late Show and Download after ack;
pending/false/rejected deletion; mounted case change; late old-case replies and ack;
A→B→A generation; Store profile→null before ack; new blank intent; unmount before
Download. API export is mocked at its public client method; component/store-hook
imports are normal modules. No source helper or extraction method is substituted.
No server/browser/full proof is inferred.

Typecheck and targeted ESLint pass after a type-only correction to the new URL mock.
All original frontend test files and E2E files are exact in both runtime copies;
primary consumed source pins and provider STOP are unchanged. The socket/DNS/listen/
fetch guard reports zero attempts. Two test runtimes use installed dependency
symlinks and fresh owned source copies only. No SQL, runner, port, CUA, provider,
model, labels/scoring or primary/Git edit was used.

Retained history: first executable-path attempt exit127 before a test process (absent
/opt/homebrew/bin/node); correct existing /Users/wpalish/.local/bin/node used later.
Initial ON37 PASS and OFF assertion reds retained; initial typecheck TS2417 came
from an overly broad new-test URL static mock type, corrected without source or
assertion changes. It is a test/static typing defect, not an app behavior red.
Current proposal remains external. Parent needs independent peer and fresh native
integration/full/UI against applied exact bytes; the prior full13 is earlier-source
evidence, not verification of this patch. Existing full/browser residuals remain
separately qualified. Downloaded files/caches/earlier recipient copies cannot be
recalled by clearing this mounted view.

The Store exportShortlist / api.downloadExport shortlist path is unchanged. These
controls prove only the screen-owned direct profile Show/Download route; pending
shortlist downloads and previously completed files are outside this patch.
