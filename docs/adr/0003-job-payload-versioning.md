# 3. Job payloads carry a version, and a worker that cannot read one parks it

Date: 2026-08-30
Status: Accepted
Extends: [0001 — durable job queue](0001-durable-job-queue.md)

## Context

A durable queue outlives the process that filled it. During a rolling
deployment two builds are alive at once, and whichever worker is running gets
whatever the API enqueued — including payloads written by a build it has never
seen.

This was not a thought experiment. `run.sh` orphaned every worker it started
(fixed separately), and one of those orphans was still polling six and a half
hours after the API had moved on. It claimed three `documents` jobs whose
payloads carried two fields added by a later schema change and failed each of
them three times:

```
ValidationError: 2 validation errors for ProgramResult
scholarships.0.restriction_logic — Extra inputs are not permitted
scholarships.0.restriction_evidence — Extra inputs are not permitted
```

Three attempts is the retry limit, so all three landed in `dead`. `dead` means
attempts are exhausted and a person has to decide. Nobody was told. From the
applicant's side their research simply stopped, and the only evidence was a
Pydantic error in a log nobody was reading.

Two distinct faults produced that outcome. The orphan is one. The other is that
**the queue had no way to express "I cannot read this"** — so a worker
expressed it as failure, and failure spends the applicant's work.

## Decision

Every job records the payload contract it was written against, and a worker
runs a job only if it supports that version.

- `jobs.payload_schema_version` — an integer, defaulting to `1` so rows written
  before the column existed decode as what they are.
- `jobs.producer_version` — which build enqueued it.
- `app/jobs/versioning.py` holds `PAYLOAD_SCHEMA_VERSION` (what this build
  writes) and `SUPPORTED_PAYLOAD_SCHEMA_VERSIONS` (what it will run). The
  supported set is explicit rather than "anything at or below current", so
  dropping support for an old payload is a visible edit with a test behind it.

A job whose version is not supported goes to a new status,
**`blocked_incompatible`**:

- it costs **no attempt** — refusing work is not an attempt at it;
- it is **not terminal**, and deliberately not `dead`, because `dead` means a
  person must intervene and this resolves itself;
- `claim()` skips it, so another equally incapable worker does not spin on it;
- `last_error` holds a structured JSON reason with the job's version, the
  worker's build, the versions it supports, and how to resolve it. It contains
  **no payload and no applicant data** — this build could not read the payload,
  so it is in no position to decide which parts are safe to repeat;
- a worker releases every parked job it *can* read at startup, so finishing the
  rollout unblocks the queue with no operator action.

The student sees "Research paused", not "failed", with an explanation that
nothing has been lost and it will continue by itself.

## Compatibility rules

**Older payload, newer worker — must work.** A queue drained after a deploy is
full of payloads written before it. New fields must therefore be optional with
a defined meaning when absent. Do not bump the version for such a field: an
older worker ignoring it still produces a correct result, and parking the job
would stall a deployment for nothing.

**Newer payload, older worker — parked, never attempted.**

Bump `PAYLOAD_SCHEMA_VERSION` when a payload gains a field a worker must
understand to be correct, or when an existing field changes meaning.

## Deployment strategy

**Deploy workers before the API.** A worker ahead of the API can read
everything the API produces, so the queue never stalls. An API ahead of its
workers parks jobs until the workers catch up — recoverable, but a stall.

**Draining is not required.** Parking is what makes that true, and it is why
this is preferred to a drain: a drain has to be enforced by a human at the
right moment, and the failure mode when they forget is the one described above.

## Consequences

- One extra integer comparison per job. Nothing measurable.
- A new status the UI must handle. The frontend `JobStatus` union is checked
  against the backend enum by `test_the_job_status_union_matches_the_backend`,
  which caught this addition rather than letting the UI branch on a value it
  did not know.
- Versioning does not rescue a worker that predates this ADR: an old build has
  no version check to run. What protects against that is the supervisor in
  `run.sh`, which no longer leaves one behind. This decision protects every
  deployment after it, and makes the failure diagnosable rather than silent.
- `/api/health` reports `build`, `payload_schema_version` and
  `supported_payload_schema_versions`, and the worker logs the same at startup,
  so a stalled queue can be traced to the two builds that disagreed.
