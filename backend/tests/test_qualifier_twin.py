"""QT-1: identity recovery reads the confirmed page's qualifier twin before it stops.

Miss stages 2026-10-19 §3.2 and ticket T1 (``CONFIRM_READS_QUALIFIER_TWIN``,
harness ``--read-qualifier-twin``). SB-1 stops identity recovery at its first
confirmation. On ubc (cohort) and unsw (dev3) that confirmation was a
qualified sibling of the gold — UBC's ``computer-science-vancouver-ba`` of
``…-bsc``, UNSW's ``bachelor-of-commerce-computer-science`` of
``bachelor-of-computer-science`` — and the gold sat unread at order #3 behind
an unlabelled page (``…-okanagan-bsc``, ``bachelor-of-science-computer-science``)
that reading on by rank would have confirmed instead (§3.1). On: the one unread
lead whose slug is the confirmed slug minus exactly one token, or with exactly
one degree slug of the requested level swapped for another
(``_DEGREE_SLUGS``), is read next, judged by the full ``profile_rejects``, and
kept as a second programme page when it passes. Nothing else is read. Off:
nothing changes.

Offline and synthetic (URLs shaped like the development pages; no recorded
page, heldout or dev5 material): English, German and French.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters import fetching
from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    StageBudget,
    qualifier_twin,
)
from app.adapters.fetching import Fetcher
from app.adapters.search.retrieval import RankedCandidate
from evaluation.research import live
from tests.test_live_discovery import StubSite

BACKEND = Path(__file__).resolve().parents[1]
CS = ["computer science"]

UBC = "https://you.ubc.ca/programs/"
UBC_BA = UBC + "computer-science-vancouver-ba/"
UBC_OKANAGAN = UBC + "computer-science-okanagan-bsc/"
UBC_BSC = UBC + "computer-science-vancouver-bsc/"
UNSW = "https://www.unsw.edu.au/study/undergraduate/"
UNSW_COMMERCE = UNSW + "bachelor-of-commerce-computer-science"
UNSW_SCIENCE = UNSW + "bachelor-of-science-computer-science"
UNSW_GOLD = UNSW + "bachelor-of-computer-science"
DE = "https://www.uni-beispiel.de/studium/"
FR = "https://www.univ-exemple.fr/formation/"
ES = "https://www.uni-ejemplo.es/estudios/"


def page_html(title: str, body: str, lang: str = "en") -> str:
    """A programme-shaped page: the head is the title, the body names level and subject."""
    return (
        f"<html lang='{lang}'><head><title>{title}</title></head><body><main>"
        f"<h1>{title}</h1><p>{body}</p></main></body></html>"
    )


EN_BODY = "{0}. Four years. Entry requirements include IELTS 6.5; tuition fees apply."
UBC_PAGES = {
    UBC_BA: page_html("Computer Science - Bachelor of Arts", EN_BODY.format("Bachelor of Arts")),
    UBC_OKANAGAN: page_html("Computer Science", EN_BODY.format("Bachelor of Science")),
    UBC_BSC: page_html(
        "Computer Science - Bachelor of Science", EN_BODY.format("Bachelor of Science")
    ),
}
UNSW_PAGES = {
    UNSW_COMMERCE: page_html(
        "Bachelor of Commerce / Computer Science",
        EN_BODY.format("Bachelor of Commerce / Computer Science double degree"),
    ),
    UNSW_SCIENCE: page_html(
        "Bachelor of Science (Computer Science)", EN_BODY.format("Bachelor of Science")
    ),
    UNSW_GOLD: page_html(
        "Bachelor of Computer Science", EN_BODY.format("Bachelor of Computer Science")
    ),
}
DE_BODY = "Bachelor Informatik. Sechs Semester. Zulassungsvoraussetzungen: Hochschulreife."
DE_PAGES = {
    DE + "informatik-ba": page_html("Informatik Bachelor", DE_BODY, "de"),
    DE + "wirtschaftsinformatik-bsc": page_html("Wirtschaftsinformatik", DE_BODY, "de"),
    DE + "informatik-bsc": page_html("Informatik Bachelor of Science", DE_BODY, "de"),
}
FR_BODY = "Licence Informatique. Trois ans. Conditions d'admission : baccalauréat."
FR_PAGES = {
    FR + "licence-informatique-lyon": page_html("Licence Informatique - Lyon", FR_BODY, "fr"),
    FR + "licence-mathematiques-lyon": page_html("Licence Mathématiques", FR_BODY, "fr"),
    FR + "licence-informatique": page_html("Licence Informatique", FR_BODY, "fr"),
}
#: (pages, leads in rank order, the twin) per language: the twin is ranked last.
SHAPES = {
    "en-swap": (UBC_PAGES, [UBC_BA, UBC_OKANAGAN, UBC_BSC], UBC_BSC),
    "en-removal": (UNSW_PAGES, [UNSW_COMMERCE, UNSW_SCIENCE, UNSW_GOLD], UNSW_GOLD),
    "de-swap": (DE_PAGES, list(DE_PAGES), DE + "informatik-bsc"),
    "fr-removal": (FR_PAGES, list(FR_PAGES), FR + "licence-informatique"),
}


@pytest.fixture(params=[False, True], ids=["off", "on"])
def qt1(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "CONFIRM_READS_QUALIFIER_TWIN", request.param)
    return request.param


@pytest.fixture
def on(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "CONFIRM_READS_QUALIFIER_TWIN", True)


async def _recover(tmp_path, profile, pages: dict[str, str], leads: list[str], *, budget=True):
    """Identity recovery on ``leads`` (in order), each served from ``pages``.

    ``budget``: SB-1 on, as in production — recovery stops at its first
    confirmation.
    """
    profile.context.intended_fields = list(CS)
    site = StubSite(dict(pages))
    domain = leads[0].split("/")[2].removeprefix("www.")
    trace = DiscoveryTrace(institution="U", domain=domain, country="")
    found: list[str] = []
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher)
        if budget:
            adapter._budget = StageBudget(deadline_seconds=10_000, read_cap=28)
        candidates = [RankedCandidate(url, "Computer Science", 1.0, "fake") for url in leads]
        await adapter._recover_search_pages(candidates, found, trace, profile)
    return found, dict(trace.rejected), site.requested, trace


# --- the flag -----------------------------------------------------------------


def test_qt1_is_on_by_default() -> None:
    assert live_discovery.CONFIRM_READS_QUALIFIER_TWIN is True


# --- the twin relation ----------------------------------------------------------


def test_ubc_degree_swap_is_a_twin_and_okanagan_is_not() -> None:
    # Okanagan is ranked first, as on the replay: it differs in two tokens.
    assert qualifier_twin(UBC_BA, [UBC_OKANAGAN, UBC_BSC], "bachelor") == UBC_BSC
    assert qualifier_twin(UBC_BA, [UBC_OKANAGAN], "bachelor") is None


def test_unsw_one_token_removed_is_a_twin_and_the_unlabelled_science_page_is_not() -> None:
    # "commerce" → "science" is a swap of two words that are no degree slugs.
    assert qualifier_twin(UNSW_COMMERCE, [UNSW_SCIENCE, UNSW_GOLD], "bachelor") == UNSW_GOLD
    assert qualifier_twin(UNSW_COMMERCE, [UNSW_SCIENCE], "bachelor") is None


@pytest.mark.parametrize(
    ("confirmed", "candidate", "twin"),
    [
        # German: a degree swap, a removal, and a field word swapped (none).
        (DE + "informatik-ba", DE + "informatik-bsc", True),
        (DE + "informatik-lehramt-bachelor", DE + "informatik-bachelor", True),
        (DE + "informatik-ba", DE + "wirtschaftsinformatik-ba", False),
        # French: a qualifier removed; licence ↔ bachelor are both bachelor slugs.
        (FR + "licence-informatique-alternance", FR + "licence-informatique", True),
        (FR + "licence-informatique", FR + "bachelor-informatique", True),
        (FR + "licence-informatique", FR + "master-informatique", False),
        # Spanish: a qualifier removed; two removed is not a twin.
        (
            ES + "grado-ingenieria-informatica-semipresencial",
            ES + "grado-ingenieria-informatica",
            True,
        ),
        (
            ES + "grado-ingenieria-informatica-semipresencial-madrid",
            ES + "grado-informatica",
            False,
        ),
    ],
)
def test_the_twin_relation_in_three_languages(confirmed, candidate, twin) -> None:
    assert (qualifier_twin(confirmed, [candidate], "bachelor") == candidate) is twin


def test_a_swap_reads_the_requested_level_only() -> None:
    # msc ↔ ma are master slugs: a twin for a master's applicant, not a bachelor's.
    confirmed, candidate = UBC + "data-science-ma", UBC + "data-science-msc"
    assert qualifier_twin(confirmed, [candidate], "master") == candidate
    assert qualifier_twin(confirmed, [candidate], "bachelor") is None
    # ba → msc crosses levels: never a twin.
    assert qualifier_twin(UBC_BA, [UBC + "computer-science-vancouver-msc"], "bachelor") is None


@pytest.mark.parametrize(
    "candidate",
    [
        "https://www.ubc.ca/programs/computer-science-vancouver-bsc/",  # another host
        UBC + "okanagan/computer-science-vancouver-bsc/",  # another parent path
        UBC + "computer-science-vancouver-bsc.html",  # another suffix
        UBC_BA,  # itself
        UBC_BA + "?lang=fr",  # the same slug, another query
        "https://you.ubc.ca/",  # no slug
    ],
)
def test_not_a_twin(candidate) -> None:
    assert qualifier_twin(UBC_BA, [candidate], "bachelor") is None


def test_the_first_twin_in_rank_order_is_read_and_the_url_is_case_and_slash_blind() -> None:
    second = UNSW + "bachelor-of-commerce-science"
    assert qualifier_twin(UNSW_COMMERCE, [UNSW_GOLD, second], "bachelor") == UNSW_GOLD
    assert qualifier_twin(UNSW_COMMERCE, [second, UNSW_GOLD], "bachelor") == second
    upper = UBC.upper().replace("HTTPS", "https") + "COMPUTER-SCIENCE-VANCOUVER-BSC"
    assert qualifier_twin(UBC_BA, [upper], "bachelor") == upper


# --- identity recovery ------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("shape", list(SHAPES))
async def test_the_twin_is_read_after_the_confirmation(tmp_path, profile, qt1, shape) -> None:
    pages, leads, twin = SHAPES[shape]
    found, _rejected, requested, trace = await _recover(tmp_path, profile, pages, leads)
    if qt1:
        # One extra read, the twin's — never the page ranked between them.
        assert requested == [leads[0], twin]
        assert found == [leads[0], twin]
        assert (
            f"QT-1: reading {twin}, the qualifier twin of the confirmed {leads[0]}" in trace.errors
        )
    else:
        assert requested == [leads[0]]
        assert found == [leads[0]]
    assert (
        "search identity recovery: checked {0}, confirmed {0}".format(len(found))
        in (trace.errors[-1])
    )


@pytest.mark.asyncio
async def test_a_twin_refused_by_profile_rejects_adds_nothing(tmp_path, profile, on) -> None:
    pages = dict(UNSW_PAGES)
    pages[UNSW_GOLD] = page_html(
        "Master of Computer Science", "Master of Computer Science. Two years. IELTS 6.5."
    )
    leads = [UNSW_COMMERCE, UNSW_SCIENCE, UNSW_GOLD]
    found, rejected, requested, _trace = await _recover(tmp_path, profile, pages, leads)
    assert requested == [UNSW_COMMERCE, UNSW_GOLD]
    assert found == [UNSW_COMMERCE]
    assert rejected[UNSW_GOLD].startswith("page names degree level master")


@pytest.mark.asyncio
async def test_an_unreachable_twin_adds_nothing(tmp_path, profile, on) -> None:
    pages = {url: html for url, html in UBC_PAGES.items() if url != UBC_BSC}  # BSc: 404
    found, rejected, requested, trace = await _recover(
        tmp_path, profile, pages, [UBC_BA, UBC_OKANAGAN, UBC_BSC]
    )
    assert requested == [UBC_BA, UBC_BSC]
    assert found == [UBC_BA]
    assert rejected[UBC_BSC].startswith("search lead unresolved")
    assert UBC_OKANAGAN not in requested


@pytest.mark.asyncio
async def test_one_twin_read_at_most(tmp_path, profile, on) -> None:
    """The confirmed twin's own twin is not read: one extra read per recovery."""
    pages = dict(UBC_PAGES)
    third = UBC + "computer-science-vancouver-beng/"
    pages[third] = page_html("Computer Science - BEng", EN_BODY.format("Bachelor of Science"))
    found, _rejected, requested, _trace = await _recover(
        tmp_path, profile, pages, [UBC_BA, UBC_OKANAGAN, UBC_BSC, third]
    )
    assert requested == [UBC_BA, UBC_BSC]
    assert found == [UBC_BA, UBC_BSC]


@pytest.mark.asyncio
async def test_no_twin_no_extra_read(tmp_path, profile, on) -> None:
    leads = [UBC_BA, UBC_OKANAGAN]
    found, _rejected, requested, trace = await _recover(tmp_path, profile, UBC_PAGES, leads)
    assert requested == [UBC_BA]
    assert found == [UBC_BA]
    assert not any(line.startswith("QT-1") for line in trace.errors)


@pytest.mark.asyncio
async def test_a_twin_read_before_the_confirmation_is_not_read_again(tmp_path, profile, on) -> None:
    # The twin ranked first and refused, then the qualified page confirmed: no re-read.
    pages = dict(UBC_PAGES)
    pages[UBC_BSC] = page_html("Admissions", "Apply now.")
    found, _rejected, requested, _trace = await _recover(
        tmp_path, profile, pages, [UBC_BSC, UBC_BA, UBC_OKANAGAN]
    )
    assert requested == [UBC_BSC, UBC_BA]
    assert found == [UBC_BA]


@pytest.mark.asyncio
async def test_without_sb1_nothing_moves(tmp_path, profile, qt1) -> None:
    """With SB-1 off recovery reads on by rank; QT-1 neither reorders nor adds."""
    leads = [UBC_BA, UBC_OKANAGAN, UBC_BSC]
    found, _rejected, requested, trace = await _recover(
        tmp_path, profile, UBC_PAGES, leads, budget=False
    )
    assert requested == leads
    assert found == leads
    assert not any(line.startswith("QT-1") for line in trace.errors)


@pytest.mark.asyncio
async def test_off_the_trace_is_byte_identical(tmp_path, profile, monkeypatch) -> None:
    """Off, the helper is never asked and the trace is today's."""

    def never(*args, **kwargs):  # pragma: no cover - reached only on a regression
        raise AssertionError("QT-1 asked while off")

    leads = [UNSW_COMMERCE, UNSW_SCIENCE, UNSW_GOLD]
    monkeypatch.setattr(live_discovery, "CONFIRM_READS_QUALIFIER_TWIN", False)
    baseline = await _recover(tmp_path / "a", profile, UNSW_PAGES, leads)
    monkeypatch.setattr(live_discovery, "qualifier_twin", never)
    found, rejected, requested, trace = await _recover(tmp_path / "b", profile, UNSW_PAGES, leads)
    assert (found, rejected, requested) == baseline[:3]
    assert trace.errors == baseline[3].errors
    assert requested == [UNSW_COMMERCE]


# --- LOCO: each motivating case stands on its own branch ----------------------------


def test_loco_without_ubc_the_rule_still_fires_on_unsw(monkeypatch) -> None:
    """Removal reads no degree table: unsw's twin survives an empty one."""
    monkeypatch.setattr(live_discovery, "_DEGREE_SLUGS", {})
    assert qualifier_twin(UNSW_COMMERCE, [UNSW_SCIENCE, UNSW_GOLD], "bachelor") == UNSW_GOLD
    assert qualifier_twin(UBC_BA, [UBC_OKANAGAN, UBC_BSC], "bachelor") is None


def test_loco_without_unsw_the_rule_still_fires_on_ubc(monkeypatch) -> None:
    """The swap does not rest on the removal branch: ubc's twin survives without it."""
    monkeypatch.setattr(live_discovery, "_one_token_removed", lambda longer, shorter: False)
    assert qualifier_twin(UBC_BA, [UBC_OKANAGAN, UBC_BSC], "bachelor") == UBC_BSC
    assert qualifier_twin(UNSW_COMMERCE, [UNSW_SCIENCE, UNSW_GOLD], "bachelor") is None


# --- the harness --------------------------------------------------------------------


def test_harness_exposes_forwards_and_negates_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--read-qualifier-twin" in result.stdout
    assert "--no-read-qualifier-twin" in result.stdout
    source = (BACKEND / "evaluation" / "research" / "live.py").read_text(encoding="utf-8")
    assert "qt1_module.CONFIRM_READS_QUALIFIER_TWIN = True" in source
    assert '["--read-qualifier-twin"] if args.read_qualifier_twin' in source
    assert live.NEGATABLE_RULES["read-qualifier-twin"] == (
        ("app.adapters.discovery.live_discovery", "CONFIRM_READS_QUALIFIER_TWIN"),
    )
    assert "read-qualifier-twin" not in live.DEFAULT_OFF_NEGATABLE


# --- SB-1b: a confirmation whose read crossed the deadline --------------------------


class _SlowFetcher:
    """The Fetcher, with the clock moved ``seconds`` forward by each read."""

    def __init__(self, inner: Fetcher, clock: list[float], seconds: float) -> None:
        self._inner, self._clock, self._seconds = inner, clock, seconds

    def __getattr__(self, name: str):
        return getattr(self._inner, name)

    async def get(self, url: str, **kwargs):
        result = await self._inner.get(url, **kwargs)
        self._clock[0] += self._seconds
        return result


async def _recover_across_the_deadline(tmp_path, profile, monkeypatch, *, reserve: bool):
    """ubc's replay timing: the confirmation read starts at 49 s and ends at 58 s of 55."""
    clock = [0.0]
    monkeypatch.setattr(live_discovery, "_clock", lambda: clock[0])
    profile.context.intended_fields = list(CS)
    site = StubSite(dict(UBC_PAGES))
    trace = DiscoveryTrace(institution="U", domain="ubc.ca", country="")
    found: list[str] = []
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher)
        budget = StageBudget(deadline_seconds=55, read_cap=28)
        adapter._budget = budget
        adapter.fetcher = _SlowFetcher(fetcher, clock, 9.0)  # type: ignore[assignment]
        clock[0] = 49.0
        leads = [UBC_BA, UBC_OKANAGAN, UBC_BSC]
        candidates = [RankedCandidate(url, "Computer Science", 1.0, "fake") for url in leads]
        await adapter._recover_search_pages(candidates, found, trace, profile, reserve=reserve)
    return found, site.requested, budget


@pytest.mark.asyncio
async def test_the_twin_uses_the_reserve_when_the_confirmation_ran_past_the_deadline(
    tmp_path, profile, monkeypatch, qt1
) -> None:
    """rp-qt1-cohort ubc: QT-1 queued the twin, then SB-1b's deadline clause stopped it.

    The reserve shuts past the deadline once a recovery read started in time —
    here the confirmation itself. The twin may still spend one reserve read;
    the page ranked between them is never read, and off nothing changes.
    """
    found, requested, budget = await _recover_across_the_deadline(
        tmp_path, profile, monkeypatch, reserve=True
    )
    if qt1:
        assert requested == [UBC_BA, UBC_BSC]
        assert found == [UBC_BA, UBC_BSC]
        assert budget.reserve_used == 1
    else:
        assert requested == [UBC_BA]
        assert found == [UBC_BA]
        assert budget.reserve_used == 0


@pytest.mark.asyncio
async def test_past_the_deadline_the_twin_is_not_read_outside_the_first_pass(
    tmp_path, profile, monkeypatch, on
) -> None:
    """Without the first pass's reserve (pass 2, or a pre-confirmed pass) the deadline holds."""
    found, requested, _budget = await _recover_across_the_deadline(
        tmp_path, profile, monkeypatch, reserve=False
    )
    assert requested == [UBC_BA]
    assert found == [UBC_BA]


@pytest.mark.asyncio
async def test_a_spent_reserve_stops_the_twin(tmp_path, profile, monkeypatch, on) -> None:
    monkeypatch.setattr(live_discovery, "RECOVERY_RESERVE_READS", 0)
    found, requested, _budget = await _recover_across_the_deadline(
        tmp_path, profile, monkeypatch, reserve=True
    )
    assert requested == [UBC_BA]
    assert found == [UBC_BA]


# --- QT-1c: the twin past the deadline only when the case clock can spare it --------

DATES = "https://you.ubc.ca/applying-ubc/dates-deadlines/"


async def _recover_then_verify(tmp_path, profile, monkeypatch, *, limit: float):
    """ubc's replay on TB-1's case clock: recovery across SB-1's deadline, then verify.

    The confirmation starts at 49 s and ends at 58 s; a twin read would end
    at 67 s. Verify then works until the deadline question is due, so that
    without a twin read "Dates & deadlines" (``question_open``) has one
    second to spare, as on rp-qt1b-cohort's flag-off arm. Returns what
    recovery read and kept, the trace, and TB-1's verdict on that core read.
    """
    clock = [0.0]
    monkeypatch.setattr(live_discovery, "_clock", lambda: clock[0])
    monkeypatch.setattr(fetching, "_clock", lambda: clock[0])
    monkeypatch.setattr(fetching, "CASE_TIME_BUDGET", True)
    monkeypatch.setattr(fetching, "CASE_TIME_SECONDS", limit)
    profile.context.intended_fields = list(CS)
    site = StubSite(dict(UBC_PAGES))
    trace = DiscoveryTrace(institution="U", domain="ubc.ca", country="")
    found: list[str] = []
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        fetcher._host_seconds["you.ubc.ca"] = [7.0]  # you.ubc.ca's mean read on the replay
        adapter = LiveDiscoveryAdapter(fetcher)
        adapter._budget = StageBudget(deadline_seconds=55, read_cap=28)
        adapter.fetcher = _SlowFetcher(fetcher, clock, 9.0)  # type: ignore[assignment]
        with fetcher.timing("ubc.ca", "discovery"):
            clock[0] = 49.0
            leads = [UBC_BA, UBC_OKANAGAN, UBC_BSC]
            candidates = [RankedCandidate(url, "Computer Science", 1.0, "fake") for url in leads]
            await adapter._recover_search_pages(candidates, found, trace, profile, reserve=True)
        timer = fetcher.timer_for("ubc.ca")
        expected = fetcher._expected_seconds(DATES)
        need = expected + min(fetching.CORE_RESERVE_SECONDS, 2 * expected)
        with fetcher.timing("ubc.ca", "verify"):
            clock[0] += 110.0 - 58.0 - need - 1.0  # the verify stage's reads before it
            refusal = await fetcher.time_admission(timer, DATES, "question_open")
    return found, site.requested, trace, refusal


@pytest.mark.asyncio
async def test_with_time_to_spare_the_twin_uses_the_reserve(
    tmp_path, profile, monkeypatch, on
) -> None:
    found, requested, trace, _refusal = await _recover_then_verify(
        tmp_path, profile, monkeypatch, limit=200.0
    )
    assert requested == [UBC_BA, UBC_BSC]
    assert found == [UBC_BA, UBC_BSC]
    assert not any(line.startswith("QT-1: not reading") for line in trace.errors)


@pytest.mark.asyncio
async def test_on_a_tight_clock_the_twin_is_skipped_and_the_core_read_starts(
    tmp_path, profile, monkeypatch, on
) -> None:
    """rp-qt1b-cohort ubc: the twin past the deadline cost ``ubc:deadline`` in both reps.

    At 58 s of 110 the twin's read cannot leave TB-1's verify and core
    reserves, so it is not read (QT-1's stop at the deadline) and the later
    "Dates & deadlines" read is admitted.
    """
    found, requested, trace, refusal = await _recover_then_verify(
        tmp_path, profile, monkeypatch, limit=110.0
    )
    assert requested == [UBC_BA]
    assert found == [UBC_BA]
    assert refusal == ""
    [line] = [line for line in trace.errors if line.startswith("QT-1: not reading")]
    assert line.startswith(f"QT-1: not reading the qualifier twin {UBC_BSC} past the deadline; ")
    assert "a discovery_extra read is expected to take" in line


@pytest.mark.asyncio
async def test_on_a_tight_clock_an_unguarded_twin_costs_the_core_read(
    tmp_path, profile, monkeypatch, on
) -> None:
    """The loss the guard prevents (QT-1b's replay): asked as a core read, the
    twin is read and the same verify work leaves "Dates & deadlines" refused."""
    monkeypatch.setattr(live_discovery, "QUALIFIER_TWIN_READ_KIND", "core")
    found, requested, _trace, refusal = await _recover_then_verify(
        tmp_path, profile, monkeypatch, limit=110.0
    )
    assert requested == [UBC_BA, UBC_BSC]
    assert found == [UBC_BA, UBC_BSC]
    assert "a question_open read is expected to take" in refusal


@pytest.mark.asyncio
async def test_time_refusal_now_is_silent_outside_a_case_clock(tmp_path) -> None:
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        assert await fetching.time_refusal_now(fetcher, DATES, "discovery_extra") == ""
        assert await fetching.time_refusal_now(object(), DATES, "discovery_extra") == ""
        with fetcher.timing("ubc.ca", "discovery"):
            assert await fetching.time_refusal_now(object(), DATES, "discovery_extra") == ""
        assert fetcher.timer_for("ubc.ca").refused == 0


def test_an_optional_discovery_read_leaves_both_reserves() -> None:
    assert fetching.time_floor("discovery_extra", 40.0, 20.0) == 60.0
    assert live_discovery.QUALIFIER_TWIN_READ_KIND == "discovery_extra"
