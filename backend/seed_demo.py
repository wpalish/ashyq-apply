"""Run the full demo pipeline from the command line.

    python seed_demo.py          # profile + run + assessment
    python seed_demo.py --approve  # also approve the top rows and build checklists
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.config import get_settings
from app.corpus.demo_profile import DEMO_PROFILE
from app.db import init_db, session_scope
from app.domain.enums import PipelineStage, UserDecision
from app.models import ApplicantProfileRow, ProgramResultRow, ResearchRun
from app.pipeline.runner import ResearchRunner
from app.pipeline.state import RunState
from app.schemas.result import ProgramResult


async def main(approve: bool) -> int:
    init_db()
    settings = get_settings()
    settings.demo_mode = True

    with session_scope() as s:
        profile_row = ApplicantProfileRow(
            display_name=DEMO_PROFILE.display_name, payload=DEMO_PROFILE.model_dump(mode="json")
        )
        s.add(profile_row)
        s.flush()
        run = ResearchRun(profile_id=profile_row.id, stage=PipelineStage.QUEUED.value,
                          demo_mode=True, stage_state=RunState.load(None).dump())
        s.add(run)
        s.flush()
        run_id, profile_id = run.id, profile_row.id
        print(f"profile={profile_id}  run={run_id}")

        runner = ResearchRunner(s, run, DEMO_PROFILE, settings)
        await runner.run_to_decision()

        rows = (
            s.query(ProgramResultRow)
            .filter(ProgramResultRow.run_id == run_id)
            .order_by(ProgramResultRow.score_total.desc())
            .all()
        )
        print(f"\nstage={run.stage}  results={len(rows)}  pages={run.pages_checked} "
              f"(failed {run.pages_failed})  claims={run.claims_recorded}")
        print(f"\n{'University':34} {'Elig':10} {'Fit':16} {'Funding':22} {'Gap':>16}  Score")
        print("-" * 122)
        for row in rows:
            r = ProgramResult.model_validate(row.payload)
            gap = (
                f"{r.funding_gap.gap.amount:,.0f} {r.funding_gap.gap.currency}"
                if r.funding_gap and r.funding_gap.computable and r.funding_gap.gap
                else "not computable"
            )
            print(f"{r.university[:33]:34} {r.eligibility.value[:9]:10} {r.admissions_fit.value[:15]:16} "
                  f"{r.best_funding_classification.value[:21]:22} {gap:>16}  {row.score_total:.2f}")

        if approve:
            for row in rows[:3]:
                row.user_decision = UserDecision.APPROVED.value
                row.user_decision_reason = "Demo auto-approval"
                r = ProgramResult.model_validate(row.payload)
                r.user_decision = UserDecision.APPROVED
                row.payload = r.model_dump(mode="json")
                s.add(row)
            s.commit()
            built = await runner.collect_documents()
            print(f"\nchecklists built for {built} approved programmes")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--approve", action="store_true")
    sys.exit(asyncio.run(main(p.parse_args().approve)))
