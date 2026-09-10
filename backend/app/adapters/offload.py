"""Running blocking work off the event loop.

The crawler is asynchronous and everything it parses arrives from a third-party
site: HTML up to ``MAX_BYTES`` and PDFs, which pypdf's own advisories name as a
denial-of-service surface — ``requirements.txt`` says so next to the pin. Doing
that work on the loop stops every other coroutine in the process, and in the
worker that includes the job heartbeat, which fires every
``job_lease_seconds / 3``.

So a page that takes longer than the lease to parse does not merely run slowly.
The heartbeat cannot fire, the lease expires, another worker reaps the job and
starts it again, and this attempt's writes are fenced off as ``LeaseLost`` —
one hostile document turning into repeated work and a run that looks stuck. The
same stall freezes whatever else that worker is running concurrently.

``to_thread`` is enough here because the part that actually takes time releases
the GIL — lxml's C parser, pypdf's zlib, the resolver's socket call — and none
of the functions handed to it touches an ORM session or any other state the
loop owns.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


async def off_loop(fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    """Run ``fn`` on a worker thread so the event loop keeps serving."""
    return await asyncio.to_thread(fn, *args, **kwargs)
