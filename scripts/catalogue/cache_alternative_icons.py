"""Public website-icon fallback for assets absent from the original caches.
The default icon is rejected by a negative control. No Wikimedia requests.
"""
import json,urllib.request,urllib.parse,hashlib,io,time
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
def read(domain,negative=False):
 url='https://icons.duckduckgo.com/ip3/'+urllib.parse.quote(domain)+'.ico'
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'UnimatchCatalogue/1.0'}),timeout=15) as f:return f.read(500000),url
 except urllib.error.HTTPError as e:
  if negative and e.code==404:return e.read(500000),url
  raise
control,_=read('nonexistent-unimatch-negative-control.invalid',negative=True);control_sha=hashlib.sha256(control).hexdigest();rows=json.loads((ROOT/'frontend/src/data/universityDirectory.json').read_text());receipt=[]
for row in rows:
 if row['image'].startswith('/'):continue
 item={'id':row['id'],'domain':row['domain'],'status':'failed','negative_control_sha256':control_sha}
 try:
  blob,url=read(row['domain']);assert hashlib.sha256(blob).hexdigest()!=control_sha,'Default icon rejected'
  image=Image.open(io.BytesIO(blob));assert image.width>=8 and image.height>=8
  dest=ROOT/'frontend/public/universities'/('site-'+row['id']+'.png');image.convert('RGBA').save(dest,'PNG')
  item.update(status='cached',content_location='https://'+row['domain'],retrieval_url=url,path='/universities/'+dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),width=image.width,height=image.height)
 except Exception as e:
  item['error']=str(e)
  if isinstance(e,urllib.error.HTTPError) and e.code in [403,429]:receipt.append(item);print('STOP',e.code,flush=True);break
 receipt.append(item);print(row['id'],item['status'],item.get('error',''),flush=True);time.sleep(.4)
(ROOT/'frontend/src/data/universityAlternativeIcons.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('DONE',sum(x['status']=='cached' for x in receipt),flush=True)
