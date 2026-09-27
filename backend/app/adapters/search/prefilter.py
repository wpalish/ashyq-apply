"""The cheap deterministic pass, before anything expensive looks at a URL.

A provider returns whatever ranked well for a string. Most of it is not a
programme page: it is the university's news feed, a vacancy, a PDF of a
newsletter, or a master's page when the applicant asked for a bachelor. Every
one of those costs a fetch, and a fetch is the expensive thing.

The rules are the phase guide's §5 list, in cheapest-first order, and almost
all of them already existed. ``live_discovery`` has canonicalisation, the
registrable-domain comparison that makes ``edu.kz`` work, the excluded-path
list and the degree-level reader; this module applies them to search results
rather than writing a second copy that would drift.

What is new here is the accounting. Every rejection is recorded with its
reason, because "search found nothing useful" and "search found forty news
articles" call for completely different fixes, and without the reasons they
look identical in a metric.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlparse

from app.adapters.discovery.live_discovery import (
    canonical_url,
    is_excluded_path,
    names_other_degree_level,
    same_institution,
)
from app.adapters.page_classifier import PageType, classify_url
from app.adapters.search.base import SearchResult
from app.domain.enums import DegreeLevel

#: Schemes worth fetching. Everything else — ``mailto:``, ``javascript:``,
#: ``data:``, ``ftp:`` — is either not a page or not one we retrieve.
ALLOWED_SCHEMES = frozenset({"http", "https"})


class Rejection:
    """Why a URL did not survive the prefilter. Values are stable for telemetry."""

    SCHEME = "unsupported_scheme"
    OTHER_INSTITUTION = "other_institution"
    NOT_A_PROGRAMME_PAGE = "not_a_programme_page"
    WRONG_DEGREE_LEVEL = "wrong_degree_level"
    DUPLICATE = "duplicate"


@dataclass(frozen=True, slots=True)
class PrefilteredCandidate:
    """A URL that survived, with what the cheap pass already knows about it."""

    url: str
    title: str
    snippet: str
    provider: str
    rank: int
    #: §9: a PDF can be a real programme handbook or credential table, so it is
    #: flagged rather than dropped. The flag lets a later stage decide.
    is_pdf: bool = False


@dataclass(frozen=True, slots=True)
class RejectedCandidate:
    url: str
    reason: str


@dataclass(frozen=True, slots=True)
class PrefilterOutcome:
    kept: tuple[PrefilteredCandidate, ...]
    rejected: tuple[RejectedCandidate, ...]

    @property
    def rejection_counts(self) -> dict[str, int]:
        """Reasons to counts — the shape telemetry wants."""
        counts: dict[str, int] = {}
        for item in self.rejected:
            counts[item.reason] = counts.get(item.reason, 0) + 1
        return counts


def _is_pdf(url: str) -> bool:
    return (urlparse(url).path or "").lower().endswith(".pdf")


def prefilter(
    results: Sequence[SearchResult],
    *,
    domain: str,
    degree: DegreeLevel,
    reject_irrelevant_kinds: bool = False,
) -> PrefilterOutcome:
    """Drop what is cheap to know is wrong, and say why for the rest.

    ``reject_irrelevant_kinds`` drops URLs the classifier already calls
    IRRELEVANT — publications, person and organisation profiles, datasets,
    theses — which the live probe repeatedly found outranking the programme
    page they were competing with (Aalto's top result was a publication;
    KAIST's was an organisation profile). It is **off by default on purpose**:
    §12 of the brief allows a discovery change only when the benchmark
    improves, this one cannot be measured without a live capture, and a
    rejection that has never been measured is exactly the kind of silent
    recall loss that rule exists to prevent. Turn it on for a measured run,
    compare, and only then change the default.

    Deduplication keeps the first occurrence, which is the best-ranked one
    because results arrive in rank order within a response and queries are run
    most-specific first. A duplicate is recorded rather than silently dropped:
    the same URL found by three query families is a signal that those families
    agree, and V2-16 will want it.
    """
    kept: list[PrefilteredCandidate] = []
    rejected: list[RejectedCandidate] = []
    seen: set[str] = set()

    for result in results:
        scheme = urlparse(result.url).scheme.lower()
        if scheme not in ALLOWED_SCHEMES:
            rejected.append(RejectedCandidate(result.url, Rejection.SCHEME))
            continue

        url = canonical_url(result.url)

        if not same_institution(url, domain):
            rejected.append(RejectedCandidate(url, Rejection.OTHER_INSTITUTION))
            continue
        if is_excluded_path(url):
            rejected.append(RejectedCandidate(url, Rejection.NOT_A_PROGRAMME_PAGE))
            continue
        if reject_irrelevant_kinds and classify_url(url) is PageType.IRRELEVANT:
            rejected.append(RejectedCandidate(url, Rejection.NOT_A_PROGRAMME_PAGE))
            continue
        if names_other_degree_level(url, str(degree)):
            # An MSc page is not a weak bachelor lead; it is the wrong page,
            # and no amount of subject-name overlap should outweigh that.
            rejected.append(RejectedCandidate(url, Rejection.WRONG_DEGREE_LEVEL))
            continue
        if url in seen:
            rejected.append(RejectedCandidate(url, Rejection.DUPLICATE))
            continue

        seen.add(url)
        kept.append(
            PrefilteredCandidate(
                url=url,
                title=result.title,
                snippet=result.snippet,
                provider=result.provider,
                rank=result.rank,
                is_pdf=_is_pdf(url),
            )
        )

    return PrefilterOutcome(kept=tuple(kept), rejected=tuple(rejected))
