"""Plan rule UC-1: service pages under a level segment, and a level guard for them.

Evidence analysis 2026-10-17 §0 cause 4 / §2.3: TCD's
``/courses/undergraduate/fees`` scored as a programme lead (9 against costs 4)
and ``/courses/postgraduate/how-to-apply`` became the bachelor applicant's
admissions page in 12 of 12 repetitions. Offline: every document is a stub.
"""

from __future__ import annotations

import json

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    LiveDiscoveryAdapter,
    PageCategory,
    categorise_url,
    label_names_other_level,
    service_category,
)
from app.adapters.fetching import Fetcher
from tests.test_live_discovery import StubSite, sitemap_xml

UG_FEES = "https://www.tcd.ie/courses/undergraduate/fees"
PG_FEES = "https://www.tcd.ie/courses/postgraduate/fees"
UG_APPLY = "https://www.tcd.ie/courses/undergraduate/how-to-apply"
PG_APPLY = "https://www.tcd.ie/courses/postgraduate/how-to-apply"


@pytest.fixture
def uc1(monkeypatch):
    monkeypatch.setattr(live_discovery, "SERVICE_PAGE_PRIORITY", True)


@pytest.fixture
def uc1_off(monkeypatch):
    monkeypatch.setattr(live_discovery, "SERVICE_PAGE_PRIORITY", False)


@pytest.fixture
def profile_bachelor(profile):
    profile.context.intended_fields = ["computer science"]
    return profile


def test_off_undergraduate_fees_is_a_programme_lead(uc1_off, monkeypatch):
    # Pins the pre-#2b ranking: fee/entry sub-pages still score as programme pages.
    monkeypatch.setattr("app.adapters.discovery.live_discovery.FEE_SUBPAGE_EXCLUSION", False)
    assert categorise_url("https://www.tcd.ie/courses/undergraduate/fees")[0] == (
        PageCategory.PROGRAM_PAGE
    )


def test_on_undergraduate_fees_is_the_cost_page(uc1):
    assert categorise_url("https://www.tcd.ie/courses/undergraduate/fees")[0] == PageCategory.COSTS
    assert categorise_url(UG_APPLY)[0] == PageCategory.ADMISSIONS
    assert categorise_url("https://u.edu/study/bachelor/scholarships.html")[0] == (
        PageCategory.SCHOLARSHIPS
    )
    # A programme slug is still a programme.
    assert categorise_url("https://www.tcd.ie/courses/undergraduate/computer-science/")[0] == (
        PageCategory.PROGRAM_PAGE
    )


@pytest.mark.parametrize(
    ("url", "category"),
    [
        ("https://u.edu/undergraduate/tuition-fees/", PageCategory.COSTS),
        ("https://u.edu/undergraduate/key-dates", PageCategory.ADMISSIONS),
        ("https://u.edu/bachelors/entry-requirements.html", PageCategory.ADMISSIONS),
        ("https://u.edu/undergraduate/funding", PageCategory.SCHOLARSHIPS),
        ("https://u.edu/undergraduate/computer-science", None),
        ("https://u.edu/news/fees", None),
    ],
)
def test_service_category_reads_the_last_segment(url, category):
    assert service_category(url) == category


def test_label_guard():
    assert label_names_other_level("Postgraduate fees", "bachelor")
    assert not label_names_other_level("Undergraduate fees", "bachelor")
    assert label_names_other_level("Undergraduate fees", "master")


def _entry() -> dict:
    return {
        "name": "Trinity College Dublin",
        "country": "Ireland",
        "city": "Dublin",
        "homepage": "https://www.tcd.ie/",
    }


async def _discover(tmp_path, profile, *urls: str):
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps([_entry()]))
    site = StubSite(
        {
            "https://www.tcd.ie/robots.txt": "Sitemap: https://www.tcd.ie/s.xml\n",
            "https://www.tcd.ie/s.xml": sitemap_xml(*urls),
        }
    )
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher, registry)
        candidate = (await adapter.discover(profile))[0]
    return candidate, adapter.traces[0]


@pytest.mark.asyncio
async def test_off_the_postgraduate_apply_page_is_the_admissions_page(
    tmp_path, profile_bachelor, uc1_off, monkeypatch
):
    # Pins the pre-#2b ranking: fee/entry sub-pages still score as programme pages.
    monkeypatch.setattr("app.adapters.discovery.live_discovery.FEE_SUBPAGE_EXCLUSION", False)
    candidate, _ = await _discover(tmp_path, profile_bachelor, PG_APPLY, UG_FEES)
    assert candidate.admissions_url == PG_APPLY
    assert candidate.costs_url is None


@pytest.mark.asyncio
async def test_on_postgraduate_apply_page_never_fills_a_bachelor_slot(
    tmp_path, profile_bachelor, uc1
):
    candidate, trace = await _discover(tmp_path, profile_bachelor, PG_APPLY, PG_FEES)
    assert candidate.admissions_url is None
    assert candidate.costs_url is None
    assert PG_APPLY not in trace.selected.get(PageCategory.ADMISSIONS, [])


@pytest.mark.asyncio
async def test_on_undergraduate_apply_and_fee_pages_are_chosen(tmp_path, profile_bachelor, uc1):
    candidate, trace = await _discover(
        tmp_path,
        profile_bachelor,
        PG_APPLY,
        "https://www.tcd.ie/admissions",
        UG_APPLY,
        PG_FEES,
        UG_FEES,
    )
    assert candidate.admissions_url == UG_APPLY
    assert candidate.costs_url == UG_FEES
    assert PG_APPLY not in trace.selected[PageCategory.ADMISSIONS]
    assert PG_FEES not in trace.selected[PageCategory.COSTS]
    assert UG_FEES not in trace.selected.get(PageCategory.PROGRAM_PAGE, [])
