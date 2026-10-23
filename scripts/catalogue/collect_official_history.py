"""Read institutional public history pages; never retry refused sources."""
import json,re,urllib.request,urllib.parse,concurrent.futures
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class Page(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[];self.links=[];self.link=None
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if t in ['script','style','nav','footer','header']:self.skip+=1
  if t=='a':self.link=[a.get('href',''),'']
  if t in ['p','h1','h2','li']:self.parts.append('\n')
 def handle_endtag(self,t):
  if t in ['script','style','nav','footer','header']:self.skip=max(0,self.skip-1)
  if t=='a' and self.link:self.links.append(self.link);self.link=None
  if t in ['p','h1','h2','li']:self.parts.append('\n')
 def handle_data(self,s):
  if self.link:self.link[1]+=s
  if not self.skip:self.parts.append(s)
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'UnimatchCatalogue/1.0 (public institution history snapshot)'})
 with urllib.request.urlopen(req,timeout=14) as f:
  p=Page();p.feed(f.read(1_500_000).decode('utf-8','replace'));return p,f.url
def collect(row):
 result={'id':row['id'],'name':row['name'],'reads':[]};url=row['website']
 if not url:return result
 try:
  p,landed=fetch(url);result['reads'].append({'url':landed})
  history=[(href,label) for href,label in p.links if re.search(r'\bhistory\b|our story|istorija|история|storia',label,re.I)]
  about=[(href,label) for href,label in p.links if re.search(r'^\s*(about us|about the university|about .+ university|university overview|history and tradition)\s*$',label,re.I)]
  for href,label in (history or about)[:1]:
   target=urllib.parse.urljoin(landed,href)
   host=urllib.parse.urlsplit(target).hostname or ''
   origin=urllib.parse.urlsplit(landed).hostname or ''
   if host==origin or host.endswith('.'+origin.removeprefix('www.')):
    p,landed=fetch(target);result['reads'].append({'url':landed,'label':label})
  text=''.join(p.parts);chunks=[re.sub(r'\s+',' ',x).strip() for x in text.split('\n')]
  result['candidates']=[x for x in chunks if len(x)>70 and re.search(r'found(ed|ation)|establish(ed|ment)|opened|created|origins|основан|истори|fundad|criada|fonda|gründ',x,re.I) and re.search(r'\b(1[0-9]{3}|20[0-2][0-9])\b',x)][:4]
 except Exception as e:result['error']=str(e)
 return result
rows=json.loads((ROOT/'frontend/src/data/universityDirectory.json').read_text())
missing=[x for x in rows if not x['history']]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 result=[]
 for item in ex.map(collect,missing):result.append(item);print(item['id'],len(item.get('candidates',[])),item.get('error',''),flush=True)
Path('/tmp/unimatch-official-history-candidates.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
