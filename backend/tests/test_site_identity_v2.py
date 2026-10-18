"""v3 rule R6: production's site-identity gate, version 2 (``SITE_IDENTITY_V2``).

Plan v3 stage 0 (wayfinder programme-discovery tickets 05 Q2, 12 and 16-Q8,
owner 2026-10-18). Identity holds when any of (i) the homepage, after
redirects, is on the seed row's own host; (ii) ``<html lang>`` is a language of
the country and the title holds the row's native name (only where a record
carries one); (iii) the English name is on the homepage's English alternate,
read once, same registrable domain; (iv) today's title rule. Never on a
third-party host, a parked domain, or a homepage naming another institution.

Offline: the homepages are trimmed copies of the development universities'
own (``fixtures/site_identity_v2``, fetched 2026-10-18), served by a fake
fetcher; the provider is a fake. No network.
"""

from __future__ import annotations

import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.adapters.discovery.live_discovery import DiscoveryTrace
from app.adapters.fetching import FetchOutcome, FetchResult
from app.catalogue import discovery
from app.catalogue.discovery import CatalogueDiscoveryAdapter
from app.catalogue.importer import identity_key, import_catalogue, stable_id
from app.catalogue.retrieval import retrieve
from app.db import create_all_for_tests
from app.models import University, UniversityObservation
from evaluation.research import live
from evaluation.research.schema import Observation

FIXTURES = Path(__file__).parent / "fixtures" / "site_identity_v2"


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    create_all_for_tests(engine)
    with Session(engine) as db:
        import_catalogue(db)
        db.commit()
        yield db
    engine.dispose()


@pytest.fixture
def v2(monkeypatch):
    monkeypatch.setattr(discovery, "SITE_IDENTITY_V2", True)


class Fetcher:
    """Serves saved pages by URL; anything else is an HTTP error. Records every read."""

    def __init__(self, pages: dict[str, FetchResult]):
        self.pages = pages
        self.read: list[str] = []

    async def get(self, url: str, **kwargs: Any) -> FetchResult:
        self.read.append(url)
        return self.pages.get(url) or FetchResult(url=url, outcome=FetchOutcome.HTTP_ERROR)


def page(
    url: str,
    fixture: str = "",
    *,
    final: str = "",
    html: str = "",
    outcome: FetchOutcome = FetchOutcome.OK,
) -> FetchResult:
    content = (FIXTURES / fixture).read_bytes() if fixture else html.encode()
    return FetchResult(url=url, outcome=outcome, content=content, final_url=final)


def university(session: Session, case_id: str) -> University:
    entry = live.dev2_entry(case_id)
    uni = session.get(University, stable_id(identity_key(entry["name"], entry["country"])))
    assert uni is not None
    return uni


def without_domain(uni: University) -> University:
    """The row as a seed row without ``official_domain`` / ``official_site`` would be."""
    snapshot = deepcopy(uni.seed_snapshot or {})
    snapshot["record"]["official_domain"] = None
    snapshot["record"]["official_site"] = None
    uni.seed_snapshot = snapshot
    uni.domain = None
    return uni


def adapter(session: Session, fetcher: Fetcher, uni: University) -> CatalogueDiscoveryAdapter:
    return CatalogueDiscoveryAdapter(
        fetcher, session=session, university_ids=[uni.id], live_limit=1
    )


def proofs(session: Session, uni: University) -> list[dict]:
    rows = session.scalars(
        select(UniversityObservation).where(
            UniversityObservation.university_id == uni.id,
            UniversityObservation.seed_version == "live-site-identity",
        )
    )
    return [row.payload for row in rows]


def no_search(monkeypatch, urls: list[str] | None = None) -> SimpleNamespace:
    results = [SimpleNamespace(url=url) for url in urls or []]
    provider = SimpleNamespace(search=AsyncMock(return_value=SimpleNamespace(results=results)))
    monkeypatch.setattr("app.catalogue.discovery.get_search_provider", lambda: provider)
    return provider


# --- flag off: today's rule, byte for byte -------------------------------------


@pytest.mark.parametrize(
    "case_id,url,fixture",
    [
        ("uppsala", "https://www.uu.se/", "uppsala_home.html"),
        ("ucph", "https://www.ku.dk/", "ucph_home.html"),
        ("tsinghua", "https://www.tsinghua.edu.cn/", "tsinghua_home.html"),
        ("tcd", "https://www.tcd.ie/", "tcd_home.html"),
    ],
)
async def test_off_the_local_language_and_long_name_homepages_still_fail(
    session, case_id, url, fixture
):
    """Ticket 12's failing homepages fail as before with the rule off."""
    assert discovery.SITE_IDENTITY_V2 is False
    uni = university(session, case_id)
    fetcher = Fetcher({url: page(url, fixture)})
    gate = adapter(session, fetcher, uni)
    assert await gate._probe_site(uni, url) is None
    assert fetcher.read == [url] and gate.site_identity_proofs == {}


async def test_off_a_passing_homepage_leaves_todays_proof_unchanged(session):
    uni = university(session, "ethz")
    fetcher = Fetcher({"https://ethz.ch/": page("https://ethz.ch/", "ethz_home.html")})
    gate = adapter(session, fetcher, uni)
    assert (await gate._probe_site(uni, "https://ethz.ch/"))["homepage"] == "https://ethz.ch/"
    (proof,) = proofs(session, uni)
    assert set(proof) == {
        "kind",
        "source_url",
        "accessed_at",
        "excerpt",
        "name",
        "domain",
        "verification_status",
    }
    assert gate.site_identity_proofs == {}


async def test_off_the_msu_business_school_is_accepted_today(session):
    """The false identity of run 39110772358 rep 2 (``en.mgubs.ru``), as today's rule makes it."""
    uni = university(session, "msu")
    url = "https://en.mgubs.ru/"
    gate = adapter(session, Fetcher({url: page(url, "mgubs_home.html")}), uni)
    assert (await gate._probe_site(uni, url))["homepage"] == url


# --- (i) the seed row's own host -------------------------------------------------


@pytest.mark.parametrize(
    "case_id,url,final,fixture",
    [
        ("tcd", "https://tcd.ie/", "https://www.tcd.ie:443/", "tcd_home.html"),
        ("uppsala", "https://uu.se/", "https://www.uu.se/", "uppsala_home.html"),
        ("ucph", "https://www.ku.dk/", "", "ucph_home.html"),
        ("uio", "https://www.uio.no/", "", "uio_home.html"),
        ("tsinghua", "https://www.tsinghua.edu.cn/", "", "tsinghua_home.html"),
        # An empty SvelteKit shell: the row's host is the proof, not the page.
        ("msu", "https://www.msu.ru/", "", "msu_home.html"),
    ],
)
async def test_the_rows_own_host_establishes_identity(session, v2, case_id, url, final, fixture):
    uni = university(session, case_id)
    fetcher = Fetcher({url: page(url, fixture, final=final)})
    gate = adapter(session, fetcher, uni)
    entry = await gate._probe_site(uni, url)
    assert entry is not None and entry["homepage"] == (final or url)
    assert fetcher.read == [url]  # no further read
    assert gate.site_identity_proofs == {uni.id: "official_site"}
    (proof,) = proofs(session, uni)
    assert proof["proof"] == "official_site" and proof["source_url"] == (final or url)
    assert uni.domain_status == "site_identity_checked"


async def test_the_rows_registrable_domain_is_not_its_host(session, v2):
    """IIT Delhi's row says ``iitd.ernet.in``; ``ernet.in`` (the network operator) is not it."""
    uni = university(session, "iitd")
    assert uni.domain == "ernet.in"
    html = "<html lang='en'><title>ERNET India</title><h1>Welcome to ERNET</h1></html>"
    fetcher = Fetcher({"https://ernet.in/": page("https://ernet.in/", html=html)})
    assert await adapter(session, fetcher, uni)._probe_site(uni, "https://ernet.in/") is None


async def test_a_redirect_off_the_rows_host_establishes_nothing(session, v2):
    uni = university(session, "ucph")
    url = "https://www.ku.dk/"
    fetcher = Fetcher({url: page(url, "ucph_home.html", final="https://www.parked.example/")})
    assert await adapter(session, fetcher, uni)._probe_site(uni, url) is None


async def test_a_parked_domain_on_the_rows_host_establishes_nothing(session, v2):
    uni = university(session, "uio")
    url = "https://www.uio.no/"
    fetcher = Fetcher({url: page(url, "parked_domain.html")})
    gate = adapter(session, fetcher, uni)
    assert await gate._probe_site(uni, url) is None
    assert proofs(session, uni) == [] and gate.site_identity_proofs == {}


async def test_the_rows_host_naming_another_institution_establishes_nothing(session, v2):
    uni = retrieve(session, query="Massachusetts Institute")[0]
    html = "<title>University directory</title><h1>Find a university</h1>"
    fetcher = Fetcher({"https://mit.edu/": page("https://mit.edu/", html=html)})
    assert await adapter(session, fetcher, uni)._probe_site(uni, "https://mit.edu/") is None
    # The same row's own host naming itself passes.
    named = "<title>Massachusetts Institute of Technology</title>"
    fetcher = Fetcher({"https://mit.edu/": page("https://mit.edu/", html=named)})
    assert await adapter(session, fetcher, uni)._probe_site(uni, "https://mit.edu/")


# --- (ii) the native name, where a record carries one ------------------------------


def with_native_name(uni: University, native: str) -> University:
    uni = without_domain(uni)
    snapshot = deepcopy(uni.seed_snapshot or {})
    snapshot["record"]["native_name"] = native
    uni.seed_snapshot = snapshot
    return uni


async def test_a_native_name_under_the_countrys_lang_establishes_identity(session, v2):
    uni = with_native_name(university(session, "utokyo"), "東京大学")
    url = "https://www.u-tokyo.ac.jp/"
    final = "https://www.u-tokyo.ac.jp/ja/index.html"
    fetcher = Fetcher({url: page(url, "utokyo_home.html", final=final)})
    gate = adapter(session, fetcher, uni)
    assert (await gate._probe_site(uni, url))["homepage"] == final
    assert fetcher.read == [url]  # no English alternate read
    assert gate.site_identity_proofs == {uni.id: "native_name"}


async def test_a_native_name_needs_the_countrys_language(session, v2):
    """National Taiwan University's native name under Japanese ``<html lang>`` proves nothing."""
    uni = with_native_name(university(session, "ntutw"), "國立臺灣大學")
    url = "https://www.ntu.edu.tw/"
    html = (FIXTURES / "ntutw_home.html").read_text().replace('lang="zh-Hant-TW"', 'lang="ja"')
    fetcher = Fetcher({url: page(url, html=html)})
    gate = adapter(session, fetcher, uni)
    # Not native_name; the English alternate is then read and decides.
    assert await gate._probe_site(uni, url) is None
    assert fetcher.read == [url, "https://www.ntu.edu.tw/english/"]


async def test_no_record_carries_a_native_name_today(session):
    """16-Q8: branch (ii) is built, and fires on no seed row until the data task lands."""
    rows = session.scalars(select(University)).all()
    assert not any(((u.seed_snapshot or {}).get("record") or {}).get("native_name") for u in rows)


# --- (iii) the English alternate, read once ---------------------------------------


@pytest.mark.parametrize(
    "case_id,url,final,fixture,alternate,english,via",
    [
        (
            "utokyo",
            "https://www.u-tokyo.ac.jp/",
            "https://www.u-tokyo.ac.jp/ja/index.html",
            "utokyo_home.html",
            "https://www.u-tokyo.ac.jp/en/index.html",
            "utokyo_en.html",
            "language_link",
        ),
        (
            "ntutw",
            "https://www.ntu.edu.tw/",
            "",
            "ntutw_home.html",
            "https://www.ntu.edu.tw/english/",
            "ntutw_en.html",
            "language_link",
        ),
        (
            "tsinghua",
            "https://www.tsinghua.edu.cn/",
            "",
            "tsinghua_home.html",
            "https://www.tsinghua.edu.cn/en/",
            "tsinghua_en.html",
            "language_link",
        ),
        (
            "uio",
            "https://www.uio.no/",
            "",
            "uio_home.html",
            "https://www.uio.no/english/",
            "uio_en.html",
            "language_link",
        ),
        (
            "ucph",
            "https://www.ku.dk/",
            "",
            "ucph_home.html",
            "https://www.ku.dk/en",
            "ucph_en.html",
            "hreflang",
        ),
        (
            "uppsala",
            "https://www.uu.se/",
            "",
            "uppsala_home.html",
            "https://www.uu.se/en",
            "uppsala_en.html",
            "hreflang",
        ),
    ],
)
async def test_the_english_alternate_establishes_identity(
    session, v2, case_id, url, final, fixture, alternate, english, via
):
    """A site reached without the row's host (the provider fallback): the English page decides."""
    uni = without_domain(university(session, case_id))
    fetcher = Fetcher({url: page(url, fixture, final=final), alternate: page(alternate, english)})
    gate = adapter(session, fetcher, uni)
    assert (await gate._probe_site(uni, url))["homepage"] == (final or url)
    assert fetcher.read == [url, alternate]  # one read beyond the homepage
    assert gate.site_identity_proofs == {uni.id: "english_alternate"}
    (proof,) = proofs(session, uni)
    assert proof["english_alternate"]["url"] == alternate
    assert proof["english_alternate"]["via"] == via


async def test_an_english_alternate_off_the_registrable_domain_is_not_read(session, v2):
    uni = without_domain(university(session, "ucph"))
    url = "https://www.ku.dk/"
    html = (
        "<html lang='da'><title>Københavns Universitet</title>"
        "<link rel='alternate' hreflang='en' href='https://ucph-english.example.com/'></html>"
    )
    fetcher = Fetcher({url: page(url, html=html)})
    assert await adapter(session, fetcher, uni)._probe_site(uni, url) is None
    assert fetcher.read == [url]


async def test_an_english_alternate_robots_refuses_is_not_retried(session, v2):
    uni = without_domain(university(session, "uppsala"))
    url, alternate = "https://www.uu.se/", "https://www.uu.se/en"
    refused = page(alternate, outcome=FetchOutcome.ROBOTS_DISALLOWED)
    fetcher = Fetcher({url: page(url, "uppsala_home.html"), alternate: refused})
    assert await adapter(session, fetcher, uni)._probe_site(uni, url) is None
    assert fetcher.read == [url, alternate]


# --- (iv) today's rule, with the English name's leading article -------------------


async def test_auckland_is_named_without_its_leading_article(session, v2):
    """Seed "The University of Auckland"; the title says "University of Auckland"."""
    uni = university(session, "auckland")
    url, final = "https://www.auckland.ac.nz/", "https://www.auckland.ac.nz/en.html"
    fetcher = Fetcher({url: page(url, "auckland_home.html", final=final)})
    gate = adapter(session, fetcher, uni)
    assert (await gate._probe_site(uni, url))["homepage"] == final
    assert gate.site_identity_proofs == {uni.id: "title_name"}


@pytest.mark.parametrize(
    "case_id,url,fixture",
    [
        ("khalifa", "https://www.ku.ac.ae/", "khalifa_home.html"),
        ("uct", "https://uct.ac.za/", "uct_home.html"),
        ("unsw", "https://www.unsw.edu.au/", "unsw_home.html"),
    ],
)
async def test_todays_passing_homepages_still_pass(session, v2, case_id, url, fixture):
    uni = university(session, case_id)
    fetcher = Fetcher({url: page(url, fixture)})
    assert (await adapter(session, fetcher, uni)._probe_site(uni, url))["homepage"] == url


# --- the precision guard ----------------------------------------------------------


async def test_iit_delhi_still_fails_on_its_short_title(session, v2):
    """Its row's host is unreadable; the site search finds says "IIT Delhi", not the seed name."""
    uni = university(session, "iitd")
    url, final = "https://www.iitd.ac.in/", "https://home.iitd.ac.in/"
    fetcher = Fetcher({url: page(url, "iitd_home.html", final=final)})
    assert await adapter(session, fetcher, uni)._probe_site(uni, url) is None


@pytest.mark.parametrize(
    "case_id,url,fixture,alternate,english",
    [
        # A different university with a similar name: OsloMet for the University of Oslo.
        (
            "uio",
            "https://www.oslomet.no/",
            "oslomet_home.html",
            "https://www.oslomet.no/en",
            "oslomet_en.html",
        ),
        # Another campus with the same short name: IIT Delhi - Abu Dhabi for IIT Delhi.
        ("iitd", "https://iitdabudhabi.ac.ae/", "iitd_abu_dhabi_home.html", "", ""),
        # A unit of ours on its own domain: the MSU Business School for Moscow State University.
        ("msu", "https://en.mgubs.ru/", "mgubs_home.html", "", ""),
    ],
)
async def test_a_similar_name_is_not_our_site(
    session, v2, case_id, url, fixture, alternate, english
):
    uni = university(session, case_id)
    pages = {url: page(url, fixture)}
    if alternate:
        pages[alternate] = page(alternate, english)
    gate = adapter(session, Fetcher(pages), uni)
    assert await gate._probe_site(uni, url) is None
    assert gate.site_identity_proofs == {} and proofs(session, uni) == []


@pytest.mark.parametrize(
    "url,fixture",
    [
        ("https://en.wikipedia.org/", "wikipedia_home.html"),
        ("https://studyinsweden.se/", "studyinsweden_home.html"),
        ("https://www.topuniversities.com/", ""),
        ("https://www.facebook.com/", ""),
    ],
)
async def test_an_aggregator_host_is_never_read(session, v2, url, fixture):
    """Even a third-party homepage that names the university is not its site."""
    uni = university(session, "uppsala")
    html = "<html lang='en'><title>Uppsala University - Study in Sweden</title></html>"
    fetcher = Fetcher({url: page(url, fixture) if fixture else page(url, html=html)})
    assert await adapter(session, fetcher, uni)._probe_site(uni, url) is None
    assert fetcher.read == []


async def test_off_an_aggregator_naming_the_university_passes_today(session):
    """Why the host guard is needed: today's rule reads the page and accepts it."""
    uni = university(session, "uppsala")
    url = "https://studyinsweden.se/"
    html = "<html lang='en'><title>Uppsala University - Study in Sweden</title></html>"
    gate = adapter(session, Fetcher({url: page(url, html=html)}), uni)
    assert await gate._probe_site(uni, url) is not None


# --- the whole gate ------------------------------------------------------------------


async def test_khalifa_through_the_fallback_skips_the_encyclopaedia(session, v2, monkeypatch):
    """The row's stale host is robots-refused; the provider's third-party result is not read."""
    uni = university(session, "khalifa")
    no_search(
        monkeypatch, ["https://en.wikipedia.org/wiki/Khalifa_University", "https://www.ku.ac.ae/x"]
    )
    refused = FetchOutcome.ROBOTS_DISALLOWED
    fetcher = Fetcher(
        {
            "https://kustar.ac.ae/": page("https://kustar.ac.ae/", outcome=refused),
            "https://www.kustar.ac.ae/": page("https://www.kustar.ac.ae/", outcome=refused),
            "https://www.ku.ac.ae/": page("https://www.ku.ac.ae/", "khalifa_home.html"),
        }
    )
    gate = adapter(session, fetcher, uni)
    trace = DiscoveryTrace(institution=uni.name, domain=uni.domain or "")
    entry = await gate._identify_site(uni, trace)
    assert entry is not None and entry["homepage"] == "https://www.ku.ac.ae/"
    assert fetcher.read == [
        "https://kustar.ac.ae/",
        "https://www.kustar.ac.ae/",
        "https://www.ku.ac.ae/",
    ]
    assert gate.site_identity_proofs == {uni.id: "title_name"}


async def test_the_row_host_answers_before_the_provider_is_asked(session, v2, monkeypatch):
    provider = no_search(monkeypatch, ["https://en.mgubs.ru/"])
    uni = university(session, "msu")
    fetcher = Fetcher(
        {
            "https://msu.ru/": page("https://msu.ru/", "msu_home.html"),
            "https://en.mgubs.ru/": page("https://en.mgubs.ru/", "mgubs_home.html"),
        }
    )
    gate = adapter(session, fetcher, uni)
    trace = DiscoveryTrace(institution=uni.name, domain=uni.domain or "")
    assert (await gate._identify_site(uni, trace))["homepage"] == "https://msu.ru/"
    assert fetcher.read == ["https://msu.ru/"]
    provider.search.assert_not_awaited()


# --- the benchmark --------------------------------------------------------------------


async def test_the_gate_arm_records_the_branch_that_fired(tmp_path, monkeypatch, session, v2):
    from scripts import canary_discovery as canary

    no_search(monkeypatch)
    fetcher = Fetcher({"https://uu.se/": page("https://uu.se/", "uppsala_home.html")})

    async def fake_canary(selector, verbose, batch=None, *, entries=None, **kwargs):
        canary._install_identified_sites(session, entries, establish=False)
        uni = university(session, "uppsala")
        trace = DiscoveryTrace(institution=uni.name, domain=uni.domain or "")
        await adapter(session, fetcher, uni)._identify_site(uni, trace)
        return {"institutions": [{"programs": []}], "run_error": ""}

    monkeypatch.setattr(canary, "run_canary", fake_canary)
    output = tmp_path / "uppsala.json"
    await live.capture_one("uppsala", output, 4, through_identity_gate=True)
    identity = Observation.model_validate_json(output.read_text()).site_identity
    assert identity is not None
    assert (identity.established, identity.homepage, identity.proof) == (
        True,
        "https://uu.se/",
        "official_site",
    )


def test_the_benchmark_flag_reaches_the_child_and_turns_the_rule_on(tmp_path, monkeypatch):
    monkeypatch.setattr(discovery, "SITE_IDENTITY_V2", False)
    argv = ["live", "--live", "--case", "uio", "--out", str(tmp_path), "--site-identity-v2"]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    commands: list[list[str]] = []

    def child(command, **kwargs):
        commands.append(command)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="uio").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    assert "--site-identity-v2" in commands[0]

    seen: list[bool] = []

    async def capture(case_id, output, max_pages, seconds, **kwargs):
        seen.append(discovery.SITE_IDENTITY_V2)

    monkeypatch.setattr(live, "capture_one", capture)
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "none")
    child_argv = ["live", "--live", "--child", "--case", "uio", "--out", str(tmp_path / "o.json")]
    monkeypatch.setattr(sys, "argv", [*child_argv, "--site-identity-v2"])
    live.main()
    assert seen == [True]
