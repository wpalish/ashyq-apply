# 4. A lease is a token, and a heartbeat is a thread

Date: 2026-08-30
Status: Accepted
Extends: [0001 — durable job queue](0001-durable-job-queue.md)

## Context

ADR 0001 lists **leases** among what the queue buys us: "a claimed job carries
an expiry; a worker that stops beating loses it." Both halves of that sentence
were false in the implementation, in ways that only show up under the conditions
leases exist for.

**Losing a lease did not stop a worker writing.** `heartbeat`, `complete`,
`fail` and `mark_cancelled` matched on job id and `RUNNING` status alone. There
was no notion of *which claim* was writing, so a worker that stalled past its
lease — a long GC pause, a suspended container, a host that swapped it out —
could wake up and extend a lease another worker now held, mark that worker's job
succeeded, or fail work it had already finished. `heartbeat`'s docstring said
"False if the job is no longer ours to extend"; the query underneath it could
not tell "ours" from anyone else's.

**A worker never stopped beating, because it never started.** Both the lease
heartbeat and the liveness heartbeat were `asyncio.Task`s, and the pipeline is
synchronous work behind an `async def`. Instrumenting a real 54-second run
showed the lease beat task starting and never waking from its first `sleep`.

The consequence is not subtle. With the shipped `job_lease_seconds = 120`, any
job that takes longer than two minutes loses its lease *while running normally*,
is reaped, and is handed to a second worker — which then runs the same research
run alongside the first. The liveness file went stale on the same schedule, so
a healthy worker doing exactly the work it exists to do failed its container
healthcheck and was restarted mid-job.

Both mechanisms were disabled by precisely the jobs they were built for.

## Decision

**Every claim mints a `lease_token`, and every write presents it.**

- `jobs.lease_token` — 32 random hex characters from `secrets.token_hex(16)`,
  regenerated at every claim. Not a PID and not a timestamp: PIDs are reused
  and clocks go backwards, and neither can distinguish two runs of one job.
- `heartbeat`, `complete`, `fail` and `mark_cancelled` match on job id, status
  **and** token. A mismatch writes nothing and says so in the return value —
  `complete` returns a bool, `fail` returns `None` — because a worker that has
  lost its lease has to be able to find out.
- An **empty** token matches nothing. Treating it as a wildcard would restore
  the original bug in a shape nobody would look at again.
- `reap_expired` clears the token. Reaping is what revokes ownership, so the
  worker that stopped beating cannot match after its job is given away.
- `fail` and `mark_cancelled` take the token optionally, because a person
  cancelling through the API holds no lease. A *worker* always passes one.

**Both heartbeats run on OS threads, not on the event loop.**

A thread is not starved by a blocked loop. It is still a real liveness signal: a
worker whose process is wedged — deadlocked, suspended, out of memory — cannot
run the thread either, which is what should make the file stale.

**An unreachable database is "unknown", not "lost".** The two are different and
the difference matters:

- the store answering *no* is definitive — another worker holds the job — and is
  acted on at once;
- the database being unreachable tells us nothing. Work continues until the
  lease would have lapsed, because until that moment no reaper can have given
  the job away. After it, the work stops whether or not the reason is knowable.

**Losing the lease stops the work, at the first safe point.** Awaited work is
cancelled directly. Blocking work stops at the pipeline's existing cancellation
checkpoint, which now also raises `LeaseLost`. `LeaseLost` writes *nothing* —
not a success, not a failure, not a cancellation — because the job's state
already belongs to whoever holds it, and a second writer recording an outcome is
the corruption this ADR is about.

## Consequences

- One indexed-by-primary-key column and one extra equality per write. Nothing
  measurable at this workload.
- `LeaseLost` is a third way a job can stop, distinct from success and failure,
  and deliberately invisible in the job's own record: the job is left exactly as
  its current holder has it.
- Two threads per busy worker (one liveness, one lease per running job). They do
  nothing but sleep and issue one small `UPDATE`.
- A job whose row predates this column has a null token. A worker refuses to run
  it rather than running it unfenced; the reaper re-claims it and mints one.
- The migration is additive and nullable, so a rollback needs no data change.

## How this is tested

- `tests/test_job_lease_fencing.py` — the store's refusals, on PostgreSQL.
- `tests/test_worker_split_brain.py` — the worker stops when the lease goes,
  including with the event loop blocked, and does not swallow a shutdown.
- `scripts/split_brain_test.py` — two real worker processes. Worker A is
  SIGSTOPped past its lease, B reaps and takes the job, then A is SIGCONTed and
  given several lease periods to interfere. Asserts no duplicate results, no
  attempt inflation, and that A reported losing the lease rather than finishing
  a job it no longer held. A mock cannot produce that state; SIGSTOP can, with
  no cooperation from the process being stopped.
