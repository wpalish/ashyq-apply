"""ER-02: campus is an unresolved identity dimension (owner decision 2026-09-28)."""

from types import SimpleNamespace

from app.adapters.discovery.live_discovery import registry_campuses
from app.domain.campus import campus_of, withhold_other_campuses

CAMPUSES = {
    "Mississauga": ["utm.utoronto.ca"],
    "Scarborough": ["utsc.utoronto.ca", "utsc.calendar.utoronto.ca"],
}


def claim(url):
    return SimpleNamespace(source_url=url)


def test_a_campus_host_and_its_subdomains_belong_to_that_campus():
    assert campus_of("https://www.utm.utoronto.ca/x", CAMPUSES) == "Mississauga"
    assert campus_of("https://utsc.calendar.utoronto.ca/", CAMPUSES) == "Scarborough"


def test_a_department_or_central_host_is_not_a_campus():
    assert campus_of("https://web.cs.utoronto.ca/bcs", CAMPUSES) is None
    assert campus_of("https://future.utoronto.ca/apply", CAMPUSES) is None


def test_an_unnamed_campus_withholds_every_campus_page():
    kept, withheld = withhold_other_campuses(
        [claim("https://future.utoronto.ca/a"), claim("https://utsc.utoronto.ca/b")], CAMPUSES
    )
    assert [c.source_url for c in kept] == ["https://future.utoronto.ca/a"]
    assert withheld == ["Scarborough"]


def test_a_named_campus_keeps_its_own_pages():
    kept, withheld = withhold_other_campuses(
        [claim("https://utsc.utoronto.ca/b"), claim("https://utm.utoronto.ca/c")],
        CAMPUSES,
        requested="Scarborough",
    )
    assert [c.source_url for c in kept] == ["https://utsc.utoronto.ca/b"]
    assert withheld == ["Mississauga"]


def test_the_registry_names_toronto_s_campuses_and_no_one_else_s():
    toronto = registry_campuses("future.utoronto.ca")
    assert set(toronto) == {
        "University of Toronto Mississauga",
        "University of Toronto Scarborough",
    }
    assert registry_campuses("rug.nl") == {}
