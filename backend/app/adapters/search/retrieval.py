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
from urllib.parse import urlsplit

from app.adapters.discovery.live_discovery import looks_like_catalogue
from app.adapters.search.base import SearchProvider, SearchResult, SearchUnavailable
from app.adapters.search.fusion import SourcedCandidate, fuse
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

    def _replace_signals(self, signals: tuple[str, ...]) -> RankedCandidate:
        """A copy carrying different signals. Frozen, so this is the only way."""
        return RankedCandidate(
            url=self.url,
            title=self.title,
            score=self.score,
            provider=self.provider,
            signals=signals,
            is_pdf=self.is_pdf,
        )


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


#: Host labels that mean "a research output lives here", not "a programme".
#: A lab, a group and a publication repository each have navigation, and none
#: of it leads to an admissions page.
_RESEARCH_HOST = re.compile(
    r"^(pure|research|lab|scholar|repository|eprints|dspace)$|lab$|^.{0,6}(lab|rg)$"
)

#: Host labels that mean "applications happen here".
_ADMISSIONS_HOST = frozenset({"admission", "admissions", "apply", "study", "studies", "future"})


def _host_priority(host: str, intent: DiscoveryIntent) -> int:
    """How likely this host's front page is to lead to a programme.

    Opening the top three hosts by search rank sent the hop to KAIST's
    publication repository, a graphics lab and the sociology department, while
    ``cs.kaist.ac.kr`` — whose navigation demonstrably holds the answer — sat
    sixth and was never opened. Rank says which host search liked; it does not
    say which host runs degrees.
    """
    label = host.lower().removeprefix("www.").split(".", 1)[0]
    if _RESEARCH_HOST.search(label):
        return -1
    if any(
        _names_host(candidate.term, label)
        for candidate in retrieval_candidates(intent.field)
        if candidate.is_match
    ):
        return 3
    if label in _ADMISSIONS_HOST:
        return 2
    return 0


def _names_host(term: str, label: str) -> bool:
    """``cs`` names computer science; ``sociology`` does not."""
    words = {w for w in re.split(r"[^a-z]+", term.lower()) if w}
    return label in words or (
        len(words) > 1 and label == "".join(w[0] for w in term.lower().split())
    )


def _entry_points(
    ranked: Sequence[RankedCandidate], limit: int, intent: DiscoveryIntent
) -> tuple[str, ...]:
    """Roots of the hosts most likely to run the requested programme.

    Search rank breaks ties, so a host search liked wins among equals.
    """
    scored: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for position, candidate in enumerate(ranked):
        parts = urlsplit(candidate.url)
        host = parts.hostname or ""
        if not host or host in seen:
            continue
        seen.add(host)
        priority = _host_priority(host, intent)
        if priority < 0:
            continue
        scored.append((-priority, position, f"{parts.scheme}://{host}/"))
    scored.sort()
    return tuple(root for _p, _r, root in scored[:limit])


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

    # Truncate the ranked search list *before* the hop appends to it. With
    # both truncated together, search fills every slot and the appended
    # coverage candidates are cut off again — which is why three consecutive
    # measured runs showed the hop contributing exactly nothing. "Never
    # displace" and "must add" cannot both hold inside one fixed budget, so
    # coverage is additive: the hop extends the list rather than competing
    # for it.
    ranked = ranked[:top_k]

    opened: list[str] = []
    hopped: list[SourcedCandidate] = []
    if fetch is not None and hop_entry_points > 0:
        # Search finds entry points reliably; a page with no words in its URL
        # is found from one, not by a better query. See navigation.py.
        #
        # **Open host roots, not the top results.** Choosing entry points by
        # search rank opened KAIST's `pure.kaist.ac.kr` research profiles and
        # never `cs.kaist.ac.kr/`, whose navigation demonstrably holds the
        # answer. A site's navigation lives at its root, so the root of each
        # distinct host among the candidates is the door worth trying — in
        # the order search ranked that host, which keeps the budget honest.
        for candidate in _entry_points(ranked, hop_entry_points, intent):
            try:
                html = await fetch(candidate)
            except Exception:
                html = ""
            if not html:
                continue
            opened.append(candidate)
            hopped.extend(navigation_candidates(html, candidate, intent))

    if hopped:
        # **Coverage, not reordering.** Fusing the hop as an equal generator
        # was measured and cost a whole case: thirty navigation candidates,
        # each restarting at rank 1 on its own page, outscored search results
        # ranked tenth or twentieth and pushed six correct pages down
        # (SEARCH_PROBE.md). A navigation list is layout, not relevance.
        #
        # So the hop may add pages search never found, and may never displace
        # one search placed. Agreement is still kept: a page both generators
        # found keeps its search position and gains the hop's attribution.
        placed = {c.url for c in ranked}
        agreed = {c.url for c in hopped if c.url in placed}
        appended: list[RankedCandidate] = []
        for row in fuse([c for c in hopped if c.url not in placed], top_k=top_k):
            appended.append(
                RankedCandidate(
                    url=row.url,
                    title=row.title,
                    # Zero, deliberately: these are ordered after every scored
                    # candidate and their score is not comparable with BM25's.
                    score=0.0,
                    provider="navigation",
                    signals=("found_by_navigation_hop",),
                )
            )
        ranked = tuple(
            c._replace_signals((*c.signals, "also_found_by_hop")) if c.url in agreed else c
            for c in ranked
        ) + tuple(appended)

    return RetrievalReport(
        candidates=ranked,
        queries_run=tuple(q.family for q in queries),
        provider=getattr(provider, "name", "unknown"),
        ontology_version=ontology_version(),
        rejection_counts=outcome.rejection_counts,
        failed_queries=tuple(failed),
        hop_entry_points=tuple(opened),
        hop_candidates=len(hopped),
    )
