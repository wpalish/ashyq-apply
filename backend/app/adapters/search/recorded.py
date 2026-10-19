"""Search answered from results a provider already returned: replay, never a request.

Added 2026-10-19, when the paid search credits ran out and the owner froze paid
search: the work *after* search (ranking, the read cap, identity and confirm,
extraction) goes on offline by replaying the result lists past benchmark
captures recorded (WF-17's ``search_results``). The pages those lists name are
still fetched live through ``Fetcher``; only the search call is replayed.

Three rules, each structural rather than a matter of care:

**No network, ever.** This module imports no HTTP client and builds no
request. A query the store has no answer for is an *explicit miss*: an empty
response, counted in :data:`COUNTERS` (``recorded_search_misses``), never a
call to anyone.

**No fallback.** The provider is constructed from a :class:`RecordedSearchStore`
and nothing else. It holds no inner provider, takes no key and has no
parameter through which one could be handed to it, so "replay, else ask the
paid provider" cannot be configured — the search layer is one provider
(``UNIMATCH_SEARCH_PROVIDER=recorded``), and a miss stays a miss.

**A miss is visible.** A rule that changes the queries is answered with empty
results for every query the captures never sent; the benchmark harness copies
the counters into each case's telemetry and the scorecard reports them, so
such a rule reads as unmeasurable on the replay rather than as a loss of the
pipeline.

The store is keyed by what reached the provider: the query text (whitespace
collapsed, NFC, case-folded), the domain filter, and ``hl``/``gl`` for a
localised query. ``max_results`` only truncates. Results carry no title or
snippet: the captures record URLs only, and an empty string is what the seam
already uses for "the provider gave none".
"""

from __future__ import annotations

import hashlib
import json
import logging
import unicodedata
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.adapters.search.base import SearchResponse, SearchResult

log = logging.getLogger(__name__)

#: Stamped on every result, so a stored result says no live retrieval happened.
RECORDED_PROVIDER_NAME = "recorded"
#: The store document's format; a file with any other value is refused.
STORE_SCHEMA = "recorded-search/1"


def normalise_query(query: str) -> str:
    """The query as the store keys it: NFC, whitespace collapsed, case-folded."""
    return unicodedata.normalize("NFC", " ".join(query.split())).casefold()


def _normalise_domain(domain: str) -> str:
    return domain.strip().casefold().lstrip(".")


def request_key(
    query: str, domains: Sequence[str] = (), hl: str | None = None, gl: str | None = None
) -> str:
    """The key of one provider request: the parameters that change its answer.

    ``domains`` is a set (order and duplicates do not change a ``site:``
    filter); ``hl``/``gl`` are empty for an ordinary query.
    """
    return json.dumps(
        [
            normalise_query(query),
            sorted({_normalise_domain(d) for d in domains if d and d.strip()}),
            (hl or "").casefold(),
            (gl or "").casefold(),
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def key_digest(key: str) -> str:
    """A short, stable name for a key, for logs that must not carry query text."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]


class RecordedStoreError(ValueError):
    """The store file is not a recorded-search store this build can trust."""


def _public_url(url: object) -> bool:
    if not isinstance(url, str) or not url:
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme in {"http", "https"} and bool(parts.hostname)


@dataclass(frozen=True)
class RecordedSearchStore:
    """Request key -> the result URLs a provider returned for it, best first."""

    entries: Mapping[str, tuple[str, ...]]
    #: Where the lists came from (runs, dates, repetitions); never read by search.
    provenance: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_document(cls, document: object) -> RecordedSearchStore:
        """Validate a parsed store document and index its entries by request key."""
        if not isinstance(document, dict) or document.get("schema") != STORE_SCHEMA:
            raise RecordedStoreError(f"not a {STORE_SCHEMA!r} document")
        rows = document.get("entries")
        if not isinstance(rows, list):
            raise RecordedStoreError("'entries' must be a list")
        entries: dict[str, tuple[str, ...]] = {}
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise RecordedStoreError(f"entry {index} is not an object")
            query = row.get("query")
            domains = row.get("domains", [])
            urls = row.get("urls")
            hl, gl = row.get("hl"), row.get("gl")
            if not isinstance(query, str) or not query.strip():
                raise RecordedStoreError(f"entry {index} has no query")
            if not isinstance(domains, list) or not all(isinstance(d, str) for d in domains):
                raise RecordedStoreError(f"entry {index}: 'domains' must be a list of strings")
            if any(v is not None and not isinstance(v, str) for v in (hl, gl)):
                raise RecordedStoreError(f"entry {index}: 'hl'/'gl' must be strings or null")
            if not isinstance(urls, list) or not all(_public_url(u) for u in urls):
                raise RecordedStoreError(f"entry {index}: 'urls' must be http(s) URLs")
            key = request_key(query, domains, hl, gl)
            kept = tuple(urls)
            if key in entries and entries[key] != kept:
                raise RecordedStoreError(
                    f"entry {index} repeats a request with a different result list"
                )
            entries[key] = kept
        provenance = document.get("provenance") or {}
        if not isinstance(provenance, dict):
            raise RecordedStoreError("'provenance' must be an object")
        return cls(entries=entries, provenance=provenance)

    @classmethod
    def from_file(cls, path: Path) -> RecordedSearchStore:
        try:
            document = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RecordedStoreError(f"cannot read recorded search store {path}: {exc}") from exc
        return cls.from_document(document)

    def __len__(self) -> int:
        return len(self.entries)


_LOADED: dict[tuple[str, int, int], RecordedSearchStore] = {}


def load_store(path: Path) -> RecordedSearchStore:
    """The store at ``path``, parsed once per process (and again if the file changes).

    ``get_search_provider`` builds a fresh adapter on every call, and one case
    asks for one several times; re-reading the JSON each time is waste.
    """
    resolved = Path(path).resolve()
    stat = resolved.stat()
    marker = (str(resolved), stat.st_mtime_ns, stat.st_size)
    store = _LOADED.get(marker)
    if store is None:
        store = RecordedSearchStore.from_file(resolved)
        _LOADED.clear()
        _LOADED[marker] = store
    return store


#: H-1 (replay plan 2026-10-19 §5.4): who asked. The store holds discovery's
#: requests only, so a topic, scholarship or identity search misses on every
#: replay; counting misses per kind lets the scorecard judge a rule on the
#: discovery misses alone instead of on query counts that vary with reads.
SEARCH_KINDS = ("discovery", "topic", "scholarship", "identity")

#: The kind of search the running stage sends; ``None`` outside every stage
#: the harness marks, and such a miss is counted in the total only. A context
#: variable, so concurrent tasks each keep the stage they were started in.
_ACTIVE_KIND: ContextVar[str | None] = ContextVar("recorded_search_kind", default=None)


@contextmanager
def search_kind(kind: str) -> Iterator[None]:
    """Attribute every recorded request made inside the block to ``kind``.

    Measurement only: the benchmark harness wraps the four stages that search
    with it, and nothing under ``app/`` calls it, so the answer to a request is
    the same whichever kind is active.
    """
    if kind not in SEARCH_KINDS:
        raise ValueError(f"Unknown search kind {kind!r}; expected one of {SEARCH_KINDS}")
    token = _ACTIVE_KIND.set(kind)
    try:
        yield
    finally:
        _ACTIVE_KIND.reset(token)


@dataclass
class RecordedCounters:
    """Process-wide hits and misses: every adapter of one capture adds here."""

    hits: int = 0
    misses: int = 0
    #: :func:`key_digest` of each missed request, in order (no query text).
    missed: list[str] = field(default_factory=list)
    #: H-1: misses per :data:`SEARCH_KINDS` entry; a miss outside every marked
    #: stage is in :attr:`misses` only.
    misses_by_kind: dict[str, int] = field(default_factory=lambda: dict.fromkeys(SEARCH_KINDS, 0))

    def reset(self) -> None:
        self.hits = 0
        self.misses = 0
        self.missed.clear()
        self.misses_by_kind = dict.fromkeys(SEARCH_KINDS, 0)


#: Read by the benchmark harness into ``recorded_search_hits`` /
#: ``recorded_search_misses``. One capture child process runs one case.
COUNTERS = RecordedCounters()


class RecordedSearchProvider:
    """Answers from a :class:`RecordedSearchStore`; a request it has no answer for is a miss.

    The constructor takes the store and an optional clock, and nothing else:
    there is deliberately no way to give it a second provider to ask.
    """

    name = RECORDED_PROVIDER_NAME

    def __init__(self, store: RecordedSearchStore, *, now: datetime | None = None) -> None:
        if not isinstance(store, RecordedSearchStore):
            raise TypeError("RecordedSearchProvider answers from a RecordedSearchStore only")
        self._store = store
        self._now = now

    async def search(
        self,
        *,
        query: str,
        domains: Sequence[str] = (),
        max_results: int = 10,
    ) -> SearchResponse:
        return self._answer(query, domains, max_results, None, None)

    async def search_localized(
        self,
        *,
        query: str,
        hl: str,
        gl: str,
        domains: Sequence[str] = (),
        max_results: int = 10,
    ) -> SearchResponse:
        """``search`` keyed with ``hl``/``gl``, as a localised query was recorded.

        Present because discovery sends R5's ``local_language`` family through
        ``search_localized`` when a provider has it, as the recorded provider
        did; without it the replay would ask for a different key.
        """
        return self._answer(query, domains, max_results, hl, gl)

    def _answer(
        self,
        query: str,
        domains: Sequence[str],
        max_results: int,
        hl: str | None,
        gl: str | None,
    ) -> SearchResponse:
        if not query.strip():
            raise ValueError("A search needs a query")
        if max_results < 1:
            raise ValueError(f"max_results must be at least 1, got {max_results}")
        key = request_key(query, domains, hl, gl)
        urls = self._store.entries.get(key)
        retrieved_at = self._now or datetime.now(UTC)
        if urls is None:
            COUNTERS.misses += 1
            COUNTERS.missed.append(key_digest(key))
            if (kind := _ACTIVE_KIND.get()) is not None:
                COUNTERS.misses_by_kind[kind] += 1
            log.info("recorded search miss %s", key_digest(key))
            urls = ()
        else:
            COUNTERS.hits += 1
        results = tuple(
            SearchResult(
                url=url, title="", provider=self.name, rank=rank, retrieved_at=retrieved_at
            )
            for rank, url in enumerate(urls[:max_results], start=1)
        )
        return SearchResponse(
            query=query, provider=self.name, retrieved_at=retrieved_at, results=results
        )
