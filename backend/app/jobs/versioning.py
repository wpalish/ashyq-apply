"""What a worker will agree to run.

A durable queue outlives the process that filled it. During a rolling
deployment two builds are alive at once, and whichever worker is running gets
whatever the API enqueued — including payloads written by a build it has never
seen.

That is not hypothetical here. A worker orphaned by `run.sh` kept polling for
six hours after the API had moved on. It claimed three `documents` jobs whose
payloads carried fields added by a later schema change, failed each of them
three times with `ValidationError: Extra inputs are not permitted`, and buried
them in the dead-letter state. From the applicant's side the research simply
stopped, and the only trace was a Pydantic error in a log nobody was reading.

Two separate things were wrong. The orphan is fixed in `run.sh`. This module
fixes the other one: a worker that cannot understand a payload must say so,
and must not consume the applicant's task while doing it.

Compatibility rules
-------------------

A payload is stamped with the schema version of the build that produced it.
A worker runs a job only when it supports that version.

  - **Older payload, newer worker** — supported. New fields must be optional
    with a defined meaning when absent, so an old payload decodes. This is the
    direction that must keep working, because a queue drained after a deploy is
    full of payloads from before it.
  - **Newer payload, older worker** — refused, never attempted. The job is
    parked in `blocked_incompatible`, which costs no attempt and is not a
    failure of the work. A worker that does support the version releases it on
    startup.

The deployment rule that follows: **deploy workers before the API**. A worker
that is ahead of the API can read everything the API produces. An API ahead of
its workers parks jobs until the workers catch up — which is recoverable, but
it is a stall, and a stall is worth avoiding by ordering the rollout.

Draining is not required *after* this mechanism exists. Parking is what makes
that true.

The first rollout is the exception, and it has to be said plainly
-----------------------------------------------------------------

A worker built before this module has no version check to run. It will happily
claim a payload from a newer API and fail it three times, which is exactly the
incident this exists to prevent — and nothing in the new build can stop it,
because the decision is taken in the old one.

For the deployment that introduces this mechanism, and only that one, the old
workers must be stopped before the new API serves traffic:

    1. stop every running worker (they hold no state; in-flight jobs return to
       the queue by lease expiry, which is what the reaper is for)
    2. deploy the new worker build
    3. deploy the new API

Every deployment after it is a normal rolling one: workers first, then the API,
with no drain, because from then on a worker that cannot read a payload parks
it instead of consuming it.

`scripts/compose_smoke.sh` exercises the steady state. The barrier above is a
one-time operational step and is written down here because there is nowhere in
the code it can be enforced from.
"""

from __future__ import annotations

import os
from typing import Final

#: Bumped when a payload gains a field a worker must understand to run the job
#: correctly, or when the meaning of an existing field changes.
#:
#: Do not bump it for a new *optional* field whose absence has a defined
#: meaning: an older worker ignoring it produces a correct result, and parking
#: the job instead would stall a deployment for no gain.
#:
#: History
#:   1 — initial durable payloads (`research`, `documents`).
PAYLOAD_SCHEMA_VERSION: Final[int] = 1

#: Versions this build will execute. Kept explicit rather than "anything at or
#: below current" so dropping support for an ancient payload is a visible edit
#: with a test behind it, not a silent consequence of a bump.
SUPPORTED_PAYLOAD_SCHEMA_VERSIONS: Final[frozenset[int]] = frozenset({1})

#: Identifies the build that produced or ran a job, so a stalled queue can be
#: traced to the pair of builds that disagreed — without reading a single
#: applicant's data.
#:
#: `"0.1.0"` identified nothing: every build this project has ever produced
#: reports it, so two builds that disagree look identical in the record. The
#: image is stamped with the commit it was built from, and that is what is
#: reported. The fallback keeps a developer's checkout working, and says
#: plainly that it is not a released build rather than inventing a version.
def _build_identifier() -> str:
    sha = (os.environ.get("ASHYQ_BUILD_SHA") or "").strip()
    if sha:
        return sha[:12]
    return "unversioned-local-build"


BUILD_VERSION: Final[str] = _build_identifier()


def supports(payload_schema_version: int) -> bool:
    """Whether this build will run a job stamped with this version."""
    return payload_schema_version in SUPPORTED_PAYLOAD_SCHEMA_VERSIONS


def incompatibility(payload_schema_version: int) -> dict[str, object]:
    """A structured reason a job was parked, safe to log and to store.

    Deliberately contains no payload and no applicant data: the whole point is
    that this build could not read the payload, so it is in no position to
    decide which parts of it are safe to repeat.
    """
    return {
        "reason": "unsupported_payload_schema_version",
        "job_payload_schema_version": payload_schema_version,
        "worker_build": BUILD_VERSION,
        "worker_supports": sorted(SUPPORTED_PAYLOAD_SCHEMA_VERSIONS),
        "resolution": (
            "start a worker that supports this payload version; it releases "
            "parked jobs on startup"
        ),
    }
