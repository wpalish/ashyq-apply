"""Two ways the pipeline used to guess, and no longer does.

Both defects came from the same habit: reaching for a cheap string operation
where the honest answer was "this cannot be settled from the page".
"""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.citizenship import CitizenshipMatch, match_citizenship
from app.domain.dates import is_ambiguous, parse_published_date


class TestCitizenshipMatching:
    def test_a_neighbouring_country_is_not_a_match(self):
        """'Korea' is a substring of 'North Korea only' — and a different country."""
        verdict, reason = match_citizenship(["North Korea only"], ["Korea"])
        assert verdict is CitizenshipMatch.NOT_APPLICABLE
        assert "not eligible" in reason

    def test_an_exact_country_matches(self):
        verdict, _ = match_citizenship(["Kazakhstan", "Uzbekistan"], ["Kazakhstan"])
        assert verdict is CitizenshipMatch.MET

    def test_a_demonym_matches_its_country(self):
        for restriction in ("Kazakhstani citizens", "Kazakh nationals only"):
            verdict, _ = match_citizenship([restriction], ["Kazakhstan"])
            assert verdict is CitizenshipMatch.MET, restriction

    def test_a_group_restriction_is_pending_not_a_refusal(self):
        """The old substring test struck this award off the applicant's list."""
        verdict, reason = match_citizenship(["Central Asian nationals"], ["Kazakhstan"])
        assert verdict is CitizenshipMatch.PENDING
        assert "admissions office" in reason

    @pytest.mark.parametrize(
        "restriction",
        ["students from developing countries", "Commonwealth nationals", "Asian applicants"],
    )
    def test_other_vague_groups_are_also_left_open(self, restriction):
        verdict, _ = match_citizenship([restriction], ["Kazakhstan"])
        assert verdict is CitizenshipMatch.PENDING

    def test_a_bloc_with_a_published_membership_list_is_answered(self):
        """EEA membership is a fact, not a fuzzy group: Kazakhstan is not in it."""
        outside, _ = match_citizenship(["European Economic Area", "Switzerland"], ["Kazakhstan"])
        assert outside is CitizenshipMatch.NOT_APPLICABLE

        inside, _ = match_citizenship(["European Economic Area"], ["Norway"])
        assert inside is CitizenshipMatch.MET

        eu, _ = match_citizenship(["EU citizens"], ["Portugal"])
        assert eu is CitizenshipMatch.MET

    def test_a_second_citizenship_counts(self):
        verdict, _ = match_citizenship(["Turkey"], ["Kazakhstan", "Turkey"])
        assert verdict is CitizenshipMatch.MET

    def test_a_plain_list_that_excludes_the_applicant_is_a_refusal(self):
        verdict, _ = match_citizenship(["Germany, France, Italy"], ["Kazakhstan"])
        assert verdict is CitizenshipMatch.NOT_APPLICABLE

    def test_an_unreadable_restriction_is_pending(self):
        verdict, _ = match_citizenship(["only"], ["Kazakhstan"])
        assert verdict is CitizenshipMatch.PENDING


class TestPublishedDates:
    def test_an_ambiguous_numeric_date_is_refused(self):
        """03/04/2027 is 3 April in Britain and 4 March in America."""
        assert parse_published_date("03/04/2027") is None
        assert is_ambiguous("03/04/2027") is True

    def test_a_date_with_only_one_valid_reading_is_kept(self):
        assert parse_published_date("25/05/2027") == date(2027, 5, 25)
        assert is_ambiguous("25/05/2027") is False

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("2027-05-25", date(2027, 5, 25)),
            ("May 25, 2027", date(2027, 5, 25)),
            ("25 May 2027", date(2027, 5, 25)),
            ("25 Jan 2027", date(2027, 1, 25)),
        ],
    )
    def test_unambiguous_formats_still_parse(self, text, expected):
        assert parse_published_date(text) == expected
        assert is_ambiguous(text) is False

    def test_a_date_object_passes_through(self):
        assert parse_published_date(date(2027, 5, 25)) == date(2027, 5, 25)

    def test_nonsense_is_none_without_raising(self):
        assert parse_published_date("rolling admissions") is None
        assert parse_published_date(None) is None


class TestGovernmentEvidenceReachesEveryRow:
    """A value on screen must carry its own source, in its own row.

    Post-study-work rights were fetched once per country and cached as a bare
    string, so the second and later universities in that country displayed the
    right with no claim behind it.
    """

    @pytest.mark.asyncio
    async def test_two_universities_in_one_country_both_carry_the_claim(
        self, settings, profile, tmp_path
    ):
        import sqlalchemy as sa
        from sqlalchemy.orm import sessionmaker

        from app.db import migrate_to_head
        from app.domain.enums import ClaimType
        from app.models import ApplicantProfileRow, ClaimRow, ProgramResultRow, ResearchRun
        from app.pipeline.runner import ResearchRunner
        from app.pipeline.state import RunState

        migrate_to_head(settings.database_url)
        engine = sa.create_engine(settings.database_url, connect_args={"check_same_thread": False})
        session = sessionmaker(bind=engine, future=True)()

        row = ApplicantProfileRow(display_name="t", payload=profile.model_dump(mode="json"))
        session.add(row)
        session.flush()
        run = ResearchRun(
            profile_id=row.id, stage="queued", demo_mode=True,
            candidate_limit=12, verify_limit=12, stage_state=RunState.load(None).dump(),
        )
        session.add(run)
        session.commit()

        await ResearchRunner(session, run, profile, settings).run_to_decision()

        rows = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run.id).all()
        by_country: dict[str, list[ProgramResultRow]] = {}
        for r in rows:
            by_country.setdefault(r.country, []).append(r)
        repeated = [rs for rs in by_country.values() if len(rs) > 1]
        assert repeated, "the corpus must give at least one country twice for this to mean anything"

        for group in repeated:
            for result_row in group:
                claims = (
                    session.query(ClaimRow)
                    .filter(
                        ClaimRow.result_id == result_row.id,
                        ClaimRow.claim_type == ClaimType.POST_STUDY_WORK.value,
                    )
                    .all()
                )
                payload = result_row.payload
                if not payload.get("post_study_work"):
                    continue
                assert claims, (
                    f"{result_row.university} shows a post-study-work right with no claim"
                )
                assert all(c.source_url for c in claims)
                assert any(c.source_url in payload["source_urls"] for c in claims)

        session.close()
        engine.dispose()
