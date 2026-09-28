"""Campus as an unresolved identity dimension (experiment ER-02, owner 2026-09-28).

A university with several campuses that are separate application routes can
publish the same programme under each. When the applicant has not named a
campus, a page that belongs to one campus answers a question the applicant
has not asked: its requirements, fees and deadlines are that campus's. Those
claims are withheld from the programme and the applicant is asked instead.

Which hosts belong to which campus is verified registry data, never inferred
from a hostname: a department or faculty subdomain is not a campus.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TypeVar
from urllib.parse import urlsplit

T = TypeVar("T")


def campus_of(url: str, campuses: Mapping[str, Sequence[str]]) -> str | None:
    """The registered campus whose hosts serve this URL, if any."""
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    for name, hosts in campuses.items():
        for h in hosts:
            h = h.lower().removeprefix("www.")
            if host == h or host.endswith("." + h):
                return name
    return None


def withhold_other_campuses(
    claims: Iterable[T],
    campuses: Mapping[str, Sequence[str]],
    *,
    requested: str | None = None,
    url_of=lambda c: c.source_url,
) -> tuple[list[T], list[str]]:
    """Keep claims that answer the request; name the campuses withheld.

    Unnamed request: every campus-specific page is withheld. Named request:
    only the other campuses' pages are. Pages on no registered campus host
    (the central admissions site, a department) are always kept.
    """
    kept: list[T] = []
    withheld: list[str] = []
    for claim in claims:
        campus = campus_of(url_of(claim), campuses)
        if campus is None or (requested is not None and campus == requested):
            kept.append(claim)
        elif campus not in withheld:
            withheld.append(campus)
    return kept, withheld
