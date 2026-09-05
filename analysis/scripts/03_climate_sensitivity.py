"""Fair test: recompute the frozen fit labels for a new preference, then rescore."""
from app.db import init_db, session_scope
from app.models import ProgramResultRow
from app.schemas.result import ProgramResult
from app.corpus.demo_profile import DEMO_PROFILE
from app.domain.scoring import score_result
from app.pipeline.runner import _fit_label
import json
init_db()
catalog = {r["name"]: r for r in json.load(open("app/corpus/pages/catalog.json"))}
with session_scope() as s:
    rows = s.query(ProgramResultRow).all()
    results = [ProgramResult.model_validate(r.payload) for r in rows]

def run(climate, label):
    p = DEMO_PROFILE.model_copy(deep=True)
    p.preferences.climate = climate
    out = []
    for r in results:
        r2 = r.model_copy(deep=True)
        r2.climate_fit = _fit_label(catalog[r.university]["climate"], climate, "climate")
        out.append((score_result(r2, p).total, r.university, r2.climate_fit))
    out.sort(reverse=True)
    print(f"\n--- climate = {climate} ---")
    for t,u,c in out[:6]:
        print(f"  {t:5.2f} {u[:30]:31} {c}")
    return out

b = run("temperate", "")
w = run("warm", "")
c = run("cold", "")
bm = {u:t for t,u,_ in b}; wm = {u:t for t,u,_ in w}
print("\nmax |delta| temperate->warm:", round(max(abs(wm[u]-bm[u]) for u in bm),3),
      " of max_possible 8.45 (=", round(100*max(abs(wm[u]-bm[u]) for u in bm)/8.45,1), "%)")
print("top-5 identical temperate vs warm?", [u for _,u,_ in b[:5]] == [u for _,u,_ in w[:5]])
print("top-5 identical temperate vs cold?", [u for _,u,_ in b[:5]] == [u for _,u,_ in c[:5]])
