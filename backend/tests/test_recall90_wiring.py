"""The actual pipeline can opt in; production defaults stay conservative."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.models import Base, ResearchRun
from app.pipeline.runner import ResearchRunner
from app.pipeline.state import RunState
from tests.conftest import profile_row


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
async def test_native_demo_pipeline_wires_explicit_frontier_flag(
    settings, profile, monkeypatch, enabled
):
    from app.pipeline import runner as module

    observed = []

    class ObservedRequirements(WebRequirementsAdapter):
        def __init__(self, *args, **kwargs):
            observed.append(kwargs.get("question_frontier", False))
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(module, "WebRequirementsAdapter", ObservedRequirements)
    settings.research_question_frontier = enabled
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        row = profile_row(session, profile)
        session.add(row)
        session.flush()
        run = ResearchRun(
            profile_id=row.id,
            demo_mode=True,
            stage="queued",
            stage_state=RunState.load(None).dump(),
        )
        session.add(run)
        session.flush()
        await ResearchRunner(session, run, profile, settings).run_to_decision()
        assert observed == [enabled]
        assert run.stage == "awaiting_user_decision"
        assert run.programs_verified > 0
    engine.dispose()
