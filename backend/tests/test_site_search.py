"""V2-15 — finding the search a university already offers its visitors.

Every fixture here is synthetic. None is a captured page from a real
university: a committed fixture that pretends to be a real site is evidence
nobody can check, and the phase guide forbids it.

Most of these tests are about restraint. The module reads what is in front of
it and stops there — it does not probe, does not follow a lead off the
institution's domain, and does not read a key even when one is lying in the
page.
"""

from __future__ import annotations

import random
import re
import time
from datetime import UTC, datetime

import pytest

from app.adapters.search import site_search
from app.adapters.search.site_search import (
    MAX_PAGES,
    MAX_RESPONSE_BYTES,
    NEEDS_CREDENTIALS,
    Provenance,
    SiteSearchKind,
    SiteSearchSurface,
    detect_surfaces,
    search_url,
)

NOW = datetime(2026, 9, 21, tzinfo=UTC)
BASE = "https://nu.edu.kz/"


def detect(html: str = "", **kw):
    return detect_surfaces(html, BASE, now=NOW, **kw)


def a_surface(**kw) -> SiteSearchSurface:
    return SiteSearchSurface(
        **{
            "kind": SiteSearchKind.JSON_ENDPOINT,
            "endpoint": "https://nu.edu.kz/api/search",
            "query_param": "q",
            "provenance": Provenance.MARKUP,
            "detected_at": NOW,
            **kw,
        }
    )


class TestPassiveEvidenceComesFirst:
    def test_a_surface_the_site_itself_called_outranks_one_read_from_markup(self):
        """§7: prefer passive discovery from network logs before inference."""
        surfaces = detect(
            '<form action="/search"><input name="q"></form>',
            network_urls=("https://nu.edu.kz/wp-json/wp/v2/programme?search=cs",),
        )

        assert surfaces[0].provenance is Provenance.NETWORK_LOG
        assert surfaces[0].kind is SiteSearchKind.WORDPRESS_REST

    def test_the_observed_query_parameter_beats_the_default(self):
        surfaces = detect(network_urls=("https://nu.edu.kz/api/search?keywords=cs&lang=en",))

        assert surfaces[0].query_param == "keywords"

    def test_nothing_is_probed(self):
        """Detection reads a page. Guessing endpoints at a university is scanning."""
        assert detect("<html><body>no search here</body></html>") == ()

    def test_every_surface_records_how_it_was_found(self):
        surfaces = detect(
            '<form action="/search"><input name="q"></form>',
            network_urls=("https://nu.edu.kz/api/programmes/search?q=x",),
        )

        assert all(s.evidence for s in surfaces)
        assert all(s.detected_at == NOW for s in surfaces)


class TestOnlyTheSitesOwnPublicEndpoints:
    def test_an_endpoint_on_another_domain_is_discarded(self):
        surfaces = detect(network_urls=("https://evil.test/api/search?q=x",))

        assert surfaces == ()

    def test_a_lookalike_domain_is_another_domain(self):
        surfaces = detect(network_urls=("https://nu.edu.kz.evil.test/api/search?q=x",))

        assert surfaces == ()

    def test_a_subdomain_of_the_institution_is_its_own(self):
        """``edu.kz`` is a multipart suffix; the shared helper already knows."""
        surfaces = detect(network_urls=("https://admissions.nu.edu.kz/api/search?q=x",))

        assert len(surfaces) == 1

    @pytest.mark.parametrize(
        "url",
        [
            "https://nu.edu.kz/wp-admin/admin-ajax.php?action=search",
            "https://nu.edu.kz/admin/api/search?q=x",
            "https://nu.edu.kz/login/api/search?q=x",
            "https://nu.edu.kz/dashboard/api/search?q=x",
        ],
    )
    def test_an_administrative_or_authenticated_surface_is_never_a_candidate(self, url):
        assert detect(network_urls=(url,)) == ()

    def test_an_admin_form_is_not_a_search_form(self):
        html = '<form action="/wp-admin/admin.php"><input name="q"></form>'

        assert detect(html) == ()


class TestNoCredentialIsEverRead:
    def test_a_key_bearing_surface_is_flagged_and_its_key_is_not_stored(self):
        """Algolia publishes a search-only key. It is still a key in a repo."""
        html = '<script>var c={appId:"ABC123",apiKey:"secret-search-key"};</script>'
        surfaces = detect(html, network_urls=("https://nu.edu.kz/1/indexes/programmes?query=cs",))

        assert surfaces[0].kind is SiteSearchKind.ALGOLIA
        assert surfaces[0].requires_credentials
        assert not surfaces[0].usable_without_owner_review
        assert "secret-search-key" not in repr(surfaces[0])

    def test_the_key_bearing_kinds_are_named_explicitly(self):
        assert set(NEEDS_CREDENTIALS) == {SiteSearchKind.ALGOLIA, SiteSearchKind.ELASTIC}

    def test_an_ordinary_surface_needs_no_owner_review(self):
        assert a_surface().usable_without_owner_review


class TestTheFamiliesFromTheGuide:
    @pytest.mark.parametrize(
        ("url", "kind"),
        [
            ("https://nu.edu.kz/wp-json/wp/v2/programme?search=cs", SiteSearchKind.WORDPRESS_REST),
            ("https://nu.edu.kz/jsonapi/node/programme", SiteSearchKind.DRUPAL_VIEWS),
            ("https://nu.edu.kz/1/indexes/programmes?query=cs", SiteSearchKind.ALGOLIA),
            ("https://nu.edu.kz/programmes/_search?q=cs", SiteSearchKind.ELASTIC),
            ("https://nu.edu.kz/solr/catalogue/select?q=cs&wt=json", SiteSearchKind.SOLR),
            ("https://nu.edu.kz/graphql", SiteSearchKind.GRAPHQL),
            ("https://nu.edu.kz/data/programmes.json", SiteSearchKind.CUSTOM_CATALOGUE),
            ("https://nu.edu.kz/api/v2/search?q=cs", SiteSearchKind.JSON_ENDPOINT),
        ],
    )
    def test_each_family_is_recognised(self, url, kind):
        assert detect(network_urls=(url,))[0].kind is kind

    def test_a_plain_html_search_form_is_recognised(self):
        html = '<form action="/search" method="get"><input name="q" type="text"></form>'

        surface = detect(html)[0]

        assert surface.kind is SiteSearchKind.HTML_FORM
        assert surface.endpoint == "https://nu.edu.kz/search"
        assert surface.query_param == "q"

    def test_a_newsletter_form_is_not_a_search_form(self):
        html = '<form action="/subscribe"><input name="email"></form>'

        assert detect(html) == ()

    def test_a_form_that_posts_to_a_json_endpoint_keeps_the_endpoints_kind(self):
        html = '<form action="/api/programmes/search"><input name="query"></form>'

        surface = detect(html)[0]

        assert surface.kind is SiteSearchKind.JSON_ENDPOINT
        assert surface.query_param == "query"

    def test_one_endpoint_is_reported_once_with_its_best_provenance(self):
        url = "https://nu.edu.kz/api/programmes/search?q=x"
        html = f'<script>var u="{url}";</script>'

        surfaces = detect(html, network_urls=(url,))

        assert len(surfaces) == 1
        assert surfaces[0].provenance is Provenance.NETWORK_LOG


class TestTheRequestIsBounded:
    def test_a_query_is_placed_in_the_surfaces_own_parameter(self):
        url = search_url(a_surface(query_param="keywords"), "computer science")

        assert "keywords=computer+science" in url

    def test_existing_filters_on_the_endpoint_survive(self):
        """A catalogue endpoint often carries the filter that makes it one."""
        surface = a_surface(endpoint="https://nu.edu.kz/api/search?type=programme")

        url = search_url(surface, "computer science")

        assert "type=programme" in url
        assert "q=computer+science" in url

    def test_an_existing_value_for_the_query_parameter_is_replaced_not_repeated(self):
        surface = a_surface(endpoint="https://nu.edu.kz/api/search?q=old")

        url = search_url(surface, "new")

        assert url.count("q=") == 1
        assert "old" not in url

    def test_pagination_is_bounded(self):
        """§7: bound pagination. An off-by-one next link is an infinite crawl."""
        assert "page=2" in search_url(a_surface(), "cs", page=2)
        with pytest.raises(ValueError, match="bounds pagination"):
            search_url(a_surface(), "cs", page=MAX_PAGES + 1)
        with pytest.raises(ValueError, match="bounds pagination"):
            search_url(a_surface(), "cs", page=0)

    def test_the_first_page_carries_no_page_parameter(self):
        assert "page=" not in search_url(a_surface(), "cs")

    def test_an_empty_query_is_refused(self):
        with pytest.raises(ValueError, match="needs a query"):
            search_url(a_surface(), "   ")

    def test_the_response_cap_is_a_named_constant(self):
        """A bound nobody can find is a bound nobody keeps."""
        assert MAX_RESPONSE_BYTES == 2 * 1024 * 1024
        assert MAX_PAGES == 5


class TestWhatIsQuietlyIgnored:
    def test_a_form_without_an_action_is_skipped(self):
        """A JavaScript-driven form tells us no endpoint, and guessing one is probing."""
        assert detect('<form method="get"><input name="q"></form>') == ()

    def test_an_ordinary_page_request_in_the_log_is_not_a_search_surface(self):
        """A network log is mostly images, fonts and pages. Only endpoints count."""
        surfaces = detect(
            network_urls=(
                "https://nu.edu.kz/about-us",
                "https://nu.edu.kz/static/logo.png",
                "https://nu.edu.kz/api/programmes/search?q=cs",
            )
        )

        assert [s.endpoint for s in surfaces] == ["https://nu.edu.kz/api/programmes/search?q=cs"]


# ------------------------------------------------- linear tag scans (SEC-3, SR2-09)

#: The patterns before SEC-3, kept as the oracle: quadratic on hostile markup,
#: but what they matched is what the linear scans must match.
_OLD_FORM = re.compile(r"<form\b[^>]*>", re.IGNORECASE)
_OLD_ATTR = re.compile(r"""(\w[\w:-]*)\s*=\s*["']([^"']*)["']""")
_OLD_SEARCH_INPUT = re.compile(
    r"""<input\b[^>]*\bname\s*=\s*["']([^"']+)["'][^>]*>""", re.IGNORECASE
)

_PIECES = (
    "<form",
    "<FORM",
    "<formx",
    "<input",
    "<INPUT",
    "<inputs",
    "<",
    ">",
    " ",
    "\t",
    "\n",
    '"',
    "'",
    "=",
    " = ",
    "name",
    "NAME",
    "data-name",
    "action",
    "method",
    "q",
    "search",
    "/",
    "-",
    ":",
    "_",
    ".",
    "a",
    "b",
    "1",
    "é",
    "ß",
)


def _markup(rng: random.Random, length: int) -> str:
    return "".join(rng.choice(_PIECES) for _ in range(length))


def _tag(rng: random.Random) -> str:
    """A realistic form or input tag, now and then malformed."""
    attrs = []
    for _ in range(rng.randint(0, 5)):
        name = rng.choice(("action", "name", "id", "data-name", "aria-label", "x:y", "_q", "-a"))
        quote = rng.choice(('"', "'", "", '"'))
        value = rng.choice(("/search", "q", "a>b", "", "query", "s", "x'y", "/find?x=1"))
        space = rng.choice(("", " ", "  "))
        attrs.append(f"{name}{space}={space}{quote}{value}{quote}")
    close = rng.choice((">", ">", "/>", ""))
    return f"<{rng.choice(('form', 'input', 'FORM', 'Input'))} {' '.join(attrs)}{close}"


def _old_and_new(text: str) -> tuple[tuple[object, ...], tuple[object, ...]]:
    old = (
        [(m.start(), m.end()) for m in _OLD_FORM.finditer(text)],
        _OLD_ATTR.findall(text),
        _OLD_SEARCH_INPUT.findall(text),
    )
    new = (
        [(m.start(), m.end()) for m in site_search._form_tags(text)],
        site_search._ATTR.findall(text),
        site_search._search_input_names(text),
    )
    return old, new


def test_the_linear_scans_match_the_old_patterns_on_generated_tags():
    rng = random.Random(20261023)
    for _ in range(20_000):
        text = _tag(rng)
        old, new = _old_and_new(text)
        assert new == old, text
    for _ in range(5_000):
        text = " ".join(_tag(rng) for _ in range(rng.randint(2, 4)))
        old, new = _old_and_new(text)
        assert new == old, text


def test_the_linear_scans_match_the_old_patterns_on_random_markup():
    rng = random.Random(9)
    for _ in range(20_000):
        text = _markup(rng, rng.randint(0, 40))
        old, new = _old_and_new(text)
        assert new == old, text


_HOSTILE = {
    # SR2-02's three inputs, then the same shapes for this module's own tags.
    "html": "<html " * 40_000,
    "link": "<link " * 40_000,
    "long-link": '<html lang="de"><link ' + "a" * 200_000 + ">",
    "form": "<form " * 40_000,
    "input": '<form action="/search">' + "<input " * 40_000,
    "attr-name": '<form action="/search" ' + "a" * 50_000 + ">",
    "name-runs": '<form action="/search"><input' + " name" * 40_000 + ">",
}


@pytest.mark.parametrize("label", sorted(_HOSTILE))
def test_hostile_markup_is_read_in_linear_time(label):
    text = _HOSTILE[label]
    started = time.perf_counter()
    detect_surfaces(text, "https://www.example.edu/", now=NOW)
    site_search._form_tags(text)
    site_search._ATTR.findall(text)
    site_search._search_input_names(text)
    assert time.perf_counter() - started < 0.5
