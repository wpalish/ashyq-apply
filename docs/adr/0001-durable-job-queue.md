# ADR 0001 — Durable job queue on PostgreSQL, not Redis

**Status:** accepted
**Date:** 2026-08-28

## Context

The in-process `asyncio` queue is not durable: a worker crash loses the job,
and a run is left claiming to be running. The brief asked for Redis with
Celery, Dramatiq or RQ.

Neither Redis nor Docker nor Homebrew is available on this machine, and
installing any of them requires either a system-wide change or the user's
password. Under rule 14 that is a checkpoint, not a default I may take.

A real PostgreSQL *is* available without any system change: the `pgserver`
package ships PostgreSQL 16.2 binaries and starts a server against a local data
directory. That gives real migrations, real constraints and real transactional
semantics — everything the schema work needs.

## Decision

Implement the durable queue on PostgreSQL using `SELECT … FOR UPDATE SKIP
LOCKED`, and do not adopt Redis for now.

This is not a workaround. It is the same mechanism behind Oban (Elixir), Que and
GoodJob (Ruby), River (Go) and Procrastinate (Python). For this workload it is
arguably the better fit:

* jobs are minutes long and low-volume — throughput is not the constraint;
* a job's state and the data it produces belong in **one** transaction, so a
  crash cannot leave a job marked done with its results missing. With Redis
  those are two systems and that guarantee has to be reconstructed;
* it removes an entire component from the deployment.

The queue is defined behind `JobStore`, whose surface is `enqueue`, `claim`,
`heartbeat`, `complete`, `fail`, `cancel` and `reap_expired` — the operations
any broker provides. Moving to Redis later replaces one module.

## What this buys us

* **Durability** — jobs survive a restart of every process.
* **Leases** — a claimed job carries an expiry and a token; a worker that stops
  beating loses it, and cannot write to it afterwards. Both halves of that were
  untrue as first written — see
  [0004 — lease fencing](0004-lease-fencing.md).
* **Reaping** — expired leases return to the queue, or to `dead` once attempts
  are exhausted.
* **Idempotency** — a unique key stops the same work being enqueued twice.
* **Backoff** — `available_at` defers a retry; the delay grows per attempt.
* **Cancellation** — observed between units of work, so it lands cleanly.
* **Bounded concurrency** — per worker and, separately, per host being fetched.

## Consequences

* PostgreSQL is now required in production. SQLite remains supported for local
  development; `SKIP LOCKED` is skipped there, which is safe because SQLite
  serialises writers anyway.
* Very high job rates would eventually want a real broker. This workload is
  nowhere near that, and the interface is ready for it.

## Checkpoint for the user

If you want Redis + Dramatiq instead, that needs Docker or Homebrew installed,
which needs your password. Say the word and it is a contained change:
`app/jobs/store.py` gains a second implementation and the compose file gains a
service.
