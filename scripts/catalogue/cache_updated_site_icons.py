"""Apply institution website changes corroborated by public institutional pages."""
import json,urllib.request,urllib.parse,io,hashlib,time
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];updates=json.loads((ROOT/'scripts/catalogue/identity_canonical_websites.json').read_text());rows=json.loads((ROOT/'frontend/src/data/universityDirectory.json').read_text());receipt=[]
for row in rows:
 if row['id'] not in updates:continue
 url='https://www.google.com/s2/favicons?'+urllib.parse.urlencode({'domain_url':updates[row['id']],'sz':128});item={'id':row['id'],'domain':row['domain'],'canonical_website':updates[row['id']],'status':'failed'}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'UnimatchCatalogue/1.0'}),timeout=16) as response:blob=response.read(500000);origin=response.headers.get('Content-Location');assert origin,'Missing source asset location'
  image=Image.open(io.BytesIO(blob));assert image.width>=8 and image.height>=8;dest=ROOT/'frontend/public/universities'/('updated-'+row['id']+'.png');image.convert('RGBA').save(dest,'PNG');item.update(status='cached',content_location=origin,retrieval_url=url,path='/universities/'+dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
 except Exception as e:
  item['error']=str(e)
  if isinstance(e,urllib.error.HTTPError) and e.code in [403,429]:receipt.append(item);print('STOP',e.code,flush=True);break
 receipt.append(item);print(row['id'],item['status'],item.get('error',''),flush=True);time.sleep(.5)
(ROOT/'frontend/src/data/universityUpdatedIcons.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
