"""Every field the form asks for must change something, or not be asked.

The audit found roughly twenty preference and funding fields that were
collected, validated, stored and exported - and never read by scoring, funding
or the pipeline. Asking someone for their budget and then ignoring it is worse
than not asking: it produces a result they believe was tailored to them.

Each test below pins one field to the behaviour it now drives. Fields that
cannot be honoured honestly were removed from the form instead, and
`docs/PROFILE_FIELDS.md` records which is which.
"""

from __future__ import annotations

import pytest

from app.domain.enums import (
    CostCategory,
    EligibilityStatus,
    FundingClassification,
    FundingFit,
)
from app.domain.scoring import score_result
from app.schemas.money import Money
from app.schemas.result import (
    CoverageBreakdown,
    FundingGap,
    ProgramResult,
    Scholarship,
)


def result(**kwargs) -> ProgramResult:
    return ProgramResult(**{
        "id": "r", "run_id": "run", "university": "Test University", "university_id": "u",
        "country": "Netherlands", "city": "Delft", "program": "BSc CS", "degree": "bachelor",
        "intake": "fall 2027",
        **kwargs,
    })


def component(res: ProgramResult, profile, name: str):
    return next(
        (c for c in score_result(res, profile).components if c.name == name),
        None,
    )


class TestUniversityShapePreferences:
    """Size and campus were asked for and read by nothing.

    The registry carries both for every bundled university, so they are graded
    exactly like city size and climate already were.
    """

    def test_the_stated_size_is_compared_with_what_the_registry_says(self):
        from app.pipeline.runner import _fit_label

        assert _fit_label("small", "small", "size") == "strong"
        assert _fit_label("medium", "small", "size") == "good"
        assert _fit_label("large", "small", "size") == "acceptable"
        # Nothing published: unknown, which scores as missing rather than bad.
        assert _fit_label(None, "small", "size") == "unknown"
        # No stated preference is not a mismatch.
        assert _fit_label("large", "any", "size") == "acceptable"

    def test_a_campus_mismatch_is_not_dressed_up_as_acceptable(self):
        """Campus has no ordering, so a near miss does not exist.

        Falling through the ladders returned "acceptable" for a known
        mismatch - the same word used when no preference was stated.
        """
        from app.pipeline.runner import _fit_label

        assert _fit_label("campus", "campus", "campus") == "strong"
        assert _fit_label("urban", "campus", "campus") == "weak"
        assert _fit_label("urban", "any", "campus") == "acceptable"
        assert _fit_label(None, "campus", "campus") == "unknown"

    def test_the_dimension_is_named_rather_than_guessed(self):
        """`size` and `city` share a vocabulary; the caller says which is meant."""
        from app.pipeline.runner import _fit_label

        # metropolis exists only on the city ladder, so asking for it under
        # `size` is a plain mismatch rather than a graded one.
        assert _fit_label("large", "metropolis", "city") == "good"
        assert _fit_label("large", "metropolis", "size") == "weak"

    def test_university_size_moves_the_score(self, profile):
        profile.preferences.university_size = "small"
        # "acceptable" is the worst a size mismatch can be: the ladder has
        # three rungs, so the gap never exceeds two.
        assert component(result(size_fit="strong"), profile, "University size").raw > (
            component(result(size_fit="acceptable"), profile, "University size").raw
        )

    def test_campus_type_moves_the_score(self, profile):
        profile.preferences.campus_type = "campus"
        assert component(result(campus_fit="strong"), profile, "Campus type").raw > (
            component(result(campus_fit="weak"), profile, "Campus type").raw
        )

    def test_an_unknown_attribute_is_missing_data_not_a_guess(self, profile):
        profile.preferences.university_size = "small"
        scored = component(result(), profile, "University size")
        assert scored.data_present is False
        assert "university size" in " ".join(score_result(result(), profile).missing_fields)


class TestFundingPreferences:
    @staticmethod
    def _award(**kwargs) -> Scholarship:
        return Scholarship(**{"id": "s", "name": "Test Award", **kwargs})

    def test_funding_criticality_changes_the_weight_of_funding(self, profile):
        rich = result(funding_fit=FundingFit.CONFIRMED_OPPORTUNITY)

        profile.funding.funding_criticality = "nice_to_have"
        relaxed = component(rich, profile, "Funding fit").weight

        profile.funding.funding_criticality = "decisive"
        decisive = component(rich, profile, "Funding fit").weight

        assert decisive > relaxed

    def test_a_must_cover_category_that_an_award_excludes_raises_a_question(self, profile):
        """"Housing must be covered" against an award that says it is not."""
        from app.domain.funding import unmet_coverage_requirements

        profile.funding.must_cover_housing = True
        award = self._award(
            coverage=[
                CoverageBreakdown(category=CostCategory.TUITION, covered="yes"),
                CoverageBreakdown(category=CostCategory.HOUSING, covered="no"),
            ]
        )
        unmet = unmet_coverage_requirements(award, profile.funding)
        assert CostCategory.HOUSING in unmet

    def test_an_unstated_category_is_not_reported_as_excluded(self, profile):
        from app.domain.funding import unmet_coverage_requirements

        profile.funding.must_cover_books = True
        award = self._award(
            coverage=[CoverageBreakdown(category=CostCategory.TUITION, covered="yes")]
        )
        # The page says nothing about books; that is unknown, not a refusal.
        assert CostCategory.BOOKS not in unmet_coverage_requirements(award, profile.funding)

    def test_requires_full_ride_marks_an_award_that_is_not_one(self, profile):
        from app.domain.funding import award_meets_shape

        profile.funding.requires_full_ride = True
        # The classification is what the shape check reads: it is the verdict
        # the coverage table produced, not the table itself.
        tuition_only = self._award(
            classification=FundingClassification.FULL_TUITION,
            coverage=[CoverageBreakdown(category=CostCategory.TUITION, covered="yes")],
        )
        met, reason = award_meets_shape(tuition_only, profile.funding)
        assert met is False
        assert "full ride" in reason.lower()

    def test_refusing_partial_awards_is_honoured(self, profile):
        from app.domain.funding import award_meets_shape

        profile.funding.requires_full_ride = False
        profile.funding.accepts_partial = False
        partial = self._award(
            classification=FundingClassification.PARTIAL,
            coverage=[CoverageBreakdown(category=CostCategory.TUITION, covered="partial")],
        )
        met, reason = award_meets_shape(partial, profile.funding)
        assert met is False
        assert "partial" in reason.lower()

    def test_max_family_contribution_appears_in_the_affordability_explanation(self, profile):
        profile.funding.max_acceptable_gap = 6000
        profile.funding.max_family_contribution = 2000
        profile.funding.budget_currency = "USD"
        scored = component(
            result(funding_gap=FundingGap(computable=True, gap=Money(amount=5000, currency="USD"))),
            profile,
            "Affordability",
        )
        assert "2,000" in scored.explanation


class TestAcademicContext:
    def test_class_rank_is_stated_in_the_explanation_without_becoming_a_score(self, profile):
        profile.academics.class_rank = 3
        profile.academics.class_size = 120
        scored = component(result(eligibility=EligibilityStatus.MET), profile, "Academic fit")

        assert "3" in scored.explanation and "120" in scored.explanation
        # Rank is context for a human, not a number this product can calibrate.
        assert scored.raw == pytest.approx(1.0)

    def test_without_a_rank_the_explanation_says_nothing_about_one(self, profile):
        profile.academics.class_rank = None
        scored = component(result(eligibility=EligibilityStatus.MET), profile, "Academic fit")
        assert "rank" not in scored.explanation.lower()


class TestAnAwardTheApplicantCannotUseDoesNotCountAsFunding:
    def test_the_programme_is_not_reported_as_funded(self, profile):
        from app.domain.funding import funding_fit_for
        from app.schemas.result import Scholarship

        unusable = Scholarship(
            id="s",
            name="Tuition discount",
            classification=FundingClassification.PARTIAL,
            meets_applicant_shape=False,
        )
        fit, classification, reason = funding_fit_for([unusable])

        assert fit is FundingFit.LIMITED_OPPORTUNITY
        assert "says why on its own row" in reason
        # Still visible: the award is not hidden, it just carries no verdict.
        assert classification is FundingClassification.PARTIAL

    def test_a_usable_award_still_carries_the_verdict(self, profile):
        from app.domain.funding import funding_fit_for
        from app.schemas.result import Scholarship

        usable = Scholarship(
            id="s", name="Full ride", classification=FundingClassification.FULL_RIDE_CONFIRMED
        )
        fit, _, _ = funding_fit_for([usable])
        assert fit is not FundingFit.LIMITED_OPPORTUNITY


class TestPreferencesThatBecomeQuestions:
    """Some answers cannot be scored, but must not vanish either.

    Co-op, work during study and research interests are not published in any
    comparable form. Scoring them would be inventing a judgement; ignoring
    them makes the form a lie. They become questions for the admissions
    office, attached to the row they concern.
    """

    @pytest.mark.asyncio
    async def test_the_run_raises_the_questions_the_pages_do_not_answer(
        self, settings, profile
    ):
        import sqlalchemy as sa
        from sqlalchemy.orm import sessionmaker

        from app.db import migrate_to_head
        from app.models import ApplicantProfileRow, ProgramResultRow, ResearchRun
        from app.pipeline.runner import ResearchRunner
        from app.pipeline.state import RunState

        profile.preferences.values_coop = True
        profile.preferences.needs_work_during_study = True
        profile.preferences.research_interests = ["quantum error correction"]

        migrate_to_head(settings.database_url)
        engine = sa.create_engine(settings.database_url, connect_args={"check_same_thread": False})
        session = sessionmaker(bind=engine, future=True)()
        row = ApplicantProfileRow(display_name="t", payload=profile.model_dump(mode="json"))
        session.add(row)
        session.flush()
        run = ResearchRun(
            profile_id=row.id, stage="queued", demo_mode=True,
            candidate_limit=4, verify_limit=4, stage_state=RunState.load(None).dump(),
        )
        session.add(run)
        session.commit()

        await ResearchRunner(session, run, profile, settings).run_to_decision()

        rows = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run.id).all()
        questions = [
            q
            for r in rows
            for q in ProgramResult.model_validate(r.payload).unresolved
        ]
        topics = {q.topic for q in questions}
        assert "study and work" in topics
        assert "research" in topics
        assert any("quantum error correction" in q.question for q in questions)

        session.close()
        engine.dispose()

    @pytest.mark.asyncio
    async def test_a_profile_with_no_such_preferences_raises_no_such_questions(
        self, settings, profile
    ):
        import sqlalchemy as sa
        from sqlalchemy.orm import sessionmaker

        from app.db import migrate_to_head
        from app.models import ApplicantProfileRow, ProgramResultRow, ResearchRun
        from app.pipeline.runner import ResearchRunner
        from app.pipeline.state import RunState

        profile.preferences.values_coop = False
        profile.preferences.needs_work_during_study = False
        profile.preferences.research_interests = []

        migrate_to_head(settings.database_url)
        engine = sa.create_engine(settings.database_url, connect_args={"check_same_thread": False})
        session = sessionmaker(bind=engine, future=True)()
        row = ApplicantProfileRow(display_name="t", payload=profile.model_dump(mode="json"))
        session.add(row)
        session.flush()
        run = ResearchRun(
            profile_id=row.id, stage="queued", demo_mode=True,
            candidate_limit=4, verify_limit=4, stage_state=RunState.load(None).dump(),
        )
        session.add(run)
        session.commit()

        await ResearchRunner(session, run, profile, settings).run_to_decision()

        rows = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run.id).all()
        topics = {
            q.topic
            for r in rows
            for q in ProgramResult.model_validate(r.payload).unresolved
        }
        assert "study and work" not in topics
        assert "research" not in topics

        session.close()
        engine.dispose()


class TestNeedBasedDocuments:
    def test_refusing_to_submit_documents_makes_a_need_based_award_unusable(self, profile):
        from app.domain.funding import award_meets_shape
        from app.schemas.result import Scholarship

        award = Scholarship(
            id="s", name="Need-based grant",
            classification=FundingClassification.NEED_BASED_POSSIBLE,
        )
        profile.funding.willing_to_submit_need_documents = False
        met, reason = award_meets_shape(award, profile.funding)
        assert met is False
        assert "financial documents" in reason

        profile.funding.willing_to_submit_need_documents = True
        assert award_meets_shape(award, profile.funding)[0] is True
