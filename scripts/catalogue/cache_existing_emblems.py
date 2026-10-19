"""Cache already-sourced static emblem files; no encyclopedia API or article calls.
One request per existing asset, no retry. Stop at the first rate-limit response.
"""
import json,urllib.request,urllib.parse,re,io,hashlib,time
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
rows=json.loads((ROOT/'frontend/src/data/universityDirectory.json').read_text());receipt=[]
for row in rows:
 url=row['image']
 if not url.startswith('https://upload.wikimedia.org/'):continue
 path=urllib.parse.urlsplit(url).path
 if '/thumb/' in path:path=path.replace('/thumb/','/',1).rsplit('/',1)[0]
 source='https://upload.wikimedia.org'+path
 item={'id':row['id'],'domain':row['domain'],'source_url':url,'content_location':source,'status':'failed'}
 try:
  req=urllib.request.Request(source,headers={'User-Agent':'UnimatchCatalogue/1.0 (public institutional identity asset snapshot)'})
  with urllib.request.urlopen(req,timeout=16) as f:blob=f.read(1500000);mime=f.headers.get('Content-Type','')
  if 'svg' in mime or b'<svg' in blob[:500]:
   assert not re.search(br'<!DOCTYPE|<!ENTITY|<script|<foreignObject|(?:href|src)\s*=\s*["\'](?:https?:|//)',blob,re.I)
   dest=ROOT/'frontend/public/universities'/('emblem-'+row['id']+'.svg');dest.write_bytes(blob)
  else:
   image=Image.open(io.BytesIO(blob));assert 8<=image.width<=4096 and 8<=image.height<=4096;dest=ROOT/'frontend/public/universities'/('emblem-'+row['id']+'.png');image.convert('RGBA').save(dest,'PNG')
  item.update(status='cached',kind='emblem',path='/universities/'+dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
 except Exception as e:
  item['error']=str(e)
  if isinstance(e,urllib.error.HTTPError) and e.code==429:receipt.append(item);print('STOP429',row['id'],flush=True);break
 receipt.append(item);print(row['id'],item['status'],item.get('error',''),flush=True);time.sleep(.3)
(ROOT/'frontend/src/data/universityEmblems.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('DONE',sum(x['status']=='cached' for x in receipt),flush=True)
