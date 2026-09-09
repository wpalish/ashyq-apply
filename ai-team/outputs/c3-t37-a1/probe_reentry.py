"""T37 A1 probe: does a funding_discovery stage re-entry duplicate claims/conflicts?

Runs the same scenario the planned TestFundingReEntry will assert, on the
baseline, and prints the before/after count tables. Not a test — evidence.
"""

import asyncio
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path("/Users/wpalish/ashyq-worktrees/c3-t37-qa/backend")
sys.path.insert(0, str(BACKEND))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config import Settings  # noqa: E402
from app.domain.enums import STAGE_ORDER, PipelineStage, UserDecision  # noqa: E402
from app.models import (  # noqa: E402
    Base,
    ClaimRow,
    ConflictRow,
    ProgramResultRow,
    ResearchRun,
)
from app.pipeline.runner import ResearchRunner  # noqa: E402
from app.pipeline.state import RunState  # noqa: E402
from app.schemas.result import ProgramResult  # noqa: E402
from tests.conftest import TEST_ORGANIZATION_ID, profile as profile_fixture, profile_row  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="t37-probe-"))
CORPUS = BACKEND / "app" / "corpus" / "pages"
if not CORPUS.exists():
    from app.corpus.build import build

    build()

settings = Settings(
    demo_mode=True,
    database_url=f"sqlite:///{TMP / 'probe.db'}",
    cache_dir=TMP / "cache",
    export_dir=TMP / "exports",
    corpus_dir=CORPUS,
    fetch_delay_seconds=0.0,
    candidate_limit=40,
    verify_limit=20,
    academic_year="2026/27",
    target_currency="USD",
    enable_browser_tier=False,
)
profile = profile_fixture.__wrapped__()

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
session = sessionmaker(bind=engine)()

prow = profile_row(session, profile)
run = ResearchRun(
    profile_id=prow.id,
    stage=PipelineStage.QUEUED.value,
    demo_mode=True,
    stage_state=RunState.load(None).dump(),
)
session.add(run)
session.flush()
runner = ResearchRunner(session, run, profile, settings)
asyncio.run(runner.run_to_decision())

rows = (
    session.query(ProgramResultRow)
    .filter(ProgramResultRow.run_id == run.id)
    .order_by(ProgramResultRow.id)
    .all()
)


def snapshot():
    claims = session.query(ClaimRow).filter(ClaimRow.run_id == run.id).all()
    conflicts = session.query(ConflictRow).filter(ConflictRow.run_id == run.id).all()
    return {
        "total": Counter(c.result_id for c in claims),
        "sch": Counter(
            c.result_id for c in claims if c.claim_type.startswith("scholarship_")
        ),
        "verify": Counter(
            c.result_id for c in claims if not c.claim_type.startswith("scholarship_")
        ),
        "conflicts": Counter(c.result_id for c in conflicts),
        "funding_conflicts": Counter(
            c.result_id for c in conflicts if c.claim_type.startswith("scholarship_")
        ),
        "conflict_types": Counter(c.claim_type for c in conflicts),
        "claim_types": Counter(c.claim_type for c in claims),
    }


before = snapshot()

# Funding stage re-entry: exactly the routes_research.py:429-439 reset for
# stage=funding_discovery.
state = RunState.load(run.stage_state)
order = [s.value for s in STAGE_ORDER]
from_index = order.index(PipelineStage.FUNDING_DISCOVERY.value)
for name, st in state.stages.items():
    after_entry_point = name in order and order.index(name) >= from_index
    if after_entry_point or st.status in ("failed", "running"):
        st.status = "pending"
        st.error = ""
run.stage_state = state.dump()
run.stage = PipelineStage.QUEUED.value
run.cancelled = False
session.commit()

print("stage_state after reset:")
for name, st in state.stages.items():
    print(f"  {name}: {st.status}")

runner2 = ResearchRunner(session, run, profile, settings)
asyncio.run(runner2.run_to_decision())

after = snapshot()

# Which stages actually re-ran?
state2 = RunState.load(run.stage_state)
print("stage_state after re-run:")
for name, st in state2.stages.items():
    print(f"  {name}: {st.status}")

print(f"\nrows: {len(rows)}; run.claims_recorded={run.claims_recorded}")
print("\nconflict types (after):", dict(after["conflict_types"]))
sch_types = {t: n for t, n in after["claim_types"].items() if t.startswith("scholarship_")}
print("scholarship claim types (after):", sch_types)

print(
    "\n{:50s} {:>6} {:>6} | {:>6} {:>6} | {:>6} {:>6} | {:>4} {:>4} | {:>4} {:>4}".format(
        "result", "tot@", "tot#", "sch@", "sch#", "ver@", "ver#", "cf@", "cf#", "fcf@", "fcf#"
    )
)
doubled_sch = 0
doubled_conf = 0
for row in rows:
    b, a = row.id, row.id
    print(
        "{:50s} {:>6} {:>6} | {:>6} {:>6} | {:>6} {:>6} | {:>4} {:>4} | {:>4} {:>4}".format(
            (row.university[:48]),
            before["total"][b],
            after["total"][a],
            before["sch"][b],
            after["sch"][a],
            before["verify"][b],
            after["verify"][a],
            before["conflicts"][b],
            after["conflicts"][a],
            before["funding_conflicts"][b],
            after["funding_conflicts"][a],
        )
    )
    if before["sch"][b] > 0 and after["sch"][a] > before["sch"][b]:
        doubled_sch += 1
    if after["conflicts"][a] > before["conflicts"][b]:
        doubled_conf += 1

print(f"\nresults with doubled scholarship claims: {doubled_sch}")
print(f"results with doubled conflicts: {doubled_conf}")

# Decision-preservation recipe (routes_results.py:276-286) applied to row 0,
# then re-entry again would re-run everything — here just confirm the fields
# _update_result carries over exist on the row.
target = rows[0]
result = ProgramResult.model_validate(target.payload)
result.user_decision = UserDecision.APPROVED
result.user_decision_reason = "shortlisted"
result.user_notes = "call the office"
result.decided_at = datetime.now(UTC)
target.user_decision = result.user_decision.value
target.user_decision_reason = result.user_decision_reason
target.user_notes = result.user_notes
target.decided_at = result.decided_at
target.payload = result.model_dump(mode="json")
session.commit()
print(f"\ndecision set on {target.university}: row={target.user_decision}, "
      f"payload={ProgramResult.model_validate(target.payload).user_decision}")
print("OK")

# ---- per-assertion baseline classification (mirrors TestFundingReEntry) ----
print("\n--- per-assertion classification on baseline (fresh scenario) ---")

run_b = ResearchRun(
    profile_id=prow.id,
    stage=PipelineStage.QUEUED.value,
    demo_mode=True,
    stage_state=RunState.load(None).dump(),
)
session.add(run_b)
session.flush()
asyncio.run(ResearchRunner(session, run_b, profile, settings).run_to_decision())
rows_b = (
    session.query(ProgramResultRow)
    .filter(ProgramResultRow.run_id == run_b.id)
    .order_by(ProgramResultRow.id)
    .all()
)
decided = next(r for r in rows_b if r.university == "University of Groningen")
res = ProgramResult.model_validate(decided.payload)
res.user_decision = UserDecision.APPROVED
res.user_decision_reason = "shortlisted"
res.user_notes = "call the office"
res.decided_at = datetime.now(UTC)
decided.user_decision = res.user_decision.value
decided.user_decision_reason = res.user_decision_reason
decided.user_notes = res.user_notes
decided.decided_at = res.decided_at
decided.payload = res.model_dump(mode="json")
delft = next(r for r in rows_b if r.university == "Delft University of Technology")
session.add(
    ClaimRow(
        run_id=run_b.id,
        result_id=delft.id,
        claim_type="scholarship_amount",
        status="SUPERSEDED",
        source_url="https://delft.example/scholarships-2025",
        source_specificity="scholarship_administrator",
        accessed_at=datetime.now(UTC),
        payload={"claim_type": "scholarship_amount", "status": "SUPERSEDED",
                 "normalized_value": 5000},
    )
)
session.commit()

def counts_b():
    claims = session.query(ClaimRow).filter(ClaimRow.run_id == run_b.id).all()
    confs = session.query(ConflictRow).filter(ConflictRow.run_id == run_b.id).all()
    return (
        Counter(c.result_id for c in claims),
        Counter(c.result_id for c in claims if c.claim_type.startswith("scholarship_")),
        Counter(c.result_id for c in claims if not c.claim_type.startswith("scholarship_")),
        Counter(c.result_id for c in confs),
    )

t0, s0, v0, cf0 = counts_b()

state = RunState.load(run_b.stage_state)
order = [s.value for s in STAGE_ORDER]
from_index = order.index(PipelineStage.FUNDING_DISCOVERY.value)
for name, st in state.stages.items():
    if (name in order and order.index(name) >= from_index) or st.status in ("failed", "running"):
        st.status = "pending"
        st.error = ""
run_b.stage_state = state.dump()
run_b.stage = PipelineStage.QUEUED.value
run_b.cancelled = False
session.commit()
asyncio.run(ResearchRunner(session, run_b, profile, settings).run_to_decision())

t1, s1, v1, cf1 = counts_b()

def check(label, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  ({label}) {detail}")

check("1 totals unchanged", t1 == t0, f"Groningen {t0[decided.id]} -> {t1[decided.id]}")
check("1 scholarship sums unchanged", s1 == s0,
      f"Groningen {s0[decided.id]} -> {s1[decided.id]}")
check("2 verify-family unchanged", v1 == v0,
      f"Delft {v0[delft.id]} -> {v1[delft.id]}")
ok3 = (decided.user_decision == "approved" and decided.user_decision_reason == "shortlisted"
       and decided.user_notes == "call the office" and decided.decided_at is not None)
ref = ProgramResult.model_validate(decided.payload)
ok3p = (ref.user_decision is UserDecision.APPROVED and ref.user_decision_reason == "shortlisted"
        and ref.user_notes == "call the office" and ref.decided_at is not None)
check("3 user_* on row", ok3, f"row={decided.user_decision}")
check("3 user_* in payload", ok3p, f"payload={ref.user_decision}")
kept = session.query(ClaimRow).filter(
    ClaimRow.result_id == delft.id, ClaimRow.status == "SUPERSEDED").all()
check("4 SUPERSEDED alive", len(kept) == 1 and kept[0].payload["status"] == "SUPERSEDED",
      f"rows={len(kept)}")
check("5 conflicts unchanged", cf1 == cf0,
      f"Delft {cf0[delft.id]} -> {cf1[delft.id]}; funding-family conflicts in corpus: "
      f"{sum(1 for c in session.query(ConflictRow).filter(ConflictRow.run_id == run_b.id).all() if c.claim_type.startswith('scholarship_'))}")
