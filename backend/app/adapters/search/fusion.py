"""Merge what every generator found, and remember who found it.

Discovery has several ways to produce a candidate URL: the curated registry,
a manual seed, the cache, a sitemap, the catalogue walker, the university's own
search, and — once a provider exists — web search. None of them is complete.
The registry knows ten pages about an institution and nothing about its
eleventh programme; a sitemap lists everything and ranks nothing; web search
ranks well and hallucinates institutions.

**Fusion here is by rank, not by score.** A BM25 score, a position in a
sitemap and a registry entry's confidence are not on one scale. Adding or
averaging them would produce a number with no meaning that would nonetheless
decide the order — the kind of quiet nonsense that survives review because the
output still looks sorted. Reciprocal Rank Fusion uses only each generator's
own ordering, so nothing has to be calibrated against anything, and a missing
generator simply contributes nothing instead of skewing a mean. That matters
today: ``WEB_SEARCH`` is absent until a provider is configured and
``SITE_SEARCH`` is absent for any site without a search.

Provenance survives into the output. A URL found by three independent
generators is one row that still names all three and the rank each gave it.
That agreement is the most useful thing fusion produces, and collapsing it
into a single score would throw it away at the moment it was computed.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from app.adapters.discovery.live_discovery import canonical_url


class Generator(StrEnum):
    """Where a candidate came from."""

    #: Curated and human-checked; the strongest evidence we hold.
    REGISTRY = "registry"
    #: An operator pointed at this page directly.
    MANUAL_SEED = "manual_seed"
    #: Verified earlier in this or a previous run.
    CACHE = "cache"
    #: The institution's own sitemap: complete, unordered.
    SITEMAP = "sitemap"
    #: Walking the catalogue pages the site publishes.
    CATALOGUE_WALKER = "catalogue_walker"
    #: The search the site offers its visitors (V2-15).
    SITE_SEARCH = "site_search"
    #: An external search provider (V2-10). Absent until one is configured.
    WEB_SEARCH = "web_search"


#: How much one generator's opinion counts. These are trust weights, not
#: quality scores: a curated registry entry was checked by a person, and a web
#: result is a stranger's guess about which page matters. Written down as a
#: named table so the judgement is arguable rather than buried in an ordering.
#: Deliberately untuned beyond that ordering — tuning belongs to a benchmark
#: run, and the reranking ceiling is currently zero.
GENERATOR_WEIGHTS: Mapping[Generator, float] = {
    Generator.REGISTRY: 1.6,
    Generator.MANUAL_SEED: 1.6,
    Generator.CACHE: 1.2,
    Generator.SITE_SEARCH: 1.2,
    Generator.CATALOGUE_WALKER: 1.0,
    Generator.WEB_SEARCH: 1.0,
    Generator.SITEMAP: 0.6,
}

#: The constant in Reciprocal Rank Fusion. 60 is the value the method was
#: published with and is used here for the reason it was chosen there: it
#: flattens the difference between ranks 1 and 2 enough that one generator
#: cannot dominate on its own, while still preferring earlier ranks.
RRF_K = 60


@dataclass(frozen=True, slots=True)
class SourcedCandidate:
    """One URL as one generator ranked it."""

    url: str
    generator: Generator
    rank: int
    title: str = ""

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError(f"Rank is 1-based, got {self.rank}")
        if not self.url:
            raise ValueError("A candidate without a URL is not a candidate")


@dataclass(frozen=True, slots=True)
class Attribution:
    """Which generator found a page, and where it put it."""

    generator: Generator
    rank: int


@dataclass(frozen=True, slots=True)
class FusedCandidate:
    url: str
    title: str
    score: float
    #: Every generator that found this URL, strongest weight first.
    attributions: tuple[Attribution, ...]

    @property
    def generators(self) -> tuple[Generator, ...]:
        return tuple(a.generator for a in self.attributions)

    @property
    def agreement(self) -> int:
        """How many independent generators found this page.

        The most useful number fusion produces: two generators that share no
        code arriving at the same URL is far stronger evidence than either
        ranking it first alone.
        """
        return len(self.attributions)

    @property
    def best_rank(self) -> int:
        return min(a.rank for a in self.attributions)

    @property
    def provenance(self) -> str:
        """Readable attribution, for a report or a reviewer."""
        return ", ".join(f"{a.generator}#{a.rank}" for a in self.attributions)


def fuse(
    streams: Mapping[Generator, Sequence[SourcedCandidate]] | Iterable[SourcedCandidate],
    *,
    top_k: int = 20,
    weights: Mapping[Generator, float] | None = None,
) -> tuple[FusedCandidate, ...]:
    """Merge ranked candidate lists into one, keeping every attribution.

    Accepts either a mapping of generator to its ranked list, or a flat
    iterable of candidates that already know their generator. Deduplication is
    on the canonical URL, so the same page reached three ways is one row.
    """
    if top_k < 1:
        raise ValueError(f"top_k must be at least 1, got {top_k}")
    table = dict(GENERATOR_WEIGHTS if weights is None else weights)

    flat: list[SourcedCandidate] = []
    if isinstance(streams, Mapping):
        for generator, candidates in streams.items():
            for candidate in candidates:
                if candidate.generator != generator:
                    raise ValueError(
                        f"{candidate.url} is filed under {generator!r} but carries "
                        f"{candidate.generator!r}. An attribution that is wrong is worse "
                        "than none: it is the thing a reviewer would trust."
                    )
                flat.append(candidate)
    else:
        flat = list(streams)

    scores: dict[str, float] = {}
    titles: dict[str, str] = {}
    found: dict[str, dict[Generator, int]] = {}

    for candidate in flat:
        url = canonical_url(candidate.url)
        weight = table.get(candidate.generator, 1.0)
        scores[url] = scores.get(url, 0.0) + weight / (RRF_K + candidate.rank)
        # First non-empty title wins; generators disagree about titles and the
        # earliest one is the best-ranked.
        if candidate.title and not titles.get(url):
            titles[url] = candidate.title
        seen = found.setdefault(url, {})
        # One generator listing a URL twice is one attribution, at its best rank.
        if candidate.generator not in seen or candidate.rank < seen[candidate.generator]:
            seen[candidate.generator] = candidate.rank

    fused = [
        FusedCandidate(
            url=url,
            title=titles.get(url, ""),
            score=round(score, 6),
            attributions=tuple(
                Attribution(generator=g, rank=r)
                for g, r in sorted(
                    found[url].items(), key=lambda kv: (-table.get(kv[0], 1.0), kv[1], kv[0])
                )
            ),
        )
        for url, score in scores.items()
    ]
    # Score, then agreement, then URL: a deterministic order a test can pin
    # and a reviewer can reproduce.
    fused.sort(key=lambda c: (-c.score, -c.agreement, c.url))
    return tuple(fused[:top_k])
