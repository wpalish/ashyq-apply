"""CU-1: ``http`` and ``https`` of one institution page are one URL.

METU's navigation offered ``http://…/admissions/undergraduate-programs`` and
``https://…/admissions/undergraduate-programs``, and the run read both — 10 s
each under the host's Crawl-delay. ``navigation.py`` already merged the two
schemes for its own links; under CU-1 ``canonical_url`` does it for every
deduplication in the pipeline, choosing ``https`` as the URL to read.
"""

from __future__ import annotations

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    _harvest_links,
    canonical_url,
    scheme_free_identity,
)
from app.adapters.search.navigation import links_from

_HTTP = "http://www.metu.edu.tr/admissions/undergraduate-programs"
_HTTPS = "https://www.metu.edu.tr/admissions/undergraduate-programs"


@pytest.fixture
def cu1(monkeypatch):
    monkeypatch.setattr(live_discovery, "CANONICAL_HTTP_HTTPS", True)


def test_the_rule_is_off_by_default_and_the_scheme_is_kept() -> None:
    assert live_discovery.CANONICAL_HTTP_HTTPS is False
    assert canonical_url(_HTTP) == _HTTP
    assert canonical_url(_HTTPS) == _HTTPS


def test_both_schemes_of_one_page_are_one_url(cu1) -> None:
    assert canonical_url(_HTTP) == canonical_url(_HTTPS) == _HTTPS
    assert canonical_url("http://www.metu.edu.tr:80/a/") == "https://www.metu.edu.tr/a"


def test_the_rest_of_the_canonical_form_is_unchanged(cu1) -> None:
    assert (
        canonical_url("HTTP://WWW.Metu.edu.tr//a/b/?utm_source=x&id=2#top")
        == "https://www.metu.edu.tr/a/b?id=2"
    )


def test_a_non_default_port_keeps_its_scheme(cu1) -> None:
    """``http://h:8080`` and ``https://h:8080`` are different services."""
    assert canonical_url("http://www.metu.edu.tr:8080/a") == "http://www.metu.edu.tr:8080/a"


def test_the_identity_is_the_one_navigation_used(cu1) -> None:
    assert scheme_free_identity(canonical_url(_HTTP)) == scheme_free_identity(_HTTP)
    assert scheme_free_identity(_HTTP) == scheme_free_identity(_HTTPS)


def test_a_page_linking_itself_both_ways_yields_one_lead(cu1) -> None:
    html = (
        f'<a href="{_HTTP}">Undergraduate programs</a><a href="{_HTTPS}">Undergraduate programs</a>'
    )

    links = [url for url, _label in _harvest_links(html, "https://www.metu.edu.tr/", "metu.edu.tr")]

    assert links == [_HTTPS]


def test_without_the_rule_the_same_page_is_two_leads() -> None:
    html = (
        f'<a href="{_HTTP}">Undergraduate programs</a><a href="{_HTTPS}">Undergraduate programs</a>'
    )

    links = [url for url, _label in _harvest_links(html, "https://www.metu.edu.tr/", "metu.edu.tr")]

    assert sorted(links) == [_HTTP, _HTTPS]


@pytest.mark.parametrize("flag", [True, False])
def test_navigation_still_merges_the_two_schemes(monkeypatch, flag: bool) -> None:
    monkeypatch.setattr(live_discovery, "CANONICAL_HTTP_HTTPS", flag)
    html = (
        f'<a href="{_HTTP}">Undergraduate programs</a><a href="{_HTTPS}">Undergraduate programs</a>'
    )

    links = links_from(html, "https://www.metu.edu.tr/")

    assert [link.url for link in links] == [_HTTPS]
