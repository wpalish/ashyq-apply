"""Plan rule QB-1: discovery leaves queries for topic and award search.

Discovery sent all six query families and stopped only on HTTP 429, so under
the shared budget (BL-1) topic search was left ``6 - 6 - 1`` queries and never
ran on a site with no seeds. With QB-1 on, the first three families go out,
their candidates are read and confirmed, and the other three are sent only if
no programme page was confirmed by then.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters.base import AdapterResult, Candidate, CandidateProgram
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    PageCategory,
)
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.search import intent as intent_module
from app.adapters.search.base import SearchResponse, SearchResult, SearchUnavailable
from app.adapters.search.intent import DiscoveryIntent, queries_for
from app.domain.enums import DegreeLevel, FetchOutcome
from app.schemas.profile import ApplicantProfileIn
from tests.test_live_discovery import program_html

NAME = "University of Groningen"
DOMAIN = "www.rug.nl"
FIELD = "Computer Science"
PROGRAMME = "https://www.rug.nl/bachelors/computing-science"
EVENT_PAGE = "https://www.rug.nl/fse/computer-science-day"
MISSING_REGISTRY = Path("/nonexistent-institution-registry.json")


def profile() -> ApplicantProfileIn:
    return ApplicantProfileIn.model_validate(
        {
            "context": {
                "level": "bachelor",
                "intended_fields": [FIELD],
                "intake_year": 2027,
                "citizenship": "KZ",
                "country_of_residence": "KZ",
                "education_country": "KZ",
                "education_system": "KZ",
            }
        }
    )


def planned_queries() -> list[str]:
    """The six discovery queries, as discovery renders them for this site."""
    discovery = DiscoveryIntent(
        institution=NAME, domain="rug.nl", degree=DegreeLevel.BACHELOR, field=FIELD
    )
    return [query.text for query in queries_for(discovery)]


class Provider:
    """Counts queries; the n-th query returns ``answers(n)``."""

    name = "fake"

    def __init__(self, answers, *, fail_with: int | None = None) -> None:
        self.answers = answers
        self.fail_with = fail_with
        self.queries: list[str] = []

    async def search(self, *, query, domains=(), max_results=10):
        self.queries.append(query)
        if self.fail_with is not None:
            raise SearchUnavailable("refused", http_status=self.fail_with)
        now = datetime.now(UTC)
        return SearchResponse(
            query=query,
            provider=self.name,
            retrieved_at=now,
            results=tuple(
                SearchResult(
                    url=url,
                    title="BSc Computer Science",
                    provider=self.name,
                    rank=i + 1,
                    retrieved_at=now,
                )
                for i, url in enumerate(self.answers(len(self.queries)))
            ),
        )


class Fetcher:
    """Serves fixed bodies; anything else is a 404. Records every read."""

    refused_hosts: dict = {}  # noqa: RUF012 - read-only test double

    def __init__(self, pages: dict[str, str]) -> None:
        self.pages = pages
        self.read: list[str] = []

    async def get(self, url):
        self.read.append(url)
        body = self.pages.get(url)

        class _Result:
            ok = body is not None
            text = body or ""
            final_url = url
            outcome = FetchOutcome.OK if body is not None else FetchOutcome.HTTP_ERROR

        return _Result()


PAGES = {
    PROGRAMME: program_html("BSc Computing Science"),
    EVENT_PAGE: "<html><head><title>Event</title></head><body><h1>Computer science "
    "day</h1><p>Join us for talks and demos on campus.</p></body></html>",
}


def adapter(provider: Provider, fetcher: Fetcher) -> LiveDiscoveryAdapter:
    built = LiveDiscoveryAdapter(fetcher, registry_path=MISSING_REGISTRY)  # type: ignore[arg-type]
    built._search_provider = provider
    built._search_provider_resolved = True
    return built


def empty_selected(pages=()) -> dict[str, list[str]]:
    return {
        category: (list(pages) if category is PageCategory.PROGRAM_PAGE else [])
        for category in PageCategory.ALL
    }


@pytest.fixture
def reserve(monkeypatch):
    monkeypatch.setattr(intent_module, "DISCOVERY_QUERY_RESERVE", True)
    monkeypatch.setattr(intent_module, "SHARED_QUERY_BUDGET", True)


async def search(provider, fetcher, *, pages=(), slots_confirmed=False):
    trace = DiscoveryTrace(institution=NAME, domain=DOMAIN)
    selected = empty_selected(pages)
    await adapter(provider, fetcher)._add_search_results(
        {"name": NAME}, DOMAIN, selected, trace, profile(), slots_confirmed=slots_confirmed
    )
    return selected, trace


def test_off_by_default():
    assert intent_module.DISCOVERY_QUERY_RESERVE is False
    assert intent_module.DISCOVERY_FIRST_PASS_QUERIES == 3


async def test_a_programme_confirmed_by_the_first_three_families_leaves_three_queries(
    reserve, monkeypatch
):
    """(a) Three queries unspent, and topic search then runs on them."""
    provider = Provider(lambda n: [PROGRAMME])
    fetcher = Fetcher(PAGES)
    selected, trace = await search(provider, fetcher)

    assert provider.queries == planned_queries()[:3]
    assert selected[PageCategory.PROGRAM_PAGE] == [PROGRAMME]
    assert trace.search_queries_sent == 3
    assert trace.discovery_query_passes == [3]
    assert trace.as_dict()["discovery_query_passes"] == [3]
    assert any("QB-1: 3 discovery queries left" in line for line in trace.errors)

    candidate = Candidate(name=NAME, country="Netherlands", city="Groningen", domain=DOMAIN)
    adapter(provider, fetcher)._apply(candidate, selected, profile(), trace)
    assert candidate.search_queries_used == 3

    from app.adapters import search as search_package

    topic = Provider(lambda n: [f"https://www.rug.nl/topic-{n}"])
    monkeypatch.setattr(search_package, "get_search_provider", lambda: topic)
    program = CandidateProgram(
        name="Computing Science", field=FIELD, degree=DegreeLevel.BACHELOR, url=PROGRAMME
    )
    found = await WebRequirementsAdapter(None, "2027/28")._find_topic_pages(  # type: ignore[arg-type]
        candidate, program, AdapterResult()
    )
    # 6 - 3 (discovery) - 1 (kept for the award search) = 2 topic queries.
    assert [name for name, _ in found] == ["english", "fees"]
    assert len(topic.queries) == 2
    assert candidate.search_queries_used == 5


async def test_no_programme_after_three_families_sends_the_other_three(reserve):
    """(b) The second pass sends only the families the first did not."""
    provider = Provider(lambda n: [EVENT_PAGE] if n <= 3 else [EVENT_PAGE, PROGRAMME])
    fetcher = Fetcher(PAGES)
    selected, trace = await search(provider, fetcher)

    assert provider.queries == planned_queries()
    assert len(provider.queries) == 6
    assert trace.discovery_query_passes == [3, 3]
    assert trace.search_queries_sent == 6
    assert selected[PageCategory.PROGRAM_PAGE] == [PROGRAMME]
    # The page the first pass rejected is not read a second time.
    assert fetcher.read.count(EVENT_PAGE) == 1


async def test_flag_off_sends_todays_six_families(monkeypatch):
    """(c) Off: one pass of all six families, whatever the first three found."""
    monkeypatch.setattr(intent_module, "DISCOVERY_QUERY_RESERVE", False)
    provider = Provider(lambda n: [PROGRAMME])
    selected, trace = await search(provider, Fetcher(PAGES))

    assert provider.queries == planned_queries()
    assert trace.search_queries_sent == 6
    assert trace.discovery_query_passes == []
    assert "discovery_query_passes" not in trace.as_dict()
    assert selected[PageCategory.PROGRAM_PAGE] == [PROGRAMME]


async def test_a_page_the_confirm_stage_accepted_counts_as_confirmed(reserve):
    """Search after confirm and the walker: a page already in a slot was read and accepted."""
    provider = Provider(lambda n: [EVENT_PAGE])
    already = "https://www.rug.nl/bachelors/artificial-intelligence"
    _, trace = await search(provider, Fetcher(PAGES), pages=[already], slots_confirmed=True)
    assert len(provider.queries) == 3
    assert trace.discovery_query_passes == [3]


async def test_an_unconfirmed_lead_in_a_slot_does_not_stop_the_second_pass(reserve):
    """Early search (SO-1): a sitemap lead nobody has read yet is not a confirmed page."""
    provider = Provider(lambda n: [EVENT_PAGE])
    lead = "https://www.rug.nl/bachelors/artificial-intelligence"
    _, trace = await search(provider, Fetcher(PAGES), pages=[lead], slots_confirmed=False)
    assert len(provider.queries) == 6
    assert trace.discovery_query_passes == [3, 3]


async def test_a_rate_limit_in_the_first_pass_ends_the_search(reserve):
    provider = Provider(lambda n: [], fail_with=429)
    _, trace = await search(provider, Fetcher(PAGES))
    assert len(provider.queries) == 1
    assert trace.discovery_query_passes == [1]
    assert any("HTTP 429" in line for line in trace.search_limitations)


async def test_an_unread_lead_is_settled_once_after_the_last_pass(reserve):
    """PG-1 on: a lead that could not be read is a diagnostic, never a programme."""
    missing = "https://www.rug.nl/bachelors/computer-science"
    provider = Provider(lambda n: [missing])
    selected, trace = await search(provider, Fetcher(PAGES))
    assert len(provider.queries) == 6
    assert selected[PageCategory.PROGRAM_PAGE] == []
    assert trace.unresolved == [missing]


def test_the_benchmark_flag_reaches_the_child_and_turns_the_rule_on(tmp_path, monkeypatch):
    import subprocess
    import sys

    from evaluation.research import live
    from evaluation.research.schema import Observation

    monkeypatch.setattr(intent_module, "DISCOVERY_QUERY_RESERVE", False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            *("live", "--live", "--case", "groningen", "--out", str(tmp_path)),
            "--discovery-query-reserve",
        ],
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    commands = []

    def child(command, **kwargs):
        commands.append(command)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="groningen").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    assert "--discovery-query-reserve" in commands[0]

    seen = []

    async def capture(case_id, output, max_pages, seconds, **kwargs):
        seen.append(intent_module.DISCOVERY_QUERY_RESERVE)

    monkeypatch.setattr(live, "capture_one", capture)
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "none")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            *("live", "--live", "--child", "--case", "groningen"),
            *("--out", str(tmp_path / "o.json"), "--discovery-query-reserve"),
        ],
    )
    live.main()
    assert seen == [True]
