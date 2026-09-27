"""A catalogue's footer is not a programme list (run 18, Vienna).

Vienna's catalogue links moodle, the wiki, webmail and the library — each the
root of another subdomain. Grouped by path alone they looked like five siblings
of one repeating list and each was read as a programme lead before search had
started. The T29 contract still reads a signal-less lead on the catalogue's own
site; only one that leaves it with no programme signal is recorded, not read.
"""

from __future__ import annotations

from app.adapters.discovery.catalog_walker import CatalogWalker, WalkerLink, _parent_directory

CATALOGUE = "https://studieren.univie.ac.at/en/degree-programmes/choice-of-degree"


def _walker() -> CatalogWalker:
    return CatalogWalker(
        fetcher=None,  # type: ignore[arg-type]
        domain="univie.ac.at",
        degree="bachelor",
        fields=["computer science"],
    )


def _link(url: str, label: str) -> WalkerLink:
    return WalkerLink(url=url, label=label, score=0, source="html")


def test_site_roots_on_different_hosts_are_not_siblings():
    assert _parent_directory("http://moodle.univie.ac.at/") == ""
    assert _parent_directory("http://wiki.univie.ac.at/") == ""
    assert _parent_directory("https://uni.edu/study/a") != _parent_directory(
        "https://x.edu/study/b"
    )


def test_footer_links_to_other_subdomains_are_recorded_not_read():
    footer = [
        _link("http://moodle.univie.ac.at/", "Moodle learning platform"),
        _link("http://wiki.univie.ac.at/", "University wiki pages"),
        _link("http://zid.univie.ac.at/en/webmail", "Webmail for staff and students"),
        _link("http://bibliothek.univie.ac.at/english", "University library services"),
        _link("https://blog.univie.ac.at/en", "University blog and stories"),
    ]
    outcomes: list[tuple[str, str]] = []
    scored = _walker()._score(footer, outcomes, "studieren.univie.ac.at")
    assert scored == []
    assert {o for _, o in outcomes} == {"walker_no_signal"}


def test_a_signal_less_lead_on_the_catalogues_own_site_is_still_read():
    """The T29 contract: read it, classify it, record what it was."""
    outcomes: list[tuple[str, str]] = []
    scored = _walker()._score(
        [
            _link(
                "https://studieren.univie.ac.at/en/study/closed-course",
                "A programme that has been discontinued",
            )
        ],
        outcomes,
        "studieren.univie.ac.at",
    )
    assert [link.url for link in scored] == [
        "https://studieren.univie.ac.at/en/study/closed-course"
    ]


def test_a_real_repeating_list_still_earns_its_bonus():
    rows = [
        _link(f"https://studieren.univie.ac.at/en/programmes/p{i}", f"Programme number {i} here")
        for i in range(5)
    ]
    outcomes: list[tuple[str, str]] = []
    scored = _walker()._score(rows, outcomes, "studieren.univie.ac.at")
    assert len(scored) == 5
    assert all(link.score > 0 for link in scored)


async def test_a_page_where_no_link_says_programme_is_not_walked():
    """Run 70: UBC's /programs HTML is navigation only; reading it cost 50 s."""
    walker = _walker()
    walker.domain = "ubc.ca"
    menu = "".join(
        f'<a href="https://you.ubc.ca/ubc-life/{slug}">{label}</a>'
        for slug, label in (
            ("getting-involved", "Getting involved"),
            ("campus-community", "Campus community"),
            ("arts-and-culture", "Arts and culture"),
        )
    )
    reads: list[str] = []

    async def read_catalogue(url):
        return f"<html><body><nav>{menu}</nav></body></html>", [], None

    async def read_lead(link, walk):
        reads.append(link.url)

    walker._read_catalogue = read_catalogue  # type: ignore[method-assign]
    walker._read_lead = read_lead  # type: ignore[method-assign]

    walk = await walker.walk_catalog("https://you.ubc.ca/programs")

    assert reads == []
    assert ("https://you.ubc.ca/programs", "js_no_program_list") in walk.outcomes
