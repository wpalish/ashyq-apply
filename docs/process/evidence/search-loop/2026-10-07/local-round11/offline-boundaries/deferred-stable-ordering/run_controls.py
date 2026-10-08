from __future__ import annotations
import asyncio,hashlib,importlib.util,json,socket,sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
B=Path(__file__).resolve().parent;BASE=B.parents[1];REPO=BASE/'ashyq-apply/backend'
sys.path.insert(0,str(REPO))
def deny(*a,**kw):raise AssertionError('Offline ordering controls forbid external calls')
socket.getaddrinfo=deny;socket.create_connection=deny;socket.socket.connect=deny
import httpx
httpx.AsyncClient.send=deny;httpx.Client.send=deny
from app.adapters.discovery import catalog_walker as actual
from app.adapters.discovery import live_discovery as ld
from app.adapters.fetching import FetchResult
from app.adapters import page_classifier as pc
from app.domain.enums import FetchOutcome
from app.pipeline.control import RunCancelled,LeaseLost,UniversityReadStopped
from app.schemas.profile import ApplicantProfileIn
spec=importlib.util.spec_from_file_location('external_stable_order',B/'catalog_walker.proposed.py');proposal=importlib.util.module_from_spec(spec);sys.modules[spec.name]=proposal;spec.loader.exec_module(proposal)
plan=json.loads((B/'PLAN.json').read_text())
for rel,want in plan['current_source_sha256'].items():assert hashlib.sha256((REPO/rel).read_bytes()).hexdigest()==want,rel
assert proposal.WALKER_ORDER_EXACT_FIELD_LEADS is False
assert ld.SUBJECT_PHRASE_MATCH is False and pc.PROGRAMME_IDENTITY_BEFORE_FUNDING is False
PREFIX='https://example.edu/bachelors/';CAT=PREFIX+'catalog';GRCAT='https://www.rug.nl/bachelors/alphabet';CS='https://www.rug.nl/bachelors/computing-science'
rows=json.loads((BASE/'local-round9/b-confirmed-coverage-plan/retained-receipt.json').read_text())['pages'];retained={}
for row in rows:
 p=Path(row['body_owned']);m=Path(row['meta_owned']);raw=p.read_bytes();meta=json.loads(m.read_text());assert hashlib.sha256(raw).hexdigest()==row['body_sha256'];retained[row['url']]=(raw,meta)

def html(name='BSc Computer Science',extra=''):
 return f'<html><head><title>{name} | Example University</title></head><body><main><h1>{name}</h1><p>This degree programme provides practical and theoretical education.</p><section><h2>Curriculum</h2><p>Year 1 modules include programming, algorithms and mathematical foundations. Year 2 modules include software systems, databases and research projects, with 120 credits.</p></section>{extra}</main></body></html>'

class MockFetcher:
 def __init__(self,pages):self.pages=pages;self.calls=[]
 async def get(self,url,**kw):
  self.calls.append(url);item=self.pages[url]
  if isinstance(item,BaseException):raise item
  if isinstance(item,FetchResult):return item
  if isinstance(item,tuple):
   raw,m=item;return FetchResult(url=url,final_url=m['final_url'],outcome=FetchOutcome.OK,status_code=m['status_code'],content=raw,text=raw.decode(m['encoding']),content_type=m['content_type'],content_hash=m['content_hash'],fetched_at=datetime.fromisoformat(m['fetched_at']))
  return FetchResult(url=url,final_url=url,outcome=FetchOutcome.OK,status_code=200,text=item,content=item.encode())

def pages_for(entries):
 cat='<html><head><title>Bachelor programmes</title></head><main><h1>Bachelor programmes</h1>'+''.join(f'<a href="{PREFIX+k}">{label}</a>' for k,label,body in entries)+'</main></html>'
 return {CAT:cat,**{PREFIX+k:body for k,label,body in entries}}

async def walk(module,flag,pages,fields,cat=CAT,top_n=20):
 if module is proposal:proposal.WALKER_ORDER_EXACT_FIELD_LEADS=flag
 f=MockFetcher(pages);w=module.CatalogWalker(fetcher=f,domain=cat.split('/')[2],degree='bachelor',fields=fields);r=await w.walk_catalog(cat,top_n=top_n)
 return {'calls':f.calls,'walk':asdict(r)}

REPORT=[]
def record(case,expected,okay,**extra):REPORT.append({'case':case,'status':'PASS' if okay else 'RED','expected':expected,**extra})

def completed_preserved(before,after):
 keys=['catalogue_url','candidates','confirmed','confirmed_subjects']
 return Counter(before['calls'])==Counter(after['calls']) and all(before['walk'][k]==after['walk'][k] for k in keys) and Counter(tuple(x) for x in before['walk']['outcomes'])==Counter(tuple(x) for x in after['walk']['outcomes'])

async def control(name,pages,fields,check=lambda old,on:True,cat=CAT,top_n=20):
 native=await walk(actual,False,pages,fields,cat,top_n);off=await walk(proposal,False,pages,fields,cat,top_n);on=await walk(proposal,True,pages,fields,cat,top_n)
 record(name+'.OFF','Exact native actual asdict and call sequence unchanged',native==off,native=native,off=off)
 record(name+'.ON','Same admitted/read multiset/count, confirmed order, subjects and caller-cap membership; only priority read order can differ',completed_preserved(native,on) and check(native,on),native=native,on=on)
 return native,on

def profile(fields):
 return ApplicantProfileIn.model_validate({'display_name':'Synthetic controls only','context':{'level':'bachelor','intended_fields':fields,'intake_term':'fall','intake_year':2027,'citizenship':'Kazakhstan','country_of_residence':'Kazakhstan','education_country':'Kazakhstan','education_system':'KZ national secondary','graduation_date':'2027-05-25'},'academics':{'gpa':{'raw_value':4.8,'raw_scale_max':5.0,'raw_scale_label':'KZ 5-point'},'ielts':{'overall':7.0,'listening':7.5,'reading':7.5,'writing':6.0,'speaking':7.0},'sat':{'total':1400,'math':760,'reading_writing':640}},'funding':{'max_annual_budget':6000,'max_acceptable_gap':6000}})

async def caller(pages,fields,enabled,initial=None):
 f=MockFetcher(pages);adapter=ld.LiveDiscoveryAdapter(f);trace=ld.DiscoveryTrace('Synthetic Example University','example.edu');selected={c:[] for c in ld.PageCategory.ALL};selected[ld.PageCategory.PROGRAM_CATALOG]=[CAT];selected[ld.PageCategory.PROGRAM_PAGE]=list(initial or [])
 if enabled:
  proposal.WALKER_ORDER_EXACT_FIELD_LEADS=True
  # Explicit external proposal injection at the native class seam, not source replacement.
  with patch.object(actual,'CatalogWalker',proposal.CatalogWalker):await adapter._walk_catalogs({'homepage':'https://example.edu/'},selected,trace,profile(fields))
 else:await adapter._walk_catalogs({'homepage':'https://example.edu/'},selected,trace,profile(fields))
 return {'selected':selected,'gets':f.calls,'confirmed_count':trace.walker['programs_confirmed']}

async def main():
 gr={u:x for u,x in retained.items() if '.rug.nl/' in u};u='https://test.ucms.rug.nl/bachelors/pedagogical-sciences';gr[u]=FetchResult(url=u,outcome=FetchOutcome.ROBOTS_DISALLOWED,error='Retained refusal; no body')
 await control('saved_groningen_all5',gr,['computer science'],lambda old,on:old['calls']==on['calls'] and len(on['calls'])==6,GRCAT,5)
 au={u:x for u,x in retained.items() if 'aut.ac.nz/' in u};auc='https://www.aut.ac.nz/study/synthetic-catalogue';labels={u:pc.classify_page(url=u,html=raw.decode(m['encoding'])).title for u,(raw,m) in au.items()};au[auc]='<html><head><title>Bachelor programmes</title></head><main><h1>Bachelor programmes</h1>'+''.join(f'<a href="{u}">{label}</a>' for u,label in labels.items())+'</main></html>'
 await control('saved_aut_both',au,['computer science'],lambda old,on:'data-science-major' in old['calls'][1] and 'computer-science-major' in on['calls'][1] and len(on['calls'])==3 and 'data-science-major' in on['walk']['confirmed'][0] and 'computer-science-major' in on['walk']['confirmed'][1],auc)
 # Misleading same labels preserve stable Data-first body ordering and continue to CS.
 au[auc]='<html><head><title>Bachelor programmes</title></head><main><h1>Bachelor programmes</h1>'+''.join(f'<a href="{u}">BSc Computer Science</a>' for u in labels)+'</main></html>'
 await control('saved_aut_mislabelled_data_first',au,['computer science'],lambda old,on:old['calls']==on['calls'] and 'data-science-major' in on['calls'][1] and 'computer-science-major' in on['calls'][2],auc)
 good=html();joint=html('BSc Computer Science and Engineering');math=html('BSc Mathematics')
 await control('exact_before_ambiguous_read_only',pages_for([('a','BSc Computer Science and Engineering',joint),('b','BSc Computer Science',good),('c','BSc Computer Science with placement',good)]),['computer science'],lambda old,on:old['calls']==[CAT,PREFIX+'a',PREFIX+'b',PREFIX+'c'] and on['calls']==[CAT,PREFIX+'b',PREFIX+'a',PREFIX+'c'])
 await control('multifield_late_route',pages_for([('a','BSc Computer Science and Engineering',joint),('b','BSc Computer Science',good),('c','BSc Mathematics',math)]),['computer science','mathematics'],lambda old,on:on['calls']==[CAT,PREFIX+'b',PREFIX+'c',PREFIX+'a'] and PREFIX+'c' in on['walk']['confirmed'])
 await control('multifield_missing_hint_no_reorder',pages_for([('a','BSc Computer Science and Engineering',joint),('b','BSc Computer Science',good),('c','BSc Mathematics with placement',math)]),['computer science','mathematics'],lambda old,on:on==old)
 for name,fields in [('unknown',['Geology']),('empty',[]),('blank',['computer science','']),('known_unknown',['computer science','Geology'])]:
  await control('no_order_'+name,pages_for([('a','BSc Computer Science and Engineering',joint),('b','BSc Computer Science',good)]),fields,lambda old,on:on==old)
 await control('alias_duplicate_route',pages_for([('a','BSc Computer Science and Engineering',joint),('b','Computing Science',good)]),['computer science','computing science'],lambda old,on:on['calls']==[CAT,PREFIX+'b',PREFIX+'a'])
 await control('top_n_admission_unchanged',pages_for([('a','BSc Computer Science and Engineering',joint),('b','BSc Computer Science with placement',good),('c','BSc Computer Science',good)]),['computer science'],lambda old,on:PREFIX+'c' not in on['calls'] and on==old,top_n=2)
 restrictions=[('year','This degree programme admits applicants only for the 2026/27 academic year.'),('population','This degree programme is available only to domestic applicants.'),('nondegree','This is a non-degree visiting study course; it does not award a Bachelor degree.')]
 for name,sentence in restrictions:
  p=pages_for([('a','BSc Computer Science',html(extra=f'<p>{sentence}</p>')),('b','BSc Computer Science',html(extra='<p>International applicants can apply for the 2027/28 academic year.</p>'))])
  await control('late_stronger_'+name,p,['computer science'],lambda old,on:PREFIX+'b' in on['calls'] and PREFIX+'b' in on['walk']['confirmed'] and on==old)
 # Actual caller cap: correct placement degree first, then three literal labels.
 valid=html('BSc Computer Science with an industrial placement year',extra='<p>International applicants can apply for 2027/28.</p>')
 bad=html(extra='<p>This degree programme is available only to domestic applicants for 2026/27.</p>')
 p=pages_for([('a','BSc Computer Science with an industrial placement year',valid),('b','BSc Computer Science',bad),('c','BSc Computer Science',bad),('d','BSc Computer Science',bad)])
 for initial in [[],['https://example.edu/bachelors/prior-1'],['https://example.edu/bachelors/prior-1','https://example.edu/bachelors/prior-2']]:
  off=await caller(p,['computer science'],False,initial);on=await caller(p,['computer science'],True,initial)
  record('native_caller_remaining_'+str(ld.MAX_PAGES_PER_CATEGORY-len(initial)),'Actual _walk_catalogs selected capped membership unchanged and valid original-first route retained',off['selected']==on['selected'] and PREFIX+'a' in on['selected'][ld.PageCategory.PROGRAM_PAGE] and Counter(off['gets'])==Counter(on['gets']),off=off,on=on)
 # Stop before a returned walk stays a propagated original exception; no fabricated walk.
 for i,signal in enumerate([RunCancelled('saved-control'),LeaseLost('saved-control'),UniversityReadStopped('checkpoint_busy'),UniversityReadStopped('read_cap')]):
  p=pages_for([('a','BSc Computer Science and Engineering',signal),('b','BSc Computer Science',good)])
  proposal.WALKER_ORDER_EXACT_FIELD_LEADS=True;f=MockFetcher(p)
  try:await proposal.CatalogWalker(fetcher=f,domain='example.edu',degree='bachelor',fields=['computer science']).walk_catalog(CAT)
  except type(signal) as got:record('typed_original_'+str(i),'Original instance propagates even after priority page has been read',got is signal and f.calls==[CAT,PREFIX+'b',PREFIX+'a'],gets=f.calls,reason=getattr(got,'reason',None))
  else:record('typed_original_'+str(i),'Original exception propagates',False)
 proposal.WALKER_ORDER_EXACT_FIELD_LEADS=False
 report={'proposal_sha256':hashlib.sha256((B/'catalog_walker.proposed.py').read_bytes()).hexdigest(),'checks':REPORT,'counts':{'PASS':sum(x['status']=='PASS' for x in REPORT),'RED':sum(x['status']=='RED' for x in REPORT),'checks':len(REPORT)},'network_provider_model_source_Git_STOP_changes':0,'claim_count':0,'genuine_Job_SQL_budget_proof':False,'end_to_end_or_scored_gain':False,'native_caller_used':True,'native_caller_proposal_injection':'temporary class seam only; ordinary app dependencies','same_admitted_fetch_count_set_and_completed_confirmations':True,'source_rule_default':False}
 (B/'controls.final.json').write_text(json.dumps(report,indent=2,default=str)+'\n');print(json.dumps(report['counts']))
 for row in REPORT:
  if row['status']=='RED':print(row['case'])
if __name__=='__main__':asyncio.run(main())
