"""Malformed links on real university pages never crash shared code (2026-10-19).

usp linked a host ending in a zero-width space and rwth wrote a phone number
where a port goes. Both raised out of ``links_from``, ``canonical_url`` and
``Fetcher.get``; ``evaluation/research/index_ceiling.py`` had to wrap them.
Offline: no network, no search provider.
"""

from __future__ import annotations

import pytest

from app.adapters.discovery.catalog_walker import extract_links
from app.adapters.discovery.live_discovery import (
    _harvest_links,
    admissions_host_from_homepage,
    canonical_url,
    declared_alternates,
    same_institution,
)
from app.adapters.document_ir import build_document_ir
from app.adapters.fetching import Fetcher
from app.adapters.search.navigation import links_from
from app.adapters.url_canonical import invalid_url_reason, page_link, strip_invisible_host
from app.domain.enums import FetchOutcome
from app.domain.site_identity import canonical_host

USP = "https://www.usp.br/"
USP_ZWSP = "https://www.usp.br​/graduacao"
RWTH = "https://www.rwth-aachen.de/"
RWTH_PHONE = "https://www.rwth-aachen.de:+49 241 80 1/cms/"

#: Every shape that must be dropped (never raised) by link extraction.
INVALID = [
    RWTH_PHONE,
    "https://www.rwth-aachen.de:+49241801/",
    "http://exa mple.com/a",
    "https://host:99999/",
    "https://[::1/x",
]
NOT_WEB = ["javascript:void(0)", "mailto:info@usp.br", "tel:+49 241 80 1"]


def _page(*hrefs: str) -> str:
    anchors = "".join(f'<a href="{h}">Graduação programme</a>' for h in hrefs)
    return f"<html><body><nav>{anchors}</nav></body></html>"


@pytest.mark.parametrize("char", ["​", "‌", "‍", "﻿", "­", "‎"])
def test_invisible_characters_are_removed_from_the_host_only(char: str) -> None:
    url = f"https://www.usp.br{char}/a{char}b?q={char}"
    assert strip_invisible_host(url) == f"https://www.usp.br/a{char}b?q={char}"
    assert page_link(USP, url) == f"https://www.usp.br/a{char}b?q={char}"


def test_a_clean_url_is_returned_unchanged() -> None:
    assert strip_invisible_host("https://www.usp.br/x") == "https://www.usp.br/x"
    assert page_link(USP, "/x?y=1#z") == "https://www.usp.br/x?y=1#z"
    assert page_link(USP, "https://bücher.de/") == "https://bücher.de/"


@pytest.mark.parametrize("url", INVALID)
def test_an_invalid_web_url_is_named_and_dropped(url: str) -> None:
    assert invalid_url_reason(url)
    assert page_link(RWTH, url) is None


@pytest.mark.parametrize("url", NOT_WEB)
def test_other_schemes_are_left_to_the_callers_scheme_rule(url: str) -> None:
    assert invalid_url_reason(url) is None
    assert page_link(USP, url) == url


def test_a_url_without_a_host_cannot_be_requested() -> None:
    assert invalid_url_reason("https:///no-host") == "URL has no host"


def test_a_zero_width_host_raises_nowhere() -> None:
    assert invalid_url_reason(USP_ZWSP)  # not requestable as written
    assert canonical_host(USP_ZWSP) == ""  # fails closed, no InvalidURL
    assert same_institution(USP_ZWSP, "usp.br") is False
    assert canonical_url(USP_ZWSP) == "https://www.usp.br/graduacao"


@pytest.mark.parametrize("url", [*INVALID, *NOT_WEB, USP_ZWSP])
def test_canonical_url_never_raises(url: str) -> None:
    assert isinstance(canonical_url(url), str)


def test_canonical_url_returns_an_unparseable_url_as_given() -> None:
    assert canonical_url(f"  {RWTH_PHONE} ") == RWTH_PHONE
    assert canonical_url("https://host:99999/") == "https://host:99999/"


def test_navigation_keeps_the_usp_link_and_drops_the_rest() -> None:
    links = links_from(_page(USP_ZWSP, *INVALID, *NOT_WEB), USP)
    assert [link.url for link in links] == ["https://www.usp.br/graduacao"]
    assert links_from(_page(*INVALID, *NOT_WEB, "/cms/studium"), RWTH)[0].url == (
        "https://www.rwth-aachen.de/cms/studium"
    )
    assert len(links_from(_page(*INVALID, *NOT_WEB, "/cms/studium"), RWTH)) == 1


def test_discovery_link_harvests_drop_malformed_links() -> None:
    html = _page(USP_ZWSP, *INVALID, *NOT_WEB)
    assert [url for url, _ in _harvest_links(html, USP, "usp.br")] == [
        "https://www.usp.br/graduacao"
    ]
    assert [link.url for link in extract_links(html, USP, "usp.br")] == [
        "https://www.usp.br/graduacao"
    ]
    assert admissions_host_from_homepage(html, USP, "usp.br") == {}


def test_declared_alternates_drop_malformed_hrefs() -> None:
    head = "".join(
        f'<link rel="alternate" hreflang="en" href="{h}">' for h in [RWTH_PHONE, "/en/x"]
    )
    html = f"<html><head>{head}</head></html>"
    assert declared_alternates("https://www.rwth-aachen.de/de/x", html, "rwth-aachen.de") == [
        "https://www.rwth-aachen.de/en/x"
    ]


def test_evidence_links_drop_malformed_hrefs() -> None:
    doc = build_document_ir(_page(RWTH_PHONE, "/cms/studium", "mailto:a@b.c"), RWTH)
    assert [link.url for link in doc.links] == ["https://www.rwth-aachen.de/cms/studium"]


@pytest.mark.parametrize("url", [USP_ZWSP, *INVALID])
async def test_fetcher_get_turns_an_invalid_url_into_a_failed_read(tmp_path, url: str) -> None:
    async with Fetcher(tmp_path) as fetcher:
        result = await fetcher.get(url)
    assert result.outcome is FetchOutcome.UNPARSEABLE
    assert not result.ok
    assert result.error.startswith("invalid URL, not fetched")
    assert fetcher.stats[FetchOutcome.UNPARSEABLE.value] == 1


async def test_fetcher_get_contains_an_invalid_url_raised_deeper(tmp_path, monkeypatch) -> None:
    import httpx

    fetcher = Fetcher(tmp_path)

    async def raising(url: str, **kwargs: object) -> object:
        raise httpx.InvalidURL("Invalid IDNA hostname")

    monkeypatch.setattr(fetcher, "_get", raising)
    result = await fetcher.get("https://www.usp.br/x")
    assert result.outcome is FetchOutcome.UNPARSEABLE
