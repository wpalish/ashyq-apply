from pathlib import Path
import subprocess
s=Path(__file__).resolve().parent
p=s/'repairs6c-proposal/backend/app/api/routes_results.py';t=p.read_text();old='q.order_by(ClaimRow.claim_type).limit(limit).offset(offset).all()';assert t.count(old)==1;t=t.replace(old,'q.order_by(ClaimRow.claim_type, ClaimRow.id).limit(limit).offset(offset).all()');p.write_text(t)
p=s/'repairs6c-proposal/backend/tests/test_result_read_freshness.py';t=p.read_text();t=t.replace('import pytest\nfrom app.', 'import pytest\n\nfrom app.');p.write_text(t)
