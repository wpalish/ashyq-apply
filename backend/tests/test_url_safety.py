"""A malformed link on a page must not end the research.

`urlparse` accepts a string and defers the parts that can fail. `parts.port`
and `parts.hostname` are properties that raise `ValueError` when they are read,
and they were read outside the `try` that was meant to guard them:

    canonical_url("https://example.edu:bad/programmes/cs")
    ValueError: Port could not be cast to integer value as 'bad'

    canonical_url("https://example.edu:99999/programmes/cs")
    ValueError: Port out of range 0-65535

    registrable_domain("https://[bad::ipv6/programmes")
    ValueError: Invalid IPv6 URL

A university page only has to contain one `<a href>` like that — a typo, a
templating accident, a deliberately hostile string — and the exception travels
out of link harvesting, out of the walk, out of `discover`, and takes every
remaining institution in the run with it. That exact shape of failure has
already happened once here, from a page lxml could not parse.

The rule these tests hold: an unusable URL is a URL with nothing behind it. It
is not fetched, it is not counted, it does not stop the page it was found on,
and it never raises.
"""
from __future__ import annotations

import pytest

from app.adapters.discovery.url_signals import (
    canonical_url,
    categorise_url,
    registrable_domain,
    same_institution,
    score_url,
    url_problem,
)

MALFORMED = [
    pytest.param("https://example.edu:bad/programmes/cs", id="non-numeric-port"),
    pytest.param("https://example.edu:99999/programmes/cs", id="port-out-of-range"),
    pytest.param("https://example.edu:-1/programmes", id="negative-port"),
    pytest.param("https://[bad::ipv6/programmes", id="unclosed-ipv6-bracket"),
    pytest.param("https://[::1:80]:x/y", id="ipv6-and-bad-port"),
    pytest.param("https:///programmes", id="empty-host"),
    pytest.param("https://exa\x00mple.edu/x", id="nul-in-host"),
    pytest.param("https://exam\nple.edu/x", id="newline-in-host"),
    pytest.param("https://exam\tple.edu/x", id="tab-in-host"),
    pytest.param("https://example.edu/" + "a" * 9000, id="oversized"),
    pytest.param("", id="empty"),
    pytest.param("   ", id="whitespace"),
    pytest.param("javascript:alert(1)", id="javascript-scheme"),
    pytest.param("data:text/html,<h1>x", id="data-scheme"),
    pytest.param("file:///etc/passwd", id="file-scheme"),
]

WELL_FORMED = [
    "https://www.rug.nl/bachelors/computing-science",
    "http://example.edu:8080/programmes",
    "https://example.edu:443/programmes",
    "https://xn--bcher-kva.example/programmes",
    "https://user:pw@example.edu/programmes",
    "https://[2001:db8::1]/programmes",
]


class TestNothingRaises:
    """Every entry point takes a string off a web page. None may raise."""

    @pytest.mark.parametrize("url", MALFORMED)
    @pytest.mark.parametrize(
        "fn",
        [canonical_url, registrable_domain, categorise_url, url_problem],
        ids=lambda f: f.__name__,
    )
    def test_a_malformed_url_returns_rather_than_raises(self, fn, url):
        fn(url)

    @pytest.mark.parametrize("url", MALFORMED)
    def test_same_institution_returns_rather_than_raises(self, url):
        assert same_institution(url, "example.edu") in (True, False)

    @pytest.mark.parametrize("url", MALFORMED)
    def test_scoring_returns_rather_than_raises(self, url):
        from app.adapters.discovery.url_signals import PageCategory

        score_url(url, PageCategory.PROGRAM_PAGE)


class TestUnusableUrlsAreRefused:
    @pytest.mark.parametrize("url", MALFORMED)
    def test_they_are_named_as_a_problem(self, url):
        assert url_problem(url), f"{url!r} should be reported as unusable"

    @pytest.mark.parametrize("url", MALFORMED)
    def test_they_score_nothing_and_belong_to_no_category(self, url):
        assert categorise_url(url) == (None, 0)

    @pytest.mark.parametrize("url", MALFORMED)
    def test_they_are_never_the_same_institution(self, url):
        """`same_institution` is what keeps a fetch on the university's own
        domain. A URL we cannot parse has no domain to compare."""
        assert same_institution(url, "example.edu") is False

    def test_the_reason_is_bounded_and_carries_no_url(self):
        """Traces are read by people and stored; a 9,000-character URL from a
        page is neither useful nor safe to repeat in full."""
        problem = url_problem("https://example.edu/" + "a" * 9000)
        assert problem
        assert len(problem) < 200
        assert "aaaaaaaaaa" not in problem


class TestWellFormedUrlsAreUntouched:
    @pytest.mark.parametrize("url", WELL_FORMED)
    def test_they_are_not_reported_as_a_problem(self, url):
        assert url_problem(url) is None, url

    @pytest.mark.parametrize("url", WELL_FORMED)
    def test_they_canonicalise_to_something_usable(self, url):
        assert canonical_url(url).startswith(("http://", "https://")), url

    def test_a_default_port_is_dropped_and_a_real_one_kept(self):
        assert canonical_url("https://example.edu:443/x") == "https://example.edu/x"
        assert canonical_url("http://example.edu:8080/x") == "http://example.edu:8080/x"

    def test_credentials_are_stripped_rather_than_carried_into_a_fetch(self):
        assert "pw" not in canonical_url("https://user:pw@example.edu/x")

    def test_an_internationalised_host_survives(self):
        assert "xn--bcher-kva" in canonical_url("https://xn--bcher-kva.example/programmes")


class TestOneBadLinkDoesNotLoseTheGoodOnes:
    def test_harvesting_keeps_every_valid_link_on_a_page_with_a_broken_one(self):
        from app.adapters.discovery.live_discovery import _harvest_links

        html = (
            "<html><body>"
            "<a href='/bachelors/computing-science'>Computing Science</a>"
            "<a href='https://example.edu:bad/broken'>Broken port</a>"
            "<a href='https://[bad::ipv6/also-broken'>Broken host</a>"
            "<a href='/bachelors/mathematics'>Mathematics</a>"
            "</body></html>"
        )
        links = _harvest_links(html, "https://example.edu/", "example.edu")
        urls = [u for u, _ in links]
        assert any("computing-science" in u for u in urls)
        assert any("mathematics" in u for u in urls)
        assert not any("broken" in u for u in urls)
