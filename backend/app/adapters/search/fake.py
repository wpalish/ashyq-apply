"""An offline provider, so every test can exercise the seam without a vendor.

It answers only from a corpus the caller hands it. That is the point: a fake
that guesses plausible URLs would let a test pass against retrieval that does
not exist, and would put invented links in front of an applicant the first
time someone wired it up by accident. Unknown query, empty response.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from urllib.parse import urlsplit

from app.adapters.search.base import SearchResponse, SearchResult, SearchUnavailable

#: Stamped on every result. Anything reading a stored result can tell at a
#: glance that no real retrieval happened.
FAKE_PROVIDER_NAME = "fake"


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def _matches(host: str, domain: str) -> bool:
    """``nu.edu.kz`` matches itself and its subdomains, never ``notnu.edu.kz``."""
    domain = domain.lower().lstrip(".")
    return host == domain or host.endswith("." + domain)


class FakeSearchProvider:
    """A deterministic provider built from an explicit corpus.

    ``corpus`` maps a query to the URLs it should return, best first. Titles
    and snippets are optional and default to empty rather than to invented
    prose — a test that needs a title states one, and a test that does not
    never sees text nobody wrote.
    """

    name = FAKE_PROVIDER_NAME

    def __init__(
        self,
        corpus: Mapping[str, Sequence[str | tuple[str, str, str]]] | None = None,
        *,
        now: datetime | None = None,
        fail_with: str = "",
    ) -> None:
        self._corpus = dict(corpus or {})
        self._now = now
        #: When set, every call raises ``SearchUnavailable``. Lets a caller's
        #: degraded path be tested without patching internals.
        self._fail_with = fail_with
        self.calls: list[tuple[str, tuple[str, ...], int]] = []

    def _clock(self) -> datetime:
        return self._now or datetime.now(UTC)

    async def search(
        self,
        *,
        query: str,
        domains: Sequence[str] = (),
        max_results: int = 10,
    ) -> SearchResponse:
        if max_results < 1:
            raise ValueError(f"max_results must be at least 1, got {max_results}")
        self.calls.append((query, tuple(domains), max_results))
        if self._fail_with:
            raise SearchUnavailable(self._fail_with)

        retrieved_at = self._clock()
        rows: list[tuple[str, str, str]] = []
        for entry in self._corpus.get(query, ()):
            rows.append((entry, "", "") if isinstance(entry, str) else entry)

        if domains:
            rows = [row for row in rows if any(_matches(_host(row[0]), d) for d in domains)]

        results = tuple(
            SearchResult(
                url=url,
                title=title,
                snippet=snippet,
                provider=self.name,
                rank=rank,
                retrieved_at=retrieved_at,
            )
            for rank, (url, title, snippet) in enumerate(rows[:max_results], start=1)
        )
        return SearchResponse(
            query=query,
            provider=self.name,
            retrieved_at=retrieved_at,
            results=results,
        )
