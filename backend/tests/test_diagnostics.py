"""Failures and unknowns are different things and are reported differently."""

from __future__ import annotations

import pytest

from app.domain.diagnostics import DiagnosticKind, classify, split


class TestClassification:
    @pytest.mark.parametrize(
        "message",
        [
            "fixture://tum/program-0.html: no statement about the application window for fall 2027",
            "general_admissions pages cannot confirm that 'BSc Informatics' exists.",
            "No candidate matched University of Nowhere (Netherlands); its funding was not read.",
            "intake status is unknown",
        ],
    )
    def test_a_page_that_does_not_say_is_an_unknown(self, message):
        assert classify(message) is DiagnosticKind.UNKNOWN

    @pytest.mark.parametrize(
        "message",
        [
            "https://example.edu/fees: timeout after 20s",
            "https://example.edu/x: HTTP error 503",
            "https://example.edu/y: robots.txt disallows this path",
            "https://example.edu/z: blocked by the network policy",
            "https://example.edu/q: response could not be parsed",
        ],
    )
    def test_a_page_that_could_not_be_read_is_a_failure(self, message):
        assert classify(message) is DiagnosticKind.FAILURE

    def test_a_failure_wins_a_tie(self):
        """"Timed out while confirming X" is a failure, not a normal unknown."""
        assert classify("timed out while trying to confirm that the programme exists") is (
            DiagnosticKind.FAILURE
        )

    def test_unrecognised_wording_is_reported_rather_than_filed_as_normal(self):
        assert classify("something nobody has seen before") is DiagnosticKind.FAILURE

    def test_split_keeps_order_within_each_bucket(self):
        failures, unknowns = split(
            [
                "timeout after 20s",
                "cannot confirm that it exists",
                "HTTP error 500",
                "no statement about fees",
            ]
        )
        assert failures == ["timeout after 20s", "HTTP error 500"]
        assert unknowns == ["cannot confirm that it exists", "no statement about fees"]


class TestARunSeparatesThem:
    @pytest.mark.asyncio
    async def test_a_clean_demo_run_reports_no_failures(self, settings, profile):
        """The audited symptom: 47 entries under "Research limitations" on a
        run where nothing had gone wrong."""
        import sqlalchemy as sa
        from sqlalchemy.orm import sessionmaker

        from app.db import migrate_to_head
        from app.models import ApplicantProfileRow, ResearchRun
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
            candidate_limit=8, verify_limit=8, stage_state=RunState.load(None).dump(),
        )
        session.add(run)
        session.commit()

        await ResearchRunner(session, run, profile, settings).run_to_decision()
        session.refresh(run)

        assert run.unknowns, "the bundled corpus does leave things unstated"
        assert not run.errors, f"nothing failed, yet errors reported: {run.errors[:3]}"

        session.close()
        engine.dispose()
