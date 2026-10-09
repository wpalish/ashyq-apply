"""Actual fetched source -> native compiler -> cached scoped question states."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.adapters.fetching import FetchResult
from app.domain.enums import ClaimStatus, ClaimType, FetchOutcome
from app.research.session import PublicSource, observe_fetch, project_run_questions
from app.schemas.claim import ClaimOut
from app.schemas.result import ProgramResult

URL = "https://example.edu/cs"
HTML = """<title>Computer Science</title>
<h1>Undergraduate applicants</h1><p>Fall 2027 intake.</p>
<p>Academic year 2027/28.</p><p>International applicants.</p>
<p>Required qualification: Attestat.</p><p>Application deadline: 2027-01-15.</p>"""


@pytest.fixture
def research_session(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.research.session.institution_identities",
        lambda: (SimpleNamespace(name="Example", country="Exampleland", domains=("example.edu",)),),
    )
    now = datetime.now(UTC)
    result = ProgramResult(
        id="programme",
        run_id="run",
        university="Example",
        university_id="example",
        country="Exampleland",
        city="City",
        program="Computer Science",
        degree="bachelor",
        intake="fall 2027",
        program_url=URL,
        claims=[
            ClaimOut(
                id="c",
                claim_type=ClaimType.ADMISSION_DEADLINE,
                normalized_value="2027-01-15",
                source_url=URL,
                official_domain=True,
                original_text_excerpt="Application deadline: 2027-01-15.",
                accessed_at=now,
                status=ClaimStatus.VERIFIED_CURRENT,
            )
        ],
    )
    row = SimpleNamespace(payload=result.model_dump(mode="json"))
    runner = SimpleNamespace(
        settings=SimpleNamespace(cache_dir=tmp_path, cache_ttl_seconds=86400),
        intake="fall 2027",
        _academic_year=lambda: "2027/28",
        _rows=lambda: [row],
        profile=SimpleNamespace(
            context=SimpleNamespace(education_system="Kazakhstan national secondary")
        ),
    )
    return (
        runner,
        row,
        FetchResult(
            url=URL,
            final_url=URL,
            outcome=FetchOutcome.OK,
            content_type="text/html",
            content=HTML.encode(),
            text=HTML,
            fetched_at=now,
        ),
    )


def test_native_html_to_complete_deadline_and_partial_academics(research_session):
    runner, _, fetched = research_session
    observe_fetch(runner, URL, fetched)
    states = project_run_questions(runner)["programme"]
    assert len(states) == 6
    assert states["deadline"]["state"] == "answered"
    assert states["academic"]["state"] == "partial"
    assert states["english"]["state"] == "pending"
    assert states["scholarship_applicability"]["state"] == "pending"
    assert len(list(runner.settings.cache_dir.rglob("source-*.json"))) == 1


def test_second_local_projection_reuses_public_sources_without_fetch(research_session):
    runner, _, fetched = research_session
    observe_fetch(runner, URL, fetched)
    first = project_run_questions(runner)
    runner._recall_public_sources = {}
    assert project_run_questions(runner) == first


def test_expired_cache_files_do_not_starve_current_source(research_session):
    runner, _, fetched = research_session
    observe_fetch(runner, URL, fetched)
    first = project_run_questions(runner)
    path = next(runner.settings.cache_dir.rglob("source-*.json"))
    record = PublicSource.model_validate_json(path.read_bytes())
    expired = record.model_copy(
        update={
            "accessed_at": datetime.now(UTC) - timedelta(days=2),
            "valid_until": datetime.now(UTC) - timedelta(days=1),
        }
    )
    for index in range(240):
        (path.parent / f"source-000-{index:03}.json").write_text(
            expired.model_dump_json(), encoding="utf-8"
        )
    runner._recall_public_sources = {}
    assert project_run_questions(runner) == first


def test_policy_work_overflow_withholds_entire_projection(research_session, monkeypatch):
    from app.research.compiler import compile_document

    monkeypatch.setattr(
        "app.research.compiler.compile_document", lambda *args: compile_document(*args) * 513
    )
    runner, _, fetched = research_session
    observe_fetch(runner, URL, fetched)
    states = project_run_questions(runner)["programme"]
    assert all(
        answer["state"] == "unavailable" and not answer["rules"] for answer in states.values()
    )


def test_changed_native_source_invalidates_old_answer(research_session):
    runner, _, fetched = research_session
    observe_fetch(runner, URL, fetched)
    first = project_run_questions(runner)
    fetched.text = HTML.replace("2027-01-15", "2027-02-01")
    observe_fetch(runner, URL, fetched)
    second = project_run_questions(runner)
    old = first["programme"]["deadline"]["rules"][0]
    new = second["programme"]["deadline"]["rules"][0]
    assert old["value"]["date"] == "2027-01-15"
    assert new["value"]["date"] == "2027-02-01"
    assert old["id"] != new["id"]


def test_untrusted_institution_does_not_enter_shared_policy_cache(research_session, monkeypatch):
    monkeypatch.setattr("app.research.session.institution_identities", lambda: ())
    runner, row, fetched = research_session
    row.payload["claims"][0]["official_domain"] = False
    observe_fetch(runner, URL, fetched)
    states = project_run_questions(runner)
    assert states["programme"]["deadline"]["state"] == "pending"
    assert not list(runner.settings.cache_dir.rglob("source-*.json"))


def test_trusted_native_source_can_prove_new_fact_without_legacy_claim(research_session):
    runner, row, fetched = research_session
    row.payload["claims"] = []
    observe_fetch(runner, URL, fetched)
    assert project_run_questions(runner)["programme"]["deadline"]["state"] == "answered"


@pytest.mark.parametrize(
    "original,final",
    [
        ("https://other.edu/cs", "https://other.edu/cs"),
        (URL, "https://other.edu/cs"),
        ("https://other.edu/cs", URL),
        (URL, "https://example.edu.attacker.com/cs"),
    ],
)
def test_other_university_and_redirect_cannot_inherit_official_flag(
    research_session, original, final
):
    runner, row, fetched = research_session
    row.payload["claims"][0]["source_url"] = final
    fetched.url, fetched.final_url = original, final
    observe_fetch(runner, original, fetched)
    assert project_run_questions(runner)["programme"]["deadline"]["state"] == "pending"
    assert not list(runner.settings.cache_dir.rglob("source-*.json"))


def test_mixed_certificate_page_does_not_inherit_nis_scope(research_session):
    runner, _, fetched = research_session
    runner.profile.context.education_system = "NIS"
    fetched.text = HTML + "<p>NIS Grade 12 Certificate applicants.</p>"
    observe_fetch(runner, URL, fetched)
    assert project_run_questions(runner)["programme"]["deadline"]["state"] == "pending"


def test_country_restriction_remains_unresolved(research_session):
    runner, _, fetched = research_session
    fetched.text = HTML + "<p>Applicants from Canada.</p>"
    observe_fetch(runner, URL, fetched)
    assert project_run_questions(runner)["programme"]["deadline"]["state"] == "pending"


def test_campus_title_cannot_become_unspecified_campus_answer(research_session):
    runner, _, fetched = research_session
    fetched.text = HTML.replace(
        "<title>Computer Science</title>", "<title>Computer Science - Satellite Campus</title>"
    )
    observe_fetch(runner, URL, fetched)
    assert project_run_questions(runner)["programme"]["deadline"]["state"] == "pending"


def test_missing_cycle_cannot_inherit_applicant_intake(research_session):
    runner, _, fetched = research_session
    fetched.text = HTML.replace("Fall 2027 intake.", "Current admissions.")
    observe_fetch(runner, URL, fetched)
    assert project_run_questions(runner)["programme"]["deadline"]["state"] == "pending"


def test_other_qualification_or_campus_cannot_become_applicants_answer(research_session):
    runner, _, fetched = research_session
    fetched.text = (
        HTML.replace("Attestat", "International Baccalaureate Diploma") + "<p>Campus: Other.</p>"
    )
    observe_fetch(runner, URL, fetched)
    assert project_run_questions(runner)["programme"]["deadline"]["state"] == "pending"
