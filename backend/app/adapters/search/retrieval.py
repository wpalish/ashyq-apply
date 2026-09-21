"""Rank what survived the prefilter, cheaply and explainably.

The phase guide's §6 lists a stack — deterministic score, BM25, multilingual
embeddings, a cross-encoder, Jev, a cheap LLM — and says in the same breath not
to deploy them all automatically. So this module ships the first two and leaves
the rest a seam. Each further layer costs money or latency per candidate and
has to earn it against the Phase-0 benchmark, which is exactly the measurement
V2-01 spent seven drafts making trustworthy.

BM25 is implemented here rather than pulled in, because it is twenty lines and
a dependency is forever. It scores a candidate's title, snippet and URL words
against the terms the ontology says name the requested field.

Every candidate carries the signals that produced its score. A ranking nobody
can explain cannot be debugged against a benchmark: "recall went from 1/10 to
3/10" is only actionable next to *why* each row moved.
"""

from __future__ import annotations

import math
import re
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field

from app.adapters.discovery.live_discovery import looks_like_catalogue
from app.adapters.search.base import SearchProvider, SearchResult, SearchUnavailable
from app.adapters.search.fusion import Generator, SourcedCandidate, fuse
from app.adapters.search.intent import DiscoveryIntent, DiscoveryQuery, queries_for
from app.adapters.search.navigation import navigation_candidates
from app.adapters.search.ontology import degree_aliases, ontology_version, retrieval_candidates
from app.adapters.search.prefilter import PrefilterOutcome, prefilter

#: How many of the best search results to open and read the navigation of.
#: A hop is a supplement to search, not a crawl: each one costs a fetch, and
#: the entry point search is surest about is the one worth opening.
DEFAULT_HOP_ENTRY_POINTS = 3

#: Standard BM25 constants. k1 bounds how much repeating a term helps; b is how
#: strongly a long document is penalised. Not tuned — tuning them without a
#: benchmark run would be decoration.
BM25_K1 = 1.5
BM25_B = 0.75

#: What the deterministic pass adds on top of the lexical score. Kept small and
#: named so a ranking can be read out loud.
SIGNAL_WEIGHTS = {
    "strong_alias_in_title": 3.0,
    "degree_in_title": 2.0,
    "catalogue_path": 1.5,
    "top_ranked_by_provider": 1.0,
    "related_field_only": -2.0,
    "pdf": -0.5,
}


def tokenize(text: str) -> list[str]:
    """Words of three or more characters, lowercased. Also splits URL slugs."""
    return [w for w in re.split(r"[^0-9a-zЀ-ӿ]+", text.lower()) if len(w) >= 3]


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    url: str
    title: str
    score: float
    provider: str
    #: Named reasons, best first. This is what makes a ranking reviewable.
    signals: tuple[str, ...] = ()
    is_pdf: bool = False

    @property
    def explanation(self) -> str:
        return ", ".join(self.signals) if self.signals else "lexical match only"


class _Bm25:
    """Okapi BM25 over a small candidate set."""

    def __init__(self, documents: Sequence[Sequence[str]]) -> None:
        self._docs = [list(d) for d in documents]
        self._n = len(self._docs)
        self._avg_len = (sum(len(d) for d in self._docs) / self._n) if self._n else 0.0
        self._df: dict[str, int] = {}
        for doc in self._docs:
            for term in set(doc):
                self._df[term] = self._df.get(term, 0) + 1

    def _idf(self, term: str) -> float:
        df = self._df.get(term, 0)
        # The +1 keeps a term present in every document from scoring negative,
        # which the textbook formula does and which would rank a perfect match
        # below an irrelevant one.
        return math.log(1 + (self._n - df + 0.5) / (df + 0.5))

    def score(self, index: int, query_terms: Sequence[str]) -> float:
        doc = self._docs[index]
        if not doc:
            return 0.0
        length = len(doc)
        total = 0.0
        for term in query_terms:
            frequency = doc.count(term)
            if not frequency:
                continue
            denominator = frequency + BM25_K1 * (
                1 - BM25_B + BM25_B * length / (self._avg_len or 1)
            )
            total += self._idf(term) * frequency * (BM25_K1 + 1) / denominator
        return total


@dataclass(frozen=True, slots=True)
class RetrievalReport:
    """What one discovery run did, in the shape telemetry and a benchmark want."""

    candidates: tuple[RankedCandidate, ...]
    queries_run: tuple[str, ...]
    provider: str
    ontology_version: str
    rejection_counts: dict[str, int] = field(default_factory=dict)
    #: Queries whose provider call failed. A degraded run must be visible as
    #: degraded rather than reported as a run that found less.
    failed_queries: tuple[str, ...] = ()
    #: Entry points whose navigation was read, and how many candidates the hop
    #: contributed. Zero of either is a fact worth seeing in a report.
    hop_entry_points: tuple[str, ...] = ()
    hop_candidates: int = 0


def rank_candidates(
    outcome: PrefilterOutcome,
    intent: DiscoveryIntent,
) -> tuple[RankedCandidate, ...]:
    """Score surviving candidates, best first."""
    kept = outcome.kept
    if not kept:
        return ()

    terms = retrieval_candidates(intent.field)
    strong = [t.term for t in terms if t.is_match]
    related = [t.term for t in terms if not t.is_match]
    query_terms = [w for term in strong for w in tokenize(term)]
    degrees = set(degree_aliases(intent.degree))

    documents = [tokenize(f"{c.title} {c.snippet} {c.url}") for c in kept]
    bm25 = _Bm25(documents)

    ranked: list[RankedCandidate] = []
    for index, candidate in enumerate(kept):
        score = bm25.score(index, query_terms)
        signals: list[str] = []
        haystack = f"{candidate.title} {candidate.url}".lower()

        if any(term.lower() in haystack for term in strong):
            signals.append("strong_alias_in_title")
        elif any(term.lower() in haystack for term in related):
            # Found the neighbourhood but not the field. Worth keeping and
            # worth pushing down: V2-12 is explicit that a related concept is
            # a candidate, never a match.
            signals.append("related_field_only")
        if any(alias in haystack for alias in degrees):
            signals.append("degree_in_title")
        if looks_like_catalogue(candidate.url):
            signals.append("catalogue_path")
        if candidate.rank == 1:
            signals.append("top_ranked_by_provider")
        if candidate.is_pdf:
            signals.append("pdf")

        score += sum(SIGNAL_WEIGHTS[s] for s in signals)
        ranked.append(
            RankedCandidate(
                url=candidate.url,
                title=candidate.title,
                score=round(score, 4),
                provider=candidate.provider,
                signals=tuple(signals),
                is_pdf=candidate.is_pdf,
            )
        )

    ranked.sort(key=lambda c: (-c.score, c.url))
    return tuple(ranked)


#: What a caller must supply to let the hop read a page: a coroutine taking a
#: URL and returning its HTML, or "" when it could not be read. Production
#: passes a ``Fetcher``-backed one so robots, rate limits, the PII guard and
#: the SSRF protections all still apply; tests pass a fake; evaluation tooling
#: passes its own. The seam exists so that none of them has to weaken
#: ``Fetcher`` to get its job done.
FetchPage = Callable[[str], Awaitable[str]]


async def discover_candidates(
    provider: SearchProvider,
    intent: DiscoveryIntent,
    *,
    query_budget: int | None = None,
    max_results_per_query: int = 10,
    top_k: int = 20,
    fetch: FetchPage | None = None,
    hop_entry_points: int = DEFAULT_HOP_ENTRY_POINTS,
) -> RetrievalReport:
    """Queries → provider → prefilter → ranking, bounded at every step.

    A provider failure on one query does not abort the run: the other queries
    are still worth asking, and the failure is reported rather than folded into
    a smaller result set.
    """
    if top_k < 1:
        raise ValueError(f"top_k must be at least 1, got {top_k}")

    queries: tuple[DiscoveryQuery, ...] = (
        queries_for(intent) if query_budget is None else queries_for(intent, budget=query_budget)
    )

    results: list[SearchResult] = []
    failed: list[str] = []
    for query in queries:
        try:
            response = await provider.search(
                query=query.text,
                domains=[intent.domain],
                max_results=max_results_per_query,
            )
        except SearchUnavailable:
            failed.append(query.family)
            continue
        results.extend(response.results)

    outcome = prefilter(results, domain=intent.domain, degree=intent.degree)
    ranked = rank_candidates(outcome, intent)

    opened: list[str] = []
    hopped: list[SourcedCandidate] = []
    if fetch is not None and hop_entry_points > 0:
        # Search finds entry points reliably; a page with no words in its URL
        # is found from one, not by a better query. See navigation.py.
        for candidate in ranked[:hop_entry_points]:
            try:
                html = await fetch(candidate.url)
            except Exception:
                html = ""
            if not html:
                continue
            opened.append(candidate.url)
            hopped.extend(navigation_candidates(html, candidate.url, intent))

    if hopped:
        # Fused by rank, so a page both generators found keeps both
        # attributions — the agreement signal is the reason to have two.
        from_search = [
            SourcedCandidate(url=c.url, generator=Generator.WEB_SEARCH, rank=index, title=c.title)
            for index, c in enumerate(ranked, start=1)
        ]
        merged = fuse([*from_search, *hopped], top_k=top_k)
        by_url = {c.url: c for c in ranked}
        ranked = tuple(
            by_url.get(
                row.url,
                RankedCandidate(
                    url=row.url,
                    title=row.title,
                    score=row.score,
                    provider="navigation",
                    signals=("found_by_navigation_hop",),
                ),
            )
            for row in merged
        )

    return RetrievalReport(
        candidates=ranked[:top_k],
        queries_run=tuple(q.family for q in queries),
        provider=getattr(provider, "name", "unknown"),
        ontology_version=ontology_version(),
        rejection_counts=outcome.rejection_counts,
        failed_queries=tuple(failed),
        hop_entry_points=tuple(opened),
        hop_candidates=len(hopped),
    )
