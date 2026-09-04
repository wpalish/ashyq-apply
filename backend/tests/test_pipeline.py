"""The pipeline end to end against the bundled corpus.

Each seeded failure case from the QA matrix gets a test, because these are the
behaviours a regression would quietly break.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.enums import (
    AdmissionsFit,
    EligibilityStatus,
    FundingClassification,
    PipelineStage,
    UserDecision,
)
from app.models import ApplicantProfileRow, Base, ClaimRow, ProgramResultRow, ResearchRun
from app.pipeline.runner import ResearchRunner, RunCancelled
from app.pipeline.state import RunState
from app.schemas.result import ProgramResult
from tests.conftest import TEST_ORGANIZATION_ID, profile_row


@pytest.fixture
def session(settings):
    engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    s = factory()
    yield s
    s.close()


@pytest.fixture
async def completed_run(session, settings, profile):
    row = ApplicantProfileRow(
        organization_id=TEST_ORGANIZATION_ID,
        display_name="t",
        payload=profile.model_dump(mode="json"),
    )
    session.add(row)
    session.flush()
    run = ResearchRun(
        profile_id=row.id,
        stage=PipelineStage.QUEUED.value,
        demo_mode=True,
        stage_state=RunState.load(None).dump(),
    )
    session.add(run)
    session.flush()
    runner = ResearchRunner(session, run, profile, settings)
    await runner.run_to_decision()
    return runner, run


def results_of(session, run) -> dict[str, ProgramResult]:
    rows = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run.id).all()
    return {r.university: ProgramResult.model_validate(r.payload) for r in rows}


class TestPipelineShape:
    @pytest.mark.asyncio
    async def test_the_run_reaches_the_decision_stage(self, session, completed_run):
        _, run = completed_run
        assert run.stage == PipelineStage.AWAITING_USER_DECISION.value

    @pytest.mark.asyncio
    async def test_every_stage_before_the_decision_point_completed(self, session, completed_run):
        _, run = completed_run
        state = RunState.load(run.stage_state)
        for stage in (
            PipelineStage.PROFILE_VALIDATION,
            PipelineStage.CANDIDATE_DISCOVERY,
            PipelineStage.PROGRAM_VERIFICATION,
            PipelineStage.FUNDING_DISCOVERY,
            PipelineStage.ASSESSMENT,
        ):
            assert state[stage].status == "done", f"{stage} did not complete"

    @pytest.mark.asyncio
    async def test_the_run_produces_results_and_records_its_evidence(self, session, completed_run):
        _, run = completed_run
        assert run.candidates_found >= 30
        assert run.programs_verified >= 15
        assert run.claims_recorded > 50
        assert session.query(ClaimRow).filter(ClaimRow.run_id == run.id).count() > 50

    @pytest.mark.asyncio
    async def test_unreadable_pages_are_counted_and_listed(self, session, completed_run):
        """The corpus deliberately contains an unreachable university."""
        _, run = completed_run
        assert run.pages_failed > 0
        assert run.errors

    @pytest.mark.asyncio
    async def test_results_are_deduplicated(self, session, completed_run):
        _, run = completed_run
        rows = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run.id).all()
        keys = [r.dedupe_key for r in rows]
        assert len(keys) == len(set(keys))

    @pytest.mark.asyncio
    async def test_the_three_axes_are_assessed_independently(self, session, completed_run):
        _, run = completed_run
        results = results_of(session, run)
        # A programme can be eligible and unfunded, or funded and ineligible.
        assert any(
            r.eligibility is EligibilityStatus.MET
            and r.best_funding_classification is FundingClassification.UNKNOWN
            for r in results.values()
        )
        assert any(
            r.eligibility is EligibilityStatus.GAP
            and r.best_funding_classification is FundingClassification.FULL_RIDE_CONFIRMED
            for r in results.values()
        )


class TestSeededFailureCases:
    @pytest.mark.asyncio
    async def test_a_qualifying_applicant_reaches_met_with_a_full_ride(
        self, session, completed_run
    ):
        _, run = completed_run
        groningen = results_of(session, run)["University of Groningen"]
        assert groningen.best_funding_classification is FundingClassification.FULL_RIDE_CONFIRMED
        assert groningen.hard_filter_failures == []

    @pytest.mark.asyncio
    async def test_a_failed_per_band_subscore_produces_a_gap(self, session, completed_run):
        _, run = completed_run
        delft = results_of(session, run)["Delft University of Technology"]
        assert delft.eligibility is EligibilityStatus.GAP
        assert any("writing" in f.lower() for f in delft.hard_filter_failures)

    @pytest.mark.asyncio
    async def test_a_citizenship_restricted_award_is_marked_not_eligible(
        self, session, completed_run
    ):
        _, run = completed_run
        leuven = results_of(session, run)["KU Leuven"]
        flemish = next(s for s in leuven.scholarships if "Flemish" in s.name)
        assert flemish.classification is FundingClassification.NOT_ELIGIBLE
        # The best remaining award still carries the programme.
        assert leuven.best_funding_classification is FundingClassification.FULL_TUITION

    @pytest.mark.asyncio
    async def test_full_ride_marketing_does_not_survive_the_coverage_table(
        self, session, completed_run
    ):
        _, run = completed_run
        asu = results_of(session, run)["Arizona State University"]
        assert asu.best_funding_classification is FundingClassification.FULL_TUITION
        award = asu.scholarships[0]
        assert "not a full ride" in award.classification_reason

    @pytest.mark.asyncio
    async def test_contradicting_official_sources_are_surfaced(self, session, completed_run):
        _, run = completed_run
        delft = results_of(session, run)["Delft University of Technology"]
        assert delft.conflicts
        conflict = delft.conflicts[0]
        assert set(conflict.values) == {6.5, 6.0}
        assert "Dear Admissions Office" in conflict.question_for_admissions

    @pytest.mark.asyncio
    async def test_a_past_deadline_is_flagged_and_blocks(self, session, completed_run):
        _, run = completed_run
        melbourne = results_of(session, run)["University of Melbourne"]
        assert melbourne.deadline_passed
        assert melbourne.eligibility is EligibilityStatus.GAP

    @pytest.mark.asyncio
    async def test_a_cross_year_zero_gap_is_refused(self, session, completed_run):
        _, run = completed_run
        toronto = results_of(session, run)["University of Toronto"]
        assert not toronto.funding_gap.computable
        assert toronto.funding_gap.year_mismatch

    @pytest.mark.asyncio
    async def test_missing_funding_data_reads_as_unknown(self, session, completed_run):
        _, run = completed_run
        vienna = results_of(session, run)["University of Vienna"]
        assert vienna.best_funding_classification is FundingClassification.UNKNOWN
        assert vienna.scholarships == []
        assert vienna.unresolved

    @pytest.mark.asyncio
    async def test_an_unreachable_site_yields_insufficient_data_not_a_guess(
        self, session, completed_run
    ):
        _, run = completed_run
        oslo = results_of(session, run)["University of Oslo"]
        assert oslo.eligibility is EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION
        assert oslo.admissions_fit is AdmissionsFit.INSUFFICIENT_DATA
        assert oslo.verification_completeness == 0.0

    @pytest.mark.asyncio
    async def test_a_catalogue_only_lead_is_kept_and_flagged(self, session, completed_run):
        _, run = completed_run
        mcgill = results_of(session, run)["McGill University"]
        assert any(q.blocking for q in mcgill.unresolved)


class TestScoringAndDecisions:
    @pytest.mark.asyncio
    async def test_no_score_is_presented_as_a_probability(self, session, completed_run):
        _, run = completed_run
        for result in results_of(session, run).values():
            if result.preference_score:
                assert "not a probability" in result.preference_score.disclaimer

    @pytest.mark.asyncio
    async def test_a_sparse_result_takes_a_missing_data_penalty(self, session, completed_run):
        _, run = completed_run
        oslo = results_of(session, run)["University of Oslo"]
        assert oslo.preference_score.missing_data_penalty > 0
        assert oslo.preference_score.missing_fields

    @pytest.mark.asyncio
    async def test_every_score_component_is_explained(self, session, completed_run):
        _, run = completed_run
        groningen = results_of(session, run)["University of Groningen"]
        assert all(c.explanation for c in groningen.preference_score.components)

    @pytest.mark.asyncio
    async def test_documents_are_collected_only_for_approved_rows(self, session, completed_run):
        runner, run = completed_run
        rows = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run.id).all()
        target = next(r for r in rows if r.university == "University of Groningen")
        target.user_decision = UserDecision.APPROVED.value
        session.commit()

        built = await runner.collect_documents()
        assert built == 1
        assert run.stage == PipelineStage.COMPLETED.value

        refreshed = results_of(session, run)
        assert refreshed["University of Groningen"].checklist is not None
        assert refreshed["Arizona State University"].checklist is None

    @pytest.mark.asyncio
    async def test_a_checklist_separates_who_must_act(self, session, completed_run):
        runner, run = completed_run
        row = (
            session.query(ProgramResultRow)
            .filter(
                ProgramResultRow.run_id == run.id,
                ProgramResultRow.university == "University of Groningen",
            )
            .one()
        )
        row.user_decision = UserDecision.APPROVED.value
        session.commit()
        await runner.collect_documents()

        checklist = results_of(session, run)["University of Groningen"].checklist
        assert checklist.school_actions, "the school must have its own actions"
        assert checklist.recommender_actions, "the referee must have their own actions"
        assert checklist.ordered_steps
        # Longest lead time first.
        leads = [
            d.lead_time_days or 0
            for d in checklist.recommender_actions + checklist.applicant_actions
        ]
        assert leads[0] >= leads[-1]


class TestCancellation:
    @pytest.mark.asyncio
    async def test_a_cancelled_run_stops_and_is_marked(self, session, settings, profile):
        row = profile_row(session, profile)
        run = ResearchRun(
            profile_id=row.id,
            stage=PipelineStage.QUEUED.value,
            demo_mode=True,
            cancelled=True,
            stage_state=RunState.load(None).dump(),
        )
        session.add(run)
        session.commit()

        runner = ResearchRunner(session, run, profile, settings)
        # The cancellation propagates: swallowing it let the caller mark the
        # job succeeded for a run that never finished.
        with pytest.raises(RunCancelled):
            await runner.run_to_decision()
        assert run.stage == PipelineStage.CANCELLED.value
        assert run.finished_at is not None
