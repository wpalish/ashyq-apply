"""Finite public editorial discovery; no model/provider, evaluation or applicant input.

Uses the product Fetcher with robots/egress/privacy unchanged. One attempt only;
stop all scheduling on the first observed429. Discovered links are candidates,
never verified admission facts. Re-run/resume requires a separate decision.
"""
import asyncio,hashlib,json,re,sys
from pathlib import Path
from urllib.parse import urljoin,urlsplit,urldefrag
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.adapters import fetching
from app.adapters.fetching import Fetcher,same_source_site
fetching.MAX_ATTEMPTS=1  # tighter retry policy, scoped to this CLI process only
OUT=Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/'STARTED.json').exists(),'A finite collection cannot silently resume or overwrite'
ROWS=json.loads((ROOT/'frontend/src/data/universityDirectory.json').read_text())
STOP=asyncio.Event();LOCK=asyncio.Lock();SEMAPHORE=asyncio.Semaphore(6)
seen={};receipts=[];candidates=[]
(OUT/'STARTED.json').write_text(json.dumps({'institutions':500,'degree_levels':['bachelor','master'],'max_pages_per_institution':9,'retry_attempts':1,'robots':True,'models':False,'candidate_status':'unreviewed','parallel_institutions':6}))
def links_of(result):
 soup=BeautifulSoup(result.content,'html.parser');links=[]
 for tag in soup.select('a[href]'):
  href=urldefrag(urljoin(result.final_url or result.url,str(tag.get('href'))))[0]
  label=' '.join(tag.get_text(' ',strip=True).split())
  if href.startswith(('http://','https://')) and label and len(href)<1800 and same_source_site(result.final_url or result.url,href):links.append((href,label[:180]))
 return list(dict.fromkeys(links))
def degree(label,url):
 text=(label+' '+url).lower()
 if re.search(r'\b(phd|dphil|doctoral|doctorate)\b',text):return None
 if re.search(r'\b(master|masters|msc|m\.sc|m\.s\.|meng|mres|maestr|magistr|maitrise|magister)\b',text):return 'master'
 if re.search(r'\b(bachelor|bachelors|bsc|b\.sc|b\.s\.|beng|undergraduate|licenc|licent)\b',text):return 'bachelor'
 return None
def named(label):
 return bool(re.search(r'computer|computing|informatics|engineering|business|economics|mathematics|biology|physics|chemistry|psychology|science|artificial intelligence|data science|informatik',label,re.I)) and len(label)>12 and not re.fullmatch(r'.*(programmes|programs|courses|degrees|admissions|requirements|graduate studies).*',label,re.I)
async def read(fetcher,row,url):
 if STOP.is_set():return None
 if url in seen:return seen[url]
 r=await fetcher.get(url);seen[url]=r
 digest=hashlib.sha256(r.content).hexdigest();entry={'institution_id':row['id'],'requested':url,'final_url':r.final_url,'status_code':r.status_code,'outcome':r.outcome.value,'fetched_at':r.fetched_at.isoformat(),'content_sha256':digest,'bytes':len(r.content),'error':r.error,'tier':r.fetch_tier}
 async with LOCK:
  receipts.append(entry)
  with (OUT/'reads.jsonl').open('a') as f:f.write(json.dumps(entry)+'\n')
  if r.content:
   (OUT/'pages').mkdir(exist_ok=True);(OUT/'pages'/f'{digest}.bin').write_bytes(r.content)
  if r.status_code==429 and not STOP.is_set():
   STOP.set();(OUT/'FIRST_429.json').write_text(json.dumps(entry,indent=2));print('STOP first429 '+url,flush=True)
 return r
async def institution(row,fetcher):
 async with SEMAPHORE:
  if STOP.is_set():return
  pages=[];found=[];issues=[]
  async def take(url):
   if len(pages)>=9 or STOP.is_set():return None
   r=await read(fetcher,row,url);pages.append(url)
   if r and r.ok:return r
   if r:issues.append({'url':url,'outcome':r.outcome.value,'status_code':r.status_code})
   return None
  try:
   home=await take(row['website'])
   if home:
    links=links_of(home)
    hubs=[(u,l) for u,l in links if re.search(r'undergraduate|postgraduate|graduate|bachelor|master|study|programmes|programs|courses|admission',l+' '+urlsplit(u).path,re.I)]
    hubs=sorted(hubs,key=lambda pair:(0 if degree(pair[1],pair[0]) else 1,len(pair[0])))[:4]
    all_links=list(links)
    for url,label in hubs:
     if url in pages:continue
     r=await take(url)
     if r:all_links.extend(links_of(r))
    for level in ['bachelor','master']:
     choices=[(u,l) for u,l in dict.fromkeys(all_links) if degree(l,u)==level and named(l)]
     if choices:
      url,label=choices[0];r=await take(url) if url not in pages else seen.get(url)
      if r and r.ok:
       soup=BeautifulSoup(r.content,'html.parser');h1=soup.find('h1');title=h1.get_text(' ',strip=True) if h1 else soup.title.get_text(' ',strip=True) if soup.title else label
       found.append({'institution_id':row['id'],'level':level,'label':label,'page_title':title[:240],'url':r.final_url or r.url,'read_at':r.fetched_at.isoformat(),'content_sha256':hashlib.sha256(r.content).hexdigest(),'state':'discovered_unreviewed'})
    candidates.extend(found)
  except Exception as e:issues.append({'error':str(e),'type':type(e).__name__})
  result={'institution_id':row['id'],'name':row['name'],'pages':len(pages),'programmes':found,'issues':issues,'status':'interrupted' if STOP.is_set() else 'observed' if found else 'needs_editorial_research'}
  async with LOCK:
   with (OUT/'institutions.jsonl').open('a') as f:f.write(json.dumps(result,ensure_ascii=False)+'\n')
   print(row['id']+' pages='+str(len(pages))+' programme_candidates='+str(len(found)),flush=True)
async def main():
 async with Fetcher(OUT/'cache',timeout=12) as fetcher:
  await asyncio.gather(*(institution(row,fetcher) for row in ROWS))
 (OUT/'candidates.json').write_text(json.dumps(candidates,ensure_ascii=False,indent=2))
 (OUT/'TERMINAL.json').write_text(json.dumps({'stopped_on_429':STOP.is_set(),'reads':len(receipts),'programme_candidates':len(candidates),'qualified_programmes':0,'unprocessed_institutions':500-len((OUT/'institutions.jsonl').read_text().splitlines()) if (OUT/'institutions.jsonl').exists() else 500},indent=2))
if __name__=='__main__':asyncio.run(main())
