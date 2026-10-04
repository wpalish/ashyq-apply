"""Experiment ER-10: leads naming no subject are capped per catalogue.

Groningen's "/education/bachelor" offered open days, brochures and campus
tours under the same path as its programmes; the walk read sixteen of them
before "/bachelors", and the run timed out (paired run 37237341528).
"""

from __future__ import annotations

import pytest

from app.adapters.discovery import catalog_walker as cw
from app.adapters.discovery.catalog_walker import CatalogWalk, CatalogWalker, WalkerLink

HUB = "https://www.rug.nl/education/bachelor"
JUNK = [
    "brochures",
    "bachelor-open-day",
    "campus-tour",
    "webklassen",
    "student-for-a-day",
    "online-university-tour",
]
PAGE = (
    "<html><body><main>"
    + "".join(
        f'<a href="/education/bachelor/{slug}">Bachelor {slug.replace("-", " ")} page</a>'
        for slug in JUNK
    )
    + '<a href="/bachelors">Bacheloropleidingen</a>'
    + '<a href="/bachelors/computing-science">Computing Science bachelor</a>'
    + "</main></body></html>"
)


def _walker(read: list[str]) -> CatalogWalker:
    walker = CatalogWalker(
        fetcher=None,  # type: ignore[arg-type]
        domain="www.rug.nl",
        degree="bachelor",
        fields=["computer science"],
    )

    async def read_catalogue(url: str):
        return PAGE, [], None

    async def read_lead(link: WalkerLink, walk: CatalogWalk) -> None:
        read.append(link.url)

    walker._read_catalogue = read_catalogue  # type: ignore[method-assign,assignment]
    walker._read_lead = read_lead  # type: ignore[method-assign]
    return walker


@pytest.mark.asyncio
async def test_off_by_default_reads_every_lead():
    assert cw.WALKER_SIGNAL_LESS_CAP is None
    read: list[str] = []
    await _walker(read).walk_catalog(HUB)
    assert len(read) == len(JUNK) + 2


@pytest.mark.asyncio
async def test_on_reads_the_subject_and_a_few_others(monkeypatch):
    monkeypatch.setattr(cw, "WALKER_SIGNAL_LESS_CAP", 3)
    read: list[str] = []
    walk = await _walker(read).walk_catalog(HUB)
    assert "https://www.rug.nl/bachelors/computing-science" in read
    assert "https://www.rug.nl/bachelors" in read, "the shortest list lead is kept"
    assert len(read) == 1 + 3
    assert sum(1 for _, o in walk.outcomes if o == "walker_no_subject") == len(JUNK) + 1 - 3
