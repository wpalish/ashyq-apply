"""The seam every web-search provider sits behind.

Discovery needs a web search layer, but the project must not end up owning a
particular vendor's client objects. Everything above this module sees
``SearchResult`` and nothing else, so swapping Brave for Exa is a configuration
change rather than a refactor.

Two rules are worth stating where the types live, because they are easy to
break later and expensive to notice:

**A search result is a discovery hint, never evidence.** It says "this URL may
be worth fetching". It does not say what the page contains. A snippet is a
vendor's summary of a page nobody on our side has read yet, and no claim,
label or requirement may ever cite one. Fetch the page through ``Fetcher`` and
cite that. ``SearchResult`` deliberately has no field a claim could be built
from: no value, no scope, no excerpt-of-record.

**No applicant data reaches a provider.** ``search`` takes a query string and
nothing else. There is no overload taking a profile, and there should never be
one: whatever a provider is sent is logged by that provider, and a name, score
or budget sent once cannot be unsent. Query construction is its own task with
its own privacy rules.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


class SearchError(RuntimeError):
    """Base class for every failure this seam reports."""


class SearchProviderNotConfigured(SearchError):
    """Raised when search is asked for and no provider is configured.

    Deliberately an error rather than an empty ``SearchResponse``. A caller
    that cannot tell "the provider found nothing" from "there is no provider"
    will quietly report the second as the first, and a discovery layer that
    silently stops searching is the hidden fallback this project bans.
    """


class SearchUnavailable(SearchError):
    """The configured provider could not answer: timeout, quota, transport.

    Separate from :class:`SearchProviderNotConfigured` because the two call for
    different behaviour. This one is retryable and is a degraded run; that one
    is a deployment that was never asked to search at all.
    """


@dataclass(frozen=True, slots=True)
class SearchResult:
    """One candidate URL, as a provider ranked it."""

    url: str
    title: str
    provider: str
    rank: int
    retrieved_at: datetime
    #: The provider's own summary, when it supplies one. A hint for ranking
    #: and nothing else — never quote it, never treat it as page content.
    snippet: str = ""

    def __post_init__(self) -> None:
        if not self.url:
            raise ValueError("A search result without a URL is not a result")
        if not self.provider:
            raise ValueError(
                "Every result records which provider produced it; an unattributed "
                "result cannot be audited or compared across providers"
            )
        if self.rank < 1:
            raise ValueError(f"Rank is 1-based, got {self.rank}")


@dataclass(frozen=True, slots=True)
class SearchResponse:
    """What one provider returned for one query."""

    query: str
    provider: str
    retrieved_at: datetime
    results: tuple[SearchResult, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        ranks = [r.rank for r in self.results]
        if ranks != sorted(ranks):
            raise ValueError("Results must be ordered by the provider's own rank")
        if len(set(ranks)) != len(ranks):
            raise ValueError("Two results share a rank; the provider's order is ambiguous")
        foreign = {r.provider for r in self.results} - {self.provider}
        if foreign:
            raise ValueError(
                f"Results attributed to {sorted(foreign)} in a {self.provider!r} response. "
                "Fusing several providers is a separate step with its own provenance."
            )

    def __len__(self) -> int:
        return len(self.results)


@runtime_checkable
class SearchProvider(Protocol):
    """What discovery may assume about any provider, present or future."""

    #: Stable, lowercase, stamped onto every result this provider returns.
    name: str

    async def search(
        self,
        *,
        query: str,
        domains: Sequence[str] = (),
        max_results: int = 10,
    ) -> SearchResponse:
        """Rank candidate URLs for ``query``.

        ``domains`` restricts results to those hosts when the provider supports
        it. A provider that cannot restrict must filter its own results rather
        than return unrestricted ones, so the caller's guarantee holds
        everywhere. Raises :class:`SearchUnavailable` if it cannot answer;
        returning an empty response means it answered and found nothing.
        """
        ...
