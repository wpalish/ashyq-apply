from app.db import init_db, session_scope
from app.models import ProgramResultRow
from app.schemas.result import ProgramResult
init_db()
with session_scope() as s:
    rows = s.query(ProgramResultRow).order_by(ProgramResultRow.score_total.desc()).all()
    print(f"{'University':30} {'total':>6} {'max':>5} {'pen':>5} | components (weighted; * = missing)")
    for r in rows[:8]:
        p = ProgramResult.model_validate(r.payload)
        sc = p.preference_score
        comps = " ".join(f"{c.name[:6]}={c.weighted:.2f}{'*' if not c.data_present else ''}" for c in sc.components if c.weight>0)
        print(f"{p.university[:30]:30} {sc.total:6.2f} {sc.max_possible:5.2f} {sc.missing_data_penalty:5.2f} | {comps}")
    print("\nmissing fields on top row:", ProgramResult.model_validate(rows[0].payload).preference_score.missing_fields)
    # How many of the 40 candidates have climate attribute at all
