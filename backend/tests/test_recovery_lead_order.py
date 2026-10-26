"""FP-1 and EF-1: which search lead identity recovery confirms.

Baseline 2 (every rule on, four repetitions) picked the wrong programme page in
some repetitions only, because the provider's results moved between them:

* FP-1 (``FRONT_PAGE_NOT_PROGRAMME``): a faculty site's front page ("Home",
  path ``/``) read as UNKNOWN, so recovery treated it as a listing, found a full
  degree title on it and confirmed it as the programme page. On: a front page
  is refused like any listing, and its own matching links are read next.
* EF-1 (``EXACT_FIELD_LEAD_FIRST``): a joint-honours sibling
  (``/courses/computer-science-jh``) outscored the field's own page
  (``/courses/computer-science``) in the ranked order and was accepted first.
  On: leads whose last path segment names exactly the requested field are read
  first, those more query families returned first.

Offline: every page is written for the test.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    FRONT_PAGE_VERDICT,
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    exact_field_leads_first,
    is_front_page,
)
from app.adapters.fetching import Fetcher
from app.adapters.search.retrieval import RankedCandidate
from tests.test_live_discovery import StubSite, program_html

BACKEND = Path(__file__).resolve().parents[1]
CS = ["computer science"]
HOME = "https://www.cs.uni.example/"
DEEP = "https://www.cs.uni.example/programmes/beng-compsc"
OWN = "https://www.uni.example/courses/undergraduate/courses/computer-science"
JOINT = "https://www.uni.example/courses/undergraduate/courses/computer-science-jh"


def front_page() -> str:
    """A faculty front page that lists its degrees and links to one of them."""
    return (
        "<html><head><title>Home</title></head><body>"
        "<header><nav><a href='/'>Home</a><a href='/about'>About</a></nav></header><main>"
        "<h1>Welcome</h1><h2>Our undergraduate programmes</h2><ul>"
        f"<li><a href='{DEEP}'>Bachelor of Engineering in Computer Science</a></li>"
        "<li><a href='/news'>News and events</a></li></ul>"
        "<p>Bachelor of Engineering in Computer Science - four years, taught in English.</p>"
        "</main></body></html>"
    )


async def _recover(tmp_path, profile, pages: dict[str, bytes | str], leads: list[RankedCandidate]):
    profile.context.intended_fields = list(CS)
    site = StubSite(pages)
    domain = leads[0].url.split("/")[2].split(".", 1)[1]
    trace = DiscoveryTrace(institution="U", domain=domain, country="Ireland")
    found: list[str] = []
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages(leads, found, trace, profile)
    return found, trace, site.requested


@pytest.fixture(params=[False, True], ids=["off", "on"])
def fp1(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "FRONT_PAGE_NOT_PROGRAMME", request.param)
    return request.param


@pytest.fixture(params=[False, True], ids=["off", "on"])
def ef1(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "EXACT_FIELD_LEAD_FIRST", request.param)
    return request.param


def test_fp1_is_on_and_ef1_off_by_default() -> None:
    assert live_discovery.FRONT_PAGE_NOT_PROGRAMME is True
    assert live_discovery.EXACT_FIELD_LEAD_FIRST is False


def test_is_front_page() -> None:
    assert is_front_page("https://www.cs.uni.example/")
    assert is_front_page("https://www.cs.uni.example")
    assert not is_front_page("https://www.cs.uni.example/?lang=en")
    assert not is_front_page("https://www.cs.uni.example/content?menu=188")
    assert not is_front_page(DEEP)
    assert not is_front_page("/")


@pytest.mark.asyncio
async def test_recovery_refuses_a_front_page_only_on(tmp_path, profile, fp1, monkeypatch) -> None:
    # FP-1 alone: CH-1 would refuse the "Home"/"Welcome" head before FP-1 reads the URL.
    monkeypatch.setattr(live_discovery, "CONFIRM_REQUIRES_HEAD_IDENTITY", False)
    found, trace, requested = await _recover(
        tmp_path,
        profile,
        {HOME: front_page(), DEEP: program_html("BEng Computer Science")},
        [RankedCandidate(HOME, "Computer Science", 0.0, "navigation")],
    )
    assert requested[0] == HOME
    if fp1:
        assert found == [DEEP]
        assert (HOME, FRONT_PAGE_VERDICT) in trace.rejected
    else:
        assert found == [HOME]
        assert DEEP not in requested


@pytest.mark.asyncio
async def test_front_page_rule_leaves_a_deep_programme_page_alone(tmp_path, profile, fp1) -> None:
    found, _trace, _requested = await _recover(
        tmp_path,
        profile,
        {DEEP: program_html("BEng Computer Science")},
        [RankedCandidate(DEEP, "Computer Science", 1.0, "fake")],
    )
    assert found == [DEEP]


def _lead(url: str, score: float, families: tuple[str, ...]) -> RankedCandidate:
    return RankedCandidate(url, "Computer Science", score, "fake", found_by=families)


def test_exact_field_leads_first_orders_only_exact_leads() -> None:
    news = _lead("https://www.uni.example/news/computer-science-week", 9.0, ("a",))
    joint = _lead(JOINT, 8.0, ("a", "b"))
    school = _lead("https://www.uni.example/school/undergraduate/computer-science/", 7.0, ("a",))
    own = _lead(OWN, 6.0, ("a", "b", "c"))
    ordered = exact_field_leads_first([news, joint, school, own], CS)
    assert [c.url for c in ordered] == [own.url, school.url, news.url, joint.url]
    assert exact_field_leads_first([news, joint], CS) == [news, joint]
    assert exact_field_leads_first([joint, own], []) == [joint, own]


@pytest.mark.asyncio
async def test_recovery_reads_the_field_own_page_before_a_joint_one_only_on(
    tmp_path, profile, ef1
) -> None:
    found, _trace, requested = await _recover(
        tmp_path,
        profile,
        {
            JOINT: program_html("BA Computer Science"),
            OWN: program_html("BA Computer Science"),
        },
        [_lead(JOINT, 9.0, ("natural_language", "programmes")), _lead(OWN, 8.0, ("a", "b", "c"))],
    )
    assert requested[0] == (OWN if ef1 else JOINT)
    assert found[0] == (OWN if ef1 else JOINT)


def test_harness_exposes_and_forwards_the_flags() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--front-page-not-programme" in result.stdout
    assert "--exact-field-lead-first" in result.stdout
    source = (BACKEND / "evaluation" / "research" / "live.py").read_text(encoding="utf-8")
    assert "fp1_module.FRONT_PAGE_NOT_PROGRAMME = True" in source
    assert "ef1_module.EXACT_FIELD_LEAD_FIRST = True" in source
    assert '["--front-page-not-programme"] if args.front_page_not_programme' in source
    assert '["--exact-field-lead-first"] if args.exact_field_lead_first' in source
