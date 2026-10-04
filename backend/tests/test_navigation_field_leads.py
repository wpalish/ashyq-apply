"""Experiment ER-09: a navigation lead must name the applicant's subject.

Groningen's bachelor hub links brochures, open days and campus tours under
``/education/bachelor/``; each scored as a programme page on structure alone,
filled the slots and cost a confirm read before the real programme was reached.
"""

from __future__ import annotations

import json

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    PageCategory,
)
from app.adapters.fetching import Fetcher
from tests.test_live_discovery import StubSite

HUB = (
    "<html><body><main>"
    '<a href="/education/bachelor/brochures">Brochures</a>'
    '<a href="/education/bachelor/bachelor-open-day">Open day</a>'
    '<a href="/education/bachelor/campus-tour">Campus tour</a>'
    '<a href="/education/bachelor/webklassen">Webklassen</a>'
    '<a href="/bachelors/computing-science">Computing Science</a>'
    "</main></body></html>"
)
TARGET = "https://uni.edu/bachelors/computing-science"


async def navigate(tmp_path, profile) -> tuple[list[str], DiscoveryTrace]:
    entry = {"name": "U", "country": "Netherlands", "city": "X", "homepage": "https://uni.edu/"}
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps([entry]))
    site = StubSite({"https://uni.edu/robots.txt": "User-agent: *\n", "https://uni.edu/": HUB})
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher, registry)
        selected: dict[str, list[str]] = {c: [] for c in PageCategory.ALL}
        trace = DiscoveryTrace(institution="U", domain="uni.edu")
        await adapter._navigation_fallback(entry, "uni.edu", selected, trace, profile)
    return selected[PageCategory.PROGRAM_PAGE], trace


@pytest.fixture
def cs_profile(profile):
    profile.context.intended_fields = ["computer science"]
    profile.context.level = "bachelor"
    return profile


@pytest.mark.asyncio
async def test_off_by_default_keeps_structural_leads(tmp_path, cs_profile):
    assert live_discovery.NAVIGATION_FIELD_LEADS is False
    leads, _ = await navigate(tmp_path, cs_profile)
    assert any("open-day" in u or "brochures" in u for u in leads)


@pytest.mark.asyncio
async def test_on_keeps_only_leads_naming_the_subject(tmp_path, cs_profile, monkeypatch):
    monkeypatch.setattr(live_discovery, "NAVIGATION_FIELD_LEADS", True)
    leads, trace = await navigate(tmp_path, cs_profile)
    assert leads == [TARGET], "Computing Science is the strong alias of the subject"
    assert any("names none of the applicant's subjects" in r for _, r in trace.rejected)
