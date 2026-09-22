"""EXTRA-6: the programme filter must also see what the search provider adds.

`discover` confirms programme candidates at step 4 and asks the search
provider at step 6. Until this pass existed, every programme page search
contributed reached the candidate unconfirmed — which on the benchmark cohort
is most of them. The filter's own comment says why it exists: live runs
offered "bachelor-open-day", "campus-tour" and a student newsletter as
programme pages.

The catalogue walker is deliberately *not* re-judged here: it confirms its own
candidates under the T29 contract, which trusts a university's own catalogue
listing even for a neighbouring subject. Whether that is right is an owner
question (HANDOFF §7), not something to change from underneath it.
"""

from __future__ import annotations

from typing import cast

import pytest

from app.adapters.discovery.live_discovery import LiveDiscoveryAdapter, PageCategory
from app.adapters.fetching import Fetcher, FetchOutcome, FetchResult

_PROGRAMME = """<html><head><title>BSc Computer Science</title></head><body>
<h1>BSc Computer Science</h1>
<p>This three-year bachelor's degree programme in computer science covers
programming, algorithms and systems. Entry requirements and the application
deadline are listed below.</p>
</body></html>"""

_OPEN_DAY = """<html><head><title>Bachelor open day</title></head><body>
<h1>Bachelor open day</h1>
<p>Join us on campus on 14 March to meet students and staff. Register for the
open day to visit our faculties.</p>
</body></html>"""


@pytest.fixture
def profile_bachelor(profile):
    profile.context.intended_fields = ["computer science"]
    profile.context.level = "bachelor"
    return profile


class _Site:
    """Serves fixed bodies, and records what was asked for."""

    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.requested: list[str] = []

    async def get(self, url: str, **kwargs) -> FetchResult:
        self.requested.append(url)
        body = self.pages.get(url)
        if body is None:
            return FetchResult(
                url=url, outcome=FetchOutcome.HTTP_ERROR, status_code=404, error="not served"
            )
        return FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            status_code=200,
            content=body.encode(),
            # Both, deliberately: the adapter reads `.text`, and a stub that
            # sets only `.content` makes every one of these tests pass by
            # serving an empty page.
            text=body,
            content_type="text/html",
            final_url=url,
        )


class _Fetcher:
    def __init__(self, site: _Site):
        self.get = site.get


def _adapter(site: _Site, tmp_path) -> LiveDiscoveryAdapter:
    # The stub serves the one method the confirm pass uses; the registry path
    # is deliberately absent, because this exercises the pass, not discovery.
    fetcher = cast(Fetcher, _Fetcher(site))
    return LiveDiscoveryAdapter(fetcher, registry_path=tmp_path / "missing.json")


async def _confirm(adapter, selected, already, profile):
    from app.adapters.discovery.live_discovery import DiscoveryTrace

    trace = DiscoveryTrace(institution="Test University", domain="uni.edu")
    await adapter._confirm_added_programs(selected, already, trace, profile)
    return trace


class TestWhatStepsFiveAndSixAdd:
    @pytest.mark.asyncio
    async def test_an_open_day_page_added_by_search_is_refused(self, tmp_path, profile_bachelor):
        site = _Site({"https://uni.edu/bachelor-open-day": _OPEN_DAY})
        selected = {PageCategory.PROGRAM_PAGE: ["https://uni.edu/bachelor-open-day"]}

        trace = await _confirm(_adapter(site, tmp_path), selected, set(), profile_bachelor)

        assert selected[PageCategory.PROGRAM_PAGE] == []
        assert trace.rejected, "a refusal always says why"

    @pytest.mark.asyncio
    async def test_a_real_programme_page_added_by_search_survives(self, tmp_path, profile_bachelor):
        site = _Site({"https://uni.edu/bsc-computer-science": _PROGRAMME})
        selected = {PageCategory.PROGRAM_PAGE: ["https://uni.edu/bsc-computer-science"]}

        await _confirm(_adapter(site, tmp_path), selected, set(), profile_bachelor)

        assert selected[PageCategory.PROGRAM_PAGE] == ["https://uni.edu/bsc-computer-science"]

    @pytest.mark.asyncio
    async def test_a_page_confirmed_at_step_four_is_not_read_again(
        self, tmp_path, profile_bachelor
    ):
        """The fetch budget is the binding constraint on the benchmark cohort."""
        already = "https://uni.edu/bsc-computer-science"
        site = _Site({already: _PROGRAMME})
        selected = {PageCategory.PROGRAM_PAGE: [already]}

        await _confirm(_adapter(site, tmp_path), selected, {already}, profile_bachelor)

        assert site.requested == []
        assert selected[PageCategory.PROGRAM_PAGE] == [already]

    @pytest.mark.asyncio
    async def test_a_page_that_cannot_be_read_is_kept(self, tmp_path, profile_bachelor):
        """An unreachable page is not a refusal, and losing a lead silently is
        the failure the step-4 filter already guards against."""
        site = _Site({})
        selected = {PageCategory.PROGRAM_PAGE: ["https://uni.edu/down"]}

        await _confirm(_adapter(site, tmp_path), selected, set(), profile_bachelor)

        assert selected[PageCategory.PROGRAM_PAGE] == ["https://uni.edu/down"]

    @pytest.mark.asyncio
    async def test_nothing_new_costs_no_fetch_at_all(self, tmp_path, profile_bachelor):
        site = _Site({})
        selected = {PageCategory.PROGRAM_PAGE: []}

        await _confirm(_adapter(site, tmp_path), selected, set(), profile_bachelor)

        assert site.requested == []
