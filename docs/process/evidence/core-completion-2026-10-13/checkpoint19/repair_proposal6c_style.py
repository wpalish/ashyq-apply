from pathlib import Path
s=Path(__file__).resolve().parent
p=s/'repairs6c-proposal/backend/tests/test_result_read_freshness.py'
t=p.read_text().replace('    from app.api import routes_results\n','    from app.api import routes_results\n    from app.domain.enums import ClaimType\n').replace('value.claim_type = kind','value.claim_type = ClaimType(kind)')
p.write_text(t)
