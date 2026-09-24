"""A catalogue's strongest lead can be the list one level down (run 40, Vienna).

Vienna's walk read "Degree programmes" and "Choice of degree"; its strongest
lead, "Bachelor/diploma programmes", was read, classified as one programme
(its title reads like a programme's name) and dropped. Only that page names
Computer Science, so the walk now descends into one such list.
"""

from __future__ import annotations

import pytest

from app.adapters.discovery import catalog_walker as cw
from app.adapters.discovery.catalog_walker import CatalogWalk, CatalogWalker

ROOT = "https://studieren.univie.ac.at/en/degree-programmes"
CHOICE = "https://studieren.univie.ac.at/en/degree-programmes/choice-of-degree"
LIST = "https://studieren.univie.ac.at/en/degree-programmes/bachelordiploma-programmes"
DEEPER = "https://studieren.univie.ac.at/en/bachelordiploma-programmes/by-topic-programmes"
CS = "https://studieren.univie.ac.at/en/bachelordiploma-programmes/computer-science-bachelor"


def _walker(pages: dict[str, CatalogWalk], walked: list[str]) -> CatalogWalker:
    walker = CatalogWalker(
        fetcher=None,  # type: ignore[arg-type]
        domain="univie.ac.at",
        degree="bachelor",
        fields=["computer science"],
    )

    async def walk_catalog(catalogue_url: str) -> CatalogWalk:
        walked.append(catalogue_url)
        return pages.get(catalogue_url, CatalogWalk(catalogue_url=catalogue_url))

    walker.walk_catalog = walk_catalog  # type: ignore[method-assign]
    return walker


@pytest.mark.asyncio
async def test_the_walk_descends_into_a_list_its_catalogue_offered():
    walked: list[str] = []
    pages = {
        ROOT: CatalogWalk(
            catalogue_url=ROOT,
            outcomes=[(LIST, "reads_as_program_detail"), (CHOICE, "reads_as_program_catalog")],
        ),
        LIST: CatalogWalk(
            catalogue_url=LIST,
            confirmed=[CS],
            outcomes=[(DEEPER, "reads_as_program_catalog")],
        ),
    }
    walks = await _walker(pages, walked).walk([ROOT, CHOICE])

    assert walked == [ROOT, CHOICE, LIST]
    assert [url for walk in walks for url in walk.confirmed] == [CS]


@pytest.mark.asyncio
async def test_the_descent_is_bounded_and_skips_a_walk_that_confirmed():
    walked: list[str] = []
    pages = {
        ROOT: CatalogWalk(catalogue_url=ROOT, outcomes=[(LIST, "reads_as_program_catalog")]),
        LIST: CatalogWalk(catalogue_url=LIST, outcomes=[(DEEPER, "reads_as_program_catalog")]),
    }
    await _walker(pages, walked).walk([ROOT])
    assert walked == [ROOT, LIST], f"at most {cw.WALKER_MAX_DESCENTS} descent"

    walked.clear()
    pages[ROOT].confirmed.append(CS)
    await _walker(pages, walked).walk([ROOT])
    assert walked == [ROOT], "a walk that found the programme has nowhere to go"


@pytest.mark.asyncio
async def test_a_programme_page_that_is_not_a_list_is_not_walked():
    walked: list[str] = []
    other = "https://studieren.univie.ac.at/en/bachelordiploma-programmes/egyptology-bachelor"
    pages = {ROOT: CatalogWalk(catalogue_url=ROOT, outcomes=[(other, "reads_as_program_detail")])}
    await _walker(pages, walked).walk([ROOT])
    assert walked == [ROOT]
