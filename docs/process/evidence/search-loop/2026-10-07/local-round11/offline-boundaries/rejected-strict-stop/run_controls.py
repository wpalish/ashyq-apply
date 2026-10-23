from __future__ import annotations
import asyncio,hashlib,importlib.util,json,socket,sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
B=Path(__file__).resolve().parent
BASE=B.parents[1];REPO=BASE/'ashyq-apply/backend'
sys.path.insert(0,str(REPO))
def deny(*a,**kw):raise AssertionError('No network/provider/model permitted')
socket.getaddrinfo=deny;socket.create_connection=deny;socket.socket.connect=deny
import httpx
httpx.AsyncClient.send=deny;httpx.Client.send=deny
from app.adapters.discovery import catalog_walker as actual
from app.adapters.discovery import live_discovery as ld
from app.adapters.fetching import FetchResult
from app.adapters import page_classifier as pc
from app.domain.enums import FetchOutcome
from app.pipeline.control import RunCancelled,LeaseLost,UniversityReadStopped
spec=importlib.util.spec_from_file_location('external_strict_own_route',B/'catalog_walker.proposed.py')
proposal=importlib.util.module_from_spec(spec);sys.modules[spec.name]=proposal;spec.loader.exec_module(proposal)
PLAN=json.loads((B/'PLAN.json').read_text())
for rel,want in PLAN['current_source_sha256'].items():assert hashlib.sha256((REPO/rel).read_bytes()).hexdigest()==want,rel
assert proposal.WALKER_STOP_AFTER_OWN_FIELD_ROUTES is False
assert ld.SUBJECT_PHRASE_MATCH is False and pc.PROGRAMME_IDENTITY_BEFORE_FUNDING is False
PREFIX='https://example.edu/bachelors/'
CAT=PREFIX+'catalog'
CS='https://www.rug.nl/bachelors/computing-science'
GRCAT='https://www.rug.nl/bachelors/alphabet'
rows=json.loads((BASE/'local-round9/b-confirmed-coverage-plan/retained-receipt.json').read_text())['pages']
retained={}
for row in rows:
 p=Path(row['body_owned']);m=Path(row['meta_owned']);raw=p.read_bytes();meta=json.loads(m.read_text());assert hashlib.sha256(raw).hexdigest()==row['body_sha256'];retained[row['url']]=(raw,meta)

def html(name='BSc Computer Science',title=None,extra='',meta='',curriculum=True):
 academic='<section><h2>Curriculum</h2><p>Year 1 modules include programming, algorithms and mathematical foundations. Year 2 modules include software systems, databases and research projects, with 120 credits in total.</p></section>' if curriculum else '<p>Contact our department for general research information.</p>'
 return f'<html><head><title>{title or name} | Example University</title></head><body><main>{meta}<h1>{name}</h1><p>This degree programme provides practical and theoretical education for future graduates.</p>{academic}{extra}</main></body></html>'

class MockFetcher:
 def __init__(self,pages):self.pages=pages;self.calls=[];self.results={}
 async def get(self,url,**kw):
  self.calls.append(url);item=self.pages[url]
  if isinstance(item,BaseException):raise item
  if isinstance(item,FetchResult):r=item
  elif isinstance(item,tuple):
   raw,m=item;r=FetchResult(url=url,final_url=m['final_url'],outcome=FetchOutcome.OK,status_code=m['status_code'],content=raw,text=raw.decode(m['encoding']),content_type=m['content_type'],content_hash=m['content_hash'],fetched_at=datetime.fromisoformat(m['fetched_at']))
  else:r=FetchResult(url=url,final_url=url,outcome=FetchOutcome.OK,status_code=200,text=item,content=item.encode())
  self.results[url]=r;return r

def pages_for(entries):
 cat='<html><head><title>Bachelor programmes</title></head><main><h1>Bachelor programmes</h1>'+''.join(f'<a href="{PREFIX+key}">{label}</a>' for key,label,body in entries)+'</main></html>'
 return {CAT:cat,**{PREFIX+key:body for key,label,body in entries}}

async def run(module,flag,pages,fields,cat=CAT,top_n=20):
 f=MockFetcher(pages);module.WALKER_STOP_AFTER_OWN_FIELD_ROUTES=flag
 w=module.CatalogWalker(fetcher=f,domain=cat.split('/')[2],degree='bachelor',fields=fields)
 result=await w.walk_catalog(cat,top_n=top_n)
 return {'calls':f.calls,'walk':asdict(result)},f

REPORT=[]
def record(name,expectation,check,**extra):
 REPORT.append({'case':name,'status':'PASS' if check else 'RED','expected':expectation,**extra})

async def control(name,pages,fields,check,cat=CAT,top_n=20):
 original,of=await run(actual,False,pages,fields,cat,top_n)
 off,_=await run(proposal,False,pages,fields,cat,top_n)
 on,nf=await run(proposal,True,pages,fields,cat,top_n)
 record(name+'.OFF','Native actual result and get order unchanged',original==off,actual=original,proposal_off=off)
 okay=check(on,original,nf)
 record(name+'.ON','Own route stop/continue contract',okay,on=on)
 return on,nf

async def main():
 # Original stored catalogue ordering, all five native budgeted leads.
 gr={u:x for u,x in retained.items() if '.rug.nl/' in u}
 gr['https://test.ucms.rug.nl/bachelors/pedagogical-sciences']=FetchResult(url='https://test.ucms.rug.nl/bachelors/pedagogical-sciences',outcome=FetchOutcome.ROBOTS_DISALLOWED,error='Retained refusal; no HTML')
 await control('saved_groningen',gr,['computer science'],lambda on,old,f:old['calls'][1:]==[CS,'https://www.rug.nl/bachelors/information-science','https://www.rug.nl/bachelors/data-science-society','https://www.rug.nl/bachelors/liberal-arts-and-sciences','https://test.ucms.rug.nl/bachelors/pedagogical-sciences'] and on['calls']==[GRCAT,CS] and on['walk']['confirmed']==[CS],GRCAT,5)
 # Actual saved detail bytes, synthetic catalogue only. AUT Data Science still first.
 au={u:x for u,x in retained.items() if 'aut.ac.nz/' in u};auc='https://www.aut.ac.nz/study/synthetic-catalogue';labels={u:pc.classify_page(url=u,html=raw.decode(m['encoding'])).title for u,(raw,m) in au.items()}
 au[auc]='<html><head><title>Bachelor programmes</title></head><main><h1>Bachelor programmes</h1>'+''.join(f'<a href="{u}">{v}</a>' for u,v in labels.items())+'</main></html>'
 await control('saved_aut_data_then_cs',au,['computer science'],lambda on,old,f:on==old and 'data-science-major' in on['calls'][1] and 'computer-science-major' in on['calls'][2] and all(proposal._own_field_route(r,pc.classify_page(url=u,html=r.text),'bachelor') is None for u,r in f.results.items() if u!=auc),auc)
 # Positive basic route; tail valid unrelated field is not read once explicit route is bound.
 good=html();tail=html('BSc Mathematics')
 await control('single_own_route',pages_for([('a','BSc Computer Science',good),('b','BSc Computer Science',tail)]),['computer science'],lambda on,old,f:on['calls']==[CAT,PREFIX+'a'] and old['calls']==[CAT,PREFIX+'a',PREFIX+'b'])
 await control('alias_duplicate_routes',pages_for([('a','BSc Computer Science',good),('b','BSc Computer Science',tail)]),['computer science','computing science'],lambda on,old,f:on['calls']==[CAT,PREFIX+'a'])
 joint=html('BSc Computer Science and Engineering')
 await control('multifield_late_math',pages_for([('a','BSc Computer Science',good),('b','BSc Computer Science',joint),('c','BSc Mathematics',tail),('d','BSc Computer Science',good)]),['computer science','mathematics'],lambda on,old,f:PREFIX+'b' in on['calls'] and PREFIX+'c' in on['calls'] and PREFIX+'d' not in on['calls'] and set(on['walk']['confirmed'][:2])=={PREFIX+'a',PREFIX+'c'})
 await control('ambiguous_before_stronger',pages_for([('a','BSc Computer Science',joint),('b','BSc Computer Science',good),('c','BSc Computer Science',good)]),['computer science'],lambda on,old,f:on['calls']==[CAT,PREFIX+'a',PREFIX+'b'] and on['walk']['confirmed']==[PREFIX+'b',PREFIX+'a'])
 for name,fields,first in [('unknown_field',['Geology'],html('BSc Geology')),('empty_fields',[],good),('known_and_unknown',['computer science','Geology'],good),('blank_entry',['computer science',''],good)]:
  await control(name,pages_for([('a','BSc '+(fields[0] if fields else 'Computer Science'),first),('b','BSc Computer Science',good)]),fields,lambda on,old,f:on==old)
 variants={
  'reverse_phrase':html('BSc Science Computer'),
  'joint_related_phrase':joint,
  'alias_extra_subject':html('BSc Business Informatics'),
  'department_only':html(curriculum=False),
  'remote_degree':html('Computer Science',title='BSc Computer Science',extra='<p>Applicants holding a Bachelor degree may contact the office.</p>'),
  'generic_title':html(title='Bachelor programmes'),
  'chrome_h1':html().replace('<h1>','<h1 class="menu-title">',1),
  'two_main_identities':html(extra='<h1>BSc Data Science</h1>'),
  'funding_purpose':html(extra='<p>This page provides scholarships and funding for applicants.</p>'),
  'wrong_local_degree':html('MSc Computer Science'),
  'contradictory_degree_label':html('Computer Science',title='BSc Computer Science',meta='<span>Master</span>'),
 }
 for name,first in variants.items():
  await control(name,pages_for([('a','BSc Computer Science',first),('b','BSc Computer Science',good)]),['computer science'],lambda on,old,f:PREFIX+'b' in on['calls'] and (PREFIX+'a' not in f.results or proposal._own_field_route(f.results[PREFIX+'a'],pc.classify_page(url=PREFIX+'a',html=f.results[PREFIX+'a'].text),'bachelor') is None))
 for i,signal in enumerate([RunCancelled('saved-control'),LeaseLost('saved-control'),UniversityReadStopped('checkpoint_busy'),UniversityReadStopped('read_cap')]):
  p=pages_for([('a','BSc Computer Science',signal),('b','BSc Computer Science',good)])
  proposal.WALKER_STOP_AFTER_OWN_FIELD_ROUTES=True;f=MockFetcher(p)
  try:await proposal.CatalogWalker(fetcher=f,domain='example.edu',degree='bachelor',fields=['computer science']).walk_catalog(CAT)
  except type(signal) as got:record('typed_stop_'+str(i),'Original instance propagates before confirmation',got is signal,calls=f.calls,reason=getattr(signal,'reason',None))
  else:record('typed_stop_'+str(i),'Original instance propagates before confirmation',False,calls=f.calls)
 # General scope-boundary blockers: every requested field has its own proof, but a
 # stronger applicable source appears later. Keep RED, never reinterpret as complete.
 for name,restriction in [('year_loss','This degree programme admits applicants only for the 2026/27 academic year.'),('population_loss','This degree programme is available only to domestic applicants.'),('nondegree_loss','This is a non-degree visiting study course; it does not award a Bachelor degree.')]:
  first=html(extra=f'<p>{restriction}</p>');second=html(extra='<p>International applicants can apply for the 2027/28 academic year.</p>')
  old,_=await run(actual,False,pages_for([('a','BSc Computer Science',first),('b','BSc Computer Science',second)]),['computer science'])
  on,_=await run(proposal,True,pages_for([('a','BSc Computer Science',first),('b','BSc Computer Science',second)]),['computer science'])
  record(name,'Retain later stronger applicable route; unresolved scope cannot authorize eliminating it',PREFIX+'b' in on['calls'],original=old,on=on,exact_earlier_source_sentence=restriction,source_scope_inferred=False,claim_count=0)
 proposal.WALKER_STOP_AFTER_OWN_FIELD_ROUTES=False
 report={'current_actual_source':PLAN['current_source_sha256'],'proposal_sha256':hashlib.sha256((B/'catalog_walker.proposed.py').read_bytes()).hexdigest(),'checks':REPORT,'counts':{'PASS':sum(r['status']=='PASS' for r in REPORT),'RED':sum(r['status']=='RED' for r in REPORT),'checks':len(REPORT)},'external_calls':0,'source_edits':0,'claims_created':0,'fresh_actual_fetcher_IO':0,'proof_kind':'Saved originals and synthetic FetchResults in actual walker and isolated external proposed module; not full adapter, SQL, native guard, or scored evaluation','candidate_status':'NOT_SOURCE_READY; scope controls retained separately'}
 (B/'controls.original.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
 print(json.dumps(report['counts']))
 for row in REPORT:
  if row['status']=='RED':print(row['case'],row.get('on',{}).get('calls'))
if __name__=='__main__':asyncio.run(main())
