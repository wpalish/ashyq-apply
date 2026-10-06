import json
import os
from pathlib import Path

root = Path('/tmp/unimatch-expert500-main57-gates-20261006')
os.environ.update(UNIMATCH_EXA_API_KEY='', UNIMATCH_DATABASE_URL=f'sqlite:///{root / "demo.db"}', UNIMATCH_DEMO_MODE='true', UNIMATCH_ENABLE_BROWSER_TIER='false')
from app.config import Settings, get_settings
Settings.model_config['env_file'] = None
get_settings.cache_clear()
from app.db import session_scope
from app.models import ProgramResultRow
from app.schemas.result import ProgramResult
with session_scope() as session:
    rows = session.query(ProgramResultRow).order_by(ProgramResultRow.score_total.desc()).all()
    results = [ProgramResult.model_validate(row.payload) for row in rows]
    ubc = [r for r in results if r.university == 'University of British Columbia']
    buckets = [r.ranking.bucket.value if r.ranking else None for r in ubc]
    receipt = {'source': 'isolated bundled synthetic demo', 'results': len(results), 'first': results[0].university if results else None, 'ubc_buckets': buckets, 'measured_pilot': False}
    receipt['passed'] = len(results) == 20 and receipt['first'] == 'University of Groningen' and bool(ubc) and all(v == 'OUT_OF_BUDGET' for v in buckets)
    (root / 'demo-readonly-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))
    if not receipt['passed']:
        raise SystemExit(1)
