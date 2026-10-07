# PR #46 — Original V10 guard failure

## Original state

Source39a14c5/tag expert500-phase1-v10-2026-10-05-39a14c5 and protocol
ba493e4f remain immutable. Trial c6586ba3 was allocated once. All10 algorithm
captures completed and independently passed their60 reads/6 queries/120s
contract. The experts stage started once at09:11:35.496413UTC and has ended.

Five expert results exist; shared STOP is true. UBC,Toronto,HKU,NTU and KAIST
never started. Aalto committed with zero accepted journal facts; Delft and
Groningen kept incomplete accepted prefixes. Vienna and Warsaw were interrupted
while their own900s guards were still valid. Journal facts are not reviewed
reference matches and do not establish a62-fact score.

The original report exited1 in verified_cohort before unsealing:
`All experts must be uniquely finalized before unsealing`.
There is no primary seal, reviewed-label load, numerical score or per-reviewed
fact diagnosis. V10 is CLOSED_UNSCORED; it is not a0/62 result.

## First causal STOP

1. Groningen's immutable deadline was09:26:35.497300UTC. Its original
   controller-28 audit began09:26:35.502686UTC with TimeoutError and
   guard_exhausted=true.
2. The uniquely identified original run37289962161 was externally canceled.
   It ended canceled without a verified source artifact. Unknown source counters
   correctly remained unaudited; they cannot be converted into zero-cost work.
3. After21.914s audit, parent source715 escalated this case expiry to shared
   STOP; caller1413 repeated it. The approximate09:26:57.417UTC STOP time is
   derived from original timings: no first-latch timestamp was persisted.
4. Warsaw controller-01 audit began later at09:26:59.181687UTC and original
   run37290076326 was canceled by the shared stop. Vienna's next dispatch failed
   the live-batch guard at about341s. Five universities never started.
5. Closing validation1655 overwrote the original case error with generic guard
   exhaustion. That later message is not the initial cause.

Delft had previously reached its own closing guard, freeing its slot for Warsaw.
Its last accepted checkpoint at847.426591s processed11 of12 recorded sources;
the12th source artifact arrived at884.800959s. Only3.852954s remained for the next
selector call. Frozen replay already permits processed k/recorded k+1 with
all_recorded_sources_processed=false; only accepted prefix facts are eligible.

All33 completed original transport audits have provider_failures=[] and no
stop_reason. Both canceled tails lack verified artifacts. Model failure is null
in every result and there is no model-batch-stop marker. Saved evidence does
not establish an Exa429, model quota or account failure. The generic parent
provider429 message does not identify the actual cause.

## Original timing meters

| Case | Selector wall seconds | Controller transport seconds | Source ledger seconds |
| --- | ---: | ---: | ---: |
| Groningen |474.275 |435.632 |16.872 |
| Delft |312.600 |580.426 |17.564 |
| Aalto |118.043 |467.396 |66.242 |
| Vienna |99.680 |239.158 |19.268 |
| Warsaw |10.759 |40.067 |0 |

Transport includes source execution; most workflow round trips took40–60s.
Selector wall includes CLI/model processing. Pure thinking is not separately
measured and is not charged to source counters. Original source accounting
does not justify lowering default reasoning effort or extending the900s guard.

## Immutable closure

`backend/evaluation/research/expert/data/runs.2026-10-05/v10-unscored/`
retains995 records/32,642,977 original bytes,65 model receipts and33 completed
source actions, including incomplete dispatch/audit/model tails.

- Manifest:1e7a4e2e648092866ff3857d315778e8f4d7c405338b3235d11e46860e9caa1a.
- Archive:c980d9ec80345b87f5cbbf037c0503416d512728716fddd5d9c8c793ab4e0766,
  5,806,965 bytes.
- Every archived entry was checked against its original SHA256 and byte length.
- The original source, trial, helpers, tag, baseline and failed stage must never
  be edited, reentered, rescored or reused as a fresh trial.

## Prospective V11 correction

Prefer original known-run artifact delivery within the existing60s audit window
before external cancellation. The controller's internal900s deadline still
forbids new source work; retrieval after deadline is audit-only and cannot supply
new accepted facts. Preserve raw declined/timed-out action counters and provenance.

Known selfguard termination is case-local. Missing artifact/counter tails stay
explicitly unknown and preseal ineligible. Genuine provider/model refusal,
identity/hash/counter/cap or integrity failure still stops the whole batch with
a durable first cause. Offline closing retains the last predeadline accepted
journal event/hash, audits every action and charges the recorded tail without
accepting its facts. Closing notes must not replace the initial error.

New V11 helpers and actual-parent/report regressions are prospective only.
After current-main integration and offline/source/OS/freeze/CI gates, use a fresh
same-ten paired trial. Owner60/6 budgets, algorithm120s, expert900s/default
reasoning,62 reviewed accessible facts and40 threshold remain fixed. No new
trial, batches50, HELDOUT150, paid credits or production completion is claimed.
