"""Offline actual-module controls. No Fetcher construction or HTTP/provider calls."""
import asyncio,json,re
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from app.adapters.base import Candidate,CandidateProgram
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.discovery.catalog_walker import CatalogWalker,extract_links
from app.adapters.extraction import _MONEY,parse_money,for_matching,readable_text
from app.adapters.fetching import FetchResult
from app.adapters.html_parse import parse_html
from app.adapters.page_classifier import main_content,classify_page,_IRRELEVANT
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.document_ir import build_document_ir
from app.domain.enums import FetchOutcome,DegreeLevel
base=Path(__file__).resolve().parent
cache={}
for p in (base/'public-cache').glob('*.meta.json'):
 m=json.loads(p.read_text());b=p.with_name(p.name.replace('.meta.json','.body')).read_bytes()
 cache[m['url']]=(m,b)
class RetainedOnly:
 def __init__(self):self.calls=[]
 async def get(self,url):
  self.calls.append(url)
  if url not in cache: raise AssertionError('UNRETAINED_URL_NO_OFFLINE_ASSUMPTION '+url)
  m,b=cache[url]
  return FetchResult(url=url,final_url=m['final_url'],outcome=FetchOutcome.OK,status_code=m['status_code'],content=b,text=b.decode(m.get('encoding') or 'utf-8'),content_type=m['content_type'],fetched_at=datetime.fromisoformat(m['fetched_at']),content_hash=m['content_hash'])
async def run():
 out={'network_calls':0,'provider_calls':0,'model_calls':0,'requested':{'field':'Computer Science','degree':'bachelor','intake':'fall2027','academic_year':'2027/28'},'scope':'DEV native modules, exact retained bytes; no classifier override'}
 f=RetainedOnly();w=CatalogWalker(fetcher=f,domain='www.aalto.fi',degree='bachelor',fields=['Computer Science']);walks=await w.walk(['https://www.aalto.fi/en/study-options','https://www.aalto.fi/en/department-of-computer-science/courses'])
 out['walker']={'calls':f.calls,'walks':[asdict(w) for w in walks]}
 candidate=Candidate(name='Aalto University',country='Finland',city='Espoo',domain='aalto.fi',admissions_url='https://www.aalto.fi/en/admission-services',costs_url='https://www.aalto.fi/en/admission-services/scholarships-and-tuition-fees',scholarships_url='https://www.aalto.fi/en/admission-services/scholarships-and-tuition-fees')
 prog=CandidateProgram(name='Computer Science (bachelor)',field='Computer Science',degree=DegreeLevel.BACHELOR,url=None)
 f=RetainedOnly();ar=await WebRequirementsAdapter(f,'2027/28').verify(candidate,prog,'fall2027')
 out['requirements']={'calls':f.calls,'result':{'claims':[c.model_dump(mode='json') for c in ar.claims],'errors':ar.errors,'page_outcomes':[asdict(p) for p in ar.page_outcomes]}}
 f=RetainedOnly();cb,cr=await WebCostAdapter(f,'2027/28').fetch(candidate)
 out['cost']={'calls':f.calls,'breakdown':cb.model_dump(mode='json'),'result':{'claims':[c.model_dump(mode='json') for c in cr.claims],'errors':cr.errors,'page_outcomes':[asdict(p) for p in cr.page_outcomes]}}
 adm=cache[candidate.admissions_url][1].decode();s=main_content(parse_html(adm));title=parse_html(adm).title.get_text(' ',strip=True);heads=[h.get_text(' ',strip=True) for h in s.find_all(re.compile('^h[1-6]$'))]
 out['admissions_primary_vs_secondary']={'title':title,'primary_h1':[h.get_text(' ',strip=True) for h in s.find_all('h1')],'irrelevant_matches':[h for h in heads if _IRRELEVANT.search(h)],'title_irrelevant':bool(_IRRELEVANT.search(title)),'all_headings':heads,'same_source_redirect':cache[candidate.admissions_url][0]['final_url']}
 fees=cache[candidate.costs_url][1].decode();text=for_matching(readable_text(fees));m=re.search(r'(?:tuition|tuition fee|programme fee|course fee)[^.\n]{0,120}',text,re.I)
 d=build_document_ir(str(main_content(parse_html(fees))),candidate.costs_url)
 out['cost_reader_boundaries']={'legacy_first_tuition_window':m.group() if m else None,'parse_money_first_window':parse_money(m.group()) if m else None,'all_currency_atoms':[{'quote':m.group(),'parse':parse_money(m.group())} for m in _MONEY.finditer(text)],'table_cells':[asdict(b) for b in d.blocks if b.kind=='table_cell']}
 for u in ['https://www.aalto.fi/en/study-options','https://www.aalto.fi/en/department-of-computer-science/courses']:
  m,b=cache[u];html=b.decode();s=main_content(parse_html(html));main_links=extract_links(str(s),u,'www.aalto.fi');out.setdefault('catalogue_dom',[]).append({'url':u,'all_anchor_count':len(parse_html(html).find_all('a',href=True)),'main_anchor_count':len(s.find_all('a',href=True)),'main_same_site_links':[asdict(l) for l in main_links],'programme_component_shell_count':len(s.select('#app, [data-v-app], .pdb-vue, pdb-vue')),'has_programme_vue_script':bool(re.search(r'(?:pdbVue|Vue\.createApp|study-options)',str(s)))})
 return out
if __name__=='__main__':
 out=asyncio.run(run());(base/'native-saved-bytes.offline.json').write_text(json.dumps(out,indent=2,default=str)+'\n');print('walker reads',len(out['walker']['calls']),'confirmed',sum(len(w['confirmed']) for w in out['walker']['walks']));print('requirements claims',len(out['requirements']['result']['claims']),'cost claims',len(out['cost']['result']['claims']));print('admissions irrelevant headings',out['admissions_primary_vs_secondary']['irrelevant_matches']);print('legacy firstcost window',out['cost_reader_boundaries']['legacy_first_tuition_window']);print('table cells',len(out['cost_reader_boundaries']['table_cells']))
