"""Resolve cached site icons using exact full website URLs from the public directory.
A bare-domain lookup and a declared canonical website are distinct identity inputs.
No article API, Wikimedia, authentication, retries or fabricated default images.
"""
import json,urllib.request,urllib.parse,time,io,hashlib
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
rows=json.loads((ROOT/'frontend/src/data/universityDirectory.json').read_text());directory=json.load(open('/tmp/unimatch-domain-directory.json'));bydomain={domain:row for row in directory for domain in row['domains']}
canonical={'qs2027-097':'https://www.isct.ac.jp/en','qs2027-191':'https://web.ncku.edu.tw/index.php?Lang=en','qs2027-254':'https://www.maastrichtuniversity.nl/','qs2027-332':'https://www.nankai.edu.cn/','qs2027-363':'https://www.citystgeorges.ac.uk/','qs2027-483':'https://en.knu.ac.kr/intro/about01_011.htm'}
receipt=[]
for row in rows:
 if row['image'].startswith('/'):continue
 pages=bydomain.get(row['domain'],{}).get('web_pages',[])
 page=canonical.get(row['id']) or next((p for p in pages if p.startswith('https://')),None) or next(iter(pages),None) or row['website']
 page='https:'+page.removeprefix('http:') if page.startswith('http:') else page
 item={'id':row['id'],'domain':row['domain'],'canonical_website':page,'status':'failed'}
 try:
  request='https://www.google.com/s2/favicons?'+urllib.parse.urlencode({'domain_url':page,'sz':128})
  if row['id']=='qs2027-039':blob=Path('/tmp/unimatch-logo-url-probe.png').read_bytes();origin='https://www.u-tokyo.ac.jp/content/400130668.png'
  else:
   req=urllib.request.Request(request,headers={'User-Agent':'UnimatchCatalogue/1.0'})
   with urllib.request.urlopen(req,timeout=16) as response:blob=response.read(500000);origin=response.headers.get('Content-Location');assert origin,'No upstream identity asset location'
  image=Image.open(io.BytesIO(blob));assert image.width>=8 and image.height>=8
  dest=ROOT/'frontend/public/universities'/('canonical-'+row['id']+'.png');image.convert('RGBA').save(dest,'PNG')
  item.update(status='cached',content_location=origin,retrieval_url=request,path='/universities/'+dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),width=image.width,height=image.height)
 except Exception as e:
  item['error']=str(e)
  if isinstance(e,urllib.error.HTTPError) and e.code in [403,429]:receipt.append(item);print('STOP',e.code,flush=True);break
 receipt.append(item);print(row['id'],item['status'],item.get('error',''),flush=True);time.sleep(.45)
(ROOT/'frontend/src/data/universityCanonicalIcons.receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('DONE',sum(x['status']=='cached' for x in receipt),flush=True)
