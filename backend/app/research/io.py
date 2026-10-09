"""Native I/O guard: durable reservation first, real operation timeout second."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Literal, TypeVar

from app.adapters.fetching import Fetcher, FetchResult
from app.pipeline.control import UniversityReadStopped

Kind = Literal["query", "read"]
T = TypeVar("T")
EVIDENCE_OBSERVER: ContextVar[Callable[[str, FetchResult], None] | None] = ContextVar(
    "staged_evidence_observer", default=None
)
ACTIVE_RESERVATION: ContextVar[Callable[[Kind], int] | None] = ContextVar(
    "staged_io_reservation", default=None
)


async def guarded_call(kind: Kind, operation: Callable[[], Awaitable[T]]) -> T:
    reserve = ACTIVE_RESERVATION.get()
    if reserve is None:
        return await operation()
    remaining_ms = reserve(kind)  # Caller commits ownership fence before returning.
    try:
        async with asyncio.timeout(remaining_ms / 1000):
            return await operation()
    except TimeoutError as exc:
        raise UniversityReadStopped("staged_time_cap") from exc


class StagedFetcher(Fetcher):
    def __init__(self, *args, legacy_before_get: Callable[[], None] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.legacy_before_get = legacy_before_get

    async def get(
        self,
        url: str,
        *,
        use_cache: bool = True,
        etag: str | None = None,
        if_modified_since: str | None = None,
    ) -> FetchResult:
        if self.legacy_before_get is not None:
            self.legacy_before_get()
        # super() must be bound outside the nested callable.
        native_get = super().get
        result = await guarded_call(
            "read",
            lambda: native_get(
                url,
                use_cache=use_cache,
                etag=etag,
                if_modified_since=if_modified_since,
            ),
        )
        observer = EVIDENCE_OBSERVER.get()
        if result.ok and observer is not None:
            observer(url, result)
        return result
