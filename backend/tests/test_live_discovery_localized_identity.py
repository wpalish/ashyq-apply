"""Plan rule LI-1: localized identity in discovery.

Generic shapes (provenance: HELDOUT_PROVENANCE_AUDIT_2026-10-20): a German
sitemap that lists only ``/studium/studienangebot/detail/informatik-bachelor-
of-science-bsc``, whose page declares an ``hreflang="en-US"`` English twin, and
a Bologna ``laurea-magistrale`` URL offered to a bachelor applicant. Offline:
every document comes from a stub; the hosts are invented.
"""

from __future__ import annotations

import json

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    LiveDiscoveryAdapter,
    categorise_url,
    degree_level_named,
    english_alternate,
    matches_degree,
    matches_field,
)
from app.adapters.fetching import Fetcher
from tests.test_live_discovery import StubSite, sitemap_xml

GERMAN = "https://www.uni.de/studium/studienangebot/detail/informatik-bachelor-of-science-bsc"
ENGLISH = "https://www.uni.de/en/studies/degree-programs/detail/informatics-bachelor-of-science-bsc"
LAUREA_MAGISTRALE = "https://www.uni.it/en/education/programmes/laurea-magistrale-computer-science"


def german_html(alternate: str = ENGLISH) -> str:
    return (
        '<html lang="de"><head><title>Informatik - Bachelor of Science (B.Sc.)</title>'
        f'<link rel="alternate" hreflang="de-DE" href="{GERMAN}">'
        f'<link rel="alternate" hreflang="en-US" href="{alternate}">'
        "</head><body><main><h1>Informatik</h1><p>Bachelor of Science (B.Sc.). "
        "Regelstudienzeit 6 Semester, 180 Credits (ECTS). Studienbeginn Wintersemester. "
        "Bewerbung und Zulassung: Eignungsverfahren.</p></main></body></html>"
    )


def english_html() -> str:
    return (
        '<html lang="en"><head><title>Informatics - Bachelor of Science (B.Sc.)</title>'
        f'<link rel="alternate" hreflang="de-DE" href="{GERMAN}">'
        "</head><body><main><h1>Informatics</h1><p>Bachelor of Science (B.Sc.). "
        "Standard duration of studies 6 semesters, 180 credits (ECTS). Start of studies: "
        "winter semester. Admission requirements: aptitude assessment. "
        "Entry requirements include IELTS 6.5 overall.</p></main></body></html>"
    )


def _registry(tmp_path, homepage: str):
    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps([{"name": "U", "country": "Germany", "city": "X", "homepage": homepage}])
    )
    return path


@pytest.fixture
def profile_bachelor(profile):
    profile.context.intended_fields = ["computer science"]
    profile.context.level = "bachelor"
    return profile


def _german_site(extra: dict[str, str] | None = None, *locations: str) -> StubSite:
    return StubSite(
        {
            "https://www.uni.de/robots.txt": "Sitemap: https://www.uni.de/s.xml\n",
            "https://www.uni.de/s.xml": sitemap_xml(GERMAN, *locations),
            GERMAN: german_html(),
            ENGLISH: english_html(),
            **(extra or {}),
        }
    )


async def _discover(tmp_path, site: StubSite, homepage: str, profile):
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher, _registry(tmp_path, homepage))
        candidate = (await adapter.discover(profile))[0]
    return candidate, adapter.traces[0]


class TestGermanSitemapAndEnglishTwin:
    def test_on_the_german_url_scores_above_zero(self, monkeypatch):
        monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)
        category, score = categorise_url(GERMAN)
        assert category == "program_page"
        fields = ["computer science"]
        assert score + matches_field(GERMAN, fields) + matches_degree(GERMAN, "bachelor") > 0

    def test_off_the_german_url_scores_zero(self, monkeypatch):
        monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", False)
        assert categorise_url(GERMAN) == (None, 0)

    @pytest.mark.asyncio
    async def test_on_the_twin_is_read_and_confirmed_beside_the_original(
        self, tmp_path, monkeypatch, profile_bachelor
    ):
        monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)
        site = _german_site()
        candidate, trace = await _discover(tmp_path, site, "https://www.uni.de/", profile_bachelor)

        assert GERMAN in site.requested
        assert ENGLISH in site.requested
        assert site.requested.index(ENGLISH) == site.requested.index(GERMAN) + 1
        assert site.requested.count(ENGLISH) == 1, "the twin is read once"
        urls = [p.url for p in candidate.programs]
        assert ENGLISH in urls
        assert GERMAN in urls, "the original is kept beside its twin"
        assert trace.sitemap_urls_kept >= 1

    @pytest.mark.asyncio
    async def test_off_nothing_is_kept_or_read(self, tmp_path, monkeypatch, profile_bachelor):
        monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", False)
        site = _german_site()
        candidate, trace = await _discover(tmp_path, site, "https://www.uni.de/", profile_bachelor)

        assert GERMAN not in site.requested
        assert ENGLISH not in site.requested
        assert candidate.programs == []
        assert trace.sitemap_urls_kept == 0

    @pytest.mark.asyncio
    async def test_on_the_twin_takes_a_read_inside_the_cap(
        self, tmp_path, monkeypatch, profile_bachelor
    ):
        monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)
        monkeypatch.setattr(live_discovery, "MAX_PROGRAM_CANDIDATES_CHECKED", 2)
        other = "https://www.uni.de/studium/studienangebot/detail/informatik-lehramt"
        site = _german_site({}, other)
        await _discover(tmp_path, site, "https://www.uni.de/", profile_bachelor)

        programme_reads = [u for u in site.requested if "/studienangebot/" in u or "/en/" in u]
        assert programme_reads == [GERMAN, ENGLISH]


class TestEnglishAlternate:
    def test_an_english_page_is_not_followed(self):
        assert english_alternate(ENGLISH, english_html(), "uni.de") is None

    def test_a_page_without_a_language_is_not_followed(self):
        html = german_html().replace(' lang="de"', "")
        assert english_alternate(GERMAN, html, "uni.de") is None

    def test_an_alternate_on_another_domain_is_not_followed(self):
        html = german_html(alternate="https://translate.example.com/uni/informatics")
        assert english_alternate(GERMAN, html, "uni.de") is None

    def test_a_relative_alternate_is_resolved_on_the_page(self):
        html = german_html(alternate="/en/studies/degree-programs/detail/informatics")
        assert english_alternate(GERMAN, html, "uni.de") == (
            "https://www.uni.de/en/studies/degree-programs/detail/informatics"
        )


class TestLocalDegreeWords:
    @pytest.mark.asyncio
    async def test_on_a_laurea_magistrale_url_is_rejected_before_a_read(
        self, tmp_path, monkeypatch, profile_bachelor
    ):
        monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)
        site = StubSite(
            {
                "https://www.uni.it/robots.txt": "Sitemap: https://www.uni.it/s.xml\n",
                "https://www.uni.it/s.xml": sitemap_xml(LAUREA_MAGISTRALE),
            }
        )
        _, trace = await _discover(tmp_path, site, "https://www.uni.it/", profile_bachelor)

        assert LAUREA_MAGISTRALE not in site.requested
        assert (LAUREA_MAGISTRALE, "names a degree level other than bachelor") in trace.rejected

    @pytest.mark.asyncio
    async def test_off_the_laurea_magistrale_url_costs_a_read(
        self, tmp_path, monkeypatch, profile_bachelor
    ):
        monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", False)
        site = StubSite(
            {
                "https://www.uni.it/robots.txt": "Sitemap: https://www.uni.it/s.xml\n",
                "https://www.uni.it/s.xml": sitemap_xml(LAUREA_MAGISTRALE),
            }
        )
        await _discover(tmp_path, site, "https://www.uni.it/", profile_bachelor)
        assert LAUREA_MAGISTRALE in site.requested

    @pytest.mark.parametrize(
        ("url", "level"),
        [
            ("https://u.it/corsi/laurea-magistrale/informatica", "master"),
            ("https://u.it/corsi/laurea/informatica", "bachelor"),
            ("https://u.edu.tr/lisans/bilgisayar", "bachelor"),
            ("https://u.edu.tr/yuksek-lisans/bilgisayar", "master"),
            ("https://u.edu.tr/on-lisans/bilgisayar", None),
            ("https://u.cz/bakalarske-studium/informatika", "bachelor"),
            ("https://u.cz/magisterske-studium/informatika", "master"),
            ("https://u.kz/bakalavriat/informatika", "bachelor"),
            ("https://u.kz/magistratura/informatika", "master"),
            ("https://u.se/kandidatprogram/datavetenskap", "bachelor"),
            ("https://u.dk/kandidat/datalogi", None),
            ("https://u.es/grado/informatica", "bachelor"),
            ("https://u.fr/licence/informatique", "bachelor"),
            ("https://u.br/mestrado/computacao", "master"),
            ("https://u.edu/master-s-programmes/computing", "master"),
        ],
    )
    def test_on_certain_local_words_name_their_level(self, monkeypatch, url, level):
        monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)
        assert degree_level_named(url) == level

    def test_off_local_words_name_no_level(self, monkeypatch):
        monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", False)
        assert degree_level_named("https://u.it/corsi/laurea-magistrale/informatica") is None
        assert degree_level_named("https://u.edu.tr/lisans/bilgisayar") is None
