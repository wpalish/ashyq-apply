"""V2-16b — one hop through a site's own navigation.

Every fixture is synthetic, but each one encodes a defect found on a real
page: the hand-written HTML passed first time and KAIST's real navigation did
not, which is the only reason these particular tests exist.
"""

from __future__ import annotations

import pytest

from app.adapters.search.fusion import Generator
from app.adapters.search.intent import DiscoveryIntent
from app.adapters.search.navigation import (
    DEFAULT_HOP_LIMIT,
    MAX_LINKS_PER_PAGE,
    links_from,
    navigation_candidates,
)
from app.domain.enums import DegreeLevel

BASE = "https://cs.example.edu/"


def an_intent(**kw) -> DiscoveryIntent:
    return DiscoveryIntent(
        **{
            "institution": "Example University",
            "domain": "cs.example.edu",
            "degree": DegreeLevel.BACHELOR,
            "field": "computer science",
            **kw,
        }
    )


def hop(html: str, **kw):
    return navigation_candidates(html, BASE, an_intent(), **kw)


class TestItReadsLinksAsAParserWould:
    def test_link_text_comes_from_the_element_not_from_attributes(self):
        """KAIST's menu puts its label in navi="..." and leaves the anchor empty.

        A regex over anchors read that attribute — and the *next* anchor's —
        as if it were link text, and ranked four staff pages above the
        programme. A parser reports an empty label as empty.
        """
        html = '<a href="/content?menu=188" navi="Education">  </a>'

        assert links_from(html, BASE)[0].text == ""

    def test_nested_markup_inside_a_link_is_flattened(self):
        html = '<a href="/education/undergraduate"><span>Computer</span> <b>Science</b></a>'

        assert links_from(html, BASE)[0].text == "Computer Science"

    def test_unparseable_markup_yields_no_links_rather_than_an_error(self):
        """One broken page must not end a discovery run."""
        assert links_from("", BASE) == ()

    def test_a_fragment_only_link_is_not_a_page(self):
        assert links_from('<a href="#main">Skip</a>', BASE) == ()

    def test_the_number_of_links_read_is_bounded(self):
        html = "".join(
            f'<a href="/p{i}">Computer Science</a>' for i in range(MAX_LINKS_PER_PAGE + 50)
        )

        assert len(links_from(html, BASE)) == MAX_LINKS_PER_PAGE


class TestWhatAHopRefusesToFollow:
    def test_another_institution_is_never_followed(self):
        html = '<a href="https://elsewhere.test/computer-science">Computer Science</a>'

        assert links_from(html, BASE) == ()

    def test_a_staff_listing_is_not_a_programme(self):
        """Four of these outranked the programme on KAIST before the rule existed."""
        html = (
            '<a href="/people/facultyInteractiveComputing">Interactive Computing</a>'
            '<a href="/faculty/members">Faculty</a>'
        )

        assert links_from(html, BASE) == ()

    def test_news_and_events_are_dropped_by_the_shared_rule(self):
        html = '<a href="/news/2027">Computer Science news</a>'

        assert links_from(html, BASE) == ()

    def test_one_page_linked_under_two_schemes_is_one_candidate(self):
        """A site that links itself both ways would spend two slots on one page."""
        html = (
            '<a href="http://cs.example.edu/education/undergraduate">Curriculum</a>'
            '<a href="https://cs.example.edu/education/undergraduate">Curriculum</a>'
        )

        links = links_from(html, BASE)

        assert len(links) == 1
        assert links[0].url.startswith("https://")

    def test_navigation_chrome_is_not_offered_to_fusion(self):
        html = '<a href="/contact-us">Contact</a><a href="/about">About</a>'

        assert hop(html) == ()


class TestRankingTheHop:
    def test_the_field_in_the_link_text_beats_an_opaque_url(self):
        """The whole point: the label carries the meaning the URL lost."""
        html = (
            '<a href="/content?menu=188">Computer Science programme</a>'
            '<a href="/x/y">Something else entirely in computing</a>'
        )

        assert hop(html)[0].url.endswith("menu=188")

    def test_a_term_must_be_a_word_in_the_url_not_a_fragment(self):
        """``facultyInteractiveComputing`` contains ``computing`` and is not it."""
        html = (
            '<a href="/labs/interactiveComputingGroup">Group</a>'
            '<a href="/education/computing">Studies</a>'
        )

        urls = [c.url for c in hop(html)]

        assert any(u.endswith("/education/computing") for u in urls)
        assert not any("interactiveComputing" in u for u in urls)

    def test_the_wrong_degree_level_is_pushed_out(self):
        html = (
            '<a href="/education/graduate">Computer Science</a>'
            '<a href="/education/undergraduate">Computer Science</a>'
        )

        urls = [c.url for c in hop(html)]

        assert urls == ["https://cs.example.edu/education/undergraduate"]

    def test_a_neighbouring_field_ranks_below_the_requested_one(self):
        html = (
            '<a href="/programmes/data-science">Data Science</a>'
            '<a href="/programmes/computer-science">Computer Science</a>'
        )

        assert hop(html)[0].url.endswith("computer-science")

    def test_a_study_section_is_recognised_in_the_sites_own_language(self):
        """On a Korean site the meaning survives in Korean, or not at all."""
        html = '<a href="/content?menu=188">교육</a>'

        assert len(hop(html)) == 1

    def test_a_loose_substring_in_a_language_without_word_breaks_is_not_used(self):
        """``학부`` alone also matched a development fund and the dean's greeting."""
        html = '<a href="/content?menu=132">학부발전기금</a>'

        assert hop(html) == ()


class TestItIsFusionInput:
    def test_candidates_are_attributed_to_the_catalogue_walker(self):
        html = '<a href="/programmes/computer-science">Computer Science</a>'

        candidate = hop(html)[0]

        assert candidate.generator is Generator.CATALOGUE_WALKER
        assert candidate.rank == 1
        assert candidate.title == "Computer Science"

    def test_every_link_remembers_the_page_it_was_found_on(self):
        html = '<a href="/programmes/computer-science">Computer Science</a>'

        assert links_from(html, BASE)[0].parent_url == BASE

    def test_the_hop_is_bounded(self):
        html = "".join(
            f'<a href="/programmes/computer-science-{i}">Computer Science</a>' for i in range(40)
        )

        assert len(hop(html)) == DEFAULT_HOP_LIMIT
        assert len(hop(html, limit=3)) == 3

    def test_a_limit_below_one_is_refused(self):
        with pytest.raises(ValueError, match="limit"):
            hop("<a href='/x'>Computer Science</a>", limit=0)

    def test_the_order_is_stable(self):
        html = (
            '<a href="/b/computer-science">Computer Science</a>'
            '<a href="/a/computer-science">Computer Science</a>'
        )

        assert [c.url for c in hop(html)] == [c.url for c in hop(html)]
