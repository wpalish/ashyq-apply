import asyncio,json,sys
from contextlib import contextmanager
import control_support as c
from run_controls import wrapper,safe,urls
from app.pipeline.control import UniversityReadStopped

async def main():
 rows=[];cap=UniversityReadStopped('read_cap');pages=c.catalog([(c.PREFIX+'a','BSc Computer Science',c.programme())])
 @contextmanager
 def refuse(candidate):
  raise cap
  yield
 for kind,module in [('live',c.live),('catalogue',c.catalogue)]:
  out=await wrapper(module,True,pages,['computer science'],kind=kind,scope=refuse)
  okay=out['error'] is None and not urls(out) and out['gets']==[] and len(out['candidates'])==1 and 'unknown' in out['candidates'][0]['notes'].lower()
  rows.append({'case':'entry_read_cap.'+kind,'status':'PASS' if okay else 'RED','result':safe(out)})
 async def later(entry,domain,selected,trace,profile):
  for _ in range(5):trace.charge_search_query_attempt()
  raise cap
 out=await wrapper(c.catalogue,True,pages,['computer science'],kind='catalogue',search=later,precharge=1)
 okay=out['error'] is None and urls(out)==[c.PREFIX+'a'] and out['candidates'][0]['search_queries_used']==6 and out['traces'][0]['search_queries_sent']==6 and not any(x['exception_active'] for x in out['applies'])
 rows.append({'case':'upstream1_later5_current_counter','status':'PASS' if okay else 'RED','result':safe(out),'counts_are_vendor_HTTP':False})
 report={'checks':rows,'counts':{'total':len(rows),'PASS':sum(x['status']=='PASS' for x in rows),'RED':sum(x['status']=='RED' for x in rows)},'network_calls':0,'native_worker_rerun':False}
 path=c.B/'b-finite.json';assert not path.exists();path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['counts']))
if __name__=='__main__':asyncio.run(main())
