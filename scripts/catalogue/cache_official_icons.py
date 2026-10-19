"""Cache a declared icon from each institutional homepage after an aggregator miss.
No retries or authentication; sources returning 403/429 stop for that institution.
"""
import json,urllib.request,urllib.parse,concurrent.futures,io,re,hashlib,ipaddress,socket
from html.parser import HTMLParser
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
class Icons(HTMLParser):
 def __init__(self):super().__init__();self.icons=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='link' and any(x in a.get('rel','').lower() for x in ['icon']):self.icons.append((0 if 'apple' in a.get('rel','') else 1,a.get('href','')))
def safe(url):
 p=urllib.parse.urlsplit(url);assert p.scheme in ['https','http'] and p.hostname and not p.username and not p.password and p.port in [None,80,443]
 for address in socket.getaddrinfo(p.hostname,None):assert ipaddress.ip_address(address[4][0]).is_global
 return url
def read(url,limit):
 req=urllib.request.Request(safe(url),headers={'User-Agent':'UnimatchCatalogue/1.0 (public institutional icon snapshot)'})
 with urllib.request.urlopen(req,timeout=14) as response:return response.read(limit),response.url,response.headers.get('Content-Type','')
def collect(row):
 result={'id':row['id'],'domain':row['domain'],'status':'failed'}
 try:
  raw,page,mime=read(row['website'],1_500_000);parser=Icons();parser.feed(raw.decode('utf-8','replace'))
  href=next((href for _,href in sorted(parser.icons) if href and not href.startswith('data:')),None)
  if not href:raise ValueError('No declared icon in homepage')
  url=urllib.parse.urljoin(page,href);blob,asset,mime=read(url,1_000_000)
  if 'svg' in mime or blob.lstrip().startswith(b'<svg') or b'<svg' in blob[:500]:
   assert not re.search(br'<!DOCTYPE|<!ENTITY|<script|<foreignObject|(?:href|src)\s*=\s*["\'](?:https?:|//)',blob,re.I)
   dest=ROOT/'frontend/public/universities'/('official-'+row['id']+'.svg');dest.write_bytes(blob);width=height=None
  else:
   image=Image.open(io.BytesIO(blob));assert 8<=image.width<=4096 and 8<=image.height<=4096
   dest=ROOT/'frontend/public/universities'/('official-'+row['id']+'.png');image.convert('RGBA').save(dest,'PNG');width,height=image.size
  result.update(status='cached',page=page,content_location=asset,path='/universities/'+dest.name,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),width=width,height=height)
 except Exception as e:result['error']=str(e)
 return result
rows=json.loads((ROOT/'frontend/src/data/universityDirectory.json').read_text());old=json.loads((ROOT/'frontend/src/data/universityIcons.receipt.json').read_text());accepted={x['id']:x for x in old if x['status']=='cached'}
missing=[row for row in rows if row['id'] not in accepted or accepted[row['id']]['domain']!=row['domain']]
result=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for item in pool.map(collect,missing):result.append(item);print(item['id'],item['status'],item.get('error',''),flush=True)
(ROOT/'frontend/src/data/universityOfficialIcons.receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print('DONE',sum(row['status']=='cached' for row in result),'/',len(result),flush=True)
