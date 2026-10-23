"""Offline log/public-meta/raw reconciliation; no gold, network or score."""
import json,re
from pathlib import Path
from app.adapters.discovery.live_discovery import parse_sitemap,canonical_url
b=Path(__file__).resolve().parent
raw=json.loads((b/'terminal/aalto.raw.json').read_text());t=raw['canary']['institutions'][0]['discovery_trace'];log=(b/'terminal/aalto.log').read_text();native=json.loads((b/'native-saved-bytes.offline.json').read_text())
metas=[json.loads(m.read_text()) for m in (b/'public-cache').glob('*.meta.json')];urls=[m['url'] for m in metas]
starts=[{'number':int(n),'t_s_log_rounded':int(tm),'url_log_truncated_at_120_chars':u} for n,tm,u in re.findall(r'^get #(\d+) start t=(\d+)s (https?://\S+)',log,re.M)]
ends={int(n):{'elapsed_s_log_rounded':float(s),'outcome':o} for n,s,o in re.findall(r'^get #(\d+) took ([\d.]+)s (\S+)',log,re.M)}
for x in starts:
 x.update(ends[x['number']]);u=x['url_log_truncated_at_120_chars']
 if x['outcome']=='ok':
  matches=[u] if u in urls else [v for v in urls if len(u)==120 and v.startswith(u)]
  assert len(matches)==1,(u,matches)
  x['exact_requested_url_from_retained_meta']=matches[0]
 else:x['exact_requested_url_from_complete_log']=u
xml=[];locations=[];children=[]
for p in (b/'public-cache').glob('*.meta.json'):
 m=json.loads(p.read_text())
 if '/sitemap.xml' not in m['url']:continue
 c,u=parse_sitemap(p.with_name(p.name.replace('.meta.json','.body')).read_text());locations.extend(u);children.extend(c);xml.append({'url':m['url'],'children':len(c),'page_locations':len(u)})
rc=[{'url':l['url'],'label':l['label'],'score':l['score'],'source':l['source']} for w in native['walker']['walks'] for l in w['candidates']];ro=[{'url':url,'outcome':o} for w in native['walker']['walks'] for url,o in w['outcomes']]
control={'native_walker_calls_equal_get22_to38':[x['url_log_truncated_at_120_chars'] for x in starts if 22<=x['number']<=38]==native['walker']['calls'],'raw_candidates_match_native_replay':t['walker']['candidates']==rc,'raw_outcomes_equal_native_first200':t['walker']['outcomes']==ro[:200],'no_native_requirements_or_cost_claims':native['requirements']['result']['claims']==native['cost']['result']['claims']==[],'money_atom_whole_eur12000':any(x['quote']=='€12 000' and x['parse']==[12000.0,'EUR'] for x in native['cost_reader_boundaries']['all_currency_atoms'])}
assert all(control.values()),control
successful=[x['exact_requested_url_from_retained_meta'] for x in starts if x['outcome']=='ok'];failed=[x['exact_requested_url_from_complete_log'] for x in starts if x['outcome']!='ok']
out={'control':control,'get_attempts':starts,'complete_logged_get_attempts':len(starts),'exact_requested_unique_urls_reconstructed':len(set(successful+failed)),'distinct_successful_requested_urls':len(set(successful)),'success_repeated_get_attempts':len(successful)-len(set(successful)),'unique_failed_robots_urls':len(set(failed)),'raw_native_unique_get_counter':None,'raw_native_unique_get_counter_reason':'not exposed; log+retained-meta reconstructed counts are DEV diagnostics','sitemap':{'cached_documents':sorted(xml,key=lambda v:v['url']),'page_locations':len(locations),'unique_canonical_page_urls_in_read_documents':len(set(map(canonical_url,locations))),'native_seen':t['sitemap_urls_seen'],'native_kept':t['sitemap_urls_kept'],'declared_child_documents':len(children),'read_child_documents':len(xml)-1,'unread_declared_child_documents':len(set(map(canonical_url,children)))-len(xml)+1,'contents_of_unread_child':'UNKNOWN; neither fetched nor read by this review'},'stage_calls':{'robots_plus_sitemaps':13,'initial_programme_confirmation':8,'catalogue_walker':17,'search_entrypoint_read':1,'search_identity_recovery':8,'requirements':1,'costs':1,'funding':7},'native_walker_candidate_count':len(rc),'native_walker_outcomes_count':len(ro),'raw_walker_outcomes_capped_count':len(t['walker']['outcomes']),'captured_initial_programme_rank_count':40,'vendor_rank_candidates_total':None,'vendor_rank_candidates_unknown_reason':'terminal raw does not expose vendor full rank/result population','native_search_recovery_checked':8,'native_search_recovery_confirmed':0,'claims_raw':len(raw['claims'])}
assert sum(out['stage_calls'].values())==len(starts)==56
(b/'funnel-counters-and-controls.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ('get_attempts','sitemap')},indent=2))
