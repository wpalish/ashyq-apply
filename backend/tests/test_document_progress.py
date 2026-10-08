"""Document completion is scoped to a stable requirement, not its title."""

from datetime import date

from app.domain.enums import DocumentOwner, DocumentPurpose
from app.models import ProgramResultRow
from app.pipeline.runner import store_result
from app.schemas.result import DocumentChecklist, DocumentItem, ProgramResult


def document(**changes):
    values = {
        "name": "Reference letter",
        "purpose": DocumentPurpose.ADMISSION,
        "owner": DocumentOwner.RECOMMENDER,
    }
    return DocumentItem(**(values | changes))


def test_identity_is_stable_across_provenance_but_separates_purpose_owner_and_limits():
    item = document()
    assert (
        item.progress_id
        == document(
            source_url="https://uni.test/documents", claim_ids=["read-2"], lead_time_days=30
        ).progress_id
    )
    for changes in [
        {"owner": DocumentOwner.APPLICANT},
        {"purpose": DocumentPurpose.SCHOLARSHIP},
        {"word_limit": 500},
        {"deadline": date(2027, 1, 15)},
    ]:
        assert document(**changes).progress_id != item.progress_id
    assert DocumentItem.model_validate(item.model_dump(mode="json")).progress_id == item.progress_id


def test_final_mutations_and_duplicate_projections_share_only_the_correct_id():
    first = document()
    original = first.progress_id
    first.name += " — scholarship one"
    first.deadline = date(2027, 1, 15)
    finalized = DocumentItem.model_validate(first.model_dump(mode="json"))
    assert finalized.progress_id != original
    c = DocumentChecklist(
        result_id="r",
        university="U",
        program="P",
        admission_documents=[first],
        recommender_actions=[first],
    )
    assert c.progress_ids() == {finalized.progress_id}


def test_new_requirement_does_not_inherit_an_old_done_mark():
    old = document()
    new = document(word_limit=1000)
    result = ProgramResult(
        id="r",
        run_id="run",
        university="U",
        university_id="u",
        country="KZ",
        city="City",
        program="P",
        degree="bachelor",
        intake="2027",
        checklist=DocumentChecklist(
            result_id="r", university="U", program="P", recommender_actions=[new]
        ),
    )
    row = ProgramResultRow(
        payload={"document_progress": {old.progress_id: True, new.progress_id: True}}
    )
    store_result(row, result, ranking_version=2)
    assert row.payload["document_progress"] == {new.progress_id: True}


def test_python_and_json_serialization_with_dates_share_requirement_identity():
    item = document(deadline=date(2027, 1, 15))
    assert item.model_dump()["progress_id"] == item.model_dump(mode="json")["progress_id"]


def test_two_devices_preserve_both_document_ticks_on_postgres(pg_session, pg_engine, profile):
    from concurrent.futures import ThreadPoolExecutor, TimeoutError
    from threading import Event

    import pytest
    from sqlalchemy.orm import Session

    from app.api.routes_results import DocumentProgressIn, _locked_result, set_document_progress
    from app.models import ResearchRun
    from app.security import Principal
    from tests.conftest import TEST_ORGANIZATION_ID, profile_row

    person = profile_row(pg_session, profile)
    run = ResearchRun(profile_id=person.id, stage="completed", demo_mode=True)
    pg_session.add(run)
    pg_session.flush()
    first, second = document(), document(name="Personal statement", owner=DocumentOwner.APPLICANT)
    result = ProgramResult(
        id="d" * 32,
        run_id=run.id,
        university="U",
        university_id="u",
        city="City",
        country="KZ",
        program="P",
        degree="bachelor",
        intake="2027",
        checklist=DocumentChecklist(
            result_id="d" * 32,
            university="U",
            program="P",
            recommender_actions=[first],
            applicant_actions=[second],
        ),
    )
    row = ProgramResultRow(
        id=result.id,
        run_id=run.id,
        dedupe_key="u:p",
        university="U",
        university_key="u",
        country="KZ",
        program="P",
        eligibility=result.eligibility.value,
        admissions_fit=result.admissions_fit.value,
        funding_fit=result.funding_fit.value,
        funding_classification=result.best_funding_classification.value,
        payload=result.model_dump(mode="json"),
        checklist=result.checklist.model_dump(mode="json"),
    )
    pg_session.add(row)
    pg_session.commit()
    run_id = run.id
    principal = Principal(
        user_id="test-device",
        organization_id=TEST_ORGANIZATION_ID,
        email="device@example.test",
        display_name="Device",
        role="owner",
    )
    locked = _locked_result(pg_session, run_id, result.id)
    payload = ProgramResult.model_validate(locked.payload)
    payload.document_progress[first.progress_id] = True
    locked.payload = payload.model_dump(mode="json")
    started = Event()

    def other_device():
        with Session(pg_engine) as db:
            started.set()
            return set_document_progress(
                run_id, result.id, second.progress_id, DocumentProgressIn(done=True), principal, db
            )

    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(other_device)
        assert started.wait(5)
        with pytest.raises(TimeoutError):
            pending.result(timeout=0.2)
        pg_session.commit()
        saved = pending.result(timeout=10)
    assert saved.document_progress == {first.progress_id: True, second.progress_id: True}
