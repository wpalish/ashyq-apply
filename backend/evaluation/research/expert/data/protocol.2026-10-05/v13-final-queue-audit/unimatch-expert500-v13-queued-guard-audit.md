# V13 queue / immutable guard / terminal transport diagnostic

Read-only, outside the primary comparison. Seventeen approved originals are
hashed in the adjacent JSON; no source, model, provider, GH, label or report call
was made. The frozen parent remains SHA256 c62fb07e. The final stage log is
3012bytes/21lines/SHA2567bdb3e32; its earlier17-line2550byte prefix is separately
bound. No original or helper was changed.

## What ended the stage

All three results are **incomplete** with `source_counters_complete=false`;
aggregate `stopped=true` leaves seven remaining case IDs. Parent exit0 and stage
`completed=3` describe process/future completion, not submitted research.

Aalto's original run37363415021 triggered the first durable batch cause:

1. Guard19:26:25.548661→19:41:25.548661UTC: exactly900s. Timeout was recorded at
   19:41:25.553591; audit started19:41:25.554024.
2. The known original run ultimately returned **failure**, no cancellation was
   attempted, and its controlled artifact/counters were unavailable.
3. At19:41:44.883867 the receipt records `source_transport_audit_incomplete`,
   `stop_scope=batch`, `_ArtifactUnavailable`, audit19330ms. The local guard-ended
   branch requires completed/cancelled + own cancellation + no existing STOP;
   Aalto did not satisfy it (parent884–908). The underlying GH job failure reason
   is absent from these headers and is not inferred.
4. The root marker hash binds that exact Aalto receipt. Its `recorded_at`
   19:41:25.553591 is the copied initiating trigger, not proof STOP was published
   at that instant. Receipt/marker publication occurs later in511–573; no exact
   STOP-set timestamp is saved.

Delft/Groningen also hit their own900s deadlines near19:41:25.55. Their original
runs37364223304/37363581991 were then cancelled in the same bounded audit and
reported missing artifacts at19:41:59.448950/19:41:59.749494 (audit33893/34189ms).
The shared Aalto STOP disables the no-STOP case-local exception and the45s
delivery grace; both receipts remain batch/incomplete. No provider/model STOP is
recorded in the inspected headers. Unknown source tails cannot establish what
unreturned tools actually did.

## Where the time went (milliseconds)

| Case | Model process | Controller transport | Other descriptive meter | Confirmed source prefix | Wall elapsed |
| --- | ---: | ---: | ---: | ---: | ---: |
| aalto | 8561 | 909465 | 42 | 0 | 919340 |
| delft | 32538 | 900012 | 145 | 3626 | 933916 |
| groningen | 52585 | 879166 | 1442 | 1112 | 934438 |

Source prefix is **inside** successful transport, not an extra additive duration.
Aalto's0ms means no verified returned source ledger, not zero actual source work.
The last dispatch in every case has unknown counters. Wall exceeds900s solely in
recorded postguard transport audit/closure; this does not renew source/model time.
Wall-minus-meter is1272/1221/1245ms and includes initial setup/gaps plus stage
rounding; it is not an independently measured pure mechanical category.

Delft's queued second action37363536608 recovered ordinary controlled-job success:
receipt19:33:44.824192 has `status=completed`, `conclusion=success`, no audit/guard
expiry/cancel, verified counters(1read/1query/3626ms cumulative). Its transport
was363146ms, while its new controlled query added894ms. Thus362252ms was outside
that controlled action (queue/setup/poll/download etc), not model thinking.
The stage then records checkpoint3 and a new, later third dispatch. That third
dispatch—not the recovered second one—was unfinished at terminal closure.

## Queue evidence and clock semantics

The three queued snapshots map to Aalto first action37363415021 (created19:26:37),
Delft second action37363536608 (19:27:43), and Groningen later action37363581991
(19:28:08). They report `status=queued`, blank conclusion and no executed steps,
but job `startedAt` is already populated2–3s after creation. Treat those dates
as insufficient proof runner execution began; zero-date completedAt is unknown.
Their createdAt==updatedAt and absent snapshot-as-of field prevent an exact pure
queue-duration calculation. Parent controller_transport measures the full wait.

The Warsaw delayed-state file is a **baseline-mode** job: baseline capture step
executed while expert-plan step was skipped. Creation→first Set up job is53s;
that baseline step spans122s. Top-level status is stillin_progress despite the
expert-named job's completed/success fields. Do not use this as an expert action,
current running-job proof or model-time measurement.

Each case starts one immutable guard on expert entry (parent1107–1109), before
setup/model work. Every plan/dispatch reuses it; start_ms is the previous measured
source_ms (1613–1664), never queue/model time. UTC remaining bounds dispatch,
commands and polling(435–498/627–672). At expiry, only the same original run may
be identified/viewed/cancelled/downloaded inside60s; normally45s allows its own
finally/upload before cancellation. Audit cannot dispatch a new source action.
Late authentic artifacts may preserve original counters/accepted prefixes;
missing or invalid proof is not converted to zero or completed research. Closing
notes are secondary to the retained transport failure, not the initiating cause.

## Existing fields that separate the components

- `wall_started_at/wall_deadline_at`, receipt trigger/audit dates and wall_elapsed_ms
  prove the immutable boundary and postguard audit separately.
- Model metadata model_started_at/model_ended_at/elapsed_ms and selector meter
  entries separate model process time (parent1333–1351/1320–1327).
- controlled_source_action.source_elapsed_ms, source_ms and strict summary/raw
  cumulative counts separate actual controlled action time (1736–1751).
- controller_transport elapsed_ms/turn/run_id measures the complete dispatch wait.
  GH createdAt + actual first step timestamps/job steps can separate scheduling
  and setup when present. The original parent run.json polling saves status,
  conclusion, headSha/url, not a detailed queue-event timeline(627–645).
- source_counters_known/complete and artifact hashes distinguish verified prefix
  counters from unknown dispatched tails. Delft/Groningen validated=true refers
  to their retained prefixes; it does not make all dispatches complete.

No retry, allowance, runner/provider/account/IP change or score is proposed.
