# V13 terminal allocation and guard diagnostic — final

Read-only, outside the primary comparison. The adjacent JSON binds **21 approved
originals** and checks their bytes before and after this audit. Earlier diagnostic
files remain unchanged; this final note adds the four subsequently supplied GH
records. No source/model/provider/GH/network call or original-file edit occurred.

## Recorded initiating cause

Aalto original run **37363415021**, expert job **111943047441**, has the exact
frozen source SHA `e327498d605d3dbe14da177a8a535c664818ce9b`. Its failure annotation
(`/tmp/unimatch-expert500-v13-aalto-check-annotations-original.json`, item0) says:

> The job was not acquired by Runner of type hosted even after multiple attempts

The job records `runner_id=0`, empty `runner_name`, and `steps=[]`. This establishes
a hosted-runner allocation failure with no recorded worker steps. The populated
job `started_at` is not active execution evidence. Workflow creation19:26:37 to
job termination19:41:41 spans904s; job metadata spans902s. Neither is902/904s of
Fetcher/model work. The three Ubuntu migration notices are separate notices.
No billing/quota/account cause is established.

The **workflow/run** ended `failure`; its **job/check** ended `cancelled`. These
are distinct original fields. Parent884–908 checks the workflow/run conclusion
plus its own cancellation flag. Aalto recorded `cancel_attempted=false`, so the
job-level `cancelled` value does not satisfy its case-local exception.

## Immutable deadline and subsequent cascade

Aalto's single guard19:26:25.548661→19:41:25.548661UTC is exactly900s. Timeout
trigger19:41:25.553591 starts the same-run audit19:41:25.554024. The job terminates
15.451339s after that deadline. At19:41:44.883867 the original transport receipt
records unavailable controlled artifact/counters, `source_transport_audit_incomplete`,
`stop_scope=batch`, and19330ms audit. Artifact download failure is reached before
the code's later unexpected-conclusion classification (parent871–880).

The root durable marker binds Aalto's exact receipt. Its `recorded_at` copies the
initiating trigger; it is not the later STOP-publication timestamp. Parent511–573
writes the receipt and origin marker before exposing STOP. No independent
STOP-set timestamp was saved.

Delft/Groningen also reached their own unchanged900s guards. Shared STOP ends the
normal45s delivery grace; their original runs37364223304/37363581991 are cancelled
inside the existing60s audit-only window, then have missing artifacts. Receipts
at19:41:59.448950/19:41:59.749494 remain batch/incomplete. This audit path only
identifies/views/cancels/downloads the original run; it never renews the guard or
dispatches another action (parent647–672/847–908).

## Recorded timing (milliseconds)

| Case | Model process | Controller transport | Verified source prefix | Final wall |
| --- | ---: | ---: | ---: | ---: |
| Aalto | 8561 | 909465 | 0* | 919340 |
| Delft | 32538 | 900012 | 3626 | 933916 |
| Groningen | 52585 | 879166 | 1112 | 934438 |

Verified source time is nested inside transport, not added to it. *Aalto0 denotes
no returned controlled source ledger; every last dispatch has unknown counters.
These records cannot supply fabricated zero tails. Postguard wall is recorded
audit/closure, not further source/model allowance.

Delft second run37363536608 did recover ordinary controlled success before its
guard: transport363146ms versus source delta894ms, leaving362252ms outside that
controlled action (queue/setup/poll/download). Its later third run was unfinished.
GH creation/step timestamps can identify scheduling/setup when steps exist;
queued snapshots alone lack collection-as-of dates. Parent meters separately
record model, transport and controlled source time; `start_ms` resumes only the
previous controlled source ledger (parent1644–1751).

## Final state and limits

All three results are incomplete with `source_counters_complete=false`; aggregate
STOP leaves seven unstarted. Exit0/`completed=3` counts finished worker futures,
not submitted research. No provider/model STOP is recorded in the inspected
headers, and unknown raw tails prevent broader assertions. The allocation metadata
explains the upstream failure but does not replace raw/counter proof or make the
trial eligible. V13 remains **CLOSED_UNSCORED**; no report, seal, labels, score,
retry or runner/provider/account workaround was performed or proposed.
