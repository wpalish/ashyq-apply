"""Cache identity icons locally, keeping the upstream content location and exact hashes.
Single worker, no retries. Stops on 429; never invokes the rate-limited Wikipedia API.
"""
import json,time,urllib.request,urllib.parse,hashlib,io
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
rows=json.loads((ROOT/'frontend/src/data/universityDirectory.json').read_text())
out=ROOT/'frontend/public/universities';out.mkdir(parents=True,exist_ok=True)
receipt=[]
for i,row in enumerate(rows):
 domain=row['domain'];url='https://www.google.com/s2/favicons?'+urllib.parse.urlencode({'domain':domain,'sz':128})
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'UnimatchCatalogue/1.0 (public university identity icons)'})
  with urllib.request.urlopen(req,timeout=16) as response:
   blob=response.read(300000);mime=response.headers.get('Content-Type','');origin=response.headers.get('Content-Location');assert mime.startswith('image/'),mime
   icon=Image.open(io.BytesIO(blob));assert 8<=icon.width<=1024 and 8<=icon.height<=1024
   dest=out/(row['id']+'.png');icon.convert('RGBA').save(dest,'PNG')
   receipt.append({'id':row['id'],'domain':domain,'request_url':url,'content_location':origin,'mime':mime,'width':icon.width,'height':icon.height,'path':'/universities/'+dest.name,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'status':'cached'})
 except Exception as e:
  receipt.append({'id':row['id'],'domain':domain,'status':'failed','error':str(e)})
  if isinstance(e,urllib.error.HTTPError) and e.code==429:
   print('STOP429',i,flush=True);break
 print(i+1,row['id'],receipt[-1]['status'],flush=True)
 if i%10==0:(ROOT/'frontend/src/data/universityIcons.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 time.sleep(.45)
(ROOT/'frontend/src/data/universityIcons.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('DONE',sum(x['status']=='cached' for x in receipt),'of',len(rows),flush=True)
