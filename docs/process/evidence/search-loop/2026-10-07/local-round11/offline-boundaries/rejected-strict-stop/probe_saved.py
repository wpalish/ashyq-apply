from __future__ import annotations
import hashlib,json,socket,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[2]
REPO=BASE/'ashyq-apply/backend'
sys.path.insert(0,str(REPO))
def deny(*args,**kwargs):raise AssertionError('Offline saved-source probe forbids network')
socket.getaddrinfo=deny;socket.create_connection=deny;socket.socket.connect=deny
import httpx
httpx.AsyncClient.send=deny;httpx.Client.send=deny
from app.adapters import page_classifier as pc
from app.adapters.html_parse import parse_html
from app.adapters.extraction import html_title
from app.adapters.discovery import live_discovery as ld
from app.adapters.search.ontology import fields_named_in
B=BASE/'local-round9/b-confirmed-coverage-plan'
paths={'groningen':B/'retained/groningen/76bb9de33b9a2ae5369072e314127aa4.body','aut-data':B/'retained/aut/data-science.body','aut-cs':B/'retained/aut/computer-science.body'}
out=[]
for name,path in paths.items():
 raw=path.read_bytes();html=raw.decode();meta=json.loads(path.with_suffix('.meta.json').read_text());root=pc.content_for_reading(parse_html(html));page=pc.classify_page(url=meta['final_url'],html=html);title=html_title(html)
 h1s=root.find_all('h1');heads=[]
 for h in root.find_all(['h1','h2','h3']):
  heads.append({'tag':h.name,'text':h.get_text(' ',strip=True),'parent':str(h.parent)[:750]})
 out.append({'case':name,'url':meta['final_url'],'raw_body_sha256':hashlib.sha256(raw).hexdigest(),'metadata_sha256':hashlib.sha256(path.with_suffix('.meta.json').read_bytes()).hexdigest(),'content_hash':meta['content_hash'],'title':title,'class':page.page_type.value,'degree':page.degree_level,'subject':page.subject,'legacy_reject_reason':ld.profile_rejects(page,'bachelor',['computer science']),'own_h1':[h.get_text(' ',strip=True) for h in h1s],'own_h1_fields':[sorted(fields_named_in(h.get_text(' ',strip=True))) for h in h1s],'academic_proof_existing_helper':pc._programme_content_identity(h1s[0].get_text(' ',strip=True) if h1s else '',title,'',root.get_text(' ',strip=True),root),'headings':heads})
Path(__file__).with_name('saved-probe.offline.json').write_text(json.dumps(out,indent=2)+'\n')
for r in out:
 print(json.dumps({k:v for k,v in r.items() if k!='headings'}))
 for h in r['headings']:
  if h['tag']=='h1' or any(w in h['text'].lower() for w in ['curriculum','study','course','programme','qualification','degree']):print(json.dumps(h))
