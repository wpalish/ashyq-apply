"""Capture two already-declared official logos with the shared network guards.

This offline asset reader accepts only PNG/SVG in addition to existing types,
with a tighter1MB bound. Product Fetcher configuration is not changed. Earlier
HTML-reader MIME refusals are not server access refusals. No retry on429/403.
"""
import asyncio,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from app.adapters import fetching
from app.adapters.fetching import Fetcher
fetching.MAX_ATTEMPTS=1;fetching.MAX_BYTES=1_000_000
fetching.ALLOWED_CONTENT_TYPES=(*fetching.ALLOWED_CONTENT_TYPES,'image/png','image/svg+xml')
async def main():
 out=Path(sys.argv[1]);out.mkdir(exist_ok=True);assert not (out/'STARTED').exists();(out/'STARTED').write_text('finite2 official declared images; shared guards')
 receipts=[]
 async with Fetcher(out/'cache',timeout=12) as f:
  for id,domain,page,url in [('qs2027-164','lancaster.ac.uk','https://www.lancaster.ac.uk/','https://www.lancaster.ac.uk/media/wdp/style-assets/images/logos/lu-logo.svg'),('qs2027-169','tamu.edu','https://www.tamu.edu/','https://www.tamu.edu/_files/images/logos/primaryTAM.png')]:
   r=await f.get(url);record={'id':id,'domain':domain,'page':page,'url':url,'status_code':r.status_code,'outcome':r.outcome.value,'error':r.error,'checked_at':r.fetched_at.isoformat()}
   if r.ok and r.content:
    ext='.svg' if 'svg' in r.content_type else '.png';name='identity-'+id+ext;path=ROOT/'frontend/public/universities'/name;path.write_bytes(r.content)
    record.update(status='cached',path='/universities/'+name,kind='institution_logo',canonical_website=page,content_location=url,sha256=hashlib.sha256(r.content).hexdigest())
   receipts.append(record);print(record,flush=True)
   if r.status_code in [429,403]:break
 (out/'RECEIPTS.json').write_text(json.dumps(receipts,indent=2))
 if len(receipts)==2 and all(r.get('status')=='cached' for r in receipts):(ROOT/'frontend/src/data/universityProgrammeIdentityImages.receipt.json').write_text(json.dumps(receipts,indent=2)+'\n')
if __name__=='__main__':asyncio.run(main())
