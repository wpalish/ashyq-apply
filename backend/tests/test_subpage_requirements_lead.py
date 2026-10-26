"""SP-2: a process sub-page SP-1 refuses becomes a requirements lead.

NEXT_CYCLES_2026-10-19 §1.4, candidate 2 (``SUBPAGE_REQUIREMENTS_LEAD``,
harness ``--subpage-requirements-lead``). SP-1 refuses a page whose head names
a process of the programme ("Application for the B.Sc. …", "Admission to …")
before the programme's own title: it is not the programme page, but it is the
page where the programme's English minima and application deadline are
written. On: the first such page discovery read is handed to the evidence
stage; the requirements adapter reads it behind QR-1's question links, inside a
free question-link slot, for the deadline and English, and its claims take the
programme's scope only when its ``h1`` names the level and the subject. A year
page ("L2 …") is never a lead. No query, no discovery read added. Off: nothing
changes.

Offline: synthetic pages, plus the development pages hand-fetched for SP-1
through the production ``Fetcher`` (``trust_env_proxy=True``, robots honoured,
2026-10-19): ``tests/fixtures/subpage_head/`` (rwth's application page, which
SP-1 refuses; ctu's FIT admissions page, which it does not).
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

import pytest

import app.adapters.search as search_pkg
from app.adapters.base import Candidate, CandidateProgram, RequirementsLead
from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    SUBPAGE_HEAD_VERDICT,
    DiscoveryTrace,
    head_names_programme,
    head_subpage_rejects,
    is_process_subpage_refusal,
)
from app.adapters.page_classifier import classify_page
from app.adapters.requirements import web_requirements
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.domain.enums import ClaimType, DegreeLevel, SourceSpecificity
from evaluation.research import live
from tests.test_question_page_order import _Fetcher
from tests.test_subpage_head import (
    BACKEND,
    CS,
    CTU,
    PSACLAY,
    PSACLAY_L2,
    RWTH_EN,
    _recover,
    fixture,
    page_html,
)

UNI = "https://www.uni.example"
PROGRAMME = f"{UNI}/study/bachelor/computer-science"
APPLY = f"{PROGRAMME}/application"
ADMISSIONS = f"{UNI}/admissions"
OTHER = f"{UNI}/study/bachelor/computer-science-and-maths"
CTU_GOLD = "https://fit.cvut.cz/en/study-programs/bachelor-study/informatics"

PROGRAMME_HTML = page_html("Computer Science | Uni", "Computer Science").replace(
    "Entry requirements include IELTS 6.5; tuition fees apply.", "Three years."
)
APPLY_HTML = (
    "<html lang='en'><head><title>Application for the B.Sc. Computer Science | Uni</title>"
    "</head><body><main><h1>Application for the B.Sc. Computer Science</h1>"
    "<p>Bachelor of Science in Computer Science. Applicants need IELTS Academic with an "
    "overall band score of 6.5.</p><p>Application deadline: 15 January 2027.</p>"
    "</main></body></html>"
)
#: A process head that names no programme: the page keeps its own scope.
GENERAL_APPLY_HTML = APPLY_HTML.replace(
    "<h1>Application for the B.Sc. Computer Science</h1>", "<h1>Admission</h1>"
)
ADMISSIONS_HTML = (
    "<html><head><title>Admissions | Uni</title></head><body><h1>Admissions</h1>"
    "<p>Welcome, future students.</p></body></html>"
)


@pytest.fixture(autouse=True)
def no_search(monkeypatch):
    class _NoSearch:
        name = "none"

        async def search(self, **kwargs: Any) -> Any:
            raise AssertionError("SP-2 sends no query")

    monkeypatch.setattr(search_pkg, "get_search_provider", lambda: _NoSearch())
    monkeypatch.setattr(web_requirements, "TOPIC_SEARCH", False)


@pytest.fixture(params=[False, True], ids=["off", "on"])
def sp2(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "CONFIRM_REJECTS_SUBPAGE_HEAD", True)
    monkeypatch.setattr(live_discovery, "SUBPAGE_REQUIREMENTS_LEAD", request.param)
    return request.param


@pytest.fixture
def on(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "CONFIRM_REJECTS_SUBPAGE_HEAD", True)
    monkeypatch.setattr(live_discovery, "SUBPAGE_REQUIREMENTS_LEAD", True)


# --- the flag, the verdict ------------------------------------------------------


def test_sp2_is_off_by_default() -> None:
    assert live_discovery.SUBPAGE_REQUIREMENTS_LEAD is False


@pytest.mark.parametrize(
    ("word", "process"),
    [
        ("application for", True),
        ("admission", True),
        ("bewerbung", True),
        ("deadlines", True),
        ("l2", False),
        ("year 2", False),
        ("first year", False),
    ],
)
def test_only_a_process_word_makes_a_lead(word, process) -> None:
    assert is_process_subpage_refusal(SUBPAGE_HEAD_VERDICT.format(word)) is process


def test_other_verdicts_are_no_lead() -> None:
    assert not is_process_subpage_refusal(None)
    assert not is_process_subpage_refusal("page head names a unit (department), not a programme")
    assert not is_process_subpage_refusal("reads as admissions, not a programme page")


def test_the_lead_takes_the_programme_scope_only_when_its_h1_names_it() -> None:
    named = classify_page(url=APPLY, html=APPLY_HTML)
    assert head_names_programme(named, "bachelor", CS)
    assert not head_names_programme(named, "master", CS)
    general = classify_page(url=APPLY, html=GENERAL_APPLY_HTML)
    assert not head_names_programme(general, "bachelor", CS)


# --- discovery hands the refused page on ------------------------------------------


async def test_recovery_keeps_a_refused_process_page_as_a_lead(tmp_path, profile, sp2) -> None:
    pages = {APPLY: APPLY_HTML, PROGRAMME: PROGRAMME_HTML}
    found, rejected, requested, trace = await _recover(tmp_path, profile, pages, [APPLY, PROGRAMME])
    # SP-1 decides what is read and confirmed; SP-2 adds no read.
    assert requested == [APPLY, PROGRAMME]
    assert found == [PROGRAMME]
    assert is_process_subpage_refusal(rejected[APPLY])
    if sp2:
        assert trace.requirements_leads == [RequirementsLead(APPLY, True)]
        assert trace.as_dict()["requirements_leads"] == [{"url": APPLY, "names_programme": True}]
    else:
        assert trace.requirements_leads == []
        assert "requirements_leads" not in trace.as_dict()


async def test_a_year_page_is_never_a_lead(tmp_path, profile, on) -> None:
    pages = {PSACLAY_L2: fixture("psaclay_l2"), PSACLAY: fixture("psaclay_gold")}
    _found, rejected, _requested, trace = await _recover(
        tmp_path, profile, pages, [PSACLAY_L2, PSACLAY]
    )
    assert rejected[PSACLAY_L2] == SUBPAGE_HEAD_VERDICT.format("l2")
    assert trace.requirements_leads == []


async def test_rwth_application_page_becomes_a_lead(tmp_path, profile, on) -> None:
    # Real page, refused by SP-1 on "Application for"; its h1 names the B.Sc.
    _found, rejected, requested, trace = await _recover(
        tmp_path, profile, {RWTH_EN: fixture("rwth_application_en")}, [RWTH_EN]
    )
    assert requested == [RWTH_EN]
    assert rejected[RWTH_EN] == SUBPAGE_HEAD_VERDICT.format("application for")
    assert trace.requirements_leads == [RequirementsLead(RWTH_EN, True)]


async def test_only_the_first_process_page_is_kept(tmp_path, profile, on) -> None:
    second = f"{UNI}/study/bachelor/computer-science/admission"
    pages = {
        APPLY: APPLY_HTML,
        second: APPLY_HTML.replace("Application for", "Admission to"),
    }
    _found, _rejected, _requested, trace = await _recover(tmp_path, profile, pages, [APPLY, second])
    assert [lead.url for lead in trace.requirements_leads] == [APPLY]


def test_sp1_off_refuses_nothing_so_nothing_is_handed_on(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "SUBPAGE_REQUIREMENTS_LEAD", True)
    monkeypatch.setattr(live_discovery, "CONFIRM_REJECTS_SUBPAGE_HEAD", False)
    page = classify_page(url=APPLY, html=APPLY_HTML)
    assert live_discovery.profile_rejects(page, "bachelor", CS, url=APPLY) is None


def test_apply_copies_the_lead_onto_the_candidate(profile, monkeypatch) -> None:
    profile.context.intended_fields = list(CS)
    trace = DiscoveryTrace(institution="U", domain="uni.example", country="")
    trace.requirements_leads.append(RequirementsLead(APPLY, True))
    candidate = Candidate(name="U", country="", city="", domain="uni.example")
    selected: dict[str, list[str]] = {c: [] for c in live_discovery.PageCategory.ALL}
    selected[live_discovery.PageCategory.PROGRAM_PAGE] = [PROGRAMME]
    live_discovery.LiveDiscoveryAdapter(None)._apply(  # type: ignore[arg-type]
        candidate, selected, profile, trace
    )
    assert candidate.requirements_leads == [RequirementsLead(APPLY, True)]


def test_ctu_admissions_page_is_not_refused_so_not_a_lead(monkeypatch) -> None:
    # Recorded limit (SP-1's, inherited): ctu's FIT admissions page heads with
    # the programme ("Bachelor's degree programme Informatics"); the process
    # is only in its URL and title. SP-1 does not refuse it, so SP-2 has
    # nothing to hand on: ctu's English labels need SP-1b (one set, not built).
    monkeypatch.setattr(live_discovery, "SUBPAGE_REQUIREMENTS_LEAD", True)
    page = classify_page(url=CTU, html=fixture("ctu_admissions"))
    assert head_subpage_rejects(page, CS) is None
    trace = DiscoveryTrace(institution="ctu", domain="cvut.cz", country="")
    trace.note_requirements_lead(CTU, None, page, "bachelor", CS)
    assert trace.requirements_leads == []


# --- the evidence stage reads it ---------------------------------------------------


def _candidate(leads: list[RequirementsLead], domain: str = "uni.example") -> Candidate:
    return Candidate(
        name="Uni",
        country="Testland",
        city="",
        domain=domain,
        admissions_url=ADMISSIONS if domain == "uni.example" else None,
        requirements_leads=leads,
    )


def _program(url: str = PROGRAMME) -> CandidateProgram:
    return CandidateProgram(
        name="Computer Science", field="computer science", degree=DegreeLevel.BACHELOR, url=url
    )


def _values(result, claim_type: ClaimType) -> list[object]:
    return [c.normalized_value for c in result.claims if c.claim_type is claim_type]


async def test_the_lead_is_read_after_the_link_sources_for_english_and_the_deadline() -> None:
    fetcher = _Fetcher({PROGRAMME: PROGRAMME_HTML, ADMISSIONS: ADMISSIONS_HTML, APPLY: APPLY_HTML})
    adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
    result = await adapter.verify(
        _candidate([RequirementsLead(APPLY, True)]), _program(), "fall 2027"
    )
    assert fetcher.calls == [PROGRAMME, ADMISSIONS, APPLY]
    assert _values(result, ClaimType.IELTS_MIN_OVERALL) == [6.5]
    assert _values(result, ClaimType.ADMISSION_DEADLINE) == ["2027-01-15"]
    from_lead = [c for c in result.claims if c.source_url == APPLY]
    assert from_lead
    assert {c.source_specificity for c in from_lead} == {SourceSpecificity.PROGRAM}


async def test_without_a_lead_the_page_is_never_read() -> None:
    fetcher = _Fetcher({PROGRAMME: PROGRAMME_HTML, ADMISSIONS: ADMISSIONS_HTML, APPLY: APPLY_HTML})
    adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
    result = await adapter.verify(_candidate([]), _program(), "fall 2027")
    assert fetcher.calls == [PROGRAMME, ADMISSIONS]
    assert _values(result, ClaimType.IELTS_MIN_OVERALL) == []


async def test_a_lead_whose_h1_names_no_programme_keeps_admissions_scope() -> None:
    fetcher = _Fetcher(
        {PROGRAMME: PROGRAMME_HTML, ADMISSIONS: ADMISSIONS_HTML, APPLY: GENERAL_APPLY_HTML}
    )
    adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
    result = await adapter.verify(
        _candidate([RequirementsLead(APPLY, False)]), _program(), "fall 2027"
    )
    from_lead = [c for c in result.claims if c.source_url == APPLY]
    assert from_lead
    assert {c.source_specificity for c in from_lead} == {SourceSpecificity.UNIVERSITY_ADMISSIONS}


async def test_answered_questions_leave_the_lead_unread() -> None:
    answered = PROGRAMME_HTML.replace(
        "</main>",
        "<p>Applicants need IELTS Academic with an overall band score of 6.5.</p>"
        "<p>Application deadline: 15 January 2027.</p></main>",
    )
    fetcher = _Fetcher({PROGRAMME: answered, ADMISSIONS: ADMISSIONS_HTML, APPLY: APPLY_HTML})
    adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
    result = await adapter.verify(
        _candidate([RequirementsLead(APPLY, True)]), _program(), "fall 2027"
    )
    assert _values(result, ClaimType.IELTS_MIN_OVERALL) == [6.5]
    assert APPLY not in fetcher.calls
    assert any(error.startswith("SP-2: ") for error in result.errors)


async def test_full_question_slots_leave_the_lead_unread() -> None:
    # Two English and two deadline links on the programme page fill QR-1's
    # caps: the lead adds no read beyond them.
    links = "".join(
        f'<a href="{UNI}/{path}">{text}</a>'
        for path, text in (
            ("english-1", "English language requirements"),
            ("english-2", "English language requirements for applicants"),
            ("deadlines-1", "Deadlines"),
            ("deadlines-2", "Key dates"),
        )
    )
    programme = PROGRAMME_HTML.replace("</main>", f"<p>{links}</p></main>")
    fetcher = _Fetcher({PROGRAMME: programme, ADMISSIONS: ADMISSIONS_HTML, APPLY: APPLY_HTML})
    adapter = WebRequirementsAdapter(fetcher, "2027/28")  # type: ignore[arg-type]
    await adapter.verify(_candidate([RequirementsLead(APPLY, True)]), _program(), "fall 2027")
    assert APPLY not in fetcher.calls


async def test_ctu_admissions_page_as_a_lead_carries_the_english_minima() -> None:
    # What the evidence stage does with ctu's page once it is a lead (under
    # SP-1b, or any page SP-1 refuses with this body): TOEFL iBT 65 (the
    # signed label), at programme specificity, since its h1 names the programme.
    page = classify_page(url=CTU, html=fixture("ctu_admissions"))
    names = head_names_programme(page, "bachelor", CS)
    assert names
    gold = (
        "<html lang='en'><head><title>Informatics - FIT CTU</title></head><body><main>"
        "<h1>Informatics</h1><p>Bachelor's degree programme, three years.</p>"
        "</main></body></html>"
    )
    fetcher = _Fetcher({CTU_GOLD: gold, CTU: fixture("ctu_admissions")})
    adapter = WebRequirementsAdapter(fetcher, "2026/27")  # type: ignore[arg-type]
    result = await adapter.verify(
        _candidate([RequirementsLead(CTU, names)], domain="cvut.cz"),
        _program(CTU_GOLD),
        "fall 2026",
    )
    assert CTU in fetcher.calls
    assert _values(result, ClaimType.TOEFL_MIN_TOTAL) == [65]
    # Recorded extraction limit, not SP-2's: "IELTS score 5.5 and above" in
    # a list of accepted certificates is read by no English reader today.
    assert _values(result, ClaimType.IELTS_MIN_OVERALL) == []
    # The page itself reads as the 2026 intake's programme page, which the
    # claim builder ranks above the lead's programme specificity.
    assert {c.source_specificity for c in result.claims if c.source_url == CTU} == {
        SourceSpecificity.PROGRAM_INTAKE
    }


# --- the harness -----------------------------------------------------------------


def test_harness_exposes_forwards_and_negates_the_flag(monkeypatch, tmp_path) -> None:
    from tests.test_benchmark_rule_negations import _parent

    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--subpage-requirements-lead" in result.stdout
    assert "--no-subpage-requirements-lead" in result.stdout
    assert live.NEGATABLE_RULES["subpage-requirements-lead"] == (
        ("app.adapters.discovery.live_discovery", "SUBPAGE_REQUIREMENTS_LEAD"),
    )
    assert {"subpage-requirements-lead", "listing-follows-local-aliases"} <= (
        live.DEFAULT_OFF_NEGATABLE
    )
    commands = _parent(monkeypatch, tmp_path, "--subpage-requirements-lead")
    assert "--subpage-requirements-lead" in commands[0]


def test_the_child_switches_the_rule_on(monkeypatch, tmp_path) -> None:
    seen: dict[str, bool] = {}

    async def fake_capture(case_id, output, max_pages, seconds, **kwargs):
        seen["sp2"] = live_discovery.SUBPAGE_REQUIREMENTS_LEAD

    monkeypatch.setattr(live_discovery, "SUBPAGE_REQUIREMENTS_LEAD", False)
    monkeypatch.setattr(live, "capture_one", fake_capture)
    argv = ["live", "--live", "--child", "--case", "ctu", "--out", str(tmp_path / "u.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--subpage-requirements-lead"])
    live.main()
    assert seen == {"sp2": True}
