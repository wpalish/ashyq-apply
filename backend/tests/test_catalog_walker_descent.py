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


def _walker(
    pages: dict[str, CatalogWalk], walked: list[str], budgets: list[int] | None = None
) -> CatalogWalker:
    budgets = [] if budgets is None else budgets
    walker = CatalogWalker(
        fetcher=None,  # type: ignore[arg-type]
        domain="univie.ac.at",
        degree="bachelor",
        fields=["computer science"],
    )

    async def walk_catalog(catalogue_url: str, top_n: int = cw.WALKER_TOP_N) -> CatalogWalk:
        walked.append(catalogue_url)
        budgets.append(top_n)
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
    budgets: list[int] = []
    walks = await _walker(pages, walked, budgets).walk([ROOT, CHOICE])

    # The list below goes before the next catalogue, and once it confirms the
    # applicant's programme the next catalogue is not read at all (run 64).
    assert walked == [ROOT, LIST], "the walk stops at the first confirmed programme"
    assert budgets == [cw.WALKER_TOP_N, cw.WALKER_DESCENT_TOP_N]
    assert [url for walk in walks for url in walk.confirmed] == [CS]


@pytest.mark.asyncio
async def test_the_descent_is_bounded_and_skips_a_walk_that_confirmed():
    walked: list[str] = []
    pages = {
        ROOT: CatalogWalk(catalogue_url=ROOT, outcomes=[(LIST, "reads_as_program_catalog")]),
        LIST: CatalogWalk(catalogue_url=LIST, outcomes=[(DEEPER, "reads_as_program_catalog")]),
    }
    deepest = "https://studieren.univie.ac.at/en/bachelordiploma-programmes/a-z-programmes"
    pages[DEEPER] = CatalogWalk(
        catalogue_url=DEEPER, outcomes=[(deepest, "reads_as_program_catalog")]
    )
    await _walker(pages, walked).walk([ROOT])
    assert walked == [ROOT, LIST, DEEPER], f"at most {cw.WALKER_MAX_DESCENTS} levels"

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


@pytest.mark.asyncio
async def test_a_language_copy_is_not_a_new_list_and_a_child_index_is():
    """Run 45, Groningen: the second descent went to ``?lang=nl`` of the same page."""
    bachelors = "https://www.rug.nl/bachelors"
    alphabet = "https://www.rug.nl/bachelors/alphabet"
    walked: list[str] = []
    pages = {
        ROOT: CatalogWalk(catalogue_url=ROOT, outcomes=[(bachelors, "reads_as_program_catalog")]),
        bachelors: CatalogWalk(
            catalogue_url=bachelors,
            outcomes=[
                (bachelors + "?lang=nl", "reads_as_program_catalog"),
                (alphabet, "reads_as_program_detail"),
            ],
        ),
    }
    await _walker(pages, walked).walk([ROOT])
    assert walked == [ROOT, bachelors, alphabet]


def test_a_site_home_page_reads_only_leads_that_say_programme():
    """Run 66: UBC's walk of you.ubc.ca read its menu for 40 s."""
    from app.adapters.discovery.catalog_walker import WalkerLink

    walker = _walker({}, [])
    walker.domain = "ubc.ca"
    walker.fields = ["computer science"]
    menu = WalkerLink(
        url="https://you.ubc.ca/indigenous", label="Indigenous", score=0, source="html"
    )
    lead = WalkerLink(
        url="https://you.ubc.ca/programs/computer-science",
        label="Computer Science",
        score=0,
        source="html",
    )
    outcomes: list[tuple[str, str]] = []

    siblings = [
        WalkerLink(url=f"https://you.ubc.ca/{slug}", label=slug, score=0, source="html")
        for slug in ("canadian", "contact-us", "tours-events", "international")
    ]

    kept = walker._score([menu, *siblings, lead], outcomes, "you.ubc.ca", site_root=True)

    # Five menu links under one root would count as a repeating list on a
    # catalogue; on a home page they are still the menu (run 67).
    assert [link.url for link in kept] == [lead.url]
    assert (menu.url, "walker_no_signal") in outcomes


def test_top_level_menu_links_on_a_catalogue_are_not_a_repeating_list():
    """Run 68: UBC's /programs HTML is only the site menu, and each item scored 2."""
    from app.adapters.discovery.catalog_walker import WalkerLink

    walker = _walker({}, [])
    walker.domain = "ubc.ca"
    menu = [
        WalkerLink(url=f"https://you.ubc.ca/{slug}", label=label, score=0, source="html")
        for slug, label in (
            ("canadian", "Canadian students"),
            ("international", "International students"),
            ("tours-events", "Tours and events"),
            ("contact-us", "Contact us"),
            ("indigenous", "Indigenous students"),
        )
    ]
    outcomes: list[tuple[str, str]] = []

    kept = walker._score(menu, outcomes, "you.ubc.ca")

    # Not a repeating list, and signal-less items one level below the root
    # are the menu: none of them is read.
    assert kept == []
    assert all(outcome == "walker_no_signal" for _url, outcome in outcomes)
