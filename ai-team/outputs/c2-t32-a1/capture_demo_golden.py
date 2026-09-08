"""Capture the R6 demo byte-identity golden on baseline 2ed4f51 (T32 A1 QA).

Replicates tests/test_pipeline.py's completed_run fixture exactly (SQLite
create_all, conftest settings/profile fixtures, demo corpus) and prints the
canonical JSON dump of every ProgramResultRow payload, with volatile values
(uuid4 hex ids, ISO timestamps) masked.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path("/Users/wpalish/ashyq-worktrees/c2-t32-qa/backend")
sys.path.insert(0, str(BACKEND))

import sqlalchemy as sa  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config import Settings  # noqa: E402
from app.models import ApplicantProfileRow, Base, ProgramResultRow, ResearchRun  # noqa: E402
from app.pipeline.runner import ResearchRunner  # noqa: E402
from app.pipeline.state import RunState  # noqa: E402
from tests.conftest import TEST_ORGANIZATION_ID, profile_row  # noqa: E402
from app.schemas.profile import ApplicantProfileIn  # noqa: E402

UUID_HEX = re.compile(r"^[0-9a-f]{32}$")
ISO_TS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def mask(node):
    if isinstance(node, dict):
        return {k: mask(v) for k, v in node.items()}
    if isinstance(node, list):
        return [mask(v) for v in node]
    if isinstance(node, str):
        if UUID_HEX.match(node):
            return "<uuid>"
        if ISO_TS.match(node):
            return "<ts>"
    return node


def main() -> int:
    corpus_dir = BACKEND / "app" / "corpus" / "pages"
    tmp = Path(tempfile.mkdtemp(prefix="t32-golden-"))
    settings = Settings(
        demo_mode=True,
        database_url=f"sqlite:///{tmp / 'golden.db'}",
        cache_dir=tmp / "cache",
        export_dir=tmp / "exports",
        corpus_dir=corpus_dir,
        fetch_delay_seconds=0.0,
        candidate_limit=40,
        verify_limit=20,
        academic_year="2026/27",
        target_currency="USD",
        enable_browser_tier=False,
    )
    profile = ApplicantProfileIn(
        display_name="Test Applicant (synthetic)",
        context={
            "level": "bachelor",
            "intended_fields": ["computer science"],
            "intake_term": "fall",
            "intake_year": 2027,
            "citizenship": "Kazakhstan",
            "country_of_residence": "Kazakhstan",
            "education_country": "Kazakhstan",
            "education_system": "KZ national secondary",
            "graduation_date": "2027-05-25",
        },
        academics={
            "gpa": {"raw_value": 4.8, "raw_scale_max": 5.0, "raw_scale_label": "KZ 5-point"},
            "ielts": {
                "overall": 7.0,
                "listening": 7.5,
                "reading": 7.5,
                "writing": 6.0,
                "speaking": 7.0,
            },
            "sat": {"total": 1400, "math": 760, "reading_writing": 640},
        },
        preferences={"preferred_countries": ["Netherlands", "Canada"]},
        funding={"max_annual_budget": 6000, "max_acceptable_gap": 6000},
    )
    engine = sa.create_engine(settings.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    row = ApplicantProfileRow(
        organization_id=TEST_ORGANIZATION_ID,
        display_name="t",
        payload=profile.model_dump(mode="json"),
    )
    session.add(row)
    session.flush()
    run = ResearchRun(
        profile_id=row.id,
        stage="queued",
        demo_mode=True,
        stage_state=RunState.load(None).dump(),
    )
    session.add(run)
    session.flush()
    runner = ResearchRunner(session, run, profile, settings)
    import asyncio

    asyncio.run(runner.run_to_decision())
    rows = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run.id).all()
    payloads = [mask(r.payload) for r in rows]
    payloads.sort(key=lambda p: (p["university"], p["program"]))
    print(json.dumps(payloads, sort_keys=True, indent=1))
    session.close()
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
