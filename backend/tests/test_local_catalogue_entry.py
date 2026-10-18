"""Plan v3 rule R4 (LC-1, ticket 20): the local catalogue as an entry point.

The homepages, catalogue pages and catalogue-host sitemaps of the development
cases (``PROGRAMME_DISCOVERY_ANALYSIS_2026-10-18.md`` §2.3 and §3 Change 3) are
hand-fetched copies trimmed into ``fixtures/local_catalogue_entry/`` — each file
names its source URL; the gold programme pages are R1's
(``fixtures/localized_identity/``). Pages written for a test say so where they
are built. No heldout page, label or capture was opened. Offline: nothing is
fetched.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters import page_classifier
from app.adapters.discovery import catalog_walker, live_discovery
from app.adapters.discovery.catalog_walker import WalkerLink
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    PageCategory,
    SitemapReader,
    canonical_url,
    categorise_url,
    looks_like_catalogue,
)
from app.adapters.fetching import Fetcher
from app.adapters.search.navigation import study_section_label
from app.adapters.search.ontology import country_languages
from tests.test_live_discovery import StubSite, sitemap_index_xml, sitemap_xml

BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "local_catalogue_entry"
GOLD = Path(__file__).parent / "fixtures" / "localized_identity"

PUC_GOLD = canonical_url(
    "https://admision.uc.cl/carreras/licenciatura-en-ingenieria-en-ciencia-de-la-computacion/"
)
UIO_GOLD = canonical_url("https://www.uio.no/studier/program/informatikk-programmering/")
UBA_GOLD = canonical_url(
    "https://ingresantes.exactas.uba.ar/licenciatura-en-ciencias-de-la-computacion/"
)


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def gold(name: str) -> str:
    return (GOLD / name).read_text(encoding="utf-8")


@pytest.fixture(params=[False, True], ids=["off", "on"])
def r4(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "LOCAL_CATALOGUE_ENTRY", request.param)
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", True)
    return request.param


@pytest.fixture
def r4_on(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "LOCAL_CATALOGUE_ENTRY", True)
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", True)


def test_flag_is_off_by_default() -> None:
    assert live_discovery.LOCAL_CATALOGUE_ENTRY is False


# --- 1. section labels (20 Q1) -------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "country", "phrase"),
    [
        # Labels as the development homepages print them (the hand checks).
        ("Carreras de pregrado launch", "Chile", "carreras de pregrado"),  # uc.cl
        ("Carreras de Grado", "Argentina", "carreras de grado"),  # uba.ar
        ("Studier", "Norway", "studier"),  # uio.no
        ("Finn studier", "Norway", "finn studier"),  # uio.no/studier
        ("Uddannelse", "Denmark", "uddannelse"),  # ku.dk
        ("Choisir sa formation", "France", "choisir sa formation"),  # universite-paris-saclay.fr
        ("Onderwijsaanbod 2026 - 2027", "Belgium", "onderwijsaanbod"),  # onderwijsaanbod.kuleuven
        ("本科专业", "China", "本科专业"),  # tsinghua.edu.cn
        ("学部", "Japan", "学部"),  # u-tokyo.ac.jp
        ("Graduação", "Brazil", "graduação"),  # usp.br
        ("教學", "Taiwan", "教學"),  # ntu.edu.tw
    ],
)
def test_a_section_label_in_the_country_language_is_a_section_link(
    label: str, country: str, phrase: str
) -> None:
    found = study_section_label(label, country_languages(country), "bachelor")
    assert found is not None
    assert found.phrase == phrase


@pytest.mark.parametrize(
    ("label", "country"),
    [
        # A headline containing a section word is news, not the section (uio.no).
        ("Ny bachelor skal styrke tilgangen på kritisk teknologikompetanse", "Norway"),
        # A section word must be the whole label.
        ("Formation continue - Validation des acquis", "France"),
        ("Formation en alternance", "France"),
        # Another level, or continuing education, is not the bachelor's section.
        ("Carreras de Posgrado", "Argentina"),
        ("Pós-graduação", "Brazil"),
        ("Ph.d.-uddannelse", "Denmark"),
        ("Efteruddannelse", "Denmark"),
        ("研究生教育", "China"),
        ("终身教育", "China"),
        # Unspaced scripts: the label is the phrase or nothing (学部 is not 学部長).
        ("学部長メッセージ", "Japan"),
        # The language is the institution's country's, never another's.
        ("Carreras de pregrado", "Norway"),
        ("Studier", "United Kingdom"),
        ("Studier", ""),
    ],
)
def test_not_a_section_link(label: str, country: str) -> None:
    assert study_section_label(label, country_languages(country), "bachelor") is None


def test_the_level_is_the_applicants() -> None:
    languages = country_languages("Chile")
    assert study_section_label("Carreras de pregrado", languages, "master") is None
    assert study_section_label("Carreras de grado y posgrado", languages, "bachelor") is not None


# --- 2. local listing words as URL signals (20 Q2) -------------------------------------


@pytest.mark.parametrize(
    ("url", "category"),
    [
        ("https://admision.uc.cl/carreras", PageCategory.PROGRAM_CATALOG),
        ("https://www.uio.no/studier", PageCategory.PROGRAM_CATALOG),
        ("https://www.universite-paris-saclay.fr/formation", PageCategory.PROGRAM_CATALOG),
        ("https://onderwijsaanbod.kuleuven.be/opleidingen/n", PageCategory.PROGRAM_CATALOG),
        ("https://exactas.uba.ar/ensenanza/carreras-de-grado", PageCategory.PROGRAM_CATALOG),
        # psaclay-fr's gold (sitemap), kuleuven's gold (catalogue code).
        (
            "https://www.universite-paris-saclay.fr/formation/licence/informatique",
            PageCategory.PROGRAM_PAGE,
        ),
        (
            "https://onderwijsaanbod.kuleuven.be/opleidingen/n/SC_51016742.htm",
            PageCategory.PROGRAM_PAGE,
        ),
    ],
)
def test_local_listing_words_categorise_only_under_the_flag(
    r4: bool, url: str, category: str
) -> None:
    assert categorise_url(url)[0] == (category if r4 else None)
    if category == PageCategory.PROGRAM_CATALOG:
        assert looks_like_catalogue(url) is r4


def test_studier_program_scores_above_the_english_rule_alone(r4: bool) -> None:
    category, score = categorise_url(UIO_GOLD)
    assert category == PageCategory.PROGRAM_PAGE
    assert score == (7 if r4 else 4)


@pytest.mark.parametrize(
    "url",
    [
        "https://uni.edu/undergraduate/computer-science",
        "https://uni.edu/study/programmes",
        "https://uni.edu/news/formation-of-a-new-lab",
        PUC_GOLD,  # LI-1 already scores /carreras/<slug>; R4 does not count it twice
    ],
)
def test_urls_the_rule_does_not_name_score_as_before(monkeypatch, url: str) -> None:
    monkeypatch.setattr(live_discovery, "LOCAL_CATALOGUE_ENTRY", False)
    before = categorise_url(url)
    monkeypatch.setattr(live_discovery, "LOCAL_CATALOGUE_ENTRY", True)
    assert categorise_url(url) == before


def test_the_walker_reads_local_list_words_as_a_list(r4: bool) -> None:
    link = WalkerLink(url="https://uni.cl/x7", label="Carreras de pregrado", score=0, source="html")
    assert catalog_walker._names_a_list(link) is r4


# --- 3. catalogue hosts (20 Q3, Q4) ----------------------------------------------------


@pytest.mark.parametrize(
    ("url", "label", "homepage", "country", "ranked"),
    [
        # uc.cl's link to its admissions catalogue host.
        (
            "https://admision.uc.cl/carreras",
            "Carreras de pregrado launch",
            "https://www.uc.cl/",
            "Chile",
            0,
        ),
        # A local listing path alone names a catalogue host too.
        (
            "https://onderwijsaanbod.kuleuven.be/opleidingen/n",
            "",
            "https://www.kuleuven.be/",
            "Belgium",
            2,
        ),
        # ku.dk's continuing-education host is not the degree catalogue.
        (
            "https://efteruddannelse.ku.dk/uddannelser",
            "Uddannelser",
            "https://www.ku.dk/",
            "Denmark",
            None,
        ),
        ("https://phd.ku.dk/", "Ph.d.-uddannelse", "https://www.ku.dk/", "Denmark", None),
        # usp.br's www5 is the main site under another name.
        (
            "https://www5.usp.br/ensino/graduacao",
            "Graduação",
            "https://www.usp.br/",
            "Brazil",
            None,
        ),
        # An English path alone is not enough (ntu.edu.tw's course site).
        (
            "https://teach.cc.ntu.edu.tw/course",
            "1151 AI數據實戰~2026/10/15",
            "https://www.ntu.edu.tw/",
            "Taiwan",
            None,
        ),
        # Another registrable domain is DI-1's case (tsinghua -> join-tsinghua).
        (
            "https://www.join-tsinghua.edu.cn/",
            "本科专业",
            "https://www.tsinghua.edu.cn/",
            "China",
            None,
        ),
        # The homepage's own host is not a catalogue host.
        ("https://www.uc.cl/carreras", "Carreras", "https://www.uc.cl/", "Chile", None),
    ],
)
def test_catalogue_host_lead(
    r4_on, url: str, label: str, homepage: str, country: str, ranked: int | None
) -> None:
    section = study_section_label(label, country_languages(country), "bachelor")
    domain = homepage.split("/")[2]
    assert (
        LiveDiscoveryAdapter._catalogue_host_lead(url, label, section, homepage, domain, "bachelor")
        == ranked
    )


def _ingresantes_site() -> StubSite:
    return StubSite(
        {
            "https://ingresantes.exactas.uba.ar/robots.txt": fixture("ingresantes_robots.txt"),
            "https://ingresantes.exactas.uba.ar/wp-sitemap.xml": fixture(
                "ingresantes_wp_sitemap.xml"
            ),
            "https://ingresantes.exactas.uba.ar/wp-sitemap-posts-page-1.xml": fixture(
                "ingresantes_pages_sitemap.xml"
            ),
        }
    )


@pytest.mark.asyncio
async def test_the_catalogue_host_sitemap_lists_ubas_gold_in_two_documents(tmp_path, r4_on) -> None:
    """uba's catalogue host: robots.txt names wp-sitemap.xml; the page sitemap holds the gold.

    The post sitemap is news and is never read. The gold's root-level slug
    scores as nothing — that is R3's case (``SITEMAP_KEEP_EVIDENCE_SUM``), so
    with the real ``keep`` the host is read and the gold is not kept.
    """
    site = _ingresantes_site()
    trace = DiscoveryTrace(institution="UBA", domain="www.uba.ar")
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        pages = await SitemapReader(fetcher).collect_catalogue_host(
            "https://ingresantes.exactas.uba.ar/",
            "www.uba.ar",
            trace,
            lambda _u: True,
            degree="bachelor",
        )
    assert UBA_GOLD in pages
    assert len(pages) == 38
    assert trace.catalogue_host["sitemaps_read"] == [
        "https://ingresantes.exactas.uba.ar/wp-sitemap.xml",
        "https://ingresantes.exactas.uba.ar/wp-sitemap-posts-page-1.xml",
    ]
    assert "https://ingresantes.exactas.uba.ar/wp-sitemap-posts-post-1.xml" not in site.requested
    assert categorise_url(UBA_GOLD) == (None, 0)


def _five_children_site(host: str) -> tuple[StubSite, list[str]]:
    """Written for the test: a catalogue host whose index lists five programme sitemaps."""
    children = [f"{host}/programas-{n}-sitemap.xml" for n in range(5)]
    site = StubSite(
        {
            f"{host}/robots.txt": f"Sitemap: {host}/sitemap.xml\n",
            f"{host}/sitemap.xml": sitemap_index_xml(*children),
            **{child: sitemap_xml(f"{host}/carreras/p-{i}") for i, child in enumerate(children)},
        }
    )
    return site, children


@pytest.mark.asyncio
@pytest.mark.parametrize("kept", [False, True], ids=["nothing-kept", "kept"])
async def test_the_catalogue_host_reads_at_most_three_documents(
    tmp_path, r4_on, kept: bool
) -> None:
    host = "https://cat.uni.cl"
    site, children = _five_children_site(host)
    trace = DiscoveryTrace(institution="U", domain="www.uni.cl")
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        await SitemapReader(fetcher).collect_catalogue_host(
            f"{host}/carreras", "www.uni.cl", trace, lambda _u: kept, degree="bachelor"
        )
    read = trace.catalogue_host["sitemaps_read"]
    assert isinstance(read, list)
    if kept:
        # The first child that yields leads ends the host's sitemap stage.
        assert read == [f"{host}/sitemap.xml", children[0]]
    else:
        assert len(read) == live_discovery.CATALOGUE_HOST_SITEMAP_DOCUMENTS
    assert children[2] not in site.requested


# --- 4. discovery on the development cases ---------------------------------------------


def _registry(tmp_path, homepage: str, country: str) -> Path:
    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps([{"name": "U", "country": country, "city": "X", "homepage": homepage}])
    )
    return path


async def _discover(tmp_path, site: StubSite, profile, homepage: str, country: str):
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher, _registry(tmp_path, homepage, country))
        candidate = (await adapter.discover(profile))[0]
    return candidate, adapter.traces[0]


def _puc_site(*, host_sitemap: bool = True) -> StubSite:
    """uc.cl: no sitemap of its own here, the real homepage, the admissions host."""
    pages: dict[str, bytes | str] = {
        "https://www.uc.cl/robots.txt": "User-agent: *\n",
        "https://www.uc.cl/": fixture("uc_home.html"),
        "https://admision.uc.cl/carreras": fixture("admision_uc_carreras.html"),
        PUC_GOLD: gold("puc.html"),
    }
    if host_sitemap:
        pages["https://admision.uc.cl/sitemap.xml"] = fixture("admision_uc_sitemap_index.xml")
        pages["https://admision.uc.cl/carreras-sitemap.xml"] = fixture(
            "admision_uc_carreras_sitemap.xml"
        )
    return StubSite(pages)


@pytest.mark.asyncio
async def test_puc_is_listed_through_the_catalogue_hosts_own_sitemap(tmp_path, r4, profile) -> None:
    site = _puc_site()
    candidate, trace = await _discover(tmp_path, site, profile, "https://www.uc.cl/", "Chile")
    urls = [p.url for p in candidate.programs]
    if not r4:
        # The walker reads one homepage link there today, never the catalogue or its list.
        assert "https://admision.uc.cl/carreras" not in site.requested
        assert PUC_GOLD not in site.requested
        assert not any("sitemap" in url and "admision" in url for url in site.requested)
        assert urls == []
        assert trace.kept_by_link_text == []
        return
    assert ("https://admision.uc.cl/carreras", "Carreras de pregrado launch") in (
        trace.kept_by_link_text
    )
    record = trace.catalogue_host
    assert record["host"] == "admision.uc.cl"
    # The index, then the carreras child; magister, postgrado and news children unread.
    assert record["sitemaps_read"] == [
        "https://admision.uc.cl/sitemap.xml",
        "https://admision.uc.cl/carreras-sitemap.xml",
    ]
    assert "https://admision.uc.cl/magister-sitemap.xml" not in site.requested
    assert "https://admision.uc.cl/programas_postgrado-sitemap.xml" not in site.requested
    assert "https://admision.uc.cl/post-sitemap.xml" not in site.requested
    assert PUC_GOLD in urls
    budget = trace.stage_budget
    assert budget["stage_reads"]["sitemap"] <= budget["sitemap_allowance"]
    assert budget["stage_reads"]["navigation"] == 1  # the homepage; the host list was enough


@pytest.mark.asyncio
async def test_puc_is_listed_through_the_catalogue_page_when_the_host_has_no_sitemap(
    tmp_path, r4, profile
) -> None:
    site = _puc_site(host_sitemap=False)
    candidate, trace = await _discover(tmp_path, site, profile, "https://www.uc.cl/", "Chile")
    urls = [p.url for p in candidate.programs]
    if not r4:
        assert "https://admision.uc.cl/carreras" not in site.requested
        assert urls == []
        return
    assert "https://admision.uc.cl/wp-sitemap.xml" in site.requested
    assert trace.catalogue_host["sitemaps_read"] == []
    assert "https://admision.uc.cl/carreras" in site.requested
    assert PUC_GOLD in urls


def _uio_site() -> StubSite:
    return StubSite(
        {
            "https://www.uio.no/robots.txt": "User-agent: *\n",
            "https://www.uio.no/": fixture("uio_home.html"),
            # Written for the test: the /studier section page, reduced to the
            # "Finn studier" link the analysis hand-checked (§2.3).
            "https://www.uio.no/studier": (
                '<html lang="no"><head><title>Studier – Universitetet i Oslo</title></head>'
                '<body><main><a href="/studier/program/">Finn studier</a>'
                '<a href="/livet-rundt-studiene/">Livet rundt studiene</a></main></body></html>'
            ),
            "https://www.uio.no/studier/program": fixture("uio_studier_program.html"),
            UIO_GOLD: gold("uio.html"),
        }
    )


@pytest.mark.asyncio
async def test_uio_reaches_finn_studier_in_two_hops(tmp_path, r4, profile) -> None:
    site = _uio_site()
    _candidate, trace = await _discover(tmp_path, site, profile, "https://www.uio.no/", "Norway")
    if not r4:
        assert "https://www.uio.no/studier" not in site.requested
        assert UIO_GOLD not in site.requested
        return
    assert ("https://www.uio.no/studier", "Studier") in trace.kept_by_link_text
    assert ("https://www.uio.no/studier/program", "Finn studier") in trace.kept_by_link_text
    # The gold is listed and read; R2 (subject title shapes) decides its title.
    assert UIO_GOLD in site.requested
    assert any(url == UIO_GOLD for url, _verdict in trace.pages_read)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("page", "homepage", "country", "section_link"),
    [
        (
            "psaclay_home.html",
            "https://www.universite-paris-saclay.fr/",
            "France",
            ("https://www.universite-paris-saclay.fr/formation", "Choisir sa formation"),
        ),
        # uba.ar's "Carreras de Grado" is its faculty list (the catalogue is two
        # more hops away on exactas.uba.ar: Change 2's case, not this rule's).
        (
            "uba_home.html",
            "https://www.uba.ar/",
            "Argentina",
            ("https://www.uba.ar/facultades", "Carreras de Grado"),
        ),
        (
            "kuleuven_onderwijsaanbod.html",
            "https://onderwijsaanbod.kuleuven.be/",
            "Belgium",
            ("https://onderwijsaanbod.kuleuven.be/opleidingen/n", "Onderwijsaanbod 2026 - 2027"),
        ),
    ],
)
async def test_the_development_homepages_name_their_section_link(
    tmp_path, r4, profile, page: str, homepage: str, country: str, section_link: tuple[str, str]
) -> None:
    host = homepage.rstrip("/")
    site = StubSite({f"{host}/robots.txt": "User-agent: *\n", homepage: fixture(page)})
    _candidate, trace = await _discover(tmp_path, site, profile, homepage, country)
    if r4:
        assert section_link in trace.kept_by_link_text
        assert section_link[0] in site.requested
    else:
        assert trace.kept_by_link_text == []


# --- 5. negatives ----------------------------------------------------------------------


def _norwegian_news_site() -> StubSite:
    """Written for the test: a "Studier" link to a page that reads as news."""
    return StubSite(
        {
            "https://www.uni.no/robots.txt": "User-agent: *\n",
            "https://www.uni.no/": (
                '<html lang="no"><body><nav>'
                '<a href="/om/studentliv">Studier</a>'
                '<a href="/aktuelt/ny-bachelor">Ny bachelor skal styrke tilgangen på '
                "kritisk teknologikompetanse</a></nav></body></html>"
            ),
            "https://www.uni.no/om/studentliv": (
                '<html lang="no"><head><title>News and announcements – Uni</title></head>'
                '<body><main><h1>News</h1><a href="/studier/program/informatikk/">'
                "Informatikk</a></main></body></html>"
            ),
        }
    )


@pytest.mark.asyncio
async def test_a_section_link_to_a_news_page_is_dropped(tmp_path, r4_on, profile) -> None:
    site = _norwegian_news_site()
    candidate, trace = await _discover(tmp_path, site, profile, "https://www.uni.no/", "Norway")
    assert "https://www.uni.no/om/studentliv" in site.requested
    assert any(
        url == "https://www.uni.no/om/studentliv" and reason.startswith("not_program_catalog")
        for url, reason in trace.rejected
    )
    # Its links are not followed, and it is no catalogue lead.
    assert "https://www.uni.no/studier/program/informatikk" not in site.requested
    assert "https://www.uni.no/om/studentliv" not in (trace.selected.get("program_catalog") or [])
    # A headline that contains a section word is not a section link.
    assert [url for url, _label in trace.kept_by_link_text] == ["https://www.uni.no/om/studentliv"]
    assert candidate.programs == []


@pytest.mark.asyncio
async def test_an_off_domain_catalogue_is_never_read(tmp_path, r4_on, profile) -> None:
    """Written for the test: "Carreras de pregrado" on another registrable domain (20 Q4)."""
    site = StubSite(
        {
            "https://www.uni.cl/robots.txt": "User-agent: *\n",
            "https://www.uni.cl/": (
                '<html lang="es"><body><nav>'
                '<a href="https://admision.otrauniversidad.cl/carreras">Carreras de pregrado</a>'
                "</nav></body></html>"
            ),
        }
    )
    _candidate, trace = await _discover(tmp_path, site, profile, "https://www.uni.cl/", "Chile")
    assert not any("otrauniversidad" in url for url in site.requested)
    assert trace.catalogue_host == {}
    assert trace.kept_by_link_text == []


@pytest.mark.asyncio
async def test_tsinghua_follows_its_own_majors_list_not_join_tsinghua(
    tmp_path, r4_on, profile
) -> None:
    site = StubSite(
        {
            "https://www.tsinghua.edu.cn/robots.txt": "User-agent: *\n",
            "https://www.tsinghua.edu.cn/": fixture("tsinghua_home.html"),
        }
    )
    _candidate, trace = await _discover(
        tmp_path, site, profile, "https://www.tsinghua.edu.cn/", "China"
    )
    assert not any("join-tsinghua" in url for url in site.requested)
    assert trace.catalogue_host == {}
    # The catalogue word (本科专业) before the section words.
    assert trace.kept_by_link_text[0] == (
        "https://www.tsinghua.edu.cn/jyjx/bksjy/bkzy.htm",
        "本科专业",
    )
    assert len(trace.kept_by_link_text) == live_discovery.LOCAL_SECTION_LINKS_PER_PAGE


def _spanish_chain_site() -> StubSite:
    """Written for the test: homepage -> section -> section -> section, opaque URLs."""
    return StubSite(
        {
            "https://www.uni.es/robots.txt": "User-agent: *\n",
            "https://www.uni.es/": (
                '<html lang="es"><body><nav><a href="/p1">Estudios</a></nav></body></html>'
            ),
            "https://www.uni.es/p1": (
                '<html lang="es"><head><title>Estudios</title></head><body><main>'
                '<a href="/p2">Oferta académica</a></main></body></html>'
            ),
            "https://www.uni.es/p2": (
                '<html lang="es"><head><title>Oferta académica</title></head><body><main>'
                '<a href="/p3">Grados</a></main></body></html>'
            ),
            "https://www.uni.es/p3": (
                '<html lang="es"><head><title>Grados</title></head><body><main>'
                '<a href="/p4">Grado en Ingeniería Informática</a></main></body></html>'
            ),
        }
    )


@pytest.mark.asyncio
async def test_section_links_stop_after_two_hops(tmp_path, r4_on, profile) -> None:
    site = _spanish_chain_site()
    _candidate, trace = await _discover(tmp_path, site, profile, "https://www.uni.es/", "Spain")
    assert "https://www.uni.es/p1" in site.requested
    assert "https://www.uni.es/p2" in site.requested
    assert "https://www.uni.es/p3" not in site.requested
    assert [url for url, _label in trace.kept_by_link_text] == [
        "https://www.uni.es/p1",
        "https://www.uni.es/p2",
    ]
    assert trace.stage_budget["stage_reads"]["navigation"] <= live_discovery.MAX_FALLBACK_PAGES


@pytest.mark.asyncio
async def test_no_section_links_for_an_english_speaking_country(tmp_path, r4_on, profile) -> None:
    site = _spanish_chain_site()
    await _discover(tmp_path, site, profile, "https://www.uni.es/", "United Kingdom")
    assert "https://www.uni.es/p1" not in site.requested


@pytest.mark.asyncio
async def test_the_catalogue_host_waits_for_the_sitemap_allowance(
    tmp_path, r4_on, profile, monkeypatch
) -> None:
    """Its reads are sitemap reads: none once the SB-1 sitemap allowance is spent."""
    monkeypatch.setattr(live_discovery, "DISCOVERY_SITEMAP_ALLOWANCE", 2)
    site = _puc_site()
    _candidate, trace = await _discover(tmp_path, site, profile, "https://www.uc.cl/", "Chile")
    assert trace.catalogue_host["skipped"] == "discovery budget"
    assert "https://admision.uc.cl/robots.txt" not in site.requested
    assert trace.stage_budget["stage_reads"]["sitemap"] <= 2


# --- 6. harness flag -------------------------------------------------------------------


def test_harness_exposes_and_forwards_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--local-catalogue-entry" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "r4_module.LOCAL_CATALOGUE_ENTRY = True" in source
    assert '["--local-catalogue-entry"]' in source
