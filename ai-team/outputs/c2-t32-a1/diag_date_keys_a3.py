"""T32 A3 QA diagnostic: where do date-only strings enter the demo payloads?

Runs the demo pipeline exactly like
tests/test_freshness_regressions.py::TestDemoRunIsByteIdentical's demo_session
fixture, then walks the RAW ProgramResultRow payloads and reports every ISO
date-only string (YYYY-MM-DD) with its JSON key path, plus a leaf-key
frequency table. Purpose: decide whether masking date-only strings in
_mask_volatile is as strong as freezing the clock (i.e. whether the dates are
volatile stamps or semantic values like deadlines).

Run with the worktree venv from anywhere. Exit 0 = diagnostic completed.
"""

from __future__ import annotations

import asyncio
import re
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path("/Users/wpalish/ashyq-worktrees/c2-t32-qa-a3/backend")
sys.path.insert(0, str(BACKEND))

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from app.models import ApplicantProfileRow, Base, ResearchRun
from app.pipeline.runner import ResearchRunner
from app.pipeline.state import RunState
from tests.conftest import TEST_ORGANIZATION_ID

DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def build_profile():
    """Byte-for-byte the tests/conftest.py::profile fixture body."""
    from app.schemas.profile import (
        AcademicRecord,
        ApplicantProfileIn,
        ApplicationContext,
        FundingNeeds,
        GradeValue,
        IeltsScore,
        Preferences,
        SatScore,
    )

    return ApplicantProfileIn(
        display_name="Test Applicant (synthetic)",
        context=ApplicationContext(
            level="bachelor",
            intended_fields=["computer science"],
            intake_term="fall",
            intake_year=2027,
            citizenship="Kazakhstan",
            country_of_residence="Kazakhstan",
            education_country="Kazakhstan",
            education_system="KZ national secondary",
            graduation_date="2027-05-25",
        ),
        academics=AcademicRecord(
            gpa=GradeValue(raw_value=4.8, raw_scale_max=5.0, raw_scale_label="KZ 5-point"),
            ielts=IeltsScore(overall=7.0, listening=7.5, reading=7.5, writing=6.0, speaking=6.0),
            sat=SatScore(total=1400, math=760, reading_writing=640),
        ),
        preferences=Preferences(preferred_countries=["Netherlands", "Canada"]),
        funding=FundingNeeds(max_annual_budget=6000, max_acceptable_gap=6000),
    )


def build_settings(tmp: Path):
    """Byte-for-byte the tests/conftest.py::settings fixture body."""
    from app.config import Settings

    CORPUS = BACKEND / "app" / "corpus" / "pages"  # tests/conftest.py:33
    return Settings(
        demo_mode=True,
        database_url=f"sqlite:///{tmp / 'diag.db'}",
        cache_dir=tmp / "cache",
        export_dir=tmp / "exports",
        corpus_dir=CORPUS,
        fetch_delay_seconds=0.0,
        candidate_limit=40,
        verify_limit=20,
        academic_year="2026/27",
        target_currency="USD",
        enable_browser_tier=False,
    )


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="t32a3-diag-"))
    settings = build_settings(tmp)
    profile = build_profile()

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
    asyncio.run(ResearchRunner(session, run, profile, settings).run_to_decision())

    from app.models import ProgramResultRow

    rows = session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run.id).all()

    hits: list[tuple[str, str]] = []
    key_counter: Counter[str] = Counter()

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str) and DATE_ONLY.match(node):
            leaf = path.split(".")[-1].split("[")[0]
            hits.append((path, node))
            key_counter[leaf] += 1

    for r in rows:
        walk(r.payload, "")

    print(f"UTC now: {datetime.now(UTC).isoformat()}")
    print(f"payload rows: {len(rows)}")
    print(f"date-only strings found: {len(hits)}")
    print("--- key paths and values ---")
    for path, val in sorted(hits):
        print(f"{path} = {val!r}")
    print("--- leaf-key frequency ---")
    for k, n in sorted(key_counter.items()):
        print(f"{k}: {n}")

    session.close()
    engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
