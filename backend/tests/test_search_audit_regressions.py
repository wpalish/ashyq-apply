"""Native pytest adaptation of the sealed 20 + 13 finite search controls.

All pages and results are synthetic. These controls verify URL boundaries,
degree/field routing and sitemap scan accounting, not measured search quality.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery as ld
from app.adapters.fetching import Fetcher, FetchResult, same_source_site
from app.adapters.search.base import SearchResult
from app.adapters.search.prefilter import prefilter
from app.domain.claim_verifier import url_matches_domains
from app.domain.enums import DegreeLevel, FetchOutcome
from app.domain.site_identity import canonical_host, hosts_share_site

DOMAIN = "uni.example"
ROOT_SITEMAP = "https://uni.example/sitemap.xml"
CHILD_SITEMAP = "https://uni.example/child.xml"
BAD_LAW_URL = "https://uni.example:not-a-port/study/bachelor/law"
GOOD_LAW_URL = "https://uni.example/study/bachelor/law"


@pytest.fixture(autouse=True)
def _deny_outbound_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Deny IP sockets/DNS within each test; restore native state afterwards."""
    attempts: list[str] = []
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_sendto = socket.socket.sendto

    def deny(*args, **kwargs):
        attempts.append("denied_network_attempt")
        raise AssertionError("Outbound network forbidden in finite search controls")

    def guarded_connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            return deny(address)
        return original_connect(sock, address)

    def guarded_connect_ex(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            return deny(address)
        return original_connect_ex(sock, address)

    def guarded_sendto(sock, *args, **kwargs):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            return deny(*args, **kwargs)
        return original_sendto(sock, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket.socket, "sendto", guarded_sendto)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    yield
    assert not attempts, "A control attempted outbound network"


def _search_observation(urls: list[str], degree: DegreeLevel = DegreeLevel.BACHELOR):
    results = [
        SearchResult(url, "Synthetic programme", "fake", rank, datetime.now(UTC))
        for rank, url in enumerate(urls, 1)
    ]
    report = prefilter(results, domain=DOMAIN, degree=degree)
    return {
        "kept": [row.url for row in report.kept],
        "rejected": [row.reason for row in report.rejected],
    }


def _urlset(locations: list[str]) -> str:
    return "<urlset>" + "".join(f"<url><loc>{url}</loc></url>" for url in locations) + "</urlset>"


async def _collect_synthetic_sitemaps(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    bodies: dict[str, str],
    declared_documents: list[str],
    *,
    keep: bool | None = None,
):
    requested: list[str] = []

    async def get(url: str, **kwargs) -> FetchResult:
        requested.append(url)
        text = bodies[url]
        return FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            content=text.encode(),
            text=text,
            final_url=url,
        )

    async def declared(origin: str, trace: ld.DiscoveryTrace) -> list[str]:
        return declared_documents

    async with Fetcher(tmp_path / "search-audit-cache", offline=True) as fetcher:
        monkeypatch.setattr(fetcher, "get", get)
        reader = ld.SitemapReader(fetcher)
        monkeypatch.setattr(reader, "_declared_sitemaps", declared)
        trace = ld.DiscoveryTrace("Synthetic University", DOMAIN)

        def keep_rule(url: str) -> bool:
            return bool(keep)

        pages = await reader.collect(
            "https://uni.example/", DOMAIN, trace, keep_rule if keep is not None else None
        )
    return pages, trace, requested


async def _bounded_sitemap_observation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    locations: list[str],
    *,
    keep: bool = True,
    plain: bool = False,
    child_locations: list[str] | None = None,
    duplicate_document: bool = False,
):
    monkeypatch.setattr(ld, "MAX_SITEMAP_URLS", 2)

    def body(rows: list[str]) -> str:
        return "\n".join(rows) if plain else _urlset(rows)

    bodies = {ROOT_SITEMAP: body(locations)}
    if child_locations is not None:
        bodies[CHILD_SITEMAP] = body(child_locations)
    declared_documents = [ROOT_SITEMAP]
    if duplicate_document:
        declared_documents.append(ROOT_SITEMAP)
    elif child_locations is not None:
        declared_documents.append(CHILD_SITEMAP)
    pages, trace, requested = await _collect_synthetic_sitemaps(
        monkeypatch, tmp_path, bodies, declared_documents, keep=keep
    )
    truncation = None
    if any("larger than we read" in error for error in trace.errors):
        truncation = "unread_urls"
    elif any("remaining sitemap documents were not read" in error for error in trace.errors):
        truncation = "unread_documents"
    return {
        "seen": trace.sitemap_urls_seen,
        "kept": trace.sitemap_urls_kept,
        "page_count": len(pages),
        "fetches": len(requested),
        "truncation": truncation,
    }


async def _malformed_sitemap_observation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, bad_document: bool = False
):
    if bad_document:
        bad_child = "https://uni.example:not-a-port/child.xml"
        root_body = (
            f"<sitemapindex><sitemap><loc>{bad_child}</loc></sitemap>"
            f"<sitemap><loc>{CHILD_SITEMAP}</loc></sitemap></sitemapindex>"
        )
        bodies = {ROOT_SITEMAP: root_body, CHILD_SITEMAP: _urlset([GOOD_LAW_URL])}
    else:
        bodies = {ROOT_SITEMAP: _urlset([BAD_LAW_URL, GOOD_LAW_URL])}
    pages, trace, requested = await _collect_synthetic_sitemaps(
        monkeypatch, tmp_path, bodies, [ROOT_SITEMAP]
    )
    return {
        "leads": pages,
        "seen": trace.sitemap_urls_seen,
        "kept": trace.sitemap_urls_kept,
        "calls": requested,
    }


def test_discovery_01_law_exact():
    assert ld.matches_field_text("Law", ["Law"]) is True


def test_discovery_02_art_exact():
    assert ld.matches_field_text("Art", ["Art"]) is True


def test_discovery_03_short_academic_wrappers():
    assert [
        ld.matches_field_text("LLB Law", ["Law"]),
        ld.matches_field_text("Art (BA)", ["Art"]),
    ] == [True, True]


def test_discovery_04_short_other_subjects():
    assert [
        ld.matches_field_text("Law and Art", ["Law"]),
        ld.matches_field_text("Art and Law", ["Art"]),
        ld.matches_field_text("Art History", ["Art"]),
        ld.matches_field_text("Law Enforcement", ["Law"]),
    ] == [False] * 4


def test_discovery_05_short_substrings():
    assert [
        ld.matches_field_text("Cartography", ["Art"]),
        ld.matches_field_text("Lawrence", ["Law"]),
    ] == [False, False]


def test_discovery_06_weak_aliases_unchanged():
    assert [
        ld.matches_field_text("Business Informatics", ["Computer Science"]),
        ld.matches_field_text("Computing and Data Science", ["Computer Science"]),
    ] == [False, False]


def test_discovery_07_long_subjects_unchanged():
    assert [
        ld.matches_field_text("Data & Computer Science", ["Computer Science"]),
        ld.matches_field_text("Computing Science (Bachelor)", ["Computer Science"]),
    ] == [True, True]


def test_discovery_08_pre_bachelor_foundation():
    url = "https://uni.example/study/pre-bachelor/computer-science"
    assert {
        "named": ld.degree_level_named(url),
        "filter": _search_observation([url], DegreeLevel.FOUNDATION),
    } == {"named": "foundation", "filter": {"kept": [url], "rejected": []}}


def test_discovery_09_preparatory_before_bachelor():
    url = "https://uni.example/study/preparatory/bachelor/computer-science"
    assert {
        "named": ld.degree_level_named(url),
        "bachelor_filter": _search_observation([url]),
    } == {
        "named": "foundation",
        "bachelor_filter": {"kept": [], "rejected": ["wrong_degree_level"]},
    }


def test_discovery_10_ordinary_degrees_unchanged():
    assert [
        ld.degree_level_named("https://uni.example/bachelor/computer-science"),
        ld.degree_level_named("https://uni.example/master/computer-science"),
        ld.degree_level_named("https://uni.example/foundation/computer-science"),
    ] == ["bachelor", "master", "foundation"]


def test_discovery_11_bad_port_does_not_abort_good_result():
    good = "https://uni.example/study/bachelor/computer-science"
    bad = "https://uni.example:not-a-port/study/bachelor/computer-science"
    assert {
        "canonical": ld.canonical_url(bad),
        "filter": _search_observation([bad, good]),
    } == {"canonical": bad, "filter": {"kept": [good], "rejected": ["malformed_url"]}}


def test_discovery_12_out_of_range_port():
    assert _search_observation(["https://uni.example:99999/study/bachelor/computer-science"]) == {
        "kept": [],
        "rejected": ["malformed_url"],
    }


def test_discovery_13_malformed_hostname_brackets():
    assert _search_observation(["https://[broken/study/bachelor/computer-science"]) == {
        "kept": [],
        "rejected": ["malformed_url"],
    }


def test_discovery_14_malformed_hostname_nfkc():
    assert _search_observation(["https://uni.example／evil/study/bachelor/computer-science"]) == {
        "kept": [],
        "rejected": ["malformed_url"],
    }


@pytest.mark.asyncio
async def test_discovery_15_sitemap_keep_false_cap(monkeypatch, tmp_path):
    six = [f"https://uni.example/news/{i}" for i in range(6)]
    assert await _bounded_sitemap_observation(monkeypatch, tmp_path, six, keep=False) == {
        "seen": 2,
        "kept": 0,
        "page_count": 0,
        "fetches": 1,
        "truncation": "unread_urls",
    }


@pytest.mark.asyncio
async def test_discovery_16_sitemap_duplicate_cap(monkeypatch, tmp_path):
    assert await _bounded_sitemap_observation(
        monkeypatch, tmp_path, ["https://uni.example/news/0"] * 6
    ) == {"seen": 2, "kept": 1, "page_count": 1, "fetches": 1, "truncation": "unread_urls"}


@pytest.mark.asyncio
async def test_discovery_17_sitemap_off_domain_cap(monkeypatch, tmp_path):
    six = [f"https://elsewhere.example/{i}" for i in range(6)]
    assert await _bounded_sitemap_observation(monkeypatch, tmp_path, six) == {
        "seen": 2,
        "kept": 0,
        "page_count": 0,
        "fetches": 1,
        "truncation": "unread_urls",
    }


@pytest.mark.asyncio
async def test_discovery_18_sitemap_exact_cap_is_complete(monkeypatch, tmp_path):
    two = [f"https://uni.example/news/{i}" for i in range(2)]
    assert await _bounded_sitemap_observation(monkeypatch, tmp_path, two) == {
        "seen": 2,
        "kept": 2,
        "page_count": 2,
        "fetches": 1,
        "truncation": None,
    }


@pytest.mark.asyncio
async def test_discovery_19_sitemap_queued_document_boundaries(monkeypatch, tmp_path):
    six = [f"https://uni.example/news/{i}" for i in range(6)]
    assert [
        await _bounded_sitemap_observation(
            monkeypatch, tmp_path, six[:2], keep=False, child_locations=six[2:4]
        ),
        await _bounded_sitemap_observation(
            monkeypatch, tmp_path, six[:2], keep=False, duplicate_document=True
        ),
    ] == [
        {"seen": 2, "kept": 0, "page_count": 0, "fetches": 1, "truncation": "unread_documents"},
        {"seen": 2, "kept": 0, "page_count": 0, "fetches": 1, "truncation": None},
    ]


@pytest.mark.asyncio
async def test_discovery_20_sitemap_plain_text_truncation(monkeypatch, tmp_path):
    six = [f"https://uni.example/news/{i}" for i in range(6)]
    assert await _bounded_sitemap_observation(
        monkeypatch, tmp_path, six, keep=False, plain=True
    ) == {"seen": 2, "kept": 0, "page_count": 0, "fetches": 1, "truncation": "unread_urls"}


def test_site_identity_01_canonical_host_bad_port_fails_closed():
    assert canonical_host(BAD_LAW_URL) == ""


def test_site_identity_02_site_compare_bad_left_fails_closed():
    assert hosts_share_site(BAD_LAW_URL, DOMAIN) is False


def test_site_identity_03_site_compare_bad_right_fails_closed():
    assert hosts_share_site(GOOD_LAW_URL, BAD_LAW_URL) is False


def test_site_identity_04_claim_domain_bad_url_fails_closed():
    assert url_matches_domains(BAD_LAW_URL, [DOMAIN]) is False


def test_site_identity_05_claim_domain_bad_allowlist_fails_closed():
    assert url_matches_domains(GOOD_LAW_URL, [BAD_LAW_URL]) is False


def test_site_identity_06_discovery_and_redirect_bad_url_fails_closed():
    assert [
        ld.same_institution(BAD_LAW_URL, DOMAIN),
        same_source_site(GOOD_LAW_URL, BAD_LAW_URL),
    ] == [False, False]


@pytest.mark.asyncio
async def test_site_identity_07_malformed_sitemap_page_precedes_good(monkeypatch, tmp_path):
    assert await _malformed_sitemap_observation(monkeypatch, tmp_path) == {
        "leads": [GOOD_LAW_URL],
        "seen": 2,
        "kept": 1,
        "calls": [ROOT_SITEMAP],
    }


@pytest.mark.asyncio
async def test_site_identity_08_malformed_sitemap_document_precedes_good(monkeypatch, tmp_path):
    assert await _malformed_sitemap_observation(monkeypatch, tmp_path, bad_document=True) == {
        "leads": [GOOD_LAW_URL],
        "seen": 1,
        "kept": 1,
        "calls": [ROOT_SITEMAP, CHILD_SITEMAP],
    }


def test_site_identity_09_valid_port_and_host_unchanged():
    assert [
        canonical_host("https://UNI.EXAMPLE:8443/a"),
        canonical_host(DOMAIN),
        hosts_share_site("https://catalog.uni.example/a", GOOD_LAW_URL),
    ] == [DOMAIN, DOMAIN, True]


def test_site_identity_10_unicode_idna_unchanged():
    assert [
        canonical_host("https://straße.de/a"),
        hosts_share_site("https://straße.de/a", "https://xn--strae-oqa.de/b"),
        hosts_share_site("https://straße.de/a", "https://strasse.de/b"),
    ] == ["xn--strae-oqa.de", True, False]


def test_site_identity_11_private_tenant_boundary_unchanged():
    assert [
        hosts_share_site("https://university.github.io/a", "https://attacker.github.io/a"),
        hosts_share_site(
            "https://catalog.university.pages.dev/a", "https://university.pages.dev/a"
        ),
    ] == [False, True]


def test_site_identity_12_public_ip_identity_unchanged():
    assert [
        hosts_share_site("https://93.184.216.34/a", "https://1.2.216.34/a"),
        hosts_share_site("https://93.184.216.34/a", "https://93.184.216.34/b"),
    ] == [False, True]


def test_site_identity_13_valid_claim_site_unchanged():
    assert [
        url_matches_domains(GOOD_LAW_URL, [DOMAIN]),
        url_matches_domains("https://attacker.example/?u=uni.example", [DOMAIN]),
    ] == [True, False]


@pytest.mark.parametrize("phrase_match", [False, True], ids=["legacy", "phrase"])
@pytest.mark.parametrize(
    ("label", "field"),
    [
        pytest.param("CS", "CS", id="cs-plain"),
        pytest.param("Bachelor of CS", "CS", id="cs-academic-wrapper"),
        pytest.param("EEE", "EEE", id="eee-plain"),
        pytest.param("BSc EEE", "EEE", id="eee-academic-wrapper"),
        pytest.param("MBA", "MBA", id="mba-plain"),
        pytest.param("MBA (Bachelor)", "MBA", id="mba-academic-wrapper"),
    ],
)
def test_discovery_short_extension_rejects_unknown_acronyms(
    monkeypatch: pytest.MonkeyPatch, label: str, field: str, phrase_match: bool
):
    """Law/Art's exact-subject extension does not approve raw short acronyms."""
    monkeypatch.setattr(ld, "SUBJECT_PHRASE_MATCH", phrase_match)
    assert ld.matches_field_text(label, [field]) is False
