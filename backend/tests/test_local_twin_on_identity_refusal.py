"""Plan v3 change #2(a): R1's local twin is read only after an identity refusal.

R1 read the twin in the institution's language of every refused English page.
A page refused for its kind ("reads as unknown, not a programme page") has a
twin of the same kind: on the r5 ON arm kit spent 3 of its 8 recovery reads,
rwth 3-4, puc 1 and ctu 1 on such twins (loss stages v3 2026-10-18 §5 #2).
With ``LOCAL_TWIN_ON_IDENTITY_REFUSAL`` on, only a page refused on its subject
or degree level has its twin read. Offline: every page is written for the test.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters import page_classifier
from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    is_identity_refusal,
    local_twin_wanted,
    profile_rejects,
)
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import classify_page
from app.adapters.search.retrieval import RankedCandidate
from tests.test_live_discovery import StubSite, sitemap_xml
from tests.test_localized_page_identity import (
    ENGLISH_STUB,
    NORWEGIAN,
    _discover,
    english_stub,
    norwegian_page,
)

BACKEND = Path(__file__).resolve().parents[1]
CS = ["computer science"]
#: An English page that is no programme page (its URL scores as one), with a
#: Norwegian twin.
CONTACT = "https://www.uni.no/english/study/programmes/office-hours"
KONTAKT = "https://www.uni.no/studier/kontakt"


def contact_page() -> str:
    return (
        '<html lang="en"><head><title>Contact the study office</title>'
        f'<link rel="alternate" hreflang="nb" href="{KONTAKT}"></head><body><main>'
        "<h1>Contact the study office</h1><p>Opening hours, telephone and the address of "
        "the reception desk.</p></main></body></html>"
    )


def kontakt_page() -> str:
    return (
        '<html lang="nb"><head><title>Kontakt studieavdelingen</title></head><body><main>'
        "<h1>Kontakt studieavdelingen</h1><p>Åpningstider, telefon og adresse.</p>"
        "</main></body></html>"
    )


@pytest.fixture
def r1_on(monkeypatch) -> None:
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", True)
    monkeypatch.setattr(page_classifier, "LEXICON_V2", False)
    monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)


@pytest.fixture(params=[False, True], ids=["off", "on"])
def tw1(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "LOCAL_TWIN_ON_IDENTITY_REFUSAL", request.param)
    return request.param


def test_flag_is_off_by_default() -> None:
    assert live_discovery.LOCAL_TWIN_ON_IDENTITY_REFUSAL is False


def _verdict(url: str, html: str) -> str | None:
    page = classify_page(url=url, html=html)
    return profile_rejects(page, "bachelor", CS, url=url, country="Norway")


def test_identity_refusals_are_subject_and_level(r1_on) -> None:
    subject = _verdict(ENGLISH_STUB, english_stub())
    kind = _verdict(CONTACT, contact_page())
    assert subject is not None and subject.startswith("page subject ")
    assert kind is not None and kind.startswith("reads as ")
    assert is_identity_refusal(subject)
    assert not is_identity_refusal(kind)
    for verdict in (
        "page names degree level master, not bachelor",
        "page names an integrated master's (master level), not bachelor",
        "page subject 'Business Informatics' names a related programme, not ['cs']",
    ):
        assert is_identity_refusal(verdict), verdict
    not_identity: tuple[str | None, ...] = (
        None,
        "",
        "reads as navigation, not a programme page",
        "page names a campus abroad (dubai), not the institution's own",
        "no privacy-safe requested subject to confirm",
    )
    for other in not_identity:
        assert not is_identity_refusal(other), other


def test_local_twin_wanted(tw1) -> None:
    assert local_twin_wanted(None) is False
    assert local_twin_wanted("page subject 'X' does not match requested fields ['y']") is True
    assert local_twin_wanted("reads as unknown, not a programme page") is (not tw1)


def _site() -> StubSite:
    return StubSite(
        {
            "https://www.uni.no/robots.txt": "Sitemap: https://www.uni.no/s.xml\n",
            "https://www.uni.no/s.xml": sitemap_xml(ENGLISH_STUB),
            ENGLISH_STUB: english_stub(),
            NORWEGIAN: norwegian_page(),
        }
    )


@pytest.mark.asyncio
async def test_confirm_a_subject_refusal_still_reads_its_twin(tmp_path, r1_on, tw1, profile):
    site = _site()
    candidate, trace = await _discover(tmp_path, site, profile)
    assert site.requested.index(NORWEGIAN) == site.requested.index(ENGLISH_STUB) + 1
    assert NORWEGIAN in [p.url for p in candidate.programs]
    assert f"hreflang: reading the local alternate of {ENGLISH_STUB}" in trace.errors


@pytest.mark.asyncio
async def test_confirm_stage_a_kind_refusal_reads_its_twin_only_off(tmp_path, r1_on, tw1, profile):
    site = StubSite(
        {
            "https://www.uni.no/robots.txt": "Sitemap: https://www.uni.no/s.xml\n",
            "https://www.uni.no/s.xml": sitemap_xml(CONTACT),
            CONTACT: contact_page(),
            KONTAKT: kontakt_page(),
        }
    )
    _candidate, trace = await _discover(tmp_path, site, profile)
    assert CONTACT in site.requested
    assert (KONTAKT in site.requested) is (not tw1)
    assert (f"hreflang: reading the local alternate of {CONTACT}" in trace.errors) is (not tw1)


async def _recover(tmp_path, profile, pages: dict[str, bytes | str], urls: list[str]):
    profile.context.intended_fields = ["computer science"]
    site = StubSite(pages)
    trace = DiscoveryTrace(institution="U", domain="uni.no", country="Norway")
    found: list[str] = []
    candidates = [RankedCandidate(u, "Computer Science", 1, "fake") for u in urls]
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages(candidates, found, trace, profile)
    return found, trace, site.requested


@pytest.mark.asyncio
async def test_recovery_a_kind_refusal_reads_its_twin_only_off(tmp_path, r1_on, tw1, profile):
    _found, trace, requested = await _recover(
        tmp_path,
        profile,
        {CONTACT: contact_page(), KONTAKT: kontakt_page()},
        [CONTACT],
    )
    assert CONTACT in requested
    assert (KONTAKT in requested) is (not tw1)
    assert (f"hreflang: reading the local alternate of {CONTACT}" in trace.errors) is (not tw1)


@pytest.mark.asyncio
async def test_recovery_a_subject_refusal_reads_its_twin_either_way(tmp_path, r1_on, tw1, profile):
    found, trace, requested = await _recover(
        tmp_path,
        profile,
        {ENGLISH_STUB: english_stub(), NORWEGIAN: norwegian_page()},
        [ENGLISH_STUB],
    )
    assert requested.index(NORWEGIAN) == requested.index(ENGLISH_STUB) + 1
    assert found == [NORWEGIAN]
    assert f"hreflang: reading the local alternate of {ENGLISH_STUB}" in trace.errors


def test_harness_exposes_and_forwards_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--local-twin-on-identity-refusal" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "tw1_module.LOCAL_TWIN_ON_IDENTITY_REFUSAL = True" in source
    assert '["--local-twin-on-identity-refusal"]' in source
